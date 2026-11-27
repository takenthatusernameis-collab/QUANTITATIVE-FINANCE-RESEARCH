#!/usr/bin/env python3
"""Read-only feasibility preflight for MEXC intraday funding dispersion -> BTC perpetual RV."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import urllib.parse
from pathlib import Path

import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01"
SYMBOL = "BTC_USDT"
START_DATE = dt.date(2025, 6, 15)
END_DATE = dt.date(2026, 11, 26)
KLINE_START = dt.datetime(2025, 6, 7, tzinfo=dt.timezone.utc)
KLINE_END = dt.datetime(2026, 11, 27, 17, tzinfo=dt.timezone.utc)
VALIDATION_START = dt.date(2025, 11, 1)
TEST_START = dt.date(2026, 1, 1)
API_BASES = ("https://api.mexc.com", "https://contract.mexc.com")
CONTRACT_PATH = "/api/v1/contract/detail/country"
FUNDING_PATH = "/api/v1/contract/funding_rate/history"
KLINE_PATH = f"/api/v1/contract/kline/{SYMBOL}"
PAGE_SIZE, MAX_PAGES = 1000, 10
SEGMENT_HOURS = 1800
MIN_FUNDING_ROWS, MIN_COMPLETE_DAYS = 1200, 400
MAX_INCOMPLETE_SHARE = 0.05
MIN_KLINE_COVERAGE, MAX_MISSING_RUN = 0.995, 2
MIN_EVENTS, MIN_WARMUP, MIN_VALIDATION, MIN_TEST = 400, 120, 30, 100

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "mexc-funding-dispersion-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def payload(body: bytes, label: str) -> dict:
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}: invalid UTF-8 JSON") from exc
    if not isinstance(data, dict) or data.get("success") is not True or str(data.get("code")) != "0":
        raise ValueError(f"{label}: expected success=true and code=0")
    return data


def fetch_first(path: str, params: dict, timeout: int) -> tuple[bytes, str, str, list[dict]]:
    attempts = []
    query = urllib.parse.urlencode(params)
    for index, host in enumerate(API_BASES):
        url = f"{host}{path}?{query}"
        try:
            body = base.fetch_bytes(url, timeout=timeout)
            if not body:
                raise RuntimeError("empty response")
            return body, host, url, attempts
        except Exception as exc:
            message = str(exc)
            attempts.append({"host": host, "url": url, "error": f"{type(exc).__name__}: {message}"})
            if any(code in message for code in ("HTTP 401", "HTTP 403", "HTTP 429", "HTTP 451")):
                break
            if index == len(API_BASES) - 1:
                break
    raise RuntimeError(f"MEXC endpoint failed on preregistered host order: {json.dumps(attempts, sort_keys=True)}")


def fetch_host(host: str, path: str, params: dict, timeout: int) -> tuple[bytes, str]:
    url = f"{host}{path}?{urllib.parse.urlencode(params)}"
    body = base.fetch_bytes(url, timeout=timeout)
    if not body:
        raise RuntimeError(f"empty response: {url}")
    return body, url


def parse_contract(body: bytes) -> dict:
    data = payload(body, "contract detail").get("data")
    candidates = data if isinstance(data, list) else (
        [data] if isinstance(data, dict) and data.get("symbol") else
        [v for v in data.values() if isinstance(v, dict)] if isinstance(data, dict) else []
    )
    row = next((v for v in candidates if v.get("symbol") == SYMBOL), None)
    if row is None:
        raise ValueError(f"contract detail lacks exact {SYMBOL}")
    try:
        future_type, state = int(row["futureType"]), int(row["state"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("contract detail lacks numeric futureType/state") from exc
    if (future_type, state) != (1, 0):
        raise ValueError(f"contract is not an enabled perpetual: futureType={future_type}, state={state}")
    if (row.get("baseCoin"), row.get("quoteCoin"), row.get("settleCoin")) != ("BTC", "USDT", "USDT"):
        raise ValueError("contract base/quote/settlement does not match BTC_USDT USDT perpetual")
    return {
        "symbol": SYMBOL, "future_type": future_type, "state": state,
        "base_coin": "BTC", "quote_coin": "USDT", "settle_coin": "USDT",
        "contract_size": str(row.get("contractSize")),
    }


def parse_funding_page(body: bytes, expected_page: int) -> tuple[dict, list[dict]]:
    data = payload(body, f"funding page {expected_page}").get("data")
    if not isinstance(data, dict):
        raise ValueError("funding data is not an object")
    try:
        page, total, pages, size = (int(data[k]) for k in ("currentPage", "totalCount", "totalPage", "pageSize"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("funding pagination metadata is invalid") from exc
    rows = data.get("resultList")
    if page != expected_page or not isinstance(rows, list) or not rows:
        raise ValueError(f"funding page progression invalid: expected {expected_page}, received {page}")
    if total < 1 or pages < 1 or pages > MAX_PAGES or size != PAGE_SIZE:
        raise ValueError("funding history exceeds preregistered pagination bounds")
    if pages != math.ceil(total / size) or len(rows) > size:
        raise ValueError("funding totalCount/totalPage/pageSize are inconsistent")
    parsed = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("symbol") != SYMBOL:
            raise ValueError(f"funding row {index} has wrong symbol/shape")
        try:
            cycle, stamp_ms = int(row["collectCycle"]), int(row["settleTime"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"funding row {index} lacks cycle/settleTime") from exc
        raw_rate = str(row.get("fundingRate"))
        rate = base.parse_float(raw_rate)
        if cycle != 8 or rate is None or stamp_ms < 1_500_000_000_000:
            raise ValueError(f"funding row {index} violates 8h schema")
        stamp = dt.datetime.fromtimestamp(stamp_ms / 1000, dt.timezone.utc)
        if stamp.minute or stamp.second or stamp.microsecond or stamp.hour not in (0, 8, 16):
            raise ValueError(f"funding settlement not aligned to 00/08/16 UTC: {stamp.isoformat()}")
        parsed.append({
            "symbol": SYMBOL, "rate": float(rate), "rate_raw": raw_rate,
            "settle_ms": stamp_ms, "settle_utc": stamp.isoformat(),
            "date": stamp.date(), "hour": stamp.hour, "cycle": cycle,
        })
    return {"page": page, "total": total, "pages": pages, "size": size}, parsed


def fetch_funding() -> tuple[list[dict], list[dict], str, list[dict]]:
    params = {"symbol": SYMBOL, "page_num": 1, "page_size": PAGE_SIZE}
    body, host, url, attempts = fetch_first(FUNDING_PATH, params, 25)
    meta, rows = parse_funding_page(body, 1)
    pages = [{"page": 1, "url": url, "sha256": digest(body), "rows": len(rows)}]
    for page in range(2, meta["pages"] + 1):
        body, page_url = fetch_host(host, FUNDING_PATH, {"symbol": SYMBOL, "page_num": page, "page_size": PAGE_SIZE}, 25)
        next_meta, next_rows = parse_funding_page(body, page)
        if (next_meta["total"], next_meta["pages"], next_meta["size"]) != (meta["total"], meta["pages"], meta["size"]):
            raise ValueError("funding pagination metadata changed mid-fetch")
        rows.extend(next_rows)
        pages.append({"page": page, "url": page_url, "sha256": digest(body), "rows": len(next_rows)})
    stamps = [r["settle_ms"] for r in rows]
    if len(stamps) != len(set(stamps)):
        raise ValueError("duplicate funding settlement timestamps")
    rows = sorted((r for r in rows if START_DATE <= r["date"] <= END_DATE), key=lambda r: r["settle_ms"])
    return rows, pages, host, attempts


def parse_klines(body: bytes) -> list[tuple[int, float, str]]:
    data = payload(body, "hourly klines").get("data")
    if not isinstance(data, dict):
        raise ValueError("kline data is not an object")
    times, closes = data.get("time"), data.get("close")
    if not isinstance(times, list) or not isinstance(closes, list) or len(times) != len(closes):
        raise ValueError("kline time/close arrays are missing or misaligned")
    if len(times) > 2000:
        raise ValueError("kline response exceeds documented 2,000-point cap")
    result = []
    for index, (raw_time, raw_close) in enumerate(zip(times, closes)):
        try:
            timestamp = int(raw_time)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"kline row {index} has invalid time") from exc
        raw = str(raw_close)
        close = base.parse_float(raw)
        if timestamp < 1_000_000_000 or timestamp > 10_000_000_000 or timestamp % 3600:
            raise ValueError(f"kline row {index} is not an hour-aligned Unix-second timestamp")
        if close is None or close <= 0:
            raise ValueError(f"kline row {index} has invalid close")
        result.append((timestamp, float(close), raw))
    return result


def fetch_klines() -> tuple[dict[int, float], dict[int, str], list[dict], str, list[dict]]:
    start, end = int(KLINE_START.timestamp()), int(KLINE_END.timestamp())
    segment_seconds = SEGMENT_HOURS * 3600
    cursor = start
    closes, raw_closes, segments = {}, {}, []
    host, attempts = None, []
    while cursor < end:
        segment_end = min(cursor + segment_seconds, end)
        params = {"interval": "Min60", "start": cursor, "end": segment_end}
        if host is None:
            body, host, url, attempts = fetch_first(KLINE_PATH, params, 30)
        else:
            body, url = fetch_host(host, KLINE_PATH, params, 30)
        rows = [r for r in parse_klines(body) if cursor <= r[0] < segment_end]
        if not rows:
            raise ValueError(f"empty hourly kline segment {cursor}-{segment_end}")
        for timestamp, close, raw in rows:
            if timestamp in closes:
                raise ValueError(f"duplicate hourly kline timestamp {timestamp}")
            closes[timestamp], raw_closes[timestamp] = close, raw
        segments.append({
            "start": dt.datetime.fromtimestamp(cursor, dt.timezone.utc).isoformat(),
            "end_exclusive": dt.datetime.fromtimestamp(segment_end, dt.timezone.utc).isoformat(),
            "url": url, "response_sha256": digest(body), "accepted_bars": len(rows),
        })
        cursor = segment_end
    return closes, raw_closes, segments, host, attempts


def funding_coverage(rows: list[dict]) -> tuple[dict, list[dt.date]]:
    if len(rows) < MIN_FUNDING_ROWS:
        raise ValueError(f"funding rows {len(rows)} below minimum {MIN_FUNDING_ROWS}")
    grouped: dict[dt.date, set[int]] = {}
    for row in rows:
        grouped.setdefault(row["date"], set())
        if row["hour"] in grouped[row["date"]]:
            raise ValueError(f"duplicate funding hour on {row['date']}")
        grouped[row["date"]].add(row["hour"])
    total_days = (END_DATE - START_DATE).days + 1
    complete = sorted(d for d, hours in grouped.items() if hours == {0, 8, 16})
    incomplete = total_days - len(complete)
    share = incomplete / total_days
    if len(complete) < MIN_COMPLETE_DAYS or share > MAX_INCOMPLETE_SHARE:
        raise ValueError(f"funding coverage gate failed: complete={len(complete)}, incomplete_share={share:.4%}")
    if max(complete) < END_DATE - dt.timedelta(days=2):
        raise ValueError(f"latest complete funding date is stale: {max(complete)}")
    return {
        "sample_start": START_DATE.isoformat(), "sample_end": END_DATE.isoformat(),
        "settlements": len(rows), "complete_days": len(complete),
        "incomplete_days": incomplete, "incomplete_share": share,
        "first_settlement": min(r["settle_utc"] for r in rows),
        "last_settlement": max(r["settle_utc"] for r in rows),
        "latest_complete_date": max(complete).isoformat(),
    }, complete


def kline_coverage(closes: dict[int, float]) -> dict:
    start, end = int(KLINE_START.timestamp()), int(KLINE_END.timestamp())
    expected = range(start, end, 3600)
    missing, run, longest = 0, 0, 0
    for timestamp in expected:
        if timestamp not in closes:
            missing += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    expected_n = len(range(start, end, 3600))
    coverage = len(closes) / expected_n
    if coverage < MIN_KLINE_COVERAGE or longest > MAX_MISSING_RUN or max(closes, default=0) < end - 3600:
        raise ValueError(f"hourly coverage gate failed: coverage={coverage:.4%}, missing={missing}, longest_run={longest}")
    return {
        "start": KLINE_START.isoformat(), "end_exclusive": KLINE_END.isoformat(),
        "expected_hours": expected_n, "returned_hours": len(closes),
        "missing_hours": missing, "coverage": coverage,
        "longest_missing_run_hours": longest,
        "first_bar": dt.datetime.fromtimestamp(min(closes), dt.timezone.utc).isoformat(),
        "last_bar_start": dt.datetime.fromtimestamp(max(closes), dt.timezone.utc).isoformat(),
    }


def event_coverage(dates: list[dt.date], closes: dict[int, float]) -> dict:
    complete = []
    for date in dates:
        signal = int(dt.datetime.combine(date, dt.time(17), tzinfo=dt.timezone.utc).timestamp())
        required = range(signal - 169 * 3600, signal + 24 * 3600, 3600)
        if all(t in closes for t in required):
            complete.append(date)
    warmup = sum(d < VALIDATION_START for d in complete)
    validation = sum(VALIDATION_START <= d < TEST_START for d in complete)
    test = sum(d >= TEST_START for d in complete)
    result = {
        "complete_event_windows": len(complete),
        "first_complete": min(complete).isoformat() if complete else None,
        "last_complete": max(complete).isoformat() if complete else None,
        "warmup_events": warmup, "validation_events_before_model_warmup": validation,
        "test_events_before_model_warmup": test,
    }
    if len(complete) < MIN_EVENTS or warmup < MIN_WARMUP or validation < MIN_VALIDATION or test < MIN_TEST:
        raise ValueError(f"event coverage gate failed: {result}")
    return result


def canonical_hash(rows: list[dict], keys: tuple[str, ...]) -> str:
    serial = [{key: row[key] for key in keys} for row in rows]
    return digest(json.dumps(serial, sort_keys=True, separators=(",", ":")).encode())


def run_preflight() -> dict:
    result = {
        "hypothesis_id": HYPOTHESIS_ID, "status": "FAIL",
        "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID,
        "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "completed_backtest": False, "model_fit_performed": False,
        "raw_observations_committed": False, "api_host_order": list(API_BASES),
    }
    try:
        contract_body, contract_host, contract_url, contract_attempts = fetch_first(CONTRACT_PATH, {"symbol": SYMBOL}, 20)
        contract = parse_contract(contract_body)
        funding, funding_pages, funding_host, funding_attempts = fetch_funding()
        funding_summary, complete_dates = funding_coverage(funding)
        closes, raw_closes, kline_segments, kline_host, kline_attempts = fetch_klines()
        kline_summary = kline_coverage(closes)
        events = event_coverage(complete_dates, closes)
        result.update({
            "status": "PASS", "contract": contract,
            "funding_coverage": funding_summary, "kline_coverage": kline_summary,
            "event_coverage": events,
            "provenance": {
                "contract": {"host": contract_host, "url": contract_url, "sha256": digest(contract_body), "route_attempts": contract_attempts},
                "funding": {
                    "host": funding_host, "pages": funding_pages, "route_attempts": funding_attempts,
                    "canonical_sha256": canonical_hash(funding, ("symbol", "settle_ms", "rate_raw", "cycle")),
                },
                "hourly_klines": {
                    "host": kline_host, "segments": kline_segments, "route_attempts": kline_attempts,
                    "canonical_sha256": digest(json.dumps(
                        [{"time": t, "close": raw_closes[t]} for t in sorted(raw_closes)],
                        sort_keys=True, separators=(",", ":")
                    ).encode()),
                },
            },
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> None:
    result = run_preflight()
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "preflight.json"
    report_path = SESSION_DIR / f"{STAMP}_session-mexc-funding-dispersion-source-preflight-{RUN_ID}.md"
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    result["report_path"] = str(report_path.relative_to(ROOT))
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        f"# MEXC funding-dispersion source preflight — {NOW.isoformat()}",
        "", f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result['status']}",
        "- **Model fit/backtest:** NOT RUN", f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Source commit:** {SOURCE_SHA}", "",
        "## Contract", json.dumps(result.get("contract", {}), indent=2, sort_keys=True), "",
        "## Funding coverage", json.dumps(result.get("funding_coverage", {}), indent=2, sort_keys=True), "",
        "## Hourly kline coverage", json.dumps(result.get("kline_coverage", {}), indent=2, sort_keys=True), "",
        "## Event coverage", json.dumps(result.get("event_coverage", {}), indent=2, sort_keys=True), "",
        "## Provenance", json.dumps(result.get("provenance", {}), indent=2, sort_keys=True), "",
        "## Error", str(result.get("error") or "None"), "",
        "No raw observations, correlations, model fits, forecast metrics or performance results were generated.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
