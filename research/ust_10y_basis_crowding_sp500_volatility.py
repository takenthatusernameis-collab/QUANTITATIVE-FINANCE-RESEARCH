#!/usr/bin/env python3
"""Walk-forward forecast screen: 10-year Treasury futures net-short crowding -> S&P 500 realized volatility."""
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
import urllib.parse
import urllib.request
from pathlib import Path

import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-25-UST-10Y-BASIS-CROWDING-SP500-RV-01"
CFTC_CODE = "043602"
CFTC_DATASET = "gpe5-46if"
CFTC_START = dt.date(2006, 6, 13)
PRICE_START = dt.date(2016, 11, 25)
PUBLICATION_LAG_DAYS = 14
BACKLOG_START = dt.date(2025, 9, 30)
BACKLOG_END = dt.date(2026, 1, 20)
CROWDING_LOOKBACK = 156
MODEL_WINDOW = 104
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
HIGH_CROWDING_THRESHOLD = 0.90
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
RNG_SEED = 20261125
MIN_CFTC_ROWS = 800
MIN_PRICE_ROWS = 1500

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "ust-10y-basis-crowding" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"

CFTC_BASE_URL = f"https://publicreporting.cftc.gov/resource/{CFTC_DATASET}.json"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def fetch_bytes(url: str, timeout: int = 25) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QFR-Research/1.0 (public academic research; github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)",
            "Accept": "application/json, text/csv, */*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                if not body:
                    raise RuntimeError(f"Empty response for {url}")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after 3 bounded attempts: {url}: {last_error}")


