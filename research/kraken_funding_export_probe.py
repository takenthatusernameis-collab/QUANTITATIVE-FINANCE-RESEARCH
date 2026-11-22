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
    return {key: instrument.get(key) for key in keys if key in instrument}


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


def analyze_archive(path: Path, instruments: list[dict[str, Any]]) -> dict[str, Any]:
    specs_by_symbol = {
        norm_key(str(item.get("symbol", ""))): item
        for item in instruments if item.get("symbol")
    }
    summary: dict[str, Any] = {
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


def crosscheck_archive_api(archive_record: dict[str, Any],
                           api_record: dict[str, Any]) -> dict[str, Any]:
    summary = archive_record.get("data_summary") or {}
    archive_rows = summary.get("_api_crosscheck_rows") or summary.get("crosscheck_samples") or []
    api_rows = api_record.get("rates") or []
    api_by_time: dict[int, dict[str, Any]] = {}
    api_duplicate_count = 0
    for row in api_rows:
        stamp = parse_timestamp_ms(row.get("timestamp"))
        if stamp is not None:
            if stamp in api_by_time:
                api_duplicate_count += 1
            api_by_time[stamp] = row

    archive_by_time: dict[int, dict[str, Any]] = {}
    for row in archive_rows:
        stamp = row.get("timestamp_ms")
        if stamp is not None:
            archive_by_time[stamp] = row

    api_times = sorted(api_by_time)
    archive_times = sorted(archive_by_time)
    overlap_start = max(api_times[0], archive_times[0]) if api_times and archive_times else None
    overlap_end = min(api_times[-1], archive_times[-1]) if api_times and archive_times else None
    if overlap_start is not None and overlap_end is not None and overlap_start <= overlap_end:
        archive_overlap = {
            stamp: row for stamp, row in archive_by_time.items()
            if overlap_start <= stamp <= overlap_end
        }
        api_overlap = {
            stamp: row for stamp, row in api_by_time.items()
            if overlap_start <= stamp <= overlap_end
        }
    else:
        archive_overlap, api_overlap = {}, {}
    matched_times = sorted(set(archive_overlap) & set(api_overlap))
    archive_only = sorted(set(archive_overlap) - set(api_overlap))
    api_only = sorted(set(api_overlap) - set(archive_overlap))

    field_pairs = (
        ("absolute_rate", "fundingRate"),
        ("relative_rate", "relativeFundingRate"),
        ("fundingRate", "fundingRate"),
        ("relativeFundingRate", "relativeFundingRate"),
    )
    field_results: dict[str, Any] = {}
    archive_field_names = set()
    for row in archive_rows:
        archive_field_names.update((row.get("rates") or {}).keys())
    for archive_name, api_name in field_pairs:
        if archive_name not in archive_field_names:
            continue
        compared = 0
        mismatch = 0
        max_abs = 0.0
        for stamp in matched_times:
            archive_value = (archive_overlap[stamp].get("rates") or {}).get(archive_name)
            api_value = api_overlap[stamp].get(api_name)
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
        positions = sorted({0, len(matched_times) // 4, len(matched_times) // 2,
                            (3 * len(matched_times)) // 4, len(matched_times) - 1})
        for index in positions:
            stamp = matched_times[index]
            archive_row = archive_overlap[stamp]
            api_row = api_overlap[stamp]
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
                        "equal_with_tolerance": math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-12),
                    }
                except (KeyError, ValueError, TypeError):
                    fields[archive_name] = {"api_field": api_name, "comparison": "unavailable"}
            sample_comparisons.append({
                "timestamp": archive_row.get("timestamp"),
                "fields": fields,
            })

    overlap_denominator = max(len(archive_overlap), len(api_overlap))
    return {
        "symbol": archive_record.get("symbol"),
        "api_status": api_record.get("status"),
        "api_result": api_record.get("result"),
        "api_rate_count": api_record.get("rate_count"),
        "api_first_timestamp": api_record.get("first_timestamp"),
        "api_last_timestamp": api_record.get("last_timestamp"),
        "archive_first_timestamp": summary.get("first_timestamp"),
        "archive_last_timestamp": summary.get("last_timestamp"),
        "overlap_start_utc": datetime.fromtimestamp(overlap_start / 1000, tz=timezone.utc).isoformat() if overlap_start is not None and overlap_start <= overlap_end else None,
        "overlap_end_utc": datetime.fromtimestamp(overlap_end / 1000, tz=timezone.utc).isoformat() if overlap_start is not None and overlap_start <= overlap_end else None,
        "archive_rows_in_overlap": len(archive_overlap),
        "api_rows_in_overlap": len(api_overlap),
        "matched_timestamps": len(matched_times),
        "archive_only_timestamps": len(archive_only),
        "api_only_timestamps": len(api_only),
        "timestamp_sets_equal": bool(archive_overlap) and not archive_only and not api_only,
        "timestamp_match_rate_against_larger_overlap_set": (
            len(matched_times) / overlap_denominator if overlap_denominator else None
        ),
        "api_duplicate_timestamp_count": api_duplicate_count,
        "rate_field_comparisons": field_results,
        "representative_overlap_samples": sample_comparisons,
        "api_history_completeness_claim": "not_established_by_endpoint_response",
    }


def run_probe(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "probe": "kraken_official_historical_funding_export",
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
                                    archive_summary = analyze_archive(archive_path, instruments["instruments"])
                                    manifest["archive"] = archive_summary
                                    api_symbols: list[str] = []
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
                                    manifest["public_api_crosschecks"] = []
                                    for item in archive_summary["perpetual_csv_summaries"]:
                                        symbol = str(item.get("symbol") or "").upper()
                                        api_record = next((entry for entry in api_records if entry.get("symbol") == symbol), None)
                                        if api_record:
                                            manifest["public_api_crosschecks"].append(
                                                crosscheck_archive_api(item, api_record)
                                            )
                                        (item.get("data_summary") or {}).pop("_api_crosscheck_rows", None)
                                    manifest["public_api_responses"] = [
                                        {key: value for key, value in item.items() if key != "rates"}
                                        for item in api_records
                                    ]
                                    manifest["status"] = "downloaded_and_inspected"
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
    args = parser.parse_args()
    result = run_probe(args.output_dir)
    print(json.dumps({
        "status": result.get("status"),
        "page_http_status": result.get("page_http_status"),
        "download_preflight": result.get("download_preflight"),
        "download_size_bytes": result.get("download_size_bytes"),
        "archive_member_count": (result.get("archive") or {}).get("archive_member_count"),
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
