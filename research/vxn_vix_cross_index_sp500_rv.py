#!/usr/bin/env python3
"""Walk-forward forecast screen: lagged Nasdaq-versus-S&P implied-volatility premium -> S&P 500 realized volatility."""
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

HYPOTHESIS_ID = "QFR-2026-11-26-VXN-VIX-CROSS-INDEX-SP500-RV-01"
START_DATE = dt.date(2016, 11, 25)
MODEL_WINDOW = 104
EVENT_STEP_SESSIONS = 6
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
RNG_SEED = 20261128
MIN_VOL_ROWS = 1500
MIN_PRICE_ROWS = 1500
MAX_VOL_AGE_DAYS = 5
MAX_PRICE_AGE_DAYS = 8

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "vxn-vix-cross-index-sp500-rv" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-VXN-VIX-CROSS-INDEX-SP500-RV-01.md"

SERIES = ("VXNCLS", "VIXCLS", "SP500")
BASELINE_FEATURES = ("pre_rv5_log", "pre_rv20_log", "log_vix")
AUGMENTED_FEATURES = BASELINE_FEATURES + ("vxn_vix_5obs_change",)
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
    for series_id in SERIES:
        values = series[series_id]
        minimum = MIN_PRICE_ROWS if series_id == "SP500" else MIN_VOL_ROWS
        if len(values) < minimum:
            raise ValueError(f"Insufficient {series_id} observations: {len(values)} < {minimum}")
        first, last = min(values), max(values)
        if first > START_DATE + dt.timedelta(days=30):
            raise ValueError(f"{series_id} history starts unexpectedly late: {first}")
        if last > today:
            raise ValueError(f"{series_id} contains a future observation: {last}")

    vxn_dates, vix_dates = set(series["VXNCLS"]), set(series["VIXCLS"])
    common_vol = sorted(vxn_dates & vix_dates)
    if len(common_vol) < MIN_VOL_ROWS:
        raise ValueError(f"Insufficient common VXN/VIX observations: {len(common_vol)}")
    if common_vol[0] > START_DATE + dt.timedelta(days=30):
        raise ValueError(f"Common VXN/VIX history starts unexpectedly late: {common_vol[0]}")
    if abs((max(vxn_dates) - max(vix_dates)).days) > 3:
        raise ValueError("VXN and VIX latest observations are not synchronized")
    vol_last = common_vol[-1]
    if (today - vol_last).days > MAX_VOL_AGE_DAYS:
        raise ValueError(
            f"VXN/VIX common observations are stale: latest={vol_last}, "
            f"age={(today - vol_last).days} days"
        )
    vol_gaps = [(b - a).days for a, b in zip(common_vol, common_vol[1:])]
    if any(gap > 5 for gap in vol_gaps):
        raise ValueError("VXN/VIX common observations contain a gap greater than five calendar days")

    prices = series["SP500"]
    price_last = max(prices)
    if abs((price_last - max(vix_dates)).days) > 4:
        raise ValueError("FRED SP500 and VIXCLS latest observations are not synchronized")
    common_price_end = min(price_last, max(vix_dates))
    if (today - common_price_end).days > MAX_PRICE_AGE_DAYS:
        raise ValueError(f"FRED price data are stale: common end {common_price_end}")

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
    vxn: dict[dt.date, float],
    vix: dict[dt.date, float],
    prices: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    price_dates, returns = daily_log_returns(prices)
    vol_dates = sorted(set(vxn) & set(vix))
    log_ratio = {day: math.log(vxn[day] / vix[day]) for day in vol_dates}
    events: list[dict] = []
    skipped = {
        "incomplete_price_window": 0,
        "missing_vix_on_signal_date": 0,
        "no_strictly_prior_common_vol_observation": 0,
        "stale_common_vol_observation": 0,
        "insufficient_five_observation_vol_history": 0,
        "irregular_vol_observation_window": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0
    for signal_index in range(20, len(price_dates) - TARGET_SESSIONS, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_date = price_dates[signal_index]
        vol_position = bisect.bisect_left(vol_dates, signal_date) - 1
        if vol_position < 0:
            skipped["no_strictly_prior_common_vol_observation"] += 1
            continue
        vol_date = vol_dates[vol_position]
        if (signal_date - vol_date).days > MAX_VOL_AGE_DAYS:
            skipped["stale_common_vol_observation"] += 1
            continue
        if vol_position < 5:
            skipped["insufficient_five_observation_vol_history"] += 1
            continue
        feature_window = vol_dates[vol_position - 5:vol_position + 1]
        if any((b - a).days > 5 for a, b in zip(feature_window, feature_window[1:])):
            skipped["irregular_vol_observation_window"] += 1
            continue
        if signal_date not in vix:
            skipped["missing_vix_on_signal_date"] += 1
            continue
        try:
            pre_rv5 = realized_volatility(returns[signal_index - 4:signal_index + 1])
            pre_rv20 = realized_volatility(returns[signal_index - 19:signal_index + 1])
            target_rv = realized_volatility(returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1])
        except ValueError:
            skipped["incomplete_price_window"] += 1
            continue
        target_end = price_dates[signal_index + TARGET_SESSIONS]
        if events and signal_date <= events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        feature = log_ratio[vol_date] - log_ratio[feature_window[0]]
        if not math.isfinite(feature):
            raise ValueError(f"Non-finite VXN/VIX log-ratio change at {signal_date}")
        events.append({
            "signal_date": signal_date,
            "vol_observation_date": vol_date,
            "vol_feature_start_date": feature_window[0],
            "target_start_date": price_dates[signal_index + 1],
            "target_end_date": target_end,
            "vxn_vix_5obs_change": feature,
            "vxn_vix_log_ratio": log_ratio[vol_date],
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "log_vix": math.log(vix[signal_date]),
            "target_rv_pct": target_rv,
            "target_bp": math.log1p(target_rv),
        })
    return events, {
        "candidate_origins": candidates,
        "accepted_events": len(events),
        "skipped": skipped,
        "signal_rule": "S&P 500 close on t; latest common VXN/VIX observation dated strictly before t",
        "spread_feature": "log(VXN/VIX)[d] - log(VXN/VIX)[d-5], where d is the latest common date strictly before t",
        "vol_observation_lag": "strictly prior common date; no same-date VXN/VIX values are used",
        "event_spacing_sp500_observations": EVENT_STEP_SESSIONS,
        "target_sessions": TARGET_SESSIONS,
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
            "signal_date": current["signal_date"],
            "vol_observation_date": current["vol_observation_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_rv_pct": current["target_rv_pct"],
            "vxn_vix_5obs_change": current["vxn_vix_5obs_change"],
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
    report_link = "../" + report_relative
    status_label = format_status_label(result)
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged five-observation increase in the Nasdaq-100 versus S&P 500 implied-volatility ratio adds information about next-five-session S&P 500 realized volatility beyond recent realized volatility and VIX. | {scope} | {disposition} | [session report]({report_link}) |"
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
        f"# Research session — VXN/VIX cross-index implied-volatility spread and S&P 500 realized volatility ({result.get('retrieved_at_utc', SESSION_TIME.isoformat())})",
        "",
        f"- Hypothesis: {HYPOTHESIS_ID}",
        f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'INCONCLUSIVE')}",
        f"- Daily real-data backtest KPI: {result.get('daily_kpi', 'not met by this study')}",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}",
        f"- Triggering commit: {SOURCE_SHA}",
        "",
        "## Preregistered mechanism and method",
        "",
        "- Predictor: five-observation change in log(VXN/VIX), where VXN is Nasdaq-100 implied volatility and VIX is S&P 500 implied volatility. A positive change means the options market repriced Nasdaq-100 risk upward relative to broad S&P 500 risk.",
        "- Signal: S&P 500 close on date t; use only the latest common VXN/VIX observation dated strictly before t.",
        "- Baseline: prior-five and prior-twenty-session S&P 500 realized volatility plus signal-date log VIX. Augmented model adds only the lagged five-observation VXN/VIX log-ratio change.",
        "- Target: next-five-session S&P 500 realized volatility; event origins are spaced six S&P 500 observations apart.",
        "- Rolling training window: 104 prior events whose target end is strictly earlier than the current signal date.",
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
            f"- Accepted non-overlapping events: {result['event_construction']['accepted_events']} of {result['event_construction']['candidate_origins']} candidate S&P 500 origins.",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- Paired test squared-loss bootstrap: {json.dumps(result['paired_squared_loss_bootstrap'], sort_keys=True)}.",
            "",
        ])
    verified = (
        "**VERIFIED:** deterministic parser, timing, prior-observation, event-maturity and decision tests; FRED source schema and coverage acceptance; exact-date VIX alignment; no same-date VXN/VIX observations; non-overlapping target windows; and the recorded result under this code/data vintage."
        if error is None else
        "**VERIFIED:** deterministic code and timing tests. Actual source acceptance did not pass, so no real-data backtest result is claimed."
    )
    unverified = (
        "**UNVERIFIED:** historical point-in-time CBOE index vintages, future-regime stability, independent source reconstruction and instrument-level economic value."
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
        "- VXN and VIX are both option-implied indices, but they reference different underlyings and sector compositions; the ratio can reflect Nasdaq concentration rather than a pure volatility spillover.",
        "- The strict prior-date rule avoids same-date publication ambiguity but does not reconstruct intraday historical dissemination timestamps or later revisions.",
        "- FRED observations are current vintages; historical point-in-time revisions are not reconstructed.",
        "- SP500 is a cash price index, not an executable futures series or total-return index.",
        "- No raw source data are committed; only retrieval metadata, hashes and aggregate metrics are retained.",
        "- Forecasting only: no causal claim, trading P&L, transaction-cost model, live strategy or deployment conclusion.",
        "",
        "## Reproducibility",
        "",
        f"- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
        f"- Manifest: ../../generated/vxn-vix-cross-index-sp500-rv/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: ../../../research/vxn_vix_cross_index_sp500_rv.py",
        "- Tests: ../../../research/test_vxn_vix_cross_index_sp500_rv.py",
    ])
    return "\n".join(lines) + "\n"


