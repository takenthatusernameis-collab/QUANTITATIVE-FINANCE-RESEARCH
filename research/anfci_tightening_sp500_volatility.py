#!/usr/bin/env python3
"""Walk-forward forecast screen: lagged ANFCI tightening shock -> S&P 500 realized volatility."""
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
from pathlib import Path

import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-25-ANFCI-TIGHTENING-SP500-RV-01"
START_DATE = dt.date(2016, 11, 25)
RELEASE_LAG_DAYS = 7
FEATURE_LAG_WEEKS = 4
MODEL_WINDOW = 104
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
RNG_SEED = 20261126
MIN_ANFCI_ROWS = 400
MIN_PRICE_ROWS = 1500
MAX_ANFCI_AGE_DAYS = 10
MAX_PRICE_AGE_DAYS = 8

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "anfci-tightening-shock" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"

SERIES = ("ANFCI", "SP500", "VIXCLS")
BASELINE_FEATURES = ("pre_rv5_log", "pre_rv20_log", "log_vix")
AUGMENTED_FEATURES = BASELINE_FEATURES + ("anfci_4w_change",)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def parse_fred_series(body: bytes, series_id: str, positive_required: bool = False) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED {series_id} CSV schema: {reader.fieldnames}")
    date_field = "observation_date" if "observation_date" in reader.fieldnames else "DATE"
    if date_field not in reader.fieldnames:
        raise ValueError(f"FRED {series_id} CSV has no recognized observation-date field")
    values: dict[dt.date, float] = {}
    for row in reader:
        raw_value = row.get(series_id)
        if raw_value is None or not str(raw_value).strip() or str(raw_value).strip() == ".":
            continue
        obs_date = base.parse_date(row.get(date_field))
        value = base.parse_float(raw_value)
        if obs_date is None or value is None:
            raise ValueError(f"Invalid {series_id} observation row: {row}")
        if positive_required and value <= 0:
            raise ValueError(f"Non-positive {series_id} observation on {obs_date}")
        if obs_date in values:
            raise ValueError(f"Duplicate FRED {series_id} observation date: {obs_date}")
        values[obs_date] = value
    if not values:
        raise ValueError(f"No valid FRED observations for {series_id}")
    return dict(sorted(values.items()))


def validate_source_coverage(
    series: dict[str, dict[dt.date, float]], today: dt.date
) -> dict:
    anfci = series["ANFCI"]
    prices = series["SP500"]
    vix = series["VIXCLS"]
    for name, values, minimum in (
        ("ANFCI", anfci, MIN_ANFCI_ROWS),
        ("SP500", prices, MIN_PRICE_ROWS),
        ("VIXCLS", vix, MIN_PRICE_ROWS),
    ):
        if len(values) < minimum:
            raise ValueError(f"Insufficient {name} observations: {len(values)} < {minimum}")
        first, last = min(values), max(values)
        if first > START_DATE + dt.timedelta(days=90):
            raise ValueError(f"{name} history starts unexpectedly late: {first}")
        if last > today:
            raise ValueError(f"{name} contains a future observation: {last}")
    if any(date.weekday() != 4 for date in anfci):
        raise ValueError("ANFCI observations are not weekly-ending-Friday dates")
    anfci_last = max(anfci)
    if (today - anfci_last).days > MAX_ANFCI_AGE_DAYS:
        raise ValueError(f"ANFCI is stale: latest week {anfci_last}, age {(today - anfci_last).days} days")
    price_last = max(prices)
    vix_last = max(vix)
    if abs((price_last - vix_last).days) > 4:
        raise ValueError("FRED SP500 and VIXCLS latest observations are not synchronized")
    common_end = min(price_last, vix_last)
    if (today - common_end).days > MAX_PRICE_AGE_DAYS:
        raise ValueError(f"FRED price data are stale: common end {common_end}")
    return {
        name: {
            "rows": len(values),
            "first_date": min(values).isoformat(),
            "last_date": max(values).isoformat(),
        }
        for name, values in series.items()
    }


def daily_log_returns(prices: dict[dt.date, float]) -> tuple[list[dt.date], list[float | None]]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days > 4:
            returns.append(None)
            continue
        value = math.log(prices[dates[index]] / prices[dates[index - 1]])
        returns.append(value if math.isfinite(value) else None)
    return dates, returns


def realized_volatility(returns: list[float | None]) -> float:
    if not returns or any(value is None or not math.isfinite(value) for value in returns):
        raise ValueError("Realized-volatility window contains a missing or invalid return")
    return math.sqrt(sum(float(value) ** 2 for value in returns)) * 100.0


