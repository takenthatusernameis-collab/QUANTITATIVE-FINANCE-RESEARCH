#!/usr/bin/env python3
"""Read-only PI timestamp mapping probe: Tardis next-event ticker vs Kraken history."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SYMBOLS = ("PI_XBTUSD", "PI_ETHUSD")
EXCHANGE = "cryptofacilities"
API = "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates"
TARDIS = "https://datasets.tardis.dev/v1/cryptofacilities/derivative_ticker"
KRAKEN_API_DOCS = "https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates"
KRAKEN_WS_DOCS = "https://docs.kraken.com/api/docs/futures-api/websocket/ticker"
TARDIS_DOCS = "https://docs.tardis.dev/downloadable-csv-files/data-types"
MAX_COMPRESSED, MAX_CSV, MAX_API, MAX_ROWS = 50_000_000, 150_000_000, 25_000_000, 500_000
MAX_AGE_SECONDS, MIN_EVENTS = 300, 20
RATE_FIELDS = ("fundingRate", "relativeFundingRate")
UTC = timezone.utc


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def _finite(value, field):
    if value is None or str(value).strip() == "":
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} is non-finite")
    return result


def _api_ms(value):
    stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Kraken API timestamp lacks timezone")
    return int(stamp.astimezone(UTC).timestamp() * 1000)


def _bounds(sample_date):
    day = date.fromisoformat(sample_date)
    if day.day != 1:
        raise ValueError("Tardis no-key sample must be the first day of a month")
    start = datetime.combine(day, time.min, tzinfo=UTC)
    return day, int(start.timestamp() * 1e6), int((start + timedelta(days=1)).timestamp() * 1e6)


def parse_tardis(payload, symbol, sample_date):
    if symbol not in SYMBOLS or not payload or len(payload) > MAX_COMPRESSED:
        raise ValueError("Unsupported symbol or invalid/oversized Tardis payload")
    day, start, end = _bounds(sample_date)
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
        raw = stream.read(MAX_CSV + 1)
    if len(raw) > MAX_CSV:
        raise ValueError("Tardis CSV exceeds uncompressed limit")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"exchange", "symbol", "timestamp", "local_timestamp", "funding_timestamp", "funding_rate"}
    if not required.issubset(set(reader.fieldnames or ())):
        raise ValueError(f"Tardis schema missing {sorted(required - set(reader.fieldnames or ()))}")
    events, locals_seen = {}, []
    rows = missing_event = missing_rate = out_of_order = 0
    previous_local = None
    for line, row in enumerate(reader, 2):
        if not row or not any(str(v or "").strip() for v in row.values()):
            continue
        rows += 1
        if rows > MAX_ROWS:
            raise ValueError("Tardis row limit exceeded")
        if row.get("exchange") != EXCHANGE or row.get("symbol") != symbol:
            raise ValueError(f"Unexpected Tardis exchange/symbol at line {line}")
        exchange_us, local_us = int(row["timestamp"]), int(row["local_timestamp"])
        if exchange_us <= 0 or local_us <= 0 or not start - 300_000_000 <= exchange_us < end + 300_000_000:
            raise ValueError(f"Invalid/out-of-window Tardis timestamp at line {line}")
        if previous_local is not None and local_us < previous_local:
            out_of_order += 1
        previous_local = local_us
        locals_seen.append(local_us)
        raw_event = str(row.get("funding_timestamp") or "").strip()
        if not raw_event:
            missing_event += 1
            continue
        event_us = int(raw_event)
        rate = _finite(row.get("funding_rate"), "funding_rate")
        if rate is None:
            missing_rate += 1
            continue
        if start <= event_us <= end and local_us < event_us:
            old = events.get(event_us)
            if old is None or local_us > old["local_us"]:
                events[event_us] = {"event_us": event_us, "local_us": local_us, "rate": rate}
    if not rows:
        raise ValueError("Tardis returned no rows")
    parsed = []
    for event_us, item in sorted(events.items()):
        if event_us % 3_600_000_000:
            raise ValueError("Tardis funding event is not on an hourly UTC boundary")
        age = (event_us - item["local_us"]) / 1e6
        parsed.append({
            "event_ms": event_us // 1000,
            "event_utc": _iso(event_us // 1000),
            "pre_event_utc": _iso(item["local_us"] // 1000),
            "seconds_before_event": round(age, 6),
            "pre_event_rate": item["rate"],
            "usable": age <= MAX_AGE_SECONDS,
        })
    return {
        "events": parsed,
        "quality": {
            "row_count": rows,
            "missing_funding_timestamp_count": missing_event,
            "missing_funding_rate_count": missing_rate,
            "out_of_order_local_timestamp_count": out_of_order,
            "first_local_timestamp_utc": _iso(min(locals_seen) // 1000),
            "last_local_timestamp_utc": _iso(max(locals_seen) // 1000),
            "uncompressed_bytes": len(raw),
        },
    }


def parse_api(payload, symbol):
    if symbol not in SYMBOLS or not payload or len(payload) > MAX_API:
        raise ValueError("Unsupported symbol or invalid/oversized Kraken API payload")
    doc = json.loads(payload.decode("utf-8"))
    if doc.get("result") != "success" or not isinstance(doc.get("rates"), list) or not doc["rates"]:
        raise ValueError("Kraken API did not return a successful nonempty rates array")
    if len(doc["rates"]) > MAX_ROWS:
        raise ValueError("Kraken API row limit exceeded")
    by_time, previous = {}, None
    duplicates = out_of_order = invalid = 0
    for row in doc["rates"]:
        stamp = _api_ms(row["timestamp"])
        if previous is not None and stamp < previous:
            out_of_order += 1
        previous = stamp
        duplicates += stamp in by_time
        absolute, relative = _finite(row.get("fundingRate"), "fundingRate"), _finite(row.get("relativeFundingRate"), "relativeFundingRate")
        invalid += absolute is None or relative is None
        by_time[stamp] = {"fundingRate": absolute, "relativeFundingRate": relative}
    times = sorted(by_time)
    return {
        "by_time": by_time,
        "row_count": len(doc["rates"]),
        "duplicate_timestamp_count": duplicates,
        "out_of_order_timestamp_count": out_of_order,
        "invalid_rate_row_count": invalid,
        "first_timestamp_utc": _iso(times[0]),
        "last_timestamp_utc": _iso(times[-1]),
    }


def compare(tardis, api, min_events=MIN_EVENTS):
    by_time, metrics, details = api["by_time"], {}, []
    for field in RATE_FIELDS:
        event_diffs, prior_diffs = [], []
        event_better = prior_better = ties = exact_event = exact_prior = 0
        for event in tardis["events"]:
            if not event["usable"]:
                continue
            current, prior = by_time.get(event["event_ms"]), by_time.get(event["event_ms"] - 3_600_000)
            if not current or not prior or current[field] is None or prior[field] is None:
                continue
            a, b = abs(event["pre_event_rate"] - current[field]), abs(event["pre_event_rate"] - prior[field])
            event_diffs.append(a); prior_diffs.append(b)
            event_better += a < b; prior_better += b < a; ties += a == b
            exact_event += math.isclose(event["pre_event_rate"], current[field], rel_tol=1e-9, abs_tol=1e-15)
            exact_prior += math.isclose(event["pre_event_rate"], prior[field], rel_tol=1e-9, abs_tol=1e-15)
        n = len(event_diffs)
        med_event = statistics.median(event_diffs) if n else None
        med_prior = statistics.median(prior_diffs) if n else None
        candidate = "INCONCLUSIVE"
        if n >= min_events and med_event is not None and med_prior is not None:
            if event_better / n >= 0.8 and med_event < med_prior * 0.5:
                candidate = "PERIOD_END"
            elif prior_better / n >= 0.8 and med_prior < med_event * 0.5:
                candidate = "PERIOD_START"
        metrics[field] = {
            "comparisons": n,
            "closer_to_event_timestamp_count": event_better,
            "closer_to_one_hour_prior_count": prior_better,
            "equal_distance_count": ties,
            "exact_at_event_count": exact_event,
            "exact_one_hour_prior_count": exact_prior,
            "median_abs_difference_at_event": med_event,
            "median_abs_difference_one_hour_prior": med_prior,
            "candidate_boundary": candidate,
        }
    for event in tardis["events"]:
        current, prior = by_time.get(event["event_ms"]), by_time.get(event["event_ms"] - 3_600_000)
        details.append({
            "event_utc": event["event_utc"],
            "pre_event_utc": event["pre_event_utc"],
            "seconds_before_event": event["seconds_before_event"],
            "tardis_funding_rate": event["pre_event_rate"],
            "api_fundingRate_at_event": current["fundingRate"] if current else None,
            "api_fundingRate_one_hour_prior": prior["fundingRate"] if prior else None,
            "api_relativeFundingRate_at_event": current["relativeFundingRate"] if current else None,
            "api_relativeFundingRate_one_hour_prior": prior["relativeFundingRate"] if prior else None,
        })
    candidates = []
    for field, metric in metrics.items():
        boundary = metric["candidate_boundary"]
        if boundary == "PERIOD_END":
            score = (metric["exact_at_event_count"], metric["closer_to_event_timestamp_count"], -(metric["median_abs_difference_at_event"] or 0))
        elif boundary == "PERIOD_START":
            score = (metric["exact_one_hour_prior_count"], metric["closer_to_one_hour_prior_count"], -(metric["median_abs_difference_one_hour_prior"] or 0))
        else:
            continue
        candidates.append((score, field, boundary))
    candidates.sort(reverse=True)
    event_matches = sum(event["event_ms"] in by_time for event in tardis["events"])
    return {
        "tardis_next_event_count": len(tardis["events"]),
        "usable_pre_event_observation_count": sum(e["usable"] for e in tardis["events"]),
        "api_exact_event_timestamp_matches": event_matches,
        "api_event_timestamp_coverage": round(event_matches / len(tardis["events"]), 6) if tardis["events"] else 0,
        "candidate_timestamp_to_accrual_mapping": candidates[0][2] if candidates else "INCONCLUSIVE",
        "best_matching_api_rate_field": candidates[0][1] if candidates else None,
        "rate_alignment_by_api_field": metrics,
        "event_comparisons": details,
        "api_row_count": api["row_count"],
        "api_first_timestamp_utc": api["first_timestamp_utc"],
        "api_last_timestamp_utc": api["last_timestamp_utc"],
        "api_duplicate_timestamp_count": api["duplicate_timestamp_count"],
        "api_out_of_order_timestamp_count": api["out_of_order_timestamp_count"],
        "api_invalid_rate_row_count": api["invalid_rate_row_count"],
    }


def _fetch(url, limit, accept):
    request = Request(url, headers={"User-Agent": "QFR-Kraken-Timestamp-Audit/1.0", "Accept": accept})
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url.split('?')[0]}")
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise RuntimeError(f"Response exceeded byte limit for {url.split('?')[0]}")
    return payload


def run_probe(output_dir, sample_date="2026-10-01"):
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "probe": "kraken_pi_tardis_next_funding_timestamp_alignment",
        "status": "INCONCLUSIVE",
        "sample_date_utc": sample_date,
        "symbols": list(SYMBOLS),
        "sources": {"kraken_api": API, "kraken_api_docs": KRAKEN_API_DOCS, "kraken_websocket_docs": KRAKEN_WS_DOCS, "tardis_docs": TARDIS_DOCS},
        "semantics": {
            "kraken_api": "Ascending timestamp order is documented; timestamp-to-accrual mapping is not.",
            "kraken_websocket": "funding_rate is current; next_funding_rate_time is time until the next funding rate.",
            "tardis": "funding_timestamp is the next event; funding_rate is for that event and the last pre-event value can differ from settlement.",
        },
        "results_by_symbol": {},
        "timestamp_to_accrual_mapping": "INCONCLUSIVE",
        "settlement_population_complete": False,
        "data_acceptance_status": "PROVISIONAL_NOT_ACCEPTED",
        "historical_archive_downloaded": False,
        "raw_data_retained": False,
        "raw_data_uploaded": False,
        "raw_data_committed": False,
        "credentials_used": False,
        "paid_data_used": False,
        "backtest_run": False,
        "cross_venue_merge_performed": False,
        "errors": [],
    }
    try:
        day, _, _ = _bounds(sample_date)
        for symbol in SYMBOLS:
            tardis_url = f"{TARDIS}/{day.year}/{day.month:02d}/{day.day:02d}/{symbol}.csv.gz"
            api_url = f"{API}?symbol={symbol}"
            try:
                tardis_bytes = _fetch(tardis_url, MAX_COMPRESSED, "text/csv")
                api_bytes = _fetch(api_url, MAX_API, "application/json")
                tardis = parse_tardis(tardis_bytes, symbol, sample_date)
                api = parse_api(api_bytes, symbol)
                result = compare(tardis, api)
                result.update({
                    "tardis_source_url": tardis_url,
                    "tardis_source_sha256": hashlib.sha256(tardis_bytes).hexdigest(),
                    "tardis_source_bytes": len(tardis_bytes),
                    "kraken_api_url": api_url,
                    "kraken_api_response_sha256": hashlib.sha256(api_bytes).hexdigest(),
                    "kraken_api_response_bytes": len(api_bytes),
                    "tardis_quality": tardis["quality"],
                })
                manifest["results_by_symbol"][symbol] = result
            except Exception as exc:
                manifest["errors"].append({"symbol": symbol, "error_type": type(exc).__name__, "error": str(exc)[:300]})
        results = list(manifest["results_by_symbol"].values())
        valid = (
            len(results) == len(SYMBOLS)
            and all(
                item["candidate_timestamp_to_accrual_mapping"] in ("PERIOD_END", "PERIOD_START")
                and item["usable_pre_event_observation_count"] >= MIN_EVENTS
                and item["api_event_timestamp_coverage"] >= 0.9
                and item["api_duplicate_timestamp_count"] == 0
                and item["api_out_of_order_timestamp_count"] == 0
                and item["api_invalid_rate_row_count"] == 0
                and item["tardis_quality"]["out_of_order_local_timestamp_count"] == 0
                for item in results
            )
            and len({item["candidate_timestamp_to_accrual_mapping"] for item in results}) == 1
        )
        if valid:
            manifest["timestamp_to_accrual_mapping"] = results[0]["candidate_timestamp_to_accrual_mapping"]
            manifest["status"] = "EVENT_TIME_MAPPING_CORROBORATED"
    except Exception as exc:
        manifest["status"] = "FAILED"
        manifest["errors"].append({"error_type": type(exc).__name__, "error": str(exc)[:300]})
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-date", default="2026-10-01")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe(args.output_dir, args.sample_date)
    print(json.dumps({
        "status": result["status"],
        "timestamp_to_accrual_mapping": result["timestamp_to_accrual_mapping"],
        "results_by_symbol": {
            symbol: {
                "candidate": item["candidate_timestamp_to_accrual_mapping"],
                "events": item["tardis_next_event_count"],
                "usable": item["usable_pre_event_observation_count"],
                "event_time_coverage": item["api_event_timestamp_coverage"],
                "best_rate_field": item["best_matching_api_rate_field"],
            }
            for symbol, item in result["results_by_symbol"].items()
        },
        "settlement_population_complete": result["settlement_population_complete"],
        "data_acceptance_status": result["data_acceptance_status"],
        "errors": result["errors"],
    }, indent=2, sort_keys=True))
    if result["status"] != "EVENT_TIME_MAPPING_CORROBORATED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
