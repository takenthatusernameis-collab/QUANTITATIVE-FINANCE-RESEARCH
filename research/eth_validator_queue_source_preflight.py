#!/usr/bin/env python3
"""Read-only, checksum-backed source preflight for the Ethereum validator-queue IDEA."""
from __future__ import annotations

import calendar
import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

CANDIDATE_ID = "QFR-2026-11-28-ETH-VALIDATOR-QUEUE-ASYMMETRY-DOWNSIDE-01"
METRIC_ID = "eth.ValidatorQueueWait"
CRYPTO_KEYHOLE_BASE = "https://cryptokeyhole.com"
OPENAPI_URL = f"{CRYPTO_KEYHOLE_BASE}/api/v1/openapi.json"
CATALOG_URL = f"{CRYPTO_KEYHOLE_BASE}/api/v1/catalog"
SERIES_URL = f"{CRYPTO_KEYHOLE_BASE}/api/v1/series"
CHART_URL = f"{CRYPTO_KEYHOLE_BASE}/charts/eth/?metric={METRIC_ID}"
DATA_ACCESS_URL = f"{CRYPTO_KEYHOLE_BASE}/data-access/"
BINANCE_VISION = "https://data.binance.vision"
BINANCE_EXCHANGE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=ETHUSDT"

QUEUE_START = dt.date(2020, 12, 1)
PRICE_START = dt.date(2020, 12, 1)
PRICE_MONTHLY_END = dt.date(2026, 10, 31)
PRICE_BUFFER_START = dt.date(2026, 11, 1)
PRICE_BUFFER_END = dt.date(2026, 11, 5)
PRICE_END = PRICE_BUFFER_END
QUEUE_END_EXCLUSIVE = dt.date(2026, 11, 28)
VALIDATION_START = dt.date(2022, 1, 1)
TEST_START = dt.date(2025, 1, 1)
SAMPLE_END = dt.date(2026, 10, 31)
PECTRA_DATE = dt.date(2025, 5, 7)
ORIGIN_GRID_START = dt.date(2020, 12, 22)
TARGET_HORIZON_DAYS = 5
ORIGIN_STEP_DAYS = 6
MIN_TRAIN_EVENTS = 60
MAX_TRAIN_EVENTS = 100
MIN_VALID_PER_SPLIT = 100
MIN_SCHEDULE_COVERAGE = 0.95
MIN_QUEUE_COVERAGE = 0.95
MAX_WORKERS = 6
HTTP_TIMEOUT_SECONDS = 40
HTTP_RETRIES = 3
DAILY_INTERVAL_MS = 86_400_000

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
OUTPUT_DIR = ROOT / "reports" / "generated" / "eth-validator-queue-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"
SESSION_DIR = ROOT / "reports" / "sessions" / NOW.strftime("%Y-%m-%d")
PARTIAL_EVIDENCE: dict = {}


class PreflightError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def unix_seconds(day: dt.date) -> int:
    return int(dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc).timestamp())