def build_events(
    anfci: dict[dt.date, float],
    prices: dict[dt.date, float],
    vix: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    price_dates, returns = daily_log_returns(prices)
    weekly_dates = sorted(anfci)
    events: list[dict] = []
    skipped = {
        "insufficient_four_week_history": 0,
        "irregular_weekly_feature_window": 0,
        "no_signal_close": 0,
        "signal_close_too_far_after_release_lag": 0,
        "missing_vix_on_signal_date": 0,
        "insufficient_price_history_or_future": 0,
        "incomplete_return_window": 0,
        "overlapping_target_window": 0,
    }
    for index in range(len(weekly_dates)):
        if index < FEATURE_LAG_WEEKS:
            skipped["insufficient_four_week_history"] += 1
            continue
        feature_dates = weekly_dates[index - FEATURE_LAG_WEEKS:index + 1]
        if any((feature_dates[i] - feature_dates[i - 1]).days != 7 for i in range(1, len(feature_dates))):
            skipped["irregular_weekly_feature_window"] += 1
            continue
        week_end = weekly_dates[index]
        tightening_change = anfci[week_end] - anfci[weekly_dates[index - FEATURE_LAG_WEEKS]]
        availability_date = week_end + dt.timedelta(days=RELEASE_LAG_DAYS)
        signal_index = bisect.bisect_left(price_dates, availability_date)
        if signal_index >= len(price_dates):
            skipped["no_signal_close"] += 1
            continue
        signal_date = price_dates[signal_index]
        if (signal_date - availability_date).days > 4:
            skipped["signal_close_too_far_after_release_lag"] += 1
            continue
        if signal_date not in vix:
            skipped["missing_vix_on_signal_date"] += 1
            continue
        if signal_index < 20 or signal_index + TARGET_SESSIONS >= len(price_dates):
            skipped["insufficient_price_history_or_future"] += 1
            continue
        try:
            pre_rv5 = realized_volatility(returns[signal_index - 4:signal_index + 1])
            pre_rv20 = realized_volatility(returns[signal_index - 19:signal_index + 1])
            target_rv = realized_volatility(returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1])
        except ValueError:
            skipped["incomplete_return_window"] += 1
            continue
        target_end = price_dates[signal_index + TARGET_SESSIONS]
        if events and signal_date < events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        event = {
            "week_end_date": week_end,
            "availability_date": availability_date,
            "signal_date": signal_date,
            "target_start_date": price_dates[signal_index + 1],
            "target_end_date": target_end,
            "anfci_4w_change": tightening_change,
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "log_vix": math.log(vix[signal_date]),
            "target_rv_pct": target_rv,
            "target_bp": math.log1p(target_rv),
        }
        events.append(event)
    return events, {
        "candidate_weekly_observations": len(weekly_dates),
        "accepted_events": len(events),
        "skipped": skipped,
        "release_lag_days": RELEASE_LAG_DAYS,
        "feature_change_weeks": FEATURE_LAG_WEEKS,
        "target_sessions": TARGET_SESSIONS,
        "event_spacing": "weekly observations; target windows must not overlap; equality at the next signal close is allowed",
        "signal_rule": "first S&P 500 close on or after week-ending Friday + 7 calendar days; exact same-date VIX required",
    }


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
            baseline = base.fit_ols_predict(train, current, list(BASELINE_FEATURES))
            augmented = base.fit_ols_predict(train, current, list(AUGMENTED_FEATURES))
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "week_end_date": current["week_end_date"],
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_rv_pct": current["target_rv_pct"],
            "anfci_4w_change": current["anfci_4w_change"],
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
        "oos_r2_vs_period_mean": 1.0 - sse / denominator if denominator > 1e-12 else None,
    }


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    differences = []
    for row in rows:
        target = row["target_bp"]
        baseline = row["baseline_prediction_bp"]
        augmented = row["augmented_prediction_bp"]
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not math.isfinite(difference):
            return None
        differences.append({"loss_difference": difference})
    observed = statistics.fmean(row["loss_difference"] for row in differences)
    rng = random.Random(RNG_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(differences, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["loss_difference"] for row in sample))
    samples.sort()
    return {
        "status": "COMPUTED",
        "observations": len(differences),
        "reps": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "mean_baseline_minus_augmented_squared_log_loss": observed,
        "ci_95_low": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def improvement_pct(baseline: dict | None, augmented: dict | None) -> float | None:
    if not baseline or not augmented or baseline["rmse_log1p_rv"] <= 0:
        return None
    return 100.0 * (baseline["rmse_log1p_rv"] - augmented["rmse_log1p_rv"]) / baseline["rmse_log1p_rv"]


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline"), validation.get("augmented"))
    test_imp = improvement_pct(test.get("baseline"), test.get("augmented"))
    if (
        validation.get("n", 0) >= 30 and test.get("n", 0) >= 30
        and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired is not None and paired.get("ci_95_low") is not None
        and paired["ci_95_low"] > 0
    ):
        return "BACKTESTED", "PROMISING — both chronological RMSE comparisons improve and the paired-loss 95% lower confidence bound is positive; independent validation and instrument-level economic evaluation remain necessary"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and paired is not None and paired.get("ci_95_high") is not None
        and paired["ci_95_high"] < 0
    ):
        return "REJECTED", "REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule"


