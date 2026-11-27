#!/usr/bin/env python3
"""Preregistered Binance BTC Spot taker-flow/price-response downside forecast screen."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc
import taker_absorption_source_preflight as source

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 17)
END_DATE = dt.date(2026, 11, 25)
SIGNAL_END_DATE = dt.date(2026, 11, 20)
EVENT_STEP_DAYS = 6
TARGET_SESSIONS = 5
MODEL_WINDOW = 104
VALIDATION_START = dt.date(2019, 1, 1)
VALIDATION_END = dt.date(2021, 12, 31)
TEST_START = dt.date(2022, 1, 1)
MIN_VALIDATION_N = 60
MIN_TEST_N = 100
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261127
SOURCE_PREFLIGHT_RUN_ID = 45924502841
SOURCE_PREFLIGHT_MANIFEST_SHA256 = "978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe"
REPOSITORY = "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "taker-absorption-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-TAKER-ABSORPTION-BTC-DOWNSIDE-01.md"

BASE_FEATURES = [
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
]
AUG_FEATURES = BASE_FEATURES + ["signed_taker_absorption"]


def signed_absorption_proxy(imbalance: float, signal_return: float) -> float:
    """Positive: aggressive buying with a falling price; negative: selling with a rising price."""
    if not all(math.isfinite(value) for value in (imbalance, signal_return)):
        raise ValueError("Absorption inputs must be finite")
    if not -1.000000001 <= imbalance <= 1.000000001:
        raise ValueError("Taker imbalance must be within [-1, 1]")
    sell_side_absorption = max(imbalance, 0.0) * max(-signal_return, 0.0)
    buy_side_absorption = max(-imbalance, 0.0) * max(signal_return, 0.0)
    return sell_side_absorption - buy_side_absorption


def build_events(rows: dict[dt.date, dict]) -> tuple[list[dict], dict]:
    dates = sorted(rows)
    expected_days = (END_DATE - START_DATE).days + 1
    if len(dates) != expected_days or dates[0] != START_DATE or dates[-1] != END_DATE:
        raise ValueError(
            f"Price/flow calendar mismatch: expected {expected_days} dates "
            f"{START_DATE}..{END_DATE}, got {len(dates)} {dates[0]}..{dates[-1]}"
        )

    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
            continue
        previous_close = float(rows[dates[index - 1]]["close"])
        current_close = float(rows[dates[index]]["close"])
        if previous_close <= 0 or current_close <= 0:
            returns.append(None)
        else:
            value = math.log(current_close / previous_close)
            returns.append(value if math.isfinite(value) else None)

    index_by_date = {day: index for index, day in enumerate(dates)}
    anchor = START_DATE + dt.timedelta(days=20)
    events = []
    skipped = {
        "missing_or_zero_volume_flow": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
        "invalid_feature": 0,
    }
    candidate_origins = 0

    for signal_date in dates:
        if signal_date < anchor or signal_date > SIGNAL_END_DATE:
            continue
        if (signal_date - anchor).days % EVENT_STEP_DAYS:
            continue
        candidate_origins += 1
        index = index_by_date[signal_date]
        if index < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if index + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        imbalance = rows[signal_date].get("taker_imbalance")
        if imbalance is None:
            skipped["missing_or_zero_volume_flow"] += 1
            continue

        prior5 = returns[index - 4:index + 1]
        prior20 = returns[index - 19:index + 1]
        future = returns[index + 1:index + 1 + TARGET_SESSIONS]
        if any(value is None or not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue
        signal_return = returns[index]
        try:
            absorption = signed_absorption_proxy(float(imbalance), float(signal_return))
        except (TypeError, ValueError):
            skipped["invalid_feature"] += 1
            continue

        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        if not math.isfinite(target) or target < 0:
            skipped["invalid_returns"] += 1
            continue
        events.append({
            "signal_date": signal_date,
            "target_start_date": dates[index + 1],
            "target_end_date": dates[index + TARGET_SESSIONS],
            "signed_taker_absorption": absorption,
            "taker_imbalance": float(imbalance),
            "signal_day_return": float(signal_return),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
        })

    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("Target windows overlap or are not fully matured before the next signal")
    metadata = {
        "candidate_origins": candidate_origins,
        "accepted_events": len(events),
        "skipped": skipped,
        "event_step_calendar_days": EVENT_STEP_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "signal_start_rule": "first BTCUSDT UTC daily close after 20 complete prior returns",
        "signal_end_date": SIGNAL_END_DATE.isoformat(),
        "target_rule": "mean(min(next-five UTC daily log return, 0)^2) * 10000",
        "feature_rule": (
            "max(taker_imbalance,0)*max(-signal_day_return,0) - "
            "max(-taker_imbalance,0)*max(signal_day_return,0)"
        ),
        "first_accepted_signal": events[0]["signal_date"].isoformat() if events else None,
        "last_accepted_signal": events[-1]["signal_date"].isoformat() if events else None,
    }
    return events, metadata


def walk_forward(events: list[dict]) -> list[dict]:
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
            baseline = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_semivariance_pct2": current["target_semivariance_pct2"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "signed_taker_absorption": current["signed_taker_absorption"],
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict]) -> dict:
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None
    if baseline and augmented and baseline["rmse_bp"] > 0:
        improvement = 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
    return {
        "n": len(rows),
        "baseline": baseline,
        "augmented": augmented,
        "rmse_improvement_pct": improvement,
    }


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    loss_rows = []
    for row in rows:
        target = float(row["target_bp"])
        baseline = float(row["baseline_prediction_bp"])
        augmented = float(row["augmented_prediction_bp"])
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not all(math.isfinite(value) for value in (target, baseline, augmented, difference)):
            return None
        loss_rows.append({"loss_difference": difference})
    observed = statistics.fmean(row["loss_difference"] for row in loss_rows)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(loss_rows, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["loss_difference"] for row in sample))
    samples.sort()
    return {
        "status": "COMPUTED",
        "observations": len(loss_rows),
        "reps": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "observed_mean_baseline_minus_augmented_squared_loss": observed,
        "ci_95_low": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if (
        validation["n"] < MIN_VALIDATION_N
        or test["n"] < MIN_TEST_N
        or paired is None
        or validation["baseline"] is None
        or test["baseline"] is None
    ):
        return "INCONCLUSIVE", (
            "The frozen minimum validation/test sample or paired-loss inference was not met."
        )
    val_improvement = validation["rmse_improvement_pct"]
    test_improvement = test["rmse_improvement_pct"]
    if (
        val_improvement is not None
        and test_improvement is not None
        and val_improvement > 0
        and test_improvement > 0
        and paired["ci_95_low"] > 0
    ):
        return "PROMISING", (
            "Validation and test RMSE both improve and the paired-test-loss 95% lower confidence "
            "bound is positive; this remains a forecast-screen result."
        )
    if (
        val_improvement is not None
        and test_improvement is not None
        and val_improvement < 0
        and test_improvement < 0
        and paired["ci_95_high"] < 0
    ):
        return "REJECTED", (
            "Validation and test RMSE both worsen and the paired-test-loss 95% upper confidence "
            "bound is negative."
        )
    return "INCONCLUSIVE", (
        "Evidence is mixed, statistically uncertain or insufficient under the frozen rule."
    )


def run_research() -> dict:
    rows, source_manifest = source.fetch_all_archives(START_DATE, END_DATE)
    if source_manifest["archive_manifest_sha256"] != SOURCE_PREFLIGHT_MANIFEST_SHA256:
        raise ValueError(
            "Archive manifest differs from the frozen source-preflight hash: "
            f"expected={SOURCE_PREFLIGHT_MANIFEST_SHA256}, "
            f"actual={source_manifest['archive_manifest_sha256']}"
        )
    coverage = source_manifest["coverage"]
    expected_rows = (END_DATE - START_DATE).days + 1
    if (
        coverage["observed_daily_rows"] != expected_rows
        or coverage["missing_dates"]
        or coverage["zero_volume_days"] != 0
    ):
        raise ValueError(f"Frozen source coverage gate failed: {coverage}")

    events, event_meta = build_events(rows)
    predictions = walk_forward(events)
    validation_rows = [
        row for row in predictions
        if VALIDATION_START <= row["signal_date"] <= VALIDATION_END
    ]
    test_rows = [
        row for row in predictions
        if TEST_START <= row["signal_date"] <= SIGNAL_END_DATE
    ]
    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    paired = bootstrap_paired_loss(test_rows)
    decision, decision_reason = decide(validation, test, paired)

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "COMPLETE",
        "decision": decision,
        "decision_reason": decision_reason,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
        "source_preflight_manifest_sha256": SOURCE_PREFLIGHT_MANIFEST_SHA256,
        "sample": {
            "symbol": "BTCUSDT",
            "venue": "Binance Spot",
            "interval": "1d UTC",
            "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(),
            "signal_end_date": SIGNAL_END_DATE.isoformat(),
        },
        "source_manifest": source_manifest,
        "feature_definition": {
            "taker_imbalance": "2*taker_buy_base_volume/total_base_volume - 1",
            "signed_taker_absorption": (
                "max(taker_imbalance,0)*max(-signal_day_return,0) - "
                "max(-taker_imbalance,0)*max(signal_day_return,0)"
            ),
            "interpretation": (
                "positive = net taker buying while price falls; negative = net taker selling "
                "while price rises; a daily-bar proxy, not observed resting liquidity"
            ),
        },
        "target_definition": (
            "mean(min(next-five UTC daily log return,0)^2)*10000; model target log1p(target)"
        ),
        "model": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUG_FEATURES,
            "window_events": MODEL_WINDOW,
            "event_step_calendar_days": EVENT_STEP_DAYS,
            "target_sessions": TARGET_SESSIONS,
            "validation_start": VALIDATION_START.isoformat(),
            "validation_end": VALIDATION_END.isoformat(),
            "test_start": TEST_START.isoformat(),
            "test_end": SIGNAL_END_DATE.isoformat(),
            "minimum_validation_n": MIN_VALIDATION_N,
            "minimum_test_n": MIN_TEST_N,
        },
        "event_metadata": event_meta,
        "forecast_count": len(predictions),
        "validation": validation,
        "test": test,
        "paired_test_loss_bootstrap": paired,
        "raw_observations_saved": False,
        "trading_pnl_evaluated": False,
    }


def render_report(result: dict) -> str:
    validation = result.get("validation") or {}
    test = result.get("test") or {}
    val_base = validation.get("baseline") or {}
    val_aug = validation.get("augmented") or {}
    test_base = test.get("baseline") or {}
    test_aug = test.get("augmented") or {}
    paired = result.get("paired_test_loss_bootstrap")
    source_manifest = result.get("source_manifest") or {}
    coverage = source_manifest.get("coverage") or {}
    event_meta = result.get("event_metadata") or {}
    manifest_path = result.get("manifest_path", "reports/generated/taker-absorption-btc-downside/manifest.json")
    manifest_path_obj = Path(manifest_path)
    manifest_relative = (
        "../../" + manifest_path_obj.relative_to("reports").as_posix()
        if manifest_path_obj.parts and manifest_path_obj.parts[0] == "reports"
        else manifest_path
    )
    report = f"""# BTC taker-flow/price-response downside forecast — {STAMP}

