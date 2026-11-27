#!/usr/bin/env python3
"""Preregistered Bitcoin difficulty-cut / downside-semivariance forecast screen."""
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
import taker_absorption_source_preflight as price_source

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 17)
END_DATE = dt.date(2026, 11, 25)
ADJUSTMENT_END_DATE = dt.date(2026, 10, 29)
MODEL_WINDOW = 52
VALIDATION_START = dt.date(2019, 1, 1)
VALIDATION_END = dt.date(2021, 12, 31)
TEST_START = dt.date(2022, 1, 1)
TEST_END = ADJUSTMENT_END_DATE + dt.timedelta(days=1)
MIN_VALIDATION_N = 50
MIN_TEST_N = 100
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261127
FIRSTHAND_URL = "https://firsthandbitcoin.com/data/api/series/adj.json"
MEMPOOL_URL = "https://mempool.space/api/v1/mining/difficulty-adjustments/3y"
REPOSITORY = "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "btc-mining-difficulty-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
CLOSURE_PATH = ROOT / "research" / "CLOSED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md"
BASE_FEATURES = [
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
]
AUG_FEATURES = BASE_FEATURES + ["difficulty_cut_pct"]


def _finite(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {field}: {value!r}")
    return number


def parse_firsthand_adjustments(body: bytes) -> tuple[list[dict], dict]:
    """Parse Firsthand's documented public difficulty-adjustment series JSON."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Firsthand difficulty-adjustment response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Firsthand response must be a JSON object")
    required = {
        "source": "Firsthand Bitcoin",
        "key": "adj",
        "label": "Difficulty adjustment",
        "unit": "%",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"Unexpected Firsthand {key}: {payload.get(key)!r}")
    if "free to use" not in str(payload.get("license", "")).lower():
        raise ValueError("Firsthand response does not carry the documented free-use attribution license")
    try:
        generated = dt.datetime.fromisoformat(str(payload["generated"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise ValueError("Invalid Firsthand generated timestamp") from exc
    if generated.tzinfo is None:
        raise ValueError("Firsthand generated timestamp must be timezone-aware")
    raw_points = payload.get("data")
    if not isinstance(raw_points, list) or not raw_points:
        raise ValueError("Firsthand response contains no adjustment points")
    if payload.get("points") != len(raw_points):
        raise ValueError("Firsthand points metadata does not match data length")
    records = []
    for index, point in enumerate(raw_points, start=1):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"Malformed Firsthand point {index}")
        try:
            day = dt.date.fromisoformat(str(point[0]))
        except ValueError as exc:
            raise ValueError(f"Invalid Firsthand date at point {index}") from exc
        change = _finite(point[1], f"difficulty adjustment at {day}")
        if not -75.0 <= change <= 300.0:
            raise ValueError(f"Difficulty adjustment outside protocol bounds at {day}: {change}")
        records.append({"date": day, "adjustment_pct": change})
    dates = [row["date"] for row in records]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("Firsthand adjustment dates must be strictly increasing and unique")
    if payload.get("from") != dates[0].isoformat() or payload.get("to") != dates[-1].isoformat():
        raise ValueError("Firsthand from/to metadata does not match observed dates")
    metadata = {
        "source": payload["source"],
        "url": FIRSTHAND_URL,
        "license": payload["license"],
        "generated_at_utc": generated.astimezone(dt.timezone.utc).isoformat(),
        "key": payload["key"],
        "label": payload["label"],
        "unit": payload["unit"],
        "points": len(records),
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
    }
    return records, metadata


def parse_mempool_adjustments(body: bytes, min_rows: int = 50) -> list[dict]:
    """Parse Mempool's documented [timestamp, height, difficulty, change-ratio] rows."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Mempool difficulty-adjustment response is not valid JSON") from exc
    if not isinstance(payload, list) or len(payload) < min_rows:
        raise ValueError(f"Mempool difficulty-adjustment response is too small: {len(payload) if isinstance(payload, list) else 'not a list'}")
    records = []
    for index, row in enumerate(payload, start=1):
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"Malformed Mempool difficulty-adjustment row {index}")
        try:
            timestamp = int(row[0])
            height = int(row[1])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Mempool timestamp/height at row {index}") from exc
        difficulty = _finite(row[2], f"Mempool difficulty at row {index}")
        ratio = _finite(row[3], f"Mempool difficulty-change ratio at row {index}")
        if timestamp <= 0 or height <= 0 or difficulty <= 0 or not 0.25 <= ratio <= 4.0:
            raise ValueError(f"Invalid Mempool adjustment field or protocol-bound ratio at row {index}")
        day = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).date()
        records.append({
            "timestamp": timestamp,
            "date": day,
            "height": height,
            "difficulty": difficulty,
            "adjustment_pct": (ratio - 1.0) * 100.0,
        })
    records.sort(key=lambda row: row["timestamp"])
    timestamps = [row["timestamp"] for row in records]
    heights = [row["height"] for row in records]
    if len(set(timestamps)) != len(timestamps) or len(set(heights)) != len(heights):
        raise ValueError("Mempool adjustment timestamps and heights must be unique")
    if timestamps != sorted(timestamps) or heights != sorted(heights):
        raise ValueError("Mempool difficulty adjustments must be chronologically ordered")
    return records