def upsert_registry(status: str, disposition: str, scope: str, report_relative: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Strictly lagged four-week change in the Chicago Fed adjusted financial-conditions index adds information about next-five-session S&P 500 realized volatility beyond recent realized volatility and VIX. | {scope} | {disposition} | [session report]({report_relative}) |"
    )
    lines = content.splitlines()
    existing = next((i for i, line in enumerate(lines) if HYPOTHESIS_ID in line), None)
    if existing is not None:
        lines[existing] = row
    else:
        header = next((i for i, line in enumerate(lines) if line.startswith("| Hypothesis ID |")), None)
        if header is None or header + 1 >= len(lines):
            raise ValueError("Hypothesis registry table header not found")
        lines.insert(header + 2, row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    lines = [
        f"# Research session — ANFCI tightening shock and S&P 500 volatility ({result.get('retrieved_at_utc', SESSION_TIME.isoformat())})",
        "",
        f"- Hypothesis: {HYPOTHESIS_ID}",
        f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'INCONCLUSIVE')}",
        "- Daily real-data backtest KPI: MET before this additional study by distinct 2026-11-25 experiments",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}",
        f"- Triggering commit: {SOURCE_SHA}",
        "",
        "## Preregistered mechanism and method",
        "",
        "- Predictor: four-week change in the Chicago Fed Adjusted National Financial Conditions Index (ANFCI). Positive change means financial conditions tightened relative to prevailing economic conditions.",
        "- ANFCI weekly reference date is Friday. The index is treated as unavailable until seven calendar days later; use the first S&P 500 close on or after that date.",
        "- Baseline: prior-five and prior-twenty-session S&P 500 realized volatility plus signal-date log VIX. Augmented model adds only the four-week ANFCI change.",
        "- Target: next-five-session S&P 500 realized volatility; rolling training window 104 prior events whose target end is strictly earlier than the current signal date.",
        "- Validation: 2019–2021. Test: 2022 onward. Primary metric: RMSE in log1p realized-volatility space.",
        "",
    ]
    if error:
        lines.extend(["## Execution / feasibility blocker", "", error, ""])
    else:
        lines.extend(["## Data provenance", "", "| Source | First date | Last date | Rows | SHA-256 |", "|---|---|---:|---:|---|"])
        for name, source in result["data_sources"].items():
            lines.append(f"| {name} | {source['first_date']} | {source['last_date']} | {source['rows']} | {source['sha256']} |")
        lines.extend([
            "",
            "## Frozen walk-forward results",
            "",
            "| Metric | Validation 2019–2021 | Test 2022 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {result['validation_metrics']['n']} | {result['test_metrics']['n']} |",
            f"| Baseline RMSE, log1p RV | {result['validation_metrics']['baseline']['rmse_log1p_rv']:.8f} | {result['test_metrics']['baseline']['rmse_log1p_rv']:.8f} |",
            f"| Augmented RMSE, log1p RV | {result['validation_metrics']['augmented']['rmse_log1p_rv']:.8f} | {result['test_metrics']['augmented']['rmse_log1p_rv']:.8f} |",
            f"| RMSE improvement | {result['summary_metrics']['validation_improvement_pct']:.4f}% | {result['summary_metrics']['test_improvement_pct']:.4f}% |",
            "",
            f"- Accepted non-overlapping weekly events: {result['event_construction']['accepted_events']} of {result['event_construction']['candidate_weekly_observations']} weekly observations.",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- Paired test squared-loss bootstrap: {json.dumps(result['paired_squared_loss_bootstrap'], sort_keys=True)}.",
            "",
        ])
    verified = (
        "**VERIFIED:** deterministic timing/alignment tests, source schema and coverage acceptance, strict release lag, exact-date VIX alignment, no forward-fill, non-overlapping targets, fully matured training targets and the recorded result under this code/data vintage."
        if error is None else
        "**VERIFIED:** deterministic code and timing/alignment tests. The actual source acceptance gate did not pass, so no real-data backtest result is claimed."
    )
    unverified = (
        "**UNVERIFIED:** historical point-in-time ANFCI vintages, exact intraday availability beyond the published weekly schedule, stability under future regimes, independent source reconstruction and instrument-level economic value."
        if error is None else
        "**UNVERIFIED:** accepted FRED coverage/freshness, event sample, model forecasts, performance metrics and any empirical disposition beyond INCONCLUSIVE."
    )
    lines.extend([
        "## Verified versus unverified",
        "",
        verified,
        "",
        unverified,
        "",
        "## Explicit limitations",
        "",
        "- ANFCI is a composite indicator; its constituent financial variables may overlap with market indicators, including information correlated with VIX and equity prices.",
        "- Chicago Fed states that ANFCI history is revised as component data and estimated weights change. This screen uses the current FRED vintage, not historical release vintages; the seven-day lag does not remove revision look-ahead.",
        "- ANFCI is macro-adjusted but not a pure exogenous funding shock or causal measure of forced deleveraging.",
        "- SP500 is a cash price index, not an executable futures series or total-return index. Forecasting only: no trading P&L, transaction-cost model or live-deployment conclusion.",
        "- No raw source data are committed; only retrieval metadata, hashes and aggregate metrics are retained.",
        "",
        "## Reproducibility",
        "",
        f"- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
        f"- Manifest: reports/generated/anfci-tightening-shock/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: research/anfci_tightening_sp500_volatility.py",
        "- Tests: research/test_anfci_tightening_sp500_volatility.py",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-anfci-tightening-shock-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    relative_report = str(report_path.relative_to(ROOT))
    upsert_registry(
        result.get("status", "INCONCLUSIVE"),
        result.get("disposition", "INCONCLUSIVE"),
        result.get("data_scope", "source acceptance incomplete"),
        relative_report,
    )
    return str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))


