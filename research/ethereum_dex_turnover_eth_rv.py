#!/usr/bin/env python3
"""Frozen walk-forward forecast: lagged Ethereum DEX turnover / ETH Spot realized variance."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
import os
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
import treasury_auction_demand as base
import ethereum_dex_turnover_eth_rv_source_preflight as preflight

HYPOTHESIS_ID = "QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01"
PREFLIGHT_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "reports/generated/ethereum-dex-turnover-eth-rv-source-preflight"
    / "46097000508-attempt-1/preflight.json"
)
EXPECTED_PREFLIGHT_RUN_ID = "46097000508"
EXPECTED_PREFLIGHT_SOURCE_SHA = "aa59537e1a7938bddd8b4fd0b64bad4c73f271be"
EXPECTED_PREFLIGHT_MANIFEST_SHA256 = "1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6"
EXPECTED_PREFLIGHT_ARTIFACT_ID = 15243896011
EXPECTED_PREFLIGHT_ARTIFACT_SHA256 = "5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49"

VALIDATION_START = dt.date(2023, 1, 1)
TEST_START = dt.date(2025, 1, 1)
TRAIN_WINDOW = 252
MIN_TRAIN_EVENTS = 180
MIN_FORECASTS_PER_SPLIT = 300
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 7
BOOTSTRAP_SEED = 20261128
IMPLEMENTATION_DEADLINE = dt.datetime(2026, 11, 30, 1, 42, 11, tzinfo=dt.timezone.utc)
FINAL_DEADLINE = dt.datetime(2026, 12, 3, 1, 42, 11, tzinfo=dt.timezone.utc)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "ethereum-dex-turnover-eth-rv" / f"{RUN_ID}-attempt-{ATTEMPT}"

BASE_FEATURES = ("pre_rv24_log", "pre_rv168_log", "abs_return24_bps")
AUG_FEATURES = BASE_FEATURES + ("dex_turnover_7d_log",)
SECONDS_PER_HOUR = 3600


class SourceMismatchError(RuntimeError):
    pass


def load_frozen_manifest() -> tuple[dict, str]:
    if not PREFLIGHT_MANIFEST.is_file():
        raise SourceMismatchError(f"accepted source-preflight manifest is missing: {PREFLIGHT_MANIFEST}")
    raw = PREFLIGHT_MANIFEST.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != EXPECTED_PREFLIGHT_MANIFEST_SHA256:
        raise SourceMismatchError(
            f"source-preflight manifest SHA-256 mismatch: expected={EXPECTED_PREFLIGHT_MANIFEST_SHA256}, actual={actual_sha}"
        )
    try:
        frozen = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceMismatchError(f"source-preflight manifest is invalid JSON: {exc}") from exc
    if frozen.get("status") != "PASS" or frozen.get("hypothesis_id") != HYPOTHESIS_ID:
        raise SourceMismatchError("frozen source-preflight manifest is not a PASS for this hypothesis")
    if str(frozen.get("workflow_run_id")) != EXPECTED_PREFLIGHT_RUN_ID:
        raise SourceMismatchError("frozen source-preflight workflow run ID differs from the preregistered run")
    if frozen.get("source_commit_sha") != EXPECTED_PREFLIGHT_SOURCE_SHA:
        raise SourceMismatchError("frozen source-preflight source commit differs from the preregistered commit")
    if frozen.get("backtest_run") is not False or frozen.get("raw_observations_saved") is not False:
        raise SourceMismatchError("source-preflight artifact is not a read-only, source-only manifest")
    hourly = frozen.get("binance_hourly_archives", {})
    if (
        hourly.get("monthly_archive_count") != 70
        or hourly.get("daily_gap_repair_archive_count") != 7
        or hourly.get("expected_hourly_rows") != 51120
        or hourly.get("observed_hourly_rows") != 51106
        or hourly.get("missing_hours") != 14
        or hourly.get("maximum_consecutive_missing_hours") != 4
    ):
        raise SourceMismatchError("frozen hourly source coverage no longer matches the accepted source record")
    return frozen, actual_sha


def assert_archive_record_matches(actual: dict, frozen: dict) -> None:
    for key in (
        "period_type",
        "period",
        "url",
        "checksum_url",
        "archive_sha256",
        "checksum_sha256",
        "checksum_verified",
        "rows",
        "timestamp_unit",
        "close_time_validation",
        "first_timestamp",
        "last_timestamp",
    ):
        if actual.get(key) != frozen.get(key):
            raise SourceMismatchError(
                f"Binance archive provenance changed for {frozen.get('period')}: "
                f"{key} expected={frozen.get(key)!r}, actual={actual.get(key)!r}"
            )


def download_frozen_archive(record: dict) -> tuple[dict, dict]:
    filename = record["url"].rsplit("/", 1)[-1]
    spec = {
        "kind": record["period_type"],
        "tag": record["period"],
        "filename": filename,
        "url": record["url"],
    }
    rows, actual = preflight.download_archive(spec)
    assert_archive_record_matches(actual, record)
    return rows, actual


def download_archive_group(records: list[dict]) -> list[tuple[dict, dict]]:
    results: dict[int, tuple[dict, dict]] = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=preflight.WORKERS) as executor:
        futures = {
            executor.submit(download_frozen_archive, record): (index, record)
            for index, record in enumerate(records)
        }
        for future in concurrent.futures.as_completed(futures):
            index, record = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({
                    "period": record.get("period"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda row: str(row["period"]))
        raise SourceMismatchError(f"frozen Binance archive revalidation failed: {json.dumps(failures, sort_keys=True)}")
    return [results[index] for index in range(len(records))]


def fetch_frozen_sources(frozen: dict, manifest_sha: str) -> tuple[dict, dict, dict, dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        dex_future = executor.submit(base.fetch_bytes, preflight.DEX_URL, 40)
        tvl_future = executor.submit(base.fetch_bytes, preflight.TVL_URL, 40)
        market_future = executor.submit(base.fetch_bytes, preflight.BINANCE_EXCHANGE_INFO_URL, 30)
        dex_body = dex_future.result()
        tvl_body = tvl_future.result()
        market_body = market_future.result()

    dex = preflight.parse_dex_history(dex_body)
    tvl = preflight.parse_tvl_history(tvl_body)
    dex_coverage = preflight.validate_daily_coverage(dex, "Ethereum DEX daily notional volume")
    tvl_coverage = preflight.validate_daily_coverage(tvl, "Ethereum DeFi TVL", require_positive=True)
    dex_canonical = preflight.canonical_daily_sha256(dex)
    tvl_canonical = preflight.canonical_daily_sha256(tvl)
    frozen_dex = frozen["dex_source"]
    frozen_tvl = frozen["tvl_source"]
    if dex_canonical != frozen_dex["canonical_daily_sha256"]:
        raise SourceMismatchError("DeFiLlama DEX values inside the frozen sample window changed after source acceptance")
    if tvl_canonical != frozen_tvl["canonical_daily_sha256"]:
        raise SourceMismatchError("DeFiLlama TVL values inside the frozen sample window changed after source acceptance")
    for label, current, expected in (
        ("DEX", dex_coverage, frozen_dex),
        ("TVL", tvl_coverage, frozen_tvl),
    ):
        for key in ("rows_in_frozen_window", "first_date", "last_date", "maximum_gap_days"):
            if current.get(key) != expected.get(key):
                raise SourceMismatchError(
                    f"DeFiLlama {label} coverage changed for {key}: "
                    f"expected={expected.get(key)!r}, actual={current.get(key)!r}"
                )

    market_info = preflight.validate_exchange_info(market_body)
    frozen_market = frozen["binance_market"]
    for key in ("symbol", "status", "base_asset", "quote_asset", "spot_trading_allowed"):
        if market_info.get(key) != frozen_market.get(key):
            raise SourceMismatchError(f"Binance ETHUSDT market metadata changed for {key}")

    hourly_frozen = frozen["binance_hourly_archives"]
    monthly_records = hourly_frozen["monthly_archives"]
    daily_records = hourly_frozen["daily_gap_repairs"]
    if len(monthly_records) != 70 or len(daily_records) != 7:
        raise SourceMismatchError("frozen archive manifest has an unexpected number of monthly or daily archives")

    monthly_results = download_archive_group(monthly_records)
    monthly_parts = [(rows, actual["timestamp_unit"]) for rows, actual in monthly_results]
    prices, timestamp_units = preflight.merge_hourly_archive_parts(monthly_parts)

    daily_results = download_archive_group(daily_records)
    daily_patch_records = []
    for record, (daily_prices, _) in zip(daily_records, daily_results):
        day = dt.date.fromisoformat(record["period"])
        prices, patch = preflight.reconcile_daily_gap_patch(prices, daily_prices, day)
        for key in ("overlap_match_count", "daily_missing_hours", "filled_hour_count", "filled_hours"):
            if patch.get(key) != record.get(key):
                raise SourceMismatchError(
                    f"Binance daily gap-repair result changed for {record['period']} {key}: "
                    f"expected={record.get(key)!r}, actual={patch.get(key)!r}"
                )
        daily_patch_records.append({"period": record["period"], **patch})

    hourly_coverage = preflight.validate_hourly_coverage(prices)
    for key in (
        "expected_hourly_rows",
        "observed_hourly_rows",
        "missing_hours",
        "missing_timestamps",
        "missing_dates",
        "maximum_consecutive_missing_hours",
        "canonical_close_sha256",
        "first_timestamp",
        "last_timestamp",
    ):
        if hourly_coverage.get(key) != hourly_frozen.get(key):
            raise SourceMismatchError(
                f"re-fetched ETHUSDT hourly coverage changed for {key}: "
                f"expected={hourly_frozen.get(key)!r}, actual={hourly_coverage.get(key)!r}"
            )
    if timestamp_units != hourly_frozen.get("timestamp_units_observed"):
        raise SourceMismatchError(
            f"Binance timestamp-unit population changed: expected={hourly_frozen.get('timestamp_units_observed')}, "
            f"actual={timestamp_units}"
        )
    if not math.isclose(
        hourly_coverage["missing_fraction"],
        hourly_frozen["missing_fraction"],
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise SourceMismatchError("ETHUSDT hourly missing fraction changed after source acceptance")

    source_info = {
        "preflight_run_id": EXPECTED_PREFLIGHT_RUN_ID,
        "preflight_source_commit_sha": EXPECTED_PREFLIGHT_SOURCE_SHA,
        "preflight_manifest_path": str(PREFLIGHT_MANIFEST.relative_to(ROOT)),
        "preflight_manifest_sha256": manifest_sha,
        "preflight_artifact_id": EXPECTED_PREFLIGHT_ARTIFACT_ID,
        "preflight_artifact_zip_sha256": EXPECTED_PREFLIGHT_ARTIFACT_SHA256,
        "dex": {
            "endpoint": preflight.DEX_URL,
            "response_sha256_at_preflight": frozen_dex["response_sha256"],
            "response_sha256_refetched": hashlib.sha256(dex_body).hexdigest(),
            "canonical_daily_sha256": dex_canonical,
            **dex_coverage,
        },
        "tvl": {
            "endpoint": preflight.TVL_URL,
            "response_sha256_at_preflight": frozen_tvl["response_sha256"],
            "response_sha256_refetched": hashlib.sha256(tvl_body).hexdigest(),
            "canonical_daily_sha256": tvl_canonical,
            **tvl_coverage,
        },
        "binance_market": {
            "endpoint": preflight.BINANCE_EXCHANGE_INFO_URL,
            "response_sha256_refetched": hashlib.sha256(market_body).hexdigest(),
            **market_info,
        },
        "hourly_klines": {
            "symbol": "ETHUSDT",
            "interval": "1h UTC",
            "monthly_archive_count": len(monthly_records),
            "daily_gap_repair_archive_count": len(daily_records),
            "timestamp_units_observed": timestamp_units,
            **hourly_coverage,
            "daily_gap_repairs": daily_patch_records,
        },
    }
    return dex, tvl, prices, source_info


def hourly_returns(closes: dict[dt.datetime, float]) -> dict[int, float]:
    """Return only exact adjacent-bar close-to-close log returns; never bridge a gap."""
    result = {}
    for stamp, close in sorted(closes.items()):
        previous_stamp = stamp - dt.timedelta(hours=1)
        previous = closes.get(previous_stamp)
        if previous is None:
            continue
        if not math.isfinite(float(previous)) or not math.isfinite(float(close)) or previous <= 0 or close <= 0:
            raise ValueError(f"non-finite or non-positive hourly close around {stamp.isoformat()}")
        result[int(stamp.timestamp())] = math.log(float(close) / float(previous))
    return result


def window_returns(returns: dict[int, float], start_ts: int, periods: int) -> list[float] | None:
    values = []
    for offset in range(periods):
        stamp = start_ts + offset * SECONDS_PER_HOUR
        value = returns.get(stamp)
        if value is None:
            return None
        values.append(float(value))
    return values


def realized_variance_bp2(values: list[float]) -> float:
    return math.fsum((value * 10_000.0) ** 2 for value in values)


def build_events(
    dex: dict[dt.date, float],
    tvl: dict[dt.date, float],
    closes: dict[dt.datetime, float],
) -> tuple[list[dict], dict]:
    returns = hourly_returns(closes)
    skipped = Counter()
    events = []
    day = preflight.SAMPLE_START + dt.timedelta(days=8)
    while day <= preflight.SAMPLE_END:
        feature_dates = [day - dt.timedelta(days=offset) for offset in range(8, 1, -1)]
        if any(feature_day not in dex for feature_day in feature_dates):
            skipped["missing_dex_feature_date"] += 1
            day += dt.timedelta(days=1)
            continue
        if any(feature_day not in tvl for feature_day in feature_dates):
            skipped["missing_tvl_feature_date"] += 1
            day += dt.timedelta(days=1)
            continue

        dex_values = [float(dex[feature_day]) for feature_day in feature_dates]
        tvl_values = [float(tvl[feature_day]) for feature_day in feature_dates]
        mean_tvl = statistics.fmean(tvl_values)
        dex_volume = math.fsum(dex_values)
        if not math.isfinite(mean_tvl) or mean_tvl <= 0 or not math.isfinite(dex_volume) or dex_volume < 0:
            skipped["invalid_dex_tvl_feature"] += 1
            day += dt.timedelta(days=1)
            continue
        turnover = dex_volume / mean_tvl
        if not math.isfinite(turnover) or turnover < 0:
            skipped["invalid_dex_turnover"] += 1
            day += dt.timedelta(days=1)
            continue

        signal_dt = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
        signal_ts = int(signal_dt.timestamp())
        pre24 = window_returns(returns, signal_ts - 24 * SECONDS_PER_HOUR, 24)
        if pre24 is None:
            skipped["incomplete_pre_rv24_returns"] += 1
            day += dt.timedelta(days=1)
            continue
        pre168 = window_returns(returns, signal_ts - 168 * SECONDS_PER_HOUR, 168)
        if pre168 is None:
            skipped["incomplete_pre_rv168_returns"] += 1
            day += dt.timedelta(days=1)
            continue
        future24 = window_returns(returns, signal_ts, 24)
        if future24 is None:
            skipped["incomplete_target_returns"] += 1
            day += dt.timedelta(days=1)
            continue

        pre_rv24_bp2 = realized_variance_bp2(pre24)
        pre_rv168_bp2 = realized_variance_bp2(pre168)
        target_rv_bp2 = realized_variance_bp2(future24)
        events.append({
            "date": day,
            "signal_ts": signal_ts,
            "target_start_ts": signal_ts,
            "target_end_ts": signal_ts + 24 * SECONDS_PER_HOUR,
            "feature_start_date": feature_dates[0].isoformat(),
            "feature_end_date": feature_dates[-1].isoformat(),
            "dex_volume_7d_usd": dex_volume,
            "mean_tvl_7d_usd": mean_tvl,
            "dex_turnover_7d": turnover,
            "dex_turnover_7d_log": math.log1p(turnover),
            "pre_rv24_bp2": pre_rv24_bp2,
            "pre_rv168_bp2": pre_rv168_bp2,
            "pre_rv24_log": math.log1p(pre_rv24_bp2),
            "pre_rv168_log": math.log1p(pre_rv168_bp2),
            "abs_return24_bps": abs(math.fsum(pre24)) * 10_000.0,
            "target_rv_bp2": target_rv_bp2,
            "target": math.log1p(target_rv_bp2),
        })
        day += dt.timedelta(days=1)
    return events, dict(sorted(skipped.items()))


def training_sample(events: list[dict], signal_ts: int, window: int = TRAIN_WINDOW) -> list[dict]:
    matured = [row for row in events if row["target_end_ts"] < signal_ts]
    return matured[-window:]


def predict_one(train: list[dict], current: dict, feature_names: tuple[str, ...]) -> float:
    if len(train) < MIN_TRAIN_EVENTS or len(train) > TRAIN_WINDOW:
        raise ValueError(
            f"training sample must contain {MIN_TRAIN_EVENTS}..{TRAIN_WINDOW} matured events; received {len(train)}"
        )
    train_rows = [
        {**{name: float(row[name]) for name in feature_names}, "target_bp": float(row["target"])}
        for row in train
    ]
    current_row = {
        **{name: float(current[name]) for name in feature_names},
        "target_bp": float(current["target"]),
    }
    # target_bp is the shared helper's legacy input key; values are log1p(RV in bp^2).
    prediction = base.fit_ols_predict(train_rows, current_row, list(feature_names))
    if not math.isfinite(float(prediction)):
        raise ValueError("non-finite standardized OLS forecast")
    return float(prediction)


def assert_non_overlapping_forecasts(rows: list[dict]) -> None:
    ordered = sorted(rows, key=lambda row: int(row["signal_ts"]))
    for previous, current in zip(ordered, ordered[1:]):
        if int(previous["target_end_ts"]) > int(current["signal_ts"]):
            raise ValueError("accepted 24-hour forecast targets overlap")
        if int(current["signal_ts"]) <= int(previous["signal_ts"]):
            raise ValueError("forecast origins are not strictly chronological")


def rolling_forecasts(events: list[dict]) -> tuple[list[dict], dict]:
    forecasts = []
    skipped = Counter()
    for event in events:
        if event["date"] < VALIDATION_START:
            continue
        train = training_sample(events, event["signal_ts"])
        if len(train) < MIN_TRAIN_EVENTS:
            skipped["insufficient_matured_training_events"] += 1
            continue
        baseline = predict_one(train, event, BASE_FEATURES)
        augmented = predict_one(train, event, AUG_FEATURES)
        split = "validation" if event["date"] < TEST_START else "test"
        forecasts.append({
            "date": event["date"].isoformat(),
            "signal_ts": event["signal_ts"],
            "target_start_ts": event["target_start_ts"],
            "target_end_ts": event["target_end_ts"],
            "feature_start_date": event["feature_start_date"],
            "feature_end_date": event["feature_end_date"],
            "split": split,
            "train_n": len(train),
            "train_start_date": train[0]["date"].isoformat(),
            "train_end_date": train[-1]["date"].isoformat(),
            "target": event["target"],
            "target_rv_bp2": event["target_rv_bp2"],
            "baseline_prediction": baseline,
            "augmented_prediction": augmented,
            "baseline_squared_error": (event["target"] - baseline) ** 2,
            "augmented_squared_error": (event["target"] - augmented) ** 2,
            "pre_rv24_log": event["pre_rv24_log"],
            "pre_rv168_log": event["pre_rv168_log"],
            "abs_return24_bps": event["abs_return24_bps"],
            "dex_volume_7d_usd": event["dex_volume_7d_usd"],
            "mean_tvl_7d_usd": event["mean_tvl_7d_usd"],
            "dex_turnover_7d": event["dex_turnover_7d"],
            "dex_turnover_7d_log": event["dex_turnover_7d_log"],
        })
    assert_non_overlapping_forecasts(forecasts)
    return forecasts, dict(sorted(skipped.items()))


def forecast_metrics(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("no accepted forecasts for requested split")
    baseline_errors = np.asarray(
        [float(row["target"]) - float(row["baseline_prediction"]) for row in rows],
        dtype=float,
    )
    augmented_errors = np.asarray(
        [float(row["target"]) - float(row["augmented_prediction"]) for row in rows],
        dtype=float,
    )
    baseline_rmse = float(np.sqrt(np.mean(baseline_errors ** 2)))
    augmented_rmse = float(np.sqrt(np.mean(augmented_errors ** 2)))
    baseline_mae = float(np.mean(np.abs(baseline_errors)))
    augmented_mae = float(np.mean(np.abs(augmented_errors)))
    return {
        "n": int(len(rows)),
        "baseline_rmse": baseline_rmse,
        "augmented_rmse": augmented_rmse,
        "baseline_mae": baseline_mae,
        "augmented_mae": augmented_mae,
        "rmse_improvement_pct": (
            (baseline_rmse - augmented_rmse) / baseline_rmse * 100.0
            if baseline_rmse > 0 else None
        ),
        "mae_improvement_pct": (
            (baseline_mae - augmented_mae) / baseline_mae * 100.0
            if baseline_mae > 0 else None
        ),
    }


def paired_loss_block_bootstrap(
    rows: list[dict],
    reps: int = BOOTSTRAP_REPS,
    block_size: int = BOOTSTRAP_BLOCK,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    differences = np.asarray([
        float(row["baseline_squared_error"]) - float(row["augmented_squared_error"])
        for row in rows
    ], dtype=float)
    n = len(differences)
    if n < block_size or reps < 1:
        raise ValueError("paired test sample is too short for the preregistered block bootstrap")
    rng = np.random.default_rng(seed)
    means = np.empty(reps, dtype=float)
    for rep in range(reps):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, n))
            indices.extend((start + offset) % n for offset in range(block_size))
        means[rep] = float(np.mean(differences[np.asarray(indices[:n], dtype=int)]))
    lower, upper = np.quantile(means, [0.025, 0.975])
    return {
        "reps": reps,
        "block_size_daily_events": block_size,
        "seed": seed,
        "observations": n,
        "mean_baseline_minus_augmented_squared_loss": float(np.mean(differences)),
        "ci95_lower": float(lower),
        "ci95_upper": float(upper),
        "bootstrap_fraction_positive": float(np.mean(means > 0)),
    }


def disposition(validation: dict, test: dict, interval: dict) -> str:
    if (
        validation["augmented_rmse"] < validation["baseline_rmse"]
        and test["augmented_rmse"] < test["baseline_rmse"]
        and interval["ci95_lower"] > 0
    ):
        return "PROMISING"
    if (
        validation["augmented_rmse"] > validation["baseline_rmse"]
        and test["augmented_rmse"] > test["baseline_rmse"]
        and interval["ci95_upper"] < 0
    ):
        return "REJECTED"
    return "INCONCLUSIVE"


def write_forecasts(path: Path, rows: list[dict]) -> None:
    fields = [
        "date", "signal_ts", "target_start_ts", "target_end_ts",
        "feature_start_date", "feature_end_date", "split", "train_n",
        "train_start_date", "train_end_date", "target", "target_rv_bp2",
        "baseline_prediction", "augmented_prediction",
        "baseline_squared_error", "augmented_squared_error",
        "pre_rv24_log", "pre_rv168_log", "abs_return24_bps",
        "dex_volume_7d_usd", "mean_tvl_7d_usd",
        "dex_turnover_7d", "dex_turnover_7d_log",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render_report(manifest: dict) -> str:
    lines = [
        f"# Ethereum DEX turnover / ETH realized variance — {NOW.isoformat()}",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {manifest.get('status')}",
        f"- **Decision:** {manifest.get('decision') or 'None'}",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Source commit:** {SOURCE_SHA}",
        f"- **Completed real-data backtest:** {manifest.get('completed_backtest')}",
        "",
        "## Frozen method",
        "",
        "- Forecast origin: daily 00:00 UTC.",
        "- DEX input: exact daily dates t-8 through t-2; seven-day aggregate Ethereum DEX notional volume divided by mean Ethereum DeFi TVL.",
        "- Baseline: log1p trailing 24-hour RV in bp^2, log1p trailing 168-hour RV in bp^2, and absolute trailing 24-hour cumulative log return in bp.",
        "- Augmented model: baseline plus log1p of the frozen seven-day DEX-turnover ratio.",
        "- Target: log1p of next-24-hour ETHUSDT Spot realized variance in bp^2.",
        "- Standardized rolling OLS; at most 252 strictly matured prior daily events, minimum 180; fixed ridge stabilization 1e-8.",
        "- Validation: 2023-01-01 through 2024-12-31. Test: 2025-01-01 through 2026-10-31.",
        "- Paired test-loss circular block bootstrap: 2,000 replications, seven daily events per block, seed 20261128.",
        "",
        "## Source provenance",
        "",
        json.dumps(manifest.get("source", {}), indent=2, sort_keys=True),
        "",
        "## Event construction and exclusions",
        "",
        json.dumps(manifest.get("event_construction", {}), indent=2, sort_keys=True),
        "",
        "## Validation metrics",
        "",
        json.dumps(manifest.get("validation_metrics", {}), indent=2, sort_keys=True),
        "",
        "## Test metrics",
        "",
        json.dumps(manifest.get("test_metrics", {}), indent=2, sort_keys=True),
        "",
        "## Paired test-loss bootstrap",
        "",
        json.dumps(manifest.get("paired_test_loss_bootstrap", {}), indent=2, sort_keys=True),
        "",
        "## Error / blocker",
        "",
        str(manifest.get("error") or "None"),
        "",
        "## Literature screen and interpretation",
        "",
        "- Hansen, Kim and Kimbrough (2024), Journal of Financial Econometrics 22(1), 224–251, DOI 10.1093/jjfinec/nbac034, document volume/volatility periodicities and report that price discovery predominantly occurs on CEXs while DEX price adjustment can be sluggish.",
        "- Alexander, Chen, Deng and Fu (2025), Price Discovery and Efficiency in Uniswap Liquidity Pools, DOI 10.1002/fut.22593, find that informed traders tend to prefer centralized venues during volatile periods and that DEX speculative activity rises during uncertainty.",
        "- Luo et al. (2024), Piercing the Veil of TVL, arXiv:2404.11745, document TVL double-counting and valuation sensitivity. The denominator here is a public aggregate proxy, not unique deployable capital.",
        "- These studies motivate a narrow predictive test; they do not establish that the exact lagged chain-wide turnover ratio predicts ETH CEX realized variance. DEX activity may respond to volatility rather than lead it.",
        "",
        "## Limitations",
        "",
        "- DeFiLlama historical values are current-vintage and may be revised; the two-day lag is conservative but does not prove historical point-in-time publication.",
        "- Aggregate Ethereum DEX volume is not ETH-specific flow and can include activity in other assets and protocols.",
        "- TVL may double-count wrapped, leveraged or composable positions; turnover/TVL is a proxy, not true unique-capital turnover.",
        "- ETHUSDT is one centralized venue; no cross-venue replication, causal identification, trading P&L, execution costs or economic value is established.",
        "- Missing hourly bars and every return/window affected by them remain excluded; no price or return is filled or interpolated.",
        "",
        "Forecast-only study. No strategy P&L, live orders, capital deployment or trading authorization.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    forecasts_path = OUTPUT_DIR / "forecast_rows.csv"
    report_path = SESSION_DIR / f"{STAMP}_session-ethereum-dex-turnover-eth-rv-{RUN_ID}.md"

    forecasts = []
    manifest = {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "ERROR",
        "decision": None,
        "completed_backtest": False,
        "backtest_run": False,
        "model_fit_performed": False,
        "raw_observations_saved": False,
        "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "timebox": {
            "cycle": 3,
            "maximum_substantive_cycles": 4,
            "implementation_deadline_utc": IMPLEMENTATION_DEADLINE.isoformat(),
            "final_conclusion_deadline_utc": FINAL_DEADLINE.isoformat(),
        },
        "model": {
            "baseline_features": list(BASE_FEATURES),
            "augmented_features": list(AUG_FEATURES),
            "training_window_max": TRAIN_WINDOW,
            "minimum_matured_training_events": MIN_TRAIN_EVENTS,
            "estimator": "repository standardized OLS helper; fixed ridge stabilization 1e-8",
            "target": "log1p(next_24h_ETHUSDT_Spot_RV_bp2)",
            "forecast_origin": "daily 00:00 UTC",
            "target_horizon_hours": 24,
        },
        "bootstrap_specification": {
            "method": "circular moving-block bootstrap of paired test squared-loss differences",
            "replications": BOOTSTRAP_REPS,
            "block_size_daily_events": BOOTSTRAP_BLOCK,
            "seed": BOOTSTRAP_SEED,
        },
    }

    try:
        if NOW > IMPLEMENTATION_DEADLINE or NOW > FINAL_DEADLINE:
            raise SourceMismatchError("preregistered implementation or final-conclusion deadline has expired")
        frozen, manifest_sha = load_frozen_manifest()
        dex, tvl, closes, source_info = fetch_frozen_sources(frozen, manifest_sha)
        manifest["source"] = source_info
        events, event_skips = build_events(dex, tvl, closes)
        manifest["event_construction"] = {
            "accepted_daily_events": len(events),
            "skipped_origins": event_skips,
            "hourly_close_rows": len(closes),
            "exact_adjacent_hourly_returns": len(hourly_returns(closes)),
            "forecast_minimum_per_split": MIN_FORECASTS_PER_SPLIT,
        }

        manifest["model_fit_performed"] = True
        forecasts, forecast_skips = rolling_forecasts(events)
        validation_rows = [row for row in forecasts if row["split"] == "validation"]
        test_rows = [row for row in forecasts if row["split"] == "test"]
        manifest["forecast_count"] = len(forecasts)
        manifest["forecast_counts_by_split"] = {
            "validation": len(validation_rows),
            "test": len(test_rows),
        }
        manifest["event_construction"]["skipped_forecast_origins"] = forecast_skips

        if (
            len(validation_rows) < MIN_FORECASTS_PER_SPLIT
            or len(test_rows) < MIN_FORECASTS_PER_SPLIT
        ):
            manifest["status"] = "INCONCLUSIVE/INFEASIBLE"
            manifest["error"] = (
                "post-exclusion forecast minimum failed: "
                f"validation={len(validation_rows)} and test={len(test_rows)}; "
                f"both must be at least {MIN_FORECASTS_PER_SPLIT}"
            )
        else:
            validation_metrics = forecast_metrics(validation_rows)
            test_metrics = forecast_metrics(test_rows)
            bootstrap = paired_loss_block_bootstrap(test_rows)
            decision = disposition(validation_metrics, test_metrics, bootstrap)
            manifest.update({
                "status": "COMPLETED",
                "decision": decision,
                "completed_backtest": True,
                "backtest_run": True,
                "validation_metrics": validation_metrics,
                "test_metrics": test_metrics,
                "paired_test_loss_bootstrap": bootstrap,
                "forecast_count": len(forecasts),
            })
    except SourceMismatchError as exc:
        manifest["status"] = "SOURCE_REVALIDATION_FAILED"
        manifest["error"] = str(exc)
    except Exception as exc:
        manifest["status"] = "ERROR"
        manifest["error"] = f"{type(exc).__name__}: {exc}"

    write_forecasts(forecasts_path, forecasts)
    manifest["paths"] = {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "forecast_rows": str(forecasts_path.relative_to(ROOT)),
        "report": str(report_path.relative_to(ROOT)),
        "preflight_manifest": str(PREFLIGHT_MANIFEST.relative_to(ROOT)),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": manifest["status"],
        "decision": manifest.get("decision"),
        "forecast_count": manifest.get("forecast_count", 0),
        "forecast_counts_by_split": manifest.get("forecast_counts_by_split", {}),
        "manifest": manifest["paths"]["manifest"],
        "report": manifest["paths"]["report"],
    }, indent=2, sort_keys=True))
    if manifest["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