def crosscheck_adjustments(
    firsthand: list[dict], mempool: list[dict], min_matches: int = 60, tolerance_pct_points: float = 0.02
) -> dict:
    """Consistency-check overlapping public series; this is not an independent-source claim."""
    matched = []
    unmatched = []
    used_primary_dates = set()
    for secondary in mempool:
        candidates = [
            primary for primary in firsthand
            if primary["date"] not in used_primary_dates
            and abs((primary["date"] - secondary["date"]).days) <= 1
        ]
        if len(candidates) != 1:
            unmatched.append(secondary["date"].isoformat())
            continue
        primary = candidates[0]
        used_primary_dates.add(primary["date"])
        difference = abs(primary["adjustment_pct"] - secondary["adjustment_pct"])
        if difference > tolerance_pct_points:
            raise ValueError(
                f"Firsthand/Mempool difficulty-adjustment mismatch near {secondary['date']}: "
                f"{primary['adjustment_pct']} vs {secondary['adjustment_pct']} percentage points"
            )
        matched.append({
            "firsthand_date": primary["date"].isoformat(),
            "mempool_date": secondary["date"].isoformat(),
            "date_offset_days": (primary["date"] - secondary["date"]).days,
            "absolute_difference_pct_points": difference,
        })
    coverage = len(matched) / len(mempool) if mempool else 0.0
    if len(matched) < min_matches or coverage < 0.95:
        raise ValueError(
            f"Insufficient Firsthand/Mempool cross-check: matched={len(matched)}, "
            f"coverage={coverage:.4f}, unmatched={unmatched[:5]}"
        )
    return {
        "mempool_rows": len(mempool),
        "matched_rows": len(matched),
        "unmatched_rows": len(unmatched),
        "coverage": coverage,
        "max_absolute_difference_pct_points": max(
            row["absolute_difference_pct_points"] for row in matched
        ),
        "tolerance_pct_points": tolerance_pct_points,
        "matches": matched,
        "interpretation": "series-consistency check only; not independent provider validation",
    }