**Hypothesis:** {HYPOTHESIS_ID}

**Status:** {result.get("status", "FAILED")}  
**Disposition:** {result.get("decision", "INCONCLUSIVE")}  
**Reason:** {result.get("decision_reason", result.get("error", "No result"))}

- Workflow run: https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}
- Triggering source commit: {SOURCE_SHA}
- Source-preflight run: https://github.com/{REPOSITORY}/actions/runs/{SOURCE_PREFLIGHT_RUN_ID}
- Source-preflight archive-manifest SHA-256: {SOURCE_PREFLIGHT_MANIFEST_SHA256}

## Data and provenance

- Instrument: Binance BTCUSDT Spot 1d UTC
- Frozen source coverage: {START_DATE} through {END_DATE}
- Checksum-verified archives: {source_manifest.get("archive_count", "not available")}
- Archive-manifest SHA-256: {source_manifest.get("archive_manifest_sha256", "not available")}
- Observed daily rows: {coverage.get("observed_daily_rows", "not available")}
- Missing dates: {len(coverage.get("missing_dates", [])) if coverage else "not available"}
- Zero-volume days: {coverage.get("zero_volume_days", "not available")}
- Raw observations committed: No

## Frozen feature and target

The single augmented feature is signed_taker_absorption:
max(taker_imbalance,0) * max(-signal_day_return,0) minus
max(-taker_imbalance,0) * max(signal_day_return,0).

