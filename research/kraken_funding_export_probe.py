#!/usr/bin/env python3
"""Anonymous, bounded inspection of Kraken's official historical-funding ZIP export.

The archive is downloaded only to runner-local temporary storage, inspected in place,
and deleted. Only a compact manifest and a landing-page screenshot are uploaded.
No authentication, account access, region attestation, CAPTCHA bypass, proxy, purchase,
trading action, raw-data artifact, or raw-data commit is used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

PAGE_URL = "https://support.kraken.com/articles/export-historical-funding-rates"
API_BASE = "https://futures.kraken.com/derivatives/api/v3"
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
MAX_CSV_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_MEMBERS_REPORTED = 500
MAX_TOTAL_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_CANDIDATE_CSVS = 30
MAX_API_SYMBOLS = 8
EXPECTED_ARCHIVE_SIZE_BYTES = 109_980_750
EXPECTED_ARCHIVE_SHA256 = "65ba6712a6ab657389d2795d3ed77bedb4270841dfe711147ae9df16e366edab"
TARGETED_SYMBOLS = ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD")
HISTORICAL_CUTOVER_MS = 1_664_452_800_000  # 2022-09-29 12:00:00 UTC
PI_DELISTING_OBSERVATION_START_MS = int(datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc).timestamp() * 1000)
PI_DELISTING_MS = int(datetime(2026, 10, 30, 16, 0, tzinfo=timezone.utc).timestamp() * 1000)
RATE_FIELD_NAMES = ("fundingRate", "relativeFundingRate", "absolute_rate", "relative_rate")
# CSV absolute_rate and relative_rate are kept separate; only overlap comparison tests their API-field correspondence.
TIME_KEYS = {"timestamp", "time", "fundingtime", "fundingtimestamp", "datetime", "date"}
PERPETUAL_PREFIXES = {"PI", "PF"}


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def parse_timestamp_ms(value: Any) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        numeric = float(raw)
        if math.isfinite(numeric):
            if abs(numeric) >= 1e12:
                return int(numeric)
            if abs(numeric) >= 1e9:
                return int(numeric * 1000)
    except (ValueError, TypeError):
        pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except (ValueError, OverflowError):
        return None


def asset_from_instrument(instrument: dict[str, Any]) -> str | None:
    base = str(instrument.get("base") or "").upper()
    pair_base = str(instrument.get("pair") or "").upper().split(":", 1)[0]
    exact_base = base or pair_base
    if exact_base in {"XBT", "BTC"}:
        return "BTC"
    if exact_base == "ETH":
        return "ETH"
    return None


def is_perpetual_instrument(instrument: dict[str, Any]) -> bool:
    symbol = str(instrument.get("symbol") or "").upper()
    prefix = symbol.split("_", 1)[0]
    kind = str(instrument.get("type") or "").lower()
    return prefix in PERPETUAL_PREFIXES or (
        kind == "flexible_futures" and not instrument.get("lastTradingTime")
    )


def compact_instrument(instrument: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "symbol", "pair", "base", "quote", "type", "underlying",
        "contractSize", "contractValue", "contractValueTradePrecision",
        "tickSize", "settlementCurrency", "openingDate", "lastTradingTime",
        "isExpired", "tradeable", "impactMidSize", "maxPositionSize",
    )
    compact = {key: instrument.get(key) for key in keys if key in instrument}
    expired = instrument.get("isExpired")
    tradeable = instrument.get("tradeable")
    if expired is True:
        compact["lifecycle_status"] = "EXPIRED"
    elif expired is False and tradeable is True:
        compact["lifecycle_status"] = "ACTIVE"
    else:
        compact["lifecycle_status"] = "UNKNOWN"
    if expired is True and tradeable is True:
        compact["lifecycle_flag_conflict"] = True
        compact["lifecycle_interpretation"] = (
            "isExpired=true conflicts with tradeable=true; use the official contract delisting/settlement notice "
            "rather than the tradeable flag to determine current lifecycle"
        )
    else:
        compact["lifecycle_flag_conflict"] = False
    return compact


def _find_column(headers: list[str], accepted: set[str]) -> str | None:
    return next((header for header in headers if norm_key(header) in accepted), None)


def analyze_csv_stream(stream: Any) -> dict[str, Any]:
    reader = csv.DictReader(stream)
    headers = reader.fieldnames or []
    time_col = _find_column(headers, TIME_KEYS)
    rate_cols = [
        header for header in headers
        if norm_key(header) in {norm_key(name) for name in RATE_FIELD_NAMES}
    ]
    row_count = 0
    valid_timestamp_count = 0
    first_timestamp_raw: str | None = None
    last_timestamp_raw: str | None = None
    null_counts = Counter()
    duplicate_count = 0
    out_of_order_count = 0
    invalid_timestamp_count = 0
    previous_ms: int | None = None
    seen: set[int] = set()
    timestamps: list[tuple[int, str, dict[str, str]]] = []
    rate_stats: dict[str, dict[str, Any]] = {
        column: {"min": None, "max": None, "invalid_count": 0}
        for column in rate_cols
    }
    categorical_counts: dict[str, Counter] = {}
    for row in reader:
        if not row or all(value is None or not str(value).strip() for value in row.values()):
            continue
        row_count += 1
        for header in headers:
            value = row.get(header)
            if value is None or not str(value).strip():
                null_counts[header] += 1
        compact_rates = {column: str(row.get(column, "") or "").strip() for column in rate_cols}
        if "tradeable" in {norm_key(header) for header in headers}:
            tradeable_col = next(header for header in headers if norm_key(header) == "tradeable")
            categorical_counts.setdefault(tradeable_col, Counter())[
                str(row.get(tradeable_col, "") or "").strip()
            ] += 1
        if time_col:
            raw_time = str(row.get(time_col, "") or "").strip()
            stamp_ms = parse_timestamp_ms(raw_time)
            if stamp_ms is None:
                invalid_timestamp_count += 1
            else:
                valid_timestamp_count += 1
                if first_timestamp_raw is None:
                    first_timestamp_raw = raw_time
                last_timestamp_raw = raw_time
                if stamp_ms in seen:
                    duplicate_count += 1
                seen.add(stamp_ms)
                if previous_ms is not None and stamp_ms < previous_ms:
                    out_of_order_count += 1
                timestamps.append((stamp_ms, raw_time, compact_rates))
                previous_ms = stamp_ms
        for column in rate_cols:
            raw_rate = str(row.get(column, "") or "").strip()
            try:
                rate = float(raw_rate)
                if not math.isfinite(rate):
                    raise ValueError("nonfinite")
                current = rate_stats[column]
                current["min"] = rate if current["min"] is None else min(current["min"], rate)
                current["max"] = rate if current["max"] is None else max(current["max"], rate)
            except (ValueError, TypeError):
                rate_stats[column]["invalid_count"] += 1

    gaps = Counter()
    gap_samples = []
    for left, right in zip(timestamps, timestamps[1:]):
        delta = right[0] - left[0]
        if delta > 0:
            hours = round(delta / 3_600_000, 6)
            gaps[hours] += 1
            if hours > 4 and len(gap_samples) < 20:
                gap_samples.append({
                    "from": left[1],
                    "to": right[1],
                    "hours": hours,
                })
    samples: list[dict[str, Any]] = []
    if timestamps:
        positions = sorted({0, len(timestamps) // 4, len(timestamps) // 2,
                            (3 * len(timestamps)) // 4, len(timestamps) - 1})
        for index in positions:
            stamp_ms, raw_time, rates = timestamps[index]
            samples.append({
                "timestamp": raw_time,
                "timestamp_ms": stamp_ms,
                "rates": rates,
            })
    column_semantics: dict[str, str] = {}
    tradeable_header = next(
        (header for header in headers if norm_key(header) == "tradeable"), None
    )
    if tradeable_header:
        observed_tradeable_values = categorical_counts.get(tradeable_header, Counter())
        if observed_tradeable_values and all(
            re.fullmatch(r"(?:PI|PF)_[A-Z0-9]+", value.upper())
            for value in observed_tradeable_values
        ):
            column_semantics[tradeable_header] = (
                "Observed values are Kraken instrument symbols, not boolean flags; "
                "preserve the raw values verbatim."
            )
    ordered_ms = [item[0] for item in timestamps]
    internal_rows = [
        {"timestamp": raw_time, "timestamp_ms": stamp_ms, "rates": rates}
        for stamp_ms, raw_time, rates in timestamps
    ]
    return {
        "format": "csv",
        "headers": headers,
        "row_count": row_count,
        "timestamp_column": time_col,
        "timestamp_timezone_note": "CSV timestamps are timezone-naive; UTC is assumed only for comparison with Kraken's UTC API timestamps.",
        "valid_timestamp_count": valid_timestamp_count,
        "invalid_timestamp_count": invalid_timestamp_count if time_col else None,
        "first_timestamp": first_timestamp_raw,
        "last_timestamp": last_timestamp_raw,
        "min_timestamp": min((item[1] for item in timestamps), key=lambda x: parse_timestamp_ms(x)) if timestamps else None,
        "max_timestamp": max((item[1] for item in timestamps), key=lambda x: parse_timestamp_ms(x)) if timestamps else None,
        "duplicate_timestamp_count": duplicate_count if time_col else None,
        "out_of_order_timestamp_count": out_of_order_count if time_col else None,
        "cadence_hours_top": [
            {"hours": hours, "count": count}
            for hours, count in gaps.most_common(20)
        ],
        "gaps_over_4h_count": sum(count for hours, count in gaps.items() if hours > 4),
        "gaps_over_4h_samples": gap_samples,
        "rate_fields": rate_stats,
        "null_counts": {header: null_counts[header] for header in headers},
        "categorical_value_counts": {
            column: dict(counts) for column, counts in categorical_counts.items()
        },
        "column_semantics": column_semantics,
        "crosscheck_samples": samples,
        "_api_crosscheck_rows": internal_rows,
    }


def _asset_from_filename(name: str) -> str | None:
    stem = Path(name).stem.upper()
    if "_" in stem:
        stem = stem.split("_", 1)[1]
    for token, asset in (("XBT", "BTC"), ("BTC", "BTC"), ("ETH", "ETH")):
        if stem.startswith(token):
            quote = stem[len(token):]
            if quote.startswith(("USD", "USDT", "USDC", "EUR", "GBP", "JPY", "CHF")):
                return asset
    return None


def _symbol_from_filename(name: str) -> str:
    return Path(name).stem.upper().replace("-", "_").replace(" ", "_")


def analyze_archive(
    path: Path,
    instruments: list[dict[str, Any]],
    target_symbols: set[str] | None = None,
) -> dict[str, Any]:
    """Inspect BTC/ETH perpetual CSVs, optionally restricted to exact instrument symbols."""
    specs_by_symbol = {
        norm_key(str(item.get("symbol", ""))): item
        for item in instruments if item.get("symbol")
    }
    summary: dict[str, Any] = {
        "target_symbols_requested": sorted(target_symbols) if target_symbols is not None else None,
        "archive_size_bytes": path.stat().st_size,
        "archive_sha256": sha256_file(path),
        "zip_valid": False,
        "archive_member_count": 0,
        "archive_members": [],
        "asset_csv_candidates": [],
        "perpetual_csv_summaries": [],
    }
    with zipfile.ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        total_uncompressed = sum(item.file_size for item in files)
        summary["total_uncompressed_bytes"] = total_uncompressed
        summary["zip_valid"] = True
        summary["zip_crc_scope"] = "candidate CSV members are CRC-checked when read; other members are listed but not decompressed"
        summary["archive_uncompressed_size_limit_exceeded"] = total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES
        summary["archive_member_count"] = len(files)
        summary["archive_members"] = [
            {"name": item.filename, "compressed_size": item.compress_size,
             "uncompressed_size": item.file_size}
            for item in files[:MAX_ARCHIVE_MEMBERS_REPORTED]
        ]
        summary["archive_members_truncated"] = len(files) > MAX_ARCHIVE_MEMBERS_REPORTED
        summary["ignored_macos_metadata_members"] = sum(
            1 for item in files
            if "__MACOSX" in Path(item.filename).parts or Path(item.filename).name.startswith("._")
        )

        candidate_files = []
        for item in files:
            if not item.filename.lower().endswith(".csv"):
                continue
            if "__MACOSX" in Path(item.filename).parts or Path(item.filename).name.startswith("._"):
                continue
            stem = _symbol_from_filename(item.filename)
            if target_symbols is not None and stem not in target_symbols:
                continue
            matched = specs_by_symbol.get(norm_key(stem))
            asset = asset_from_instrument(matched) if matched else _asset_from_filename(item.filename)
            if asset not in {"BTC", "ETH"}:
                continue
            prefix = stem.split("_", 1)[0]
            perpetual = bool(matched and is_perpetual_instrument(matched)) or prefix in PERPETUAL_PREFIXES
            candidate = {
                "member": item.filename,
                "asset": asset,
                "symbol_from_filename": stem,
                "matched_instrument": compact_instrument(matched) if matched else None,
                "perpetual_candidate": perpetual,
                "classification_basis": (
                    "exact instrument base plus instrument metadata" if matched
                    else "exact base token plus Kraken PI_/PF_ symbol prefix"
                ),
                "uncompressed_size_bytes": item.file_size,
            }
            summary["asset_csv_candidates"].append(candidate)
            if perpetual:
                candidate_files.append((item, asset, stem, matched))

        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            summary["perpetual_csv_summaries"] = []
            summary["candidate_csvs_truncated"] = len(candidate_files) > MAX_CANDIDATE_CSVS
            return summary

        for item, asset, symbol, matched in candidate_files[:MAX_CANDIDATE_CSVS]:
            record = {
                "member": item.filename,
                "asset": asset,
                "symbol": str((matched or {}).get("symbol") or symbol),
                "instrument": compact_instrument(matched) if matched else None,
                "inspection": "not_started",
            }
            if item.file_size > MAX_CSV_UNCOMPRESSED_BYTES:
                record["inspection"] = "uncompressed_csv_size_limit_exceeded"
            else:
                try:
                    with archive.open(item) as raw:
                        text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig",
                                                       errors="replace", newline="")
                        record["data_summary"] = analyze_csv_stream(text_stream)
                    record["inspection"] = "inspected"
                except Exception as exc:
                    record["inspection"] = "csv_parse_error"
                    record["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            summary["perpetual_csv_summaries"].append(record)
    summary["candidate_csvs_truncated"] = len([
        item for item in summary["asset_csv_candidates"] if item["perpetual_candidate"]
    ]) > MAX_CANDIDATE_CSVS
    if target_symbols is not None:
        found = {
            str(item.get("symbol") or "").upper()
            for item in summary["perpetual_csv_summaries"]
        }
        summary["target_symbols_found"] = sorted(found)
        summary["target_symbols_missing"] = sorted(target_symbols - found)
    return summary


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_download(url: str) -> dict[str, Any]:
    result: dict[str, Any] = {"requested_url": url}
    session = requests.Session()
    try:
        response = session.head(url, allow_redirects=True, timeout=(10, 30))
        headers = {key.lower(): value for key, value in response.headers.items()}
        result.update({
            "method": "HEAD",
            "status": response.status_code,
            "final_url": response.url,
            "content_type": headers.get("content-type"),
            "content_length": int(headers["content-length"]) if headers.get("content-length", "").isdigit() else None,
            "content_disposition": headers.get("content-disposition"),
        })
        if response.status_code not in (200, 206) or result["content_length"] is None:
            response.close()
            ranged = session.get(url, headers={"Range": "bytes=0-0"},
                                 allow_redirects=True, stream=True, timeout=(10, 30))
            range_headers = {key.lower(): value for key, value in ranged.headers.items()}
            content_range = range_headers.get("content-range", "")
            total_match = re.search(r"/(\d+)$", content_range)
            result["range_probe"] = {
                "status": ranged.status_code,
                "final_url": ranged.url,
                "content_type": range_headers.get("content-type"),
                "content_range": content_range or None,
                "content_length": int(total_match.group(1)) if total_match else (
                    int(range_headers["content-length"])
                    if range_headers.get("content-length", "").isdigit() else None
                ),
            }
            if result["range_probe"]["content_length"] is not None:
                result["content_length"] = result["range_probe"]["content_length"]
            if result.get("content_type") is None:
                result["content_type"] = result["range_probe"].get("content_type")
            ranged.close()
        return result
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        return result
    finally:
        session.close()


def fetch_instruments() -> dict[str, Any]:
    result: dict[str, Any] = {"requests": [], "instruments": [], "perpetual_btc_eth": []}
    seen: set[str] = set()
    for expired in (False, True):
        url = f"{API_BASE}/instruments"
        try:
            response = requests.get(url, params={"expired": str(expired).lower()},
                                    timeout=(10, 45))
            request_record = {
                "url": response.url,
                "status": response.status_code,
                "expired_filter": expired,
                "content_type": response.headers.get("Content-Type"),
            }
            if response.status_code != 200:
                request_record["error"] = response.text[:300]
                result["requests"].append(request_record)
                continue
            payload = response.json()
            request_record["result"] = payload.get("result")
            request_record["serverTime"] = payload.get("serverTime")
            rows = payload.get("instruments") or []
            request_record["instrument_count"] = len(rows)
            result["requests"].append(request_record)
            for item in rows:
                symbol = str(item.get("symbol") or "").upper()
                if symbol and symbol not in seen:
                    seen.add(symbol)
                    result["instruments"].append(item)
        except (requests.RequestException, ValueError) as exc:
            result["requests"].append({
                "expired_filter": expired,
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            })

    candidates = []
    for item in result["instruments"]:
        if asset_from_instrument(item) in {"BTC", "ETH"} and is_perpetual_instrument(item):
            candidates.append(item)
    result["perpetual_btc_eth"] = [compact_instrument(item) for item in candidates]
    return result


def fetch_historical_funding(symbol: str) -> dict[str, Any]:
    url = f"{API_BASE}/historical-funding-rates"
    try:
        response = requests.get(url, params={"symbol": symbol}, timeout=(10, 60))
        record: dict[str, Any] = {
            "symbol": symbol,
            "url": response.url,
            "status": response.status_code,
            "content_type": response.headers.get("Content-Type"),
            "response_sha256": hashlib.sha256(response.content).hexdigest(),
        }
        if response.status_code != 200:
            record["error"] = response.text[:400]
            return record
        payload = response.json()
        rates = payload.get("rates") or []
        record.update({
            "result": payload.get("result"),
            "serverTime": payload.get("serverTime"),
            "rate_count": len(rates),
            "first_timestamp": rates[0].get("timestamp") if rates else None,
            "last_timestamp": rates[-1].get("timestamp") if rates else None,
            "rates": rates,
        })
        return record
    except (requests.RequestException, ValueError) as exc:
        return {"symbol": symbol, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def _utc_iso(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()

def _compact_rate_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep only timestamp and the two funding-rate fields in evidence manifests."""
    rates = row.get("rates") or {}
    return {
        "timestamp": row.get("timestamp"),
        "timestamp_ms": row.get("timestamp_ms"),
        "rates": {
            key: rates.get(key)
            for key in ("absolute_rate", "relative_rate", "fundingRate", "relativeFundingRate")
            if key in rates
        },
    }