def build_events(
    prices: dict[dt.date, dict],
    adjustments: list[dict],
    start_date: dt.date = START_DATE,
    end_date: dt.date = END_DATE,
    adjustment_end: dt.date = ADJUSTMENT_END_DATE,
) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    expected_days = (end_date - start_date).days + 1
    if len(dates) != expected_days or dates[0] != start_date or dates[-1] != end_date:
        raise ValueError(
            f"BTC price calendar mismatch: expected {expected_days} dates {start_date}..{end_date}, "
            f"got {len(dates)} {dates[0]}..{dates[-1]}"
        )
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            raise ValueError(f"Missing BTC daily price date between {dates[index - 1]} and {dates[index]}")
        previous_close = _finite(prices[dates[index - 1]]["close"], "previous BTC close")
        current_close = _finite(prices[dates[index]]["close"], "current BTC close")
        if previous_close <= 0 or current_close <= 0:
            raise ValueError("BTC close prices must be positive")
        returns.append(math.log(current_close / previous_close))
    index_by_date = {day: index for index, day in enumerate(dates)}
    events = []
    skipped = {
        "outside_frozen_window": 0,
        "missing_signal_date": 0,
        "insufficient_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
    }
    candidates = 0
    for adjustment in adjustments:
        adjustment_date = adjustment["date"]
        if not start_date <= adjustment_date <= adjustment_end:
            skipped["outside_frozen_window"] += 1
            continue
        candidates += 1
        # Date-only adjustment timestamps are lagged through the full next UTC day.
        signal_date = adjustment_date + dt.timedelta(days=1)
        index = index_by_date.get(signal_date)
        if index is None:
            skipped["missing_signal_date"] += 1
            continue
        if index < 20:
            skipped["insufficient_history"] += 1
            continue
        if index + 5 >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        prior5 = returns[index - 4:index + 1]
        prior20 = returns[index - 19:index + 1]
        future = returns[index + 1:index + 6]
        if any(value is None or not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue
        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        adjustment_pct = _finite(adjustment["adjustment_pct"], "difficulty adjustment percentage")
        cut_pct = max(-adjustment_pct, 0.0)
        events.append({
            "adjustment_date": adjustment_date,
            "signal_date": signal_date,
            "target_start_date": dates[index + 1],
            "target_end_date": dates[index + 5],
            "difficulty_adjustment_pct": adjustment_pct,
            "difficulty_cut_pct": cut_pct,
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
        })
    events.sort(key=lambda row: row["signal_date"])
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("Difficulty-adjustment target windows overlap or are not fully matured")
    metadata = {
        "candidate_adjustments": candidates,
        "accepted_events": len(events),
        "skipped": skipped,
        "signal_rule": "adjustment date plus one full UTC calendar day; features observed after that day's close",
        "target_rule": "next five UTC daily close-to-close returns after signal_date",
        "target_sessions": 5,
        "first_signal_date": events[0]["signal_date"].isoformat() if events else None,
        "last_signal_date": events[-1]["signal_date"].isoformat() if events else None,
        "first_adjustment_date": events[0]["adjustment_date"].isoformat() if events else None,
        "last_adjustment_date": events[-1]["adjustment_date"].isoformat() if events else None,
    }
    if len(events) < MODEL_WINDOW + MIN_VALIDATION_N + MIN_TEST_N:
        # The actual split/warm-up counts are checked after walk-forward prediction.
        metadata["sample_warning"] = "Total event count is below the conservative aggregate threshold."
    return events, metadata


def walk_forward(events: list[dict], model_window: int = MODEL_WINDOW) -> list[dict]:
    predictions = []
    for current in events:
        train = [
            row for row in events
            if row["signal_date"] < current["signal_date"]
            and row["target_end_date"] < current["signal_date"]
        ][-model_window:]
        if len(train) < model_window:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "record_date": current["signal_date"],
            "signal_date": current["signal_date"],
            "adjustment_date": current["adjustment_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_semivariance_pct2": current["target_semivariance_pct2"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "difficulty_adjustment_pct": current["difficulty_adjustment_pct"],
            "difficulty_cut_pct": current["difficulty_cut_pct"],
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict]) -> dict:
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None
    if baseline and augmented and baseline["rmse_bp"] > 0:
        improvement = 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
    return {"n": len(rows), "baseline": baseline, "augmented": augmented, "rmse_improvement_pct": improvement}


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
        return "INCONCLUSIVE", "The frozen minimum validation/test sample or paired-loss inference was not met."
    val_improvement = validation["rmse_improvement_pct"]
    test_improvement = test["rmse_improvement_pct"]
    if (
        val_improvement is not None and test_improvement is not None
        and val_improvement > 0 and test_improvement > 0 and paired["ci_95_low"] > 0
    ):
        return "PROMISING", "Both chronological periods improve and the paired-test-loss 95% lower confidence bound is positive; this remains a forecast screen."
    if (
        val_improvement is not None and test_improvement is not None
        and val_improvement < 0 and test_improvement < 0 and paired["ci_95_high"] < 0
    ):
        return "REJECTED", "Both chronological periods worsen and the paired-test-loss 95% upper confidence bound is negative."
    return "INCONCLUSIVE", "Evidence is mixed, statistically uncertain or insufficient under the frozen rule."


def assert_empirical_execution_allowed() -> None:
    """Fail closed: this identity was never admitted and is permanently closed."""
    raise RuntimeError(
        f"{HYPOTHESIS_ID} is closed as an unadmitted draft; no empirical execution is "
        "authorized for this identity. A materially revised hypothesis requires a new "
        "ID and a frozen preregistration/timebox before implementation."
    )


def run_research() -> dict:
    assert_empirical_execution_allowed()
    firsthand_body = base.fetch_bytes(FIRSTHAND_URL, timeout=30)
    mempool_body = base.fetch_bytes(MEMPOOL_URL, timeout=30)
    adjustments, firsthand_meta = parse_firsthand_adjustments(firsthand_body)
    mempool = parse_mempool_adjustments(mempool_body)
    crosscheck = crosscheck_adjustments(adjustments, mempool)
    frozen_adjustments = [
        row for row in adjustments
        if START_DATE <= row["date"] <= ADJUSTMENT_END_DATE
    ]
    if len(frozen_adjustments) < 200:
        raise ValueError(f"Insufficient frozen difficulty-adjustment history: {len(frozen_adjustments)}")

    prices, price_manifest = price_source.fetch_all_archives(START_DATE, END_DATE)
    events, event_meta = build_events(prices, frozen_adjustments)
    predictions = walk_forward(events)
    validation_rows = [
        row for row in predictions if VALIDATION_START <= row["signal_date"] <= VALIDATION_END
    ]
    test_rows = [
        row for row in predictions if TEST_START <= row["signal_date"] <= TEST_END
    ]
    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    paired = bootstrap_paired_loss(test_rows)
    decision, reason = decide(validation, test, paired)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "COMPLETE",
        "deterministic_tests_passed": os.environ.get("QFR_DETERMINISTIC_TESTS_PASSED") == "true",
        "decision": decision,
        "decision_reason": reason,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "sample": {
            "symbol": "BTCUSDT",
            "venue": "Binance Spot",
            "price_interval": "1d UTC",
            "price_start": START_DATE.isoformat(),
            "price_end": END_DATE.isoformat(),
            "adjustment_start": START_DATE.isoformat(),
            "adjustment_end": ADJUSTMENT_END_DATE.isoformat(),
            "signal_end": TEST_END.isoformat(),
        },
        "sources": {
            "difficulty_adjustments": {
                **firsthand_meta,
                "response_sha256": hashlib.sha256(firsthand_body).hexdigest(),
                "frozen_event_count": len(frozen_adjustments),
                "frozen_first_date": frozen_adjustments[0]["date"].isoformat(),
                "frozen_last_date": frozen_adjustments[-1]["date"].isoformat(),
            },
            "mempool_consistency_check": {
                "url": MEMPOOL_URL,
                "response_sha256": hashlib.sha256(mempool_body).hexdigest(),
                **crosscheck,
            },
            "binance_spot_prices": price_manifest,
        },
        "feature_definition": {
            "difficulty_adjustment_pct": "published percentage change in network difficulty at the 2016-block retarget",
            "difficulty_cut_pct": "max(-difficulty_adjustment_pct, 0); positive only for downward difficulty adjustments",
            "interpretation": "a realized difficulty cut is a lagged proxy for slower block production / hash-rate contraction, not direct evidence of miner identities, forced selling, or profitability",
        },
        "target_definition": "mean(min(next-five UTC daily close-to-close log returns,0)^2)*10000; model target log1p(target)",
        "model": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUG_FEATURES,
            "rolling_training_events": MODEL_WINDOW,
            "signal_lag_days_after_adjustment_date": 1,
            "target_sessions": 5,
            "validation_start": VALIDATION_START.isoformat(),
            "validation_end": VALIDATION_END.isoformat(),
            "test_start": TEST_START.isoformat(),
            "test_end": TEST_END.isoformat(),
            "minimum_validation_n": MIN_VALIDATION_N,
            "minimum_test_n": MIN_TEST_N,
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
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
    sources = result.get("sources") or {}
    firsthand = sources.get("difficulty_adjustments") or {}
    mempool = sources.get("mempool_consistency_check") or {}
    price = sources.get("binance_spot_prices") or {}
    coverage = price.get("coverage") or {}
    event_meta = result.get("event_metadata") or {}
    manifest_path = result.get("manifest_path", "reports/generated/btc-mining-difficulty-btc-downside/manifest.json")
    manifest_relative = "../../" + Path(manifest_path).relative_to("reports").as_posix()
    paired = result.get("paired_test_loss_bootstrap")
    return f"""# Closed unadmitted draft — Bitcoin mining difficulty-cut downside — {STAMP}

**Hypothesis:** {HYPOTHESIS_ID}

**Status:** {result.get('status', 'FAILED')}  
**Disposition:** {result.get('decision', 'INCONCLUSIVE/INFEASIBLE')}  
**Reason:** {result.get('decision_reason', result.get('error', 'No result'))}  
**Execution error:** {result.get('error', 'None')}

- Workflow run: https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}
- Triggering source commit: {SOURCE_SHA}

## Data and provenance

- Difficulty source: [Firsthand Bitcoin adjustment series]({FIRSTHAND_URL})
- Firsthand points: {firsthand.get('points', 'unavailable')}; source dates {firsthand.get('first_date', 'unavailable')} to {firsthand.get('last_date', 'unavailable')}
- Frozen adjustment sample: {firsthand.get('frozen_first_date', 'unavailable')} to {firsthand.get('frozen_last_date', 'unavailable')} ({firsthand.get('frozen_event_count', 0)} events)
- Firsthand response SHA-256: {firsthand.get('response_sha256', 'unavailable')}
- Mempool 3y consistency check: {mempool.get('matched_rows', 0)}/{mempool.get('mempool_rows', 0)} matched; coverage={mempool.get('coverage', 'unavailable')}; maximum absolute discrepancy={mempool.get('max_absolute_difference_pct_points', 'unavailable')} percentage points
- Binance BTCUSDT Spot daily archives: {price.get('archive_count', 0)} checksum-verified; {coverage.get('observed_daily_rows', 0)} rows; missing dates={len(coverage.get('missing_dates', [])) if coverage else 'unavailable'}; zero-volume dates={coverage.get('zero_volume_days', 'unavailable')}
- Binance archive-manifest SHA-256: {price.get('archive_manifest_sha256', 'unavailable')}
- Raw observations committed: No

The Firsthand/Mempool comparison is a series-consistency check, not an independent-provider validation claim. The Firsthand source is a commercial mining-data publisher; the underlying difficulty change is an objective consensus retarget, but the publisher's derivation is not a full-node reconstruction performed by this repository.

## Frozen feature and timing

The sole augmented feature is `difficulty_cut_pct = max(-difficulty_adjustment_pct, 0)`. It is positive only when the network difficulty is reduced. A downward retarget is consistent with slower block production and a lower realized hash-rate estimate over the preceding 2,016-block epoch; it does not identify which miners exited or establish forced BTC selling.

Because the source reports an adjustment date rather than an exact publication timestamp, the signal is delayed through the next full UTC calendar day. Features are formed after that day's close. The target is the following five UTC daily close-to-close returns, excluding the signal day. Target windows are required to be non-overlapping and fully matured before subsequent training events.

## Event construction

- Candidate adjustments: {event_meta.get('candidate_adjustments', 'unavailable')}
- Accepted events: {event_meta.get('accepted_events', 'unavailable')}
- Walk-forward forecasts: {result.get('forecast_count', 'unavailable')}
- Validation forecasts: {validation.get('n', 0)}
- Test forecasts: {test.get('n', 0)}
- First signal: {event_meta.get('first_signal_date', 'unavailable')}
- Last signal: {event_meta.get('last_signal_date', 'unavailable')}

## Forecast results

| Metric | Validation | Test |
|---|---:|---:|
| Baseline log-semivariance RMSE | {val_base.get('rmse_bp', 'unavailable')} | {test_base.get('rmse_bp', 'unavailable')} |
| Augmented log-semivariance RMSE | {val_aug.get('rmse_bp', 'unavailable')} | {test_aug.get('rmse_bp', 'unavailable')} |
| RMSE improvement (%) | {validation.get('rmse_improvement_pct', 'unavailable')} | {test.get('rmse_improvement_pct', 'unavailable')} |

Paired test squared-loss bootstrap: {json.dumps(paired, sort_keys=True) if paired else 'not computed'}.

## Interpretation and limitations

This is an incremental forecast screen, not a causal estimate or trading P&L. Difficulty adjusts only about every two weeks and summarizes the prior block epoch; the one-day lag avoids same-day timestamp ambiguity but cannot eliminate all endogeneity between price, miner economics and hash rate. The Firsthand series is current-vintage and may have provider-specific methodology; Mempool comparison checks recent consistency only. The sample begins in 2017 because the frozen BTC Spot price archive begins then.

No profitability, CAGR, Sharpe, drawdown, transaction costs or live deployment claim is made. No feature, threshold, model, target, sample, split or acceptance-rule retuning was performed.

## End-of-session digest

- **Research output:** no admitted hypothesis and no empirical result; the pre-existing draft was closed for violating the preregistration/timebox admission rule.
- **Hypotheses/ranking:** `{HYPOTHESIS_ID}`; forecast-only and not comparable to strategy P&L rankings.
- **Daily KPI:** already met earlier on 2026-11-27 by the separate real-data BTC taker-absorption backtest; no duplicate backtest was run.
- **Changed:** the draft source serialization and fail-closed guard were repaired for deterministic validation only; this identity remains unadmitted and closed.
- **Verified:** the code now blocks before any source fetch; deterministic tests are the only authorized execution for this closed draft.
- **Unverified/blocked:** no accepted source coverage, empirical model result, predictive value, live strategy validation, profitability, causal miner-selling inference or independent Firsthand-provider validation is established.
- **Research vs operations:** research and empirical validation were the primary objective; GitHub Actions and evidence persistence were supporting operations.
- **Next:** do not reopen this identity; any future mining-network study must be materially redesigned and preregistered with a new ID before implementation.

## Evidence files

- Manifest: [{result.get('manifest_path', 'not yet written')}]({manifest_relative})
- Closure record: [unadmitted draft closure](../../../research/CLOSED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md)
- Registry: [hypothesis registry](../../../research/HYPOTHESIS-REGISTRY.md)
"""


def write_outputs(result: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-wakeup-automation-7-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = report_path.relative_to(ROOT).as_posix()
    result["manifest_path"] = manifest_path.relative_to(ROOT).as_posix()
    report = render_report(result)
    report_path.write_text(report, encoding="utf-8")
    result["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return report_path, manifest_path


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FAILED",
            "deterministic_tests_passed": os.environ.get("QFR_DETERMINISTIC_TESTS_PASSED") == "true",
            "decision": "INCONCLUSIVE/INFEASIBLE",
            "decision_reason": "The source, coverage, or empirical execution gate failed before a valid performance conclusion.",
            "error": f"{type(exc).__name__}: {exc}",
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "closure_record_path": CLOSURE_PATH.relative_to(ROOT).as_posix(),
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
        "error": result.get("error"),
    }, indent=2))
    return 0 if result.get("status") == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