def format_status_label(result: dict) -> str:
    status = str(result.get("status") or "INCONCLUSIVE").strip()
    disposition = str(result.get("disposition") or "INCONCLUSIVE").strip()
    if disposition == status or disposition.startswith(status + " —"):
        return disposition
    return f"{status} — {disposition}"


def update_preregistration(result: dict, report_relative: str) -> None:
    content = PREREG_PATH.read_text(encoding="utf-8")
    report_link = "../" + report_relative
    status_line = next((line for line in content.splitlines() if line.startswith("- **Status:**")), None)
    if status_line is not None:
        content = content.replace(
            status_line,
            f"- **Status:** {status_label}",
            1,
        )
    if "## Empirical disposition" in content:
        content = content.split("## Empirical disposition", 1)[0].rstrip()
    summary = result.get("summary_metrics") or {}
    disposition = [
        "## Empirical disposition",
        "",
        f"- **Final status:** {status_label.rstrip().rstrip('.')}.",
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}.",
        f"- **Data scope:** {result.get('data_scope', 'source acceptance incomplete')}.",
    ]
    if summary:
        validation_improvement = summary.get("validation_improvement_pct")
        test_improvement = summary.get("test_improvement_pct")
        if validation_improvement is None or test_improvement is None:
            disposition.append(
                f"- **Summary:** validation/test n={summary.get('validation_n')}/{summary.get('test_n')}; "
                "insufficient forecasts for both RMSE comparisons."
            )
        else:
            disposition.append(
                f"- **Summary:** validation/test n={summary.get('validation_n')}/{summary.get('test_n')}; "
                f"RMSE improvement={validation_improvement:.4f}%/{test_improvement:.4f}%."
            )
    disposition.extend([
        f"- **Report:** [{report_link}]({report_link}).",
        "",
        "Forecasting screen only. No causal, trading, profitability or deployment claim.",
        "",
    ])
    PREREG_PATH.write_text(content.rstrip() + "\n\n" + "\n".join(disposition), encoding="utf-8")


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-vxn-vix-cross-index-{RUN_ID}.md"
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
    update_preregistration(result, relative_report)
    return str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))


