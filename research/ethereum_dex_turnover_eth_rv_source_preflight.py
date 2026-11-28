#!/usr/bin/env python3
"""Read-only, checksum-backed feasibility preflight for Ethereum DEX turnover / ETH RV."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import urllib.parse
import zipfile
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as market

HYPOTHESIS_ID = "QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01"
SAMPLE_START = dt.date(2021, 1, 1)
SAMPLE_END = dt.date(2026, 10, 31)
DEX_URL = (
    "https://api.llama.fi/overview/dexs/ethereum?"
    "excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
)
TVL_URL = "https://api.llama.fi/v2/historicalChainTvl/Ethereum"
BINANCE_EXCHANGE_INFO_URL = (
    "https://data-api.binance.vision/api/v3/exchangeInfo?"
    + urllib.parse.urlencode({"symbol": "ETHUSDT"})
)
BINANCE_VISION = "https://data.binance.vision"
INTERVAL_MS = 3_600_000
MIN_DAILY_ROWS = 2_000
MAX_DAILY_GAP_DAYS = 3
MAX_MISSING_HOURS = 24
MAX_MISSING_FRACTION = 0.001
MAX_CONSECUTIVE_MISSING_HOURS = 2
MIN_LATEST_DATE = SAMPLE_END - dt.timedelta(days=2)
WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
OUTPUT_DIR = (
    ROOT / "reports" / "generated" / "ethereum-dex-turnover-eth-rv-source-preflight"
    / f"{RUN_ID}-attempt-{ATTEMPT}"
)
PARTIAL_EVIDENCE: dict = {}


def parse_number(value, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Missing/invalid {field}: {value!r}")
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {field}: {value!r}")
    return number


def parse_utc_date(value) -> dt.date:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Invalid DeFiLlama UTC date: {value!r}")
    text = str(value).strip()
    if not text:
        raise ValueError("Empty DeFiLlama UTC date")
    if "-" in text:
        try:
            return dt.date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError(f"Invalid ISO UTC date: {text!r}") from exc
    try:
        timestamp = int(text)
    except ValueError as exc:
        raise ValueError(f"Invalid Unix UTC date: {text!r}") from exc
    if timestamp <= 0:
        raise ValueError(f"Non-positive Unix UTC date: {timestamp}")
    scale = 1_000 if timestamp >= 100_000_000_000 else 1
    return dt.datetime.fromtimestamp(timestamp / scale, tz=dt.timezone.utc).date()


def _parse_chart_rows(body: bytes, field: str, envelope: str | None) -> dict[dt.date, float]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"DeFiLlama response is not valid UTF-8 JSON: {exc}") from exc
    rows = payload.get(envelope) if envelope else payload
    if not isinstance(rows, list) or not rows:
        keys = sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
        raise ValueError(f"DeFiLlama {envelope or 'TVL'} response has no non-empty row array; envelope={keys}")
    values: dict[dt.date, float] = {}
    for index, row in enumerate(rows):
        if envelope == "totalDataChart":
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise ValueError(
                    f"DeFiLlama DEX chart row {index} must be [unix_timestamp, USD_volume]; "
                    f"actual_type={type(row).__name__}, actual_value={row!r}"
                )
            day = parse_utc_date(row[0])
            value = parse_number(row[1], field)
        else:
            if not isinstance(row, dict):
                raise ValueError(f"DeFiLlama {field} row {index} is not an object")
            if "date" not in row or field not in row:
                raise ValueError(
                    f"DeFiLlama {field} row {index} lacks date/{field}; actual_keys={sorted(row.keys())}"
                )
            day = parse_utc_date(row["date"])
            value = parse_number(row[field], field)
        if value < 0:
            raise ValueError(f"DeFiLlama {field} row {index} has invalid negative value {value}")
        if day in values:
            raise ValueError(f"Duplicate DeFiLlama {field} UTC date: {day}")
        values[day] = value
    return dict(sorted(values.items()))

def parse_dex_history(body: bytes) -> dict[dt.date, float]:
    """Parse the documented overview/dexs/{chain}.totalDataChart aggregate."""
    return _parse_chart_rows(body, "totalVolume", "totalDataChart")


def parse_tvl_history(body: bytes) -> dict[dt.date, float]:
    """Parse historicalChainTvl/{chain} date/tvl observations."""
    return _parse_chart_rows(body, "tvl", None)


def canonical_daily_sha256(values: dict[dt.date, float]) -> str:
    sample = {
        day: value for day, value in values.items()
        if SAMPLE_START <= day <= MIN_LATEST_DATE
    }
    canonical = "".join(
        f"{day.isoformat()},{value:.12g}\\n"
        for day, value in sorted(sample.items())
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def validate_daily_coverage(
    values: dict[dt.date, float], label: str, require_positive: bool = False
) -> dict:
    sample = {day: value for day, value in values.items() if SAMPLE_START <= day <= MIN_LATEST_DATE}
    if not sample:
        raise ValueError(f"No {label} observations inside the frozen sample window")
    dates = sorted(sample)
    if require_positive and any(value <= 0 for value in sample.values()):
        raise ValueError(f"{label} contains non-positive values inside the frozen sample window")
    if len(dates) < MIN_DAILY_ROWS:
        raise ValueError(f"Insufficient {label} observations: {len(dates)} < {MIN_DAILY_ROWS}")
    if dates[0] > SAMPLE_START:
        raise ValueError(f"{label} starts after the frozen sample start: {dates[0]}")
    if dates[-1] < MIN_LATEST_DATE:
        raise ValueError(f"{label} ends before required lagged cutoff {MIN_LATEST_DATE}: {dates[-1]}")
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    maximum_gap = max(gaps, default=0)
    if maximum_gap > MAX_DAILY_GAP_DAYS:
        raise ValueError(f"{label} maximum daily observation gap {maximum_gap} exceeds {MAX_DAILY_GAP_DAYS}")
    return {
        "rows_in_frozen_window": len(dates),
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "minimum_required_last_date": MIN_LATEST_DATE.isoformat(),
        "maximum_gap_days": maximum_gap,
        "minimum_value": min(sample.values()),
        "maximum_value": max(sample.values()),
    }


def validate_exchange_info(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Binance exchangeInfo is not valid JSON: {exc}") from exc
    symbols = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(symbols, list) or len(symbols) != 1 or not isinstance(symbols[0], dict):
        raise ValueError("Binance exchangeInfo did not return exactly one ETHUSDT symbol")
    symbol = symbols[0]
    if (
        symbol.get("symbol"),
        symbol.get("status"),
        symbol.get("baseAsset"),
        symbol.get("quoteAsset"),
    ) != ("ETHUSDT", "TRADING", "ETH", "USDT"):
        raise ValueError(f"ETHUSDT is not the expected active Spot market: {symbol}")
    if symbol.get("isSpotTradingAllowed") is False:
        raise ValueError("ETHUSDT does not allow Spot trading")
    return {
        "symbol": "ETHUSDT",
        "status": symbol.get("status"),
        "base_asset": symbol.get("baseAsset"),
        "quote_asset": symbol.get("quoteAsset"),
        "spot_trading_allowed": symbol.get("isSpotTradingAllowed"),
    }


def build_monthly_archive_specs(start: dt.date, end: dt.date) -> list[dict]:
    next_month = (
        dt.date(end.year + 1, 1, 1)
        if end.month == 12
        else dt.date(end.year, end.month + 1, 1)
    )
    month_end = next_month - dt.timedelta(days=1)
    if start.day != 1 or end != month_end:
        raise ValueError("Hourly archive feasibility window must cover complete UTC calendar months")
    specs = []
    cursor = dt.date(start.year, start.month, 1)
    while cursor <= end:
        tag = cursor.strftime("%Y-%m")
        filename = f"ETHUSDT-1h-{tag}.zip"
        url = f"{BINANCE_VISION}/data/spot/monthly/klines/ETHUSDT/1h/{filename}"
        specs.append({"tag": tag, "filename": filename, "url": url})
        if cursor.month == 12:
            cursor = dt.date(cursor.year + 1, 1, 1)
        else:
            cursor = dt.date(cursor.year, cursor.month + 1, 1)
    return specs



def build_daily_archive_specs(days: list[dt.date]) -> list[dict]:
    specs = []
    for day in sorted(set(days)):
        tag = day.isoformat()
        filename = f"ETHUSDT-1h-{tag}.zip"
        url = f"{BINANCE_VISION}/data/spot/daily/klines/ETHUSDT/1h/{filename}"
        specs.append({"kind": "daily", "tag": tag, "filename": filename, "url": url})
    return specs


def parse_hourly_archive(body: bytes) -> tuple[dict[dt.datetime, float], str]:
    """Parse 12-column Binance Spot hourly klines and validate complete hourly bars."""
    values: dict[dt.datetime, float] = {}
    units: set[str] = set()
    reader = csv.reader(io.StringIO(body.decode("utf-8-sig")))
    for row_number, row in enumerate(reader, start=1):
        if not row:
            continue
        if row_number == 1 and row[0].strip().lower() in {"open_time", "open time"}:
            continue
        if len(row) != 12:
            raise ValueError(f"Expected 12 Binance kline columns at row {row_number}; found {len(row)}")
        try:
            open_time, close_time = int(row[0]), int(row[6])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Binance hourly timestamp at row {row_number}") from exc
        if open_time >= 100_000_000_000_000:
            unit, scale = "microseconds", 1_000_000
        elif open_time >= 100_000_000_000:
            unit, scale = "milliseconds", 1_000
        else:
            raise ValueError(f"Unsupported Binance timestamp magnitude at row {row_number}")
        step = INTERVAL_MS * (1_000 if unit == "microseconds" else 1)
        if open_time % step or not (open_time <= close_time < open_time + step):
            raise ValueError(f"Row {row_number} has invalid UTC hourly bounds: open_time={open_time}, close_time={close_time}, unit={unit}, step={step}")
        stamp = dt.datetime.fromtimestamp(open_time / scale, tz=dt.timezone.utc)
        if stamp in values:
            raise ValueError(f"Duplicate ETHUSDT hourly candle: {stamp.isoformat()}")
        open_price, high, low, close = (
            parse_number(row[1], "open"),
            parse_number(row[2], "high"),
            parse_number(row[3], "low"),
            parse_number(row[4], "close"),
        )
        volume = parse_number(row[5], "base volume")
        quote_volume = parse_number(row[7], "quote volume")
        trade_count = parse_number(row[8], "trade count")
        if min(open_price, high, low, close) <= 0:
            raise ValueError(f"Non-positive ETHUSDT OHLC at row {row_number}")
        if low > min(open_price, close) or high < max(open_price, close) or low > high:
            raise ValueError(f"Invalid ETHUSDT OHLC relationship at row {row_number}")
        if volume < 0 or quote_volume < 0 or trade_count < 0 or int(trade_count) != trade_count:
            raise ValueError(f"Invalid ETHUSDT volume/trade-count field at row {row_number}")
        values[stamp] = close
        units.add(unit)
    if not values:
        raise ValueError("Binance hourly archive contains no kline observations")
    if len(units) != 1:
        raise ValueError(f"Mixed timestamp units within one Binance archive: {sorted(units)}")
    return dict(sorted(values.items())), next(iter(units))


def parse_archive_checksum(body: bytes, filename: str) -> str:
    return market.parse_checksum(body, filename)

def download_archive(spec: dict) -> tuple[dict[dt.datetime, float], dict]:
    payload = base.fetch_bytes(spec["url"], timeout=45)
    checksum_body = base.fetch_bytes(spec["url"] + ".CHECKSUM", timeout=20)
    expected_sha = parse_archive_checksum(checksum_body, spec["filename"])
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(
            f"Binance Vision checksum mismatch for {spec['filename']}: "
            f"expected={expected_sha}, actual={actual_sha}"
        )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {spec['filename']}; found {len(csv_names)}")
        csv_body = archive.read(csv_names[0])
    rows, timestamp_unit = parse_hourly_archive(csv_body)
    kind = spec.get("kind", "monthly")
    if kind == "monthly":
        year, month = map(int, spec["tag"].split("-"))
        invalid_period = any(stamp.year != year or stamp.month != month for stamp in rows)
        period_error = "out-of-month"
    elif kind == "daily":
        expected_day = dt.date.fromisoformat(spec["tag"])
        invalid_period = any(stamp.date() != expected_day for stamp in rows)
        period_error = "outside requested UTC day"
    else:
        raise ValueError(f"Unsupported Binance archive period type: {kind}")
    if invalid_period:
        raise ValueError(f"Binance archive {spec['filename']} contains rows {period_error}")
    return rows, {
        "period_type": kind,
        "period": spec["tag"],
        "url": spec["url"],
        "checksum_url": spec["url"] + ".CHECKSUM",
        "archive_sha256": actual_sha,
        "checksum_sha256": hashlib.sha256(checksum_body).hexdigest(),
        "checksum_verified": True,
        "rows": len(rows),
        "timestamp_unit": timestamp_unit,
        "close_time_validation": "within_hourly_interval; open_time_is_grid_anchor",
        "first_timestamp": min(rows).isoformat(),
        "last_timestamp": max(rows).isoformat(),
    }


def merge_hourly_archive_parts(
    parts: list[tuple[dict[dt.datetime, float], str]],
) -> tuple[dict[dt.datetime, float], list[str]]:
    merged: dict[dt.datetime, float] = {}
    units = set()
    for rows, unit in parts:
        overlap = set(merged).intersection(rows)
        if overlap:
            raise ValueError(f"Duplicate ETHUSDT hourly timestamps across archives: {sorted(overlap)[:3]}")
        merged.update(rows)
        units.add(unit)
    if not merged:
        raise ValueError("No ETHUSDT hourly rows were supplied for archive merge")
    return dict(sorted(merged.items())), sorted(units)


def expected_hourly_timestamps() -> set[dt.datetime]:
    start = dt.datetime.combine(SAMPLE_START, dt.time(), tzinfo=dt.timezone.utc)
    end_exclusive = dt.datetime.combine(SAMPLE_END + dt.timedelta(days=1), dt.time(), tzinfo=dt.timezone.utc)
    count = int((end_exclusive - start).total_seconds() // 3600)
    return {start + dt.timedelta(hours=index) for index in range(count)}


def missing_hour_timestamps(rows: dict[dt.datetime, float]) -> list[dt.datetime]:
    return sorted(expected_hourly_timestamps() - set(rows))


def reconcile_daily_gap_patch(
    monthly_prices: dict[dt.datetime, float],
    daily_prices: dict[dt.datetime, float],
    day: dt.date,
) -> tuple[dict[dt.datetime, float], dict]:
    day_start = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc)
    expected_day = {day_start + dt.timedelta(hours=hour) for hour in range(24)}
    observed_day = set(daily_prices)
    outside = sorted(observed_day - expected_day)
    if not observed_day or outside:
        raise ValueError(
            f"Daily ETHUSDT archive {day} has no rows or contains out-of-day timestamps: "
            f"{[stamp.isoformat() for stamp in outside]}"
        )
    daily_missing = sorted(expected_day - observed_day)
    overlap = set(monthly_prices).intersection(daily_prices)
    mismatches = [
        stamp for stamp in sorted(overlap)
        if not math.isclose(monthly_prices[stamp], daily_prices[stamp], rel_tol=1e-12, abs_tol=1e-12)
    ]
    if mismatches:
        raise ValueError(
            f"Monthly/daily ETHUSDT close mismatch on {day}: "
            f"{[stamp.isoformat() for stamp in mismatches[:10]]}"
        )
    to_fill = sorted(observed_day - set(monthly_prices))
    merged = dict(monthly_prices)
    for stamp in to_fill:
        merged[stamp] = daily_prices[stamp]
    return dict(sorted(merged.items())), {
        "overlap_match_count": len(overlap),
        "daily_missing_hours": [stamp.isoformat() for stamp in daily_missing],
        "filled_hour_count": len(to_fill),
        "filled_hours": [stamp.isoformat() for stamp in to_fill],
    }


def validate_hourly_coverage(rows: dict[dt.datetime, float]) -> dict:
    expected = expected_hourly_timestamps()
    expected_count = len(expected)
    observed = set(rows)
    missing = sorted(expected - observed)
    outside = sorted(observed - expected)
    missing_fraction = len(missing) / expected_count
    max_consecutive = 0
    current_consecutive = 0
    previous = None
    for stamp in missing:
        if previous is not None and stamp - previous == dt.timedelta(hours=1):
            current_consecutive += 1
        else:
            current_consecutive = 1
        max_consecutive = max(max_consecutive, current_consecutive)
        previous = stamp
    if outside:
        raise ValueError(
            f"ETHUSDT hourly archive contains {len(outside)} out-of-window timestamps: "
            f"{[stamp.isoformat() for stamp in outside[:20]]}"
        )
    if (
        len(missing) > MAX_MISSING_HOURS
        or missing_fraction > MAX_MISSING_FRACTION
        or max_consecutive > MAX_CONSECUTIVE_MISSING_HOURS
    ):
        raise ValueError(
            f"ETHUSDT hourly gaps exceed the frozen sparse-gap limits: "
            f"missing={len(missing)}, fraction={missing_fraction:.8f}, "
            f"max_consecutive={max_consecutive}, "
            f"missing_timestamps={[stamp.isoformat() for stamp in missing]}"
        )
    digest = hashlib.sha256()
    for stamp, close in sorted(rows.items()):
        digest.update(f"{stamp.isoformat()},{close:.12g}\\n".encode("ascii"))
    return {
        "expected_hourly_rows": expected_count,
        "observed_hourly_rows": len(rows),
        "first_timestamp": min(rows).isoformat(),
        "last_timestamp": max(rows).isoformat(),
        "missing_hours": len(missing),
        "missing_timestamps": [stamp.isoformat() for stamp in missing],
        "missing_dates": sorted({stamp.date().isoformat() for stamp in missing}),
        "missing_fraction": missing_fraction,
        "coverage_ratio": 1.0 - missing_fraction,
        "maximum_consecutive_missing_hours": max_consecutive,
        "maximum_allowed_missing_hours": MAX_MISSING_HOURS,
        "maximum_allowed_missing_fraction": MAX_MISSING_FRACTION,
        "maximum_allowed_consecutive_missing_hours": MAX_CONSECUTIVE_MISSING_HOURS,
        "outside_hours": 0,
        "canonical_close_sha256": digest.hexdigest(),
    }


def run_preflight() -> dict:
    PARTIAL_EVIDENCE.clear()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        dex_future = executor.submit(base.fetch_bytes, DEX_URL, 40)
        tvl_future = executor.submit(base.fetch_bytes, TVL_URL, 40)
        dex_body = dex_future.result()
        tvl_body = tvl_future.result()

    dex = parse_dex_history(dex_body)
    tvl = parse_tvl_history(tvl_body)
    dex_coverage = validate_daily_coverage(dex, "Ethereum DEX daily notional volume")
    tvl_coverage = validate_daily_coverage(tvl, "Ethereum DeFi TVL", require_positive=True)
    dex_canonical = hashlib.sha256(
        "".join(f"{day.isoformat()},{value:.12g}\n" for day, value in sorted(dex.items())).encode("ascii")
    ).hexdigest()
    tvl_canonical = hashlib.sha256(
        "".join(f"{day.isoformat()},{value:.12g}\n" for day, value in sorted(tvl.items())).encode("ascii")
    ).hexdigest()
    PARTIAL_EVIDENCE["dex_source"] = {
        "endpoint": DEX_URL,
        "response_sha256": hashlib.sha256(dex_body).hexdigest(),
        "canonical_daily_sha256": dex_canonical,
        **dex_coverage,
    }
    PARTIAL_EVIDENCE["tvl_source"] = {
        "endpoint": TVL_URL,
        "response_sha256": hashlib.sha256(tvl_body).hexdigest(),
        "canonical_daily_sha256": tvl_canonical,
        **tvl_coverage,
    }

    exchange_body = base.fetch_bytes(BINANCE_EXCHANGE_INFO_URL, 20)
    market_info = validate_exchange_info(exchange_body)
    PARTIAL_EVIDENCE["binance_market"] = {
        "endpoint": BINANCE_EXCHANGE_INFO_URL,
        "response_sha256": hashlib.sha256(exchange_body).hexdigest(),
        **market_info,
    }

    specs = build_monthly_archive_specs(SAMPLE_START, SAMPLE_END)
    results: dict[int, tuple[dict[dt.datetime, float], dict]] = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(download_archive, spec): (index, spec)
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
        failures.sort(key=lambda row: row["period"])
        PARTIAL_EVIDENCE["binance_monthly_archive_failures"] = failures
        raise RuntimeError(
            f"Binance Vision monthly hourly archive ingestion failed for {len(failures)}/{len(specs)} archives: "
            f"{json.dumps(failures, sort_keys=True)}"
        )

    monthly_manifest = []
    archive_parts = []
    for index in range(len(specs)):
        part, record = results[index]
        monthly_manifest.append(record)
        archive_parts.append((part, record["timestamp_unit"]))
    prices, timestamp_units = merge_hourly_archive_parts(archive_parts)
    PARTIAL_EVIDENCE["binance_monthly_archives"] = {
        "archive_count": len(monthly_manifest),
        "timestamp_units_observed": timestamp_units,
        "observed_hourly_rows": len(prices),
        "archives": monthly_manifest,
    }

    missing_before_patch = missing_hour_timestamps(prices)
    daily_manifest = []
    daily_failures = []
    daily_reconciliation_failures = []
    if missing_before_patch:
        missing_days = sorted({stamp.date() for stamp in missing_before_patch})
        daily_specs = build_daily_archive_specs(missing_days)
        daily_results: dict[int, tuple[dict[dt.datetime, float], dict]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS, len(daily_specs))) as executor:
            futures = {
                executor.submit(download_archive, spec): (index, spec)
                for index, spec in enumerate(daily_specs)
            }
            for future in concurrent.futures.as_completed(futures):
                index, spec = futures[future]
                try:
                    daily_results[index] = future.result()
                except Exception as exc:
                    daily_failures.append({
                        "period": spec["tag"], "url": spec["url"],
                        "error": f"{type(exc).__name__}: {exc}",
                    })
        for index, day in enumerate(missing_days):
            if index not in daily_results:
                continue
            day_rows, record = daily_results[index]
            try:
                prices, patch = reconcile_daily_gap_patch(prices, day_rows, day)
                daily_manifest.append({**record, **patch})
            except Exception as exc:
                daily_reconciliation_failures.append({
                    "period": day.isoformat(),
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if daily_failures:
        daily_failures.sort(key=lambda row: row["period"])
        PARTIAL_EVIDENCE["binance_daily_archive_failures"] = daily_failures
    if daily_reconciliation_failures:
        PARTIAL_EVIDENCE["binance_daily_reconciliation_failures"] = daily_reconciliation_failures
        raise RuntimeError(
            "Official Binance monthly/daily archives disagree: "
            + json.dumps(daily_reconciliation_failures, sort_keys=True)
        )
    PARTIAL_EVIDENCE["binance_daily_gap_repairs"] = {
        "archive_count": len(daily_manifest),
        "archives": daily_manifest,
        "daily_archive_failures": daily_failures,
        "hours_missing_before_patch": len(missing_before_patch),
    }
    price_coverage = validate_hourly_coverage(prices)
    PARTIAL_EVIDENCE["binance_hourly_coverage"] = price_coverage

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "source_commit_sha": SOURCE_SHA,
        "workflow_run_id": RUN_ID,
        "workflow_run_attempt": ATTEMPT,
        "status": "PASS",
        "retrieved_at_utc": NOW.isoformat(),
        "dex_source": {
            "endpoint": DEX_URL,
            "host": "api.llama.fi",
            "expected_field": "totalDataChart[][0:2] = [unix_timestamp, USD_volume]",
            "response_sha256": hashlib.sha256(dex_body).hexdigest(),
            "canonical_daily_sha256": dex_canonical,
            **dex_coverage,
        },
        "tvl_source": {
            "endpoint": TVL_URL,
            "host": "api.llama.fi",
            "expected_field": "[].tvl",
            "response_sha256": hashlib.sha256(tvl_body).hexdigest(),
            "canonical_daily_sha256": tvl_canonical,
            **tvl_coverage,
        },
        "binance_market": {
            "endpoint": BINANCE_EXCHANGE_INFO_URL,
            "response_sha256": hashlib.sha256(exchange_body).hexdigest(),
            **market_info,
        },
        "binance_hourly_archives": {
            "source": "official Binance Vision Spot monthly 1h klines with checksum-verified daily gap repair attempts when required",
            "missing_hour_policy": "no fill; incomplete feature/target windows excluded",
            "symbol": "ETHUSDT",
            "interval": "1h UTC",
            "requested_start": SAMPLE_START.isoformat(),
            "requested_end": SAMPLE_END.isoformat(),
            "monthly_archive_count": len(monthly_manifest),
            "daily_gap_repair_archive_count": len(daily_manifest),
            "timestamp_units_observed": timestamp_units,
            "monthly_archives": monthly_manifest,
            "daily_gap_repairs": daily_manifest,
            "daily_archive_failures": daily_failures,
            **price_coverage,
        },
        "raw_observations_saved": False,
        "backtest_run": False,
    }


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "source_commit_sha": SOURCE_SHA,
            "workflow_run_id": RUN_ID,
            "workflow_run_attempt": ATTEMPT,
            "status": "FAIL",
            "retrieved_at_utc": NOW.isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "partial_evidence": PARTIAL_EVIDENCE,
            "raw_observations_saved": False,
            "backtest_run": False,
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "preflight.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Ethereum DEX turnover / ETH RV source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: {HYPOTHESIS_ID}\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
