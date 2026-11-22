#!/usr/bin/env python3
"""Bounded, no-key Tardis funding-schedule sample and Binance archive cross-check.

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
import math
import statistics
import sys
import zipfile
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
BINANCE_FUNDING_COLUMNS = ("calc_time", "funding_interval_hours", "last_funding_rate")
BINANCE_FUTURES_DOCS = "https://docs.tardis.dev/historical-data-details/binance-futures"
DATA_TYPES_DOCS = "https://docs.tardis.dev/downloadable-csv-files/data-types"
BINANCE_FUNDING_DOCS = (
    "https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data"
)
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
    if not math.isfinite(parsed):
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

    start = datetime.combine(sample_day, datetime.min.time(), tzinfo=timezone.utc)
    start_us = int(start.timestamp() * 1_000_000)
    end_us = int((start + timedelta(days=1)).timestamp() * 1_000_000)
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
    original_local_times = [row["local_timestamp"] for row in rows]
    out_of_order_count = sum(
        right < left for left, right in zip(original_local_times, original_local_times[1:])
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


def parse_binance_funding_archive_csv(
    csv_text: str, symbol: str, sample_date: str
) -> dict[str, Any]:
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError(f"Unsupported symbol: {symbol}")
    day = date.fromisoformat(sample_date)
    month_start = datetime(day.year, day.month, 1, tzinfo=timezone.utc)
    if day.month == 12:
        next_month = datetime(day.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(day.year, day.month + 1, 1, tzinfo=timezone.utc)
    start_us = int(month_start.timestamp() * 1_000_000)
    end_us = int(next_month.timestamp() * 1_000_000)

    rows = list(csv.reader(io.StringIO(csv_text)))
    if not rows:
        raise ValueError("Empty Binance funding archive CSV")
    header_detected = tuple(value.strip().lower() for value in rows[0]) == BINANCE_FUNDING_COLUMNS
    data_rows = rows[1:] if header_detected else rows
    events = []
    for line_number, row in enumerate(data_rows, start=2 if header_detected else 1):
        if len(row) != 3:
            raise ValueError(f"Expected 3 Binance funding fields at CSV line {line_number}")
        calc_time_ms = int(row[0])
        interval_hours = float(row[1])
        funding_rate = float(row[2])
        if calc_time_ms <= 0 or not math.isfinite(interval_hours) or interval_hours <= 0:
            raise ValueError(f"Invalid timestamp/interval at Binance CSV line {line_number}")
        if not math.isfinite(funding_rate):
            raise ValueError(f"Invalid funding rate at Binance CSV line {line_number}")
        timestamp_us = calc_time_ms * 1_000
        if not (start_us <= timestamp_us < end_us):
            raise ValueError(f"Binance funding timestamp outside UTC month at line {line_number}")
        events.append({
            "timestamp_us": timestamp_us,
            "timestamp_utc": utc_from_microseconds(timestamp_us),
            "funding_interval_hours": interval_hours,
            "archive_last_funding_rate": funding_rate,
        })
    if not events:
        raise ValueError("No Binance funding events in archive CSV")
    events.sort(key=lambda item: item["timestamp_us"])
    timestamps = [item["timestamp_us"] for item in events]
    return {
        "symbol": symbol,
        "month_utc": month_start.strftime("%Y-%m"),
        "status": "PARSED",
        "header_detected": header_detected,
        "rows": len(events),
        "duplicate_timestamps": len(timestamps) - len(set(timestamps)),
        "first_event_timestamp_utc": events[0]["timestamp_utc"],
        "last_event_timestamp_utc": events[-1]["timestamp_utc"],
        "interval_hours_observed": sorted({item["funding_interval_hours"] for item in events}),
        "events": events,
    }


def compare_tardis_to_archive(
    tardis_sample: dict[str, Any], archive_sample: dict[str, Any]
) -> dict[str, Any]:
    archive_by_timestamp = {
        item["timestamp_us"]: item for item in archive_sample["events"]
    }
    tardis_event_times = [
        int(datetime.fromisoformat(value).timestamp() * 1_000_000)
        for value in tardis_sample["unique_next_funding_timestamps_utc"]
    ]
    matched_timestamps = [value for value in tardis_event_times if value in archive_by_timestamp]
    rate_comparisons = []
    for observation in tardis_sample["pre_event_observations"]:
        event_time = int(
            datetime.fromisoformat(observation["next_funding_timestamp_utc"]).timestamp()
            * 1_000_000
        )
        archive_event = archive_by_timestamp.get(event_time)
        if archive_event is None:
            continue
        estimate = float(observation["funding_rate_estimate_for_next_event"])
        settled_archive_rate = float(archive_event["archive_last_funding_rate"])
        difference = estimate - settled_archive_rate
        rate_comparisons.append({
            "event_timestamp_utc": observation["next_funding_timestamp_utc"],
            "tardis_pre_event_rate_estimate": estimate,
            "binance_archive_last_funding_rate": settled_archive_rate,
            "absolute_rate_difference": abs(difference),
            "exact_rate_match_within_1e_12": math.isclose(
                estimate, settled_archive_rate, rel_tol=0.0, abs_tol=1e-12
            ),
        })
    abs_differences = [item["absolute_rate_difference"] for item in rate_comparisons]
    timestamp_pass = (
        len(tardis_event_times) > 0
        and len(matched_timestamps) == len(tardis_event_times)
        and archive_sample["duplicate_timestamps"] == 0
    )
    return {
        "status": (
            "CROSSCHECK_PASS"
            if timestamp_pass and len(rate_comparisons) >= 2
            else "CROSSCHECK_INCOMPLETE"
        ),
        "tardis_next_event_timestamp_count": len(tardis_event_times),
        "binance_archive_event_rows_in_month": archive_sample["rows"],
        "exact_event_timestamp_matches": len(matched_timestamps),
        "event_timestamp_match_rate": (
            len(matched_timestamps) / len(tardis_event_times) if tardis_event_times else None
        ),
        "pre_event_rate_comparison_count": len(rate_comparisons),
        "pre_event_rate_exact_matches": sum(
            item["exact_rate_match_within_1e_12"] for item in rate_comparisons
        ),
        "mean_absolute_rate_difference": (
            statistics.mean(abs_differences) if abs_differences else None
        ),
        "maximum_absolute_rate_difference": max(abs_differences) if abs_differences else None,
        "rate_comparisons": rate_comparisons,
        "interpretation": (
            "Timestamp reconciliation tests whether Tardis next-event times align with Binance archive "
            "calc_time values for this sample. Rate differences are diagnostic only: Tardis documents "
            "that the last pre-event estimate can differ from the final rate applied."
        ),
    }


def request_bytes(url: str, timeout: int = 90) -> tuple[bytes, int, str | None, str | None]:
    request = Request(url, headers={"User-Agent": "qfr-funding-source-probe/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return (
            response.read(),
            response.status,
            response.headers.get("Content-Type"),
            response.headers.get("Content-Length"),
        )


def download_binance_funding_archive(
    symbol: str, sample_date: str, cache_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    day = date.fromisoformat(sample_date)
    month_tag = day.strftime("%Y-%m")
    filename = f"{symbol}-fundingRate-{month_tag}.zip"
    url = (
        "https://data.binance.vision/data/futures/um/monthly/fundingRate/"
        f"{symbol}/{filename}"
    )
    payload, status, content_type, content_length = request_bytes(url)
    checksum_payload, _, _, _ = request_bytes(url + ".CHECKSUM", timeout=30)
    tokens = checksum_payload.decode("utf-8", errors="replace").strip().split()
    if not tokens:
        raise ValueError(f"Empty Binance checksum sidecar for {url}")
    expected_sha256 = tokens[0].lower()
    actual_sha256 = hashlib.sha256(payload).hexdigest().lower()
    if expected_sha256 != actual_sha256:
        raise ValueError(
            f"Binance funding archive SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / filename
    archive_path.write_bytes(payload)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one CSV in Binance archive; found {len(csv_names)}")
        csv_text = archive.read(csv_names[0]).decode("utf-8-sig")
    parsed = parse_binance_funding_archive_csv(csv_text, symbol, sample_date)
    manifest = {
        "source": "Binance Vision monthly USD-M fundingRate archive",
        "source_url": url,
        "checksum_url": url + ".CHECKSUM",
        "http_status": status,
        "content_type": content_type,
        "content_length_header": content_length,
        "archive_file": archive_path.name,
        "archive_bytes": len(payload),
        "archive_sha256": actual_sha256,
        "checksum_sha256": expected_sha256,
        "checksum_verified": True,
        "csv_member": csv_names[0],
        "header_detected": parsed["header_detected"],
        "rows": parsed["rows"],
        "duplicate_timestamps": parsed["duplicate_timestamps"],
        "first_event_timestamp_utc": parsed["first_event_timestamp_utc"],
        "last_event_timestamp_utc": parsed["last_event_timestamp_utc"],
        "interval_hours_observed": parsed["interval_hours_observed"],
        "status": parsed["status"],
    }
    return manifest, parsed


def probe_symbol(
    symbol: str, sample_date: str, cache_dir: Path, output_dir: Path
) -> dict[str, Any]:
    day = date.fromisoformat(sample_date)
    if day.day != 1:
        raise ValueError("The no-key Tardis sample probe is restricted to the first day of a month")
    url = (
        f"https://datasets.tardis.dev/v1/{EXCHANGE}/derivative_ticker/"
        f"{day:%Y/%m/%d}/{symbol}.csv.gz"
    )
    raw_path = cache_dir / f"{symbol}_derivative_ticker_{sample_date}.csv.gz"
    manifest_path = output_dir / f"{symbol}_manifest.json"
    manifest: dict[str, Any] = {
        "symbol": symbol,
        "sample_date_utc": sample_date,
        "tardis": {
            "provider": "Tardis.dev",
            "provider_exchange": EXCHANGE,
            "data_type": "derivative_ticker",
            "source_url": url,
            "documentation": [BINANCE_FUTURES_DOCS, DATA_TYPES_DOCS],
            "download_status": "NOT_STARTED",
            "raw_file_cache_path": str(raw_path),
            "raw_sha256": None,
            "raw_bytes": None,
        },
        "binance_archive": {
            "documentation": [BINANCE_FUNDING_DOCS],
            "status": "NOT_STARTED",
        },
        "crosscheck": {"status": "NOT_RUN"},
    }
    tardis_sample = None
    try:
        payload, http_status, content_type, content_length = request_bytes(url)
        if not payload:
            raise ValueError("Tardis returned an empty response body")
        cache_dir.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)
        csv_text = gzip.decompress(payload).decode("utf-8-sig")
        tardis_sample = parse_derivative_ticker_csv(csv_text, symbol, sample_date)
        manifest["tardis"].update({
            "download_status": "HTTP_200",
            "http_status": http_status,
            "content_type": content_type,
            "content_length_header": content_length,
            "raw_sha256": hashlib.sha256(payload).hexdigest(),
            "raw_bytes": len(payload),
            "sample": tardis_sample,
        })
    except HTTPError as exc:
        manifest["tardis"].update({
            "download_status": "HTTP_ERROR",
            "http_status": exc.code,
            "error": exc.read().decode("utf-8", errors="replace")[:1000],
        })
    except (URLError, TimeoutError, OSError, ValueError, csv.Error) as exc:
        manifest["tardis"].update({
            "download_status": "FAILED",
            "error": str(exc)[:1500],
        })

    archive_sample = None
    try:
        archive_manifest, archive_sample = download_binance_funding_archive(
            symbol, sample_date, cache_dir
        )
        manifest["binance_archive"] = archive_manifest
    except HTTPError as exc:
        manifest["binance_archive"] = {
            "status": "HTTP_ERROR",
            "http_status": exc.code,
            "error": exc.read().decode("utf-8", errors="replace")[:1000],
        }
    except (URLError, TimeoutError, OSError, ValueError, csv.Error, zipfile.BadZipFile) as exc:
        manifest["binance_archive"] = {
            "status": "FAILED",
            "error": str(exc)[:1500],
        }

    if tardis_sample is not None and archive_sample is not None:
        manifest["crosscheck"] = compare_tardis_to_archive(tardis_sample, archive_sample)

    manifest["status"] = (
        "SAMPLE_VALID_CROSSCHECK_PASS"
        if tardis_sample is not None
        and tardis_sample["status"] == "SAMPLE_VALID"
        and manifest["binance_archive"].get("checksum_verified") is True
        and manifest["crosscheck"].get("status") == "CROSSCHECK_PASS"
        else "INCOMPLETE"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_probe(
    sample_date: str,
    symbols: tuple[str, ...],
    output_dir: Path,
    cache_dir: Path,
) -> dict[str, Any]:
    day = date.fromisoformat(sample_date)
    if day.day != 1:
        raise ValueError("The no-key Tardis sample probe is restricted to the first day of a month")
    if not symbols or any(symbol not in ALLOWED_SYMBOLS for symbol in symbols):
        raise ValueError(f"Symbols must be selected from {ALLOWED_SYMBOLS}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifests = [probe_symbol(symbol, sample_date, cache_dir, output_dir) for symbol in symbols]
    valid = all(item.get("status") == "SAMPLE_VALID_CROSSCHECK_PASS" for item in manifests)
    summary = {
        "provider": "Tardis.dev",
        "exchange": EXCHANGE,
        "data_type": "derivative_ticker",
        "sample_date_utc": sample_date,
        "symbols_requested": list(symbols),
        "symbols_valid": [
            item["symbol"] for item in manifests
            if item.get("status") == "SAMPLE_VALID_CROSSCHECK_PASS"
        ],
        "status": "SAMPLE_VALID_CROSSCHECK_PASS" if valid else "INCOMPLETE",
        "settled_funding_rate_available": False,
        "settlement_population_complete": False,
        "manifest_files": [f"{item['symbol']}_manifest.json" for item in manifests],
        "raw_files_retained_in_runner_cache_only": True,
        "research_decision": (
            "This validates a one-day Tardis sample and event-time alignment with a checksum-verified "
            "Binance archive. Pre-event Tardis rates remain estimates, not settled rates; neither source "
            "cross-check proves the complete 2020–2026 payable-settlement population."
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2024-01-01")
    parser.add_argument("--symbols", default="ETHUSDT,BTCUSDT")
    parser.add_argument("--output-dir", default="reports/generated/tardis-funding-probe-2024-01-01")
    parser.add_argument("--cache-dir", default="data/cache/tardis-funding-probe-2024-01-01")
    args = parser.parse_args(argv)
    try:
        summary = run_probe(
            args.date,
            tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()),
            Path(args.output_dir),
            Path(args.cache_dir),
        )
    except Exception as exc:
        print(f"Tardis probe configuration error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "SAMPLE_VALID_CROSSCHECK_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
