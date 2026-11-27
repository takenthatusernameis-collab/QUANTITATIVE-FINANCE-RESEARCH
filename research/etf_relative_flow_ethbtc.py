#!/usr/bin/env python3
"""Frozen walk-forward forecast: relative U.S. BTC/ETH spot ETF flows -> ETH/BTC returns."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

import etf_relative_flow_source_preflight as source
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01"
PRICE_START_DATE = dt.date(2024, 7, 1)
PRICE_END_DATE = dt.date(2026, 11, 26)
PRICE_AS_OF_DATE = dt.date(2026, 11, 27)
FLOW_CUTOFF_DATE = dt.date(2026, 11, 16)
FLOW_EMBARGO_DAYS = 5
TARGET_SESSIONS = 5
FLOW_WARMUP = 60
FLOW_EVENT_STEP = 2
MODEL_WINDOW = 65
VALIDATION_START = dt.date(2025, 1, 1)
VALIDATION_END = dt.date(2025, 12, 31)
TEST_START = dt.date(2026, 1, 1)
TEST_END = dt.date(2026, 11, 21)
MIN_VALIDATION_N = 45
MIN_TEST_N = 60
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 5
BOOTSTRAP_SEED = 20261127

SOURCE_PREFLIGHT_RUN_ID = 45996756282
SOURCE_PREFLIGHT_COMMIT_SHA = "8538e696c78a590916145a8c0cbcb313cc901ae1"
FROZEN_FLOW_PANEL_SHA256 = "4d7d2a8c54b5b6eebbf48631f4641ad24d4692a21dc5d6681beba65e4ae79a18"
FROZEN_BTC_ARCHIVE_MANIFEST_SHA256 = "f70f8a1b01098cee6f8299514888363b04956f66cf122ffae95579b12e08faf5"
FROZEN_ETH_ARCHIVE_MANIFEST_SHA256 = "0ef90c2cde6888e0ca7512670a84ff2fba17995950870ce847f0d22e635dc314"

BASE_FEATURES = [
    "pre_ratio_return5",
    "pre_ratio_return20",
    "pre_ratio_rv20_log",
    "pre_btc_return5",
    "pre_eth_return5",
    "common_flow_pressure",
]
AUGMENTED_FEATURES = BASE_FEATURES + ["relative_flow_pressure"]

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "etf-relative-flow-ethbtc" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md"


class FrozenSourceMismatch(ValueError):
    """The live source no longer reproduces the admitted, frozen source sample."""


def _compact_price_manifest(value: dict) -> dict:
    return {key: item for key, item in value.items() if key != "archives"}


def fetch_frozen_inputs() -> tuple[list[dict], dict, dict, dict]:
    """Fetch current Farside pages and exact frozen Binance archive coverage."""
    retrieved_at = dt.datetime.now(dt.timezone.utc)
    btc_html = base.fetch_bytes(source.BTC_FLOW_URL, timeout=30)
    eth_html = base.fetch_bytes(source.ETH_FLOW_URL, timeout=30)
    btc_flows, btc_flow_meta = source.parse_farside_html(btc_html, "Farside Bitcoin ETF all-data")
    eth_flows, eth_flow_meta = source.parse_farside_html(eth_html, "Farside Ethereum ETF all-data")

    panel, panel_meta = source.build_flow_panel(btc_flows, eth_flows, FLOW_CUTOFF_DATE)
    if panel_meta.get("sha256") != FROZEN_FLOW_PANEL_SHA256:
        raise FrozenSourceMismatch(
            "Farside flow panel no longer matches the frozen SHA-256: "
            f"expected={FROZEN_FLOW_PANEL_SHA256}, actual={panel_meta.get('sha256')}"
        )

    btc_end, btc_end_probes = source.resolve_latest_available_end_date(
        "BTCUSDT", PRICE_START_DATE, PRICE_END_DATE, PRICE_AS_OF_DATE
    )
    eth_end, eth_end_probes = source.resolve_latest_available_end_date(
        "ETHUSDT", PRICE_START_DATE, PRICE_END_DATE, PRICE_AS_OF_DATE
    )
    common_end = min(btc_end, eth_end)
    if common_end != PRICE_END_DATE:
        raise FrozenSourceMismatch(
            f"Frozen common price end changed: expected={PRICE_END_DATE}, actual={common_end}"
        )

    btc_prices, btc_manifest = source.fetch_symbol_prices(
        "BTCUSDT", PRICE_START_DATE, common_end, PRICE_AS_OF_DATE
    )
    eth_prices, eth_manifest = source.fetch_symbol_prices(
        "ETHUSDT", PRICE_START_DATE, common_end, PRICE_AS_OF_DATE
    )
    price_sources = {
        "common_end_date": common_end.isoformat(),
        "requested_end_date": PRICE_END_DATE.isoformat(),
        "btc_end_probes": btc_end_probes,
        "eth_end_probes": eth_end_probes,
        "btc": _compact_price_manifest(btc_manifest),
        "eth": _compact_price_manifest(eth_manifest),
    }
    source_manifest = {
        "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
        "source_preflight_commit_sha": SOURCE_PREFLIGHT_COMMIT_SHA,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "flow_embargo_calendar_days": FLOW_EMBARGO_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "btc_flow_source": btc_flow_meta,
        "eth_flow_source": eth_flow_meta,
        "flow_panel": panel_meta,
        "price_sources": price_sources,
        "raw_observations_saved": False,
    }
    return panel, btc_prices, eth_prices, source_manifest


def verify_frozen_source_manifest(source_manifest: dict) -> None:
    flow = source_manifest.get("flow_panel") or {}
    prices = source_manifest.get("price_sources") or {}
    btc = prices.get("btc") or {}
    eth = prices.get("eth") or {}
    checks = [
        (flow.get("sha256") == FROZEN_FLOW_PANEL_SHA256, "flow-panel SHA-256"),
        (flow.get("rows") == 583, "flow-panel row count"),
        (flow.get("first_date") == "2024-07-23", "flow-panel first date"),
        (flow.get("last_date") == "2026-11-16", "flow-panel last date"),
        (flow.get("cutoff_date") == FLOW_CUTOFF_DATE.isoformat(), "flow-panel cutoff"),
        (flow.get("unmatched_dates") == [], "unmatched flow dates"),
        (prices.get("common_end_date") == PRICE_END_DATE.isoformat(), "common price end date"),
        (btc.get("archive_manifest_sha256") == FROZEN_BTC_ARCHIVE_MANIFEST_SHA256, "BTC archive-manifest SHA-256"),
        (eth.get("archive_manifest_sha256") == FROZEN_ETH_ARCHIVE_MANIFEST_SHA256, "ETH archive-manifest SHA-256"),
        (btc.get("rows") == 879 and btc.get("start_date") == PRICE_START_DATE.isoformat()
         and btc.get("end_date") == PRICE_END_DATE.isoformat() and btc.get("missing_dates") == [], "BTC price coverage"),
        (eth.get("rows") == 879 and eth.get("start_date") == PRICE_START_DATE.isoformat()
         and eth.get("end_date") == PRICE_END_DATE.isoformat() and eth.get("missing_dates") == [], "ETH price coverage"),
    ]
    failed = [label for passed, label in checks if not passed]
    if failed:
        raise FrozenSourceMismatch("Frozen source acceptance failed: " + ", ".join(failed))


def build_events(
    panel: list[dict],
    btc_prices: dict[dt.date, float],
    eth_prices: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    dates = sorted(btc_prices)
    if dates != sorted(eth_prices):
        raise ValueError("BTC and ETH price calendars do not match")
    expected_count = (PRICE_END_DATE - PRICE_START_DATE).days + 1
    if (
        len(dates) != expected_count
        or not dates
        or dates[0] != PRICE_START_DATE
        or dates[-1] != PRICE_END_DATE
        or any((right - left).days != 1 for left, right in zip(dates, dates[1:]))
    ):
        raise ValueError("Price calendar differs from the frozen 879-day UTC sample")
    if not panel or [row["date"] for row in panel] != sorted(row["date"] for row in panel):
        raise ValueError("Flow panel is empty or not ordered")
    if len({row["date"] for row in panel}) != len(panel):
        raise ValueError("Duplicate common ETF flow date")

    btc_returns: dict[dt.date, float | None] = {dates[0]: None}
    eth_returns: dict[dt.date, float | None] = {dates[0]: None}
    ratio_returns: dict[dt.date, float | None] = {dates[0]: None}
    for index in range(1, len(dates)):
        day, previous = dates[index], dates[index - 1]
        btc_close, previous_btc = float(btc_prices[day]), float(btc_prices[previous])
        eth_close, previous_eth = float(eth_prices[day]), float(eth_prices[previous])
        if min(btc_close, previous_btc, eth_close, previous_eth) <= 0:
            raise ValueError(f"Non-positive BTC/ETH close on {day}")
        btc_return = math.log(btc_close / previous_btc)
        eth_return = math.log(eth_close / previous_eth)
        btc_returns[day] = btc_return
        eth_returns[day] = eth_return
        ratio_returns[day] = eth_return - btc_return

    index_by_date = {day: index for index, day in enumerate(dates)}
    candidate_count = len(range(FLOW_WARMUP, len(panel), FLOW_EVENT_STEP))
    skipped = {
        "missing_signal_anchor": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "zero_flow_standard_deviation": 0,
        "invalid_price_returns": 0,
        "invalid_variance": 0,
    }
    events = []
    for panel_index in range(FLOW_WARMUP, len(panel), FLOW_EVENT_STEP):
        flow = panel[panel_index]
        flow_date = flow["date"]
        signal_date = flow_date + dt.timedelta(days=FLOW_EMBARGO_DAYS)
        price_index = index_by_date.get(signal_date)
        if price_index is None:
            skipped["missing_signal_anchor"] += 1
            continue
        if price_index < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if price_index + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior_flows = panel[panel_index - FLOW_WARMUP:panel_index]
        btc_history = [float(row["btc_total_usdm"]) for row in prior_flows]
        eth_history = [float(row["eth_total_usdm"]) for row in prior_flows]
        btc_current = float(flow["btc_total_usdm"])
        eth_current = float(flow["eth_total_usdm"])
        btc_sd = statistics.pstdev(btc_history)
        eth_sd = statistics.pstdev(eth_history)
        if (
            btc_sd <= 1e-12 or eth_sd <= 1e-12
            or not all(math.isfinite(value) for value in btc_history + eth_history + [btc_current, eth_current])
        ):
            skipped["zero_flow_standard_deviation"] += 1
            continue
        z_btc = (btc_current - statistics.fmean(btc_history)) / btc_sd
        z_eth = (eth_current - statistics.fmean(eth_history)) / eth_sd

        prior5_dates = dates[price_index - 4:price_index + 1]
        prior20_dates = dates[price_index - 19:price_index + 1]
        future_dates = dates[price_index + 1:price_index + 1 + TARGET_SESSIONS]
        prior5_ratio = [ratio_returns[day] for day in prior5_dates]
        prior20_ratio = [ratio_returns[day] for day in prior20_dates]
        future_ratio = [ratio_returns[day] for day in future_dates]
        prior5_btc = [btc_returns[day] for day in prior5_dates]
        prior5_eth = [eth_returns[day] for day in prior5_dates]
        windows = prior5_ratio + prior20_ratio + future_ratio + prior5_btc + prior5_eth
        if any(value is None or not math.isfinite(value) for value in windows):
            skipped["invalid_price_returns"] += 1
            continue

        prior20_variance = statistics.fmean(float(value) ** 2 for value in prior20_ratio)
        if not math.isfinite(prior20_variance) or prior20_variance <= 0:
            skipped["invalid_variance"] += 1
            continue
        target_bp = math.fsum(float(value) for value in future_ratio) * 10_000.0
        features = {
            "pre_ratio_return5": math.fsum(float(value) for value in prior5_ratio),
            "pre_ratio_return20": math.fsum(float(value) for value in prior20_ratio),
            "pre_ratio_rv20_log": math.log(prior20_variance),
            "pre_btc_return5": math.fsum(float(value) for value in prior5_btc),
            "pre_eth_return5": math.fsum(float(value) for value in prior5_eth),
            "common_flow_pressure": (z_btc + z_eth) / 2.0,
            "relative_flow_pressure": z_eth - z_btc,
        }
        if not math.isfinite(target_bp) or not all(math.isfinite(value) for value in features.values()):
            skipped["invalid_price_returns"] += 1
            continue
        events.append({
            "flow_date": flow_date,
            "signal_date": signal_date,
            "target_start_date": future_dates[0],
            "target_end_date": future_dates[-1],
            "target_bp": target_bp,
            **features,
        })

    metadata = {
        "candidate_origins": candidate_count,
        "accepted_events": len(events),
        "skipped": skipped,
        "flow_warmup_observations": FLOW_WARMUP,
        "event_step_common_flow_observations": FLOW_EVENT_STEP,
        "flow_embargo_calendar_days": FLOW_EMBARGO_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "first_signal_date": events[0]["signal_date"].isoformat() if events else None,
        "last_signal_date": events[-1]["signal_date"].isoformat() if events else None,
        "first_flow_date": events[0]["flow_date"].isoformat() if events else None,
        "last_flow_date": events[-1]["flow_date"].isoformat() if events else None,
        "target_windows_overlap": any(
            left["target_end_date"] >= right["signal_date"]
            for left, right in zip(events, events[1:])
        ),
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
            augmented = base.fit_ols_predict(train, current, AUGMENTED_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "signal_date": current["signal_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "training_events": len(train),
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
    normalized = []
    for row in rows:
        values = [
            float(row["target_bp"]),
            float(row["baseline_prediction_bp"]),
            float(row["augmented_prediction_bp"]),
        ]
        if not all(math.isfinite(value) for value in values):
            return None
        target, baseline, augmented = values
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        normalized.append((row["signal_date"], difference))
    normalized.sort(key=lambda item: item[0])
    loss_rows = [{"loss_difference_bp2": difference} for _, difference in normalized]
    observed = statistics.fmean(row["loss_difference_bp2"] for row in loss_rows)
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap_means = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(loss_rows, rng, BOOTSTRAP_BLOCK)
        bootstrap_means.append(statistics.fmean(row["loss_difference_bp2"] for row in sample))
    bootstrap_means.sort()
    return {
        "status": "COMPUTED",
        "observations": len(loss_rows),
        "reps": len(bootstrap_means),
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "observed_mean_baseline_minus_augmented_squared_loss_bp2": observed,
        "ci_95_low_bp2": bootstrap_means[int(0.025 * (len(bootstrap_means) - 1))],
        "ci_95_high_bp2": bootstrap_means[int(0.975 * (len(bootstrap_means) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in bootstrap_means) / len(bootstrap_means),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < MIN_VALIDATION_N or test["n"] < MIN_TEST_N or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient validation/test forecasts or paired-loss inference"
    validation_improvement = validation.get("rmse_improvement_pct")
    test_improvement = test.get("rmse_improvement_pct")
    if (
        validation_improvement is not None and test_improvement is not None
        and validation_improvement > 0 and test_improvement > 0
        and paired["ci_95_low_bp2"] > 0
    ):
        return "PROMISING", "PROMISING — both chronological RMSE comparisons improve and the paired test-loss 95% interval favors the augmented model; current-vintage source limitations remain"
    if (
        validation_improvement is not None and test_improvement is not None
        and validation_improvement < 0 and test_improvement < 0
        and paired["ci_95_high_bp2"] < 0
    ):
        return "REJECTED", "REJECTED — both chronological RMSE comparisons worsen and the paired test-loss 95% interval favors the baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish incremental predictive value or decisive inferiority"


def run_research() -> dict:
    panel, btc_prices, eth_prices, source_manifest = fetch_frozen_inputs()
    verify_frozen_source_manifest(source_manifest)
    if set(btc_prices) != set(eth_prices):
        raise FrozenSourceMismatch("BTC and ETH price dates differ after source-manifest validation")
    events, event_metadata = build_events(panel, btc_prices, eth_prices)
    predictions = walk_forward(events)
    validation_rows = [
        row for row in predictions
        if VALIDATION_START <= row["signal_date"] <= VALIDATION_END
    ]
    test_rows = [
        row for row in predictions
        if TEST_START <= row["signal_date"] <= TEST_END
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
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
        "source_preflight_commit_sha": SOURCE_PREFLIGHT_COMMIT_SHA,
        "sample": {
            "flow_start_date": "2024-07-23",
            "flow_cutoff_date": FLOW_CUTOFF_DATE.isoformat(),
            "flow_rows": len(panel),
            "price_start_date": PRICE_START_DATE.isoformat(),
            "price_end_date": PRICE_END_DATE.isoformat(),
            "price_rows_per_symbol": len(btc_prices),
            "eligible_signal_start_date": "2024-07-28",
            "eligible_signal_end_date": TEST_END.isoformat(),
        },
        "source_manifest": source_manifest,
        "model": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUGMENTED_FEATURES,
            "flow_zscore_window": FLOW_WARMUP,
            "event_step_common_flow_observations": FLOW_EVENT_STEP,
            "rolling_training_events": MODEL_WINDOW,
            "target_sessions": TARGET_SESSIONS,
            "validation_start": VALIDATION_START.isoformat(),
            "validation_end": VALIDATION_END.isoformat(),
            "test_start": TEST_START.isoformat(),
            "test_end": TEST_END.isoformat(),
            "minimum_validation_n": MIN_VALIDATION_N,
            "minimum_test_n": MIN_TEST_N,
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_size_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "event_metadata": event_metadata,
        "forecast_count": len(predictions),
        "validation": validation,
        "test": test,
        "paired_test_loss_bootstrap": paired,
        "raw_observations_saved": False,
        "trading_pnl_evaluated": False,
    }


def _display(value) -> str:
    return "not available" if value is None else str(value)


def render_report(result: dict) -> str:
    validation = result.get("validation") or {}
    test = result.get("test") or {}
    val_base = validation.get("baseline") or {}
    val_aug = validation.get("augmented") or {}
    test_base = test.get("baseline") or {}
    test_aug = test.get("augmented") or {}
    paired = result.get("paired_test_loss_bootstrap")
    source_manifest = result.get("source_manifest") or {}
    flow = source_manifest.get("flow_panel") or {}
    prices = source_manifest.get("price_sources") or {}
    btc = prices.get("btc") or {}
    eth = prices.get("eth") or {}
    event = result.get("event_metadata") or {}
    report = f"""# BTC/ETH ETF relative-flow forecast for ETH/BTC — {STAMP}

