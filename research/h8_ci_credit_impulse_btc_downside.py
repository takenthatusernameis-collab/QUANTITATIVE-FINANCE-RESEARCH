#!/usr/bin/env python3
"""Frozen point-in-time H.8 C&I credit impulse -> BTC downside-semivariance forecast."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
import os
import statistics
import time
from pathlib import Path

import numpy as np
import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc
import h8_ci_credit_impulse_source_preflight as preflight

HYPOTHESIS_ID = "QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "h8-ci-credit-impulse-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
README_PATH = ROOT / "README.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md"

PREFLIGHT_MANIFEST = ROOT / "reports/generated/h8-ci-credit-impulse-source-preflight/46115128898-attempt-1/preflight.json"
PREFLIGHT_RUN_ID = 46115128898
PREFLIGHT_SOURCE_SHA = "3d76c559ae41c92b1befa0bfccc296a5469eb514"
PREFLIGHT_CANONICAL_SHA256 = "bb50c137a1e1a1d6ce42b79e17899b027476f92b97103522bc3775c2107196c8"
PREFLIGHT_RAW_SHA256 = "9f0d1451b2c6749738ca700535823a86d020fe76952ff7e18f7815425b3e0fff"

BTC_SOURCE_MANIFEST = ROOT / "reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json"
BTC_SOURCE_PREFLIGHT_RUN_ID = 45925248340
BTC_ARCHIVE_MANIFEST_SHA256 = "978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe"
BTC_START_DATE = dt.date(2017, 8, 17)
BTC_END_DATE = dt.date(2026, 11, 25)
FIRST_SIGNAL_DATE = dt.date(2017, 8, 20)
LAST_SIGNAL_DATE = dt.date(2026, 11, 15)

ALFRED_BATCH_SIZE = 12
ALFRED_INTER_REQUEST_SECONDS = 1.5
ARCHIVE_WORKERS = 6
MODEL_WINDOW = 104
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
MIN_FORECASTS = 100
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261128

BASE_FEATURES = (
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
)
AUG_FEATURES = BASE_FEATURES + ("totci_change_4w_pct",)

ARCHIVE_COMPARE_FIELDS = (
    "kind", "period", "url", "checksum_url", "archive_sha256",
    "checksum_sha256", "checksum_verified", "rows", "timestamp_unit",
    "first_date", "last_date",
)


class FrozenSourceMismatch(RuntimeError):
    """The live source no longer matches preregistered, accepted evidence."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_archive_sha256(rows: list[dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def chunk_vintages(vintages: list[str], size: int = ALFRED_BATCH_SIZE) -> list[list[str]]:
    if size < 1 or size > 12:
        raise ValueError("ALFRED vintage batches must contain between one and twelve dates")
    if len(vintages) != len(set(vintages)):
        raise ValueError("duplicate ALFRED vintages are not allowed")
    parsed = [dt.date.fromisoformat(value) for value in vintages]
    if any(value.weekday() != 6 for value in parsed):
        raise ValueError("all ALFRED event vintages must be Sundays")
    return [vintages[index:index + size] for index in range(0, len(vintages), size)]


def sunday_dates(start: dt.date, end: dt.date) -> list[str]:
    if start.weekday() != 6 or end.weekday() != 6 or end < start:
        raise ValueError("Sunday date range is invalid")
    result = []
    cursor = start
    while cursor <= end:
        result.append(cursor.isoformat())
        cursor += dt.timedelta(days=7)
    return result


