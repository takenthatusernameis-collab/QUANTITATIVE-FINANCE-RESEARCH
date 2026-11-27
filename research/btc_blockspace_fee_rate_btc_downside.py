#!/usr/bin/env python3
"""Frozen forecast screen: lagged Bitcoin blockspace fee-rate pressure -> BTC downside semivariance."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

import btc_blockspace_fee_rate_source_preflight as fee_source
import stlfsi4_btc_downside_semivariance as btc
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01"
MODEL_START = dt.date(2023, 11, 28)
ACCEPTED_PRICE_MANIFEST = Path("reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json")
ACCEPTED_PRICE_ARCHIVE_MANIFEST_SHA256 = "978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe"
MODEL_WINDOW = 65
TARGET_SESSIONS = 5
EVENT_STEP_DAYS = 6
VALIDATION_START = dt.date(2025, 1, 1)
TEST_START = dt.date(2025, 7, 1)
MIN_VALIDATION_FORECASTS = 25
MIN_TEST_FORECASTS = 60
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 5
BOOTSTRAP_SEED = 20261127
ARCHIVE_WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "btc-blockspace-fee-rate-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md"

BASE_FEATURES = [
    "pre_return5_log",
    "pre_return20_log",
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
]
AUGMENTED_FEATURES = BASE_FEATURES + ["blockspace_fee_pressure_7d"]


class SourceInfeasibleError(RuntimeError):
    """A frozen source gate failed; this is not a model-performance result."""


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_accepted_price_evidence(path: Path | None = None) -> dict:
    manifest_path = path or (ROOT / ACCEPTED_PRICE_MANIFEST)
    if not manifest_path.is_file():
        raise SourceInfeasibleError(f"Accepted Binance source manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = manifest["source_manifest"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SourceInfeasibleError(f"Cannot read accepted Binance source evidence: {exc}") from exc

    required = {
        "symbol": "BTCUSDT",
        "interval": "1d UTC",
        "archive_manifest_sha256": ACCEPTED_PRICE_ARCHIVE_MANIFEST_SHA256,
        "requested_start": "2017-08-17",
        "requested_end": "2026-11-25",
    }
    for key, expected in required.items():
        if source.get(key) != expected:
            raise SourceInfeasibleError(
                f"Accepted Binance source evidence mismatch for {key}: "
                f"expected={expected!r}, observed={source.get(key)!r}"
            )
    coverage = source.get("coverage") or {}
    if (
        coverage.get("missing_dates") != []
        or coverage.get("observed_daily_rows") != 3388
        or coverage.get("expected_daily_rows") != 3388
        or source.get("raw_observations_saved") is not False
    ):
        raise SourceInfeasibleError("Accepted Binance manifest no longer satisfies its frozen completeness contract")
    return source


def fetch_price_archives(
    start_date: dt.date,
    end_date: dt.date,
    accepted_source: dict,
) -> tuple[dict[dt.date, float], dict]:
    specs = btc.build_archive_specs(start_date, end_date, as_of_date=NOW.date())
    accepted_by_url = {row["url"]: row for row in accepted_source.get("archives", [])}
    if not specs:
        raise SourceInfeasibleError("No Binance Vision archives were generated for the frozen price window")

    results: dict[int, tuple[dict, dict]] = {}
    failures: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as executor:
        future_map = {
            executor.submit(btc.download_binance_archive, spec): (index, spec)
            for index, spec in enumerate(specs)
        }
        for future in concurrent.futures.as_completed(future_map):
            index, spec = future_map[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({
                    "period": spec["tag"],
                    "kind": spec["kind"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda row: (row["kind"], row["period"]))
        raise SourceInfeasibleError(
            f"Binance Vision archive/checksum retrieval failed for {len(failures)}/{len(specs)} files: "
            f"{json.dumps(failures, sort_keys=True)}"
        )

    prices: dict[dt.date, float] = {}
    archive_rows = []
    timestamp_units = set()
    for index in range(len(specs)):
        page, row = results[index]
        prior = accepted_by_url.get(row["url"])
        if prior is None:
            raise SourceInfeasibleError(f"Downloaded Binance archive was not part of the accepted source manifest: {row['url']}")
        if (
            row.get("archive_sha256") != prior.get("archive_sha256")
            or row.get("checksum_sha256") != prior.get("checksum_sha256")
            or row.get("checksum_verified") is not True
        ):
            raise SourceInfeasibleError(f"Binance archive differs from previously accepted checksummed evidence: {row['url']}")
        archive_rows.append(row)
        timestamp_units.add(row["timestamp_unit"])
        for day, close in page.items():
            if start_date <= day <= end_date:
                if day in prices:
                    raise SourceInfeasibleError(f"Duplicate BTCUSDT candle across archives: {day}")
                prices[day] = close

    prices = dict(sorted(prices.items()))
    expected_dates = []
    day = start_date
    while day <= end_date:
        expected_dates.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected_dates if day not in prices]
    if missing:
        raise SourceInfeasibleError(
            f"BTCUSDT accepted archive subset has {len(missing)} missing dates; "
            f"first={missing[0]}, last={missing[-1]}"
        )
    archive_sha = sha256(json.dumps(archive_rows, sort_keys=True, separators=(",", ":")).encode())
    return prices, {
        "symbol": "BTCUSDT",
        "source": "Binance Vision official Spot monthly/daily 1d UTC klines",
        "interval": "1d UTC",
        "first_date": min(prices).isoformat(),
        "last_date": max(prices).isoformat(),
        "rows": len(prices),
        "archive_count": len(archive_rows),
        "archive_manifest_sha256": archive_sha,
        "accepted_full_history_archive_manifest_sha256": accepted_source["archive_manifest_sha256"],
        "accepted_full_history_manifest_path": str(ACCEPTED_PRICE_MANIFEST),
        "archives": archive_rows,
        "timestamp_units_observed": sorted(timestamp_units),
        "all_downloaded_archives_match_previously_accepted_checksums": True,
        "raw_observations_saved": False,
    }


def fetch_sources() -> tuple[dict[dt.date, float], dict[dt.date, float], dict]:
    # The Mempool endpoint is deliberately called exactly once; its own fetcher never retries.
    try:
        body, http_status, final_url, headers = fee_source.fetch_fee_rate_payload()
        fee_bins, fee_summary = fee_source.parse_fee_rate_payload(body)
        fee_daily, fee_coverage = fee_source.validate_coverage(fee_bins, NOW)
    except Exception as exc:
        raise SourceInfeasibleError(f"Frozen Mempool source acceptance failed: {type(exc).__name__}: {exc}") from exc

    if http_status != 200 or final_url.rstrip("/") != fee_source.ENDPOINT.rstrip("/"):
        raise SourceInfeasibleError(f"Unexpected Mempool response: HTTP {http_status}, final URL {final_url}")
    if fee_coverage["first_utc_date"] != MODEL_START.isoformat():
        raise SourceInfeasibleError(
            f"Mempool first accepted date differs from frozen common-window start: {fee_coverage['first_utc_date']}"
        )

    accepted_price = load_accepted_price_evidence()
    accepted_end = dt.date.fromisoformat(accepted_price["requested_end"])
    price_end = min(NOW.date() - dt.timedelta(days=2), accepted_end)
    if price_end < MODEL_START + dt.timedelta(days=900):
        raise SourceInfeasibleError(f"Accepted BTC price window is too short: {MODEL_START} through {price_end}")
    prices, price_source = fetch_price_archives(MODEL_START, price_end, accepted_price)

    fee_source_manifest = {
        "provider": "Mempool Open Source Project REST API",
        "endpoint": fee_source.ENDPOINT,
        "http_status": http_status,
        "final_url": final_url,
        "api_requests": 1,
        "retry_count": 0,
        "response_bytes": len(body),
        "response_sha256": sha256(body),
        "retrieved_at_utc": NOW.isoformat(),
        "coverage": fee_coverage,
        "summary": fee_summary,
        "rate_limit_headers": {
            key: value for key, value in headers.items()
            if "rate" in key.lower() or "retry" in key.lower()
        },
        "raw_observations_saved": False,
    }
    coverage = validate_coverage(fee_daily, prices)
    return fee_daily, prices, {
        "fee_rate": fee_source_manifest,
        "BTCUSDT": price_source,
        "coverage": coverage,
    }


def validate_coverage(fee_daily: dict[dt.date, float], prices: dict[dt.date, float]) -> dict:
    fee_dates, price_dates = sorted(fee_daily), sorted(prices)
    if not fee_dates or not price_dates:
        raise SourceInfeasibleError("Fee-rate or BTC price series is empty")
    if fee_dates[0] != MODEL_START:
        raise SourceInfeasibleError(f"Fee-rate history starts at {fee_dates[0]}, not {MODEL_START}")
    if price_dates[0] != MODEL_START:
        raise SourceInfeasibleError(f"BTC price history starts at {price_dates[0]}, not {MODEL_START}")
    if any((right - left).days != 1 for left, right in zip(fee_dates, fee_dates[1:])):
        raise SourceInfeasibleError("Mempool completed daily fee-rate history has an internal date gap")
    if any((right - left).days != 1 for left, right in zip(price_dates, price_dates[1:])):
        raise SourceInfeasibleError("BTCUSDT daily candles have an internal UTC date gap")
    if price_dates[-1] > fee_dates[-1]:
        raise SourceInfeasibleError("BTC price history extends beyond accepted fee-rate history")
    if len(price_dates) < 900:
        raise SourceInfeasibleError(f"Insufficient common BTC price history: {len(price_dates)} days")
    return {
        "first_common_utc_date": max(fee_dates[0], price_dates[0]).isoformat(),
        "last_btc_price_utc_date": price_dates[-1].isoformat(),
        "last_completed_fee_rate_utc_date": fee_dates[-1].isoformat(),
        "btc_price_rows": len(price_dates),
        "fee_rate_daily_rows": len(fee_dates),
        "common_price_window_contiguous": True,
        "raw_observations_saved": False,
    }


def build_events(
    fee_daily: dict[dt.date, float],
    prices: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    if len(dates) < 21:
        raise ValueError("Insufficient BTC history for 20-session baseline features")
    if any((right - left).days != 1 for left, right in zip(dates, dates[1:])):
        raise ValueError("BTC prices are not a contiguous daily UTC series")

    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        returns.append(math.log(prices[dates[index]] / prices[dates[index - 1]]))
    index_by_date = {day: index for index, day in enumerate(dates)}

    first_signal = max(dates[20], min(fee_daily) + dt.timedelta(days=8))
    last_signal = dates[-1] - dt.timedelta(days=TARGET_SESSIONS)
    events = []
    skipped = {
        "missing_fee_lag": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
    }
    candidate_dates = []
    signal = first_signal
    while signal <= last_signal:
        candidate_dates.append(signal)
        signal += dt.timedelta(days=EVENT_STEP_DAYS)

    for signal in candidate_dates:
        j = index_by_date.get(signal)
        if j is None:
            skipped["insufficient_price_history"] += 1
            continue
        fee_lag_1 = signal - dt.timedelta(days=1)
        fee_lag_8 = signal - dt.timedelta(days=8)
        if fee_lag_1 not in fee_daily or fee_lag_8 not in fee_daily:
            skipped["missing_fee_lag"] += 1
            continue
        if j < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior5 = returns[j - 4:j + 1]
        prior20 = returns[j - 19:j + 1]
        future = returns[j + 1:j + 1 + TARGET_SESSIONS]
        if any(value is None for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue

        prior5_values = [float(value) for value in prior5]
        prior20_values = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        fee_feature = math.log1p(fee_daily[fee_lag_1]) - math.log1p(fee_daily[fee_lag_8])
        events.append({
            "record_date": signal,
            "signal_date": signal,
            "target_start_date": dates[j + 1],
            "target_end_date": dates[j + TARGET_SESSIONS],
            "fee_lag_1_date": fee_lag_1,
            "fee_lag_8_date": fee_lag_8,
            "fee_lag_1_sat_vb": fee_daily[fee_lag_1],
            "fee_lag_8_sat_vb": fee_daily[fee_lag_8],
            "blockspace_fee_pressure_7d": fee_feature,
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
            "pre_return5_log": math.fsum(prior5_values),
            "pre_return20_log": math.fsum(prior20_values),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior5_values)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(prior20_values)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(prior20_values)),
        })

    for left, right in zip(events, events[1:]):
        gap_days = (right["signal_date"] - left["signal_date"]).days
        if gap_days != EVENT_STEP_DAYS:
            raise ValueError("Accepted signal origins do not follow the frozen six-calendar-day schedule")
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("Five-session target windows overlap or are not fully matured")

    return events, {
        "candidate_origins": len(candidate_dates),
        "accepted_events": len(events),
        "skipped": skipped,
        "event_spacing_calendar_days": EVENT_STEP_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "target_windows_overlap": False,
        "first_signal_date": events[0]["signal_date"].isoformat() if events else None,
        "last_signal_date": events[-1]["signal_date"].isoformat() if events else None,
        "first_target_end_date": events[0]["target_end_date"].isoformat() if events else None,
        "last_target_end_date": events[-1]["target_end_date"].isoformat() if events else None,
    }


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
            "record_date": current["signal_date"],
            "signal_date": current["signal_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "train_n": len(train),
            "train_last_signal_date": max(row["signal_date"] for row in train),
            "train_last_target_end_date": max(row["target_end_date"] for row in train),
        })
    return predictions


def summarize(rows: list[dict]) -> dict:
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    if baseline is None or augmented is None:
        return {
            "n": len(rows), "baseline": baseline, "augmented": augmented,
            "rmse_improvement_pct": None,
        }
    return {
        "n": len(rows),
        "baseline": baseline,
        "augmented": augmented,
        "rmse_improvement_pct": (
            100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
            if baseline["rmse_bp"] > 0 else None
        ),
    }


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    differences = [
        {
            "loss_difference": (row["baseline_prediction_bp"] - row["target_bp"]) ** 2
            - (row["augmented_prediction_bp"] - row["target_bp"]) ** 2
        }
        for row in rows
    ]
    if any(not math.isfinite(row["loss_difference"]) for row in differences):
        return None
    observed = statistics.fmean(row["loss_difference"] for row in differences)
    rng = random.Random(BOOTSTRAP_SEED)
    means = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(differences, rng, BOOTSTRAP_BLOCK)
        means.append(statistics.fmean(row["loss_difference"] for row in sample))
    means.sort()
    return {
        "status": "COMPUTED",
        "observations": len(differences),
        "reps": len(means),
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "mean_baseline_minus_augmented_squared_loss": observed,
        "ci_95_low": means[int(0.025 * (len(means) - 1))],
        "ci_95_high": means[int(0.975 * (len(means) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in means) / len(means),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if (
        validation["n"] < MIN_VALIDATION_FORECASTS
        or test["n"] < MIN_TEST_FORECASTS
        or paired is None
    ):
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient validation/test forecasts or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi >= 1.0 and ti >= 1.0 and paired["ci_95_low"] > 0:
        return "GO", "GO (research-only) — validation and test RMSE each improve by at least 1.0%, and the paired test-loss 95% confidence interval is entirely above zero"
    if vi is not None and ti is not None and vi <= 0.0 and ti <= 0.0 and paired["ci_95_high"] < 0:
        return "REJECTED", "REJECTED — neither validation nor test RMSE improves, and the paired test-loss 95% confidence interval is entirely below zero"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish incremental predictive value or decisive inferiority"


def run_research() -> dict:
    fee_daily, prices, sources = fetch_sources()
    events, event_meta = build_events(fee_daily, prices)
    if not events:
        raise SourceInfeasibleError("No complete six-day-spaced forecast events passed the frozen event gates")
    predictions = walk_forward(events)
    validation = summarize([
        row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START
    ])
    test = summarize([row for row in predictions if row["signal_date"] >= TEST_START])
    paired = paired_loss_bootstrap([row for row in predictions if row["signal_date"] >= TEST_START])
    decision, disposition = decide(validation, test, paired)
    registry_status = "BACKTESTED" if decision == "GO" else decision
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": registry_status,
        "decision": decision,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "The UTC 2026-11-27 minimum was already met by the distinct ETF-relative-flow real-data forecast screen; this is an additional hypothesis backtest.",
        "coverage": sources["coverage"],
        "data_sources": {"Mempool_fee_rate": sources["fee_rate"], "BTCUSDT": sources["BTCUSDT"]},
        "event_construction": event_meta,
        "data_scope": (
            f"Mempool.space avgFee_75 12h bins, daily median {sources['fee_rate']['coverage']['first_utc_date']} "
            f"to {sources['fee_rate']['coverage']['last_utc_date']} ("
            f"{sources['fee_rate']['coverage']['unique_utc_dates']} complete dates); "
            f"Binance BTCUSDT Spot 1d UTC {sources['BTCUSDT']['first_date']} to "
            f"{sources['BTCUSDT']['last_date']} ({sources['BTCUSDT']['rows']} candles); "
            "six-calendar-day events; validation 2025-H1; test 2025-H2 onward"
        ),
        "methodology": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUGMENTED_FEATURES,
            "predictor": "log1p(daily_median_avgFee_75[t-1]) - log1p(daily_median_avgFee_75[t-8]); avgFee_75 is sat/vB",
            "availability": "One full UTC-day embargo; only completed fee-rate dates t-1 and t-8 are used at the close of BTC day t",
            "target": "log1p(mean squared negative BTC daily log returns over t+1 through t+5, multiplied by 10,000; percentage-points-squared units)",
            "event_spacing_calendar_days": EVENT_STEP_DAYS,
            "rolling_training_events": MODEL_WINDOW,
            "training_rule": "latest 65 events whose signal_date and target_end_date are both strictly earlier than the current signal date",
            "validation": "2025-01-01 through 2025-06-30",
            "test": "2025-07-01 through latest eligible signal date",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_test_loss_bootstrap": paired,
        "limitations": [
            "Mempool's three-year endpoint is current-vintage and does not reconstruct historical API publication timestamps or point-in-time revisions; the frozen one-day embargo does not eliminate all vintage risk.",
            "Each avgFee_75 value is an average of underlying block-level p75 feerates within a 12-hour bin; the daily feature is the median of two bin averages, not the median of all block-level p75 values in a UTC day.",
            "The fee-rate series is a blockspace price/congestion proxy, not a direct measure of transaction count, backlog, exchange flows, investor positioning or forced selling.",
            "The model is a BTC Spot forecast screen, not an executable strategy or P&L. No trading profitability, causal or live-deployment claim is made.",
            "The price series is one venue's BTCUSDT Spot close. The downloaded archive subset was checksum-matched to the previously accepted 2017-08-17 through 2026-11-25 source manifest.",
            "No raw fee-rate or price observations are saved or committed; only hashes, source metadata and aggregate results are retained.",
        ],
    }


def render_report(result: dict) -> str:
    lines = [
        f"# Research session — Bitcoin blockspace fee-rate pressure and BTC downside semivariance ({STAMP})",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Decision:** {result.get('decision', result.get('status'))}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi')}",
        "- **Implementation timebox:** MEDIUM; 4 substantive cycles maximum; implementation deadline 2026-11-30T13:55:51Z; final conclusion deadline 2026-12-02T13:55:51Z.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Triggering commit:** {SOURCE_SHA}",
        "",
    ]
    if result.get("error"):
        lines += ["## Source/implementation blocker", "", f"- {result['error']}", "- No valid empirical backtest completed; this attempt does not count as a new backtest.", ""]
    else:
        v, t = result["validation_metrics"], result["test_metrics"]
        lines += [
            "## Frozen method", "",
            "- Predictor: log1p of the daily median of two 12-hour-bin avgFee_75 averages at t-1 minus the same value at t-8; one full UTC-day embargo.",
            "- Baseline: prior 5- and 20-session BTC momentum, prior 5- and 20-session downside semivariance, and prior 20-session total realized variance.",
            "- Augmented model: baseline plus exactly one blockspace fee-pressure feature.",
            "- Target: log1p of next-five-session BTC downside semivariance; signal-day return excluded.",
            "- Event spacing: every six UTC calendar days; five-session target windows do not overlap.",
            "- Rolling training: latest 65 fully matured prior events. Validation: 2025-H1. Test: 2025-07-01 onward.",
            "- Estimator: standardized OLS with the repository's fixed 1e-8 coefficient ridge stabilization; no tuning.",
            "",
            "## Data provenance", "",
            "| Source | Coverage | Rows / events | SHA-256 |", "|---|---|---:|---|",
            f"| Mempool avgFee_75 | {result['data_sources']['Mempool_fee_rate']['coverage']['first_utc_date']} to {result['data_sources']['Mempool_fee_rate']['coverage']['last_utc_date']} | {result['data_sources']['Mempool_fee_rate']['coverage']['unique_utc_dates']} completed dates | {result['data_sources']['Mempool_fee_rate']['response_sha256']} |",
            f"| Binance BTCUSDT | {result['data_sources']['BTCUSDT']['first_date']} to {result['data_sources']['BTCUSDT']['last_date']} | {result['data_sources']['BTCUSDT']['rows']} candles; {result['data_sources']['BTCUSDT']['archive_count']} archives | {result['data_sources']['BTCUSDT']['archive_manifest_sha256']} |",
            f"| Previously accepted full BTC history | 2017-08-17 to 2026-11-25 | 3,388 daily candles | {result['data_sources']['BTCUSDT']['accepted_full_history_archive_manifest_sha256']} |",
            "",
            "## Walk-forward results", "",
            "| Metric | Validation 2025-H1 | Test 2025-07-01 onward |", "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE, log1p semivariance | {v['baseline']['rmse_bp'] if v['baseline'] else None} | {t['baseline']['rmse_bp'] if t['baseline'] else None} |",
            f"| Augmented RMSE, log1p semivariance | {v['augmented']['rmse_bp'] if v['augmented'] else None} | {t['augmented']['rmse_bp'] if t['augmented'] else None} |",
            f"| RMSE improvement | {v['rmse_improvement_pct']}% | {t['rmse_improvement_pct']}% |",
            "",
            "## Paired test-loss uncertainty", "",
            f"- {json.dumps(base.json_safe(result.get('paired_test_loss_bootstrap')), sort_keys=True)}", "",
            "## Interpretation", "", result.get("disposition", "No disposition established."), "",
            "## Verified / unverified", "",
            "**VERIFIED:** accepted Mempool schema and coverage, one-day embargo, Binance archive checksum identity against previously accepted evidence, event maturity, walk-forward mechanics and the frozen metrics under this code/data vintage.",
            "**UNVERIFIED:** point-in-time API publication/revision history, independent source replication, causal interpretation, future-regime stability and instrument-level economic value.",
            "",
            "## Limitations", "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines += ["", "## Reproducibility", "", f"- Workflow: https://github.com/{base.REPO}/actions/runs/{RUN_ID}", "- Implementation: research/btc_blockspace_fee_rate_btc_downside.py", "- Tests: research/test_btc_blockspace_fee_rate_btc_downside.py", ""]
    return "\n".join(lines)


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE/INFEASIBLE")
    decision = result.get("decision", status)
    disposition = result.get("disposition", "INCONCLUSIVE/INFEASIBLE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete")
    v = result.get("validation_metrics") or {}
    t = result.get("test_metrics") or {}
    summary = (
        f"decision={decision}; validation/test n={v.get('n', 0)}/{t.get('n', 0)}, "
        f"RMSE improvement={v.get('rmse_improvement_pct')}/{t.get('rmse_improvement_pct')} percent; forecast-only"
    )
    report_link, manifest_link = "../" + report_path, "../" + manifest_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged seven-calendar-day increase in the daily median of two 12-hour-bin averages of block-level 75th-percentile Bitcoin feerates may add information about next-five-UTC-day BTC downside semivariance beyond recent downside risk, realized variance and momentum. | "
        f"{scope} | {disposition}; {summary} | [preregistration](PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md) / [report]({report_link}) / [manifest]({manifest_link}) |"
    )
    registry_lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is None:
        separator = next((i for i, line in enumerate(registry_lines) if line.startswith("|---")), None)
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        registry_lines.insert(separator + 1, row)
    else:
        registry_lines[existing] = row
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    prereg_lines = PREREG_PATH.read_text(encoding="utf-8").splitlines()
    status_line = f"- **Status:** {status}; decision={decision}. {'One frozen real-data backtest completed.' if result.get('completed_backtest') else 'No valid empirical backtest completed.'}"
    found = False
    for index, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[index] = status_line
            found = True
            break
    if not found:
        hypothesis_index = next((i for i, line in enumerate(prereg_lines) if line.startswith("- **Hypothesis ID:**")), None)
        if hypothesis_index is None:
            raise ValueError("Preregistration has no embedded Hypothesis ID line")
        prereg_lines.insert(hypothesis_index + 1, status_line)
    prereg_text = "\n".join(prereg_lines).split("\n## Empirical disposition")[0].rstrip()
    prereg_text += (
        "\n\n## Empirical disposition\n\n"
        f"- **Final status:** {status}; decision={decision}.\n"
        f"- **Disposition:** {disposition}.\n"
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}.\n"
        f"- **Data scope:** {scope}.\n"
        f"- **Validation metrics:** {json.dumps(base.json_safe(v), sort_keys=True)}.\n"
        f"- **Test metrics:** {json.dumps(base.json_safe(t), sort_keys=True)}.\n"
        f"- **Paired test-loss bootstrap:** {json.dumps(base.json_safe(result.get('paired_test_loss_bootstrap')), sort_keys=True)}.\n"
        f"- **Report:** [{report_path}]({report_link}).\n"
        f"- **Manifest:** [{manifest_path}]({manifest_link}).\n"
        "- Forecast-only; no causal, trading or deployment claim.\n"
    )
    PREREG_PATH.write_text(prereg_text + "\n", encoding="utf-8")


def write_outputs(result: dict) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-btc-blockspace-feerate-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = str(report_path.relative_to(ROOT))
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_documents(result, result["report_path"], result["manifest_path"])
    return result["report_path"], result["manifest_path"]


def main() -> int:
    try:
        result = run_research()
    except SourceInfeasibleError as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE/INFEASIBLE",
            "decision": "INCONCLUSIVE/INFEASIBLE",
            "disposition": f"INCONCLUSIVE/INFEASIBLE — frozen source acceptance failed: {error}",
            "completed_backtest": False,
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "The UTC 2026-11-27 minimum was already met by the distinct ETF-relative-flow real-data forecast screen; this source-infeasible attempt does not count as another backtest.",
            "data_scope": "source acceptance incomplete",
            "error": error,
        }
    report_path, manifest_path = write_outputs(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result["status"],
        "decision": result.get("decision"),
        "completed_backtest": result.get("completed_backtest", False),
        "report_path": report_path,
        "manifest_path": manifest_path,
        "validation_n": (result.get("validation_metrics") or {}).get("n"),
        "test_n": (result.get("test_metrics") or {}).get("n"),
        "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
