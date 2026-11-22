#!/usr/bin/env python3
"""Bounded public Bybit funding-history sample; not Binance data or backtest evidence."""
from __future__ import annotations
import argparse, hashlib, json, math, statistics, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.bybit.com/v5/market/funding/history"
DOCS_URL = "https://bybit-exchange.github.io/docs/v5/market/history-fund-rate"
ALLOWED_SYMBOLS = ("BTCUSDT", "ETHUSDT")
MAX_LIMIT, MAX_REQUESTS, RETRY_ATTEMPTS = 200, 6, 3
REQUEST_DELAY_SECONDS = 0.25
SAMPLE_ENDS_UTC = ("2020-01-01T23:59:59Z", "2022-01-01T23:59:59Z")


def to_ms(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def utc(value):
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def parse_payload(payload, symbol, end_ms, limit):
    if not isinstance(payload, dict):
        raise ValueError("response JSON must be an object")
    if payload.get("retCode") not in (0, "0"):
        raise ValueError(f"Bybit API rejected request: {payload.get('retCode')} {payload.get('retMsg')}")
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("category") != "linear":
        raise ValueError("result category must be linear")
    items = result.get("list")
    if not isinstance(items, list):
        raise ValueError("result.list must be a list")
    if len(items) > limit:
        raise ValueError(f"response exceeded requested limit: {len(items)} > {limit}")
    rows = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or item.get("symbol") != symbol:
            raise ValueError(f"symbol mismatch or malformed record at list[{i}]")
        try:
            rate, ts = float(item["fundingRate"]), int(item["fundingRateTimestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid record at list[{i}]") from exc
        if not math.isfinite(rate) or ts <= 0:
            raise ValueError(f"invalid rate or timestamp at list[{i}]")
        if ts > end_ms:
            raise ValueError("record timestamp exceeds requested endTime")
        rows.append((ts, rate))
    timestamps = [r[0] for r in rows]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate funding timestamps")
    rows.sort()
    gaps = [(b[0] - a[0]) / 3_600_000 for a, b in zip(rows, rows[1:])]
    return {
        "status": "OBSERVED" if rows else "NO_RECORDS", "symbol": symbol,
        "sample_end_utc": utc(end_ms), "limit_requested": limit,
        "records_returned": len(rows), "duplicate_timestamps": 0,
        "earliest_record_utc": utc(rows[0][0]) if rows else None,
        "latest_record_utc": utc(rows[-1][0]) if rows else None,
        "observed_timestamp_gap_hours_distribution": dict(sorted(Counter(round(g, 6) for g in gaps).items())),
        "observed_timestamp_gap_hours_median": statistics.median(gaps) if gaps else None,
        "timestamp_gaps_do_not_prove_settlement_completeness": True,
    }


def request_sample(symbol, end_ms, limit=MAX_LIMIT):
    url = API_URL + "?" + urlencode({"category": "linear", "symbol": symbol, "endTime": end_ms, "limit": limit})
    req = Request(url, headers={"User-Agent": "qfr-bybit-funding-probe/1.0", "Accept": "application/json"})
    error = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urlopen(req, timeout=20) as response:
                raw = response.read()
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("response JSON must be an object")
            return payload, raw
        except HTTPError as exc:
            error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code != 429 and exc.code < 500:
                raise RuntimeError(error) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
            error = str(exc)
        if attempt + 1 < RETRY_ATTEMPTS:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {RETRY_ATTEMPTS} attempts: {error}")


def probe_symbol(symbol, limit=MAX_LIMIT, fetcher=request_sample, sleeper=time.sleep, cache_dir=None):
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError(f"unsupported symbol: {symbol}")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be 1..{MAX_LIMIT}")
    dates = [*SAMPLE_ENDS_UTC, datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")]
    samples = []
    for index, date in enumerate(dates):
        end_ms = to_ms(date)
        if index:
            sleeper(REQUEST_DELAY_SECONDS)
        try:
            payload, raw = fetcher(symbol, end_ms, limit)
            sample = parse_payload(payload, symbol, end_ms, limit)
            sample.update({"sample_date": date, "response_sha256": hashlib.sha256(raw).hexdigest(),
                          "raw_response_cache_only": True})
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
                (cache_dir / f"{symbol}_{date[:10]}_response.json").write_bytes(raw)
        except Exception as exc:
            sample = {"status": "SAMPLE_FAILED", "symbol": symbol, "sample_date": date,
                      "sample_end_utc": utc(end_ms), "error": str(exc), "accepted_for_research": False}
        samples.append(sample)
    return {
        "provider": "Bybit", "endpoint": API_URL, "documentation": DOCS_URL,
        "symbol": symbol, "category": "linear", "sample_count": len(samples), "samples": samples,
        "pagination_attempted": False,
        "pagination_policy": "Three bounded endTime-only samples; no full pagination attempted",
        "historical_retention_officially_documented": False,
        "accepted_for_full_history_backtest": False,
        "limitations": [
            "2020-01-01, 2022-01-01 and run-time UTC samples do not establish continuous coverage.",
            "Observed timestamp gaps do not establish the complete payable settlement population or interval semantics.",
            "Bybit is an independent venue and is not Binance evidence; any follow-up is a separate experiment.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--limit", type=int, default=MAX_LIMIT)
    args = parser.parse_args(argv)
    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    if len(symbols) != 2 or set(symbols) != set(ALLOWED_SYMBOLS):
        parser.error("symbols must be exactly BTCUSDT,ETHUSDT")
    if not 1 <= args.limit <= MAX_LIMIT:
        parser.error(f"limit must be 1..{MAX_LIMIT}")
    if len(symbols) * 3 > MAX_REQUESTS:
        parser.error("request count exceeds fixed bound")
    output, cache = Path(args.output_dir), Path(args.cache_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifests = []
    for index, symbol in enumerate(symbols):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        manifest = probe_symbol(symbol, args.limit, cache_dir=cache)
        manifests.append(manifest)
        (output / f"{symbol}_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "provider": "Bybit", "probe_type": "bounded public funding-history sample",
        "symbols_requested": symbols, "sample_dates_utc": [*SAMPLE_ENDS_UTC, "run-time UTC"],
        "max_requests_without_retries": MAX_REQUESTS,
        "max_total_attempts_including_retries": MAX_REQUESTS * RETRY_ATTEMPTS,
        "limit_per_request": args.limit,
        "status": "PROBE_COMPLETE" if all(not any(s["status"] == "SAMPLE_FAILED" for s in m["samples"]) for m in manifests) else "PROBE_PARTIAL",
        "accepted_for_full_history_backtest": False,
        "decision": "Public API samples only; no history acceptance, settlement completeness claim, or strategy backtest.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if summary["status"] == "PROBE_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
