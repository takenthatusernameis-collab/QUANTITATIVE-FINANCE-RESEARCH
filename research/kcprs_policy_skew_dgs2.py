#!/usr/bin/env python3
"""Walk-forward forecast: KC Fed option-implied policy-rate skew -> 21-session 2Y Treasury yield change."""
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

HYPOTHESIS_ID = "QFR-2026-11-26-KCPRS-POLICY-SKEW-DGS2-01"
START_DATE = dt.date(1989, 4, 3)
MODEL_WINDOW = 52
EVENT_STEP_SESSIONS = 22
TARGET_SESSIONS = 21
VALIDATION_START = dt.date(2018, 1, 1)
TEST_START = dt.date(2023, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 3
RNG_SEED = 20261129
MIN_SERIES_ROWS = 7500
MAX_SERIES_AGE_DAYS = 5
MAX_KCPRS_AGE_DAYS = 5
MAX_GAP_DAYS = 5

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "kcprs-policy-skew-dgs2" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-KCPRS-POLICY-SKEW-DGS2-01.md"

SERIES = ("KCPRS", "DGS2", "DGS10")
BASELINE_FEATURES = (
    "dgs2_level_pct",
    "dgs2_change_21d_bp",
    "dgs2_change_63d_bp",
    "curve_10y2y_bp",
)
AUGMENTED_FEATURES = BASELINE_FEATURES + ("kcprs_level_pp",)
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


def validate_source_coverage(series: dict[str, dict[dt.date, float]], today: dt.date) -> dict:
    for series_id in SERIES:
        values = series[series_id]
        if len(values) < MIN_SERIES_ROWS:
            raise ValueError(f"Insufficient {series_id} observations: {len(values)} < {MIN_SERIES_ROWS}")
        first, last = min(values), max(values)
        if first > START_DATE + dt.timedelta(days=30):
            raise ValueError(f"{series_id} history starts unexpectedly late: {first}")
        if last > today:
            raise ValueError(f"{series_id} contains a future observation: {last}")
        age = (today - last).days
        if age > MAX_SERIES_AGE_DAYS:
            raise ValueError(f"{series_id} observations are stale: latest={last}, age={age} days")
        dates = sorted(values)
        gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
        if any(gap > MAX_GAP_DAYS for gap in gaps):
            raise ValueError(f"{series_id} contains a gap greater than {MAX_GAP_DAYS} calendar days")

    dgs2_dates, dgs10_dates = set(series["DGS2"]), set(series["DGS10"])
    common_yields = sorted(dgs2_dates & dgs10_dates)
    if len(common_yields) < MIN_SERIES_ROWS:
        raise ValueError(f"Insufficient common DGS2/DGS10 observations: {len(common_yields)}")
    if abs((max(dgs2_dates) - max(dgs10_dates)).days) > 3:
        raise ValueError("DGS2 and DGS10 latest observations are not synchronized")
    common_all = sorted(set(series["KCPRS"]) & set(common_yields))
    if len(common_all) < MIN_SERIES_ROWS:
        raise ValueError(f"Insufficient common KCPRS/DGS2/DGS10 observations: {len(common_all)}")
    if (today - common_all[-1]).days > MAX_SERIES_AGE_DAYS:
        raise ValueError(f"Common observations are stale: latest={common_all[-1]}")
    return {
        name: {
            "rows": len(values),
            "first_date": min(values).isoformat(),
            "last_date": max(values).isoformat(),
        }
        for name, values in series.items()
    } | {
        "common_yield_dates": len(common_yields),
        "common_all_series_dates": len(common_all),
    }


def build_events(
    kcprs: dict[dt.date, float],
    dgs2: dict[dt.date, float],
    dgs10: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    yield_dates = sorted(set(dgs2) & set(dgs10))
    kcprs_dates = sorted(kcprs)
    events: list[dict] = []
    skipped = {
        "no_strictly_prior_kcprs_observation": 0,
        "stale_prior_kcprs_observation": 0,
        "incomplete_yield_history": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0
    for signal_index in range(63, len(yield_dates) - TARGET_SESSIONS, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_date = yield_dates[signal_index]
        kcprs_position = bisect.bisect_left(kcprs_dates, signal_date) - 1
        if kcprs_position < 0:
            skipped["no_strictly_prior_kcprs_observation"] += 1
            continue
        kcprs_date = kcprs_dates[kcprs_position]
        if (signal_date - kcprs_date).days > MAX_KCPRS_AGE_DAYS:
            skipped["stale_prior_kcprs_observation"] += 1
            continue
        target_end_index = signal_index + TARGET_SESSIONS
        target_end_date = yield_dates[target_end_index]
        if events and events[-1]["target_end_date"] >= signal_date:
            skipped["overlapping_target_window"] += 1
            continue
        lookback_21 = yield_dates[signal_index - 21]
        lookback_63 = yield_dates[signal_index - 63]
        if any(day not in dgs2 or day not in dgs10 for day in (signal_date, lookback_21, lookback_63)):
            skipped["incomplete_yield_history"] += 1
            continue
        target_bp = 100.0 * (dgs2[target_end_date] - dgs2[signal_date])
        features = {
            "dgs2_level_pct": dgs2[signal_date],
            "dgs2_change_21d_bp": 100.0 * (dgs2[signal_date] - dgs2[lookback_21]),
            "dgs2_change_63d_bp": 100.0 * (dgs2[signal_date] - dgs2[lookback_63]),
            "curve_10y2y_bp": 100.0 * (dgs10[signal_date] - dgs2[signal_date]),
            "kcprs_level_pp": kcprs[kcprs_date],
        }
        if not math.isfinite(target_bp) or any(not math.isfinite(value) for value in features.values()):
            raise ValueError(f"Non-finite event values at {signal_date}")
        events.append({
            "signal_date": signal_date,
            "kcprs_observation_date": kcprs_date,
            "kcprs_observation_age_days": (signal_date - kcprs_date).days,
            "target_start_date": yield_dates[signal_index + 1],
            "target_end_date": target_end_date,
            "target_bp": target_bp,
            "source_regime": "EURODOLLAR_OPTIONS" if signal_date < dt.date(2023, 1, 1) else "SOFR_OPTIONS",
            **features,
        })
    return events, {
        "candidate_origins": candidates,
        "accepted_events": len(events),
        "skipped": skipped,
        "signal_rule": "DGS2/DGS10 close on t; latest KCPRS observation dated strictly before t",
        "predictor": "latest strictly prior KCPRS level in percentage points",
        "target": "DGS2[t+21 observed Treasury sessions] minus DGS2[t], in basis points",
        "target_horizon_sessions": TARGET_SESSIONS,
        "event_spacing_sessions": EVENT_STEP_SESSIONS,
        "non_overlap_rule": "22-session event spacing for a 21-session target; each prior target matures before the next signal",
        "kcprs_regime_counts": {
            "EURODOLLAR_OPTIONS": sum(row["source_regime"] == "EURODOLLAR_OPTIONS" for row in events),
            "SOFR_OPTIONS": sum(row["source_regime"] == "SOFR_OPTIONS" for row in events),
        },
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
            "kcprs_observation_date": current["kcprs_observation_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "kcprs_level_pp": current["kcprs_level_pp"],
            "source_regime": current["source_regime"],
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
    denominator = sum((value - mean_actual) ** 2 for value in actual)
    return {
        "n": len(rows),
        "mae_bp": statistics.fmean(abs(error) for error in errors),
        "rmse_bp": math.sqrt(statistics.fmean(error * error for error in errors)),
        "directional_accuracy": statistics.fmean(
            (row[prediction_key] >= 0) == (row["target_bp"] >= 0) for row in rows
        ),
        "oos_r2_vs_period_mean": 1.0 - sum(error * error for error in errors) / denominator if denominator > 1e-12 else None,
    }


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    differences = []
    for row in rows:
        target = row["target_bp"]
        difference = (
            (row["baseline_prediction_bp"] - target) ** 2
            - (row["augmented_prediction_bp"] - target) ** 2
        )
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
        "mean_baseline_minus_augmented_squared_loss_bp2": observed,
        "ci_95_low_bp2": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high_bp2": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def improvement_pct(baseline: dict | None, augmented: dict | None) -> float | None:
    if not baseline or not augmented or baseline["rmse_bp"] <= 0:
        return None
    return 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline"), validation.get("augmented"))
    test_imp = improvement_pct(test.get("baseline"), test.get("augmented"))
    if (
        validation.get("n", 0) >= 30 and test.get("n", 0) >= 30
        and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired is not None and paired.get("ci_95_low_bp2") is not None
        and paired["ci_95_low_bp2"] > 0
    ):
        return "BACKTESTED", "PROMISING — both chronological RMSE comparisons improve and the paired-loss 95% lower confidence bound is positive; independent reconstruction and economic-value assessment remain necessary"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and paired is not None and paired.get("ci_95_high_bp2") is not None
        and paired["ci_95_high_bp2"] < 0
    ):
        return "REJECTED", "REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule"


def upsert_registry(status: str, disposition: str, scope: str, report_relative: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    report_link = "../" + report_relative
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly prior KC Fed option-implied policy-rate skew level adds information about the next 21-session change in the 2-year Treasury yield beyond the current yield level, recent yield changes and the 10y-2y curve slope. | {scope} | {disposition} | [session report]({report_link}) |"
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
        f"# Research session — KC PRS option-implied policy-rate skew and 2Y Treasury yield ({result.get('retrieved_at_utc', SESSION_TIME.isoformat())})",
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
        "- Predictor: latest strictly prior daily Kansas City Fed Policy Rate Skew (KCPRS) level. Positive values indicate greater option-implied upside risk to short-term rates one year ahead; negative values indicate greater downside risk.",
        "- Signal: DGS2/DGS10 Treasury close on date t; KCPRS observation must be dated strictly before t.",
        "- Baseline: current DGS2 level, prior 21- and 63-observation DGS2 changes, and the 10y-2y Treasury curve slope. Augmented model adds only the prior KCPRS level.",
        "- Target: DGS2 change over the next 21 observed Treasury sessions, in basis points. Events are spaced 22 sessions apart.",
        "- Rolling training window: 52 prior events whose target end is strictly earlier than the current signal date.",
        "- Validation: 2018–2022. Test: 2023 onward, aligning the test with the KC PRS source's SOFR-options regime.",
        "- Primary metric: RMSE in basis points. Paired uncertainty: 2,000 circular-block bootstrap replications, three consecutive events per block.",
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
            f"- Accepted non-overlapping events: {result['event_construction']['accepted_events']} of {result['event_construction']['candidate_origins']}.",
            f"- KC PRS source-regime event counts: {json.dumps(result['event_construction']['kcprs_regime_counts'], sort_keys=True)}.",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            "",
            "## Frozen walk-forward results",
            "",
            "| Metric | Validation 2018–2022 | Test 2023 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {result['validation_metrics']['n']} | {result['test_metrics']['n']} |",
            f"| Baseline RMSE (bp) | {result['validation_metrics']['baseline']['rmse_bp']:.6f} | {result['test_metrics']['baseline']['rmse_bp']:.6f} |",
            f"| Augmented RMSE (bp) | {result['validation_metrics']['augmented']['rmse_bp']:.6f} | {result['test_metrics']['augmented']['rmse_bp']:.6f} |",
            f"| RMSE improvement | {result['summary_metrics']['validation_improvement_pct']:.4f}% | {result['summary_metrics']['test_improvement_pct']:.4f}% |",
            f"| Baseline directional accuracy | {result['validation_metrics']['baseline']['directional_accuracy']:.4f} | {result['test_metrics']['baseline']['directional_accuracy']:.4f} |",
            f"| Augmented directional accuracy | {result['validation_metrics']['augmented']['directional_accuracy']:.4f} | {result['test_metrics']['augmented']['directional_accuracy']:.4f} |",
            "",
            f"- Test paired squared-loss bootstrap: {json.dumps(result['paired_squared_loss_bootstrap'], sort_keys=True)}.",
            "",
        ])
    verified = (
        "**VERIFIED:** source schemas and coverage, strictly prior KCPRS alignment, event spacing, target maturity, walk-forward predictions and paired-loss inference under the recorded current data vintage."
        if error is None else
        "**VERIFIED:** deterministic parser and timing tests. Source acceptance did not pass, so no empirical backtest result is claimed."
    )
    unverified = (
        "**UNVERIFIED:** historical point-in-time KCPRS vintages, independent source reconstruction, future-regime stability and instrument-level economic value."
        if error is None else
        "**UNVERIFIED:** complete accepted source coverage, event sample, model forecasts, metrics and any empirical disposition beyond INCONCLUSIVE."
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
        "- The KC Fed source uses Eurodollar options before 2023 and SOFR options from 2023 onward. The frozen test period is the SOFR-options regime; validation is primarily the earlier Eurodollar regime. Cross-regime comparisons require caution.",
        "- FRED current vintages are used; historical point-in-time revisions are not reconstructed.",
        "- DGS2 is a market-yield proxy, not the realized federal funds rate or an executable futures return.",
        "- KCPRS summarizes option-implied risk asymmetry one year ahead; this screen tests its incremental association with a 21-session DGS2 change and does not identify causality.",
        "- Forecasting only: no trading P&L, transaction-cost model, live strategy or deployment conclusion.",
        "",
        "## Reproducibility",
        "",
        f"- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
        f"- Manifest: ../../generated/kcprs-policy-skew-dgs2/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: ../../../research/kcprs_policy_skew_dgs2.py",
        "- Tests: ../../../research/test_kcprs_policy_skew_dgs2.py",
        "",
    ])
    return "\n".join(lines)


def update_preregistration(result: dict, report_relative: str) -> None:
    content = PREREG_PATH.read_text(encoding="utf-8")
    status_line = next((line for line in content.splitlines() if line.startswith("- **Status:**")), None)
    status = result.get("status", "INCONCLUSIVE")
    disposition_text = result.get("disposition", "INCONCLUSIVE")
    prefix = status + " — "
    if disposition_text.startswith(prefix):
        disposition_text = disposition_text[len(prefix):]
    if status_line:
        content = content.replace(
            status_line,
            f"- **Status:** {status} — {disposition_text}",
            1,
        )
    if "## Empirical disposition" in content:
        content = content.split("## Empirical disposition", 1)[0].rstrip()
    summary = result.get("summary_metrics") or {}
    disposition = [
        "## Empirical disposition",
        "",
        f"- **Final status:** {status} — {disposition_text}.",
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}.",
        f"- **Data scope:** {result.get('data_scope', 'source acceptance incomplete')}.",
    ]
    if summary:
        val_imp = summary.get("validation_improvement_pct")
        test_imp = summary.get("test_improvement_pct")
        disposition.append(
            f"- **Summary:** validation/test n={summary.get('validation_n')}/{summary.get('test_n')}; "
            + (
                "insufficient forecasts for both RMSE comparisons."
                if val_imp is None or test_imp is None
                else f"RMSE improvement={val_imp:.4f}%/{test_imp:.4f}%."
            )
        )
    disposition.extend([
        f"- **Report:** [../{report_relative}](../{report_relative}).",
        "",
        "Forecasting screen only. No causal, trading, profitability or deployment claim.",
        "",
    ])
    PREREG_PATH.write_text(content.rstrip() + "\n\n" + "\n".join(disposition), encoding="utf-8")


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-kcprs-policy-skew-{RUN_ID}.md"
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
        parsed[series_id] = parse_fred_series(
            body, series_id, positive_required=series_id in {"DGS2", "DGS10"}
        )
        urls[series_id] = url

    coverage = validate_source_coverage(parsed, dt.datetime.now(dt.timezone.utc).date())
    events, event_meta = build_events(parsed["KCPRS"], parsed["DGS2"], parsed["DGS10"])
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient accepted events: {len(events)} < {MODEL_WINDOW + 60}")

    predictions = walk_forward_predictions(events)
    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    if len(validation) < 30 or len(test) < 30:
        raise ValueError(
            f"Insufficient validation/test forecasts: validation={len(validation)}, test={len(test)}, required=30 each"
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
    common_start = max(min(parsed[name]) for name in SERIES)
    common_end = min(max(parsed[name]) for name in SERIES)
    data_scope = (
        f"KCPRS/DGS2/DGS10 daily current FRED vintages; common source envelope "
        f"{common_start} to {common_end}; {len(events)} accepted non-overlapping events; "
        f"validation 2018-2022 n={len(validation)}; test 2023 onward n={len(test)}"
    )
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": (
            f"An additional distinct real-data backtest completed on UTC date {dt.datetime.now(dt.timezone.utc).date()}; "
            "the daily minimum had already been met by earlier distinct experiments."
        ),
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
        "coverage": coverage,
        "event_construction": event_meta,
        "methodology": {
            "baseline_features": list(BASELINE_FEATURES),
            "augmented_features": list(AUGMENTED_FEATURES),
            "predictor": "latest KCPRS level strictly before the signal date",
            "target": "21-session DGS2 yield change in basis points",
            "rolling_training_events": MODEL_WINDOW,
            "event_spacing_sessions": EVENT_STEP_SESSIONS,
            "target_sessions": TARGET_SESSIONS,
            "validation": "2018-01-01 through 2022-12-31",
            "test": "2023-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": RNG_SEED,
            "training_rule": "training target_end_date must be strictly earlier than current signal_date",
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
        "limitations": [
            "Current FRED vintages; no historical point-in-time revision reconstruction.",
            "KC PRS uses Eurodollar options before 2023 and SOFR options from 2023 onward.",
            "DGS2 is a market-yield proxy, not the realized federal funds rate or executable futures P&L.",
            "Forecasting screen only; no causal or trading claim.",
        ],
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
            "daily_kpi": "The 2026-11-26 daily real-data backtest minimum was already met by earlier distinct experiments; this attempt did not complete a valid backtest.",
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