**Hypothesis:** {HYPOTHESIS_ID}

**Status:** {result.get("status", "FAILED")}  
**Disposition:** {result.get("decision", "INCONCLUSIVE")}  
**Reason:** {result.get("decision_reason", result.get("error", "No result"))}

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}
- Triggering source commit: {SOURCE_SHA}
- Frozen source-preflight run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{SOURCE_PREFLIGHT_RUN_ID}
- Frozen flow-panel SHA-256: {flow.get("sha256", "not available")}
- Frozen BTC archive-manifest SHA-256: {btc.get("archive_manifest_sha256", "not available")}
- Frozen ETH archive-manifest SHA-256: {eth.get("archive_manifest_sha256", "not available")}

## Data and provenance

- Farside common BTC/ETH flow panel: {flow.get("rows", "not available")} rows, {flow.get("first_date", "not available")} through {flow.get("last_date", "not available")}
- Binance BTCUSDT and ETHUSDT Spot 1d UTC: {btc.get("rows", "not available")} / {eth.get("rows", "not available")} rows
- Common price range: {btc.get("start_date", "not available")} through {btc.get("end_date", "not available")}
- Checksum-verified archive counts: BTC {btc.get("archive_count", "not available")}; ETH {eth.get("archive_count", "not available")}
- Raw observations saved: No