def expected_interval_hours(left_timestamp_ms: int) -> int:
    """Return the observed/documented Kraken cadence regime for an interval's left boundary."""
    return 4 if left_timestamp_ms < HISTORICAL_CUTOVER_MS else 1


def extract_archive_interval_anomalies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract every interval inconsistent with the 4h-to-1h schedule, with adjacent rows."""
    ordered = sorted(
        (
            row for row in rows
            if isinstance(row, dict) and row.get("timestamp_ms") is not None
        ),
        key=lambda row: int(row["timestamp_ms"]),
    )
    anomalies = []
    for index, (left, right) in enumerate(zip(ordered, ordered[1:])):
        left_ms = int(left["timestamp_ms"])
        right_ms = int(right["timestamp_ms"])
        delta_ms = right_ms - left_ms
        if delta_ms <= 0:
            continue
        actual_hours = round(delta_ms / 3_600_000, 6)
        expected_hours = expected_interval_hours(left_ms)
        if math.isclose(actual_hours, expected_hours, rel_tol=0.0, abs_tol=1e-6):
            continue
        context = ordered[max(0, index - 1):min(len(ordered), index + 3)]
        missing_hourly = []
        if delta_ms % 3_600_000 == 0:
            missing_hourly = [
                _utc_iso(stamp)
                for stamp in range(left_ms + 3_600_000, right_ms, 3_600_000)
            ]
        anomalies.append({
            "from_utc": _utc_iso(left_ms),
            "to_utc": _utc_iso(right_ms),
            "actual_interval_hours": actual_hours,
            "expected_interval_hours": expected_hours,
            "missing_hourly_boundaries": missing_hourly,
            "left_record": _compact_rate_row(left),
            "right_record": _compact_rate_row(right),
            "adjacent_context_records": [_compact_rate_row(row) for row in context],
            "classification": "UNEXPECTED_ARCHIVE_INTERVAL_REQUIRES_EXPLANATION",
        })
    return anomalies


def compare_archive_anomalies_to_api(
    anomalies: list[dict[str, Any]],
    api_record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare exact archive gap endpoints and missing hourly boundaries with the API tail."""
    api_by_timestamp = {}
    for row in api_record.get("rates") or []:
        if not isinstance(row, dict):
            continue
        stamp = parse_timestamp_ms(row.get("timestamp"))
        if stamp is not None:
            api_by_timestamp[stamp] = row

    compared = []
    for anomaly in anomalies:
        item = dict(anomaly)
        endpoint_checks = {}
        for label in ("left_record", "right_record"):
            archive_row = anomaly.get(label) or {}
            stamp = archive_row.get("timestamp_ms")
            try:
                stamp = int(stamp)
            except (TypeError, ValueError):
                stamp = None
            api_row = api_by_timestamp.get(stamp)
            comparisons = {}
            archive_rates = archive_row.get("rates") or {}
            if api_row is not None:
                for archive_field, api_field in (
                    ("absolute_rate", "fundingRate"),
                    ("relative_rate", "relativeFundingRate"),
                ):
                    try:
                        archive_value = float(archive_rates.get(archive_field))
                        api_value = float(api_row.get(api_field))
                        equal = (
                            math.isfinite(archive_value)
                            and math.isfinite(api_value)
                            and math.isclose(archive_value, api_value, rel_tol=1e-10, abs_tol=1e-12)
                        )
                    except (TypeError, ValueError):
                        archive_value = archive_rates.get(archive_field)
                        api_value = api_row.get(api_field)
                        equal = False
                    comparisons[archive_field] = {
                        "api_field": api_field,
                        "archive_value": archive_value,
                        "api_value": api_value,
                        "equal_with_tolerance": equal,
                    }
            endpoint_checks[label] = {
                "timestamp": archive_row.get("timestamp"),
                "api_row_present": api_row is not None,
                "rate_comparisons": comparisons,
            }

        missing_boundaries = []
        for timestamp in anomaly.get("missing_hourly_boundaries") or []:
            stamp = parse_timestamp_ms(timestamp)
            api_row = api_by_timestamp.get(stamp)
            missing_boundaries.append({
                "timestamp": timestamp,
                "api_row_present": api_row is not None,
                "api_rates": {
                    field: api_row.get(field)
                    for field in ("fundingRate", "relativeFundingRate")
                } if api_row is not None else None,
            })
        endpoint_present = all(
            value["api_row_present"] for value in endpoint_checks.values()
        )
        boundary_present = [value["api_row_present"] for value in missing_boundaries]
        if not endpoint_present:
            comparison_status = "API_ENDPOINT_COVERAGE_INCOMPLETE"
        elif boundary_present and all(boundary_present):
            comparison_status = "API_CONTAINS_ARCHIVE_MISSING_BOUNDARIES"
        elif boundary_present and not any(boundary_present):
            comparison_status = "BOTH_SOURCES_OMIT_ARCHIVE_MISSING_BOUNDARIES"
        elif any(boundary_present):
            comparison_status = "PARTIAL_API_BOUNDARY_COVERAGE"
        else:
            comparison_status = "ENDPOINTS_PRESENT_NO_HOURLY_BOUNDARY_EXPECTED"
        item["api_comparison"] = {
            "api_symbol": api_record.get("symbol"),
            "api_response_sha256": api_record.get("response_sha256"),
            "endpoint_checks": endpoint_checks,
            "missing_boundary_checks": missing_boundaries,
            "comparison_status": comparison_status,
            "interpretation": (
                "Source-row presence comparison only; neither source's absence proves no payable funding event."
            ),
        }
        compared.append(item)
    return compared