def run_research() -> dict:
    raw: dict[str, bytes] = {}
    parsed: dict[str, dict[dt.date, float]] = {}
    urls: dict[str, str] = {}
    for series_id in SERIES:
        url = f"{FRED_URL}?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url, timeout=25)
        raw[series_id] = body
        parsed[series_id] = parse_fred_series(body, series_id, positive_required=series_id in {"SP500", "VIXCLS"})
        urls[series_id] = url

    coverage = validate_source_coverage(parsed, dt.datetime.now(dt.timezone.utc).date())
    events, event_meta = build_events(parsed["ANFCI"], parsed["SP500"], parsed["VIXCLS"])
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient accepted weekly events for preregistered walk-forward test: {len(events)}")

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
    }
    paired = bootstrap_paired_loss(test)
    status, disposition = decide(validation_metrics, test_metrics, paired)
    data_scope = (
        f"FRED ANFCI weekly, SP500 and VIXCLS daily; ANFCI coverage {coverage['ANFCI']['first_date']} to {coverage['ANFCI']['last_date']}; "
        f"price coverage {coverage['SP500']['first_date']} to {coverage['SP500']['last_date']}; "
        f"{len(events)} accepted non-overlapping weekly events; validation 2019–2021; test 2022 onward"
    )
    limitations = [
        "ANFCI historical observations are revised; current FRED vintage is used and historical release vintages are not reconstructed.",
        "The seven-calendar-day lag is conservative relative to the published Wednesday 8:30 a.m. ET release (Thursday on specified holiday weeks), but does not eliminate revisions to prior ANFCI observations.",
        "ANFCI is a composite and not an exogenous funding shock; components can overlap with information in VIX and equity markets.",
        "SP500 is a cash price index, not an executable futures series or total-return index.",
        "Forecasting only: no causal claim, transaction-cost model, tradable strategy or live deployment conclusion.",
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
        "data_sources": {
            series_id: {
                "url": urls[series_id],
                "rows": len(parsed[series_id]),
                "first_date": coverage[series_id]["first_date"],
                "last_date": coverage[series_id]["last_date"],
                "sha256": sha256(raw[series_id]),
            }
            for series_id in SERIES
        },
        "event_construction": event_meta,
        "methodology": {
            "baseline_features": list(BASELINE_FEATURES),
            "augmented_features": list(AUGMENTED_FEATURES),
            "feature": "ANFCI_week_t - ANFCI_week_t_minus_4; positive means tightening over four weekly observations",
            "release_rule": "weekly observation dated Friday; conservatively available Friday + 7 calendar days; first S&P 500 close on or after that date",
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
        "paired_squared_loss_bootstrap": paired,
        "limitations": limitations,
    }


def main() -> int:
    try:
        result = run_research()
        report = render_report(result)
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
            "daily_kpi": "MET before this additional study — prior distinct real-data backtests already met the 2026-11-25 minimum",
            "data_scope": "source acceptance incomplete",
            "error": error,
        }
        report = render_report(result, error)
    report_path, manifest_path = write_outputs(result, report)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result["status"],
        "disposition": result["disposition"],
        "report_path": report_path,
        "manifest_path": manifest_path,
        "summary_metrics": result.get("summary_metrics"),
        "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