## Frozen signal, target and features

Each common Farside flow observation is embargoed for five calendar days. At the Binance daily close dated five days after the U.S. ETF flow date, each asset's current net flow is standardized against the preceding 60 common valid observations for that same asset. The current observation is excluded from its own z-score.

- Common flow pressure: (z_BTC + z_ETH) / 2
- Relative flow pressure: z_ETH - z_BTC
- Target: cumulative ETH/BTC log return over the next five complete UTC daily candles, in basis points
- Baseline: prior 5-session and 20-session ETH/BTC returns, log prior 20-session ETH/BTC realized variance, prior 5-session BTC and ETH returns, and common ETF flow pressure
- Augmented model: baseline plus relative flow pressure
- Rolling training: 65 most recent events whose five-session target ended strictly before the current signal date

## Event construction

- Candidate origins after warm-up: {event.get("candidate_origins", "not available")}
- Accepted events: {event.get("accepted_events", "not available")}
- Walk-forward forecasts: {result.get("forecast_count", "not available")}
- First accepted signal: {event.get("first_signal_date", "not available")}
- Last accepted signal: {event.get("last_signal_date", "not available")}
- Overlapping five-session target windows: {event.get("target_windows_overlap", "not available")}
- Skipped events: {json.dumps(event.get("skipped", {}), sort_keys=True)}