The target is the mean squared negative log return over the next five UTC daily sessions,
scaled by 10,000. The signal-day return is excluded from the target. Every six-day event
origin has a five-session forward window, so accepted target windows do not overlap.

## Event construction

- Candidate origins: {event_meta.get("candidate_origins", "not available")}
- Accepted events: {event_meta.get("accepted_events", "not available")}
- Walk-forward forecasts: {result.get("forecast_count", "not available")}
- Validation forecasts: {validation.get("n", 0)}
- Test forecasts: {test.get("n", 0)}
- First accepted signal: {event_meta.get("first_accepted_signal", "not available")}
- Last accepted signal: {event_meta.get("last_accepted_signal", "not available")}

## Forecast results

| Metric | Validation | Test |
|---|---:|---:|
| Baseline log-semivariance RMSE | {val_base.get("rmse_bp", "not available")} | {test_base.get("rmse_bp", "not available")} |
| Augmented log-semivariance RMSE | {val_aug.get("rmse_bp", "not available")} | {test_aug.get("rmse_bp", "not available")} |
| RMSE improvement (%) | {validation.get("rmse_improvement_pct", "not available")} | {test.get("rmse_improvement_pct", "not available")} |

Paired test squared-loss bootstrap: {json.dumps(paired, sort_keys=True) if paired else "not computed"}.