def rate_cap_assessment(
    symbol: str,
    field: str,
    timestamp_ms: int | None,
    value: float,
) -> dict[str, Any]:
    """Compare relative rates only with the date-appropriate documented cap."""
    symbol = symbol.upper()
    result = {
        "symbol": symbol,
        "field": field,
        "value": value,
        "timestamp_utc": _utc_iso(timestamp_ms),
        "applicable_absolute_cap": None,
        "cap_status": "NOT_APPLICABLE",
        "evidence_scope": "absolute fundingRate is not the relative hourly rate",
        "evidence_url": None,
    }
    if field != "relativeFundingRate":
        return result
    if timestamp_ms is None:
        result.update({
            "cap_status": "UNVERIFIABLE_TIMESTAMP",
            "evidence_scope": "rate timestamp could not be parsed",
        })
        return result
    if symbol.startswith("PI_"):
        cap = 0.001 if timestamp_ms < HISTORICAL_CUTOVER_MS else 0.0025
        result.update({
            "applicable_absolute_cap": cap,
            "evidence_scope": (
                "historical inverse cap before 2022-09-29 12:00 UTC"
                if timestamp_ms < HISTORICAL_CUTOVER_MS
                else "current inverse cap ±0.25% per hour"
            ),
            "evidence_url": (
                "https://support.mtf.kraken.com/hc/en-us/articles/7009378818333-Inverse-Perpetual-Contracts-Funding-Rate-Method-Prior-to-September-29-2022"
                if timestamp_ms < HISTORICAL_CUTOVER_MS
                else "https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives"
            ),
        })
    elif symbol.startswith("PF_"):
        if timestamp_ms < HISTORICAL_CUTOVER_MS:
            result.update({
                "cap_status": "HISTORICAL_LINEAR_CAP_UNVERIFIED",
                "evidence_scope": "pre-cutover PF cadence is observed, but PF-specific historical cap is not established",
                "evidence_url": None,
            })
            return result
        cap = 0.005
        result.update({
            "applicable_absolute_cap": cap,
            "evidence_scope": "current linear cap ±0.50% per hour",
            "evidence_url": "https://support.kraken.com/articles/4844359082772-linear-multi-collateral-derivatives-contract-specifications",
        })
    else:
        result.update({
            "cap_status": "UNKNOWN_INSTRUMENT_FAMILY",
            "evidence_scope": "no contract-family cap mapping",
        })
        return result

    result["cap_status"] = (
        "EXCEEDS_DOCUMENTED_CAP"
        if abs(value) > cap + 1e-12
        else "WITHIN_DOCUMENTED_CAP"
    )
    if symbol.startswith("PI_") and timestamp_ms >= PI_DELISTING_OBSERVATION_START_MS:
        result["delisting_observation_window_review"] = (
            "AT_OR_AFTER_2026-10-30T15:00:00Z; timestamp-to-accrual mapping remains unresolved"
        )
        result["delisting_evidence_url"] = "https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings"
    if symbol.startswith("PI_") and timestamp_ms >= PI_DELISTING_MS:
        result["delisting_settlement_boundary_review"] = "AT_OR_AFTER_2026-10-30T16:00:00Z"
    return result