def parse_number(value, field: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or value is None:
        raise PreflightError(f"Missing/invalid {field}: {value!r}")
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise PreflightError(f"Invalid {field}: {value!r}") from exc
    if not math.isfinite(number) or (not allow_zero and number <= 0) or (allow_zero and number < 0):
        raise PreflightError(f"Out-of-range {field}: {value!r}")
    return number


def fetch_bytes(url: str, *, accept: str = "application/json") -> tuple[bytes, dict]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QFR-Research/1.0 (+https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)",
            "Accept": accept,
        },
        method="GET",
    )
    last_error = None
    for attempt in range(HTTP_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                body = response.read()
                headers = {key.lower(): value for key, value in response.headers.items()}
                if response.status != 200:
                    raise PreflightError(f"HTTP {response.status} for {url}")
                if not body:
                    raise PreflightError(f"Empty response from {url}")
                return body, headers
        except urllib.error.HTTPError as exc:
            if exc.code in {400, 401, 402, 403, 404}:
                raise PreflightError(f"HTTP {exc.code} for {url}: {exc.reason}") from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        if attempt + 1 < HTTP_RETRIES:
            time.sleep(2 ** attempt)
    raise PreflightError(f"Request failed after {HTTP_RETRIES} attempts: {url}: {last_error}")


def parse_json(raw: bytes, label: str):
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{label} response is not valid UTF-8 JSON: {exc}") from exc


def validate_openapi(payload: dict) -> dict:
    schemas = payload.get("components", {}).get("schemas", {})
    series_schema = schemas.get("Series", {})
    point_schema = schemas.get("Point", {})
    components = series_schema.get("properties", {}).get("components", {})
    require(payload.get("openapi", "").startswith("3."), "CryptoKeyhole OpenAPI is not OpenAPI 3.x")
    require(components.get("type") == "array", "OpenAPI Series schema does not expose component lines")
    require({"t", "v", "finality"}.issubset(set(point_schema.get("required", []))),
            "OpenAPI Point schema does not require t/v/finality")
    return {
        "openapi_version": payload.get("openapi"),
        "api_version": payload.get("info", {}).get("version"),
        "series_components_schema": "array",
        "point_required_fields": point_schema.get("required", []),
    }


def validate_catalog(payload: dict) -> dict:
    require(payload.get("asset") == "ETH", f"Unexpected catalog asset: {payload.get('asset')!r}")
    metrics = payload.get("metrics")
    require(isinstance(metrics, list), "CryptoKeyhole catalog has no metrics array")
    matches = [item for item in metrics if item.get("id") == METRIC_ID]
    require(len(matches) == 1, f"Expected exactly one {METRIC_ID} catalog item; found {len(matches)}")
    metric = matches[0]
    require(metric.get("status") not in {"held", "locked"}, f"Queue metric is not published: {metric}")
    require("24h" in metric.get("intervals", []), "Queue metric does not offer free daily 24h data")
    history_start = metric.get("historyStart")
    if history_start is not None:
        first_day = dt.datetime.fromtimestamp(int(history_start), tz=dt.timezone.utc).date()
        require(first_day <= ORIGIN_GRID_START - dt.timedelta(days=2),
                f"Queue history starts too late for the warm-up feature: {first_day}")
    return {
        "id": metric.get("id"),
        "name": metric.get("name"),
        "family": metric.get("family"),
        "unit": metric.get("unit"),
        "status": metric.get("status"),
        "intervals": metric.get("intervals"),
        "history_start_utc": (
            dt.datetime.fromtimestamp(int(history_start), tz=dt.timezone.utc).isoformat()
            if history_start is not None else None
        ),
        "history_end_utc": (
            dt.datetime.fromtimestamp(int(metric["historyEnd"]), tz=dt.timezone.utc).isoformat()
            if metric.get("historyEnd") is not None else None
        ),
        "description": metric.get("description"),
        "method": metric.get("method"),
    }


def parse_component(component: dict) -> dict:
    component_id = str(component.get("id", "")).strip()
    name = str(component.get("name", "")).strip()
    unit = str(component.get("unit", "")).strip()
    label = f"{component_id} {name}".lower()
    kind = "entry" if "entry" in label else "exit" if "exit" in label else (
        "consolidation" if "consolidation" in label else "other"
    )
    require(component_id and name, f"Queue component is missing id/name: {component}")
    require("day" in unit.lower(), f"Queue component {component_id} is not expressed in days: {unit!r}")
    points = component.get("points")
    require(isinstance(points, list) and points, f"Queue component {component_id} has no points")
    values: dict[dt.date, float] = {}
    null_count = 0
    non_final_count = 0
    previous_ts = None
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise PreflightError(f"{component_id} point {index} is not an object")
        try:
            timestamp = int(point["t"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PreflightError(f"{component_id} point {index} has invalid UTC timestamp") from exc
        require(timestamp % 86400 == 0, f"{component_id} point {index} is not aligned to a UTC day")
        if previous_ts is not None:
            require(timestamp > previous_ts, f"{component_id} points are not strictly chronological")
        previous_ts = timestamp
        day = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date()
        finality = point.get("finality")
        require(finality in {"final", "partial", "provisional"},
                f"{component_id} point {index} has unknown finality {finality!r}")
        value = point.get("v")
        if finality != "final" or value is None:
            if finality != "final":
                non_final_count += 1
            if value is None:
                null_count += 1
            continue
        parsed = parse_number(value, f"{component_id} wait days")
        if day in values:
            raise PreflightError(f"Duplicate {component_id} observation for {day}")
        values[day] = parsed
    require(values, f"{component_id} has no final non-null daily observations")
    dates = sorted(values)
    return {
        "id": component_id,
        "name": name,
        "unit": unit,
        "kind": kind,
        "values": values,
        "point_count": len(points),
        "final_non_null_count": len(values),
        "null_count": null_count,
        "non_final_count": non_final_count,
        "first_final_date": dates[0],
        "last_final_date": dates[-1],
        "canonical_sha256": hashlib.sha256(
            "".join(f"{day.isoformat()},{values[day]:.12g}\n" for day in dates).encode("ascii")
        ).hexdigest(),
    }


def validate_queue_series(payload: dict, headers: dict) -> dict:
    metric = payload.get("metric", {})
    require(metric.get("id") == METRIC_ID, f"Series metric mismatch: {metric.get('id')!r}")
    require(payload.get("interval") == "24h", "Queue series is not daily")
    state = payload.get("state")
    require(state not in {"held", "locked"}, f"Queue series is unavailable: {state} {payload.get('reason')}")
    require(headers.get("x-ckh-preview") is None, "CryptoKeyhole returned a fixed plan preview, not full history")
    license_header = headers.get("link", "")
    license_ok = "creativecommons.org/licenses/by/4.0" in license_header.lower() and 'rel="license"' in license_header.lower()
    require(license_ok, f"Free-series CC BY 4.0 Link header is missing or unexpected: {license_header!r}")
    components_raw = payload.get("components")
    require(isinstance(components_raw, list) and len(components_raw) >= 2,
            "Queue series does not expose component lines")
    parsed = [parse_component(component) for component in components_raw]
    entries = [item for item in parsed if item["kind"] == "entry"]
    exits = [item for item in parsed if item["kind"] == "exit"]
    require(len(entries) == 1, f"Expected exactly one entry-wait component; found {[x['name'] for x in entries]}")
    require(len(exits) == 1, f"Expected exactly one exit-wait component; found {[x['name'] for x in exits]}")
    entry, exit_ = entries[0], exits[0]
    for label, component in (("entry", entry), ("exit", exit_)):
        require(component["first_final_date"] <= ORIGIN_GRID_START - dt.timedelta(days=2),
                f"{label} wait history begins too late: {component['first_final_date']}")
        require(component["last_final_date"] >= SAMPLE_END - dt.timedelta(days=3),
                f"{label} wait history ends too early: {component['last_final_date']}")
    return {
        "state": state,
        "reason": payload.get("reason"),
        "generated_at_utc": (
            dt.datetime.fromtimestamp(int(payload["generatedAt"]), tz=dt.timezone.utc).isoformat()
            if payload.get("generatedAt") is not None else None
        ),
        "source_observed_at_utc": (
            dt.datetime.fromtimestamp(int(payload["sourceObservedAt"]), tz=dt.timezone.utc).isoformat()
            if payload.get("sourceObservedAt") is not None else None
        ),
        "history_start_utc": payload.get("historyStart"),
        "history_end_utc": payload.get("historyEnd"),
        "license_link_header": license_header,
        "components": [
            {
                key: value for key, value in component.items()
                if key != "values" and key not in {"first_final_date", "last_final_date"}
            } | {
                "first_final_date": component["first_final_date"].isoformat(),
                "last_final_date": component["last_final_date"].isoformat(),
            }
            for component in parsed
        ],
        "entry_values": entry["values"],
        "exit_values": exit_["values"],
        "consolidation_component_present": any(item["kind"] == "consolidation" for item in parsed),
    }


def parse_archive_checksum(body: bytes, filename: str) -> str:
    text = body.decode("utf-8-sig").strip()
    tokens = text.split()
    if len(tokens) < 2:
        raise PreflightError(f"Invalid Binance SHA-256 sidecar for {filename}: {text!r}")
    digest = tokens[0].lower()
    sidecar_name = tokens[-1].lstrip("*")
    require(len(digest) == 64 and all(char in "0123456789abcdef" for char in digest),
            f"Invalid SHA-256 in Binance sidecar for {filename}")
    require(sidecar_name == filename, f"Binance checksum sidecar names a different archive: {sidecar_name!r}")
    return digest


def build_monthly_archive_specs(start: dt.date, end: dt.date) -> list[dict]:
    require(start.day == 1 and end.day == calendar.monthrange(end.year, end.month)[1],
            "Binance monthly archive window must cover complete UTC calendar months")
    specs = []
    cursor = dt.date(start.year, start.month, 1)
    while cursor <= end:
        tag = cursor.strftime("%Y-%m")
        filename = f"ETHUSDT-1d-{tag}.zip"
        last = dt.date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        expected = [cursor + dt.timedelta(days=index) for index in range((last - cursor).days + 1)]
        url = f"{BINANCE_VISION}/data/spot/monthly/klines/ETHUSDT/1d/{filename}"
        specs.append({"kind": "monthly", "tag": tag, "filename": filename, "url": url, "expected_dates": expected})
        cursor = dt.date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return specs


def build_daily_archive_specs(start: dt.date, end: dt.date) -> list[dict]:
    specs = []
    day = start
    while day <= end:
        tag = day.isoformat()
        filename = f"ETHUSDT-1d-{tag}.zip"
        url = f"{BINANCE_VISION}/data/spot/daily/klines/ETHUSDT/1d/{filename}"
        specs.append({"kind": "daily", "tag": tag, "filename": filename, "url": url, "expected_dates": [day]})
        day += dt.timedelta(days=1)
    return specs


def parse_daily_klines(raw: bytes) -> tuple[dict[dt.date, float], str]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PreflightError(f"Binance daily kline CSV is not UTF-8: {exc}") from exc
    values: dict[dt.date, float] = {}
    units = set()
    reader = csv.reader(io.StringIO(text))
    for row_number, row in enumerate(reader, start=1):
        if not row:
            continue
        if row_number == 1 and row[0].strip().lower() in {"open_time", "open time"}:
            continue
        require(len(row) == 12, f"Binance daily kline row {row_number} has {len(row)} columns, expected 12")
        try:
            open_time = int(row[0])
            close_time = int(row[6])
        except (TypeError, ValueError) as exc:
            raise PreflightError(f"Invalid Binance daily timestamp at row {row_number}") from exc
        if open_time >= 100_000_000_000_000:
            unit, scale = "microseconds", 1_000_000
        elif open_time >= 100_000_000_000:
            unit, scale = "milliseconds", 1_000
        else:
            raise PreflightError(f"Unsupported Binance daily timestamp magnitude at row {row_number}")
        step = DAILY_INTERVAL_MS * (1_000 if unit == "microseconds" else 1)
        require(open_time % step == 0, f"Daily kline row {row_number} is not UTC-midnight aligned")
        require(open_time <= close_time < open_time + step, f"Daily kline row {row_number} has invalid close time")
        day = dt.datetime.fromtimestamp(open_time / scale, tz=dt.timezone.utc).date()
        require(day not in values, f"Duplicate Binance ETHUSDT daily candle: {day}")
        open_price, high, low, close = (
            parse_number(row[1], "open", allow_zero=False),
            parse_number(row[2], "high", allow_zero=False),
            parse_number(row[3], "low", allow_zero=False),
            parse_number(row[4], "close", allow_zero=False),
        )
        volume = parse_number(row[5], "base volume")
        quote_volume = parse_number(row[7], "quote volume")
        trade_count = parse_number(row[8], "trade count")
        require(low <= min(open_price, close) and high >= max(open_price, close) and low <= high,
                f"Invalid Binance OHLC relationship at row {row_number}")
        require(volume >= 0 and quote_volume >= 0 and int(trade_count) == trade_count,
                f"Invalid Binance volume/trade count at row {row_number}")
        values[day] = close
        units.add(unit)
    require(values, "Binance daily archive contains no candles")
    require(len(units) == 1, f"Mixed timestamp units inside one Binance daily archive: {sorted(units)}")
    return values, next(iter(units))


def download_archive(spec: dict) -> tuple[dict[dt.date, float], dict]:
    archive_body, _ = fetch_bytes(spec["url"], accept="application/zip")
    checksum_body, _ = fetch_bytes(spec["url"] + ".CHECKSUM", accept="text/plain")
    expected_digest = parse_archive_checksum(checksum_body, spec["filename"])
    actual_digest = sha256(archive_body)
    require(actual_digest == expected_digest, f"Binance archive SHA-256 mismatch for {spec['filename']}")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_body)) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            require(len(csv_names) == 1, f"{spec['filename']} does not contain exactly one CSV")
            csv_body = archive.read(csv_names[0])
    except zipfile.BadZipFile as exc:
        raise PreflightError(f"Invalid Binance ZIP archive {spec['filename']}: {exc}") from exc
    prices, timestamp_unit = parse_daily_klines(csv_body)
    expected_dates = spec["expected_dates"]
    require(sorted(prices) == expected_dates,
            f"{spec['filename']} candle dates differ from expected calendar coverage")
    record = {
        "kind": spec["kind"],
        "period": spec["tag"],
        "filename": spec["filename"],
        "url": spec["url"],
        "sha256": actual_digest,
        "checksum_sidecar_sha256": expected_digest,
        "checksum_verified": True,
        "csv_sha256": sha256(csv_body),
        "rows": len(prices),
        "timestamp_unit": timestamp_unit,
    }
    return prices, record


def validate_exchange_info(raw: bytes) -> dict:
    payload = parse_json(raw, "Binance exchangeInfo")
    symbols = payload.get("symbols") if isinstance(payload, dict) else None
    require(isinstance(symbols, list) and len(symbols) == 1 and isinstance(symbols[0], dict),
            "Binance exchangeInfo did not return exactly one ETHUSDT symbol")
    symbol = symbols[0]
    require(
        (symbol.get("symbol"), symbol.get("status"), symbol.get("baseAsset"), symbol.get("quoteAsset"))
        == ("ETHUSDT", "TRADING", "ETH", "USDT"),
        f"ETHUSDT is not the expected active Spot market: {symbol}",
    )
    require(symbol.get("isSpotTradingAllowed") is not False, "ETHUSDT Spot trading is disabled")
    return {
        "symbol": "ETHUSDT",
        "status": symbol.get("status"),
        "base_asset": symbol.get("baseAsset"),
        "quote_asset": symbol.get("quoteAsset"),
        "spot_trading_allowed": symbol.get("isSpotTradingAllowed"),
    }


def build_origin_schedule() -> list[dict]:
    schedule = []
    origin = ORIGIN_GRID_START
    while origin <= SAMPLE_END:
        if origin >= VALIDATION_START:
            split = "validation" if origin < TEST_START else "test"
            schedule.append({
                "date": origin,
                "split": split,
                "feature_date": origin - dt.timedelta(days=2),
                "target_end": origin + dt.timedelta(days=TARGET_HORIZON_DAYS),
                "baseline_start": origin - dt.timedelta(days=21),
                "target_last_close": origin + dt.timedelta(days=4),
            })
        origin += dt.timedelta(days=ORIGIN_STEP_DAYS)
    return schedule


def evaluate_schedule(entry_values: dict[dt.date, float], exit_values: dict[dt.date, float],
                      prices: dict[dt.date, float]) -> dict:
    warmup_origins = []
    origin = ORIGIN_GRID_START
    while origin < VALIDATION_START:
        warmup_origins.append(origin)
        origin += dt.timedelta(days=ORIGIN_STEP_DAYS)
    schedule = build_origin_schedule()
    all_origins = warmup_origins + [item["date"] for item in schedule]
    valid_dates = []
    exclusions = {"missing_entry_or_exit_feature": 0, "missing_price_window": 0}
    for day in all_origins:
        feature_day = day - dt.timedelta(days=2)
        if feature_day not in entry_values or feature_day not in exit_values:
            exclusions["missing_entry_or_exit_feature"] += 1
            continue
        price_days = [day - dt.timedelta(days=offset) for offset in range(21, -5, -1)]
        if any(price_day not in prices for price_day in price_days):
            exclusions["missing_price_window"] += 1
            continue
        valid_dates.append(day)

    accepted = []
    training_counts = []
    previous_valid = []
    for day in valid_dates:
        if day >= VALIDATION_START:
            matured = [prior for prior in previous_valid
                       if prior + dt.timedelta(days=TARGET_HORIZON_DAYS) < day]
            if len(matured) >= MIN_TRAIN_EVENTS:
                accepted.append(day)
                training_counts.append(min(MAX_TRAIN_EVENTS, len(matured)))
        previous_valid.append(day)

    validation = [day for day in accepted if VALIDATION_START <= day < TEST_START]
    test = [day for day in accepted if TEST_START <= day <= SAMPLE_END]
    pre_pectra_test = [day for day in test if day < PECTRA_DATE]
    post_pectra_test = [day for day in test if day >= PECTRA_DATE]
    expected_validation = len([item for item in schedule if item["split"] == "validation"])
    expected_test = len([item for item in schedule if item["split"] == "test"])
    validation_coverage = len(validation) / expected_validation if expected_validation else 0.0
    test_coverage = len(test) / expected_test if expected_test else 0.0
    require(len(validation) >= MIN_VALID_PER_SPLIT,
            f"Only {len(validation)} valid validation origins; minimum is {MIN_VALID_PER_SPLIT}")
    require(len(test) >= MIN_VALID_PER_SPLIT,
            f"Only {len(test)} valid test origins; minimum is {MIN_VALID_PER_SPLIT}")
    require(validation_coverage >= MIN_SCHEDULE_COVERAGE,
            f"Validation source coverage {validation_coverage:.3%} is below {MIN_SCHEDULE_COVERAGE:.1%}")
    require(test_coverage >= MIN_SCHEDULE_COVERAGE,
            f"Test source coverage {test_coverage:.3%} is below {MIN_SCHEDULE_COVERAGE:.1%}")
    require(pre_pectra_test and post_pectra_test,
            "Test period does not contain both pre- and post-Pectra observations")
    require(all(left + dt.timedelta(days=TARGET_HORIZON_DAYS) < right
                for left, right in zip(accepted, accepted[1:])),
            "Accepted five-day target windows overlap")
    return {
        "origin_grid_start": ORIGIN_GRID_START.isoformat(),
        "origin_step_days": ORIGIN_STEP_DAYS,
        "target_horizon_days": TARGET_HORIZON_DAYS,
        "target_windows_non_overlapping": True,
        "validation": {
            "start": VALIDATION_START.isoformat(),
            "end": (TEST_START - dt.timedelta(days=1)).isoformat(),
            "scheduled_origins": expected_validation,
            "valid_origins_after_source_exclusions": len(validation),
            "coverage_fraction": validation_coverage,
        },
        "test": {
            "start": TEST_START.isoformat(),
            "end": SAMPLE_END.isoformat(),
            "scheduled_origins": expected_test,
            "valid_origins_after_source_exclusions": len(test),
            "coverage_fraction": test_coverage,
            "pre_pectra_origins": len(pre_pectra_test),
            "post_pectra_origins": len(post_pectra_test),
        },
        "warmup_valid_origins": len([day for day in valid_dates if day < VALIDATION_START]),
        "minimum_training_events": MIN_TRAIN_EVENTS,
        "maximum_training_events": MAX_TRAIN_EVENTS,
        "observed_training_count_min": min(training_counts),
        "observed_training_count_max": max(training_counts),
        "source_exclusions": exclusions,
    }


def coverage_summary(values: dict[dt.date, float], start: dt.date, end: dt.date) -> dict:
    expected = []
    day = start
    while day <= end:
        expected.append(day)
        day += dt.timedelta(days=1)
    observed = [day for day in expected if day in values]
    missing = [day for day in expected if day not in values]
    observed_sorted = sorted(observed)
    max_gap = max(((right - left).days - 1 for left, right in zip(observed_sorted, observed_sorted[1:])), default=0)
    return {
        "expected_days": len(expected),
        "observed_final_days": len(observed),
        "missing_days": len(missing),
        "coverage_fraction": len(observed) / len(expected) if expected else 0.0,
        "first_final_date": observed_sorted[0].isoformat() if observed_sorted else None,
        "last_final_date": observed_sorted[-1].isoformat() if observed_sorted else None,
        "maximum_internal_gap_days": max_gap,
        "missing_date_examples": [day.isoformat() for day in missing[:12]],
    }


def build_catalog_url_candidates() -> list[str]:
    """Use the documented id-inferred asset route before the explicit ETH route."""
    return [
        f"{CATALOG_URL}?{urllib.parse.urlencode({'ids': METRIC_ID})}",
        f"{CATALOG_URL}?{urllib.parse.urlencode({'asset': 'ETH'})}",
    ]


def fetch_eth_catalog() -> tuple[str, bytes, dict]:
    attempts = []
    evidence = PARTIAL_EVIDENCE.setdefault("cryptokeyhole", {})
    for url in build_catalog_url_candidates():
        attempt = {"url": url}
        attempts.append(attempt)
        evidence["catalog_attempts"] = attempts
        try:
            raw, _ = fetch_bytes(url)
            attempt["response_sha256"] = sha256(raw)
            attempt["response_bytes"] = len(raw)
            payload = parse_json(raw, "CryptoKeyhole ETH catalog")
            attempt["response_asset"] = payload.get("asset")
            metrics = payload.get("metrics")
            attempt["metric_ids"] = (
                [str(item.get("id")) for item in metrics if isinstance(item, dict)]
                if isinstance(metrics, list) else None
            )
            catalog = validate_catalog(payload)
            attempt["accepted"] = True
            evidence["catalog_url"] = url
            evidence["catalog_response_sha256"] = sha256(raw)
            evidence["catalog"] = catalog
            return url, raw, catalog
        except PreflightError as exc:
            attempt["accepted"] = False
            attempt["error"] = str(exc)
    raise PreflightError(
        "No valid ETH catalog response from the documented id-inferred or explicit-asset routes: "
        + json.dumps(attempts, sort_keys=True)
    )


def run_preflight() -> dict:
    PARTIAL_EVIDENCE.clear()
    series_url = f"{SERIES_URL}?{urllib.parse.urlencode({'metric': METRIC_ID, 'interval': '24h', 'start': unix_seconds(QUEUE_START), 'end': unix_seconds(QUEUE_END_EXCLUSIVE), 'limit': 20000})}"
    openapi_raw, _ = fetch_bytes(OPENAPI_URL)
    PARTIAL_EVIDENCE["cryptokeyhole"] = {
        "openapi_url": OPENAPI_URL,
        "openapi_sha256": sha256(openapi_raw),
        "openapi_response_bytes": len(openapi_raw),
    }
    openapi = validate_openapi(parse_json(openapi_raw, "CryptoKeyhole OpenAPI"))
    PARTIAL_EVIDENCE["cryptokeyhole"]["openapi"] = openapi

    catalog_url, catalog_raw, catalog = fetch_eth_catalog()
    series_raw, series_headers = fetch_bytes(series_url)
    PARTIAL_EVIDENCE["cryptokeyhole"].update({
        "series_url": series_url,
        "series_response_sha256": sha256(series_raw),
        "series_response_bytes": len(series_raw),
        "series_license_link": series_headers.get("link"),
        "series_preview_header": series_headers.get("x-ckh-preview"),
    })
    queue = validate_queue_series(parse_json(series_raw, "CryptoKeyhole queue series"), series_headers)
    PARTIAL_EVIDENCE["cryptokeyhole"]["series"] = {
        key: value for key, value in queue.items() if key not in {"entry_values", "exit_values"}
    }

    entry_values = queue["entry_values"]
    exit_values = queue["exit_values"]
    queue_start_required = ORIGIN_GRID_START - dt.timedelta(days=2)
    queue_end_required = SAMPLE_END - dt.timedelta(days=3)
    entry_coverage = coverage_summary(entry_values, queue_start_required, queue_end_required)
    exit_coverage = coverage_summary(exit_values, queue_start_required, queue_end_required)
    require(entry_coverage["coverage_fraction"] >= MIN_QUEUE_COVERAGE,
            f"Entry-wait daily coverage {entry_coverage['coverage_fraction']:.3%} is below threshold")
    require(exit_coverage["coverage_fraction"] >= MIN_QUEUE_COVERAGE,
            f"Exit-wait daily coverage {exit_coverage['coverage_fraction']:.3%} is below threshold")
    PARTIAL_EVIDENCE["queue_component_coverage"] = {
        "entry": entry_coverage,
        "exit": exit_coverage,
        "required_start": queue_start_required.isoformat(),
        "required_end": queue_end_required.isoformat(),
    }

    exchange_raw, _ = fetch_bytes(BINANCE_EXCHANGE_INFO_URL)
    market = validate_exchange_info(exchange_raw)
    monthly_specs = build_monthly_archive_specs(PRICE_START, PRICE_MONTHLY_END)
    daily_specs = build_daily_archive_specs(PRICE_BUFFER_START, PRICE_BUFFER_END)
    specs = monthly_specs + daily_specs
    downloaded: dict[int, tuple[dict[dt.date, float], dict]] = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(specs))) as executor:
        futures = {executor.submit(download_archive, spec): (index, spec) for index, spec in enumerate(specs)}
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                downloaded[index] = future.result()
            except Exception as exc:
                failures.append({"kind": spec["kind"], "period": spec["tag"], "url": spec["url"],
                                 "error": f"{type(exc).__name__}: {exc}"})
    if failures:
        failures.sort(key=lambda item: (item["kind"], item["period"]))
        PARTIAL_EVIDENCE["binance_archive_failures"] = failures
        raise PreflightError(f"Binance ETHUSDT daily archive acquisition failed: {json.dumps(failures, sort_keys=True)}")

    prices: dict[dt.date, float] = {}
    archive_records = []
    timestamp_units = set()
    for index, spec in enumerate(specs):
        rows, record = downloaded[index]
        overlap = set(prices).intersection(rows)
        require(not overlap, f"Overlapping Binance daily archive dates: {sorted(overlap)[:5]}")
        prices.update(rows)
        archive_records.append(record)
        timestamp_units.add(record["timestamp_unit"])
    expected_price_days = (PRICE_END - PRICE_START).days + 1
    require(len(prices) == expected_price_days,
            f"Binance daily close population {len(prices)} differs from expected {expected_price_days}")
    price_days = sorted(prices)
    require(price_days[0] == PRICE_START and price_days[-1] == PRICE_END,
            "Binance ETHUSDT daily close history does not cover the frozen target buffer")
    require(all((right - left).days == 1 for left, right in zip(price_days, price_days[1:])),
            "Binance ETHUSDT daily close history contains missing calendar days")
    canonical_price = "".join(f"{day.isoformat()},{prices[day]:.12g}\n" for day in price_days)
    price_summary = {
        "symbol": "ETHUSDT",
        "interval": "1d UTC",
        "requested_start": PRICE_START.isoformat(),
        "requested_end": PRICE_END.isoformat(),
        "monthly_archive_count": len(monthly_specs),
        "daily_buffer_archive_count": len(daily_specs),
        "archive_count": len(archive_records),
        "observed_daily_rows": len(prices),
        "expected_daily_rows": expected_price_days,
        "first_date": price_days[0].isoformat(),
        "last_date": price_days[-1].isoformat(),
        "timestamp_units_observed": sorted(timestamp_units),
        "canonical_daily_close_sha256": sha256(canonical_price.encode("ascii")),
        "archives": archive_records,
        "missing_daily_dates": [],
        "missing_data_policy": "no fill; incomplete baseline or target windows excluded",
    }
    PARTIAL_EVIDENCE["binance_daily_price"] = {
        key: value for key, value in price_summary.items() if key != "archives"
    }

    schedule = evaluate_schedule(entry_values, exit_values, prices)
    PARTIAL_EVIDENCE["forecast_schedule_feasibility"] = schedule
    return {
        "candidate_id": CANDIDATE_ID,
        "source_commit_sha": SOURCE_SHA,
        "workflow_run_id": RUN_ID,
        "workflow_run_attempt": ATTEMPT,
        "status": "PASS",
        "retrieved_at_utc": NOW.isoformat(),
        "cryptokeyhole": {
            "base_url": CRYPTO_KEYHOLE_BASE,
            "metric_id": METRIC_ID,
            "chart_url": CHART_URL,
            "data_access_url": DATA_ACCESS_URL,
            "access": "Free daily 24h view; no API key, account or sign-up used",
            "license": "CC BY 4.0; include Source: CryptoKeyhole and a link to the chart",
            "openapi_url": OPENAPI_URL,
            "openapi_sha256": sha256(openapi_raw),
            "catalog_url": catalog_url,
            "catalog_response_sha256": sha256(catalog_raw),
            "series_url": series_url,
            "series_response_sha256": sha256(series_raw),
            "catalog": catalog,
            "series": {key: value for key, value in queue.items() if key not in {"entry_values", "exit_values"}},
            "entry_wait_coverage": entry_coverage,
            "exit_wait_coverage": exit_coverage,
            "entry_wait_canonical_sha256": next(item["canonical_sha256"] for item in queue["components"] if item["kind"] == "entry"),
            "exit_wait_canonical_sha256": next(item["canonical_sha256"] for item in queue["components"] if item["kind"] == "exit"),
            "vintage_limitation": "Free current-vintage daily history; first-published vintages require API & Team and the recorder began 2026-11-08, so historical point-in-time values are unavailable.",
            "methodology_breaks": [
                {
                    "date": "2025-05-07",
                    "entry_queue_pre_pectra": "Validators eligible for activation and not yet activated, 32 ETH each, reconstructed from registry eligibility and activation epochs.",
                    "entry_queue_post_pectra": "Deposits waiting in the consensus-state deposit queue, read from full day-end states.",
                    "exit_queue": "Validators whose exit has started and whose exit epoch has not been reached; includes voluntary exits, slashings and execution-layer exit requests.",
                    "churn_pre_pectra": "max(4, active validators / 65,536) validators per epoch; activations capped at 8 per epoch from Deneb on 2024-03-13.",
                    "churn_post_pectra": "min(256 ETH, max(128 ETH, total active balance / 65,536)) per epoch for deposits and exits; remaining balance churn reserved for consolidations.",
                },
                {
                    "date": "2025-05-07",
                    "partial_withdrawals": "Execution-layer-requested partial withdrawals share exit churn but are not in daily history; hourly current-state readings include them.",
                    "consolidations": "Separate queue and churn limit; not part of the proposed entry-minus-exit feature.",
                },
            ],
        },
        "binance_market": {"endpoint": BINANCE_EXCHANGE_INFO_URL, "response_sha256": sha256(exchange_raw), **market},
        "binance_daily_price": price_summary,
        "forecast_schedule_feasibility": schedule,
        "raw_observations_saved": False,
        "model_fit_performed": False,
        "backtest_run": False,
    }


