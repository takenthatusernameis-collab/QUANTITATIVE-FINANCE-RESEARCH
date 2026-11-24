#!/usr/bin/env python3
"""Bounded, read-only Binance Spot catalogue and archive feasibility audit.

Raw exchangeInfo responses and ZIP/CSV market data remain in memory only.
Only normalized metadata, request provenance, hashes and quality summaries are
written to the output directory.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import email.utils
import hashlib
import io
import json
import math
import re
import time
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests

API_BASE = "https://data-api.binance.vision"
ARCHIVE_BASE = "https://data.binance.vision/"
EXCHANGE_INFO_URL = API_BASE + "/api/v3/exchangeInfo"
KLINES_URL = API_BASE + "/api/v3/klines"
MAX_METADATA_REQUESTS = 50
MAX_ARCHIVE_OBJECTS = 12
MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
SEED_SYMBOLS = ("BTCUSDT", "ETHUSDT")
HISTORICAL_MONTH = "2020-01"
NEGATIVE_CONTROL_SYMBOL = "QFRNOTREALUSDT"
BLOCKED_STATUSES = {403, 418, 451}
UTC = dt.timezone.utc


class AuditStop(RuntimeError):
    """A route or budget must stop without bypassing its restriction."""


class RestrictedRoute(AuditStop):
    def __init__(self, status: int, url: str, message: str | None = None):
        self.status = status
        self.url = url
        super().__init__(message or f"HTTP {status}; stopped this route without retry or workaround")


class BudgetExceeded(AuditStop):
    pass


class NetworkFailure(AuditStop):
    pass


def now_utc() -> str:
    return dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def month_bounds(month: str) -> tuple[dt.datetime, dt.datetime, int]:
    year, number = (int(part) for part in month.split("-"))
    days = calendar.monthrange(year, number)[1]
    start = dt.datetime(year, number, 1, tzinfo=UTC)
    if number == 12:
        end = dt.datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = dt.datetime(year, number + 1, 1, tzinfo=UTC)
    return start, end, days * 24


def last_complete_month(now: dt.datetime | None = None) -> str:
    current = now or dt.datetime.now(UTC)
    first = current.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last = first - dt.timedelta(days=1)
    return last.strftime("%Y-%m")


def _retry_after_seconds(value: str | None) -> float:
    if not value:
        return 2.0
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return max(0.0, (parsed.astimezone(UTC) - dt.datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 2.0


class RequestClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.metadata_requests = 0
        self.http_requests = 0
        self.archive_object_urls: set[str] = set()
        self.downloaded_bytes = 0
        self.request_log: list[dict] = []

    @property
    def archive_objects(self) -> int:
        return len(self.archive_object_urls)

    @staticmethod
    def _headers(response: requests.Response) -> dict:
        wanted = (
            "Date", "Content-Type", "Content-Length", "Retry-After", "ETag",
            "X-MBX-USED-WEIGHT-1M", "x-amz-bucket-region",
        )
        return {key: response.headers[key] for key in wanted if key in response.headers}

    def get(self, url: str, *, kind: str = "metadata", params: dict | None = None):
        if kind not in {"metadata", "object"}:
            raise ValueError(f"Unknown request kind: {kind}")
        if kind == "object" and url not in self.archive_object_urls:
            if self.archive_objects >= MAX_ARCHIVE_OBJECTS:
                raise BudgetExceeded(f"Archive-object budget exhausted ({MAX_ARCHIVE_OBJECTS})")
            self.archive_object_urls.add(url)

        for attempt in range(2):
            if kind == "metadata":
                if self.metadata_requests >= MAX_METADATA_REQUESTS:
                    raise BudgetExceeded(
                        f"Metadata/API request budget exhausted ({MAX_METADATA_REQUESTS})"
                    )
                self.metadata_requests += 1
            self.http_requests += 1
            started = now_utc()
            try:
                response = self.session.get(
                    url, params=params, timeout=45, stream=(kind == "object")
                )
            except requests.RequestException as exc:
                self.request_log.append({
                    "kind": kind, "requested_url": url, "params": params,
                    "started_at_utc": started, "status_code": None,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                raise NetworkFailure(f"Network request failed for {url}: {exc}") from exc

            status = response.status_code
            record = {
                "kind": kind,
                "requested_url": url,
                "final_url": response.url,
                "params": params,
                "started_at_utc": started,
                "completed_at_utc": now_utc(),
                "status_code": status,
                "response_headers": self._headers(response),
                "attempt": attempt + 1,
            }

            if status == 429:
                wait = _retry_after_seconds(response.headers.get("Retry-After"))
                record["retry_after_seconds"] = wait
                self.request_log.append(record)
                response.close()
                if attempt == 0 and wait <= 120:
                    time.sleep(wait)
                    continue
                raise AuditStop(
                    f"HTTP 429 on {url}; Retry-After={wait:g}s; route deferred without another retry"
                )

            if status in BLOCKED_STATUSES:
                self.request_log.append(record)
                response.close()
                raise RestrictedRoute(status, url)

            if status == 404:
                record["response_bytes"] = 0
                self.request_log.append(record)
                response.close()
                return response, b""

            if status != 200:
                record["response_bytes"] = 0
                self.request_log.append(record)
                response.close()
                return response, b""

            if kind == "object":
                declared = response.headers.get("Content-Length")
                remaining = MAX_ARCHIVE_BYTES - self.downloaded_bytes
                if declared:
                    try:
                        if int(declared) > remaining:
                            self.request_log.append(record)
                            response.close()
                            raise BudgetExceeded(
                                f"Archive byte budget would be exceeded by {url}"
                            )
                    except ValueError:
                        pass
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if self.downloaded_bytes + size > MAX_ARCHIVE_BYTES:
                        self.request_log.append(record)
                        response.close()
                        raise BudgetExceeded(
                            f"Archive byte budget exceeded while downloading {url}"
                        )
                    chunks.append(chunk)
                payload = b"".join(chunks)
                self.downloaded_bytes += size
                record["response_bytes"] = size
            else:
                payload = response.content
                record["response_bytes"] = len(payload)

            self.request_log.append(record)
            response.close()
            return response, payload

        raise AuditStop(f"Request attempts exhausted for {url}")


def normalize_exchange_info(payload: bytes) -> tuple[list[dict], list[dict], dict]:
    data = json.loads(payload.decode("utf-8"))
    raw_symbols = data.get("symbols")
    if not isinstance(raw_symbols, list):
        raise ValueError("exchangeInfo response has no symbols array")

    records: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_symbols):
        if not isinstance(item, dict):
            errors.append({"index": index, "error": "symbol entry is not an object"})
            continue
        required = ("symbol", "status", "baseAsset", "quoteAsset")
        missing = [field for field in required if not item.get(field)]
        if missing:
            errors.append({"index": index, "symbol": item.get("symbol"), "error": f"missing {missing}"})
            continue
        symbol = str(item["symbol"])
        if symbol in seen:
            errors.append({"index": index, "symbol": symbol, "error": "duplicate symbol"})
            continue
        seen.add(symbol)
        records.append({
            "symbol": symbol,
            "status": str(item["status"]),
            "baseAsset": str(item["baseAsset"]),
            "quoteAsset": str(item["quoteAsset"]),
            "isSpotTradingAllowed": item.get("isSpotTradingAllowed"),
            "isMarginTradingAllowed": item.get("isMarginTradingAllowed"),
            "permissions": item.get("permissions", []),
            "permissionSets": item.get("permissionSets", []),
            "orderTypes": item.get("orderTypes", []),
            "filters": item.get("filters", []),
        })

    summary = {
        "timezone": data.get("timezone"),
        "server_time": data.get("serverTime"),
        "rate_limits": data.get("rateLimits", []),
        "symbol_count_reported": len(raw_symbols),
        "symbol_count_normalized": len(records),
        "parse_error_count": len(errors),
        "status_counts": dict(sorted(Counter(x["status"] for x in records).items())),
        "quote_asset_counts": dict(sorted(Counter(x["quoteAsset"] for x in records).items())),
        "quote_status_strata_counts": {
            f"{quote}|{status}": count
            for (quote, status), count in sorted(
                Counter((x["quoteAsset"], x["status"]) for x in records).items()
            )
        },
        "spot_trading_allowed_counts": {
            str(key): value
            for key, value in sorted(
                Counter(str(x["isSpotTradingAllowed"]) for x in records).items()
            )
        },
    }
    return records, errors, summary


def select_sample(records: list[dict]) -> tuple[list[str], dict]:
    lookup = {item["symbol"]: item for item in records}
    missing_seeds = [symbol for symbol in SEED_SYMBOLS if symbol not in lookup]
    if missing_seeds:
        raise ValueError(f"Positive-control symbols missing from full catalogue: {missing_seeds}")

    candidates = [item for item in records if item["symbol"] not in SEED_SYMBOLS]
    if not candidates:
        raise ValueError("No non-seed symbol available for deterministic sample")

    def diversity_score(item: dict) -> int:
        return int(item["quoteAsset"] != "USDT") + int(item["status"] != "TRADING")

    best_score = max(diversity_score(item) for item in candidates)
    pool = [item for item in candidates if diversity_score(item) == best_score]
    group_counts = Counter((item["quoteAsset"], item["status"]) for item in pool)
    rarest = min(group_counts.values())
    eligible_groups = sorted(group for group, count in group_counts.items() if count == rarest)
    chosen_group = eligible_groups[0]
    group_items = [
        item for item in pool
        if (item["quoteAsset"], item["status"]) == chosen_group
    ]
    chosen = min(
        group_items,
        key=lambda item: hashlib.sha256(
            f'{item["quoteAsset"]}|{item["status"]}|{item["symbol"]}'.encode("utf-8")
        ).hexdigest(),
    )
    symbols = [*SEED_SYMBOLS, chosen["symbol"]]
    return symbols, {
        "method": (
            "mandatory BTCUSDT/ETHUSDT controls; among all other catalogue entries, "
            "maximize (non-USDT quote, non-TRADING status), select the least-populated "
            "remaining quote/status stratum, then choose the minimum SHA-256 rank"
        ),
        "sample_symbols": symbols,
        "non_seed_symbol": chosen["symbol"],
        "selected_quote_status_stratum": {
            "quoteAsset": chosen["quoteAsset"], "status": chosen["status"]
        },
        "diversity_score": best_score,
        "candidate_count": len(candidates),
        "selected_stratum_population": len(group_items),
        "sample_is_non_exhaustive": True,
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_s3_listing(payload: bytes) -> dict:
    root = ET.fromstring(payload)
    if _local_name(root.tag) != "ListBucketResult":
        raise ValueError(f"Unexpected archive listing root: {_local_name(root.tag)}")
    values: dict[str, list[str] | str | None] = {
        "common_prefixes": [],
        "keys": [],
        "is_truncated": None,
        "next_continuation_token": None,
        "key_count": None,
    }
    for child in root:
        name = _local_name(child.tag)
        if name == "IsTruncated":
            values["is_truncated"] = (child.text or "").strip().lower() == "true"
        elif name == "NextContinuationToken":
            values["next_continuation_token"] = child.text
        elif name == "KeyCount":
            values["key_count"] = child.text
        elif name == "CommonPrefixes":
            for nested in child:
                if _local_name(nested.tag) == "Prefix" and nested.text:
                    values["common_prefixes"].append(nested.text)
        elif name == "Contents":
            for nested in child:
                if _local_name(nested.tag) == "Key" and nested.text:
                    values["keys"].append(nested.text)
    if values["is_truncated"] is None:
        raise ValueError("Archive listing response omitted IsTruncated")
    return values


def list_s3_prefix(
    client: RequestClient, prefix: str, *, delimiter: str | None = None
) -> dict:
    pages = 0
    common_prefixes: set[str] = set()
    keys: set[str] = set()
    page_summaries: list[dict] = []
    token: str | None = None
    complete = False
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if delimiter:
            params["delimiter"] = delimiter
        if token:
            params["continuation-token"] = token
        response, payload = client.get(ARCHIVE_BASE, kind="metadata", params=params)
        pages += 1
        if response.status_code != 200:
            return {
                "status": f"HTTP_{response.status_code}",
                "complete": False,
                "pages": pages,
                "common_prefix_count": len(common_prefixes),
                "key_count": len(keys),
                "page_summaries": page_summaries,
            }
        parsed = parse_s3_listing(payload)
        common_prefixes.update(parsed["common_prefixes"])
        keys.update(parsed["keys"])
        page_summaries.append({
            "page": pages,
            "key_count": parsed["key_count"],
            "is_truncated": parsed["is_truncated"],
            "common_prefixes_returned": len(parsed["common_prefixes"]),
            "keys_returned": len(parsed["keys"]),
            "continuation_token_present": bool(parsed["next_continuation_token"]),
        })
        if not parsed["is_truncated"]:
            complete = True
            break
        token = parsed["next_continuation_token"]
        if not token:
            break
        if client.metadata_requests >= MAX_METADATA_REQUESTS:
            break
    return {
        "status": "OK" if complete else "PAGINATION_INCOMPLETE",
        "complete": complete,
        "pages": pages,
        "common_prefix_count": len(common_prefixes),
        "key_count": len(keys),
        "common_prefixes": sorted(common_prefixes),
        "keys": sorted(keys),
        "page_summaries": page_summaries,
    }


def parse_timestamp(value: int) -> tuple[dt.datetime, str]:
    if value >= 10**14:
        unit = "us"
        stamp = dt.datetime.fromtimestamp(value / 1_000_000, tz=UTC)
    elif value >= 10**11:
        unit = "ms"
        stamp = dt.datetime.fromtimestamp(value / 1_000, tz=UTC)
    else:
        raise ValueError(f"Unsupported kline timestamp scale: {value}")
    return stamp, unit


def parse_monthly_kline_zip(payload: bytes, month: str) -> dict:
    start, end, expected_hours = month_bounds(month)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one CSV member; found {len(csv_names)}")
        text = archive.read(csv_names[0]).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    header_detected = False
    if rows and rows[0] and rows[0][0].strip().lower() in {"open_time", "open time"}:
        header_detected = True
        rows = rows[1:]

    expected_unit = "us" if month >= "2025-01" else "ms"
    expected_step = 3_600_000_000 if expected_unit == "us" else 3_600_000
    timestamps: list[int] = []
    close_errors = 0
    numeric_errors = 0
    ohlc_errors = 0
    out_of_month = 0
    observed_unit: str | None = None

    for row_number, row in enumerate(rows, start=2 if header_detected else 1):
        if len(row) != 12:
            raise ValueError(f"Row {row_number} has {len(row)} columns; expected 12")
        try:
            open_time = int(row[0])
            close_time = int(row[6])
            stamp, unit = parse_timestamp(open_time)
            if observed_unit is None:
                observed_unit = unit
            elif observed_unit != unit:
                raise ValueError("Mixed timestamp units within one archive")
            numeric = [float(row[index]) for index in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11)]
            if not all(math.isfinite(value) for value in numeric):
                numeric_errors += 1
            open_price, high, low, close, volume = numeric[:5]
            if (
                min(open_price, high, low, close) <= 0
                or high < max(open_price, close)
                or low > min(open_price, close)
                or high < low
                or volume < 0
                or numeric[5] < 0
                or numeric[6] < 0
            ):
                ohlc_errors += 1
            if close_time != open_time + expected_step - 1:
                close_errors += 1
            if stamp < start or stamp >= end:
                out_of_month += 1
            timestamps.append(open_time)
        except (ValueError, OverflowError, OSError) as exc:
            raise ValueError(f"Invalid kline row {row_number}: {exc}") from exc

    unique = set(timestamps)
    duplicate_count = len(timestamps) - len(unique)
    order_errors = sum(
        1 for previous, current in zip(timestamps, timestamps[1:]) if current <= previous
    )
    scale = 1_000_000 if observed_unit == "us" else 1_000
    start_value = int(start.timestamp() * scale)
    expected_values = set(range(start_value, start_value + expected_hours * expected_step, expected_step))
    observed_values = {value for value in unique if value in expected_values}
    missing_count = len(expected_values - observed_values)
    unexpected_count = len(unique - expected_values)
    first_stamp = parse_timestamp(timestamps[0])[0].isoformat() if timestamps else None
    last_stamp = parse_timestamp(timestamps[-1])[0].isoformat() if timestamps else None
    complete = bool(
        len(timestamps) == expected_hours
        and duplicate_count == 0
        and order_errors == 0
        and missing_count == 0
        and unexpected_count == 0
        and close_errors == 0
        and numeric_errors == 0
        and ohlc_errors == 0
        and out_of_month == 0
        and observed_unit == expected_unit
    )
    return {
        "csv_member": csv_names[0],
        "header_detected": header_detected,
        "columns": 12,
        "timestamp_unit": observed_unit,
        "expected_timestamp_unit": expected_unit,
        "rows": len(timestamps),
        "expected_hourly_rows": expected_hours,
        "first_open_time_utc": first_stamp,
        "last_open_time_utc": last_stamp,
        "duplicate_timestamps": duplicate_count,
        "out_of_order_timestamps": order_errors,
        "missing_hours": missing_count,
        "unexpected_timestamps": unexpected_count,
        "close_time_alignment_errors": close_errors,
        "numeric_errors": numeric_errors,
        "ohlc_or_volume_errors": ohlc_errors,
        "out_of_month_rows": out_of_month,
        "complete_month": complete,
    }


def parse_checksum(payload: bytes) -> str:
    match = re.search(rb"\b([0-9a-fA-F]{64})\b", payload)
    if not match:
        raise ValueError("No 64-character SHA-256 digest found in .CHECKSUM sidecar")
    return match.group(1).decode("ascii").lower()


def download_archive_check(
    client: RequestClient, symbol: str, month: str
) -> dict:
    filename = f"{symbol}-1h-{month}.zip"
    url = urljoin(ARCHIVE_BASE, f"data/spot/monthly/klines/{symbol}/1h/{filename}")
    result = {
        "symbol": symbol,
        "month": month,
        "url": url,
        "status": "NOT_STARTED",
        "checksum_verified": False,
        "archive_sha256": None,
        "archive_bytes": None,
        "checksum_error": None,
        "data_quality": None,
    }
    response, payload = client.get(url, kind="object")
    if response.status_code != 200:
        result["status"] = f"ARCHIVE_HTTP_{response.status_code}"
        return result
    result["archive_sha256"] = sha256_bytes(payload)
    result["archive_bytes"] = len(payload)

    checksum_response, checksum_payload = client.get(url + ".CHECKSUM", kind="object")
    if checksum_response.status_code == 200:
        try:
            expected = parse_checksum(checksum_payload)
            actual = result["archive_sha256"]
            if expected != actual:
                raise ValueError(f"SHA-256 mismatch: expected {expected}, got {actual}")
            result["checksum_verified"] = True
            result["checksum_sha256"] = expected
        except ValueError as exc:
            result["checksum_error"] = str(exc)
    else:
        result["checksum_error"] = f"Checksum sidecar HTTP {checksum_response.status_code}"

    try:
        result["data_quality"] = parse_monthly_kline_zip(payload, month)
    except Exception as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"

    result["status"] = (
        "ACCEPTED_SAMPLE"
        if result["checksum_verified"]
        and result["data_quality"]
        and result["data_quality"]["complete_month"]
        else "REJECTED_OR_INCOMPLETE_SAMPLE"
    )
    return result


def first_kline_inception(client: RequestClient, symbol: str) -> dict:
    params = {"symbol": symbol, "interval": "1h", "startTime": 0, "limit": 1}
    response, payload = client.get(KLINES_URL, kind="metadata", params=params)
    result = {
        "symbol": symbol,
        "request_url": response.url,
        "status_code": response.status_code,
        "first_kline_open_time_utc": None,
        "timestamp_unit": None,
        "rows_returned": None,
    }
    if response.status_code != 200:
        result["error"] = payload[:300].decode("utf-8", "replace") if payload else None
        return result
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        result["error"] = "Unexpected kline response type"
        return result
    result["rows_returned"] = len(data)
    if data:
        stamp, unit = parse_timestamp(int(data[0][0]))
        result["first_kline_open_time_utc"] = stamp.isoformat()
        result["timestamp_unit"] = unit
    return result


def symbol_from_prefix(prefix: str) -> str:
    parts = prefix.strip("/").split("/")
    return parts[-1] if parts else ""


def run_audit(output_dir: Path, run_id: str | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    client = RequestClient()
    recent_month = last_complete_month()
    manifest: dict = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "git_sha": __import__("os").environ.get("GITHUB_SHA"),
        "status": "INCOMPLETE",
        "scope": "public read-only Binance Spot catalogue and monthly 1h archive feasibility only",
        "limits": {
            "max_metadata_api_requests": MAX_METADATA_REQUESTS,
            "max_archive_objects": MAX_ARCHIVE_OBJECTS,
            "max_archive_bytes": MAX_ARCHIVE_BYTES,
        },
        "months": {
            "recent_complete_month": recent_month,
            "historical_month": HISTORICAL_MONTH,
        },
        "exchange_info": {},
        "catalogue": {},
        "archive_index": {},
        "sample": {},
        "first_kline_inception": [],
        "archive_checks": [],
        "negative_control": {},
        "classifications": {},
        "stop_reasons": [],
    }
    normalized_records: list[dict] = []
    archive_prefixes: list[str] = []
    try:
        retrieved = now_utc()
        response, payload = client.get(EXCHANGE_INFO_URL, kind="metadata")
        manifest["exchange_info"] = {
            "url": response.url,
            "retrieved_at_utc": retrieved,
            "status_code": response.status_code,
            "response_bytes": len(payload),
            "raw_response_sha256": sha256_bytes(payload) if payload else None,
            "response_headers": RequestClient._headers(response),
        }
        if response.status_code != 200:
            manifest["stop_reasons"].append(
                f"exchangeInfo returned HTTP {response.status_code}; no catalogue accepted"
            )
            return manifest
        normalized_records, parse_errors, summary = normalize_exchange_info(payload)
        manifest["catalogue"] = {**summary, "parse_errors": parse_errors}
        catalogue_doc = {
            "schema_version": 1,
            "retrieved_at_utc": retrieved,
            "source_url": response.url,
            "raw_response_sha256": manifest["exchange_info"]["raw_response_sha256"],
            "normalized_symbols": normalized_records,
        }
        (output_dir / "catalogue.json").write_text(
            json.dumps(catalogue_doc, indent=2, sort_keys=True), encoding="utf-8"
        )
        if parse_errors:
            manifest["stop_reasons"].append(
                f"{len(parse_errors)} catalogue entries could not be normalized"
            )

        sample_symbols, sample_method = select_sample(normalized_records)
        manifest["sample"] = sample_method

        # A delimiter listing enumerates symbol directories without downloading market data.
        try:
            index = list_s3_prefix(
                client, "data/spot/monthly/klines/", delimiter="/"
            )
            manifest["archive_index"] = {
                key: value for key, value in index.items() if key != "common_prefixes"
            }
            archive_prefixes = index.get("common_prefixes", [])
            if archive_prefixes:
                archive_symbols = sorted(symbol_from_prefix(item) for item in archive_prefixes)
                current_symbols = {item["symbol"] for item in normalized_records}
                archive_symbol_set = set(archive_symbols)
                manifest["archive_index"].update({
                    "archive_symbol_prefixes_count": len(archive_symbols),
                    "archive_only_prefix_count": len(archive_symbol_set - current_symbols),
                    "archive_only_prefix_sample": sorted(archive_symbol_set - current_symbols)[:100],
                    "current_catalogue_without_archive_prefix_count": len(current_symbols - archive_symbol_set),
                    "current_catalogue_without_archive_prefix_sample": sorted(current_symbols - archive_symbol_set)[:100],
                })
                archive_prefixes = sorted(archive_prefixes)
                (output_dir / "archive_symbol_prefixes.json").write_text(
                    json.dumps({
                        "retrieved_at_utc": now_utc(),
                        "complete": index.get("complete", False),
                        "prefixes": archive_prefixes,
                    }, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
        except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop, ValueError) as exc:
            manifest["archive_index"] = {
                "status": "UNAVAILABLE_OR_INCOMPLETE",
                "complete": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            manifest["stop_reasons"].append(
                "Archive listing/index route stopped; direct documented object URLs remain a separate route"
            )

        # Per-symbol 1h folder listings establish month-key semantics for the bounded sample.
        if manifest["archive_index"].get("status") == "OK":
            sample_month_indexes = []
            for symbol in sample_symbols:
                try:
                    listing = list_s3_prefix(
                        client, f"data/spot/monthly/klines/{symbol}/1h/"
                    )
                    month_keys = listing.get("keys", [])
                    sample_month_indexes.append({
                        "symbol": symbol,
                        "status": listing.get("status"),
                        "complete": listing.get("complete"),
                        "pages": listing.get("pages"),
                        "key_count": listing.get("key_count"),
                        "keys_for_recent_month": [
                            key for key in month_keys if key.endswith(f"-{recent_month}.zip")
                        ],
                        "keys_for_historical_month": [
                            key for key in month_keys if key.endswith(f"-{HISTORICAL_MONTH}.zip")
                        ],
                    })
                except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop, ValueError) as exc:
                    sample_month_indexes.append({
                        "symbol": symbol,
                        "status": "STOPPED",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    break
            manifest["archive_index"]["sample_symbol_month_indexes"] = sample_month_indexes

        # Earliest available kline is an independent sample-level inception proxy, not delisting evidence.
        for symbol in sample_symbols:
            try:
                manifest["first_kline_inception"].append(
                    first_kline_inception(client, symbol)
                )
            except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop) as exc:
                manifest["first_kline_inception"].append({
                    "symbol": symbol,
                    "status": "STOPPED",
                    "error": f"{type(exc).__name__}: {exc}",
                })
                manifest["stop_reasons"].append("Kline API route stopped; no alternate identity or route used")
                break

        # Five positive archive objects plus their sidecars, then one negative control: 11 objects maximum.
        checks = []
        plan = [
            (SEED_SYMBOLS[0], recent_month),
            (SEED_SYMBOLS[1], recent_month),
            (sample_symbols[2], recent_month),
            (SEED_SYMBOLS[0], HISTORICAL_MONTH),
            (SEED_SYMBOLS[1], HISTORICAL_MONTH),
        ]
        archive_route_stopped = False
        for symbol, month in plan:
            try:
                checks.append(download_archive_check(client, symbol, month))
            except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop) as exc:
                checks.append({
                    "symbol": symbol, "month": month, "status": "STOPPED",
                    "error": f"{type(exc).__name__}: {exc}",
                })
                manifest["stop_reasons"].append(
                    "Direct archive-object route stopped immediately; no access-control workaround attempted"
                )
                archive_route_stopped = True
                break
        manifest["archive_checks"] = checks

        if not archive_route_stopped:
            negative_url = urljoin(
                ARCHIVE_BASE,
                f"data/spot/monthly/klines/{NEGATIVE_CONTROL_SYMBOL}/1h/"
                f"{NEGATIVE_CONTROL_SYMBOL}-1h-{recent_month}.zip",
            )
            try:
                negative_response, negative_payload = client.get(negative_url, kind="object")
                manifest["negative_control"] = {
                    "symbol": NEGATIVE_CONTROL_SYMBOL,
                    "month": recent_month,
                    "url": negative_url,
                    "status_code": negative_response.status_code,
                    "expected_http_404": True,
                    "passed": negative_response.status_code == 404,
                    "unexpected_bytes": len(negative_payload),
                }
            except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop) as exc:
                manifest["negative_control"] = {
                    "symbol": NEGATIVE_CONTROL_SYMBOL,
                    "month": recent_month,
                    "status": "STOPPED",
                    "error": f"{type(exc).__name__}: {exc}",
                }

        current_symbols = {item["symbol"] for item in normalized_records}
        archive_symbols = {symbol_from_prefix(item) for item in archive_prefixes}
        index_complete = manifest["archive_index"].get("complete") is True
        positive_checks = [item for item in checks if item.get("status") == "ACCEPTED_SAMPLE"]
        manifest["classifications"] = {
            "current_spot_catalogue": (
                "VERIFIED" if normalized_records and not manifest["catalogue"].get("parse_error_count")
                and len(normalized_records) == manifest["catalogue"].get("symbol_count_reported")
                else "SAMPLE_ONLY"
            ),
            "archive_symbol_directory_index": "VERIFIED" if index_complete else "UNKNOWN",
            "archive_month_key_index_for_sample": (
                "SAMPLE_ONLY"
                if manifest["archive_index"].get("sample_symbol_month_indexes")
                else "UNKNOWN"
            ),
            "sampled_monthly_archive_integrity": (
                "SAMPLE_ONLY" if positive_checks else "UNKNOWN"
            ),
            "sampled_product_inception": (
                "SAMPLE_ONLY"
                if any(item.get("first_kline_open_time_utc") for item in manifest["first_kline_inception"])
                else "UNKNOWN"
            ),
            "delisted_symbol_inventory": (
                "SAMPLE_ONLY"
                if index_complete and archive_symbols - current_symbols
                else "UNKNOWN"
            ),
            "point_in_time_membership_and_delisting_dates": "UNKNOWN",
            "universe_wide_historical_archive_completeness": "UNKNOWN",
        }
        manifest["status"] = (
            "COMPLETED_WITH_SAMPLE_EVIDENCE"
            if manifest["classifications"]["current_spot_catalogue"] == "VERIFIED"
            else "INCOMPLETE"
        )
    except (RestrictedRoute, BudgetExceeded, NetworkFailure, AuditStop, ValueError, json.JSONDecodeError) as exc:
        manifest["status"] = "STOPPED_OR_INCOMPLETE"
        manifest["stop_reasons"].append(f"{type(exc).__name__}: {exc}")
    finally:
        manifest["completed_at_utc"] = now_utc()
        manifest["request_budget_used"] = {
            "metadata_api_requests": client.metadata_requests,
            "metadata_api_limit": MAX_METADATA_REQUESTS,
            "http_requests_total": client.http_requests,
            "unique_archive_objects": client.archive_objects,
            "archive_object_limit": MAX_ARCHIVE_OBJECTS,
            "archive_bytes_downloaded": client.downloaded_bytes,
            "archive_byte_limit": MAX_ARCHIVE_BYTES,
        }
        manifest["request_log"] = client.request_log
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        if archive_prefixes and not (output_dir / "archive_symbol_prefixes.json").exists():
            (output_dir / "archive_symbol_prefixes.json").write_text(
                json.dumps({"complete": False, "prefixes": sorted(archive_prefixes)}, indent=2),
                encoding="utf-8",
            )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    manifest = run_audit(Path(args.output_dir), run_id=args.run_id)
    print(json.dumps({
        "status": manifest.get("status"),
        "classifications": manifest.get("classifications"),
        "request_budget_used": manifest.get("request_budget_used"),
        "stop_reasons": manifest.get("stop_reasons"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