def extract_api_extrema(api_record: dict[str, Any]) -> dict[str, Any]:
    """Retain timestamped min/max rows and immediate neighbors, never the full API history."""
    rows = api_record.get("rates") or []
    symbol = str(api_record.get("symbol") or "").upper()
    result: dict[str, Any] = {
        "symbol": symbol,
        "http_status": api_record.get("status"),
        "result": api_record.get("result"),
        "request_url": api_record.get("url"),
        "serverTime": api_record.get("serverTime"),
        "response_sha256": api_record.get("response_sha256"),
        "row_count": len(rows),
        "extrema": {},
    }
    for field in ("fundingRate", "relativeFundingRate"):
        valid = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            stamp = parse_timestamp_ms(row.get("timestamp"))
            try:
                value = float(row.get(field))
                if stamp is None or not math.isfinite(value):
                    continue
                valid.append((index, stamp, value, row))
            except (TypeError, ValueError):
                continue
        field_result = {"valid_count": len(valid), "min": None, "max": None}
        for label, selector in (("min", min), ("max", max)):
            if not valid:
                continue
            extreme_value = selector(item[2] for item in valid)
            matches = [item for item in valid if item[2] == extreme_value]
            match_records = []
            for index, stamp, value, row in matches:
                context = []
                for neighbor_index in range(max(0, index - 1), min(len(rows), index + 2)):
                    neighbor = rows[neighbor_index]
                    if not isinstance(neighbor, dict):
                        continue
                    neighbor_stamp = parse_timestamp_ms(neighbor.get("timestamp"))
                    if neighbor_stamp is None:
                        continue
                    neighbor_values = {}
                    for rate_field in ("fundingRate", "relativeFundingRate"):
                        raw = neighbor.get(rate_field)
                        try:
                            number = float(raw)
                            neighbor_values[rate_field] = number if math.isfinite(number) else None
                        except (TypeError, ValueError):
                            neighbor_values[rate_field] = None
                    context.append({
                        "timestamp": neighbor.get("timestamp"),
                        "timestamp_ms": neighbor_stamp,
                        "rates": neighbor_values,
                    })
                match_records.append({
                    "timestamp": row.get("timestamp"),
                    "timestamp_ms": stamp,
                    "value": value,
                    "cap_assessment": rate_cap_assessment(symbol, field, stamp, value),
                    "adjacent_context_records": context,
                })
            field_result[label] = {
                "value": extreme_value,
                "match_count": len(matches),
                "matches": match_records,
            }
        result["extrema"][field] = field_result
    return result


def timestamp_semantics_assessment() -> dict[str, Any]:
    """Separate documented rate-period mechanics from undocumented API timestamp mapping."""
    return {
        "official_contract_mechanics": (
            "The inverse contract specification describes a one-hour rate-setting window, "
            "next-period application, continuous accrual and hourly settlement. Its examples "
            "describe the mechanics but do not explicitly bind a historical API row's timestamp "
            "to the accrual interval."
        ),
        "api_reference_scope": (
            "The historical-funding API documents the symbol parameter and ascending timestamp "
            "order, but does not define whether each returned timestamp labels the start or end "
            "of the rate's accrual interval. Therefore the API field-to-period mapping remains "
            "unresolved even though the contract's rate-setting mechanics are described."
        ),
        "evidence_urls": {
            "historical_funding_api": "https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates",
            "inverse_contract_specs": "https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives",
            "linear_contract_specs": "https://support.kraken.com/articles/4844359082772-linear-multi-collateral-derivatives-contract-specifications",
            "historical_inverse_method": "https://support.mtf.kraken.com/hc/en-us/articles/7009378818333-Inverse-Perpetual-Contracts-Funding-Rate-Method-Prior-to-September-29-2022",
        },
        "rate_period_mechanics": "NEXT_PERIOD_RATE_SET_AT_PRIOR_BOUNDARY",
        "api_timestamp_boundary_semantics": "UNRESOLVED",
        "backtest_alignment_status": "BLOCKED_PENDING_API_FIELD_MAPPING",
        "inference_prohibited": True,
    }



def _interval_metrics(timestamps: list[int]) -> dict[str, Any]:
    ordered = sorted(set(timestamps))
    gaps = Counter()
    gap_samples = []
    non_hourly_gap_samples = []
    non_hourly_gap_count = 0
    max_gap_hours: float | None = None
    for left, right in zip(ordered, ordered[1:]):
        hours = round((right - left) / 3_600_000, 6)
        if hours <= 0:
            continue
        gaps[hours] += 1
        max_gap_hours = hours if max_gap_hours is None else max(max_gap_hours, hours)
        sample = {
            "from_utc": _utc_iso(left),
            "to_utc": _utc_iso(right),
            "hours": hours,
        }
        if hours > 4 and len(gap_samples) < 20:
            gap_samples.append(sample)
        if not math.isclose(hours, 1.0, rel_tol=0.0, abs_tol=1e-6):
            non_hourly_gap_count += 1
            if len(non_hourly_gap_samples) < 20:
                non_hourly_gap_samples.append(sample)
    return {
        "cadence_hours_top": [
            {"hours": hours, "count": count}
            for hours, count in gaps.most_common(20)
        ],
        "gaps_over_4h_count": sum(count for hours, count in gaps.items() if hours > 4),
        "gaps_over_4h_samples": gap_samples,
        "non_hourly_gap_count": non_hourly_gap_count,
        "non_hourly_gap_samples": non_hourly_gap_samples,
        "max_positive_gap_hours": max_gap_hours,
    }


def _compact_rate_context_row(symbol: str, row: Any) -> dict[str, Any] | None:
    """Retain one API row's timestamp and two rate fields, never unrelated payload."""
    if not isinstance(row, dict):
        return None
    timestamp_ms = parse_timestamp_ms(row.get("timestamp"))
    if timestamp_ms is None:
        return None
    rates: dict[str, float | None] = {}
    for field in ("fundingRate", "relativeFundingRate"):
        try:
            value = float(row.get(field))
            rates[field] = value if math.isfinite(value) else None
        except (TypeError, ValueError):
            rates[field] = None
    relative = rates["relativeFundingRate"]
    return {
        "timestamp": row.get("timestamp"),
        "timestamp_ms": timestamp_ms,
        "rates": rates,
        "relative_rate_cap_assessment": (
            rate_cap_assessment(symbol, "relativeFundingRate", timestamp_ms, relative)
            if relative is not None else None
        ),
    }


