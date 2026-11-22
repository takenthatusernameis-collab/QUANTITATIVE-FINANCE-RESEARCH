#!/usr/bin/env python3
"""Bounded, no-key Tardis derivative-ticker sample probe.

This audits one first-of-month sample only. It does not certify the historical
settlement population or expose the final settled funding rate.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXCHANGE = "binance-futures"
ALLOWED_SYMBOLS = ("ETHUSDT", "BTCUSDT")
REQUIRED_COLUMNS = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "funding_timestamp",
    "funding_rate",
    "mark_price",
)
BINANCE_FUTURES_DOCS = "https://docs.tardis.dev/historical-data-details/binance-futures"
DATA_TYPES_DOCS = "https://docs.tardis.dev/downloadable-csv-files/data-types"
MAX_ACCEPTED_LOCAL_GAP_SECONDS = 60.0
MAX_ACCEPTED_PRE_EVENT_AGE_SECONDS = 60.0


def utc_from_microseconds(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000, tz=timezone.utc).isoformat()


def parse_optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    parsed = int(value.strip())
    if parsed <= 0:
        raise ValueError("timestamp must be a positive integer")
    return parsed


def parse_optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    parsed = float(value.strip())
    if not (parsed == parsed and abs(parsed) != float("inf")):
        raise ValueError("numeric field must be finite")
    return parsed


def parse_derivative_ticker_csv(csv_text: str, symbol: str, sample_date: str) -> dict[str, Any]:
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError(f"Unsupported symbol: {symbol}")
    sample_day = date.fromisoformat(sample_date)
    if sample_day.day != 1:
        raise ValueError("The no-key Tardis sample probe is restricted to the first day of a month")

    reader = csv.DictReader(io.StringIO(csv_text))
    columns = tuple(reader.fieldnames or ())
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise ValueError(f"Missing required derivative_ticker columns: {missing}")

    start_us = int(datetime.combine(sample_day, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1_000_000)
    end_us = int((datetime.combine(sample_day, datetime.min.time(), tzinfo=timezone.utc)
                  + timedelta(days=1)).timestamp() * 1_000_000)
    rows: list[dict[str, Any]] = []
    funding_rate_count = 0
    mark_price_count = 0
    funding_timestamp_count = 0
    for line_number, row in enumerate(reader, start=2):
        if not row or not any(value for value in row.values() if value):
            continue
        if row.get("exchange") != EXCHANGE or row.get("symbol") != symbol:
            raise ValueError(
                f"Unexpected exchange/symbol at CSV line {line_number}: "
                f"{row.get('exchange')}/{row.get('symbol')}"
            )
        timestamp = parse_optional_int(row.get("timestamp"))
        local_timestamp = parse_optional_int(row.get("local_timestamp"))
        if timestamp is None or local_timestamp is None:
            raise ValueError(f"Missing exchange/local timestamp at CSV line {line_number}")
        if not (start_us - 300_000_000 <= timestamp < end_us + 300_000_000):
            raise ValueError(f"Exchange timestamp outside sample day at CSV line {line_number}")
        funding_timestamp = parse_optional_int(row.get("funding_timestamp"))
        funding_rate = parse_optional_float(row.get("funding_rate"))
        mark_price = parse_optional_float(row.get("mark_price"))
        funding_timestamp_count += funding_timestamp is not None
        funding_rate_count += funding_rate is not None
        mark_price_count += mark_price is not None
        rows.append({
            "timestamp": timestamp,
            "local_timestamp": local_timestamp,
            "funding_timestamp": funding_timestamp,
            "funding_rate": funding_rate,
            "mark_price": mark_price,
        })

    if not rows:
        raise ValueError("No derivative_ticker rows were returned")

    local_times = sorted({row["local_timestamp"] for row in rows})
    gaps = [
        (right - left) / 1_000_000
        for left, right in zip(local_times, local_times[1:])
        if right >= left
    ]
    out_of_order_count = sum(
        right < left
        for left, right in zip(
            [row["local_timestamp"] for row in rows],
            [row["local_timestamp"] for row in rows][1:],
        )
    )
    max_gap = max(gaps) if gaps else None

    event_candidates: dict[int, dict[str, Any]] = {}
    unique_next_events: set[int] = set()
    for row in rows:
        event_time = row["funding_timestamp"]
        if event_time is None:
            continue
        unique_next_events.add(event_time)
        if row["local_timestamp"] >= event_time or row["funding_rate"] is None:
            continue
        previous = event_candidates.get(event_time)
        if previous is None or row["local_timestamp"] > previous["local_timestamp"]:
            event_candidates[event_time] = row

    pre_event_observations = []
    for event_time in sorted(unique_next_events):
        observation = event_candidates.get(event_time)
        if observation is None:
            continue
        age = (event_time - observation["local_timestamp"]) / 1_000_000
        pre_event_observations.append({
            "next_funding_timestamp_utc": utc_from_microseconds(event_time),
            "last_observation_local_timestamp_utc": utc_from_microseconds(observation["local_timestamp"]),
            "seconds_before_event": round(age, 6),
            "funding_rate_estimate_for_next_event": observation["funding_rate"],
            "mark_price_at_observation": observation["mark_price"],
        })

    max_pre_event_age = max(
        (item["seconds_before_event"] for item in pre_event_observations),
        default=None,
    )
    sample_valid = (
        len(rows) >= 1_000
        and len(local_times) >= 1_000
        and funding_timestamp_count > 0
        and funding_rate_count > 0
        and mark_price_count > 0
        and len(pre_event_observations) >= 2
        and max_gap is not None
        and max_gap <= MAX_ACCEPTED_LOCAL_GAP_SECONDS
        and max_pre_event_age is not None
        and max_pre_event_age <= MAX_ACCEPTED_PRE_EVENT_AGE_SECONDS
    )

    return {
        "symbol": symbol,
        "exchange": EXCHANGE,
        "sample_date_utc": sample_date,
        "status": "SAMPLE_VALID" if sample_valid else "SAMPLE_INCOMPLETE",
        "schema_columns": list(columns),
        "row_count": len(rows),
        "unique_local_timestamp_count": len(local_times),
        "out_of_order_local_timestamp_count": out_of_order_count,
        "funding_timestamp_non_null_rows": funding_timestamp_count,
        "funding_rate_non_null_rows": funding_rate_count,
        "mark_price_non_null_rows": mark_price_count,
        "first_exchange_timestamp_utc": utc_from_microseconds(min(r["timestamp"] for r in rows)),
        "last_exchange_timestamp_utc": utc_from_microseconds(max(r["timestamp"] for r in rows)),
        "first_local_timestamp_utc": utc_from_microseconds(min(local_times)),
        "last_local_timestamp_utc": utc_from_microseconds(max(local_times)),
        "unique_next_funding_timestamps_utc": [
            utc_from_microseconds(value) for value in sorted(unique_next_events)
        ],
        "pre_event_observations": pre_event_observations,
        "local_timestamp_gap_seconds": {
            "median": round(statistics.median(gaps), 6) if gaps else None,
            "maximum": round(max_gap, 6) if max_gap is not None else None,
            "count_over_60_seconds": sum(gap > MAX_ACCEPTED_LOCAL_GAP_SECONDS for gap in gaps),
        },
        "max_pre_event_observation_age_seconds": (
            round(max_pre_event_age, 6) if max_pre_event_age is not None else None
        ),
        "funding_semantics": (
            "funding_timestamp is the next funding event; funding_rate is the rate for that next event "
            "and may change before it. Tardis documents that the last pre-event value can differ from "
            "the rate ultimately settled."
        ),
        "settled_funding_rate_available": False,
        "settlement_population_complete": False,
        "limitations": [
            "This is one free first-of-month sample, not a full historical series.",
            "Pre-event funding_rate is an as-of estimate, not the final settled rate.",
            "The downloadable CSV omits disconnect-event markers; timestamp-gap diagnostics are not proof of zero packet loss.",
            "A successful sample does not prove complete payable-settlement population or contract-incarnation coverage.",
        ],
    }


def probe_symbol(symbol: str, sample_date: str, output_dir: Path) -> dict[str, Any]:
    day = date.fromisoformat(sample_date)
    if day.day != 1:
        raise ValueError("The no-key Tardis sample probe is restricted to the first day of a month")
    url = (
        f"https://datasets.tardis.dev/v1/{EXCHANGE}/derivative_ticker/"
        f"{day:%Y/%m/%d}/{symbol}.csv.gz"
    )
    raw_path = output_dir / f"{symbol}_derivative_ticker_{sample_date}.csv.gz"
    manifest_path = output_dir / f"{symbol}_manifest.json"
    manifest: dict[str, Any] = {
        "provider": "Tardis.dev",
        "provider_exchange": EXCHANGE,
        "data_type": "derivative_ticker",
        "symbol": symbol,
        "sample_date_utc": sample_date,
        "source_url": url,
        "documentation": [BINANCE_FUTURES_DOCS, DATA_TYPES_DOCS],
        "download_status": "NOT_STARTED",
        "raw_file": raw_path.name,
        "raw_sha256": None,
        "raw_bytes": None,
    }
    try:
        request = Request(url, headers={"User-Agent": "qfr-tardis-funding-probe/1.0"})
        with urlopen(request, timeout=90) as response:
            payload = response.read()
            manifest["http_status"] = response.status
            manifest["content_type"] = response.headers.get("Content-Type")
            manifest["content_length_header"] = response.headers.get("Content-Length")
        if not payload:
            raise ValueError("Tardis returned an empty response body")
        raw_path.write_bytes(payload)
        manifest["raw_bytes"] = len(payload)
        manifest["raw_sha256"] = hashlib.sha256(payload).hexdigest()
        manifest["download_status"] = "HTTP_200"
        csv_text = gzip.decompress(payload).decode("utf-8-sig")
        parsed = parse_derivative_ticker_csv(csv_text, symbol, sample_date)
        manifest.update(parsed)
    except HTTPError as exc:
        manifest["download_status"] = "HTTP_ERROR"
        manifest["http_status"] = exc.code
        manifest["error"] = exc.read().decode("utf-8", errors="replace")[:1000]
        manifest["status"] = "DOWNLOAD_FAILED"
    except (URLError, TimeoutError, OSError, ValueError, csv.Error) as exc:
        manifest["download_status"] = "FAILED"
        manifest["error"] = str(exc)[:1500]
        manifest["status"] = "PROBE_FAILED"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_probe(sample_date: str, symbols: tuple[str, ...], output_dir: Path) -> dict[str, Any]:
    day = date.fromisoformat(sample_date)
    if day.day != 1:
        raise ValueError("The no-key Tardis sample probe is restricted to the first day of a month")
    if not symbols or any(symbol not in ALLOWED_SYMBOLS for symbol in symbols):
        raise ValueError(f"Symbols must be selected from {ALLOWED_SYMBOLS}")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = [probe_symbol(symbol, sample_date, output_dir) for symbol in symbols]
    valid = all(item.get("status") == "SAMPLE_VALID" for item in manifests)
    summary = {
        "provider": "Tardis.dev",
        "exchange": EXCHANGE,
        "data_type": "derivative_ticker",
        "sample_date_utc": sample_date,
        "symbols_requested": list(symbols),
        "symbols_valid": [item["symbol"] for item in manifests if item.get("status") == "SAMPLE_VALID"],
        "status": "SAMPLE_VALID" if valid else "INCOMPLETE",
        "settled_funding_rate_available": False,
        "settlement_population_complete": False,
        "manifest_files": [f"{item['symbol']}_manifest.json" for item in manifests],
        "raw_files": [item["raw_file"] for item in manifests if item.get("raw_sha256")],
        "research_decision": (
            "Sample access/schema and upcoming-event observability only; do not use this sample "
            "as proof of final settlement rates or complete historical funding."
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2024-01-01")
    parser.add_argument("--symbols", default="ETHUSDT,BTCUSDT")
    parser.add_argument("--output-dir", default="data/raw/tardis-funding-probe-2024-01-01")
    args = parser.parse_args(argv)
    try:
        summary = run_probe(
            args.date,
            tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()),
            Path(args.output_dir),
        )
    except Exception as exc:
        print(f"Tardis probe configuration error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "SAMPLE_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