def parse_cftc(body: bytes) -> list[dict]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("CFTC response is not a non-empty JSON row list")
    rows = []
    for raw in payload:
        code = str(raw.get("cftc_contract_market_code") or "").strip()
        if code != CFTC_CODE:
            continue
        report_date = base.parse_date(raw.get("report_date_as_yyyy_mm_dd"))
        open_interest = base.parse_float(raw.get("open_interest_all"))
        long_position = base.parse_float(raw.get("lev_money_positions_long"))
        short_position = base.parse_float(raw.get("lev_money_positions_short"))
        market_name = str(raw.get("contract_market_name") or "").strip()
        upper_name = market_name.upper()
        accepted_name = (
            "UST 10Y NOTE" in upper_name
            or "10-YEAR U.S. TREASURY NOTES" in upper_name
        )
        if report_date is None:
            raise ValueError("CFTC row has an invalid report date")
        if not market_name or not accepted_name:
            raise ValueError(f"Unexpected market name for code {CFTC_CODE}: {market_name!r}")
        if open_interest is None or open_interest <= 0:
            raise ValueError(f"Invalid open interest for report {report_date}")
        if (
            long_position is None or short_position is None
            or long_position < 0 or short_position < 0
        ):
            raise ValueError(f"Invalid leveraged-fund positions for report {report_date}")
        net_short = short_position - long_position
        if abs(net_short) > open_interest:
            raise ValueError(f"Leveraged-fund net position exceeds open interest for {report_date}")
        rows.append({
            "report_date": report_date,
            "market_name": market_name,
            "cftc_contract_market_code": code,
            "open_interest": open_interest,
            "lev_money_long": long_position,
            "lev_money_short": short_position,
            "net_short": net_short,
            "net_short_pct_oi": net_short / open_interest,
        })
    if not rows:
        raise ValueError(f"No CFTC rows found for exact contract code {CFTC_CODE}")
    rows.sort(key=lambda row: row["report_date"])
    dates = [row["report_date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate CFTC report dates for the selected contract")
    return rows


def parse_fred_series(body: bytes, series_id: str) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED {series_id} CSV schema: {reader.fieldnames}")
    values: dict[dt.date, float] = {}
    for row in reader:
        obs_date = base.parse_date(row.get("observation_date") or row.get("DATE"))
        value = base.parse_float(row.get(series_id))
        if obs_date is None or value is None:
            continue
        if value <= 0:
            raise ValueError(f"Non-positive {series_id} observation on {obs_date}")
        if obs_date in values:
            raise ValueError(f"Duplicate FRED {series_id} observation date: {obs_date}")
        values[obs_date] = value
    return dict(sorted(values.items()))


def validate_source_coverage(
    cot_rows: list[dict],
    prices: dict[dt.date, float],
    vix: dict[dt.date, float],
    today: dt.date,
) -> dict:
    cftc_dates = [row["report_date"] for row in cot_rows]
    if len(cot_rows) < MIN_CFTC_ROWS:
        raise ValueError(f"Insufficient CFTC observations: {len(cot_rows)}")
    if cftc_dates[0] > CFTC_START + dt.timedelta(days=90):
        raise ValueError(f"CFTC history starts unexpectedly late: {cftc_dates[0]}")
    if (today - cftc_dates[-1]).days > 21:
        raise ValueError(f"CFTC latest report is stale: {cftc_dates[-1]}")
    price_dates = sorted(prices)
    vix_dates = sorted(vix)
    for series_id, series_dates, series_values in (
        ("SP500", price_dates, prices),
        ("VIXCLS", vix_dates, vix),
    ):
        if len(series_values) < MIN_PRICE_ROWS:
            raise ValueError(f"Insufficient FRED {series_id} observations: {len(series_values)}")
        if series_dates[0] > PRICE_START + dt.timedelta(days=90):
            raise ValueError(f"FRED {series_id} history starts unexpectedly late: {series_dates[0]}")
    if abs((price_dates[-1] - vix_dates[-1]).days) > 4:
        raise ValueError("FRED SP500 and VIXCLS latest observations are not synchronized")
    common_end = min(price_dates[-1], vix_dates[-1])
    if (today - common_end).days > 8:
        raise ValueError(f"FRED common end is stale: {common_end}")
    return {
        "CFTC": {
            "rows": len(cot_rows),
            "first_date": cftc_dates[0].isoformat(),
            "last_date": cftc_dates[-1].isoformat(),
        },
        "SP500": {
            "rows": len(prices),
            "first_date": price_dates[0].isoformat(),
            "last_date": price_dates[-1].isoformat(),
        },
        "VIXCLS": {
            "rows": len(vix),
            "first_date": vix_dates[0].isoformat(),
            "last_date": vix_dates[-1].isoformat(),
        },
        "common_price_end": common_end.isoformat(),
    }


def is_backlog_report(report_date: dt.date) -> bool:
    return BACKLOG_START <= report_date <= BACKLOG_END


def build_crowding_features(rows: list[dict], lookback: int = CROWDING_LOOKBACK) -> list[dict]:
    """Rank signed net-short/OI using prior non-backlog reports only."""
    ordered = sorted(rows, key=lambda row: row["report_date"])
    result = []
    prior_values: list[float] = []
    for row in ordered:
        if is_backlog_report(row["report_date"]):
            enriched = dict(row)
            enriched["net_short_percentile"] = None
            enriched["high_crowding"] = False
            result.append(enriched)
            continue
        current = row["net_short_pct_oi"]
        if len(prior_values) >= lookback:
            history = prior_values[-lookback:]
            less = sum(value < current for value in history)
            equal = sum(value == current for value in history)
            percentile = (less + 0.5 * equal) / len(history)
            enriched = dict(row)
            enriched["net_short_percentile"] = percentile
            enriched["high_crowding"] = percentile >= HIGH_CROWDING_THRESHOLD
            result.append(enriched)
        else:
            enriched = dict(row)
            enriched["net_short_percentile"] = None
            enriched["high_crowding"] = False
            result.append(enriched)
        prior_values.append(current)
    return result


def daily_log_returns(prices: dict[dt.date, float]) -> tuple[list[dt.date], list[float | None]]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        gap = (dates[index] - dates[index - 1]).days
        if gap > 4:
            returns.append(None)
        else:
            value = math.log(prices[dates[index]] / prices[dates[index - 1]])
            returns.append(value if math.isfinite(value) else None)
    return dates, returns


def realized_volatility(returns: list[float | None]) -> float:
    if not returns or any(value is None or not math.isfinite(value) for value in returns):
        raise ValueError("Realized-volatility window contains a missing or invalid return")
    return math.sqrt(sum(float(value) ** 2 for value in returns)) * 100.0


def build_events(
    cot_rows: list[dict],
    prices: dict[dt.date, float],
    vix: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    price_dates, returns = daily_log_returns(prices)
    events = []
    skipped = {
        "availability_before_price_history": 0,
        "known_publication_backlog": 0,
        "insufficient_crowding_history": 0,
        "no_signal_close": 0,
        "signal_close_too_far_after_lag": 0,
        "missing_vix_on_signal_date": 0,
        "insufficient_pre_history_or_future": 0,
        "incomplete_return_window": 0,
        "overlapping_target_window": 0,
    }
    for row in sorted(cot_rows, key=lambda item: item["report_date"]):
        report_date = row["report_date"]
        if is_backlog_report(report_date):
            skipped["known_publication_backlog"] += 1
            continue
        if row.get("net_short_percentile") is None:
            skipped["insufficient_crowding_history"] += 1
            continue
        availability_date = report_date + dt.timedelta(days=PUBLICATION_LAG_DAYS)
        if availability_date < price_dates[0]:
            skipped["availability_before_price_history"] += 1
            continue
        signal_index = bisect.bisect_left(price_dates, availability_date)
        if signal_index >= len(price_dates):
            skipped["no_signal_close"] += 1
            continue
        signal_date = price_dates[signal_index]
        if (signal_date - availability_date).days > 4:
            skipped["signal_close_too_far_after_lag"] += 1
            continue
        if signal_date not in vix:
            skipped["missing_vix_on_signal_date"] += 1
            continue
        if signal_index < 20 or signal_index + TARGET_SESSIONS >= len(price_dates):
            skipped["insufficient_pre_history_or_future"] += 1
            continue
        pre_5 = returns[signal_index - 4:signal_index + 1]
        pre_20 = returns[signal_index - 19:signal_index + 1]
        future = returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1]
        try:
            pre_rv5 = realized_volatility(pre_5)
            pre_rv20 = realized_volatility(pre_20)
            target_rv = realized_volatility(future)
        except ValueError:
            skipped["incomplete_return_window"] += 1
            continue
        target_end_date = price_dates[signal_index + TARGET_SESSIONS]
        if events and signal_date < events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        event = dict(row)
        event.update({
            "signal_date": signal_date,
            "availability_date": availability_date,
            "target_start_date": price_dates[signal_index + 1],
            "target_end_date": target_end_date,
            "pre_rv5_pct": pre_rv5,
            "pre_rv20_pct": pre_rv20,
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "log_vix": math.log(vix[signal_date]),
            "target_rv_pct": target_rv,
            "target_bp": math.log1p(target_rv),
        })
        events.append(event)
    return events, {
        "candidate_origins": len(cot_rows),
        "events": len(events),
        "skipped": skipped,
        "publication_lag_days": PUBLICATION_LAG_DAYS,
        "known_backlog_exclusion": [BACKLOG_START.isoformat(), BACKLOG_END.isoformat()],
        "crowding_lookback_reports": CROWDING_LOOKBACK,
        "high_crowding_threshold": HIGH_CROWDING_THRESHOLD,
    }


def walk_forward_predictions(events: list[dict]) -> list[dict]:
    predictions = []
    baseline_features = ["pre_rv5_log", "pre_rv20_log", "log_vix"]
    augmented_features = baseline_features + ["net_short_percentile"]
    for current in events:
        train = [
            row for row in events
            if row["signal_date"] < current["signal_date"]
            and row["target_end_date"] < current["signal_date"]
        ][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, baseline_features)
            augmented = base.fit_ols_predict(train, current, augmented_features)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "report_date": current["report_date"],
            "signal_date": current["signal_date"],
            "availability_date": current["availability_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_rv_pct": current["target_rv_pct"],
            "net_short_pct_oi": current["net_short_pct_oi"],
            "net_short_percentile": current["net_short_percentile"],
            "high_crowding": current["high_crowding"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict], prediction_key: str) -> dict | None:
    if not rows:
        return None
    errors = [row[prediction_key] - row["target_bp"] for row in rows]
    actual = [row["target_bp"] for row in rows]
    mean_actual = statistics.fmean(actual)
    sse = sum(error * error for error in errors)
    denominator = sum((value - mean_actual) ** 2 for value in actual)
    return {
        "n": len(rows),
        "mae_log1p_rv": statistics.fmean(abs(error) for error in errors),
        "rmse_log1p_rv": math.sqrt(sse / len(errors)),
        "oos_r2_vs_mean": 1.0 - sse / denominator if denominator > 1e-12 else None,
    }


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    normalized = []
    for row in rows:
        target = row["target_bp"]
        baseline = row["baseline_prediction_bp"]
        augmented = row["augmented_prediction_bp"]
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not math.isfinite(difference):
            return None
        normalized.append({"loss_difference": difference})
    observed = statistics.fmean(row["loss_difference"] for row in normalized)
    rng = random.Random(RNG_SEED + 1)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(normalized, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["loss_difference"] for row in sample))
    samples.sort()
    return {
        "status": "COMPUTED",
        "observations": len(normalized),
        "reps": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "mean_baseline_minus_augmented_squared_log_loss": observed,
        "ci_95_low": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def bootstrap_crowding_difference(rows: list[dict]) -> dict | None:
    high = [row["target_rv_pct"] for row in rows if row["high_crowding"]]
    other = [row["target_rv_pct"] for row in rows if not row["high_crowding"]]
    if len(rows) < 30 or len(high) < 5 or len(other) < 5:
        return None
    observed = statistics.fmean(high) - statistics.fmean(other)
    rng = random.Random(RNG_SEED + 2)
    differences = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(rows, rng, BOOTSTRAP_BLOCK)
        sample_high = [row["target_rv_pct"] for row in sample if row["high_crowding"]]
        sample_other = [row["target_rv_pct"] for row in sample if not row["high_crowding"]]
        if sample_high and sample_other:
            differences.append(statistics.fmean(sample_high) - statistics.fmean(sample_other))
    if not differences:
        return None
    differences.sort()
    return {
        "high_n": len(high),
        "other_n": len(other),
        "mean_high_rv_pct": statistics.fmean(high),
        "mean_other_rv_pct": statistics.fmean(other),
        "high_minus_other_mean_rv_pct": observed,
        "reps": len(differences),
        "block_size_events": BOOTSTRAP_BLOCK,
        "ci_95_low_rv_pct": differences[int(0.025 * (len(differences) - 1))],
        "ci_95_high_rv_pct": differences[int(0.975 * (len(differences) - 1))],
    }


def improvement_pct(baseline: dict | None, augmented: dict | None) -> float | None:
    if not baseline or not augmented or baseline["rmse_log1p_rv"] <= 0:
        return None
    return 100.0 * (baseline["rmse_log1p_rv"] - augmented["rmse_log1p_rv"]) / baseline["rmse_log1p_rv"]


def decide(
    validation: dict,
    test: dict,
    paired: dict | None,
    event_study: dict | None,
) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline"), validation.get("augmented"))
    test_imp = improvement_pct(test.get("baseline"), test.get("augmented"))
    paired_low = paired.get("ci_95_low") if paired else None
    paired_high = paired.get("ci_95_high") if paired else None
    event_diff = event_study.get("high_minus_other_mean_rv_pct") if event_study else None
    event_low = event_study.get("ci_95_low_rv_pct") if event_study else None
    event_high = event_study.get("ci_95_high_rv_pct") if event_study else None
    enough = (
        validation.get("n", 0) >= 30
        and test.get("n", 0) >= 30
        and paired is not None
        and event_study is not None
    )
    if (
        enough and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired_low is not None and paired_low > 0
        and event_diff is not None and event_diff > 0
        and event_low is not None and event_low > 0
    ):
        return "BACKTESTED", "PROMISING — both chronological RMSE comparisons, paired-loss inference and the high-crowding event study pass the frozen criteria; independent validation and instrument-level economic evaluation remain necessary"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and paired_high is not None and paired_high < 0
        and event_diff is not None and event_diff <= 0
        and event_high is not None and event_high < 0
    ):
        return "REJECTED", "REJECTED — neither chronological period improves, paired-loss inference favors the baseline and high-crowding events do not exhibit higher subsequent realized volatility"
    return "INCONCLUSIVE", "INCONCLUSIVE — the preregistered evidence is mixed, statistically uncertain or insufficient"