## Interpretation and limitations

The signed feature is a daily aggressor-flow/price-response mismatch proxy. Binance Spot is one venue,
and daily aggregates do not reveal order-book depth, cancellations, trader identity or actual passive
liquidity absorption. The experiment is a forecast screen, not a trading P&L or deployment test.

No strategy profitability, CAGR, Sharpe, drawdown or live-trading claim is made. The disposition follows
the frozen validation/test and paired-loss rules; no parameter retuning was performed.

## Evidence files

- Manifest: [{result.get("manifest_path", "not yet written")}]({manifest_relative})
- Preregistration: [frozen protocol](../../../research/PREREGISTERED-QFR-2026-11-27-TAKER-ABSORPTION-BTC-DOWNSIDE-01.md)
- Registry: [hypothesis registry](../../../research/HYPOTHESIS-REGISTRY.md)
"""
    return report

def update_documents(result: dict, report_path: Path, manifest_path: Path) -> None:
    decision = result.get("decision", "INCONCLUSIVE")
    status = "BACKTESTED" if result.get("status") == "COMPLETE" else "INCONCLUSIVE"
    validation = result.get("validation") or {}
    test = result.get("test") or {}
    val_imp = validation.get("rmse_improvement_pct")
    test_imp = test.get("rmse_improvement_pct")
    source_manifest = result.get("source_manifest") or {}
    coverage = source_manifest.get("coverage") or {}
    summary = (
        f"{result.get('status')}; decision={decision}; validation/test n="
        f"{validation.get('n', 0)}/{test.get('n', 0)}; RMSE improvement={val_imp}/{test_imp}; "
        f"paired CI={result.get('paired_test_loss_bootstrap')}"
    )
    if result.get("error"):
        summary = f"FAILED before a valid empirical conclusion: {result['error']}"
    source_summary = (
        f"Binance Vision BTCUSDT Spot 1d UTC; {source_manifest.get('archive_count', 0)} "
        f"checksum-verified archives; {coverage.get('observed_daily_rows', 0)} rows; "
        f"{START_DATE} to {END_DATE}; preflight run {SOURCE_PREFLIGHT_RUN_ID}"
    )
    relative_report = "../" + report_path.relative_to(ROOT).as_posix()
    relative_manifest = "../" + manifest_path.relative_to(ROOT).as_posix()
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Signed Binance Spot taker-flow/price-response divergence "
        "(buy-initiated imbalance while price falls, less sell-initiated imbalance while price rises) "
        "may add information about next-five-session BTC downside semivariance beyond prior downside "
        f"risk, realized variance and momentum. | {source_summary} | {summary} | "
        f"[session report]({relative_report}) / [manifest]({relative_manifest}) / "
        "[preregistration](PREREGISTERED-QFR-2026-11-27-TAKER-ABSORPTION-BTC-DOWNSIDE-01.md) |"
    )
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    lines = registry.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[index] = row
            replaced = True
            break
    if not replaced:
        lines.extend(["", row])
    REGISTRY_PATH.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

    prereg = PREREG_PATH.read_text(encoding="utf-8")
    status_line = "- **Status:** PREREGISTERED; source feasibility PASS; backtest not yet run."
    new_status = (
        f"- **Status:** EXECUTED; decision {decision}; workflow run {RUN_ID}; "
        f"validation/test forecasts {validation.get('n', 0)}/{test.get('n', 0)}."
    )
    if status_line in prereg:
        prereg = prereg.replace(status_line, new_status)
    section = f"""## 8. Execution result

