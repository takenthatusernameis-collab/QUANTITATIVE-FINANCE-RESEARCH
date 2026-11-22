#!/usr/bin/env python3
"""Read-only, bounded MEXC funding-history pagination pilot.

This is an independent provider feasibility check, not Binance evidence and not a
backtest acceptance gate. Raw API pages remain in runner-only cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://contract.mexc.com/api/v1/contract/funding_rate/history"
DOCS_URL = "https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history"
ALLOWED_SYMBOLS = ("BTC_USDT", "ETH_USDT")
MAX_PAGE_SIZE = 1000
MAX_PAGES = 200
MAX_RECORDS = 200_000
TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3


def utc_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def _positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _finite_rate(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("fundingRate must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError("fundingRate must be finite")
    return parsed


def parse_page_payload(
    payload: dict, symbol: str, page_num: int, requested_page_size: int
) -> tuple[dict, list[dict]]:
    if payload.get("success") is not True or payload.get("code") not in (0, "0"):
        raise ValueError(f"MEXC API rejected request: {payload.get('code')} {payload.get('message')}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("data must be an object")
    page_size = _positive_int(data.get("pageSize"), "pageSize")
    if page_size != requested_page_size:
        raise ValueError(f"pageSize mismatch: expected {requested_page_size}, received {page_size}")
    total_count = int(data.get("totalCount", -1))
    total_pages = int(data.get("totalPage", -1))
    current_page = int(data.get("currentPage", -1))
    if total_count < 0 or total_pages < 0 or current_page != page_num:
        raise ValueError("invalid or inconsistent pagination metadata")
    expected_pages = math.ceil(total_count / page_size) if total_count else 0
    if total_pages != expected_pages:
        raise ValueError(f"totalPage mismatch: expected {expected_pages}, received {total_pages}")
    result_list = data.get("resultList")
    if not isinstance(result_list, list):
        raise ValueError("resultList must be a list")
    expected_rows = min(page_size, max(0, total_count - (page_num - 1) * page_size))
    if len(result_list) != expected_rows:
        raise ValueError(f"page row count mismatch: expected {expected_rows}, received {len(result_list)}")
    rows = []
    for index, item in enumerate(result_list):
        if not isinstance(item, dict):
            raise ValueError(f"resultList[{index}] must be an object")
        row_symbol = item.get("symbol")
        if row_symbol != symbol:
            raise ValueError(f"symbol mismatch: expected {symbol}, received {row_symbol}")
        rate = _finite_rate(item.get("fundingRate"))
        settle_time = _positive_int(item.get("settleTime"), "settleTime")
        cycle = _positive_int(item.get("collectCycle"), "collectCycle")
        rows.append({"symbol": symbol, "funding_rate": rate, "settle_time_ms": settle_time,
                    "collect_cycle_hours": cycle})
    meta = {"page_size": page_size, "total_count": total_count,
             "total_pages": total_pages, "current_page": current_page}
    return meta, rows


def request_page(symbol: str, page_num: int, page_size: int) -> tuple[dict, bytes]:
    query = urlencode({"symbol": symbol, "page_num": page_num, "page_size": page_size})
    request = Request(API_URL + "?" + query, headers={"User-Agent": "qfr-mexc-funding-probe/1.0"})
    last_error = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError("response JSON must be an object")
                return payload, raw
        except HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code != 429 and exc.code < 500:
                raise RuntimeError(last_error) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
        if attempt + 1 < RETRY_ATTEMPTS:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed after {RETRY_ATTEMPTS} attempts: {last_error}")


def fetch_symbol(
    symbol: str,
    page_size: int = MAX_PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    max_records: int = MAX_RECORDS,
    page_fetcher=request_page,
    sleeper=time.sleep,
    cache_dir: Path | None = None,
) -> dict:
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError(f"unsupported symbol: {symbol}")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    if max_pages < 1 or max_records < 1:
        raise ValueError("max_pages and max_records must be positive")

    first_payload, first_raw = page_fetcher(symbol, 1, page_size)
    first_meta, first_rows = parse_page_payload(first_payload, symbol, 1, page_size)
    total_count = first_meta["total_count"]
    total_pages = first_meta["total_pages"]
    if total_pages > max_pages or total_count > max_records:
        raise ValueError(f"bounded probe exceeded limits: {total_pages} pages, {total_count} rows")
    rows = list(first_rows)
    page_hashes = [hashlib.sha256(first_raw).hexdigest()]
    page_metadata = [{"page": 1, "rows": len(first_rows), "sha256": page_hashes[0]}]
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{symbol}_page_1.json").write_bytes(first_raw)

    for page_num in range(2, total_pages + 1):
        sleeper(0.1)
        payload, raw = page_fetcher(symbol, page_num, page_size)
        meta, page_rows = parse_page_payload(payload, symbol, page_num, page_size)
        for key in ("page_size", "total_count", "total_pages"):
            if meta[key] != first_meta[key]:
                raise ValueError(f"pagination metadata changed across pages: {key}")
        rows.extend(page_rows)
        digest = hashlib.sha256(raw).hexdigest()
        page_hashes.append(digest)
        page_metadata.append({"page": page_num, "rows": len(page_rows), "sha256": digest})
        if cache_dir:
            (cache_dir / f"{symbol}_page_{page_num}.json").write_bytes(raw)

    times = [row["settle_time_ms"] for row in rows]
    duplicates = len(times) - len(set(times))
    if len(rows) != total_count or len(page_hashes) != total_pages:
        raise ValueError(f"pagination incomplete: fetched {len(rows)}/{total_count} rows across {len(page_hashes)}/{total_pages} pages")
    if duplicates:
        raise ValueError(f"duplicate settlement timestamps: {duplicates}")
    rows.sort(key=lambda item: item["settle_time_ms"])
    intervals = [(b["settle_time_ms"] - a["settle_time_ms"]) / 3_600_000
                for a, b in zip(rows, rows[1:])]
    cycles = Counter(row["collect_cycle_hours"] for row in rows)
    gap_hours = Counter(round(value, 6) for value in intervals)
    return {
        "provider": "MEXC",
        "api_endpoint": API_URL,
        "documentation": DOCS_URL,
        "symbol": symbol,
        "status": "OBSERVED_COMPLETE",
        "page_size_requested": page_size,
        "total_count_reported": total_count,
        "total_pages_reported": total_pages,
        "pages_fetched": len(page_hashes),
        "records_fetched": len(rows),
        "pagination_complete": True,
        "duplicate_settlement_timestamps": duplicates,
        "earliest_settlement_utc": utc_from_ms(rows[0]["settle_time_ms"]) if rows else None,
        "latest_settlement_utc": utc_from_ms(rows[-1]["settle_time_ms"]) if rows else None,
        "collect_cycle_hours_distribution": dict(sorted(cycles.items())),
        "observed_timestamp_gap_hours_distribution": dict(sorted(gap_hours.items())),
        "observed_gap_hours_median": statistics.median(intervals) if intervals else None,
        "observed_gap_hours_min": min(intervals) if intervals else None,
        "observed_gap_hours_max": max(intervals) if intervals else None,
        "page_sha256": page_hashes,
        "page_metadata": page_metadata,
        "raw_response_cache_only": True,
        "historical_retention_officially_documented": False,
        "accepted_for_full_history_backtest": False,
        "limitations": [
            "Pagination completion verifies only the API's reported population, not its historical retention completeness.",
            "No official per-symbol inception, retention, delisting or symbol-incarnation coverage statement was established.",
            "This is an independent MEXC provider pilot and does not validate Binance funding data or the original Binance experiment."
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="BTC_USDT,ETH_USDT")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--page-size", type=int, default=MAX_PAGE_SIZE)
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--max-records", type=int, default=MAX_RECORDS)
    args = parser.parse_args(argv)

    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    output_dir = Path(args.output_dir)
    cache_dir = Path(args.cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for symbol in symbols:
        try:
            result = fetch_symbol(symbol, args.page_size, args.max_pages, args.max_records,
                                 cache_dir=cache_dir)
        except Exception as exc:
            result = {"provider": "MEXC", "symbol": symbol, "status": "PROBE_FAILED",
                      "error": str(exc), "accepted_for_full_history_backtest": False,
                      "raw_response_cache_only": True}
        results.append(result)
        (output_dir / f"{symbol}_manifest.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )

    success = all(item.get("status") == "OBSERVED_COMPLETE" for item in results)
    summary = {
        "provider": "MEXC",
        "probe_type": "public funding-history pagination and coverage feasibility",
        "symbols_requested": symbols,
        "symbols_observed_complete": [item["symbol"] for item in results if item.get("status") == "OBSERVED_COMPLETE"],
        "status": "OBSERVED_COMPLETE" if success else "PROBE_FAILED",
        "historical_retention_officially_documented": False,
        "accepted_for_full_history_backtest": False,
        "research_decision": "Provider population was enumerated only as reported by MEXC; no retention/completeness guarantee or contract-incarnation mapping was established. This independent provider is not Binance evidence.",
        "manifest_files": [f"{item['symbol']}_manifest.json" for item in results],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