def analyze_api_rows(api_record: dict[str, Any]) -> dict[str, Any]:
    """Quality-check every returned Kraken API row without claiming history completeness."""
    raw_rows = api_record.get("rates")
    rows = raw_rows if isinstance(raw_rows, list) else []
    symbol = str(api_record.get("symbol") or "").upper()
    cap_status_counts = Counter()
    cap_exception_rows = []
    cap_assessed_count = 0
    required_fields = ("timestamp", "fundingRate", "relativeFundingRate")
    observed_fields = {
        str(key)
        for row in rows if isinstance(row, dict)
        for key in row.keys()
    }
    fields = sorted(observed_fields | set(required_fields))
    null_counts = {field: 0 for field in fields}
    rate_fields = {
        field: {"min": None, "max": None, "valid_count": 0, "invalid_count": 0}
        for field in ("fundingRate", "relativeFundingRate")
    }
    valid_timestamps: list[int] = []
    raw_first_timestamp = None
    raw_last_timestamp = None
    invalid_row_count = 0
    invalid_timestamp_count = 0
    duplicate_timestamp_count = 0
    out_of_order_timestamp_count = 0
    seen: set[int] = set()
    previous_timestamp: int | None = None

    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            invalid_row_count += 1
            for field in fields:
                null_counts[field] += 1
            for field in rate_fields:
                rate_fields[field]["invalid_count"] += 1
            invalid_timestamp_count += 1
            continue

        for field in fields:
            value = row.get(field)
            if value is None or not str(value).strip():
                null_counts[field] += 1

        raw_timestamp = row.get("timestamp")
        if raw_first_timestamp is None:
            raw_first_timestamp = raw_timestamp
        raw_last_timestamp = raw_timestamp
        timestamp_ms = parse_timestamp_ms(raw_timestamp)
        if timestamp_ms is None:
            invalid_timestamp_count += 1
        else:
            valid_timestamps.append(timestamp_ms)
            if timestamp_ms in seen:
                duplicate_timestamp_count += 1
            seen.add(timestamp_ms)
            if previous_timestamp is not None and timestamp_ms < previous_timestamp:
                out_of_order_timestamp_count += 1
            previous_timestamp = timestamp_ms

        for field, stats in rate_fields.items():
            raw_value = row.get(field)
            try:
                value = float(raw_value)
                if not math.isfinite(value):
                    raise ValueError("nonfinite")
                stats["min"] = value if stats["min"] is None else min(stats["min"], value)
                stats["max"] = value if stats["max"] is None else max(stats["max"], value)
                stats["valid_count"] += 1
            except (ValueError, TypeError):
                stats["invalid_count"] += 1

        if timestamp_ms is not None:
            try:
                relative_value = float(row.get("relativeFundingRate"))
                if not math.isfinite(relative_value):
                    raise ValueError("nonfinite")
                assessment = rate_cap_assessment(symbol, "relativeFundingRate", timestamp_ms, relative_value)
                cap_status = assessment.get("cap_status", "UNKNOWN")
                cap_status_counts[cap_status] += 1
                cap_assessed_count += 1
                if cap_status == "EXCEEDS_DOCUMENTED_CAP":
                    absolute_rate = None
                    try:
                        candidate_absolute = float(row.get("fundingRate"))
                        if math.isfinite(candidate_absolute):
                            absolute_rate = candidate_absolute
                    except (TypeError, ValueError):
                        pass
                    adjacent_context = [
                        compact
                        for neighbor_index in range(max(0, row_index - 1), min(len(rows), row_index + 2))
                        if (compact := _compact_rate_context_row(symbol, rows[neighbor_index])) is not None
                    ]
                    cap_exception_rows.append({
                        "timestamp": raw_timestamp,
                        "timestamp_utc": assessment.get("timestamp_utc"),
                        "fundingRate": absolute_rate,
                        "relativeFundingRate": relative_value,
                        "adjacent_context_records": adjacent_context,
                        "value": relative_value,
                        "applicable_absolute_cap": assessment.get("applicable_absolute_cap"),
                        "cap_status": cap_status,
                        "evidence_scope": assessment.get("evidence_scope"),
                        "evidence_url": assessment.get("evidence_url"),
                        "delisting_observation_window_review": assessment.get("delisting_observation_window_review"),
                        "delisting_settlement_boundary_review": assessment.get("delisting_settlement_boundary_review"),
                    })
            except (ValueError, TypeError):
                pass

    unique_timestamps = sorted(set(valid_timestamps))
    intervals = _interval_metrics(unique_timestamps)
    return {
        "http_status": api_record.get("status"),
        "api_result": api_record.get("result"),
        "row_count": len(rows),
        "invalid_row_count": invalid_row_count,
        "valid_timestamp_count": len(valid_timestamps),
        "invalid_timestamp_count": invalid_timestamp_count,
        "unique_timestamp_count": len(unique_timestamps),
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "out_of_order_timestamp_count": out_of_order_timestamp_count,
        "source_order_non_decreasing": out_of_order_timestamp_count == 0,
        "first_timestamp_in_response": raw_first_timestamp,
        "last_timestamp_in_response": raw_last_timestamp,
        "min_timestamp_utc": _utc_iso(unique_timestamps[0]) if unique_timestamps else None,
        "max_timestamp_utc": _utc_iso(unique_timestamps[-1]) if unique_timestamps else None,
        "null_counts": null_counts,
        "rate_fields": rate_fields,
        "relative_rate_cap_assessment": {
            "symbol": symbol,
            "field": "relativeFundingRate",
            "rows_assessed": cap_assessed_count,
            "rows_unassessed": len(rows) - cap_assessed_count,
            "status_counts": dict(cap_status_counts),
            "exceeds_documented_cap_count": len(cap_exception_rows),
            "exceeds_documented_cap_rows": cap_exception_rows,
        },
        **intervals,
        "history_completeness_status": "PROVISIONAL_NOT_ACCEPTED",
        "history_completeness_claim": "not_established_by_endpoint_response",
    }


