#!/usr/bin/env python3
"""Preregistered walk-forward test of Treasury yield-curve volatility and S&P 500 realized volatility."""
from __future__ import annotations

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

HYPOTHESIS_ID = "QFR-2026-11-25-TREASURY-CURVE-VOL-SP500-RV-01"
SERIES = ("SP500", "VIXCLS", "T10Y3M")
START_DATE = dt.date(2016, 11, 25)
MODEL_WINDOW = 104
EVENT_STEP_SESSIONS = 6
TARGET_SESSIONS = 5
CURVE_WINDOW_CHANGES = 20
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261128

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "treasury-curve-volatility" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"

BASELINE_FEATURES = ["pre_rv5_log", "pre_rv20_log", "log_vix"]
AUGMENTED_FEATURES = BASELINE_FEATURES + ["curve_rv20_log"]


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def parse_fred_series(body: bytes, series_id: str, positive_required: bool = True) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED {series_id} CSV schema: {reader.fieldnames}")
    date_field = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_field is None:
        raise ValueError(f"FRED {series_id} CSV has no recognized date column")
    values: dict[dt.date, float] = {}
    seen_dates: set[dt.date] = set()
    for row in reader:
        observation_date = base.parse_date(row.get(date_field))
        if observation_date is None:
            continue
        if observation_date in seen_dates:
            raise ValueError(f"Duplicate {series_id} observation date: {observation_date}")
        seen_dates.add(observation_date)
        value = base.parse_float(row.get(series_id))
        if value is None:
            continue
        if positive_required and value <= 0:
            raise ValueError(f"Non-positive {series_id} observation on {observation_date}")
        values[observation_date] = value
    if len(values) < 1500:
        raise ValueError(f"Insufficient {series_id} observations: {len(values)}")
    ordered = dict(sorted(values.items()))
    if next(iter(ordered)) > dt.date(2017, 3, 1):
        raise ValueError(f"{series_id} history starts unexpectedly late: {next(iter(ordered))}")
    return ordered


def validate_source_coverage(series: dict[str, dict[dt.date, float]]) -> dict:
    coverage = {}
    for series_id, values in series.items():
        dates = sorted(values)
        coverage[series_id] = {
            "rows": len(values),
            "first_date": dates[0].isoformat(),
            "last_date": dates[-1].isoformat(),
        }
    latest = [max(values) for values in series.values()]
    if (max(latest) - min(latest)).days > 4:
        raise ValueError(f"Source histories do not reach a common recent date: {coverage}")
    if min(latest) < dt.date(2026, 11, 17):
        raise ValueError(f"At least one source is unexpectedly stale: {coverage}")
    return coverage


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


def curve_realized_variation(
    curve: dict[dt.date, float],
    signal_date: dt.date,
) -> tuple[float | None, dt.date | None, str | None]:
    """Return 20-change root-sum-square in bp using only curve dates strictly before signal_date."""
    eligible = [date for date in sorted(curve) if date < signal_date]
    if not eligible:
        return None, None, "no_strictly_prior_curve_observation"
    latest = eligible[-1]
    if (signal_date - latest).days > 4:
        return None, latest, "stale_curve_observation"
    window_dates = eligible[-(CURVE_WINDOW_CHANGES + 1):]
    if len(window_dates) < CURVE_WINDOW_CHANGES + 1:
        return None, latest, "insufficient_curve_history"
    if (window_dates[-1] - window_dates[0]).days > 35:
        return None, latest, "curve_window_too_wide"
    gaps = [(right - left).days for left, right in zip(window_dates, window_dates[1:])]
    if any(gap > 4 for gap in gaps):
        return None, latest, "curve_observation_gap"
    changes_bp = [
        100.0 * (curve[right] - curve[left])
        for left, right in zip(window_dates, window_dates[1:])
    ]
    value = math.sqrt(sum(change * change for change in changes_bp))
    if not math.isfinite(value) or value < 0:
        return None, latest, "invalid_curve_variation"
    return value, latest, None