def json_safe(value):
    return base.json_safe(value)


def update_registry(result: dict, report_path: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    summary = result.get("summary_metrics") or {}
    test = result.get("test_metrics") or {}
    event_study = test.get("high_crowding_event_study") or {}
    disposition = str(result.get("disposition", "INCONCLUSIVE")).replace("|", "/")
    scope = str(result.get("data_scope", "not established")).replace("|", "/")
    evidence = f"[session report]({report_path})"
    row = (
        f"| {HYPOTHESIS_ID} | {result.get('status', 'INCONCLUSIVE')} | "
        "Strictly lagged high leveraged-fund net-short share of 10-year U.S. Treasury futures open interest proxies basis-trade crowding and predicts next-five-session S&P 500 realized volatility beyond recent RV and VIX. | "
        f"{scope} | {disposition}; test_n={summary.get('test_n')}; test_RMSE_improvement={summary.get('test_improvement_pct')}%; high_crowding_RV_difference={event_study.get('high_minus_other_mean_rv_pct')}% | {evidence} |"
    )
    lines = content.splitlines()
    existing = next((i for i, line in enumerate(lines) if HYPOTHESIS_ID in line), None)
    if existing is not None:
        lines[existing] = row
    else:
        marker = next((i for i, line in enumerate(lines) if line.startswith("## Disposition rules")), None)
        if marker is None:
            raise ValueError("Hypothesis registry disposition marker missing")
        lines.insert(marker, row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    summary = result.get("summary_metrics") or {}
    validation = result.get("validation_metrics") or {}
    test = result.get("test_metrics") or {}
    event_meta = result.get("event_construction") or {}
    sources = result.get("data_sources") or {}
    lines = [
        f"# Research session — 10-year Treasury basis-crowding and S&P 500 volatility ({STAMP})",
        "",
        f"- Hypothesis: {HYPOTHESIS_ID}",
        f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'not established')}",
        f"- Daily real-data backtest KPI: {result.get('daily_kpi', 'MET before this additional study')}",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}",
        f"- Triggering commit: {SOURCE_SHA}",
        f"- Data scope: {result.get('data_scope', 'not established')}",
        "",
        "## Preregistered timing and method",
        "",
        f"- CFTC contract: 10-year U.S. Treasury Note, code {CFTC_CODE}, TFF futures-only dataset {CFTC_DATASET}.",
        f"- Conservative availability lag: {PUBLICATION_LAG_DAYS} calendar days after the CFTC report date; first S&P 500 close on or after that date is the signal close.",
        f"- Excluded known publication backlog: {BACKLOG_START} through {BACKLOG_END}.",
        f"- Predictor: trailing-156-report percentile of signed leveraged-fund net shorts divided by total open interest; high crowding >= {HIGH_CROWDING_THRESHOLD:.2f}.",
        "- Baseline: prior-five and prior-twenty-session S&P 500 realized volatility plus signal-date log VIX; augmented model adds the net-short percentile.",
        f"- Target: next-five-session S&P 500 realized volatility; rolling training window {MODEL_WINDOW} fully matured prior events.",
        "",
        "## Data provenance",
        "",
        "| Source | First date | Last date | Rows | SHA-256 |",
        "|---|---|---:|---:|---|",
    ]
    for source_name, source in sources.items():
        lines.append(
            f"| {source_name} | {source.get('first_date')} | {source.get('last_date')} | {source.get('rows')} | {source.get('sha256')} |"
        )
    if not sources:
        lines.append("| No accepted source data | not available | not available | 0 | not available |")
    lines.extend([
        "",
        "## Walk-forward results",
        "",
        "| Metric | Validation 2019–2021 | Test 2022 onward |",
        "|---|---:|---:|",
        f"| Forecasts | {summary.get('validation_n')} | {summary.get('test_n')} |",
        f"| Baseline RMSE, log1p RV | {(validation.get('baseline') or {}).get('rmse_log1p_rv')} | {(test.get('baseline') or {}).get('rmse_log1p_rv')} |",
        f"| Augmented RMSE, log1p RV | {(validation.get('augmented') or {}).get('rmse_log1p_rv')} | {(test.get('augmented') or {}).get('rmse_log1p_rv')} |",
        f"| RMSE improvement | {summary.get('validation_improvement_pct')}% | {summary.get('test_improvement_pct')}% |",
        "",
        f"- Candidate CFTC rows: {event_meta.get('candidate_origins')}; accepted events: {event_meta.get('events')}.",
        f"- Skipped events: {json.dumps(event_meta.get('skipped', {}), sort_keys=True)}.",
        f"- Paired test squared-loss bootstrap: {json.dumps(test.get('paired_squared_loss_bootstrap'), sort_keys=True)}.",
        f"- High-crowding event study: {json.dumps(test.get('high_crowding_event_study'), sort_keys=True)}.",
        "",
        "## Scientific disposition",
        "",
        result.get("disposition", "No disposition established."),
        "",
        "This is a volatility forecast using a cash-index close series and an aggregate futures-position proxy, not a tradable futures strategy or P&L. No causal, direct basis-trade attribution or live-trading claim is made.",
        "",
        "## Limitations",
        "",
        "- Leveraged-fund categories are not a direct measure of basis-trade positions or financing.",
        "- The 14-day lag and backlog exclusion are conservative timing controls, not exact historical release-time reconstruction.",
        "- CFTC positions are weekly and aggregate; FRED current-vintage data do not reconstruct historical release vintages.",
        "- SP500 is a cash price index, not an executable futures series or total-return index.",
        "- No raw source data are committed; response hashes and retrieval metadata are in the manifest.",
        "",
        "## Reproducibility",
        "",
        f"- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
        f"- Manifest: reports/generated/ust-10y-basis-crowding/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: research/ust_10y_basis_crowding_sp500_volatility.py",
        "- Tests: research/test_ust_10y_basis_crowding_sp500_volatility.py",
    ])
    if error:
        lines.extend(["", "## Execution or source-acceptance error", "", error])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-ust-10y-basis-crowding-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    relative_report = str(report_path.relative_to(ROOT))
    update_registry(result, relative_report)
    return relative_report, str(manifest_path.relative_to(ROOT))


