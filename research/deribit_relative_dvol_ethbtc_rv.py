#!/usr/bin/env python3
"""Forecast screen: relative ETH/BTC option-implied volatility -> relative realized volatility."""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01"
START_DATE = dt.date(2023, 3, 26)
TARGET_SESSIONS = 7
EVENT_STEP_SESSIONS = 7
MODEL_WINDOW = 52
VALIDATION_START = dt.date(2024, 4, 1)
TEST_START = dt.date(2025, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261126
MIN_PRICE_ROWS = 1200
MIN_DVOL_ROWS = 1200
MAX_DVOL_AGE_DAYS = 2
MAX_DVOL_PAGES = 10
DAY_MS = 86_400_000

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
REPORT_PATH = SESSION_DIR / f"{STAMP}_session-deribit-relative-dvol-ethbtc-rv-{RUN_ID}.md"
OUTPUT_DIR = ROOT / "reports" / "generated" / "deribit-relative-dvol-ethbtc-rv" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01.md"

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
DERIBIT_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
PRICE_SERIES = ("CBBTCUSD", "CBETHUSD")
CURRENCIES = ("BTC", "ETH")
BASE_FEATURES = [
    "pre_btc_rv7_log",
    "pre_btc_rv30_log",
    "pre_eth_rv7_log",
    "pre_eth_rv30_log",
]
AUGMENTED_FEATURES = BASE_FEATURES + ["relative_dvol_log_ratio"]


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def parse_fred_series(body: bytes, series_id: str) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED {series_id} CSV schema: {reader.fieldnames}")
    date_field = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_field is None:
        raise ValueError(f"FRED {series_id} CSV has no recognized observation-date column")
    values: dict[dt.date, float] = {}
    seen: set[dt.date] = set()
    for row in reader:
        day = base.parse_date(row.get(date_field))
        if day is None:
            continue
        if day in seen:
            raise ValueError(f"Duplicate {series_id} observation date: {day}")
        seen.add(day)
        value = base.parse_float(row.get(series_id))
        if value is None:
            continue
        if value <= 0:
            raise ValueError(f"Non-positive {series_id} observation on {day}")
        values[day] = value
    if not values:
        raise ValueError(f"No valid {series_id} observations")
    return dict(sorted(values.items()))


def utc_midnight_ms(day: dt.date, end_of_day: bool = False) -> int:
    stamp = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
    value = int(stamp.timestamp() * 1000)
    return value + DAY_MS - 1 if end_of_day else value


def parse_dvol_page(body: bytes, currency: str, start_ms: int, end_ms: int) -> tuple[list[dict], int | None]:
    payload = json.loads(body.decode("utf-8"))
    if payload.get("jsonrpc") != "2.0":
        raise ValueError(f"Unexpected Deribit JSON-RPC version for {currency}")
    if payload.get("error"):
        raise ValueError(f"Deribit {currency} API error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ValueError(f"Deribit {currency} response has no candle data array")
    rows = []
    for row_number, row in enumerate(result["data"], start=1):
        if not isinstance(row, list) or len(row) != 5:
            raise ValueError(f"Malformed Deribit {currency} candle row {row_number}")
        try:
            timestamp = int(row[0])
            open_value, high_value, low_value, close_value = [float(value) for value in row[1:]]
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid Deribit {currency} candle row {row_number}") from exc
        values = (open_value, high_value, low_value, close_value)
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError(f"Non-positive or non-finite Deribit {currency} candle value at row {row_number}")
        if timestamp < start_ms or timestamp > end_ms or timestamp % DAY_MS:
            raise ValueError(f"Deribit {currency} candle timestamp outside the requested UTC daily range")
        if low_value > min(open_value, close_value) or high_value < max(open_value, close_value) or low_value > high_value:
            raise ValueError(f"Invalid Deribit {currency} OHLC ordering at row {row_number}")
        day = dt.datetime.fromtimestamp(timestamp / 1000, dt.timezone.utc).date()
        rows.append({
            "date": day,
            "timestamp_ms": timestamp,
            "open": open_value,
            "high": high_value,
            "low": low_value,
            "close": close_value,
        })
    continuation = result.get("continuation")
    if continuation is not None:
        try:
            continuation = int(continuation)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Deribit {currency} continuation cursor") from exc
    return rows, continuation


def fetch_dvol_page(currency: str, start_ms: int, end_ms: int, page_number: int) -> bytes:
    payload = {
        "jsonrpc": "2.0",
        "id": page_number,
        "method": "public/get_volatility_index_data",
        "params": {
            "currency": currency,
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "resolution": "1D",
        },
    }
    request = urllib.request.Request(
        DERIBIT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "User-Agent": "QFR-Research/1.0 (public academic research; github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError(f"HTTP {response.status} or empty Deribit {currency} response")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable Deribit HTTP {exc.code} for {currency}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Deribit {currency} request failed after three bounded attempts: {last_error}")


def fetch_dvol_history(currency: str, start_date: dt.date, end_date: dt.date) -> tuple[dict[dt.date, float], dict]:
    start_ms = utc_midnight_ms(start_date)
    end_ms = utc_midnight_ms(end_date, end_of_day=True)
    cursor_end = end_ms
    seen_cursors: set[int] = set()
    all_rows: dict[dt.date, dict] = {}
    page_meta = []
    for page_number in range(1, MAX_DVOL_PAGES + 1):
        body = fetch_dvol_page(currency, start_ms, cursor_end, page_number)
        rows, continuation = parse_dvol_page(body, currency, start_ms, cursor_end)
        page_meta.append({
            "page": page_number,
            "request_start_timestamp_ms": start_ms,
            "request_end_timestamp_ms": cursor_end,
            "response_sha256": sha256(body),
            "rows": len(rows),
            "first_date": min((row["date"] for row in rows), default=None).isoformat() if rows else None,
            "last_date": max((row["date"] for row in rows), default=None).isoformat() if rows else None,
            "continuation": continuation,
        })
        for row in rows:
            prior = all_rows.get(row["date"])
            if prior is not None and prior != row:
                raise ValueError(f"Conflicting duplicate Deribit {currency} candle for {row['date']}")
            all_rows[row["date"]] = row
        if continuation is None:
            break
        if continuation < start_ms:
            break
        if not rows:
            raise ValueError(f"Deribit {currency} returned an empty page with a continuation cursor")
        if continuation == cursor_end:
            if cursor_end == start_ms:
                break
            raise ValueError(f"Deribit {currency} pagination did not make strict backward progress")
        if continuation > cursor_end or continuation in seen_cursors:
            raise ValueError(f"Deribit {currency} pagination did not make strict backward progress")
        seen_cursors.add(continuation)
        cursor_end = continuation
    else:
        raise ValueError(f"Deribit {currency} history exceeded the {MAX_DVOL_PAGES}-page safety bound")

    ordered = dict(sorted((day, row["close"]) for day, row in all_rows.items()))
    if not ordered:
        raise ValueError(f"No Deribit {currency} DVOL candles returned")
    dates = sorted(ordered)
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    metadata = {
        "url": DERIBIT_URL,
        "currency": currency,
        "resolution": "1D",
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "rows": len(ordered),
        "maximum_calendar_gap_days": max(gaps) if gaps else 0,
        "pages": page_meta,
        "combined_page_sha256": sha256("".join(item["response_sha256"] for item in page_meta).encode("ascii")),
    }
    return ordered, metadata


def normalize_dvol_scale(values: dict[dt.date, float]) -> tuple[dict[dt.date, float], str, float]:
    if not values:
        raise ValueError("Cannot normalize an empty DVOL series")
    median = statistics.median(values.values())
    if 0.01 <= median <= 2.5:
        scale, factor = "decimal_fraction", 100.0
    elif 10.0 <= median <= 250.0:
        scale, factor = "percentage_points", 1.0
    else:
        raise ValueError(f"Ambiguous or unrecognized Deribit DVOL numeric scale: median={median}")
    normalized = {day: value * factor for day, value in values.items()}
    if any(not 1.0 <= value <= 250.0 for value in normalized.values()):
        raise ValueError("Normalized Deribit DVOL contains an implausible value outside 1-250 volatility points")
    return normalized, scale, factor


def validate_source_coverage(
    prices: dict[str, dict[dt.date, float]],
    dvol: dict[str, dict[dt.date, float]],
    as_of: dt.date,
) -> dict:
    coverage = {}
    for series_id, values in prices.items():
        dates = sorted(values)
        if len(values) < MIN_PRICE_ROWS or dates[0] > START_DATE + dt.timedelta(days=7):
            raise ValueError(f"Insufficient or late-starting Coinbase {series_id} history: n={len(values)}, first={dates[0]}")
        if dates[-1] > as_of or (as_of - dates[-1]).days > 3:
            raise ValueError(f"Coinbase {series_id} history is future-dated or stale: {dates[-1]}")
        gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
        if gaps and max(gaps) > 1:
            raise ValueError(f"Coinbase {series_id} has a missing calendar day; max gap={max(gaps)}")
        coverage[series_id] = {
            "rows": len(values),
            "first_date": dates[0].isoformat(),
            "last_date": dates[-1].isoformat(),
            "maximum_calendar_gap_days": max(gaps) if gaps else 0,
        }

    for currency, values in dvol.items():
        dates = sorted(values)
        if len(values) < MIN_DVOL_ROWS or dates[0] > START_DATE + dt.timedelta(days=7):
            raise ValueError(f"Insufficient or late-starting Deribit {currency} DVOL history: n={len(values)}, first={dates[0]}")
        if dates[-1] > as_of or (as_of - dates[-1]).days > 2:
            raise ValueError(f"Deribit {currency} DVOL history is future-dated or stale: {dates[-1]}")
        gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
        if gaps and max(gaps) > MAX_DVOL_AGE_DAYS:
            raise ValueError(f"Deribit {currency} DVOL history has an excessive daily gap: {max(gaps)}")
        coverage[f"{currency}_DVOL"] = {
            "rows": len(values),
            "first_date": dates[0].isoformat(),
            "last_date": dates[-1].isoformat(),
            "maximum_calendar_gap_days": max(gaps) if gaps else 0,
        }

    common_prices = sorted(set(prices["CBBTCUSD"]) & set(prices["CBETHUSD"]))
    common_dvol = sorted(set(dvol["BTC"]) & set(dvol["ETH"]))
    if len(common_prices) < MIN_PRICE_ROWS or len(common_dvol) < MIN_DVOL_ROWS:
        raise ValueError("Insufficient common BTC/ETH price or DVOL dates")
    if any((right - left).days != 1 for left, right in zip(common_prices, common_prices[1:])):
        raise ValueError("Common Coinbase BTC/ETH prices are not consecutive daily observations")
    if any((right - left).days > MAX_DVOL_AGE_DAYS for left, right in zip(common_dvol, common_dvol[1:])):
        raise ValueError("Common BTC/ETH DVOL observations contain a gap exceeding two calendar days")
    coverage["COMMON"] = {
        "price_rows": len(common_prices),
        "price_first_date": common_prices[0].isoformat(),
        "price_last_date": common_prices[-1].isoformat(),
        "dvol_rows": len(common_dvol),
        "dvol_first_date": common_dvol[0].isoformat(),
        "dvol_last_date": common_dvol[-1].isoformat(),
    }
    return coverage


def daily_log_returns(prices: dict[dt.date, float], dates: list[dt.date]) -> list[float | None]:
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
            continue
        value = math.log(prices[dates[index]] / prices[dates[index - 1]])
        returns.append(value if math.isfinite(value) else None)
    return returns


def realized_volatility(returns: list[float | None]) -> float:
    if not returns or any(value is None or not math.isfinite(float(value)) for value in returns):
        raise ValueError("Realized-volatility window contains a missing or invalid return")
    variance = sum(float(value) ** 2 for value in returns) * 365.0 / len(returns)
    result = math.sqrt(variance) * 100.0
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Realized volatility must be finite and positive")
    return result


def build_events(
    btc_prices: dict[dt.date, float],
    eth_prices: dict[dt.date, float],
    btc_dvol: dict[dt.date, float],
    eth_dvol: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    price_dates = sorted(set(btc_prices) & set(eth_prices))
    dvol_dates = sorted(set(btc_dvol) & set(eth_dvol))
    if not price_dates or not dvol_dates:
        raise ValueError("No common BTC/ETH price or DVOL dates")
    if any((right - left).days != 1 for left, right in zip(price_dates, price_dates[1:])):
        raise ValueError("Common BTC/ETH price dates contain a calendar gap; returns will not be bridged")
    btc_returns = daily_log_returns(btc_prices, price_dates)
    eth_returns = daily_log_returns(eth_prices, price_dates)
    events = []
    skipped = {
        "incomplete_prior_returns": 0,
        "incomplete_future_returns": 0,
        "no_strictly_prior_common_dvol": 0,
        "stale_common_dvol": 0,
        "nonpositive_realized_volatility": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0
    for signal_index in range(30, len(price_dates) - TARGET_SESSIONS, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_date = price_dates[signal_index]
        pre_btc_7 = btc_returns[signal_index - 6:signal_index + 1]
        pre_eth_7 = eth_returns[signal_index - 6:signal_index + 1]
        pre_btc_30 = btc_returns[signal_index - 29:signal_index + 1]
        pre_eth_30 = eth_returns[signal_index - 29:signal_index + 1]
        future_btc = btc_returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1]
        future_eth = eth_returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1]
        if any(value is None for value in pre_btc_7 + pre_eth_7 + pre_btc_30 + pre_eth_30):
            skipped["incomplete_prior_returns"] += 1
            continue
        if any(value is None for value in future_btc + future_eth):
            skipped["incomplete_future_returns"] += 1
            continue

        dvol_index = bisect.bisect_left(dvol_dates, signal_date) - 1
        if dvol_index < 0:
            skipped["no_strictly_prior_common_dvol"] += 1
            continue
        dvol_date = dvol_dates[dvol_index]
        if dvol_date >= signal_date:
            raise ValueError(f"Same-date or future DVOL observation leaked into signal {signal_date}")
        if (signal_date - dvol_date).days > MAX_DVOL_AGE_DAYS:
            skipped["stale_common_dvol"] += 1
            continue

        try:
            pre_btc_rv7 = realized_volatility(pre_btc_7)
            pre_eth_rv7 = realized_volatility(pre_eth_7)
            pre_btc_rv30 = realized_volatility(pre_btc_30)
            pre_eth_rv30 = realized_volatility(pre_eth_30)
            future_btc_rv = realized_volatility(future_btc)
            future_eth_rv = realized_volatility(future_eth)
        except ValueError:
            skipped["nonpositive_realized_volatility"] += 1
            continue
        relative_dvol = math.log(eth_dvol[dvol_date] / btc_dvol[dvol_date])
        target = math.log(future_eth_rv / future_btc_rv)
        event = {
            "signal_date": signal_date,
            "dvol_observation_date": dvol_date,
            "target_start_date": price_dates[signal_index + 1],
            "target_end_date": price_dates[signal_index + TARGET_SESSIONS],
            "pre_btc_rv7_log": math.log(pre_btc_rv7),
            "pre_btc_rv30_log": math.log(pre_btc_rv30),
            "pre_eth_rv7_log": math.log(pre_eth_rv7),
            "pre_eth_rv30_log": math.log(pre_eth_rv30),
            "relative_dvol_log_ratio": relative_dvol,
            "target_log_relative_rv": target,
            "pre_btc_rv7_pct": pre_btc_rv7,
            "pre_eth_rv7_pct": pre_eth_rv7,
            "future_btc_rv_pct": future_btc_rv,
            "future_eth_rv_pct": future_eth_rv,
        }
        if event["target_end_date"] <= signal_date:
            raise ValueError(f"Invalid target dates for signal {signal_date}")
        if events and event["target_start_date"] <= events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        events.append(event)

    return events, {
        "candidate_origins": candidates,
        "events": len(events),
        "skipped": skipped,
        "event_spacing_price_observations": EVENT_STEP_SESSIONS,
        "target_price_observations": TARGET_SESSIONS,
        "rolling_training_events": MODEL_WINDOW,
        "signal_rule": "Coinbase daily close on t; use the latest common BTC/ETH Deribit daily DVOL candle with candle date strictly earlier than t",
        "target_rule": "log of next-seven-observation annualized ETH realized volatility divided by BTC realized volatility",
        "target_maturity_rule": "a training target_end_date must be strictly earlier than the current signal_date; the immediately preceding seven-day target ends on the current signal date and is therefore excluded from training",
    }


def fit_target_predict(train: list[dict], current: dict, feature_names: list[str], target_key: str) -> float:
    # The shared repository OLS helper uses the legacy target_bp key.
    # Adapt only the training target locally; the relative-RV target remains
    # explicitly named in this experiment's event and evidence schemas.
    adapted_train = [{**row, "target_bp": row[target_key]} for row in train]
    return base.fit_ols_predict(adapted_train, current, feature_names)


def walk_forward_predictions(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = [
            row for row in events
            if row["signal_date"] < current["signal_date"]
            and row["target_end_date"] < current["signal_date"]
        ][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = fit_target_predict(train, current, BASE_FEATURES, "target_log_relative_rv")
            augmented = fit_target_predict(train, current, AUGMENTED_FEATURES, "target_log_relative_rv")
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_log_relative_rv": current["target_log_relative_rv"],
            "baseline_prediction": baseline,
            "augmented_prediction": augmented,
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict], prediction_key: str) -> dict:
    if not rows:
        return {"n": 0, "rmse_log_relative_rv": None, "mae_log_relative_rv": None, "oos_r2_vs_period_mean": None}
    errors = [row[prediction_key] - row["target_log_relative_rv"] for row in rows]
    actual = [row["target_log_relative_rv"] for row in rows]
    mean_actual = statistics.fmean(actual)
    sse = sum(error * error for error in errors)
    denominator = sum((value - mean_actual) ** 2 for value in actual)
    return {
        "n": len(rows),
        "rmse_log_relative_rv": math.sqrt(sse / len(errors)),
        "mae_log_relative_rv": statistics.fmean(abs(error) for error in errors),
        "oos_r2_vs_period_mean": 1.0 - sse / denominator if denominator > 1e-12 else None,
    }


def improvement_pct(baseline: dict, augmented: dict) -> float | None:
    base_rmse = baseline.get("rmse_log_relative_rv")
    aug_rmse = augmented.get("rmse_log_relative_rv")
    if not isinstance(base_rmse, (int, float)) or not isinstance(aug_rmse, (int, float)) or base_rmse <= 0:
        return None
    return 100.0 * (base_rmse - aug_rmse) / base_rmse


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    differences = []
    for row in rows:
        target = row["target_log_relative_rv"]
        difference = (row["baseline_prediction"] - target) ** 2 - (row["augmented_prediction"] - target) ** 2
        if not math.isfinite(difference):
            return None
        differences.append({"difference": difference})
    observed = statistics.fmean(row["difference"] for row in differences)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(differences, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["difference"] for row in sample))
    samples.sort()
    return {
        "observations": len(differences),
        "reps": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "mean_baseline_minus_augmented_squared_loss": observed,
        "ci95_low": samples[int(0.025 * (len(samples) - 1))],
        "ci95_high": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline", {}), validation.get("augmented", {}))
    test_imp = improvement_pct(test.get("baseline", {}), test.get("augmented", {}))
    enough = validation.get("n", 0) >= 30 and test.get("n", 0) >= 30 and paired is not None
    if (
        enough and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired.get("ci95_low") is not None and paired["ci95_low"] > 0
    ):
        return "BACKTESTED", "PROMISING FORECAST SCREEN — the relative-DVOL augmentation improves both chronological periods and paired test-loss inference favors it; independent reconstruction and a separate tradable study remain required"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and paired is not None and paired.get("ci95_high") is not None
        and paired["ci95_high"] < 0
    ):
        return "REJECTED", "REJECTED — neither chronological period improves and paired test-loss inference favors the baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — the frozen chronological and paired-loss criteria do not establish incremental predictive value or decisive inferiority"


def run_research() -> dict:
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    source_meta = {}
    prices = {}
    for series_id in PRICE_SERIES:
        url = f"{FRED_URL}?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url, timeout=30)
        prices[series_id] = parse_fred_series(body, series_id)
        source_meta[series_id] = {
            "url": url,
            "sha256": sha256(body),
            "rows": len(prices[series_id]),
            "first_date": min(prices[series_id]).isoformat(),
            "last_date": max(prices[series_id]).isoformat(),
            "copyright_notice": "Coinbase observations as of 5 PM Pacific; raw observations are not redistributed",
        }

    dvol = {}
    dvol_meta = {}
    scale_labels = set()
    for currency in CURRENCIES:
        raw, metadata = fetch_dvol_history(currency, START_DATE, NOW.date() - dt.timedelta(days=1))
        normalized, scale, factor = normalize_dvol_scale(raw)
        dvol[currency] = normalized
        scale_labels.add(scale)
        metadata["raw_numeric_scale"] = scale
        metadata["normalization_factor_to_volatility_points"] = factor
        metadata["raw_sha256"] = metadata["combined_page_sha256"]
        dvol_meta[currency] = metadata
    if len(scale_labels) != 1:
        raise ValueError(f"BTC and ETH DVOL endpoints returned inconsistent numeric scales: {sorted(scale_labels)}")

    coverage = validate_source_coverage(prices, dvol, NOW.date())
    events, event_meta = build_events(prices["CBBTCUSD"], prices["CBETHUSD"], dvol["BTC"], dvol["ETH"])
    predictions = walk_forward_predictions(events)
    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    if len(validation) < 30 or len(test) < 30:
        raise ValueError(
            f"Insufficient frozen chronological samples: validation={len(validation)}, test={len(test)}, "
            f"events={len(events)}, coverage={coverage}"
        )

    validation_metrics = {
        "n": len(validation),
        "baseline": forecast_metrics(validation, "baseline_prediction"),
        "augmented": forecast_metrics(validation, "augmented_prediction"),
    }
    test_metrics = {
        "n": len(test),
        "baseline": forecast_metrics(test, "baseline_prediction"),
        "augmented": forecast_metrics(test, "augmented_prediction"),
    }
    paired = paired_loss_bootstrap(test)
    status, disposition = decide(validation_metrics, test_metrics, paired)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": retrieved_at,
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "source_meta": source_meta,
        "dvol_meta": dvol_meta,
        "coverage": coverage,
        "event_meta": event_meta,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "paired_loss_bootstrap": paired,
        "validation_improvement_pct": improvement_pct(validation_metrics["baseline"], validation_metrics["augmented"]),
        "test_improvement_pct": improvement_pct(test_metrics["baseline"], test_metrics["augmented"]),
    }


def update_documents(result: dict, report_relative: str, manifest_relative: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = str(result.get("disposition", "INCONCLUSIVE/INFEASIBLE — no empirical result established")).replace("|", "/")
    coverage = result.get("coverage") or {}
    common = coverage.get("COMMON") or {}
    validation = result.get("validation_metrics") or {}
    test = result.get("test_metrics") or {}
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Latest strictly prior log(ETH DVOL / BTC DVOL) adds information about the next-seven-observation log ratio of annualized ETH/BTC realized volatility beyond each asset's own trailing 7/30-day realized volatility. | "
        f"Deribit BTC/ETH DVOL and Coinbase CBBTCUSD/CBETHUSD; common price rows={common.get('price_rows', 'not established')}; common DVOL rows={common.get('dvol_rows', 'not established')}; "
        f"price={common.get('price_first_date', 'unknown')} to {common.get('price_last_date', 'unknown')}; DVOL={common.get('dvol_first_date', 'unknown')} to {common.get('dvol_last_date', 'unknown')} | "
        f"{disposition}; validation/test n={validation.get('n', 'not computed')}/{test.get('n', 'not computed')}; RMSE improvement={result.get('validation_improvement_pct')}/{result.get('test_improvement_pct')}% | "
        f"[session report](../{report_relative}) / [manifest](../{manifest_relative}) / [preregistration](PREREGISTERED-QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01.md) |"
    )
    lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    prefix = f"| {HYPOTHESIS_ID} |"
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) > 1:
        raise ValueError(f"Duplicate registry rows for {HYPOTHESIS_ID}")
    if matches:
        lines[matches[0]] = row
    else:
        marker = "## Disposition rules"
        if marker not in lines:
            raise ValueError("Hypothesis registry disposition marker missing")
        lines.insert(lines.index(marker), row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    prereg = PREREG_PATH.read_text(encoding="utf-8")
    marker = "## Empirical disposition"
    if marker in prereg:
        prereg = prereg.split(marker, 1)[0].rstrip()
    paired = result.get("paired_loss_bootstrap")
    section = (
        f"\n\n{marker}\n\n"
        f"- **Status:** {status}\n"
        f"- **Disposition:** {disposition}\n"
        f"- **Completed real-data backtest:** {result.get('completed_backtest', False)}\n"
        f"- **Run:** {RUN_ID}, attempt {RUN_ATTEMPT}; source commit {SOURCE_SHA}\n"
        f"- **Data coverage:** {json.dumps(coverage, sort_keys=True)}\n"
        f"- **Validation metrics:** {json.dumps(validation, sort_keys=True)}\n"
        f"- **Test metrics:** {json.dumps(test, sort_keys=True)}\n"
        f"- **RMSE improvement:** validation={result.get('validation_improvement_pct')}; test={result.get('test_improvement_pct')}\n"
        f"- **Paired test-loss bootstrap:** {json.dumps(paired, sort_keys=True) if paired else 'NOT COMPUTED'}\n"
        f"- **Report:** [{report_relative}](../{report_relative})\n"
        f"- **Manifest:** [{manifest_relative}](../{manifest_relative})\n"
    )
    if result.get("error"):
        section += f"- **Execution blocker:** {result['error']}\n"
    PREREG_PATH.write_text(prereg.rstrip() + section, encoding="utf-8")


def write_outputs(result: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    report_relative = REPORT_PATH.relative_to(ROOT).as_posix()
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_relative = manifest_path.relative_to(ROOT).as_posix()
    manifest = {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result.get("status", "INCONCLUSIVE"),
        "disposition": result.get("disposition"),
        "completed_backtest": result.get("completed_backtest", False),
        "retrieved_at_utc": result.get("retrieved_at_utc", dt.datetime.now(dt.timezone.utc).isoformat()),
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "price_sources": result.get("source_meta", {}),
        "dvol_sources": result.get("dvol_meta", {}),
        "coverage": result.get("coverage", {}),
        "event_construction": result.get("event_meta", {}),
        "methodology": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUGMENTED_FEATURES,
            "signal": "Coinbase daily close on t; latest common Deribit BTC/ETH 1D DVOL candle whose UTC date is strictly earlier than t",
            "relative_dvol_feature": "log(ETH_DVOL[d] / BTC_DVOL[d]) using the same strictly prior common DVOL date",
            "target": "log(annualized next-seven-observation ETH realized volatility / BTC realized volatility)",
            "event_spacing": EVENT_STEP_SESSIONS,
            "target_observations": TARGET_SESSIONS,
            "training_window": MODEL_WINDOW,
            "training_maturity": "target_end_date must be strictly earlier than the current signal_date",
            "validation": f"{VALIDATION_START.isoformat()} through 2024-12-31",
            "test": f"{TEST_START.isoformat()} onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "validation_metrics": result.get("validation_metrics"),
        "test_metrics": result.get("test_metrics"),
        "rmse_improvement_pct": {
            "validation": result.get("validation_improvement_pct"),
            "test": result.get("test_improvement_pct"),
        },
        "paired_loss_bootstrap": result.get("paired_loss_bootstrap"),
        "error": result.get("error"),
        "limitations": [
            "Deribit DVOL is a 30-day forward implied-volatility index; the target is seven-day realized volatility, so the horizon mismatch is deliberate and must not be hidden.",
            "Deribit represents one options venue; the index is not a consolidated global options surface.",
            "Coinbase CBBTCUSD and CBETHUSD are daily closes as of 5 PM Pacific and are copyrighted; raw observations are not committed or redistributed.",
            "The signal uses only the latest common Deribit daily candle dated strictly before the Coinbase signal date; this conservative date embargo may lag the options close.",
            "Current-vintage FRED observations are used; historical point-in-time revisions are not reconstructed.",
            "Daily close-to-close realized volatility does not capture intraday jumps or microstructure effects.",
            "Forecast-only: no directional-return claim, causal claim, executable strategy P&L, transaction-cost model or live deployment.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if result.get("completed_backtest"):
        validation = result["validation_metrics"]
        test = result["test_metrics"]
        report = f"""# Deribit relative DVOL / ETH-BTC realized-volatility session — {STAMP}

## Research result

**Hypothesis:** {HYPOTHESIS_ID}

**Disposition:** {result['status']} — {result['disposition']}.

The test asks whether the strictly prior common-date log ratio of ETH DVOL to BTC DVOL adds chronological out-of-sample information about the next seven daily observations' relative realized volatility, beyond each asset's own trailing realized volatility.

### Data coverage

| Source | First | Last | Rows |
|---|---|---|---:|
| Coinbase BTCUSD | {result['coverage']['CBBTCUSD']['first_date']} | {result['coverage']['CBBTCUSD']['last_date']} | {result['coverage']['CBBTCUSD']['rows']} |
| Coinbase ETHUSD | {result['coverage']['CBETHUSD']['first_date']} | {result['coverage']['CBETHUSD']['last_date']} | {result['coverage']['CBETHUSD']['rows']} |
| Deribit BTC DVOL | {result['coverage']['BTC_DVOL']['first_date']} | {result['coverage']['BTC_DVOL']['last_date']} | {result['coverage']['BTC_DVOL']['rows']} |
| Deribit ETH DVOL | {result['coverage']['ETH_DVOL']['first_date']} | {result['coverage']['ETH_DVOL']['last_date']} | {result['coverage']['ETH_DVOL']['rows']} |

Common aligned sample: {json.dumps(result['coverage']['COMMON'], sort_keys=True)}.

### Event and forecast construction

- Accepted events: {result['event_meta']['events']} of {result['event_meta']['candidate_origins']} candidates.
- Skipped events: {json.dumps(result['event_meta']['skipped'], sort_keys=True)}.
- Signal: Coinbase close on t; latest common Deribit daily candle date strictly earlier than t.
- Target: log of next-seven-observation annualized ETH realized volatility divided by BTC realized volatility.
- Event spacing: seven observations; target windows do not overlap.
- Training: 52 prior events whose target end is strictly earlier than the current signal.
- Validation: 2024-04-01 through 2024-12-31; test: 2025-01-01 onward.

### Forecast results

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | {validation['n']} | {test['n']} |
| Baseline RMSE | {validation['baseline']['rmse_log_relative_rv']:.6f} | {test['baseline']['rmse_log_relative_rv']:.6f} |
| Augmented RMSE | {validation['augmented']['rmse_log_relative_rv']:.6f} | {test['augmented']['rmse_log_relative_rv']:.6f} |
| RMSE improvement | {result['validation_improvement_pct']:.4f}% | {result['test_improvement_pct']:.4f}% |
| Baseline MAE | {validation['baseline']['mae_log_relative_rv']:.6f} | {test['baseline']['mae_log_relative_rv']:.6f} |
| Augmented MAE | {validation['augmented']['mae_log_relative_rv']:.6f} | {test['augmented']['mae_log_relative_rv']:.6f} |

Paired test squared-loss bootstrap: {json.dumps(result['paired_loss_bootstrap'], sort_keys=True)}.

## Literature boundary

- Chevallier and Sanhaji (2023), “Jump-Robust Realized-GARCH-MIDAS-X Estimators for Bitcoin and Ethereum Volatility Indices,” Stats 6(4), 1339–1370, DOI https://doi.org/10.3390/stats6040082. Their study finds that 30-day implied-volatility indices can improve separate BTC and ETH realized-volatility forecasts. This study does not claim that result is new; it tests a relative ETH/BTC DVOL feature against a joint cross-asset baseline.
- Hoang and Baur (2020), “Forecasting bitcoin volatility: evidence from the options market,” Journal of Futures Markets 40(10), 1584–1602, DOI https://doi.org/10.1002/fut.22144. Their results distinguish short and longer forecasting horizons and find that implied volatility is more useful at longer horizons; this motivates explicit horizon reporting.
- Deribit documents the public daily-candle endpoint and its 1D resolution at https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data. The DVOL index measures 30-day annualized implied volatility; it is not a directional signal.

## Reproducibility

- FRED and Deribit URLs, source hashes, exact coverage, row counts, page cursors and numeric-scale normalization are recorded in the manifest.
- Raw Coinbase observations and raw Deribit response bodies are not committed.
- Deterministic parser, pagination, timestamp, missingness, non-overlap, maturity and decision-rule tests ran before data retrieval.

## Verified / unverified

**VERIFIED:** source retrieval, response hashes, daily candle parsing, source coverage, strict prior-date alignment, complete daily price windows, non-overlapping target returns, matured walk-forward training, chronological metrics and paired block-bootstrap under this data/code vintage.

**UNVERIFIED:** historical point-in-time revisions; generalization beyond the observed Deribit/Coinbase sample; causal interpretation; relative-volatility hedge or portfolio performance; executable fees, spreads, liquidity, funding and slippage.

## Disposition boundary

This is a forecast-only screen, not an ETH/BTC trading strategy. No CAGR, Sharpe, Sortino, Calmar, drawdown or live-trading claim is warranted. A promising result requires independent reconstruction and a separately preregistered tradable strategy study.
"""
    else:
        report = f"""# Deribit relative DVOL / ETH-BTC session — {STAMP}

## Status

**INCONCLUSIVE/INFEASIBLE.** No complete real-data backtest was established.

- Hypothesis: {HYPOTHESIS_ID}
- Run: {RUN_ID}, attempt {RUN_ATTEMPT}
- Source commit: {SOURCE_SHA}
- Error: {result.get('error', 'No detailed error supplied')}
- No forecast metrics or empirical performance conclusion are claimed.

The failure is a source/implementation/execution feasibility result only. It is not evidence that the relative-DVOL hypothesis is profitable, unprofitable or rejected.

## Required next action

Diagnose the exact error, change the failed invocation or source route materially, and continue only within the frozen timebox. Do not extend the clock or weaken coverage, timing, sample-size or decision gates.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    update_documents(result, report_relative, manifest_relative)
    return REPORT_PATH, manifest_path


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE/INFEASIBLE — bounded source or execution failure: {type(exc).__name__}: {exc}",
            "completed_backtest": False,
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "error": f"{type(exc).__name__}: {exc}",
        }
    report_path, manifest_path = write_outputs(result)
    print(f"REPORT={report_path.relative_to(ROOT)}")
    print(f"MANIFEST={manifest_path.relative_to(ROOT)}")
    print(json.dumps(result, indent=2, default=str, sort_keys=True))
    return 0 if result.get("completed_backtest") else 1


if __name__ == "__main__":
    raise SystemExit(main())