def build_events(
    prices: dict[dt.date, float],
    vix: dict[dt.date, float],
    curve: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    dates, returns = daily_log_returns(prices)
    events = []
    skipped = {
        "missing_vix_on_signal_date": 0,
        "no_strictly_prior_curve_observation": 0,
        "stale_curve_observation": 0,
        "insufficient_curve_history": 0,
        "curve_window_too_wide": 0,
        "curve_observation_gap": 0,
        "invalid_curve_variation": 0,
        "incomplete_pre_return_window": 0,
        "incomplete_future_return_window": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0
    # Use the signal-date VIX close and only a strictly prior Treasury-spread observation.
    # The target begins on the next S&P 500 session.
    for target_start_index in range(21, len(dates) - TARGET_SESSIONS + 1, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_index = target_start_index - 1
        signal_date = dates[signal_index]
        if signal_date not in vix:
            skipped["missing_vix_on_signal_date"] += 1
            continue
        curve_rv, curve_date, curve_error = curve_realized_variation(curve, signal_date)
        if curve_error:
            skipped[curve_error] += 1
            continue
        pre_5 = returns[signal_index - 4:signal_index + 1]
        pre_20 = returns[signal_index - 19:signal_index + 1]
        future = returns[target_start_index:target_start_index + TARGET_SESSIONS]
        try:
            pre_rv5 = realized_volatility(pre_5)
            pre_rv20 = realized_volatility(pre_20)
        except ValueError:
            skipped["incomplete_pre_return_window"] += 1
            continue
        try:
            target_rv = realized_volatility(future)
        except ValueError:
            skipped["incomplete_future_return_window"] += 1
            continue
        vix_value = vix[signal_date]
        if vix_value <= 0:
            raise ValueError(f"Invalid VIX value on {signal_date}")
        event = {
            "signal_date": signal_date,
            "target_start_date": dates[target_start_index],
            "target_end_date": dates[target_start_index + TARGET_SESSIONS - 1],
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "log_vix": math.log(vix_value),
            "curve_rv20_bp": curve_rv,
            "curve_rv20_log": math.log1p(curve_rv),
            "curve_source_date": curve_date,
            "curve_source_age_days": (signal_date - curve_date).days,
            "target_rv_pct": target_rv,
            "target_bp": math.log1p(target_rv),
        }
        if events and event["target_start_date"] <= events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        events.append(event)
    return events, {
        "candidate_origins": candidates,
        "events": len(events),
        "skipped": skipped,
        "event_spacing_sessions": EVENT_STEP_SESSIONS,
        "target_sessions": TARGET_SESSIONS,
        "curve_window_changes": CURVE_WINDOW_CHANGES,
        "signal_rule": "signal-date VIX close; latest T10Y3M observation strictly before signal date; target begins next S&P 500 session",
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
            baseline = base.fit_ols_predict(train, current, BASELINE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUGMENTED_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_rv_pct": current["target_rv_pct"],
            "curve_rv20_bp": current["curve_rv20_bp"],
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
    rng = random.Random(BOOTSTRAP_SEED)
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
        f"| {HYPOTHESIS_ID} | {status} | Strictly lagged 20-observation realized variation of the 10-year-minus-3-month Treasury spread adds information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and VIX level. | {scope} | {disposition} | [session report]({report_relative}) |"
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
        f"# Research session — {result.get('retrieved_at_utc', SESSION_TIME.isoformat())}",
        "",
        f"## {HYPOTHESIS_ID}",
        "",
        f"**Disposition: {result.get('disposition', 'INCONCLUSIVE')}**",
        "",
        "### Selection and scope",
        "",
        "- The hypothesis tests Treasury yield-curve volatility, not VIX/VXV option-implied term structure or Treasury auction microstructure.",
        "- The same-day research KPI had already been met by earlier distinct real-data backtests; this is an additional preregistered experiment.",
        "- Research/paper simulation only. No live orders, capital deployment, paid data or credentials.",
        "",
    ]
    if error:
        lines.extend(["### Execution / feasibility blocker", "", error, ""])
    else:
        lines.extend([
            "### Source coverage",
            "",
            "| Series | First date | Last date | Rows | SHA-256 |",
            "|---|---|---:|---:|---|",
        ])
        for series_id, source in result["data_sources"].items():
            lines.append(
                f"| {series_id} | {source['first_date']} | {source['last_date']} | {source['rows']} | {source['sha256']} |"
            )
        lines.extend([
            "",
            "### Frozen walk-forward results",
            "",
            "| Metric | Validation | Test |",
            "|---|---:|---:|",
            f"| Forecasts | {result['validation_metrics']['n']} | {result['test_metrics']['n']} |",
            f"| Baseline RMSE (log1p RV) | {result['validation_metrics']['baseline']['rmse_log1p_rv']:.8f} | {result['test_metrics']['baseline']['rmse_log1p_rv']:.8f} |",
            f"| Augmented RMSE (log1p RV) | {result['validation_metrics']['augmented']['rmse_log1p_rv']:.8f} | {result['test_metrics']['augmented']['rmse_log1p_rv']:.8f} |",
            f"| RMSE improvement | {result['summary_metrics']['validation_improvement_pct']:.4f}% | {result['summary_metrics']['test_improvement_pct']:.4f}% |",
            "",
            f"- Accepted non-overlapping events: {result['event_construction']['events']} of {result['event_construction']['candidate_origins']} candidate origins.",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- Paired test squared-loss bootstrap: {json.dumps(result['paired_squared_loss_bootstrap'], sort_keys=True)}.",
            "",
        ])
    lines.extend([
        "### Verified versus unverified",
        "",
        "**VERIFIED:** deterministic tests, source schema and coverage acceptance, strict prior-date curve alignment, no forward-fill, gap handling, non-overlapping targets, fully matured training targets and the recorded result under this code/data vintage.",
        "",
        "**UNVERIFIED:** historical point-in-time FRED vintages, causal transmission, stability in future regimes, independent source reconstruction and instrument-level economic value.",
        "",
        "### Next action",
        "",
        "- If BACKTESTED, require independent reconstruction and a separately preregistered instrument-level economic study.",
        "- If REJECTED or INCONCLUSIVE, close under the frozen decision rule; do not tune this hypothesis ID.",
        "- No automatic timebox extension.",
        "",
        "## Reproducibility",
        "",
        f"- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
        f"- Manifest: reports/generated/treasury-curve-volatility/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        f"- Source: research/treasury_curve_volatility_sp500.py",
        f"- Tests: research/test_treasury_curve_volatility_sp500.py",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-treasury-curve-volatility-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    relative_report = str(report_path.relative_to(ROOT))
    upsert_registry(
        result["status"],
        result["disposition"],
        result.get("data_scope", "source acceptance incomplete"),
        relative_report,
    )
    return str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))


def run_research() -> dict:
    raw = {}
    parsed = {}
    urls = {}
    for series_id in SERIES:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url, timeout=25)
        raw[series_id] = body
        parsed[series_id] = parse_fred_series(body, series_id, positive_required=series_id != "T10Y3M")
        urls[series_id] = url

    coverage = validate_source_coverage(parsed)
    events, event_meta = build_events(parsed["SP500"], parsed["VIXCLS"], parsed["T10Y3M"])
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
    }
    paired = bootstrap_paired_loss(test)
    status, disposition = decide(validation_metrics, test_metrics, paired)

    data_scope = (
        f"FRED SP500, VIXCLS and T10Y3M daily; aligned price coverage "
        f"{coverage['SP500']['first_date']} to {coverage['SP500']['last_date']}; "
        f"{len(events)} non-overlapping six-session-spaced origins; validation 2019–2021; test 2022 onward"
    )
    limitations = [
        "SP500 is a cash price index, not an executable futures series or total-return index.",
        "T10Y3M is a constructed daily Treasury spread, not a directly traded instrument.",
        "The latest T10Y3M observation strictly before each signal date is used; same-date values are excluded.",
        "The 20-observation curve variation is a simple daily root-sum-square, not the exact term-structure-volatility model in the cited literature.",
        "FRED current-vintage observations were used; historical release vintages were not reconstructed.",
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
            "baseline_features": BASELINE_FEATURES,
            "augmented_features": AUGMENTED_FEATURES,
            "curve_feature": "sqrt(sum of squared 20 daily T10Y3M changes in basis points), using 21 observations strictly before the S&P 500 signal date",
            "curve_feature_transform": "log1p(curve_rv20_bp)",
            "rolling_training_events": MODEL_WINDOW,
            "event_spacing_sessions": EVENT_STEP_SESSIONS,
            "target_sessions": TARGET_SESSIONS,
            "target": "log1p(next-five-session S&P 500 realized volatility in percent)",
            "training_rule": "training target_end_date must be strictly earlier than current signal_date",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
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
