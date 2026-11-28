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

HYPOTHESIS_ID = "QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01"
SAMPLE_START = dt.date(2021, 1, 1)
SAMPLE_END = dt.date(2026, 10, 31)
DEX_URL = (
    "https://api.llama.fi/overview/dexs/ethereum?"
    "excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true"
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
MIN_LATEST_DATE = SAMPLE_END - dt.timedelta(days=2)
WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
NOW = dt.datetime.now(dt.timezone.utc)
OUTPUT_DIR = (
    ROOT / "reports" / "generated" / "ethereum-dex-turnover-eth-rv-source-preflight"
    / f"{RUN_ID}-attempt-{ATTEMPT}"
)


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
        if not isinstance(row, dict):
            raise ValueError(f"DeFiLlama {field} row {index} is not an object")
        if "date" not in row or field not in row:
            raise ValueError(
                f"DeFiLlama {field} row {index} lacks date/{field}; actual_keys={sorted(row.keys())}"
            )
        day = parse_utc_date(row["date"])
        value = parse_number(row[field], field)
        if value < 0 or (field == "tvl" and value <= 0):
            raise ValueError(f"DeFiLlama {field} row {index} has invalid value {value}")
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


def validate_daily_coverage(values: dict[dt.date, float], label: str) -> dict:
    sample = {day: value for day, value in values.items() if SAMPLE_START <= day <= MIN_LATEST_DATE}
    if not sample:
        raise ValueError(f"No {label} observations inside the frozen sample window")
    dates = sorted(sample)
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
        if open_time % step or close_time != open_time + step - 1:
            raise ValueError(f"Row {row_number} is not a complete UTC hourly candle")
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


def download_archive(spec: dict) -> tuple[dict[dt.datetime, float], dict]:
    payload = base.fetch_bytes(spec["url"], timeout=45)
    checksum_body = base.fetch_bytes(spec["url"] + ".CHECKSUM", timeout=20)
    expected_sha = base.parse_checksum(checksum_body, spec["filename"])
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
    year, month = map(int, spec["tag"].split("-"))
    if any(stamp.year != year or stamp.month != month for stamp in rows):
        raise ValueError(f"Monthly archive {spec['filename']} contains out-of-month rows")
    return rows, {
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


def validate_hourly_coverage(rows: dict[dt.datetime, float]) -> dict:
    start = dt.datetime.combine(SAMPLE_START, dt.time(), tzinfo=dt.timezone.utc)
    end_exclusive = dt.datetime.combine(SAMPLE_END + dt.timedelta(days=1), dt.time(), tzinfo=dt.timezone.utc)
    expected_count = int((end_exclusive - start).total_seconds() // 3600)
    expected = {
        start + dt.timedelta(hours=index)
        for index in range(expected_count)
    }
    observed = set(rows)
    missing = sorted(expected - observed)
    outside = sorted(observed - expected)
    if missing or outside or len(rows) != expected_count:
        raise ValueError(
            f"ETHUSDT hourly coverage mismatch: expected={expected_count}, observed={len(rows)}, "
            f"missing={len(missing)}, first_missing={missing[0].isoformat() if missing else None}, "
            f"outside={len(outside)}"
        )
    digest = hashlib.sha256()
    for stamp, close in sorted(rows.items()):
        digest.update(f"{stamp.isoformat()},{close:.12g}\n".encode("ascii"))
    return {
        "expected_hourly_rows": expected_count,
        "observed_hourly_rows": len(rows),
        "first_timestamp": min(rows).isoformat(),
        "last_timestamp": max(rows).isoformat(),
        "missing_hours": 0,
        "outside_hours": 0,
        "canonical_close_sha256": digest.hexdigest(),
    }


def run_preflight() -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        dex_future = executor.submit(base.fetch_bytes, DEX_URL, 40)
        tvl_future = executor.submit(base.fetch_bytes, TVL_URL, 40)
        dex_body = dex_future.result()
        tvl_body = tvl_future.result()

    dex = parse_dex_history(dex_body)
    tvl = parse_tvl_history(tvl_body)
    dex_coverage = validate_daily_coverage(dex, "Ethereum DEX daily notional volume")
    tvl_coverage = validate_daily_coverage(tvl, "Ethereum DeFi TVL")

    exchange_body = base.fetch_bytes(BINANCE_EXCHANGE_INFO_URL, 20)
    market = validate_exchange_info(exchange_body)

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
        raise RuntimeError(
            f"Binance Vision hourly archive ingestion failed for {len(failures)}/{len(specs)} "
            f"archives: {json.dumps(failures, sort_keys=True)}"
        )

    prices: dict[dt.datetime, float] = {}
    archive_manifest = []
    timestamp_units = set()
    for index in range(len(specs)):
        part, record = results[index]
        archive_manifest.append(record)
        timestamp_units.add(record["timestamp_unit"])
        overlap = set(prices).intersection(part)
        if overlap:
            raise ValueError(f"Duplicate ETHUSDT hourly timestamps across archives: {sorted(overlap)[:3]}")
        prices.update(part)
    if len(timestamp_units) != 1:
        raise ValueError(f"Mixed timestamp units across ETHUSDT archives: {sorted(timestamp_units)}")
    price_coverage = validate_hourly_coverage(prices)

    dex_canonical = hashlib.sha256(
        "".join(f"{day.isoformat()},{value:.12g}\n" for day, value in sorted(dex.items())).encode("ascii")
    ).hexdigest()
    tvl_canonical = hashlib.sha256(
        "".join(f"{day.isoformat()},{value:.12g}\n" for day, value in sorted(tvl.items())).encode("ascii")
    ).hexdigest()

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": NOW.isoformat(),
        "dex_source": {
            "endpoint": DEX_URL,
            "host": "api.llama.fi",
            "expected_field": "totalDataChart[].totalVolume",
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
            **market,
        },
        "binance_hourly_archives": {
            "source": "official Binance Vision Spot monthly 1h klines",
            "symbol": "ETHUSDT",
            "interval": "1h UTC",
            "requested_start": SAMPLE_START.isoformat(),
            "requested_end": SAMPLE_END.isoformat(),
            "archive_count": len(archive_manifest),
            "archives": archive_manifest,
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
            "status": "FAIL",
            "retrieved_at_utc": NOW.isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
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
