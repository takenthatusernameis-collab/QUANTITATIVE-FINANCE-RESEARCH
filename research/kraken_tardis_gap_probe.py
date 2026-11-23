#!/usr/bin/env python3
"""Read-only PI event-context audit for five common Kraken API gaps and delisting."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from kraken_tardis_timestamp_probe import (
    API,
    TARDIS,
    SYMBOLS,
    MAX_API,
    MAX_COMPRESSED,
    _api_ms,
    _fetch,
    _iso,
    parse_api,
    parse_tardis,
)

GAP_SAMPLES = (
    {"gap_start_utc": "2025-12-04T08:00:00Z", "gap_end_utc": "2025-12-04T10:00:00Z"},
    {"gap_start_utc": "2026-02-04T11:00:00Z", "gap_end_utc": "2026-02-04T13:00:00Z"},
    {"gap_start_utc": "2026-02-13T17:00:00Z", "gap_end_utc": "2026-02-13T19:00:00Z"},
    {"gap_start_utc": "2026-05-09T05:00:00Z", "gap_end_utc": "2026-05-09T07:00:00Z"},
    {"gap_start_utc": "2026-10-30T02:00:00Z", "gap_end_utc": "2026-10-30T04:00:00Z"},
)
DELISTING_DATE = "2026-10-30"
DELISTING_API_TIMESTAMPS = (
    "2026-10-30T14:00:00Z",
    "2026-10-30T15:00:00Z",
    "2026-10-30T16:00:00Z",
)
ONE_HOUR_MS = 3_600_000


def _event_index(tardis):
    return {event["event_ms"]: event for event in tardis["events"]}


def _exact_relative_match(api_row, tardis_event):
    if not api_row or not tardis_event or not tardis_event["usable"]:
        return False
    value = api_row.get("relativeFundingRate")
    if value is None:
        return False
    return math.isclose(tardis_event["pre_event_rate"], value, rel_tol=1e-9, abs_tol=1e-15)


def map_api_row_to_next_event(api, tardis, api_timestamp_utc):
    """Compare an inverse API row at T with the Tardis next event at T+1h."""
    api_ms = _api_ms(api_timestamp_utc)
    event_ms = api_ms + ONE_HOUR_MS
    api_row = api["by_time"].get(api_ms)
    event = _event_index(tardis).get(event_ms)
    return {
        "api_row_timestamp_utc": _iso(api_ms),
        "expected_funding_event_utc": _iso(event_ms),
        "api_row_present": api_row is not None,
        "api_relativeFundingRate": api_row.get("relativeFundingRate") if api_row else None,
        "tardis_event_observed": event is not None,
        "tardis_pre_event_utc": event["pre_event_utc"] if event else None,
        "tardis_pre_event_rate": event["pre_event_rate"] if event else None,
        "tardis_pre_event_age_seconds": event["seconds_before_event"] if event else None,
        "tardis_pre_event_usable": bool(event and event["usable"]),
        "exact_relative_rate_match": _exact_relative_match(api_row, event),
    }


def audit_gap_context(api, tardis, gap):
    """Inspect one two-hour API timestamp gap without inserting a rate or settlement."""
    start_ms = _api_ms(gap["gap_start_utc"])
    end_ms = _api_ms(gap["gap_end_utc"])
    if end_ms - start_ms != 2 * ONE_HOUR_MS:
        raise ValueError("Gap sample must span exactly two hours")
    missing_api_ms = start_ms + ONE_HOUR_MS
    gap_event_ms = missing_api_ms + ONE_HOUR_MS
    if gap_event_ms != end_ms:
        raise ValueError("Expected missing API row must map to the right gap boundary event")

    events = _event_index(tardis)
    missing_row = api["by_time"].get(missing_api_ms)
    gap_event = events.get(gap_event_ms)
    next_event = events.get(gap_event_ms + ONE_HOUR_MS)
    next_event_after_gap = bool(
        next_event and next_event["pre_event_ms"] >= gap_event_ms
    )
    if missing_row:
        classification = "API_ROW_PRESENT"
    elif gap_event and next_event_after_gap:
        classification = "MISSING_API_ROW_WITH_TARDIS_EVENT_AND_NEXT_EVENT_SCHEDULE"
    elif gap_event:
        classification = "MISSING_API_ROW_WITH_TARDIS_PRE_EVENT_OBSERVATION_ONLY"
    else:
        classification = "MISSING_API_ROW_WITHOUT_TARDIS_EVENT_OBSERVATION"

    return {
        "gap_start_utc": _iso(start_ms),
        "gap_end_utc": _iso(end_ms),
        "expected_missing_api_row_timestamp_utc": _iso(missing_api_ms),
        "funding_event_for_missing_api_row_utc": _iso(gap_event_ms),
        "api_missing_row_present": missing_row is not None,
        "api_missing_row_relativeFundingRate": missing_row.get("relativeFundingRate") if missing_row else None,
        "tardis_gap_event_observed": gap_event is not None,
        "tardis_gap_event_pre_event_utc": gap_event["pre_event_utc"] if gap_event else None,
        "tardis_gap_event_pre_event_rate": gap_event["pre_event_rate"] if gap_event else None,
        "tardis_gap_event_pre_event_age_seconds": gap_event["seconds_before_event"] if gap_event else None,
        "tardis_gap_event_pre_event_usable": bool(gap_event and gap_event["usable"]),
        "tardis_next_event_observed": next_event is not None,
        "tardis_next_event_pre_event_utc": next_event["pre_event_utc"] if next_event else None,
        "tardis_next_event_pre_event_after_gap_event": next_event_after_gap,
        "left_api_boundary_mapping": map_api_row_to_next_event(api, tardis, gap["gap_start_utc"]),
        "right_api_boundary_mapping": map_api_row_to_next_event(api, tardis, gap["gap_end_utc"]),
        "classification": classification,
        "settlement_observed": False,
        "settlement_population_complete": False,
    }


def audit_delisting_context(api, tardis):
    """Map final API rows to the next scheduled event around the 16:00 UTC delisting."""
    events = _event_index(tardis)
    rows = [map_api_row_to_next_event(api, tardis, stamp) for stamp in DELISTING_API_TIMESTAMPS]
    event_16 = events.get(_api_ms("2026-10-30T16:00:00Z"))
    event_17 = events.get(_api_ms("2026-10-30T17:00:00Z"))
    return {
        "official_delisting_settlement_boundary_utc": "2026-10-30T16:00:00Z",
        "api_row_to_next_event_mappings": rows,
        "tardis_event_at_16_utc_observed": event_16 is not None,
        "tardis_event_at_17_utc_observed": event_17 is not None,
        "api_16_utc_row_maps_to_17_utc_event": True,
        "api_16_utc_row_has_tardis_17_utc_event": event_17 is not None,
        "settlement_observed": False,
        "interpretation": "The 16:00 API row maps to a 17:00 next event under the corroborated one-hour offset; absence of that Tardis event would make it a post-delisting-row candidate, not proof of an invalid settlement.",
    }


def run_gap_audit(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_dates = sorted({gap["gap_start_utc"][:10] for gap in GAP_SAMPLES} | {DELISTING_DATE})
    manifest = {
        "probe": "kraken_pi_tardis_gap_and_delisting_event_context",
        "status": "INCOMPLETE",
        "sample_dates_utc": sample_dates,
        "symbols": list(SYMBOLS),
        "gap_samples": list(GAP_SAMPLES),
        "sources": {
            "kraken_api": API,
            "tardis_dataset": TARDIS,
            "tardis_schema": "https://docs.tardis.dev/downloadable-csv-files/data-types",
            "kraken_inverse_specification": "https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives",
        },
        "working_timestamp_semantics": "RATE_SETTING_WINDOW_START",
        "api_timestamp_to_next_funding_event_offset_hours": 1,
        "rate_field_compared": "relativeFundingRate",
        "tardis_caveat": "Tardis funding_rate describes the next event and its final pre-event value can differ from the rate actually settled by the exchange.",
        "api_sources": {},
        "tardis_sources": {},
        "gap_results": [],
        "delisting_context_by_symbol": {},
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

    for symbol in SYMBOLS:
        api = None
        try:
            api_url = f"{API}?symbol={symbol}"
            api_bytes = _fetch(api_url, MAX_API, "application/json")
            api = parse_api(api_bytes, symbol)
            manifest["api_sources"][symbol] = {
                "url": api_url,
                "sha256": hashlib.sha256(api_bytes).hexdigest(),
                "bytes": len(api_bytes),
                "row_count": api["row_count"],
                "first_timestamp_utc": api["first_timestamp_utc"],
                "last_timestamp_utc": api["last_timestamp_utc"],
                "duplicate_timestamp_count": api["duplicate_timestamp_count"],
                "out_of_order_timestamp_count": api["out_of_order_timestamp_count"],
                "invalid_rate_row_count": api["invalid_rate_row_count"],
            }
        except Exception as exc:
            manifest["errors"].append({
                "symbol": symbol,
                "source": "kraken_api",
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })
            continue

        for sample_date in sample_dates:
            try:
                day = sample_date.split("-")
                tardis_url = f"{TARDIS}/{day[0]}/{day[1]}/{day[2]}/{symbol}.csv.gz"
                tardis_bytes = _fetch(tardis_url, MAX_COMPRESSED, "text/csv")
                tardis = parse_tardis(tardis_bytes, symbol, sample_date)
                source_key = f"{symbol}@{sample_date}"
                manifest["tardis_sources"][source_key] = {
                    "url": tardis_url,
                    "sha256": hashlib.sha256(tardis_bytes).hexdigest(),
                    "bytes": len(tardis_bytes),
                    "quality": tardis["quality"],
                    "event_count": len(tardis["events"]),
                    "usable_pre_event_observation_count": sum(event["usable"] for event in tardis["events"]),
                }
                for gap in GAP_SAMPLES:
                    if gap["gap_start_utc"][:10] == sample_date:
                        result = audit_gap_context(api, tardis, gap)
                        result.update({
                            "symbol": symbol,
                            "tardis_source_key": source_key,
                        })
                        manifest["gap_results"].append(result)
                if sample_date == DELISTING_DATE:
                    manifest["delisting_context_by_symbol"][symbol] = audit_delisting_context(api, tardis)
            except Exception as exc:
                manifest["errors"].append({
                    "symbol": symbol,
                    "sample_date_utc": sample_date,
                    "source": "tardis",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                })

    expected_tardis_sources = len(SYMBOLS) * len(sample_dates)
    api_quality_ok = (
        len(manifest["api_sources"]) == len(SYMBOLS)
        and all(
            item["duplicate_timestamp_count"] == 0
            and item["out_of_order_timestamp_count"] == 0
            and item["invalid_rate_row_count"] == 0
            for item in manifest["api_sources"].values()
        )
    )
    complete = (
        len(manifest["api_sources"]) == len(SYMBOLS)
        and len(manifest["tardis_sources"]) == expected_tardis_sources
        and len(manifest["gap_results"]) == len(SYMBOLS) * len(GAP_SAMPLES)
        and len(manifest["delisting_context_by_symbol"]) == len(SYMBOLS)
        and not manifest["errors"]
        and api_quality_ok
    )
    if complete:
        manifest["status"] = "TARGETED_EVENT_CONTEXT_COMPLETE"
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_gap_audit(args.output_dir)
    print(json.dumps({
        "status": result["status"],
        "gap_results": [
            {
                "symbol": item["symbol"],
                "gap_start_utc": item["gap_start_utc"],
                "expected_missing_api_row_timestamp_utc": item["expected_missing_api_row_timestamp_utc"],
                "funding_event_for_missing_api_row_utc": item["funding_event_for_missing_api_row_utc"],
                "classification": item["classification"],
                "tardis_gap_event_observed": item["tardis_gap_event_observed"],
                "tardis_next_event_pre_event_after_gap_event": item["tardis_next_event_pre_event_after_gap_event"],
                "settlement_observed": item["settlement_observed"],
            }
            for item in result["gap_results"]
        ],
        "delisting_context_by_symbol": result["delisting_context_by_symbol"],
        "settlement_population_complete": result["settlement_population_complete"],
        "data_acceptance_status": result["data_acceptance_status"],
        "errors": result["errors"],
    }, indent=2, sort_keys=True))
    if result["status"] != "TARGETED_EVENT_CONTEXT_COMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