## Forecast results

| Metric | Validation 2025 | Test 2026 |
|---|---:|---:|
| Forecasts | {validation.get("n", 0)} | {test.get("n", 0)} |
| Baseline RMSE (bps) | {_display(val_base.get("rmse_bp"))} | {_display(test_base.get("rmse_bp"))} |
| Augmented RMSE (bps) | {_display(val_aug.get("rmse_bp"))} | {_display(test_aug.get("rmse_bp"))} |
| RMSE improvement (%) | {_display(validation.get("rmse_improvement_pct"))} | {_display(test.get("rmse_improvement_pct"))} |

Paired test squared-loss bootstrap: {json.dumps(paired, sort_keys=True) if paired else "not computed"}.

## Interpretation and limitations

Farside's current-vintage aggregator tables have no historical as-of snapshots or verified publication timestamps. The fixed five-calendar-day embargo is conservative but does not prove that the values were available at the historical signal time. ETF net flows are creations/redemptions, not secondary-market ETF volume, exchange spot order flow or direct evidence of asset purchases at a particular timestamp.

The result is a forecast screen for ETH/BTC, not a trading P&L. No CAGR, Sharpe, drawdown, profitability or deployment claim is made. No parameter tuning was performed. No raw flow or price observations were saved or committed.

## Evidence files