- Workflow run: https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}
- Triggering source commit: {SOURCE_SHA}
- Status: {result.get("status")}
- Decision: {decision}
- Validation/test forecasts: {validation.get("n", 0)}/{test.get("n", 0)}
- Validation/test RMSE improvement: {val_imp}/{test_imp}
- Paired test-loss bootstrap: {json.dumps(result.get("paired_test_loss_bootstrap"), sort_keys=True)}
- Report: {relative_report}
- Manifest: {relative_manifest}

{result.get("decision_reason", result.get("error", ""))}
"""
    marker = "## 8. Execution result"
    if marker in prereg:
        prereg = prereg.split(marker, 1)[0].rstrip() + chr(10) + chr(10) + section
    else:
        prereg = prereg.rstrip() + chr(10) + chr(10) + section
    PREREG_PATH.write_text(prereg, encoding="utf-8")

def write_outputs(result: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-taker-absorption-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = report_path.relative_to(ROOT).as_posix()
    result["manifest_path"] = manifest_path.relative_to(ROOT).as_posix()
    report_text = render_report(result)
    report_path.write_text(report_text, encoding="utf-8")
    result["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + chr(10),
        encoding="utf-8",
    )
    update_documents(result, report_path, manifest_path)
    result["registry_sha256"] = hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
    result["prereg_sha256"] = hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + chr(10),
        encoding="utf-8",
    )
    return report_path, manifest_path


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FAILED",
            "decision": "INCONCLUSIVE",
            "decision_reason": "The real-data run failed before a valid empirical disposition.",
            "error": f"{type(exc).__name__}: {exc}",
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
            "source_preflight_manifest_sha256": SOURCE_PREFLIGHT_MANIFEST_SHA256,
            "validation": {"n": 0},
            "test": {"n": 0},
            "forecast_count": 0,
            "raw_observations_saved": False,
            "trading_pnl_evaluated": False,
        }
    report_path, manifest_path = write_outputs(result)
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "report_path": report_path.relative_to(ROOT).as_posix(),
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "report_sha256": result.get("report_sha256"),
        "registry_sha256": result.get("registry_sha256"),
        "prereg_sha256": result.get("prereg_sha256"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
