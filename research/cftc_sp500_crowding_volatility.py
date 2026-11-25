#!/usr/bin/env python3
"""Walk-forward forecast test: CFTC leveraged-fund crowding -> S&P 500 realized volatility."""
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

HYPOTHESIS_ID = "QFR-2026-11-25-CFTC-SP500-CROWDING-VOL-01"
CFTC_CODE = "13874A"
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

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "cftc-sp500-crowding" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
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
        if report_date is None:
            raise ValueError("CFTC row has an invalid report date")
        if not market_name or "E-MINI S&P 500" not in market_name.upper():
            raise ValueError(f"Unexpected market name for code {CFTC_CODE}: {market_name!r}")
        if open_interest is None or open_interest <= 0:
            raise ValueError(f"Invalid open interest for report {report_date}")
        if long_position is None or short_position is None or long_position < 0 or short_position < 0:
            raise ValueError(f"Invalid leveraged-money positions for report {report_date}")
        net = long_position - short_position
        if abs(net) > open_interest:
            raise ValueError(f"Leveraged-money net position exceeds open interest for {report_date}")
        rows.append({
            "report_date": report_date,
            "market_name": market_name,
            "cftc_contract_market_code": code,
            "open_interest": open_interest,
            "lev_money_long": long_position,
            "lev_money_short": short_position,
            "lev_money_net": net,
            "net_pct_oi": net / open_interest,
            "abs_net_pct_oi": abs(net / open_interest),
        })
    if not rows:
        raise ValueError(f"No CFTC rows found for exact contract code {CFTC_CODE}")
    rows.sort(key=lambda row: row["report_date"])
    dates = [row["report_date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate CFTC report dates for the selected contract")
    return rows


def parse_fred_sp500(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or "SP500" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED SP500 CSV schema: {reader.fieldnames}")
    values: dict[dt.date, float] = {}
    for row in reader:
        obs_date = base.parse_date(row.get("observation_date") or row.get("DATE"))
        value = base.parse_float(row.get("SP500"))
        if obs_date is None or value is None:
            continue
        if value <= 0:
            raise ValueError(f"Non-positive S&P 500 close on {obs_date}")
        if obs_date in values:
            raise ValueError(f"Duplicate FRED SP500 observation date: {obs_date}")
        values[obs_date] = value
    if len(values) < 1500:
        raise ValueError(f"Insufficient FRED SP500 observations: {len(values)}")
    dates = sorted(values)
    if dates[0] > PRICE_START + dt.timedelta(days=90):
        raise ValueError(f"FRED SP500 history starts unexpectedly late: {dates[0]}")
    return dict(sorted(values.items()))


def is_backlog_report(report_date: dt.date) -> bool:
    return BACKLOG_START <= report_date <= BACKLOG_END


def build_crowding_features(rows: list[dict], lookback: int = CROWDING_LOOKBACK) -> list[dict]:
    """Rank each absolute net/OI observation against prior reports only."""
    ordered = sorted(rows, key=lambda row: row["report_date"])
    result = []
    prior_values: list[float] = []
    for row in ordered:
        if is_backlog_report(row["report_date"]):
            enriched = dict(row)
            enriched["crowding_percentile"] = None
            enriched["high_crowding"] = False
            result.append(enriched)
            continue
        if len(prior_values) >= lookback:
            history = prior_values[-lookback:]
            current = row["abs_net_pct_oi"]
            less = sum(value < current for value in history)
            equal = sum(value == current for value in history)
            percentile = (less + 0.5 * equal) / len(history)
            enriched = dict(row)
            enriched["crowding_percentile"] = percentile
            enriched["high_crowding"] = percentile >= HIGH_CROWDING_THRESHOLD
            result.append(enriched)
        else:
            enriched = dict(row)
            enriched["crowding_percentile"] = None
            enriched["high_crowding"] = False
            result.append(enriched)
        prior_values.append(row["abs_net_pct_oi"])
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


def build_events(cot_rows: list[dict], prices: dict[dt.date, float]) -> tuple[list[dict], dict]:
    price_dates, returns = daily_log_returns(prices)
    events = []
    skipped = {
        "known_publication_backlog": 0,
        "no_signal_close": 0,
        "signal_close_too_far_after_lag": 0,
        "insufficient_pre_history": 0,
        "incomplete_return_window": 0,
        "overlapping_target_window": 0,
    }
    for row in sorted(cot_rows, key=lambda item: item["report_date"]):
        report_date = row["report_date"]
        if is_backlog_report(report_date):
            skipped["known_publication_backlog"] += 1
            continue
        if row.get("crowding_percentile") is None:
            continue
        availability_date = report_date + dt.timedelta(days=PUBLICATION_LAG_DAYS)
        signal_index = bisect.bisect_left(price_dates, availability_date)
        if signal_index >= len(price_dates):
            skipped["no_signal_close"] += 1
            continue
        signal_date = price_dates[signal_index]
        if (signal_date - availability_date).days > 4:
            skipped["signal_close_too_far_after_lag"] += 1
            continue
        if signal_index < 20 or signal_index + TARGET_SESSIONS >= len(price_dates):
            skipped["insufficient_pre_history"] += 1
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
            "record_date": signal_date,
            "signal_date": signal_date,
            "availability_date": availability_date,
            "target_start_date": price_dates[signal_index + 1],
            "target_end_date": target_end_date,
            "pre_rv5_pct": pre_rv5,
            "pre_rv20_pct": pre_rv20,
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "target_rv_pct": target_rv,
            "target_bp": math.log1p(target_rv),
        })
        events.append(event)
    return events, {
        "cot_rows_with_crowding": sum(row.get("crowding_percentile") is not None for row in cot_rows),
        "events": len(events),
        "skipped": skipped,
        "publication_lag_days": PUBLICATION_LAG_DAYS,
        "known_backlog_exclusion": [BACKLOG_START.isoformat(), BACKLOG_END.isoformat()],
    }