- Manifest: {result.get("manifest_path", "not yet written")}
- Preregistration: [frozen protocol](../../../research/PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md)
- Registry: [hypothesis registry](../../../research/HYPOTHESIS-REGISTRY.md)
"""
    return report


def write_outputs(result: dict) -> tuple[Path, Path]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-etf-relative-flow-ethbtc-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = report_path.relative_to(ROOT).as_posix()
    result["manifest_path"] = manifest_path.relative_to(ROOT).as_posix()
    report_path.write_text(render_report(result), encoding="utf-8")
    result["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(base.json_safe(result), indent=2, sort_keys=True) + chr(10),
        encoding="utf-8",
    )
    return report_path, manifest_path


def update_documents(result: dict, report_path: Path, manifest_path: Path) -> None:
    status = result.get("status")
    if status not in {"COMPLETE", "INCONCLUSIVE/INFEASIBLE"}:
        return
    decision = result.get("decision", "INCONCLUSIVE")
    validation = result.get("validation") or {}
    test = result.get("test") or {}
    paired = result.get("paired_test_loss_bootstrap") or {}
    report_rel = Path(result["report_path"]).as_posix()
    manifest_rel = Path(result["manifest_path"]).as_posix()
    registry_report = "../" + report_rel
    registry_manifest = "../" + manifest_rel
    if status == "COMPLETE":
        row_status = "BACKTESTED"
        disposition = (
            f"decision={decision}; validation/test n={validation.get('n', 0)}/{test.get('n', 0)}; "
            f"RMSE improvement={validation.get('rmse_improvement_pct')}/{test.get('rmse_improvement_pct')}%; "
            f"paired test-loss 95% CI={paired.get('ci_95_low_bp2')}/{paired.get('ci_95_high_bp2')} bp²"
        )
        status_line = (
            f"- **Status:** BACKTESTED; decision={decision}; workflow run {RUN_ID}; "
            f"validation/test forecasts {validation.get('n', 0)}/{test.get('n', 0)}."
        )
    else:
        row_status = "INCONCLUSIVE/INFEASIBLE"
        disposition = "Frozen source mismatch; no model fit or performance conclusion. " + str(result.get("decision_reason", ""))
        status_line = f"- **Status:** INCONCLUSIVE/INFEASIBLE; frozen source mismatch; no model fit; workflow run {RUN_ID}."

    row = (
        f"| {HYPOTHESIS_ID} | {row_status} | Strictly lagged relative U.S. spot BTC-versus-ETH ETF flow pressure may add information "
        "about next-five-session ETH/BTC ratio returns beyond prior BTC/ETH price dynamics and common ETF flow pressure. | "
        "Farside common flow panel 583 rows (2024-07-23–2026-11-16); Binance BTCUSDT/ETHUSDT Spot 1d UTC 879 days each "
        "(2024-07-01–2026-11-26) | "
        f"{disposition} | [preregistration](PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md) / "
        f"[report]({registry_report}) / [manifest]({registry_manifest}) |"
    )
    registry_lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, line in enumerate(registry_lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            registry_lines[index] = row
            replaced = True
            break
    if not replaced:
        registry_lines.extend(["", row])
    REGISTRY_PATH.write_text(chr(10).join(registry_lines) + chr(10), encoding="utf-8")

    prereg = PREREG_PATH.read_text(encoding="utf-8")
    prereg_lines = prereg.splitlines()
    status_index = next(
        (index for index, line in enumerate(prereg_lines) if line.startswith("- **Status:**")),
        None,
    )
    if status_index is not None:
        prereg_lines[status_index] = status_line
    prereg = chr(10).join(prereg_lines)
    section = f"""## 9. Execution result

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}
- Triggering source commit: {result.get("source_commit_sha", SOURCE_SHA)}
- Status: {status}
- Decision: {decision}
- Source-preflight run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{SOURCE_PREFLIGHT_RUN_ID}
- Validation/test forecasts: {validation.get("n", 0)}/{test.get("n", 0)}
- Validation/test RMSE improvement: {validation.get("rmse_improvement_pct", "not computed")}/{test.get("rmse_improvement_pct", "not computed")}
- Paired test-loss bootstrap: {json.dumps(paired, sort_keys=True) if paired else "not computed"}
- Report: ../{report_rel}
- Manifest: ../{manifest_rel}