def run_research() -> dict:
    raw: dict[str, bytes] = {}
    parsed: dict[str, dict[dt.date, float]] = {}
    urls: dict[str, str] = {}
    for series_id in SERIES:
        url = f"{FRED_URL}?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url, timeout=25)
        raw[series_id] = body
        parsed[series_id] = parse_fred_series(body, series_id, positive_required=True)
        urls[series_id] = url

    coverage = validate_source_coverage(parsed, dt.datetime.now(dt.timezone.utc).date())
    events, event_meta = build_events(parsed["VXNCLS"], parsed["VIXCLS"], parsed["SP500"])
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient accepted events for preregistered walk-forward test: {len(events)}")

    predictions = walk_forward_predictions(events)
    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    if len(validation) < 30 or len(test) < 30:
        raise ValueError(
            f"Insufficient validation/test forecasts for the frozen decision rule: "
            f"validation={len(validation)}, test={len(test)}, required=30 each"
        )
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
        f"FRED VXNCLS/VIXCLS daily from {coverage['VXNCLS']['first_date']} to {coverage['VXNCLS']['last_date']} "
        f"(common end {min(coverage['VXNCLS']['last_date'], coverage['VIXCLS']['last_date'])}); "
        f"SP500 {coverage['SP500']['first_date']} to {coverage['SP500']['last_date']}; "
        f"{len(events)} accepted non-overlapping six-session-spaced events; validation 2019-2021; test 2022 onward"
    )
    limitations = [
        "VXN and VIX are current FRED vintages; historical point-in-time CBOE dissemination and later revisions are not reconstructed.",
        "VXN measures Nasdaq-100 implied volatility while VIX measures S&P 500 implied volatility; their ratio can reflect sector concentration, index composition and relative option demand rather than a pure spillover shock.",
        "The strict prior-date rule avoids same-date publication look-ahead but does not reconstruct intraday historical publication timestamps.",
        "The baseline controls for broad VIX level and recent S&P 500 realized volatility, but not every cross-index or sector-specific risk factor.",
        "SP500 is a cash price index, not an executable futures series or total-return index.",
        "Forecasting only: no causal claim, transaction-cost model, tradable strategy or live-deployment conclusion.",
        "No raw source data are committed; only URLs, retrieval metadata, hashes and aggregate metrics are retained.",
    ]
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": f"This distinct real-data backtest completed on UTC date {dt.datetime.now(dt.timezone.utc).date()}; the 2026-11-26 minimum was already met by the earlier STLFSI4 and SOFR-EFFR real-data backtests.",
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
            "feature": "log(VXN/VIX)[d] - log(VXN/VIX)[d-5]; d is the latest common VXN/VIX observation strictly before the signal date",
            "availability": "VXN and VIX are used only from their latest common date strictly before the signal date",
            "rolling_training_events": MODEL_WINDOW,
            "event_spacing_sp500_observations": EVENT_STEP_SESSIONS,
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
            "completed_backtest": False,
            "disposition": f"INCONCLUSIVE — bounded source or execution failure: {error}",
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "The 2026-11-26 daily minimum was already met by two earlier real-data backtests; this additional attempt did not complete a valid backtest.",
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