def analyze_archive_api_union(
    archive_rows: list[dict[str, Any]],
    api_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize timestamp coverage union per exact instrument; do not merge rate values."""
    archive_timestamps = []
    for row in archive_rows:
        stamp = row.get("timestamp_ms")
        try:
            stamp = int(stamp)
        except (ValueError, TypeError):
            continue
        archive_timestamps.append(stamp)

    api_timestamps = []
    for row in api_rows:
        if not isinstance(row, dict):
            continue
        stamp = parse_timestamp_ms(row.get("timestamp"))
        if stamp is not None:
            api_timestamps.append(stamp)

    archive_set = set(archive_timestamps)
    api_set = set(api_timestamps)
    overlap = archive_set & api_set
    archive_only = archive_set - api_set
    api_only = api_set - archive_set
    archive_min = min(archive_set) if archive_set else None
    archive_max = max(archive_set) if archive_set else None
    api_min = min(api_set) if api_set else None
    api_max = max(api_set) if api_set else None
    api_only_tail = {
        stamp for stamp in api_only
        if archive_max is None or stamp > archive_max
    }
    api_only_before = {
        stamp for stamp in api_only
        if archive_min is not None and stamp < archive_min
    }
    api_only_within = api_only - api_only_tail - api_only_before
    union_timestamps = sorted(archive_set | api_set)
    intervals = _interval_metrics(union_timestamps)

    return {
        "archive_valid_timestamp_rows": len(archive_timestamps),
        "api_valid_timestamp_rows": len(api_timestamps),
        "archive_unique_timestamps": len(archive_set),
        "api_unique_timestamps": len(api_set),
        "archive_duplicate_timestamp_count": len(archive_timestamps) - len(archive_set),
        "api_duplicate_timestamp_count": len(api_timestamps) - len(api_set),
        "overlap_timestamps": len(overlap),
        "archive_only_timestamps": len(archive_only),
        "api_only_timestamps": len(api_only),
        "api_only_tail_timestamps": len(api_only_tail),
        "api_only_before_archive_timestamps": len(api_only_before),
        "api_only_within_archive_bounds": len(api_only_within),
        "union_unique_timestamps": len(union_timestamps),
        "archive_start_utc": _utc_iso(archive_min),
        "archive_end_utc": _utc_iso(archive_max),
        "api_start_utc": _utc_iso(api_min),
        "api_end_utc": _utc_iso(api_max),
        "union_start_utc": _utc_iso(union_timestamps[0]) if union_timestamps else None,
        "union_end_utc": _utc_iso(union_timestamps[-1]) if union_timestamps else None,
        "rate_values_merged": False,
        "history_completeness_status": "PROVISIONAL_NOT_ACCEPTED",
        **{f"union_{key}": value for key, value in intervals.items()},
    }


def crosscheck_archive_api(
    archive_record: dict[str, Any],
    api_record: dict[str, Any],
) -> dict[str, Any]:
    summary = archive_record.get("data_summary") or {}
    archive_rows = (
        summary.get("_api_crosscheck_rows")
        or summary.get("crosscheck_samples")
        or []
    )
    api_rows = api_record.get("rates") or []
    api_by_time: dict[int, dict[str, Any]] = {}
    for row in api_rows:
        if not isinstance(row, dict):
            continue
        stamp = parse_timestamp_ms(row.get("timestamp"))
        if stamp is not None:
            api_by_time[stamp] = row

    archive_by_time: dict[int, dict[str, Any]] = {}
    for row in archive_rows:
        stamp = row.get("timestamp_ms")
        if stamp is not None:
            archive_by_time[int(stamp)] = row

    api_set = set(api_by_time)
    archive_set = set(archive_by_time)
    matched_times = sorted(api_set & archive_set)
    archive_only = sorted(archive_set - api_set)
    api_only = sorted(api_set - archive_set)

    shared_start = max(min(api_set), min(archive_set)) if api_set and archive_set else None
    shared_end = min(max(api_set), max(archive_set)) if api_set and archive_set else None
    if shared_start is not None and shared_end is not None and shared_start <= shared_end:
        archive_shared = {stamp for stamp in archive_set if shared_start <= stamp <= shared_end}
        api_shared = {stamp for stamp in api_set if shared_start <= stamp <= shared_end}
    else:
        archive_shared, api_shared = set(), set()

    field_pairs = (
        ("absolute_rate", "fundingRate"),
        ("relative_rate", "relativeFundingRate"),
        ("fundingRate", "fundingRate"),
        ("relativeFundingRate", "relativeFundingRate"),
    )
    field_results: dict[str, Any] = {}
    archive_field_names = {
        key
        for row in archive_rows
        for key in (row.get("rates") or {}).keys()
    }
    for archive_name, api_name in field_pairs:
        if archive_name not in archive_field_names:
            continue
        compared = 0
        mismatch = 0
        max_abs = 0.0
        for stamp in matched_times:
            archive_value = (archive_by_time[stamp].get("rates") or {}).get(archive_name)
            api_value = api_by_time[stamp].get(api_name)
            try:
                left, right = float(archive_value), float(api_value)
                if not math.isfinite(left) or not math.isfinite(right):
                    raise ValueError("nonfinite")
                difference = abs(left - right)
                max_abs = max(max_abs, difference)
                compared += 1
                if not math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-12):
                    mismatch += 1
            except (ValueError, TypeError):
                mismatch += 1
        field_results[f"{archive_name} -> {api_name}"] = {
            "compared_values": compared,
            "mismatches": mismatch,
            "max_absolute_difference": max_abs if compared else None,
            "all_compared_values_equal_with_tolerance": compared > 0 and mismatch == 0,
        }

    sample_comparisons = []
    if matched_times:
        positions = sorted({
            0, len(matched_times) // 4, len(matched_times) // 2,
            (3 * len(matched_times)) // 4, len(matched_times) - 1,
        })
        for index in positions:
            stamp = matched_times[index]
            archive_row = archive_by_time[stamp]
            api_row = api_by_time[stamp]
            fields = {}
            for archive_name, api_name in field_pairs:
                if archive_name not in (archive_row.get("rates") or {}):
                    continue
                try:
                    left = float(archive_row["rates"][archive_name])
                    right = float(api_row[api_name])
                    fields[archive_name] = {
                        "api_field": api_name,
                        "archive": left,
                        "api": right,
                        "absolute_difference": abs(left - right),
                        "equal_with_tolerance": math.isclose(
                            left, right, rel_tol=1e-8, abs_tol=1e-12
                        ),
                    }
                except (KeyError, ValueError, TypeError):
                    fields[archive_name] = {
                        "api_field": api_name,
                        "comparison": "unavailable",
                    }
            sample_comparisons.append({
                "timestamp": archive_row.get("timestamp"),
                "fields": fields,
            })

    api_quality = analyze_api_rows(api_record)
    union_summary = analyze_archive_api_union(archive_rows, api_rows)
    shared_denominator = max(len(archive_shared), len(api_shared))
    return {
        "symbol": archive_record.get("symbol"),
        "api_status": api_record.get("status"),
        "api_result": api_record.get("result"),
        "api_rate_count": api_record.get("rate_count"),
        "api_first_timestamp": api_record.get("first_timestamp"),
        "api_last_timestamp": api_record.get("last_timestamp"),
        "archive_first_timestamp": summary.get("first_timestamp"),
        "archive_last_timestamp": summary.get("last_timestamp"),
        "overlap_start_utc": _utc_iso(shared_start) if shared_start is not None and shared_start <= shared_end else None,
        "overlap_end_utc": _utc_iso(shared_end) if shared_start is not None and shared_start <= shared_end else None,
        "archive_rows_in_shared_coverage": len(archive_shared),
        "api_rows_in_shared_coverage": len(api_shared),
        "matched_timestamps": len(matched_times),
        "archive_only_timestamps": len(archive_only),
        "api_only_timestamps": len(api_only),
        "api_only_tail_timestamps": union_summary["api_only_tail_timestamps"],
        "timestamp_sets_equal": bool(archive_set) and archive_set == api_set,
        "shared_coverage_timestamp_sets_equal": bool(archive_shared) and archive_shared == api_shared,
        "timestamp_match_rate_against_larger_shared_coverage_set": (
            len(matched_times) / shared_denominator if shared_denominator else None
        ),
        "api_quality": api_quality,
        "archive_api_union": union_summary,
        "rate_field_comparisons": field_results,
        "representative_overlap_samples": sample_comparisons,
        "api_history_completeness_claim": "not_established_by_endpoint_response",
    }



def run_api_cap_audit(output_dir: Path) -> dict[str, Any]:
    """Audit every public API relative-rate row without downloading the historical ZIP."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "probe": "kraken_public_historical_funding_api_rate_cap_census",
        "mode": "api-cap-audit",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "access_mode": "anonymous_public_api",
        "auth_used": False,
        "account_access_used": False,
        "region_attestation_used": False,
        "captcha_bypass_used": False,
        "proxy_or_network_workaround_used": False,
        "purchase_or_payment_used": False,
        "trading_action_used": False,
        "archive_download_attempted": False,
        "raw_api_rows_retained": False,
        "raw_api_rows_uploaded": False,
        "raw_api_rows_committed": False,
        "funding_acceptance_status": "PROVISIONAL_NOT_ACCEPTED",
        "status": "not_started",
    }
    try:
        instruments = fetch_instruments()
        manifest["instrument_api"] = {
            "requests": instruments.get("requests", []),
            "instrument_count": len(instruments.get("instruments") or []),
        }
        manifest["target_instrument_lifecycle"] = [
            compact_instrument(item)
            for item in instruments.get("instruments", [])
            if str(item.get("symbol") or "").upper() in TARGETED_SYMBOLS
        ]
        api_records = [fetch_historical_funding(symbol) for symbol in TARGETED_SYMBOLS]
        manifest["public_api_quality"] = [
            {"symbol": item.get("symbol"), **analyze_api_rows(item)}
            for item in api_records
        ]
        manifest["api_extrema"] = [extract_api_extrema(item) for item in api_records]
        quality_by_symbol = {item.get("symbol"): item for item in manifest["public_api_quality"]}
        manifest["api_rate_cap_status_counts_by_symbol"] = {
            symbol: (quality.get("relative_rate_cap_assessment") or {}).get("status_counts", {})
            for symbol, quality in quality_by_symbol.items()
        }
        manifest["api_rate_cap_exception_count_by_symbol"] = {
            symbol: (quality.get("relative_rate_cap_assessment") or {}).get("exceeds_documented_cap_count", 0)
            for symbol, quality in quality_by_symbol.items()
        }
        manifest["api_rate_cap_exceptions"] = [
            {"symbol": symbol, **row}
            for symbol, quality in quality_by_symbol.items()
            for row in (quality.get("relative_rate_cap_assessment") or {}).get("exceeds_documented_cap_rows", [])
        ]
        manifest["api_rate_cap_extrema_exceptions"] = [
            {
                "symbol": item.get("symbol"), "field": field, "extreme": extreme,
                "value": row.get("value"), "timestamp": row.get("timestamp"),
                "cap_assessment": row.get("cap_assessment"),
            }
            for item in manifest["api_extrema"]
            for field in ("relativeFundingRate",)
            for extreme in ("min", "max")
            for row in (item.get("extrema", {}).get(field, {}).get(extreme) or {}).get("matches", [])
            if row.get("cap_assessment", {}).get("cap_status") == "EXCEEDS_DOCUMENTED_CAP"
        ]
        manifest["public_api_responses"] = [
            {key: value for key, value in item.items() if key != "rates"}
            for item in api_records
        ]
        manifest["timestamp_semantics_assessment"] = timestamp_semantics_assessment()
        manifest["parameter_changelog_review"] = {
            "source_url": "https://support.kraken.com/ro/articles/13049711807636-derivatives-platform-parameters-changelog",
            "page_last_updated": "2026-10-01",
            "finding": (
                "The reviewed public changelog contains a PF_OGNUSD-specific maximum relative funding-rate change "
                "in 2023 and PI_XBTUSD/PI_ETHUSD margin-class entries in 2024; no PI_XBTUSD or PI_ETHUSD funding-cap "
                "change was found in the reviewed entries. This is not proof that no unpublished or omitted parameter "
                "change ever occurred."
            ),
        }
        manifest["delisting_reference"] = {
            "source_url": "https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings",
            "settlement_date": "2026-10-30",
            "inverse_btc_eth_settlement_time_utc": "16:00",
        }
        api_ok = (
            len(api_records) == len(TARGETED_SYMBOLS)
            and all(item.get("status") == 200 and item.get("rates") for item in api_records)
            and set(quality_by_symbol) == set(TARGETED_SYMBOLS)
        )
        api_integrity_ok = api_ok and all(
            quality.get("invalid_row_count") == 0
            and quality.get("invalid_timestamp_count") == 0
            and quality.get("duplicate_timestamp_count") == 0
            and quality.get("out_of_order_timestamp_count") == 0
            and all(count == 0 for count in quality.get("null_counts", {}).values())
            and all(stats.get("invalid_count") == 0 for stats in quality.get("rate_fields", {}).values())
            for quality in quality_by_symbol.values()
        )
        all_cap_rows_assessed = api_ok and all(
            (quality.get("relative_rate_cap_assessment") or {}).get("rows_unassessed") == 0
            for quality in quality_by_symbol.values()
        )
        lifecycle_symbols = {
            str(item.get("symbol") or "").upper()
            for item in manifest["target_instrument_lifecycle"]
        }
        lifecycle_ok = lifecycle_symbols == set(TARGETED_SYMBOLS)
        manifest["targeted_acceptance_checks"] = {
            "all_four_api_responses_nonempty": api_ok,
            "all_four_api_rows_pass_integrity": api_integrity_ok,
            "all_four_instrument_lifecycle_records_found": lifecycle_ok,
            "all_relative_rate_rows_cap_assessed": all_cap_rows_assessed,
            "cap_violation_count_by_symbol": manifest["api_rate_cap_exception_count_by_symbol"],
            "funding_acceptance": "PROVISIONAL_NOT_ACCEPTED",
        }
        manifest["status"] = (
            "api_cap_audit_complete"
            if api_ok and api_integrity_ok and lifecycle_ok and all_cap_rows_assessed
            else "api_cap_audit_incomplete"
        )
    except Exception as exc:
        manifest["status"] = "api_cap_audit_error"
        manifest["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return manifest



def run_probe(output_dir: Path, mode: str = "export") -> dict[str, Any]:
    if mode not in {"export", "anomaly-audit"}:
        raise ValueError("mode must be 'export' or 'anomaly-audit'")
    targeted = mode == "anomaly-audit"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "probe": "kraken_official_historical_funding_export",
        "mode": mode,
        "funding_acceptance_status": "PROVISIONAL_NOT_ACCEPTED",
        "page_url": PAGE_URL,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "access_mode": "anonymous_public_page_and_public_api",
        "auth_used": False,
        "account_access_used": False,
        "region_attestation_used": False,
        "captcha_bypass_used": False,
        "proxy_or_network_workaround_used": False,
        "purchase_or_payment_used": False,
        "trading_action_used": False,
        "raw_download_uploaded": False,
        "raw_download_committed": False,
        "raw_download_deleted_after_inspection": False,
        "status": "not_started",
    }
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True,
                                         viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            response_records: list[dict[str, Any]] = []

            def capture_response(response: Any) -> None:
                if "assets-cms.kraken.com" in response.url:
                    try:
                        headers = response.all_headers()
                    except Exception:
                        headers = {}
                    response_records.append({
                        "url": response.url,
                        "status": response.status,
                        "content_type": headers.get("content-type"),
                        "content_length": headers.get("content-length"),
                        "content_disposition": headers.get("content-disposition"),
                    })

            page.on("response", capture_response)
            page_response = page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=60000)
            manifest["page_http_status"] = page_response.status if page_response else None
            manifest["page_final_url"] = page.url
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except PlaywrightTimeout:
                manifest["page_networkidle_timeout"] = True
            page.wait_for_timeout(1000)
            manifest["page_title"] = page.title()
            manifest["page_text_excerpt"] = (page.locator("body").inner_text(timeout=5000) or "")[:2500]
            screenshot = output_dir / "kraken-funding-export-page.png"
            page.screenshot(path=str(screenshot), full_page=False)
            manifest["screenshot"] = screenshot.name

            links = page.get_by_role("link", name=re.compile(r"^\s*Export funding rates\s*$", re.I))
            if links.count() != 1:
                manifest["status"] = "export_link_not_unique"
                manifest["export_link_count"] = links.count()
            else:
                href = links.first.get_attribute("href")
                if href and href.startswith("/"):
                    href = page.url.rstrip("/") + href
                manifest["export_link_url"] = href
                if not href or urlparse(href).scheme != "https":
                    manifest["status"] = "export_link_not_https"
                else:
                    preflight = _head_download(href)
                    manifest["download_preflight"] = preflight
                    content_length = preflight.get("content_length")
                    status = preflight.get("status")
                    range_status = (preflight.get("range_probe") or {}).get("status")
                    usable_status = status in (200, 206) or range_status == 206
                    if not usable_status:
                        manifest["status"] = "download_preflight_failed"
                    elif content_length is None:
                        manifest["status"] = "download_size_unknown"
                        manifest["download_skipped_reason"] = "No bounded Content-Length or Content-Range total was exposed."
                    elif content_length > MAX_DOWNLOAD_BYTES:
                        manifest["status"] = "download_size_limit_exceeded"
                        manifest["download_skipped_reason"] = "Advertised archive exceeds the 512 MiB safety limit."
                    else:
                        with tempfile.TemporaryDirectory(prefix="kraken-funding-export-") as temporary:
                            archive_path = Path(temporary) / "kraken-funding-export.zip"
                            try:
                                with page.expect_download(timeout=90000) as download_info:
                                    links.first.click(timeout=15000)
                                download = download_info.value
                                manifest["download_suggested_filename"] = download.suggested_filename
                                manifest["download_url"] = download.url
                                download.save_as(str(archive_path))
                                manifest["download_response_records"] = response_records[:10]
                                if not archive_path.exists():
                                    manifest["status"] = "download_file_missing"
                                elif archive_path.stat().st_size > MAX_DOWNLOAD_BYTES:
                                    manifest["status"] = "download_size_limit_exceeded_after_download"
                                    manifest["download_size_bytes"] = archive_path.stat().st_size
                                elif not zipfile.is_zipfile(archive_path):
                                    manifest["status"] = "downloaded_file_not_zip"
                                    manifest["download_size_bytes"] = archive_path.stat().st_size
                                    manifest["download_sha256"] = sha256_file(archive_path)
                                else:
                                    instruments = fetch_instruments()
                                    manifest["instrument_api"] = {
                                        "requests": instruments["requests"],
                                        "instrument_count": len(instruments["instruments"]),
                                        "perpetual_btc_eth": instruments["perpetual_btc_eth"],
                                    }
                                    if targeted:
                                        manifest["target_instrument_lifecycle"] = [
                                            compact_instrument(item)
                                            for item in instruments["instruments"]
                                            if str(item.get("symbol") or "").upper() in TARGETED_SYMBOLS
                                        ]
                                    archive_summary = analyze_archive(
                                        archive_path,
                                        instruments["instruments"],
                                        target_symbols=set(TARGETED_SYMBOLS) if targeted else None,
                                    )
                                    manifest["archive"] = archive_summary
                                    manifest["archive_hash_check"] = {
                                        "expected_size_bytes": EXPECTED_ARCHIVE_SIZE_BYTES if targeted else None,
                                        "actual_size_bytes": archive_path.stat().st_size,
                                        "size_matches_prior": (
                                            archive_path.stat().st_size == EXPECTED_ARCHIVE_SIZE_BYTES
                                            if targeted else None
                                        ),
                                        "expected_sha256": EXPECTED_ARCHIVE_SHA256 if targeted else None,
                                        "actual_sha256": archive_summary.get("archive_sha256"),
                                        "matches_prior_inspected_archive": (
                                            archive_summary.get("archive_sha256") == EXPECTED_ARCHIVE_SHA256
                                            if targeted else None
                                        ),
                                    }
                                    if targeted:
                                        for item in archive_summary["perpetual_csv_summaries"]:
                                            data_summary = item.get("data_summary") or {}
                                            item["residual_interval_anomalies"] = extract_archive_interval_anomalies(
                                                data_summary.get("_api_crosscheck_rows") or []
                                            )
                                    api_symbols: list[str] = list(TARGETED_SYMBOLS) if targeted else []
                                    if not targeted:
                                        for item in archive_summary["perpetual_csv_summaries"]:
                                            symbol = str(item.get("symbol") or "").upper()
                                            if symbol and symbol not in api_symbols:
                                                api_symbols.append(symbol)
                                        for item in instruments["perpetual_btc_eth"]:
                                            symbol = str(item.get("symbol") or "").upper()
                                            if symbol and symbol not in api_symbols:
                                                api_symbols.append(symbol)
                                        api_symbols = api_symbols[:MAX_API_SYMBOLS]
                                    api_records = [fetch_historical_funding(symbol) for symbol in api_symbols]
                                    manifest["public_api_quality"] = [
                                        {"symbol": item.get("symbol"), **analyze_api_rows(item)}
                                        for item in api_records
                                    ]
                                    quality_by_symbol = {
                                        item.get("symbol"): item for item in manifest["public_api_quality"]
                                    }
                                    manifest["api_rate_cap_status_counts_by_symbol"] = {
                                        symbol: (quality.get("relative_rate_cap_assessment") or {}).get("status_counts", {})
                                        for symbol, quality in quality_by_symbol.items()
                                    }
                                    manifest["api_rate_cap_exception_count_by_symbol"] = {
                                        symbol: (quality.get("relative_rate_cap_assessment") or {}).get(
                                            "exceeds_documented_cap_count", 0
                                        )
                                        for symbol, quality in quality_by_symbol.items()
                                    }
                                    manifest["api_rate_cap_exceptions"] = [
                                        {"symbol": symbol, **row}
                                        for symbol, quality in quality_by_symbol.items()
                                        for row in (quality.get("relative_rate_cap_assessment") or {}).get(
                                            "exceeds_documented_cap_rows", []
                                        )
                                    ]
                                    if targeted:
                                        manifest["api_extrema"] = [
                                            extract_api_extrema(item) for item in api_records
                                        ]
                                        manifest["timestamp_semantics_assessment"] = timestamp_semantics_assessment()
                                        manifest["parameter_changelog_review"] = {
                                            "source_url": "https://support.kraken.com/ro/articles/13049711807636-derivatives-platform-parameters-changelog",
                                            "page_last_updated": "2026-10-01",
                                            "finding": (
                                                "The reviewed public changelog contains a PF_OGNUSD-specific maximum relative funding-rate change "
                                                "in 2023 and PI_XBTUSD/PI_ETHUSD margin-class entries in 2024; no PI_XBTUSD or PI_ETHUSD funding-cap "
                                                "change was found in the reviewed entries. This is not proof that no unpublished or omitted parameter "
                                                "change ever occurred."
                                            ),
                                        }
                                        manifest["delisting_reference"] = {
                                            "source_url": "https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings",
                                            "settlement_date": "2026-10-30",
                                            "inverse_btc_eth_settlement_time_utc": "16:00",
                                        }
                                        manifest["api_rate_cap_assessment"] = {
                                            item.get("symbol"): {
                                                field: {
                                                    extreme: {
                                                        "value": (item.get("extrema", {}).get(field, {}).get(extreme) or {}).get("value"),
                                                        "matches": [
                                                            row["cap_assessment"]
                                                            for row in (item.get("extrema", {}).get(field, {}).get(extreme) or {}).get("matches", [])
                                                        ],
                                                    }
                                                    for extreme in ("min", "max")
                                                }
                                                for field in ("fundingRate", "relativeFundingRate")
                                            }
                                            for item in manifest["api_extrema"]
                                        }
                                        manifest["api_rate_cap_extrema_exceptions"] = [
                                            {
                                                "symbol": item.get("symbol"),
                                                "field": field,
                                                "extreme": extreme,
                                                "value": row.get("value"),
                                                "timestamp": row.get("timestamp"),
                                                "cap_assessment": row.get("cap_assessment"),
                                            }
                                            for item in manifest["api_extrema"]
                                            for field in ("relativeFundingRate",)
                                            for extreme in ("min", "max")
                                            for row in (item.get("extrema", {}).get(field, {}).get(extreme) or {}).get("matches", [])
                                            if row.get("cap_assessment", {}).get("cap_status") == "EXCEEDS_DOCUMENTED_CAP"
                                        ]
                                    manifest["public_api_crosschecks"] = []
                                    for item in archive_summary["perpetual_csv_summaries"]:
                                        symbol = str(item.get("symbol") or "").upper()
                                        api_record = next((entry for entry in api_records if entry.get("symbol") == symbol), None)
                                        if api_record:
                                            manifest["public_api_crosschecks"].append(
                                                crosscheck_archive_api(item, api_record)
                                            )
                                            if targeted:
                                                item["residual_interval_anomalies"] = compare_archive_anomalies_to_api(
                                                    item.get("residual_interval_anomalies") or [],
                                                    api_record,
                                                )
                                        (item.get("data_summary") or {}).pop("_api_crosscheck_rows", None)
                                    manifest["public_api_responses"] = [
                                        {key: value for key, value in item.items() if key != "rates"}
                                        for item in api_records
                                    ]
                                    manifest["status"] = "downloaded_and_inspected"
                                    if targeted:
                                        found = set(archive_summary.get("target_symbols_found") or [])
                                        lifecycle_symbols = {
                                            str(item.get("symbol") or "").upper()
                                            for item in manifest.get("target_instrument_lifecycle", [])
                                        }
                                        api_ok = all(item.get("status") == 200 and item.get("rates") for item in api_records)
                                        api_quality_by_symbol = {
                                            item.get("symbol"): item
                                            for item in manifest["public_api_quality"]
                                        }
                                        api_integrity_ok = all(
                                            quality.get("invalid_row_count") == 0
                                            and quality.get("invalid_timestamp_count") == 0
                                            and quality.get("duplicate_timestamp_count") == 0
                                            and quality.get("out_of_order_timestamp_count") == 0
                                            and all(count == 0 for count in quality.get("null_counts", {}).values())
                                            and all(
                                                stats.get("invalid_count") == 0
                                                for stats in quality.get("rate_fields", {}).values()
                                            )
                                            for quality in api_quality_by_symbol.values()
                                        ) and set(api_quality_by_symbol) == set(TARGETED_SYMBOLS)
                                        anomaly_counts = {
                                            item.get("symbol"): len(item.get("residual_interval_anomalies") or [])
                                            for item in archive_summary["perpetual_csv_summaries"]
                                        }
                                        anomaly_distributions = {
                                            item.get("symbol"): dict(Counter(
                                                str(anomaly.get("actual_interval_hours"))
                                                for anomaly in item.get("residual_interval_anomalies") or []
                                            ))
                                            for item in archive_summary["perpetual_csv_summaries"]
                                        }
                                        expected_distribution = {"2.0": 5, "3.0": 1}
                                        anomaly_distribution_match = (
                                            set(anomaly_distributions) == set(TARGETED_SYMBOLS)
                                            and all(distribution == expected_distribution
                                                    for distribution in anomaly_distributions.values())
                                        )
                                        hash_ok = archive_summary.get("archive_sha256") == EXPECTED_ARCHIVE_SHA256
                                        manifest["targeted_acceptance_checks"] = {
                                            "all_four_exact_csvs_found": found == set(TARGETED_SYMBOLS),
                                            "all_four_instrument_lifecycle_records_found": lifecycle_symbols == set(TARGETED_SYMBOLS),
                                            "all_four_api_responses_nonempty": api_ok,
                                            "all_four_api_rows_pass_integrity": api_integrity_ok,
                                            "all_relative_rate_rows_cap_assessed": (
                                                set(api_quality_by_symbol) == set(TARGET_SYMBOLS)
                                                and all((quality.get("relative_rate_cap_assessment") or {}).get("rows_unassessed") == 0
                                                        for quality in api_quality_by_symbol.values())
                                            ),
                                            "relative_rate_cap_exception_count_by_symbol": manifest.get(
                                                "api_rate_cap_exception_count_by_symbol", {}
                                            ),
                                            "known_archive_size_matches": archive_path.stat().st_size == EXPECTED_ARCHIVE_SIZE_BYTES,
                                            "known_archive_sha256_matches": hash_ok,
                                            "archive_anomaly_counts_by_symbol": anomaly_counts,
                                            "archive_anomaly_distribution_by_symbol": anomaly_distributions,
                                            "expected_anomaly_count_per_symbol": 6,
                                            "expected_anomaly_distribution_per_symbol": expected_distribution,
                                            "anomaly_counts_match_expected": (
                                                set(anomaly_counts) == set(TARGETED_SYMBOLS)
                                                and all(count == 6 for count in anomaly_counts.values())
                                            ),
                                            "anomaly_distribution_matches_expected": anomaly_distribution_match,
                                            "funding_acceptance": "PROVISIONAL_NOT_ACCEPTED",
                                        }
                                        manifest["status"] = (
                                            "targeted_anomaly_audit_complete"
                                            if (
                                                found == set(TARGETED_SYMBOLS)
                                                and lifecycle_symbols == set(TARGETED_SYMBOLS)
                                                and api_ok
                                                and api_integrity_ok
                                                and manifest["targeted_acceptance_checks"]["all_relative_rate_rows_cap_assessed"]
                                                and hash_ok
                                                and archive_path.stat().st_size == EXPECTED_ARCHIVE_SIZE_BYTES
                                                and set(anomaly_counts) == set(TARGETED_SYMBOLS)
                                                and all(count == 6 for count in anomaly_counts.values())
                                                and anomaly_distribution_match
                                            )
                                            else "targeted_anomaly_audit_incomplete"
                                        )
                                    manifest["download_size_bytes"] = archive_path.stat().st_size
                                    manifest["download_sha256"] = sha256_file(archive_path)
                            except PlaywrightTimeout as exc:
                                manifest["status"] = "download_event_timeout"
                                manifest["download_error"] = f"{type(exc).__name__}: {str(exc)[:250]}"
                            except Exception as exc:
                                manifest["status"] = "download_or_inspection_error"
                                manifest["download_error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
                            finally:
                                manifest["raw_download_deleted_after_inspection"] = True
            browser.close()
    except Exception as exc:
        manifest["status"] = "probe_error"
        manifest["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"

    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["raw_download_uploaded"] = False
    manifest["raw_download_committed"] = False
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("export", "anomaly-audit", "api-cap-audit"), default="export")
    args = parser.parse_args()
    result = run_api_cap_audit(args.output_dir) if args.mode == "api-cap-audit" else run_probe(args.output_dir, mode=args.mode)
    print(json.dumps({
        "status": result.get("status"),
        "page_http_status": result.get("page_http_status"),
        "download_preflight": result.get("download_preflight"),
        "download_size_bytes": result.get("download_size_bytes"),
        "mode": result.get("mode"),
        "archive_member_count": (result.get("archive") or {}).get("archive_member_count"),
        "archive_hash_check": result.get("archive_hash_check"),
        "api_extrema": [
            {"symbol": item.get("symbol"), "extrema": item.get("extrema")}
            for item in result.get("api_extrema", [])
        ],
        "timestamp_semantics_assessment": result.get("timestamp_semantics_assessment"),
        "api_rate_cap_exception_count_by_symbol": result.get("api_rate_cap_exception_count_by_symbol"),
        "api_rate_cap_exceptions": result.get("api_rate_cap_exceptions"),
        "targeted_acceptance_checks": result.get("targeted_acceptance_checks"),
        "perpetual_csv_summaries": [
            {
                "member": item.get("member"),
                "symbol": item.get("symbol"),
                "inspection": item.get("inspection"),
                "row_count": (item.get("data_summary") or {}).get("row_count"),
                "first_timestamp": (item.get("data_summary") or {}).get("first_timestamp"),
                "last_timestamp": (item.get("data_summary") or {}).get("last_timestamp"),
            }
            for item in (result.get("archive") or {}).get("perpetual_csv_summaries", [])
        ],
        "error": result.get("error") or result.get("download_error"),
    }, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
