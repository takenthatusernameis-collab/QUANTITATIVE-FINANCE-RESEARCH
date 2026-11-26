#!/usr/bin/env python3
"""Read-only source feasibility check for Bitcoin Wikipedia attention data."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HYPOTHESIS_ID = "QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01"
PROJECT = "en.wikipedia"
PROJECT_PATH = "en.wikipedia.org"
ARTICLE = "Bitcoin"
ACCESS = "all-access"
AGENT = "user"
GRANULARITY = "daily"
SAMPLE_START = dt.date(2017, 8, 17)
SAMPLE_END = dt.date(2026, 11, 18)
CHUNK_DAYS = 90
MIN_NONZERO_ROWS = 3000
MAX_CONSECUTIVE_OMITTED_DAYS = 1
PAGEVIEWS_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
BINANCE_EXCHANGE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT"
USER_AGENT = "QFR-Research/1.0 (+https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
NOW = dt.datetime.now(dt.timezone.utc)


def iter_date_chunks(start: dt.date, end: dt.date, chunk_days: int = CHUNK_DAYS):
    """Yield non-overlapping inclusive date windows covering [start, end]."""
    if start > end:
        raise ValueError("start date must not be after end date")
    if chunk_days < 1:
        raise ValueError("chunk_days must be positive")
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + dt.timedelta(days=chunk_days - 1))
        yield cursor, chunk_end
        cursor = chunk_end + dt.timedelta(days=1)


def build_pageviews_url(start: dt.date, end: dt.date) -> str:
    parts = [
        PAGEVIEWS_BASE,
        urllib.parse.quote(PROJECT_PATH, safe="."),
        ACCESS,
        AGENT,
        urllib.parse.quote(ARTICLE, safe=""),
        GRANULARITY,
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
    ]
    return "/".join(parts)


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last_error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError(f"HTTP {response.status} or empty response for {url}")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable HTTP {exc.code} for {url}") from exc
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2.0
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            delay = 2.0
        if attempt == 0:
            time.sleep(delay)
    raise RuntimeError(f"Request failed after two bounded attempts: {url}: {last_error}")


def parse_pageviews(body: bytes, expected_start: dt.date, expected_end: dt.date) -> dict[dt.date, int]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Wikimedia response is not valid UTF-8 JSON: {exc}") from exc
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError("Wikimedia response lacks an items array")
    if not items:
        raise ValueError(f"Wikimedia returned no pageview records for {expected_start}..{expected_end}")

    values: dict[dt.date, int] = {}
    for index, row in enumerate(items):
        if not isinstance(row, dict):
            raise ValueError(f"Wikimedia row {index} is not an object")
        expected_fields = {
            "project": PROJECT,
            "article": ARTICLE,
            "granularity": GRANULARITY,
            "access": ACCESS,
            "agent": AGENT,
        }
        for field, expected in expected_fields.items():
            if row.get(field) != expected:
                raise ValueError(f"Wikimedia row {index} has unexpected {field}: {row.get(field)!r}")
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, str) or len(timestamp) != 10 or not timestamp.endswith("00"):
            raise ValueError(f"Wikimedia row {index} has invalid UTC daily timestamp: {timestamp!r}")
        try:
            day = dt.datetime.strptime(timestamp, "%Y%m%d%H").date()
        except ValueError as exc:
            raise ValueError(f"Wikimedia row {index} has malformed timestamp: {timestamp!r}") from exc
        if not expected_start <= day <= expected_end:
            raise ValueError(f"Wikimedia row {index} is outside requested date window: {day}")
        views = row.get("views")
        if isinstance(views, bool) or not isinstance(views, int) or views < 0:
            raise ValueError(f"Wikimedia row {index} has invalid views count: {views!r}")
        if day in values:
            raise ValueError(f"Duplicate Wikimedia UTC date: {day}")
        values[day] = views
    return dict(sorted(values.items()))


def validate_pageview_coverage(
    values: dict[dt.date, int],
    start: dt.date = SAMPLE_START,
    end: dt.date = SAMPLE_END,
) -> dict:
    if not values:
        raise ValueError("No Wikimedia pageview observations in frozen sample")
    dates = sorted(values)
    expected_days = (end - start).days + 1
    if dates[0] > start + dt.timedelta(days=MAX_CONSECUTIVE_OMITTED_DAYS):
        raise ValueError(f"Wikimedia coverage starts too late: {dates[0]} after {start}")
    if dates[-1] < end - dt.timedelta(days=MAX_CONSECUTIVE_OMITTED_DAYS):
        raise ValueError(f"Wikimedia coverage ends too early: {dates[-1]} before {end}")

    calendar = set(start + dt.timedelta(days=i) for i in range(expected_days))
    missing = sorted(calendar.difference(values))
    max_missing_run = 0
    current_run = 0
    for day in sorted(calendar):
        if day in missing:
            current_run += 1
            max_missing_run = max(max_missing_run, current_run)
        else:
            current_run = 0
    if max_missing_run > MAX_CONSECUTIVE_OMITTED_DAYS:
        raise ValueError(
            f"Wikimedia omitted {max_missing_run} consecutive dates; only a single omitted zero-view day is allowed"
        )
    if any(day < start or day > end for day in values):
        raise ValueError("Wikimedia observations extend outside the frozen sample")
    if len(values) < MIN_NONZERO_ROWS:
        raise ValueError(f"Insufficient nonzero Wikimedia pageview rows: {len(values)} < {MIN_NONZERO_ROWS}")

    return {
        "expected_calendar_days": expected_days,
        "observed_nonzero_rows": len(values),
        "documented_zero_view_days_reconstructed": len(missing),
        "first_observed_date": dates[0].isoformat(),
        "last_observed_date": dates[-1].isoformat(),
        "sample_start": start.isoformat(),
        "sample_end": end.isoformat(),
        "maximum_consecutive_omitted_days": max_missing_run,
        "minimum_views": min(values.values()),
        "maximum_views": max(values.values()),
    }


def validate_binance_exchange_info(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Binance exchangeInfo is not valid JSON: {exc}") from exc
    symbols = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(symbols, list) or len(symbols) != 1 or not isinstance(symbols[0], dict):
        raise ValueError("Binance exchangeInfo did not return exactly one BTCUSDT symbol")
    symbol = symbols[0]
    if (symbol.get("symbol"), symbol.get("status"), symbol.get("baseAsset"), symbol.get("quoteAsset")) != (
        "BTCUSDT", "TRADING", "BTC", "USDT"
    ):
        raise ValueError(f"Binance BTCUSDT is not the expected active Spot market: {symbol}")
    if symbol.get("isSpotTradingAllowed") is False:
        raise ValueError("Binance BTCUSDT does not allow Spot trading")
    return {
        "symbol": "BTCUSDT",
        "status": symbol.get("status"),
        "base_asset": symbol.get("baseAsset"),
        "quote_asset": symbol.get("quoteAsset"),
        "spot_trading_allowed": symbol.get("isSpotTradingAllowed"),
    }


def run_preflight() -> dict:
    all_values: dict[dt.date, int] = {}
    chunk_records = []
    for chunk_index, (chunk_start, chunk_end) in enumerate(iter_date_chunks(SAMPLE_START, SAMPLE_END), start=1):
        url = build_pageviews_url(chunk_start, chunk_end)
        body = fetch_bytes(url, timeout=30)
        parsed = parse_pageviews(body, chunk_start, chunk_end)
        overlap = set(all_values).intersection(parsed)
        if overlap:
            raise ValueError(f"Overlapping Wikimedia chunk dates: {sorted(overlap)[:3]}")
        all_values.update(parsed)
        chunk_records.append({
            "chunk": chunk_index,
            "start": chunk_start.isoformat(),
            "end": chunk_end.isoformat(),
            "observed_rows": len(parsed),
            "response_sha256": hashlib.sha256(body).hexdigest(),
        })
        if chunk_end < SAMPLE_END:
            time.sleep(0.7)

    coverage = validate_pageview_coverage(all_values)
    combined_hash = hashlib.sha256(
        "\n".join(record["response_sha256"] for record in chunk_records).encode("ascii")
    ).hexdigest()
    binance_body = fetch_bytes(BINANCE_EXCHANGE_INFO_URL, timeout=20)
    market = validate_binance_exchange_info(binance_body)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": NOW.isoformat(),
        "wikipedia_pageviews": {
            "endpoint": PAGEVIEWS_BASE,
            "project": PROJECT,
            "project_endpoint": PROJECT_PATH,
            "article": ARTICLE,
            "access": ACCESS,
            "agent": AGENT,
            "granularity": GRANULARITY,
            "definition": "daily English Wikipedia user pageviews; omitted zero-view days reconstructed as zero per Wikimedia tutorial",
            "user_agent": USER_AGENT,
            "chunk_count": len(chunk_records),
            "chunk_response_sha256_combined": combined_hash,
            "chunks": chunk_records,
            **coverage,
        },
        "binance_source": {
            "endpoint": BINANCE_EXCHANGE_INFO_URL,
            "response_sha256": hashlib.sha256(binance_body).hexdigest(),
            **market,
        },
        "frozen_sample": {
            "start": SAMPLE_START.isoformat(),
            "end": SAMPLE_END.isoformat(),
            "signal_embargo_days": 2,
            "feature": "log1p(views[d-2]) - log1p(views[d-9])",
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
    output_dir = ROOT / "reports" / "generated" / "wikipedia-attention-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "preflight.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Wikimedia Bitcoin-attention source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: `{HYPOTHESIS_ID}`\n")
            handle.write("- Backtest executed: **No**\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