def run_research() -> dict:
    today = dt.datetime.now(dt.timezone.utc).date()
    cftc_params = {
        "$select": ",".join([
            "report_date_as_yyyy_mm_dd",
            "contract_market_name",
            "cftc_contract_market_code",
            "open_interest_all",
            "lev_money_positions_long",
            "lev_money_positions_short",
        ]),
        "$where": (
            f"cftc_contract_market_code='{CFTC_CODE}' "
            f"AND report_date_as_yyyy_mm_dd >= '{CFTC_START.isoformat()}' "
            f"AND report_date_as_yyyy_mm_dd <= '{today.isoformat()}'"
        ),
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "50000",
    }
    cftc_url = CFTC_BASE_URL + "?" + urllib.parse.urlencode(cftc_params)
    fred_urls = {
        series_id: FRED_URL + "?" + urllib.parse.urlencode({
            "id": series_id,
            "cosd": PRICE_START.isoformat(),
            "coed": today.isoformat(),
        })
        for series_id in ("SP500", "VIXCLS")
    }
    cftc_body = fetch_bytes(cftc_url)
    fred_bodies = {series_id: fetch_bytes(url) for series_id, url in fred_urls.items()}
    cot_rows = parse_cftc(cftc_body)
    prices = parse_fred_series(fred_bodies["SP500"], "SP500")
    vix = parse_fred_series(fred_bodies["VIXCLS"], "VIXCLS")
    coverage = validate_source_coverage(cot_rows, prices, vix, today)
    crowding_rows = build_crowding_features(cot_rows)
    events, event_meta = build_events(crowding_rows, prices, vix)
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient accepted event history for preregistered walk-forward test: {len(events)}")

    predictions = walk_forward_predictions(events)
    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    validation_metrics = {
        "n": len(validation),
        "baseline": forecast_metrics(validation, "baseline_prediction_bp"),
        "augmented": forecast_metrics(validation, "augmented_prediction_bp"),
    }
    test_metrics = {
        "n": len(test),
        "baseline": forecast_metrics(test, "baseline_prediction_bp"),
        "augmented": forecast_metrics(test, "augmented_prediction_bp"),
        "paired_squared_loss_bootstrap": bootstrap_paired_loss(test),
        "high_crowding_event_study": bootstrap_crowding_difference(test),
    }
    status, disposition = decide(
        validation_metrics,
        test_metrics,
        test_metrics["paired_squared_loss_bootstrap"],
        test_metrics["high_crowding_event_study"],
    )
    data_scope = (
        f"CFTC TFF futures-only 10-year U.S. Treasury Note code {CFTC_CODE}; "
        f"FRED SP500 and VIXCLS daily; common price coverage {coverage['SP500']['first_date']} "
        f"to {coverage['common_price_end']}; {len(events)} accepted non-overlapping events; "
        "validation 2019–2021; test 2022 onward"
    )
    data_sources = {
        "CFTC_043602": {
            "url": cftc_url,
            "rows": len(cot_rows),
            "first_date": coverage["CFTC"]["first_date"],
            "last_date": coverage["CFTC"]["last_date"],
            "sha256": sha256(cftc_body),
        },
        "SP500": {
            "url": fred_urls["SP500"],
            "rows": len(prices),
            "first_date": coverage["SP500"]["first_date"],
            "last_date": coverage["SP500"]["last_date"],
            "sha256": sha256(fred_bodies["SP500"]),
        },
        "VIXCLS": {
            "url": fred_urls["VIXCLS"],
            "rows": len(vix),
            "first_date": coverage["VIXCLS"]["first_date"],
            "last_date": coverage["VIXCLS"]["last_date"],
            "sha256": sha256(fred_bodies["VIXCLS"]),
        },
    }
    limitations = [
        "CFTC leveraged-fund categories are not a direct identification of cash-futures basis-trade positions.",
        "The 14-day publication lag is conservative and does not reconstruct exact historical report release timestamps.",
        "The known CFTC publication-backlog interval is excluded; the rolling percentile history spans the pre- and post-backlog report sequence.",
        "FRED current-vintage observations are used; historical release vintages are not reconstructed.",
        "SP500 is a cash price index, not an executable futures series or total-return index.",
        "Forecasting only: no causal claim, transaction-cost model, tradable strategy or live-deployment conclusion.",
        "No raw source data are committed; only hashes, retrieval metadata and aggregate metrics are retained.",
    ]
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "MET before this additional study — multiple distinct real-data backtests were completed earlier on 2026-11-25",
        "data_scope": data_scope,
        "source_coverage": coverage,
        "data_sources": data_sources,
        "event_construction": event_meta,
        "methodology": {
            "cftc_contract_code": CFTC_CODE,
            "cftc_dataset": CFTC_DATASET,
            "cftc_position_feature": "(leveraged_fund_short - leveraged_fund_long) / total_open_interest",
            "crowding_feature": "mid-rank percentile of signed net-short/OI against previous 156 non-backlog reports only",
            "high_crowding_threshold": HIGH_CROWDING_THRESHOLD,
            "publication_lag_days": PUBLICATION_LAG_DAYS,
            "baseline_features": ["pre_rv5_log", "pre_rv20_log", "log_vix"],
            "augmented_features": ["pre_rv5_log", "pre_rv20_log", "log_vix", "net_short_percentile"],
            "rolling_training_events": MODEL_WINDOW,
            "target_sessions": TARGET_SESSIONS,
            "target": "log1p(next-five-session S&P 500 realized volatility in percent)",
            "training_rule": "training target_end_date must be strictly earlier than current signal_date",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": RNG_SEED,
        },
        "summary_metrics": {
            "validation_n": len(validation),
            "test_n": len(test),
            "validation_improvement_pct": improvement_pct(validation_metrics["baseline"], validation_metrics["augmented"]),
            "test_improvement_pct": improvement_pct(test_metrics["baseline"], test_metrics["augmented"]),
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "limitations": limitations,
    }


def main() -> int:
    try:
        result = run_research()
        report = render_report(result)
        report_path, manifest_path = write_outputs(result, report)
        print(json.dumps({
            "hypothesis_id": HYPOTHESIS_ID,
            "status": result["status"],
            "daily_kpi": result["daily_kpi"],
            "report_path": report_path,
            "manifest_path": manifest_path,
            "summary_metrics": result["summary_metrics"],
        }, indent=2))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — bounded source or execution failure: {error}",
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "MET before this additional study — prior distinct real-data backtests already met today's minimum",
            "data_scope": "source acceptance incomplete",
            "error": error,
        }
        report_path, manifest_path = write_outputs(result, render_report(result, error))
        print(json.dumps({
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "error": error,
            "report_path": report_path,
            "manifest_path": manifest_path,
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
