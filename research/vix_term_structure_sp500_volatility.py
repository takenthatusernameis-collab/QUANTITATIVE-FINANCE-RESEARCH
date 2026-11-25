#!/usr/bin/env python3
"""Preregistered walk-forward test of VIX term-structure slope and S&P 500 realized volatility."""
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

HYPOTHESIS_ID = "QFR-2026-11-25-VIX-TERM-STRUCTURE-SP500-RV-01"
SERIES = ("SP500", "VIXCLS", "VXVCLS")
START_DATE = dt.date(2016, 11, 25)
MODEL_WINDOW = 104
EVENT_STEP_SESSIONS = 6
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
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
REPORT_PATH = SESSION_DIR / f"{STAMP}_session-wakeup-7-vix-term-structure-{RUN_ID}.md"
OUTPUT_DIR = ROOT / "reports" / "generated" / "vix-term-structure" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"

BASELINE_FEATURES = ["pre_rv5_log", "pre_rv20_log", "log_vix"]
AUGMENTED_FEATURES = BASELINE_FEATURES + ["term_slope"]


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def parse_fred_series(body: bytes, series_id: str) -> dict[dt.date, float]:
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
        if value <= 0:
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


def build_events(
    prices: dict[dt.date, float],
    vix: dict[dt.date, float],
    vxv: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    dates, returns = daily_log_returns(prices)
    events = []
    skipped = {
        "missing_vix_on_signal_date": 0,
        "missing_vxv_on_signal_date": 0,
        "incomplete_pre_return_window": 0,
        "incomplete_future_return_window": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0
    # Signal at the prior S&P session close; target begins on the next session.
    # Six-session spacing leaves a strict maturity gap between adjacent five-session targets.
    for target_start_index in range(21, len(dates) - TARGET_SESSIONS + 1, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_index = target_start_index - 1
        signal_date = dates[signal_index]
        if signal_date not in vix:
            skipped["missing_vix_on_signal_date"] += 1
            continue
        if signal_date not in vxv:
            skipped["missing_vxv_on_signal_date"] += 1
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
        vxv_value = vxv[signal_date]
        if vix_value <= 0 or vxv_value <= 0:
            raise ValueError(f"Invalid option-implied volatility value on {signal_date}")
        slope = math.log(vix_value / vxv_value)
        event = {
            "signal_date": signal_date,
            "target_start_date": dates[target_start_index],
            "target_end_date": dates[target_start_index + TARGET_SESSIONS - 1],
            "pre_rv5_log": math.log1p(pre_rv5),
            "pre_rv20_log": math.log1p(pre_rv20),
            "log_vix": math.log(vix_value),
            "term_slope": slope,
            "vix": vix_value,
            "vxv": vxv_value,
            "inverted": vix_value >= vxv_value,
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
        "signal_rule": "VIX/VXV and pre-event RV observed at prior S&P 500 close; target begins next S&P 500 session",
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
            "term_slope": current["term_slope"],
            "inverted": current["inverted"],
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


def bootstrap_inversion_difference(rows: list[dict]) -> dict | None:
    high_n = sum(row["inverted"] for row in rows)
    other_n = len(rows) - high_n
    if len(rows) < 30 or high_n < 5 or other_n < 5:
        return None
    high = [row["target_rv_pct"] for row in rows if row["inverted"]]
    other = [row["target_rv_pct"] for row in rows if not row["inverted"]]
    observed = statistics.fmean(high) - statistics.fmean(other)
    rng = random.Random(RNG_SEED + 2)
    differences = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(rows, rng, BOOTSTRAP_BLOCK)
        sample_high = [row["target_rv_pct"] for row in sample if row["inverted"]]
        sample_other = [row["target_rv_pct"] for row in sample if not row["inverted"]]
        if sample_high and sample_other:
            differences.append(statistics.fmean(sample_high) - statistics.fmean(sample_other))
    if len(differences) < BOOTSTRAP_REPS // 2:
        return None
    differences.sort()
    return {
        "high_inversion_n": high_n,
        "contango_n": other_n,
        "mean_high_inversion_rv_pct": statistics.fmean(high),
        "mean_contango_rv_pct": statistics.fmean(other),
        "high_minus_contango_mean_rv_pct": observed,
        "reps": len(differences),
        "block_size_events": BOOTSTRAP_BLOCK,
        "ci_95_low_rv_pct": differences[int(0.025 * (len(differences) - 1))],
        "ci_95_high_rv_pct": differences[int(0.975 * (len(differences) - 1))],
    }


def improvement_pct(baseline: dict | None, augmented: dict | None) -> float | None:
    if not baseline or not augmented or baseline["rmse_log1p_rv"] <= 0:
        return None
    return 100.0 * (baseline["rmse_log1p_rv"] - augmented["rmse_log1p_rv"]) / baseline["rmse_log1p_rv"]


def decide(validation: dict, test: dict, paired: dict | None, inversion: dict | None) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline"), validation.get("augmented"))
    test_imp = improvement_pct(test.get("baseline"), test.get("augmented"))
    difference = inversion.get("high_minus_contango_mean_rv_pct") if inversion else None
    inversion_ci = inversion.get("ci_95_low_rv_pct") if inversion else None
    paired_ci = paired.get("ci_95_low") if paired else None
    enough = (
        validation.get("n", 0) >= 30
        and test.get("n", 0) >= 30
        and paired is not None
        and inversion is not None
    )
    if (
        enough and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired_ci is not None and paired_ci > 0
        and difference is not None and difference > 0
        and inversion_ci is not None and inversion_ci > 0
    ):
        return "BACKTESTED", "PROMISING — all preregistered forecast and inversion-event criteria passed; independent validation and instrument-level economic evaluation remain necessary"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and difference is not None and difference <= 0
    ):
        return "REJECTED", "REJECTED — the augmented model did not improve either period and inverted-term-structure events did not have higher subsequent realized volatility"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule"


def upsert_registry(status: str, disposition: str, scope: str, report_relative: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    row = (
        f"| {HYPOTHESIS_ID} | {status} | VIX/VXV 30-day versus 3-month implied-volatility slope adds information about next-five-session S&P 500 realized volatility beyond recent realized volatility and VIX level; inversion predicts higher volatility. | {scope} | {disposition} | [wake-up report]({report_relative}) |"
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


def main() -> None:
    raw = {}
    parsed = {}
    urls = {}
    for series_id in SERIES:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url, timeout=25)
        raw[series_id] = body
        parsed[series_id] = parse_fred_series(body, series_id)
        urls[series_id] = url
    coverage = validate_source_coverage(parsed)
    events, event_meta = build_events(parsed["SP500"], parsed["VIXCLS"], parsed["VXVCLS"])
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient event history for preregistered walk-forward test: {len(events)}")
    predictions = walk_forward_predictions(events)
    validation = [row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    validation_result = {
        "n": len(validation),
        "baseline": forecast_metrics(validation, "baseline_prediction_bp"),
        "augmented": forecast_metrics(validation, "augmented_prediction_bp"),
    }
    test_result = {
        "n": len(test),
        "baseline": forecast_metrics(test, "baseline_prediction_bp"),
        "augmented": forecast_metrics(test, "augmented_prediction_bp"),
    }
    paired = bootstrap_paired_loss(test)
    inversion = bootstrap_inversion_difference(test)
    status, disposition = decide(validation_result, test_result, paired, inversion)

    scope = (
        f"FRED/CBOE SP500, VIXCLS and VXVCLS daily closes; aligned S&P 500 price coverage "
        f"{coverage['SP500']['first_date']} to {coverage['SP500']['last_date']}; "
        f"{len(events)} non-overlapping six-session-spaced origins; validation 2019–2021; test 2022 onward"
    )
    limitations = [
        "SP500 is a cash price index, not an executable futures series or total-return index.",
        "VIXCLS and VXVCLS are CBOE option-implied indices, not directly investable assets; the simple log(VIX/VXV) slope is not the full multi-maturity principal-component term structure used in some literature.",
        "The signal uses the prior S&P 500 session's CBOE volatility-index closes; the next five S&P 500 sessions form the target, preserving the close-time gap.",
        "FRED states that historical observations may be revised; this run uses the current retrieved vintage and does not reconstruct historical release vintages.",
        "Forecast evaluation only: no executable strategy, transaction-cost model, causal claim or live-deployment conclusion.",
        "No raw source data are committed; only hashes, retrieval metadata and aggregate research metrics are retained.",
    ]
    manifest = {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "retrieved_at_utc": SESSION_TIME.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "MET before this additional study — three distinct Treasury real-data backtests and the CFTC real-data backtest were already completed on 2026-11-25",
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
            "term_slope": "log(VIXCLS / VXVCLS); positive values indicate inversion",
            "inversion_event_rule": "VIXCLS >= VXVCLS",
            "target": "log1p(next-five-session S&P 500 realized volatility in percent)",
            "rolling_training_events": MODEL_WINDOW,
            "event_spacing_sessions": EVENT_STEP_SESSIONS,
            "target_sessions": TARGET_SESSIONS,
            "training_maturity_rule": "training target_end_date must be strictly earlier than current signal_date",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": RNG_SEED,
        },
        "coverage": coverage,
        "validation_metrics": validation_result,
        "test_metrics": test_result,
        "summary_metrics": {
            "validation_improvement_pct": improvement_pct(validation_result["baseline"], validation_result["augmented"]),
            "test_improvement_pct": improvement_pct(test_result["baseline"], test_result["augmented"]),
        },
        "paired_squared_loss_bootstrap": paired,
        "inversion_event_study": inversion,
        "limitations": limitations,
    }

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_relative = f"../reports/sessions/{STAMP[:10]}/{REPORT_PATH.name}"
    upsert_registry(status, disposition, scope, report_relative)

    val_imp = manifest["summary_metrics"]["validation_improvement_pct"]
    test_imp = manifest["summary_metrics"]["test_improvement_pct"]
    report = f"""# Wake-up session report — {SESSION_TIME.strftime('%Y-%m-%dT%H:%M:%SZ')}

## Repository state and selection

- Default branch at dispatch: main; source commit {SOURCE_SHA}.
- No open pull requests, open issues or in-progress Actions runs were present at selection.
- Earlier on 2026-11-25, three distinct Treasury real-data backtests and one CFTC real-data backtest had already met the daily minimum. This is an additional, materially distinct option-implied-volatility term-structure hypothesis.
- The prior CFTC crowding experiment is closed INCONCLUSIVE; no further tuning was performed under that ID.
- Research/paper simulation only. No live orders, capital deployment, paid data, credentials or external permissions.

## Research output

### {HYPOTHESIS_ID}

**Disposition: {status} — {disposition}.**

The hypothesis tests whether the simple 30-day/3-month CBOE implied-volatility slope contains incremental information about next-five-session S&P 500 realized volatility beyond recent realized volatility and the VIX level.

- Data: FRED/CBOE SP500, VIXCLS and VXVCLS daily observations.
- Aligned price coverage: {coverage['SP500']['first_date']} to {coverage['SP500']['last_date']}.
- Valid non-overlapping forecast origins: {len(events)}; candidates: {event_meta['candidate_origins']}; skipped: {event_meta['skipped']}.
- Signal: prior S&P 500 session close, using VIX/VXV and realized-volatility features known by that close.
- Target: next five S&P 500 sessions' root-sum-square log-return volatility, transformed with log1p.
- Event spacing: {EVENT_STEP_SESSIONS} sessions; targets do not overlap.
- Rolling training window: {MODEL_WINDOW} fully matured prior events.
- Validation: 2019–2021; test: 2022 onward.

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | {validation_result['n']} | {test_result['n']} |
| Baseline RMSE (log1p RV) | {validation_result['baseline']['rmse_log1p_rv'] if validation_result['baseline'] else 'N/A'} | {test_result['baseline']['rmse_log1p_rv'] if test_result['baseline'] else 'N/A'} |
| Augmented RMSE (log1p RV) | {validation_result['augmented']['rmse_log1p_rv'] if validation_result['augmented'] else 'N/A'} | {test_result['augmented']['rmse_log1p_rv'] if test_result['augmented'] else 'N/A'} |
| RMSE improvement | {val_imp if val_imp is not None else 'N/A'}% | {test_imp if test_imp is not None else 'N/A'}% |

- Paired squared-log-loss bootstrap: {json.dumps(paired, sort_keys=True) if paired else 'NOT COMPUTED'}.
- Inverted-term-structure event study: {json.dumps(inversion, sort_keys=True) if inversion else 'NOT COMPUTED'}.

## Literature and novelty boundary

- Chang, Hung & Wang (2018), “Volatility information implied in the term structure of VIX,” *Journal of Futures Markets*, DOI: https://doi.org/10.1002/fut.21964. Their study reports incremental realized-volatility forecasting information in term-structure variables. This is prior evidence, not proof that the simple VIX/VXV slope, five-session horizon or present walk-forward design works.
- Johnson (2017), “Risk Premia and the VIX Term Structure,” *Journal of Financial and Quantitative Analysis*, DOI: https://doi.org/10.1017/S0022109017000825. The paper relates term-structure shape to variance risk premia and synthetic variance-linked returns; that is adjacent, not the same target.
- Li, Aschakulporn & Zhang (2025), “VIX term structure and future realized volatility,” DOI: https://doi.org/10.1080/00036846.2025.2601895, is directly related. The present test is a bounded retail-data replication/screen of a simple two-tenor slope, not a claim of first discovery.

## Reproducibility and data integrity

- Deterministic tests: see the workflow run.
- Source response SHA-256 hashes, row counts, exact coverage, retrieval time, code commit and metrics are in reports/generated/vix-term-structure/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json.
- No raw market-data files were committed.
- FRED current-vintage data were used; historical revisions were not reconstructed.

## Verified versus unverified

**VERIFIED:** source HTTP retrieval and CSV parsing; source row counts and date coverage; exact-date alignment; one-session signal/target gap; non-overlapping target windows; strict target maturity; deterministic walk-forward metrics and bootstrap under this code/data vintage.

**UNVERIFIED:** historical point-in-time FRED vintages; persistence in future regimes; executable futures/ETF performance; transaction costs; causal interpretation; economic value.

## Daily KPI and research versus operations

**DAILY KPI: MET before this additional study.** The three Treasury hypotheses and one CFTC hypothesis already completed real-data backtests today. This experiment adds another distinct, preregistered real-data result.

Research: one new cross-horizon implied-volatility mechanism tested against a realized-volatility and VIX-level baseline. Operations: source retrieval, deterministic tests, report/manifest persistence and registry update only as needed.

## Next action

- If promising, require an independently coded/source-checked validation and then a separate instrument-level economic study; do not promote this forecast to a trading strategy.
- If rejected or inconclusive, close this hypothesis under its frozen decision rule. Do not tune the term-slope formula, event threshold, horizon, model window or date split under this ID.
- No automatic timebox extension.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("=== SESSION REPORT ===")
    print(report)
    print("=== GENERATED MANIFEST ===")
    print(manifest_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