{result.get("decision_reason", result.get("error", ""))}
"""
    heading = "## 9. Execution result"
    if heading in prereg:
        prereg = prereg.split(heading, 1)[0].rstrip() + chr(10) + chr(10) + section
    else:
        prereg = prereg.rstrip() + chr(10) + chr(10) + section
    PREREG_PATH.write_text(prereg + chr(10), encoding="utf-8")


def main() -> int:
    try:
        result = run_research()
    except FrozenSourceMismatch as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE/INFEASIBLE",
            "decision": "INCONCLUSIVE",
            "decision_reason": str(exc),
            "error": str(exc),
            "source_commit_sha": SOURCE_SHA,
            "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
            "source_preflight_commit_sha": SOURCE_PREFLIGHT_COMMIT_SHA,
            "raw_observations_saved": False,
            "trading_pnl_evaluated": False,
        }
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FAILED",
            "decision": "INCONCLUSIVE",
            "decision_reason": f"Execution failed: {type(exc).__name__}: {exc}",
            "error": f"{type(exc).__name__}: {exc}",
            "source_commit_sha": SOURCE_SHA,
            "source_preflight_run_id": SOURCE_PREFLIGHT_RUN_ID,
            "source_preflight_commit_sha": SOURCE_PREFLIGHT_COMMIT_SHA,
            "raw_observations_saved": False,
            "trading_pnl_evaluated": False,
        }
    result.setdefault("run_id", RUN_ID)
    result.setdefault("run_attempt", RUN_ATTEMPT)
    report_path, manifest_path = write_outputs(result)
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "report_path": report_path.relative_to(ROOT).as_posix(),
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "report_sha256": result.get("report_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