def write_outputs(result: dict) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "preflight.json"
    stamp = NOW.strftime("%Y-%m-%dT%H%M%SZ")
    report_path = SESSION_DIR / f"{stamp}_session-eth-validator-queue-source-preflight-{RUN_ID}.md"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Ethereum validator queue / ETH downside — source-only preflight",
        "",
        f"- **Candidate:** {CANDIDATE_ID}",
        f"- **Status:** {result['status']}",
        f"- **Run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Retrieved:** {NOW.isoformat()}",
        "- **Model fit:** False",
        "- **Backtest:** False",
        "- **Raw observations saved:** False",
        "",
    ]
    if result["status"] == "PASS":
        schedule = result["forecast_schedule_feasibility"]
        queue = result["cryptokeyhole"]
        price = result["binance_daily_price"]
        lines += [
            "## Source feasibility",
            "",
            f"- CryptoKeyhole metric: `{METRIC_ID}`; state `{queue['series']['state']}`; daily components: "
            + ", ".join(f"{item['name']} ({item['id']}, {item['final_non_null_count']} final values)"
                        for item in queue["series"]["components"]),
            f"- Entry/exit feature coverage: {queue['entry_wait_coverage']['coverage_fraction']:.3%} / "
            f"{queue['exit_wait_coverage']['coverage_fraction']:.3%}.",
            f"- Binance ETHUSDT daily rows: {price['observed_daily_rows']} across "
            f"{price['monthly_archive_count']} monthly and {price['daily_buffer_archive_count']} daily archives; "
            f"{price['archive_count']} SHA-256 sidecars verified.",
            f"- Forecast schedule: validation {schedule['validation']['valid_origins_after_source_exclusions']} / "
            f"{schedule['validation']['scheduled_origins']}; test "
            f"{schedule['test']['valid_origins_after_source_exclusions']} / {schedule['test']['scheduled_origins']}.",
            f"- Test regime coverage: {schedule['test']['pre_pectra_origins']} pre-Pectra and "
            f"{schedule['test']['post_pectra_origins']} post-Pectra origins.",
            f"- Training history: {schedule['minimum_training_events']}–{schedule['maximum_training_events']} "
            f"matured prior events; observed {schedule['observed_training_count_min']}–"
            f"{schedule['observed_training_count_max']}.",
            "",
            "## Methodology and limitations",
            "",
            "- Queue waits are computed as queue divided by churn limit, in days of 225 epochs.",
            "- Entry queue definition and churn calculation change at Pectra (2025-05-07); preserve a regime indicator and report pre/post results separately.",
            "- Exit queue includes voluntary exits, slashings and execution-layer exit requests; it is not a direct measure of ETH sales.",
            "- Execution-layer-requested partial withdrawals share exit churn but are absent from daily history; consolidation is a separate queue.",
            "- The free chart is current-vintage, not point-in-time. A two-day lag does not remove historical revision risk.",
            "- The source preflight is not a preregistration, model fit, empirical backtest or trading authorization.",
            "",
            "## Provenance",
            "",
            f"- CryptoKeyhole OpenAPI SHA-256: `{queue['openapi_sha256']}`.",
            f"- CryptoKeyhole catalog SHA-256: `{queue['catalog_response_sha256']}`.",
            f"- CryptoKeyhole series SHA-256: `{queue['series_response_sha256']}`.",
            f"- Binance canonical daily-close SHA-256: `{price['canonical_daily_close_sha256']}`.",
            "",
        ]
    else:
        lines += [
            "## Failure",
            "",
            f"- Error: `{result.get('error', 'unknown')}`",
            "",
            "## Partial evidence",
            "",
            json.dumps(result.get("partial_evidence", {}), indent=2, sort_keys=True),
            "",
        ]
    lines += [
        "## Durable artifacts",
        "",
        f"- Machine-readable manifest: `{manifest_path.relative_to(ROOT)}`.",
        f"- Source documentation: {CHART_URL} and {DATA_ACCESS_URL}.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(f"## ETH validator queue source preflight: {result['status']}\n\n")
            handle.write(f"- Candidate: {CANDIDATE_ID}\n")
            handle.write(f"- Manifest: `{manifest_path.relative_to(ROOT)}`\n")
    return manifest_path, report_path


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "candidate_id": CANDIDATE_ID,
            "source_commit_sha": SOURCE_SHA,
            "workflow_run_id": RUN_ID,
            "workflow_run_attempt": ATTEMPT,
            "status": "FAIL",
            "retrieved_at_utc": NOW.isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "partial_evidence": PARTIAL_EVIDENCE,
            "raw_observations_saved": False,
            "model_fit_performed": False,
            "backtest_run": False,
        }
    manifest_path, report_path = write_outputs(result)
    print(json.dumps({
        "result": result,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "report_path": str(report_path.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