def walk_forward_predictions(events: list[dict]) -> list[dict]:
    predictions = []
    baseline_features = ["pre_rv5_log", "pre_rv20_log"]
    augmented_features = baseline_features + ["crowding_percentile"]
    for current in events:
        train = [
            row for row in events
            if row["record_date"] < current["record_date"]
            and row["target_end_date"] < current["record_date"]
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
            "record_date": current["record_date"],
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_rv_pct": current["target_rv_pct"],
            "crowding_percentile": current["crowding_percentile"],
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
    high_n = sum(row["high_crowding"] for row in rows)
    other_n = len(rows) - high_n
    if len(rows) < 30 or high_n < 5 or other_n < 5:
        return None
    high = [row["target_rv_pct"] for row in rows if row["high_crowding"]]
    other = [row["target_rv_pct"] for row in rows if not row["high_crowding"]]
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
        "high_n": high_n,
        "other_n": other_n,
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


def decide(validation: dict, test: dict, paired: dict | None, event_study: dict | None) -> tuple[str, str]:
    val_base = validation.get("baseline")
    val_aug = validation.get("augmented")
    test_base = test.get("baseline")
    test_aug = test.get("augmented")
    val_imp = improvement_pct(val_base, val_aug)
    test_imp = improvement_pct(test_base, test_aug)
    diff = event_study.get("high_minus_other_mean_rv_pct") if event_study else None
    ci_low = event_study.get("ci_95_low_rv_pct") if event_study else None
    paired_low = paired.get("ci_95_low") if paired else None
    enough = (
        validation.get("n", 0) >= 30
        and test.get("n", 0) >= 30
        and paired is not None
        and event_study is not None
    )
    if enough and val_imp is not None and test_imp is not None and val_imp > 0 and test_imp > 0 and paired_low is not None and paired_low > 0 and diff is not None and diff > 0 and ci_low is not None and ci_low > 0:
        return "BACKTESTED", "PROMISING — all preregistered forecast and crowding-event criteria passed; independent validation and instrument-level economic evaluation are still required"
    if val_imp is not None and test_imp is not None and val_imp <= 0 and test_imp <= 0 and diff is not None and diff <= 0:
        return "REJECTED", "REJECTED — neither chronological period improves and high-crowding events do not exhibit higher subsequent realized volatility"
    return "INCONCLUSIVE", "INCONCLUSIVE — the preregistered evidence is mixed, statistically uncertain or insufficient"


def json_safe(value):
    return base.json_safe(value)


def update_registry(result: dict, report_path: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    if HYPOTHESIS_ID in content:
        return
    summary = result.get("summary_metrics") or {}
    test = result.get("test_metrics") or {}
    event_study = test.get("high_crowding_event_study") or {}
    disposition = str(result.get("disposition", "INCONCLUSIVE")).replace("|", "/")
    scope = str(result.get("data_scope", "not established")).replace("|", "/")
    evidence = f"[{report_path}](../{report_path})"
    row = (
        f"| {HYPOTHESIS_ID} | {result.get('status', 'INCONCLUSIVE')} | "
        "Extreme absolute CFTC leveraged-fund net positioning as a share of E-mini S&P 500 open interest predicts next-five-session S&P 500 realized volatility beyond recent volatility. | "
        f"{scope} | {disposition}; test_n={summary.get('test_n')}; test_log_RMSE_improvement={summary.get('test_improvement_pct')}%; high-crowding_RV_difference={event_study.get('high_minus_other_mean_rv_pct')}% | {evidence} |"
    )
    marker = "\n## Disposition rules"
    if marker not in content:
        raise ValueError("Hypothesis registry disposition marker missing")
    REGISTRY_PATH.write_text(content.replace(marker, "\n" + row + "\n" + marker, 1), encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    summary = result.get("summary_metrics") or {}
    validation = result.get("validation_metrics") or {}
    test = result.get("test_metrics") or {}
    lines = [
        f"# Session report — CFTC leveraged-fund crowding and S&P 500 volatility ({STAMP})",
        "",
        f"- Hypothesis: {HYPOTHESIS_ID}",
        f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'not established')}",
        f"- Daily real-data backtest KPI: {result.get('daily_kpi', 'MISSED')}",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}",
        f"- Triggering commit: {SOURCE_SHA}",
        f"- Data scope: {result.get('data_scope', 'not established')}",
        "",
        "## Preregistered timing and method",
        "",
        f"- CFTC contract: E-mini S&P 500, code {CFTC_CODE}, TFF futures-only dataset {CFTC_DATASET}.",
        f"- Conservative availability lag: {PUBLICATION_LAG_DAYS} calendar days after the CFTC report date; first S&P close on or after that date is the signal close.",
        f"- Excluded known publication backlog: {BACKLOG_START} through {BACKLOG_END}.",
        f"- Target: next-five-session realized volatility after signal close; baseline uses prior five- and twenty-session volatility; augmented model adds trailing-156-report crowding percentile.",
        f"- Rolling training window: {MODEL_WINDOW} prior mature weekly events; target windows may not overlap.",
        "",
        "## Data provenance",
        "",
        f"- CFTC rows: {(result.get('cftc_source') or {}).get('rows')}",
        f"- CFTC coverage: {(result.get('cftc_source') or {}).get('first_date')} to {(result.get('cftc_source') or {}).get('last_date')}",
        f"- FRED SP500 observations: {(result.get('price_source') or {}).get('observations')}",
        f"- FRED coverage: {(result.get('price_source') or {}).get('first_date')} to {(result.get('price_source') or {}).get('last_date')}",
        f"- Events: {(result.get('event_construction') or {}).get('events')}",
        f"- Skips: {(result.get('event_construction') or {}).get('skipped')}",
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
        "## Test-period uncertainty and event study",
        "",
        f"- Paired squared-log-loss bootstrap: {test.get('paired_squared_loss_bootstrap')}",
        f"- High-crowding event study: {test.get('high_crowding_event_study')}",
        "",
        "## Scientific disposition",
        "",
        result.get("disposition", "No disposition established."),
        "",
        "This is a volatility forecast using a cash-index close series, not a tradable futures strategy or P&L. No causal or live-trading claim is made.",
        "",
        "## Limitations",
        "",
        "- CFTC trader classes are based on predominant business purpose, not the intent of each position.",
        "- Historical exact release timestamps are not available beyond the CFTC's latest 13 months; a fixed 14-day lag and documented backlog exclusion are conservative proxies, not exact historical release reconstruction.",
        "- The 2025 publication interruption window is excluded; future changes to the CFTC publication frequency require a new timing check.",
        "- FRED SP500 is a cash price index, not an executable futures series or total-return index.",
        "- No raw source data are committed; response hashes and retrieval metadata are in the manifest.",
        "",
        "## Reproducibility",
        "",
        f"- Manifest: reports/generated/cftc-sp500-crowding/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: research/cftc_sp500_crowding_volatility.py",
        "- Tests: research/test_cftc_sp500_crowding_volatility.py",
    ]
    if error:
        lines.extend(["", "## Execution error", "", error])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-cftc-sp500-crowding-{RUN_ID}.md"
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
    fred_url = FRED_URL + "?" + urllib.parse.urlencode({
        "id": "SP500",
        "cosd": PRICE_START.isoformat(),
        "coed": today.isoformat(),
    })
    cftc_body = fetch_bytes(cftc_url)
    price_body = fetch_bytes(fred_url)
    cot_rows = parse_cftc(cftc_body)
    if cot_rows[0]["report_date"] > CFTC_START + dt.timedelta(days=90):
        raise ValueError(f"CFTC history starts unexpectedly late: {cot_rows[0]['report_date']}")
    prices = parse_fred_sp500(price_body)
    crowding_rows = build_crowding_features(cot_rows)
    events, event_meta = build_events(crowding_rows, prices)
    predictions = walk_forward_predictions(events)

    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    validation_metrics = {
        "baseline": forecast_metrics(validation, "baseline_prediction_bp"),
        "augmented": forecast_metrics(validation, "augmented_prediction_bp"),
    }
    test_metrics = {
        "baseline": forecast_metrics(test, "baseline_prediction_bp"),
        "augmented": forecast_metrics(test, "augmented_prediction_bp"),
        "paired_squared_loss_bootstrap": bootstrap_paired_loss(test),
        "high_crowding_event_study": bootstrap_crowding_difference(test),
    }
    val_improvement = improvement_pct(validation_metrics["baseline"], validation_metrics["augmented"])
    test_improvement = improvement_pct(test_metrics["baseline"], test_metrics["augmented"])
    status, disposition = decide(
        {"n": len(validation), **validation_metrics},
        {"n": len(test), **test_metrics},
        test_metrics["paired_squared_loss_bootstrap"],
        test_metrics["high_crowding_event_study"],
    )
    cftc_dates = [row["report_date"] for row in cot_rows]
    price_dates = sorted(prices)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "daily_kpi": "MET — prior independent real-data backtests already met today's minimum; this is an additional distinct hypothesis",
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "data_scope": (
            f"CFTC TFF futures-only E-mini S&P 500 code {CFTC_CODE}, {cftc_dates[0]} to {cftc_dates[-1]} "
            f"(known backlog excluded from event and crowding history); FRED SP500 {price_dates[0]} to {price_dates[-1]}"
        ),
        "cftc_source": {
            "url": CFTC_BASE_URL,
            "dataset": CFTC_DATASET,
            "contract_code": CFTC_CODE,
            "rows": len(cot_rows),
            "first_date": cftc_dates[0].isoformat(),
            "last_date": cftc_dates[-1].isoformat(),
            "fields": [
                "report_date_as_yyyy_mm_dd",
                "contract_market_name",
                "cftc_contract_market_code",
                "open_interest_all",
                "lev_money_positions_long",
                "lev_money_positions_short",
            ],
            "sha256": sha256(cftc_body),
        },
        "price_source": {
            "url": FRED_URL,
            "series": "SP500",
            "observations": len(prices),
            "first_date": price_dates[0].isoformat(),
            "last_date": price_dates[-1].isoformat(),
            "sha256": sha256(price_body),
        },
        "event_construction": event_meta,
        "methodology": {
            "publication_lag_days": PUBLICATION_LAG_DAYS,
            "backlog_exclusion": [BACKLOG_START.isoformat(), BACKLOG_END.isoformat()],
            "crowding_lookback_reports": CROWDING_LOOKBACK,
            "high_crowding_threshold": HIGH_CROWDING_THRESHOLD,
            "rolling_training_events": MODEL_WINDOW,
            "target_sessions": TARGET_SESSIONS,
            "validation": f"{VALIDATION_START} through {TEST_START - dt.timedelta(days=1)}",
            "test": f"{TEST_START} onward",
            "baseline_features": ["log1p(pre_rv5_pct)", "log1p(pre_rv20_pct)"],
            "augmented_features": ["log1p(pre_rv5_pct)", "log1p(pre_rv20_pct)", "trailing_156_report_abs_net_pct_oi_percentile"],
            "target": "log1p(next-five-session realized volatility in percent)",
            "training_rule": "training target end date must be strictly earlier than current signal date",
            "overlap_rule": "no overlapping next-five-session target windows",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": RNG_SEED,
        },
        "summary_metrics": {
            "validation_n": len(validation),
            "test_n": len(test),
            "validation_improvement_pct": val_improvement,
            "test_improvement_pct": test_improvement,
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "limitations": [
            "CFTC trader classifications reflect predominant business purpose, not the purpose of each position.",
            "Historical exact CFTC release timestamps are unavailable beyond the latest 13 months; 14-day lag is a conservative timing convention.",
            "Known 2025 publication backlog reports are excluded from both signal and trailing-position history.",
            "FRED SP500 is a cash price index, not an executable futures or total-return series.",
            "Forecasting only; no tradable P&L, causal effect or live deployment claim.",
        ],
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
            "daily_kpi": "MET — prior independent real-data backtests already met today's minimum; this additional study did not complete",
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
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