def verify_frozen_preflights() -> tuple[dict, dict, dict]:
    if not PREFLIGHT_MANIFEST.is_file():
        raise FrozenSourceMismatch(f"accepted ALFRED preflight manifest is missing: {PREFLIGHT_MANIFEST}")
    if not BTC_SOURCE_MANIFEST.is_file():
        raise FrozenSourceMismatch(f"accepted BTC source manifest is missing: {BTC_SOURCE_MANIFEST}")

    preflight_manifest = json.loads(PREFLIGHT_MANIFEST.read_text(encoding="utf-8"))
    required_preflight = {
        "status": "PASS",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": PREFLIGHT_RUN_ID,
        "source_commit_sha": PREFLIGHT_SOURCE_SHA,
        "canonical_panel_sha256": PREFLIGHT_CANONICAL_SHA256,
        "raw_response_sha256": PREFLIGHT_RAW_SHA256,
        "http_status": 200,
        "api_key_used": False,
        "paid_data_used": False,
        "network_requests": 1,
        "network_retries": 0,
        "backtest_run": False,
    }
    for key, expected in required_preflight.items():
        if preflight_manifest.get(key) != expected:
            raise FrozenSourceMismatch(
                f"ALFRED preflight field {key!r} differs from the accepted run: "
                f"expected={expected!r}, actual={preflight_manifest.get(key)!r}"
            )
    expected_acceptance = {
        "exact_vintage_columns": True,
        "four_prior_weekly_observations": True,
        "latest_observation_age_days_within_3_to_14": True,
        "latest_observation_is_wednesday": True,
        "minimum_history_rows_met": True,
        "no_future_observations": True,
    }
    if preflight_manifest.get("acceptance") != expected_acceptance:
        raise FrozenSourceMismatch("ALFRED preflight acceptance flags are incomplete")

    btc_manifest = json.loads(BTC_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source = btc_manifest.get("source_manifest") or {}
    coverage = source.get("coverage") or {}
    if btc_manifest.get("source_preflight_run_id") != BTC_SOURCE_PREFLIGHT_RUN_ID:
        raise FrozenSourceMismatch("BTC source-preflight run ID differs from the frozen source")
    if btc_manifest.get("source_preflight_manifest_sha256") != BTC_ARCHIVE_MANIFEST_SHA256:
        raise FrozenSourceMismatch("BTC source-preflight manifest hash differs from the frozen source")
    if source.get("archive_manifest_sha256") != BTC_ARCHIVE_MANIFEST_SHA256:
        raise FrozenSourceMismatch("BTC archive-manifest hash differs from the frozen source")
    if source.get("archive_count") != 136 or len(source.get("archives") or []) != 136:
        raise FrozenSourceMismatch("BTC accepted source must contain exactly 136 archives")
    expected_coverage = {
        "expected_daily_rows": 3388,
        "first_date": BTC_START_DATE.isoformat(),
        "last_date": BTC_END_DATE.isoformat(),
        "missing_dates": [],
        "observed_daily_rows": 3388,
    }
    for key, expected in expected_coverage.items():
        if coverage.get(key) != expected:
            raise FrozenSourceMismatch(
                f"BTC accepted coverage field {key!r} differs: "
                f"expected={expected!r}, actual={coverage.get(key)!r}"
            )
    if any(row.get("checksum_verified") is not True for row in source["archives"]):
        raise FrozenSourceMismatch("BTC accepted manifest contains an unverified archive")
    return preflight_manifest, btc_manifest, {
        "alfred_preflight_file_sha256": file_sha256(PREFLIGHT_MANIFEST),
        "btc_manifest_file_sha256": file_sha256(BTC_SOURCE_MANIFEST),
    }


def verify_archive_manifest(actual: list[dict], expected: list[dict], expected_sha256: str) -> str:
    if len(actual) != len(expected):
        raise FrozenSourceMismatch(
            f"BTC archive count changed: expected={len(expected)}, actual={len(actual)}"
        )
    for index, (actual_row, expected_row) in enumerate(zip(actual, expected)):
        for field in ARCHIVE_COMPARE_FIELDS:
            if actual_row.get(field) != expected_row.get(field):
                raise FrozenSourceMismatch(
                    f"BTC archive {index} field {field!r} differs for {expected_row.get('period')}: "
                    f"expected={expected_row.get(field)!r}, actual={actual_row.get(field)!r}"
                )
        if actual_row.get("checksum_verified") is not True:
            raise FrozenSourceMismatch(f"BTC archive {index} checksum was not verified")
    actual_sha = canonical_archive_sha256(actual)
    if actual_sha != expected_sha256:
        raise FrozenSourceMismatch(
            f"BTC canonical archive manifest hash changed: expected={expected_sha256}, actual={actual_sha}"
        )
    return actual_sha


def fetch_btc_prices(btc_manifest: dict) -> tuple[dict[dt.date, float], dict]:
    """Re-materialize only the already accepted archives and require exact manifest identity."""
    source = btc_manifest["source_manifest"]
    expected_archives = source["archives"]
    specs = btc.build_archive_specs(BTC_START_DATE, BTC_END_DATE, as_of_date=dt.date(2026, 11, 28))
    if len(specs) != len(expected_archives):
        raise FrozenSourceMismatch(
            f"BTC archive specification count differs: {len(specs)} vs {len(expected_archives)}"
        )

    results: dict[int, tuple[dict, dict]] = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as executor:
        futures = {
            executor.submit(btc.download_binance_archive, spec): (index, spec)
            for index, spec in enumerate(specs)
        }
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({
                    "period": spec["tag"],
                    "url": spec["url"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda item: item["period"])
        raise RuntimeError(
            f"Frozen Binance archive re-materialization failed for {len(failures)}/{len(specs)} files: "
            f"{json.dumps(failures, sort_keys=True)}"
        )

    prices: dict[dt.date, float] = {}
    archive_rows = []
    timestamp_units = set()
    for index in range(len(specs)):
        page, archive_row = results[index]
        archive_rows.append(archive_row)
        timestamp_units.add(archive_row["timestamp_unit"])
        for day, close in page.items():
            if day < BTC_START_DATE or day > BTC_END_DATE:
                continue
            if day in prices:
                raise ValueError(f"duplicate BTCUSDT UTC date across accepted archives: {day}")
            if not math.isfinite(close) or close <= 0:
                raise ValueError(f"invalid BTCUSDT close on {day}: {close}")
            prices[day] = close

    archive_sha = verify_archive_manifest(
        archive_rows, expected_archives, BTC_ARCHIVE_MANIFEST_SHA256
    )
    expected_dates = []
    cursor = BTC_START_DATE
    while cursor <= BTC_END_DATE:
        expected_dates.append(cursor)
        cursor += dt.timedelta(days=1)
    expected_set = set(expected_dates)
    missing = [day.isoformat() for day in expected_dates if day not in prices]
    extra = [day.isoformat() for day in prices if day not in expected_set]
    if missing or extra or len(prices) != 3388:
        raise FrozenSourceMismatch(
            f"BTC daily coverage differs from frozen manifest: rows={len(prices)}, "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )

    return dict(sorted(prices.items())), {
        "provider": "Binance Vision official Spot monthly/daily 1d kline archives",
        "symbol": "BTCUSDT",
        "interval": "1d UTC",
        "first_date": min(prices).isoformat(),
        "last_date": max(prices).isoformat(),
        "rows": len(prices),
        "archive_count": len(archive_rows),
        "archive_manifest_sha256": archive_sha,
        "timestamp_units": sorted(timestamp_units),
        "accepted_source_manifest": str(BTC_SOURCE_MANIFEST.relative_to(ROOT)),
        "accepted_source_preflight_run_id": BTC_SOURCE_PREFLIGHT_RUN_ID,
        "raw_daily_rows_saved": False,
        "rehydration_note": (
            "The accepted source manifest records archive hashes but the prior run did not retain raw daily rows. "
            "The exact same 136 official archives were re-materialized and every archive/checksum/coverage field "
            "was required to match the accepted manifest; no alternate source or date extension was used."
        ),
    }


def fetch_alfred_panel() -> tuple[dict[str, dict[dt.date, float]], dict]:
    event_vintages = sunday_dates(FIRST_SIGNAL_DATE, LAST_SIGNAL_DATE)
    all_vintages = sorted(set(event_vintages).union(preflight.SAMPLE_VINTAGES))
    batches = chunk_vintages(all_vintages, ALFRED_BATCH_SIZE)
    panel: dict[str, dict[dt.date, float]] = {}
    batch_records = []

    for index, batch in enumerate(batches):
        if index:
            time.sleep(ALFRED_INTER_REQUEST_SECONDS)
        url = preflight.build_url(batch)
        raw, final_url, status = preflight.fetch_once(url)
        parsed = preflight.parse_vintage_csv(raw, batch)
        panel.update(parsed)
        batch_records.append({
            "batch_index": index,
            "vintage_count": len(batch),
            "first_vintage": batch[0],
            "last_vintage": batch[-1],
            "http_status": status,
            "final_url": final_url,
            "raw_response_sha256": sha256_bytes(raw),
            "canonical_batch_sha256": preflight.canonical_sha256(parsed),
        })

    if set(panel) != set(all_vintages):
        raise FrozenSourceMismatch("ALFRED returned an incomplete weekly-vintage panel")
    sample_panel = {value: panel[value] for value in preflight.SAMPLE_VINTAGES}
    sample_sha = preflight.canonical_sha256(sample_panel)
    if sample_sha != PREFLIGHT_CANONICAL_SHA256:
        raise FrozenSourceMismatch(
            f"ALFRED frozen sample vintages changed: expected={PREFLIGHT_CANONICAL_SHA256}, actual={sample_sha}"
        )
    revisions = preflight.revision_stats(sample_panel)
    accepted_revisions = {
        "older_vintage": "2020-03-15",
        "newer_vintage": "2026-11-22",
        "common_observations": 2462,
        "changed_observations": 1831,
    }
    if revisions != accepted_revisions:
        raise FrozenSourceMismatch(
            f"ALFRED revision diagnostics differ from the accepted preflight: {revisions}"
        )

    return panel, {
        "provider": "Federal Reserve Board H.8 via ALFRED",
        "series_id": "TOTCI",
        "series_title": "Commercial and Industrial Loans, All Commercial Banks",
        "frequency": "weekly ending Wednesday",
        "units": "billions of U.S. dollars, seasonally adjusted",
        "vintage_count": len(panel),
        "request_count": len(batch_records),
        "batch_size_max": max(row["vintage_count"] for row in batch_records),
        "inter_request_delay_seconds": ALFRED_INTER_REQUEST_SECONDS,
        "retries": 0,
        "api_key_used": False,
        "paid_data_used": False,
        "sample_vintages": list(preflight.SAMPLE_VINTAGES),
        "accepted_sample_canonical_sha256": sample_sha,
        "sample_revision_comparison": revisions,
        "batch_records": batch_records,
        "raw_observations_saved": False,
    }


def feature_from_vintage(
    vintage: str,
    observations: dict[dt.date, float],
) -> tuple[float | None, str | None, dict]:
    vintage_date = dt.date.fromisoformat(vintage)
    if not observations:
        return None, "no_observations", {}
    future_dates = sorted(day for day in observations if day > vintage_date)
    if future_dates:
        return None, "future_observation", {"future_observation": future_dates[0].isoformat()}

    dates = sorted(observations)
    latest = dates[-1]
    age_days = (vintage_date - latest).days
    if age_days < 3 or age_days > 14:
        return None, "stale_or_early_latest_observation", {
            "latest_observation_date": latest.isoformat(),
            "latest_observation_age_days": age_days,
        }
    if latest.weekday() != 2:
        return None, "latest_observation_not_wednesday", {
            "latest_observation_date": latest.isoformat(),
        }
    if len(dates) < 5:
        return None, "insufficient_four_week_history", {"observation_count": len(dates)}

    tail = dates[-5:]
    gaps = [(right - left).days for left, right in zip(tail, tail[1:])]
    if any(gap < 5 or gap > 9 for gap in gaps):
        return None, "irregular_weekly_history", {"weekly_gaps_days": gaps}
    span = (tail[-1] - tail[0]).days
    if not 21 <= span <= 35:
        return None, "invalid_four_observation_span", {"four_observation_span_days": span}

    latest_value = observations[latest]
    lag_value = observations[tail[0]]
    if latest_value <= 0 or lag_value <= 0:
        return None, "non_positive_credit_value", {}
    change = 100.0 * math.log(latest_value / lag_value)
    if not math.isfinite(change):
        return None, "non_finite_credit_change", {}
    return change, None, {
        "latest_observation_date": latest.isoformat(),
        "latest_observation_age_days": age_days,
        "latest_value_billions_usd_sa": latest_value,
        "fourth_prior_observation_date": tail[0].isoformat(),
        "four_observation_span_days": span,
        "weekly_gaps_days": gaps,
    }


def build_events(
    panel: dict[str, dict[dt.date, float]],
    prices: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
            continue
        previous, current = prices[dates[index - 1]], prices[dates[index]]
        if previous <= 0 or current <= 0:
            returns.append(None)
        else:
            value = math.log(current / previous)
            returns.append(value if math.isfinite(value) else None)

    index_by_date = {day: index for index, day in enumerate(dates)}
    events = []
    skipped = {
        "source_vintage_gate": 0,
        "missing_signal_anchor": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_price_returns": 0,
        "invalid_credit_feature": 0,
    }
    skip_reasons: dict[str, int] = {}

    for vintage in sorted(panel):
        signal_date = dt.date.fromisoformat(vintage)
        if signal_date < FIRST_SIGNAL_DATE or signal_date > LAST_SIGNAL_DATE:
            continue
        if signal_date.weekday() != 6:
            raise ValueError(f"non-Sunday event vintage: {vintage}")

        credit_change, reason, vintage_meta = feature_from_vintage(vintage, panel[vintage])
        if reason:
            skipped["source_vintage_gate"] += 1
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            continue

        index = index_by_date.get(signal_date)
        if index is None:
            skipped["missing_signal_anchor"] += 1
            continue
        if index < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if index + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior5 = returns[index - 4:index + 1]
        prior20 = returns[index - 19:index + 1]
        future = returns[index + 1:index + 1 + TARGET_SESSIONS]
        if any(value is None or not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_price_returns"] += 1
            continue

        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        if not math.isfinite(target) or target < 0:
            skipped["invalid_price_returns"] += 1
            continue
        if not math.isfinite(float(credit_change)):
            skipped["invalid_credit_feature"] += 1
            continue

        events.append({
            "observation_date": signal_date,
            "signal_date": signal_date,
            "target_start_date": dates[index + 1],
            "target_end_date": dates[index + TARGET_SESSIONS],
            "totci_change_4w_pct": float(credit_change),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
            "target_log1p_semivariance": math.log1p(target),
            "vintage_metadata": vintage_meta,
        })

    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("five-session BTC target windows overlap or are not matured before the next Sunday signal")

    return events, {
        "candidate_sunday_vintages": len([
            value for value in panel
            if FIRST_SIGNAL_DATE <= dt.date.fromisoformat(value) <= LAST_SIGNAL_DATE
        ]),
        "accepted_events": len(events),
        "skipped": skipped,
        "skip_reasons": skip_reasons,
        "event_frequency": "Sunday UTC; five-session Monday-Friday target; no overlap",
        "target_sessions": TARGET_SESSIONS,
        "first_signal": events[0]["signal_date"].isoformat() if events else None,
        "last_signal": events[-1]["signal_date"].isoformat() if events else None,
        "target_end_last_event": events[-1]["target_end_date"].isoformat() if events else None,
    }


def training_sample(events: list[dict], signal_date: dt.date, window: int = MODEL_WINDOW) -> list[dict]:
    matured = [
        row for row in events
        if row["signal_date"] < signal_date and row["target_end_date"] < signal_date
    ]
    return matured[-window:]


def walk_forward(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = training_sample(events, current["signal_date"])
        if len(train) != MODEL_WINDOW:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, list(BASE_FEATURES))
            augmented = base.fit_ols_predict(train, current, list(AUG_FEATURES))
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        if not math.isfinite(float(baseline)) or not math.isfinite(float(augmented)):
            continue
        target = float(current["target_log1p_semivariance"])
        predictions.append({
            "observation_date": current["observation_date"].isoformat(),
            "signal_date": current["signal_date"].isoformat(),
            "target_start_date": current["target_start_date"].isoformat(),
            "target_end_date": current["target_end_date"].isoformat(),
            "target_log1p_semivariance": target,
            "baseline_prediction": float(baseline),
            "augmented_prediction": float(augmented),
            "baseline_squared_error": (target - float(baseline)) ** 2,
            "augmented_squared_error": (target - float(augmented)) ** 2,
            "totci_change_4w_pct": current["totci_change_4w_pct"],
            "pre_downside5_log": current["pre_downside5_log"],
            "pre_downside20_log": current["pre_downside20_log"],
            "pre_rv20_log": current["pre_rv20_log"],
            "pre_return5": current["pre_return5"],
            "pre_return20": current["pre_return20"],
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0, "baseline_rmse": None, "augmented_rmse": None,
            "baseline_mae": None, "augmented_mae": None, "rmse_improvement_pct": None,
        }
    baseline_errors = [
        row["baseline_prediction"] - row["target_log1p_semivariance"] for row in rows
    ]
    augmented_errors = [
        row["augmented_prediction"] - row["target_log1p_semivariance"] for row in rows
    ]
    baseline_rmse = math.sqrt(statistics.fmean(value * value for value in baseline_errors))
    augmented_rmse = math.sqrt(statistics.fmean(value * value for value in augmented_errors))
    return {
        "n": len(rows),
        "baseline_rmse": baseline_rmse,
        "augmented_rmse": augmented_rmse,
        "baseline_mae": statistics.fmean(abs(value) for value in baseline_errors),
        "augmented_mae": statistics.fmean(abs(value) for value in augmented_errors),
        "rmse_improvement_pct": (
            100.0 * (baseline_rmse - augmented_rmse) / baseline_rmse if baseline_rmse > 0 else None
        ),
    }


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < BOOTSTRAP_BLOCK:
        return None
    differences = np.asarray([
        row["baseline_squared_error"] - row["augmented_squared_error"] for row in rows
    ], dtype=float)
    if not np.isfinite(differences).all():
        return None
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = np.empty(BOOTSTRAP_REPS, dtype=float)
    n = len(differences)
    for replication in range(BOOTSTRAP_REPS):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, n))
            indices.extend((start + offset) % n for offset in range(BOOTSTRAP_BLOCK))
        samples[replication] = float(np.mean(differences[np.asarray(indices[:n], dtype=int)]))
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "status": "COMPUTED",
        "observations": n,
        "replications": BOOTSTRAP_REPS,
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "mean_baseline_minus_augmented_squared_loss": float(np.mean(differences)),
        "ci_95_low": float(lower),
        "ci_95_high": float(upper),
        "bootstrap_fraction_positive": float(np.mean(samples > 0)),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < MIN_FORECASTS or test["n"] < MIN_FORECASTS or paired is None:
        return "INCONCLUSIVE", (
            "INCONCLUSIVE — the frozen minimum of 100 validation and 100 test forecasts "
            "or paired-loss inference was not met"
        )
    validation_improvement = validation["rmse_improvement_pct"]
    test_improvement = test["rmse_improvement_pct"]
    if (
        validation_improvement is not None
        and test_improvement is not None
        and validation_improvement >= 1.0
        and test_improvement >= 1.0
        and paired["ci_95_low"] > 0
    ):
        return "PROMISING", (
            "PROMISING forecast screen — validation and test RMSE each improve by at least 1.0% "
            "and the paired test-loss 95% interval is entirely above zero; independent validation "
            "and strategy economics remain untested"
        )
    if (
        validation_improvement is not None
        and test_improvement is not None
        and validation_improvement <= 0
        and test_improvement <= 0
        and paired["ci_95_high"] < 0
    ):
        return "REJECTED", (
            "REJECTED — neither validation nor test RMSE improves and the paired test-loss "
            "95% interval is entirely below zero"
        )
    return "INCONCLUSIVE", (
        "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"
    )


def run_research() -> dict:
    preflight_manifest, btc_manifest, frozen_file_hashes = verify_frozen_preflights()
    panel, alfred_source = fetch_alfred_panel()
    prices, btc_source = fetch_btc_prices(btc_manifest)
    events, event_metadata = build_events(panel, prices)
    forecasts = walk_forward(events)

    validation_rows = [
        row for row in forecasts
        if VALIDATION_START <= dt.date.fromisoformat(row["signal_date"]) < TEST_START
    ]
    test_rows = [
        row for row in forecasts
        if dt.date.fromisoformat(row["signal_date"]) >= TEST_START
    ]
    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    paired = paired_loss_bootstrap(test_rows)
    decision, disposition = decide(validation, test, paired)
    status = "REJECTED" if decision == "REJECTED" else "BACKTESTED"

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "decision": decision,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": (
            "The 2026-11-28 UTC minimum was already met by the separate MEXC funding-dispersion / "
            "BTC realized-variance backtest #46085887442; this H.8 study is additional research."
        ),
        "timebox": {
            "difficulty": "MEDIUM",
            "start_utc": "2026-11-28T05:49:20Z",
            "maximum_substantive_cycles": 4,
            "implementation_deadline_utc": "2026-12-01T05:49:20Z",
            "final_conclusion_deadline_utc": "2026-12-03T05:49:20Z",
            "completed_cycle": 3,
            "next_cycle": "independent reconstruction and final disposition",
        },
        "frozen_file_hashes": frozen_file_hashes,
        "source_preflight": {
            "run_id": PREFLIGHT_RUN_ID,
            "source_commit_sha": PREFLIGHT_SOURCE_SHA,
            "canonical_panel_sha256": preflight_manifest["canonical_panel_sha256"],
            "raw_response_sha256": preflight_manifest["raw_response_sha256"],
            "accepted_status": preflight_manifest["status"],
        },
        "coverage": {
            "ALFRED": {
                "vintage_count": len(panel),
                "first_vintage": min(panel),
                "last_vintage": max(panel),
                "source_series": "H.8 TOTCI",
            },
            "BTCUSDT": {
                "first_date": btc_source["first_date"],
                "last_date": btc_source["last_date"],
                "rows": btc_source["rows"],
                "archive_count": btc_source["archive_count"],
            },
        },
        "data_sources": {
            "ALFRED": alfred_source,
            "BTCUSDT": btc_source,
        },
        "event_construction": event_metadata,
        "data_scope": (
            f"ALFRED H.8 TOTCI {len(panel)} Sunday as-of vintages from {min(panel)} to {max(panel)}; "
            f"Binance BTCUSDT Spot 1d UTC {btc_source['first_date']} to {btc_source['last_date']} "
            f"({btc_source['rows']} candles, {btc_source['archive_count']} manifest-matched archives); "
            "weekly Sunday events; validation 2019-2021; test 2022 onward"
        ),
        "methodology": {
            "predictor": "100 * ln(TOTCI latest available in the Sunday vintage / fourth prior weekly observation in the same vintage)",
            "point_in_time": (
                "One ALFRED as-of vintage per Sunday signal; latest observation must be Wednesday and 3-14 days old; "
                "four prior weekly observations must have 5-9 day spacing; invalid vintages are excluded"
            ),
            "baseline_features": list(BASE_FEATURES),
            "augmented_features": list(AUG_FEATURES),
            "target": "log1p(mean(min(next-five UTC daily BTC log return, 0)^2) * 10000)",
            "event_frequency": "weekly Sunday UTC; target Monday-Friday; no overlap",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "latest 104 prior events with both signal date and five-session target end strictly before the current Sunday signal",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "minimum_validation_forecasts": MIN_FORECASTS,
            "minimum_test_forecasts": MIN_FORECASTS,
            "bootstrap_replications": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_test_loss_bootstrap": paired,
        "forecast_rows": forecasts,
        "raw_observations_saved": False,
        "trading_pnl_evaluated": False,
        "limitations": [
            "ALFRED vintage dates have day-level, not intraday, resolution; the Sunday convention follows the scheduled Friday H.8 release and rejects stale vintages, but it does not prove exact intraday first-publication time.",
            "TOTCI is a seasonally adjusted aggregate and may be revised; the model uses the exact Sunday vintage rather than today's current-vintage FRED series.",
            "C&I loan growth mixes credit supply and credit demand and is not an identified exogenous lending shock.",
            "BTCUSDT is one venue's Spot close; archive checksums establish file integrity, not consolidated exchange-independent prices.",
            "The accepted prior BTC run retained the archive manifest but not raw daily rows; the same 136 official archives were re-materialized and every archive hash, checksum hash, date and row count was matched to that manifest.",
            "This is a forecast-only screen, not causal identification, trading P&L, profitability, a strategy promotion or live deployment evidence.",
            "The result is one exploratory hypothesis among many; nominal bootstrap intervals do not adjust for repository-wide multiple testing or selection bias.",
        ],
    }


def render_report(result: dict) -> str:
    lines = [
        f"# Research session — H.8 C&I credit impulse and BTC downside semivariance ({STAMP})",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Decision:** {result.get('decision')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi')}",
        f"- **Timebox:** MEDIUM; four cycles maximum; implementation deadline 2026-12-01T05:49:20Z; final conclusion deadline 2026-12-03T05:49:20Z.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Triggering commit:** {SOURCE_SHA}",
        "",
    ]
    if result.get("error"):
        lines += [
            "## Source or implementation blocker",
            "",
            f"- {result['error']}",
            "- No valid empirical backtest completed; this attempt does not count toward the daily research minimum.",
            "",
        ]
    else:
        validation = result["validation_metrics"]
        test = result["test_metrics"]
        alfred = result["data_sources"]["ALFRED"]
        btc_source = result["data_sources"]["BTCUSDT"]
        lines += [
            "## Cycle accounting",
            "",
            f"- Cycle 1 source feasibility: PASS; ALFRED preflight run #{PREFLIGHT_RUN_ID}.",
            "- Cycle 2 model implementation and deterministic validation: completed in the admitted source commit.",
            f"- Cycle 3 immutable empirical run: #{RUN_ID}; cycle 4 independent reconstruction remains pending.",
            "",
            "## Frozen method",
            "",
            "- Predictor: 100 × ln(TOTCI latest available in each Sunday ALFRED vintage / fourth prior weekly observation in the same vintage).",
            "- Vintage gates: no future observation; latest observation Wednesday and 3–14 days old; four weekly gaps each 5–9 days.",
            "- Baseline: prior 5/20-session momentum, prior 5/20-session downside semivariance and prior 20-session total realized variance.",
            "- Augmented model: baseline plus exactly one four-observation TOTCI log change.",
            "- Target: log1p of next-five-session BTC downside semivariance; signal-day return is excluded from the target.",
            "- Rolling training: latest 104 fully matured weekly events. Validation: 2019–2021. Test: 2022 onward.",
            "- Estimator: repository standardized OLS helper with fixed ridge stabilization; no parameter tuning.",
            "",
            "## Data provenance",
            "",
            "| Source | Coverage | Rows / requests | SHA-256 |",
            "|---|---|---:|---|",
            f"| ALFRED H.8 TOTCI | {result['coverage']['ALFRED']['first_vintage']} to {result['coverage']['ALFRED']['last_vintage']} | {alfred['vintage_count']} Sunday vintages; {alfred['request_count']} requests | sample panel {alfred['accepted_sample_canonical_sha256']} |",
            f"| Binance BTCUSDT Spot | {btc_source['first_date']} to {btc_source['last_date']} | {btc_source['rows']} candles; {btc_source['archive_count']} archives | {btc_source['archive_manifest_sha256']} |",
            "",
            "## Event construction",
            "",
            f"- Candidate Sunday vintages: {result['event_construction']['candidate_sunday_vintages']}",
            f"- Accepted events: {result['event_construction']['accepted_events']}",
            f"- First/last signal: {result['event_construction']['first_signal']} / {result['event_construction']['last_signal']}",
            f"- Last target end: {result['event_construction']['target_end_last_event']}",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}",
            f"- Vintage-gate reasons: {json.dumps(result['event_construction']['skip_reasons'], sort_keys=True)}",
            "",
            "## Walk-forward results",
            "",
            "| Metric | Validation 2019–2021 | Test 2022 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {validation['n']} | {test['n']} |",
            f"| Baseline RMSE (log1p semivariance) | {validation['baseline_rmse']} | {test['baseline_rmse']} |",
            f"| Augmented RMSE (log1p semivariance) | {validation['augmented_rmse']} | {test['augmented_rmse']} |",
            f"| RMSE improvement | {validation['rmse_improvement_pct']}% | {test['rmse_improvement_pct']}% |",
            "",
            "## Paired test-loss uncertainty",
            "",
            f"- {json.dumps(result.get('paired_test_loss_bootstrap'), sort_keys=True)}",
            "",
            "## Interpretation",
            "",
            result.get("disposition", "No disposition established."),
            "",
            "## Verified / unverified",
            "",
            "**VERIFIED:** accepted ALFRED preflight identity and vintage sample hash, 0-key/0-retry ALFRED retrieval, per-vintage as-of timing gates, exact match of all 136 Binance archive/checksum hashes to the prior accepted manifest, daily price coverage, weekly event construction, fully matured 104-event training windows, non-overlapping targets and deterministic forecast/bootstrap arithmetic.",
            "**UNVERIFIED:** independent reconstruction, server-side intraday first-publication timestamps, independent market-source replication, causal interpretation, future-regime stability and instrument-level economic value.",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines += [
        "",
        "## Reproducibility",
        "",
        f"- ALFRED source preflight: https://github.com/{base.REPO}/actions/runs/{PREFLIGHT_RUN_ID}",
        f"- BTC accepted source manifest: https://github.com/{base.REPO}/blob/main/{BTC_SOURCE_MANIFEST.relative_to(ROOT).as_posix()}",
        f"- Empirical workflow: https://github.com/{base.REPO}/actions/runs/{RUN_ID}",
        "- Implementation: research/h8_ci_credit_impulse_btc_downside.py",
        "- Tests: research/test_h8_ci_credit_impulse_btc_downside.py",
        "",
    ]
    return "\n".join(lines)


def update_documents(result: dict, report_path: str, manifest_path: str, forecast_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE/INFEASIBLE")
    decision = result.get("decision", "INCONCLUSIVE/INFEASIBLE")
    disposition = result.get("disposition", "INCONCLUSIVE/INFEASIBLE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete").replace("|", "/")
    validation = result.get("validation_metrics") or {}
    test = result.get("test_metrics") or {}
    paired = result.get("paired_test_loss_bootstrap") or {}
    summary = (
        f"decision={decision}; validation/test n={validation.get('n', 0)}/{test.get('n', 0)}, "
        f"RMSE improvement={validation.get('rmse_improvement_pct')}/{test.get('rmse_improvement_pct')} percent; "
        "forecast-only"
    )
    report_link = "../" + report_path
    manifest_link = "../" + manifest_path
    forecast_link = "../" + forecast_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Point-in-time four-observation log growth in U.S. commercial-and-industrial bank loans may add information about next-five-UTC-session BTC downside semivariance beyond recent downside risk, realized variance and momentum. | "
        f"{scope} | {disposition}; {summary}; paired 95% CI={paired.get('ci_95_low')}/{paired.get('ci_95_high')} | "
        "[preregistration](PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md) / "
        "[source preflight](../reports/generated/h8-ci-credit-impulse-source-preflight/46115128898-attempt-1/preflight.json) / "
        f"[report]({report_link}) / [manifest]({manifest_link}) / [forecasts]({forecast_link}) |"
    )
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    registry_lines = registry.splitlines()
    matching = [index for index, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")]
    if len(matching) != 1:
        raise ValueError(f"expected exactly one H.8 registry row, found {len(matching)}")
    registry_lines[matching[0]] = row
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    readme = README_PATH.read_text(encoding="utf-8")
    start_marker = "## Active workstream — H.8 C&I bank-credit impulse / BTC downside (model implementation)"
    end_marker = "## Non-negotiable boundaries"
    start = readme.find(start_marker)
    end = readme.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise ValueError("canonical README H.8 active-workstream markers were not found")

    if result.get("completed_backtest"):
        heading = "## Active workstream — H.8 C&I bank-credit impulse / BTC downside (independent audit pending)"
        body = [
            heading,
            "",
            f"Hypothesis {HYPOTHESIS_ID} completed its immutable real-data forecast screen. **Current status: {status}; decision: {decision}; cycle 4 independent reconstruction pending.**",
            "",
            f"- **ALFRED source acceptance:** passed in [run #{PREFLIGHT_RUN_ID}](https://github.com/{base.REPO}/actions/runs/{PREFLIGHT_RUN_ID}); one no-key request, zero retries, HTTP 200; 483 latest-vintage weekly observations since 2017-08-16. The five-vintage canonical panel SHA-256 is {PREFLIGHT_CANONICAL_SHA256}. The 2020-03-15 and 2026-11-22 vintages differ on 1,831 of 2,462 common observations, confirming that current-vintage FRED substitution would be inappropriate.",
            f"- **BTC input:** the same 3,388 daily BTCUSDT Spot candles (2017-08-17–2026-11-25) from 136 official Binance archives; every archive SHA, checksum-sidecar SHA, row count and date range matched the prior accepted manifest {BTC_ARCHIVE_MANIFEST_SHA256}. The raw daily rows were not retained by the earlier run, so the exact manifest-pinned archives were re-materialized; no alternate source or date extension was used.",
            f"- **Event construction:** {result['event_construction']['accepted_events']} accepted Sunday events from {result['event_construction']['first_signal']} through {result['event_construction']['last_signal']}; last five-session target ended {result['event_construction']['target_end_last_event']}. Skips: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- **Walk-forward:** validation {validation.get('n')} forecasts, RMSE improvement {validation.get('rmse_improvement_pct')}%; test {test.get('n')} forecasts, RMSE improvement {test.get('rmse_improvement_pct')}%. Paired test-loss 95% CI: [{paired.get('ci_95_low')}, {paired.get('ci_95_high')}].",
            f"- **Interpretation:** {disposition}. This is forecast-only, not causal evidence, trading P&L, profitability or strategy promotion.",
            f"- **Canonical evidence:** [preregistration](research/PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md) · [ALFRED preflight](reports/generated/h8-ci-credit-impulse-source-preflight/46115128898-attempt-1/preflight.json) · [session report]({report_path}) · [manifest]({manifest_path}) · [forecast rows]({forecast_path}).",
            "- **Next:** independently reconstruct every forecast and paired bootstrap from the persisted forecast rows, verify source hashes and final disposition, then close the workstream without retuning.",
            "",
        ]
    else:
        heading = "## Closed workstream — H.8 C&I bank-credit impulse / BTC downside"
        body = [
            heading,
            "",
            f"Hypothesis {HYPOTHESIS_ID} is **CLOSED — INCONCLUSIVE/INFEASIBLE**. The ALFRED source preflight passed, but the immutable empirical run did not complete: {result.get('error', 'no complete empirical result was produced')}. This is not a performance NO-GO.",
            "",
            f"- ALFRED preflight: [run #{PREFLIGHT_RUN_ID}](https://github.com/{base.REPO}/actions/runs/{PREFLIGHT_RUN_ID}); accepted canonical panel SHA-256 {PREFLIGHT_CANONICAL_SHA256}.",
            f"- BTC accepted source manifest: {BTC_ARCHIVE_MANIFEST_SHA256}; the empirical run did not establish a valid result.",
            f"- Canonical evidence: [preregistration](research/PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md) · [ALFRED preflight](reports/generated/h8-ci-credit-impulse-source-preflight/46115128898-attempt-1/preflight.json) · [session report]({report_path}) · [manifest]({manifest_path}).",
            "- No alternate series, vendor, lag or hypothesis identity is authorized under this closed workstream.",
            "",
        ]
    readme = readme[:start] + "\n".join(body) + readme[end:]
    README_PATH.write_text(readme, encoding="utf-8")


def write_outputs(result: dict) -> tuple[str, str, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-h8-ci-credit-impulse-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    forecast_path = OUTPUT_DIR / "forecast_rows.csv"
    result["report_path"] = str(report_path.relative_to(ROOT))
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    result["forecast_path"] = str(forecast_path.relative_to(ROOT))
    result["prereg_sha256"] = file_sha256(PREREG_PATH) if PREREG_PATH.is_file() else None
    result["manifest_generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()

    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    fields = [
        "observation_date", "signal_date", "target_start_date", "target_end_date",
        "target_log1p_semivariance", "baseline_prediction", "augmented_prediction",
        "baseline_squared_error", "augmented_squared_error", "totci_change_4w_pct",
        "pre_downside5_log", "pre_downside20_log", "pre_rv20_log",
        "pre_return5", "pre_return20", "train_n",
    ]
    with forecast_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result.get("forecast_rows", []))
    update_documents(result, result["report_path"], result["manifest_path"], result["forecast_path"])
    return result["report_path"], result["manifest_path"], result["forecast_path"]


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE/INFEASIBLE",
            "decision": "INCONCLUSIVE/INFEASIBLE",
            "disposition": f"INCONCLUSIVE/INFEASIBLE — frozen source or implementation acceptance failed: {error}",
            "completed_backtest": False,
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": (
                "The 2026-11-28 minimum was already met by the separate MEXC funding-dispersion / "
                "BTC realized-variance backtest #46085887442; this failed attempt does not count as another backtest."
            ),
            "timebox": {
                "difficulty": "MEDIUM",
                "start_utc": "2026-11-28T05:49:20Z",
                "maximum_substantive_cycles": 4,
                "implementation_deadline_utc": "2026-12-01T05:49:20Z",
                "final_conclusion_deadline_utc": "2026-12-03T05:49:20Z",
                "completed_cycle": 3,
            },
            "data_scope": "source acceptance or empirical execution incomplete",
            "error": error,
            "forecast_rows": [],
            "raw_observations_saved": False,
            "trading_pnl_evaluated": False,
        }
    report_path, manifest_path, forecast_path = write_outputs(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result["status"],
        "decision": result.get("decision"),
        "completed_backtest": result.get("completed_backtest", False),
        "report_path": report_path,
        "manifest_path": manifest_path,
        "forecast_path": forecast_path,
        "validation_n": (result.get("validation_metrics") or {}).get("n"),
        "test_n": (result.get("test_metrics") or {}).get("n"),
        "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
