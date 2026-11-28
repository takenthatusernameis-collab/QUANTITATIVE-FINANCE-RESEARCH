#!/usr/bin/env python3
"""Read-only, checksum-backed feasibility preflight for Friday S&P / BTC weekend risk."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import zipfile
from pathlib import Path

import treasury_auction_demand as base
import ethereum_dex_turnover_eth_rv_source_preflight as hourly_source

HYPOTHESIS_ID = "QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 18)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = "SP500"
BINANCE_VISION = "https://data.binance.vision"
INTERVAL = "1h"
SECONDS_PER_HOUR = 3600
SIGNAL_HOUR_UTC = 12
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
TRAIN_WINDOW = 104
MIN_FORECASTS_PER_SPLIT = 60
MIN_SP500_ROWS = 2200
MAX_SP500_AGE_DAYS = 5
MAX_SP500_GAP_DAYS = 7
MAX_MISSING_HOURS = 24
MAX_MISSING_FRACTION = 0.0005
MAX_CONSECUTIVE_MISSING_HOURS = 4
WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
OUTPUT_DIR = ROOT / "reports" / "generated" / "sp500-weekend-btc-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"


def build_fred_url(start: dt.date = START_DATE) -> str:
    return f"{FRED_URL}?id={FRED_SERIES}&cosd={start.isoformat()}"


def parse_sp500_csv(body: bytes) -> dict[dt.date, float]:
    try:
        reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise ValueError("FRED SP500 response is not UTF-8 CSV") from exc
    if not reader.fieldnames or FRED_SERIES not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED SP500 schema: {reader.fieldnames}")
    date_column = next(
        (name for name in ("observation_date", "DATE") if name in reader.fieldnames),
        None,
    )
    if date_column is None:
        raise ValueError("FRED SP500 CSV has no recognized observation-date column")
    values: dict[dt.date, float] = {}
    for row_number, row in enumerate(reader, start=2):
        day = base.parse_date(row.get(date_column))
        if day is None:
            raise ValueError(f"Invalid SP500 observation date on row {row_number}")
        value = base.parse_float(row.get(FRED_SERIES))
        if value is None:
            continue
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"SP500 close must be positive and finite on {day}")
        if day in values:
            raise ValueError(f"Duplicate SP500 observation date: {day}")
        values[day] = float(value)
    if not values:
        raise ValueError("FRED SP500 returned no numeric observations")
    return dict(sorted(values.items()))


def canonical_sp500_sha256(values: dict[dt.date, float]) -> str:
    digest = hashlib.sha256()
    for day, close in sorted(values.items()):
        digest.update(f"{day.isoformat()},{close:.12g}\n".encode("ascii"))
    return digest.hexdigest()


def validate_sp500_coverage(values: dict[dt.date, float], now: dt.datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("SP500 coverage validation requires an offset-aware timestamp")
    if len(values) < MIN_SP500_ROWS:
        raise ValueError(f"Insufficient SP500 observations: {len(values)} < {MIN_SP500_ROWS}")
    dates = sorted(values)
    if dates[0] > START_DATE + dt.timedelta(days=14):
        raise ValueError(f"SP500 history starts too late: {dates[0]}")
    if dates[-1] > now.astimezone(dt.timezone.utc).date():
        raise ValueError("SP500 contains a future-dated observation")
    age_days = (now.astimezone(dt.timezone.utc).date() - dates[-1]).days
    if age_days > MAX_SP500_AGE_DAYS:
        raise ValueError(f"SP500 is stale: latest={dates[-1]}, age_days={age_days}")
    if any(day.weekday() >= 5 for day in dates):
        raise ValueError("SP500 contains a Saturday or Sunday observation")
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    maximum_gap = max(gaps, default=0)
    if maximum_gap > MAX_SP500_GAP_DAYS:
        raise ValueError(f"SP500 has a calendar gap above {MAX_SP500_GAP_DAYS} days: {maximum_gap}")
    return {
        "series_id": FRED_SERIES,
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "rows": len(values),
        "maximum_calendar_gap_days": maximum_gap,
        "latest_observation_age_days": age_days,
        "minimum_rows": MIN_SP500_ROWS,
        "maximum_age_days": MAX_SP500_AGE_DAYS,
        "maximum_gap_days": MAX_SP500_GAP_DAYS,
        "canonical_daily_sha256": canonical_sp500_sha256(values),
        "historical_intraday_publication_timestamps_available": False,
        "point_in_time_limitation": (
            "FRED supplies daily observation dates but this series does not provide "
            "historical intraday first-publication timestamps or vintages."
        ),
    }


def latest_matured_friday(values: dict[dt.date, float], now: dt.datetime) -> tuple[dt.date, int, int]:
    now_utc = now.astimezone(dt.timezone.utc)
    for day in reversed(sorted(values)):
        if day.weekday() != 4:
            continue
        signal = dt.datetime.combine(
            day + dt.timedelta(days=1),
            dt.time(hour=SIGNAL_HOUR_UTC),
            tzinfo=dt.timezone.utc,
        )
        target_end = signal + dt.timedelta(hours=24)
        if target_end <= now_utc:
            return day, int(signal.timestamp()), int(target_end.timestamp())
    raise ValueError("No fully matured Friday-to-Sunday target window is available")


def build_monthly_archive_specs(start: dt.date, latest_target_end: dt.date) -> list[dict]:
    cursor = dt.date(start.year, start.month, 1)
    target_month_start = dt.date(latest_target_end.year, latest_target_end.month, 1)
    monthly_end = target_month_start - dt.timedelta(days=1)
    specs = []
    while cursor <= monthly_end:
        tag = cursor.strftime("%Y-%m")
        filename = f"BTCUSDT-1h-{tag}.zip"
        url = f"{BINANCE_VISION}/data/spot/monthly/klines/BTCUSDT/1h/{filename}"
        specs.append({"kind": "monthly", "tag": tag, "filename": filename, "url": url})
        cursor = (
            dt.date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else dt.date(cursor.year, cursor.month + 1, 1)
        )
    return specs


def build_daily_archive_specs(latest_target_end: dt.date) -> list[dict]:
    month_start = dt.date(latest_target_end.year, latest_target_end.month, 1)
    specs = []
    for offset in range((latest_target_end - month_start).days + 1):
        day = month_start + dt.timedelta(days=offset)
        tag = day.isoformat()
        filename = f"BTCUSDT-1h-{tag}.zip"
        url = f"{BINANCE_VISION}/data/spot/daily/klines/BTCUSDT/1h/{filename}"
        specs.append({"kind": "daily", "tag": tag, "filename": filename, "url": url})
    return specs


def download_archive(spec: dict) -> tuple[dict[dt.datetime, float], dict]:
    payload = base.fetch_bytes(spec["url"], timeout=45)
    checksum_body = base.fetch_bytes(spec["url"] + ".CHECKSUM", timeout=20)
    expected_sha = hourly_source.parse_archive_checksum(checksum_body, spec["filename"])
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(
            f"Binance Vision SHA-256 mismatch for {spec['filename']}: "
            f"expected={expected_sha}, actual={actual_sha}"
        )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {spec['filename']}; found {len(csv_names)}")
        csv_body = archive.read(csv_names[0])
    rows, timestamp_unit = hourly_source.parse_hourly_archive(csv_body)
    if spec["kind"] == "monthly":
        year, month = map(int, spec["tag"].split("-"))
        invalid = any(stamp.year != year or stamp.month != month for stamp in rows)
        description = "outside requested month"
    elif spec["kind"] == "daily":
        expected_day = dt.date.fromisoformat(spec["tag"])
        invalid = any(stamp.date() != expected_day for stamp in rows)
        description = "outside requested UTC day"
    else:
        raise ValueError(f"Unsupported archive period type: {spec['kind']}")
    if invalid:
        raise ValueError(f"Binance archive {spec['filename']} contains rows {description}")
    return rows, {
        "period_type": spec["kind"],
        "period": spec["tag"],
        "url": spec["url"],
        "checksum_url": spec["url"] + ".CHECKSUM",
        "archive_sha256": actual_sha,
        "checksum_sha256": hashlib.sha256(checksum_body).hexdigest(),
        "checksum_verified": True,
        "rows": len(rows),
        "timestamp_unit": timestamp_unit,
        "first_timestamp": min(rows).isoformat(),
        "last_timestamp": max(rows).isoformat(),
    }


def download_archive_group(specs: list[dict], downloader=download_archive) -> list[tuple[dict, dict]]:
    results: dict[int, tuple[dict, dict]] = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(downloader, spec): (index, spec)
            for index, spec in enumerate(specs)
        }
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({
                    "period": spec.get("tag"),
                    "filename": spec.get("filename"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda row: str(row["period"]))
        raise RuntimeError(f"Binance archive acquisition failed: {json.dumps(failures, sort_keys=True)}")
    return [results[index] for index in range(len(specs))]


def merge_archive_results(results: list[tuple[dict, dict]]) -> dict[dt.datetime, float]:
    merged: dict[dt.datetime, float] = {}
    for rows, record in results:
        overlap = set(merged).intersection(rows)
        if overlap:
            raise ValueError(
                f"Duplicate hourly timestamps across Binance archives for {record['period']}: "
                f"{[stamp.isoformat() for stamp in sorted(overlap)[:5]]}"
            )
        merged.update(rows)
    if not merged:
        raise ValueError("No Binance BTCUSDT hourly rows were acquired")
    return dict(sorted(merged.items()))


def validate_hourly_coverage(
    rows: dict[dt.datetime, float],
    start: dt.datetime,
    end_exclusive: dt.datetime,
) -> dict:
    if start.tzinfo is None or end_exclusive.tzinfo is None:
        raise ValueError("Hourly coverage bounds must be timezone-aware")
    start = start.astimezone(dt.timezone.utc)
    end_exclusive = end_exclusive.astimezone(dt.timezone.utc)
    hours = (end_exclusive - start).total_seconds() / SECONDS_PER_HOUR
    if hours <= 0 or not hours.is_integer():
        raise ValueError("Hourly coverage bounds must form a positive whole-hour window")
    expected_count = int(hours)
    expected = {start + dt.timedelta(hours=index) for index in range(expected_count)}
    observed = set(rows)
    outside = sorted(observed - expected)
    missing = sorted(expected - observed)
    if outside:
        raise ValueError(f"Binance hourly data contains {len(outside)} out-of-window timestamps")
    missing_fraction = len(missing) / expected_count
    maximum_consecutive = 0
    current_consecutive = 0
    previous = None
    for stamp in missing:
        if previous is not None and stamp - previous == dt.timedelta(hours=1):
            current_consecutive += 1
        else:
            current_consecutive = 1
        maximum_consecutive = max(maximum_consecutive, current_consecutive)
        previous = stamp
    if (
        len(missing) > MAX_MISSING_HOURS
        or missing_fraction > MAX_MISSING_FRACTION
        or maximum_consecutive > MAX_CONSECUTIVE_MISSING_HOURS
    ):
        raise ValueError(
            "Binance hourly gaps exceed frozen limits: "
            f"missing={len(missing)}, fraction={missing_fraction:.8f}, "
            f"max_consecutive={maximum_consecutive}"
        )
    digest = hashlib.sha256()
    for stamp, close in sorted(rows.items()):
        digest.update(f"{stamp.isoformat()},{float(close):.12g}\n".encode("ascii"))
    return {
        "first_timestamp": min(rows).isoformat(),
        "last_timestamp": max(rows).isoformat(),
        "expected_hourly_rows": expected_count,
        "observed_hourly_rows": len(rows),
        "missing_hours": len(missing),
        "missing_fraction": missing_fraction,
        "coverage_ratio": 1.0 - missing_fraction,
        "maximum_consecutive_missing_hours": maximum_consecutive,
        "maximum_allowed_missing_hours": MAX_MISSING_HOURS,
        "maximum_allowed_missing_fraction": MAX_MISSING_FRACTION,
        "maximum_allowed_consecutive_missing_hours": MAX_CONSECUTIVE_MISSING_HOURS,
        "canonical_close_sha256": digest.hexdigest(),
    }


def hourly_returns(closes: dict[dt.datetime, float]) -> dict[int, float]:
    result = {}
    for stamp, close in sorted(closes.items()):
        previous = closes.get(stamp - dt.timedelta(hours=1))
        if previous is None:
            continue
        if not math.isfinite(float(previous)) or not math.isfinite(float(close)) or previous <= 0 or close <= 0:
            raise ValueError(f"Invalid BTCUSDT close around {stamp.isoformat()}")
        result[int(stamp.timestamp())] = math.log(float(close) / float(previous))
    return result


def window_complete(returns: dict[int, float], start_ts: int, periods: int) -> bool:
    return all(start_ts + offset * SECONDS_PER_HOUR in returns for offset in range(periods))


def event_feasibility(
    sp500: dict[dt.date, float],
    returns: dict[int, float],
    latest_friday: dt.date,
    validation_start: dt.date = VALIDATION_START,
    test_start: dt.date = TEST_START,
    minimum_training_events: int = TRAIN_WINDOW,
) -> dict:
    accepted = []
    for day in sorted(sp500):
        if day.weekday() != 4 or day < START_DATE or day > latest_friday:
            continue
        signal = dt.datetime.combine(
            day + dt.timedelta(days=1),
            dt.time(hour=SIGNAL_HOUR_UTC),
            tzinfo=dt.timezone.utc,
        )
        signal_ts = int(signal.timestamp())
        if not window_complete(returns, signal_ts - 24 * SECONDS_PER_HOUR, 24):
            continue
        if not window_complete(returns, signal_ts - 168 * SECONDS_PER_HOUR, 168):
            continue
        if not window_complete(returns, signal_ts, 24):
            continue
        accepted.append({
            "date": day,
            "signal_ts": signal_ts,
            "target_end_ts": signal_ts + 24 * SECONDS_PER_HOUR,
        })
    validation_count = 0
    test_count = 0
    for index, event in enumerate(accepted):
        matured = [
            row for row in accepted[:index]
            if row["target_end_ts"] < event["signal_ts"]
        ]
        if len(matured) < minimum_training_events:
            continue
        if event["date"] < validation_start:
            continue
        if event["date"] < test_start:
            validation_count += 1
        else:
            test_count += 1
    return {
        "accepted_weekly_events": len(accepted),
        "first_accepted_friday": accepted[0]["date"].isoformat() if accepted else None,
        "last_accepted_friday": accepted[-1]["date"].isoformat() if accepted else None,
        "minimum_matured_training_events": minimum_training_events,
        "validation_start": validation_start.isoformat(),
        "test_start": test_start.isoformat(),
        "eligible_validation_forecasts": validation_count,
        "eligible_test_forecasts": test_count,
        "minimum_forecasts_per_split": MIN_FORECASTS_PER_SPLIT,
        "forecast_windows_are_exactly_24h": True,
        "target_windows_non_overlapping_by_weekly_schedule": True,
    }


def run_preflight(
    now: dt.datetime | None = None,
    fred_fetcher=base.fetch_bytes,
    archive_downloader=download_archive,
) -> dict:
    retrieved_at = now or dt.datetime.now(dt.timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("Preflight timestamp must be timezone-aware")
    retrieved_at = retrieved_at.astimezone(dt.timezone.utc)
    fred_url = build_fred_url()
    fred_body = fred_fetcher(fred_url, timeout=30)
    sp500 = parse_sp500_csv(fred_body)
    sp500_coverage = validate_sp500_coverage(sp500, retrieved_at)
    latest_friday, signal_ts, target_end_ts = latest_matured_friday(sp500, retrieved_at)
    target_end = dt.datetime.fromtimestamp(target_end_ts, dt.timezone.utc)
    monthly_specs = build_monthly_archive_specs(START_DATE, target_end.date())
    daily_specs = build_daily_archive_specs(target_end.date())
    archive_specs = monthly_specs + daily_specs
    archive_results = download_archive_group(archive_specs, downloader=archive_downloader)
    all_prices = merge_archive_results(archive_results)
    start = dt.datetime.combine(START_DATE, dt.time(), tzinfo=dt.timezone.utc)
    prices = {
        stamp: close for stamp, close in all_prices.items()
        if start <= stamp < target_end
    }
    hourly_coverage = validate_hourly_coverage(prices, start, target_end)
    returns = hourly_returns(prices)
    feasibility = event_feasibility(sp500, returns, latest_friday)
    if feasibility["eligible_validation_forecasts"] < MIN_FORECASTS_PER_SPLIT:
        raise ValueError(
            f"Insufficient eligible validation forecasts: {feasibility['eligible_validation_forecasts']}"
        )
    if feasibility["eligible_test_forecasts"] < MIN_FORECASTS_PER_SPLIT:
        raise ValueError(
            f"Insufficient eligible test forecasts: {feasibility['eligible_test_forecasts']}"
        )
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": retrieved_at.isoformat(),
        "source_commit_sha": SOURCE_SHA,
        "workflow_run_id": RUN_ID,
        "workflow_run_attempt": ATTEMPT,
        "sp500_source": {
            "provider": "Federal Reserve Bank of St. Louis FRED",
            "series_id": FRED_SERIES,
            "url": fred_url,
            "http_status": 200,
            "response_sha256": hashlib.sha256(fred_body).hexdigest(),
            "response_bytes": len(fred_body),
            **sp500_coverage,
        },
        "binance_hourly_source": {
            "provider": "Binance Vision official Spot kline archives",
            "symbol": "BTCUSDT",
            "interval": INTERVAL,
            "start_utc": start.isoformat(),
            "end_exclusive_utc": target_end.isoformat(),
            "monthly_archive_count": len(monthly_specs),
            "daily_archive_count": len(daily_specs),
            "all_archive_checksums_verified": all(record["checksum_verified"] for _, record in archive_results),
            "monthly_archives": [record for _, record in archive_results[:len(monthly_specs)]],
            "daily_archives": [record for _, record in archive_results[len(monthly_specs):]],
            "coverage": hourly_coverage,
        },
        "event_feasibility": {
            **feasibility,
            "latest_matured_friday": latest_friday.isoformat(),
            "signal_timestamp_utc": dt.datetime.fromtimestamp(signal_ts, dt.timezone.utc).isoformat(),
            "target_end_timestamp_utc": target_end.isoformat(),
            "signal_embargo_hours_after_friday_16_00_new_york": "15 in EST / 16 in EDT",
        },
        "feature_definition": (
            "max(0, -10000 * ln(SP500 Friday close / previous SP500 trading-day close)); "
            "signal Saturday 12:00 UTC; target Saturday 12:00 to Sunday 12:00 UTC"
        ),
        "raw_observations_saved": False,
        "backtest_run": False,
        "model_fitted": False,
    }


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FAIL",
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_commit_sha": SOURCE_SHA,
            "workflow_run_id": RUN_ID,
            "workflow_run_attempt": ATTEMPT,
            "raw_observations_saved": False,
            "backtest_run": False,
            "model_fitted": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "preflight.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("# Friday S&P 500 / Bitcoin weekend source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: {HYPOTHESIS_ID}\n")
            handle.write("- Model fitted: **No**\n")
            handle.write("- Backtest executed: **No**\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
