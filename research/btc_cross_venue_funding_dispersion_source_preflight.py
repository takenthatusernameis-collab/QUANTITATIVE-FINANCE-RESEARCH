#!/usr/bin/env python3
"""Read-only source feasibility for matched MEXC/Binance BTC perpetual funding dispersion."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import statistics
import urllib.parse

import mexc_btc_funding_downside as mexc
import stlfsi4_btc_downside_semivariance as btc
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-CROSS-VENUE-FUNDING-DISPERSION-DOWNSIDE-01"
START_DATE = dt.date(2025, 6, 15)
END_DATE = dt.date(2026, 11, 23)
PRICE_START_DATE = START_DATE - dt.timedelta(days=5)
PAGE_SIZE = 1000
MAX_PAGES = 10
MIN_MATCHED_DAYS = 400
MAX_INCOMPLETE_SHARE = 0.05
MAX_MISSING_RUN = 3
MIN_ACCEPTED_EVENTS = 400
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
SLOT_HOURS = (0, 8, 16)
EIGHT_HOURS_MS = 8 * 60 * 60 * 1000
TIMEBOX = {
    "difficulty": "MEDIUM",
    "start_utc": "2026-11-27T04:37:33Z",
    "max_substantive_cycles": 4,
    "implementation_deadline_utc": "2026-11-30T04:37:33Z",
    "final_conclusion_deadline_utc": "2026-12-02T04:37:33Z",
}


def utc_ms(value: dt.datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("UTC timestamp must be timezone-aware")
    return int(value.astimezone(dt.timezone.utc).timestamp() * 1000)


def boundary_times() -> tuple[int, int]:
    start = dt.datetime.combine(START_DATE, dt.time(), tzinfo=dt.timezone.utc) - dt.timedelta(hours=8)
    end = dt.datetime.combine(END_DATE + dt.timedelta(days=1), dt.time(), tzinfo=dt.timezone.utc)
    return utc_ms(start), utc_ms(end)


def parse_binance_funding_page(body: bytes, cursor_ms: int, end_ms: int) -> list[dict]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Binance funding response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, list) or len(payload) > PAGE_SIZE:
        raise ValueError("Binance funding response must be a bounded JSON array")
    parsed = []
    previous = None
    for index, row in enumerate(payload):
        if not isinstance(row, dict) or row.get("symbol") != "BTCUSDT":
            raise ValueError(f"Binance funding row {index} has an unexpected symbol or shape")
        try:
            stamp_ms = int(row.get("fundingTime"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Binance funding row {index} lacks a millisecond fundingTime") from exc
        rate = base.parse_float(row.get("fundingRate"))
        if stamp_ms < 1_500_000_000_000 or rate is None:
            raise ValueError(f"Binance funding row {index} has an invalid timestamp or non-finite rate")
        if stamp_ms < cursor_ms or stamp_ms > end_ms:
            raise ValueError(f"Binance funding row {index} lies outside the requested inclusive window")
        stamp = dt.datetime.fromtimestamp(stamp_ms / 1000.0, dt.timezone.utc)
        if stamp.minute or stamp.second or stamp.microsecond or stamp.hour not in SLOT_HOURS:
            raise ValueError(
                "Binance funding settlement is off the frozen 00:00/08:00/16:00 UTC grid: "
                + stamp.isoformat()
            )
        if previous is not None and stamp_ms <= previous:
            raise ValueError("Binance funding page is not strictly ascending or contains duplicates")
        previous = stamp_ms
        parsed.append({
            "symbol": "BTCUSDT",
            "funding_rate": float(rate),
            "settle_time_ms": stamp_ms,
            "settle_time_utc": stamp.isoformat(),
            "settle_date": stamp.date(),
            "settle_hour": stamp.hour,
        })
    return parsed


def validate_eight_hour_history(rows: list[dict], source_name: str) -> dict:
    if not rows:
        raise ValueError(f"{source_name} funding history is empty")
    start_ms, end_ms = boundary_times()
    times = [int(row["settle_time_ms"]) for row in rows]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ValueError(f"{source_name} funding timestamps are not unique and ascending")
    if times[0] != start_ms or times[-1] != end_ms:
        raise ValueError(
            f"{source_name} funding boundary mismatch: "
            f"first={times[0]}, expected_first={start_ms}, last={times[-1]}, expected_last={end_ms}"
        )
    for row in rows:
        stamp = dt.datetime.fromtimestamp(int(row["settle_time_ms"]) / 1000.0, dt.timezone.utc)
        if stamp.minute or stamp.second or stamp.microsecond or stamp.hour not in SLOT_HOURS:
            raise ValueError(f"{source_name} funding timestamp is off the common 8-hour grid: {stamp.isoformat()}")
        if source_name == "MEXC" and row.get("collect_cycle_hours") != 8:
            raise ValueError("MEXC funding history contains a non-eight-hour collectCycle")
    for previous, current in zip(times, times[1:]):
        delta = current - previous
        if delta <= 0 or delta % EIGHT_HOURS_MS:
            raise ValueError(
                f"{source_name} funding history contains a non-eight-hour cadence interval: {delta} ms"
            )
    return {
        "rows_in_boundary_window": len(rows),
        "first_settlement_utc": dt.datetime.fromtimestamp(times[0] / 1000.0, dt.timezone.utc).isoformat(),
        "last_settlement_utc": dt.datetime.fromtimestamp(times[-1] / 1000.0, dt.timezone.utc).isoformat(),
        "non_eight_hour_intervals": 0,
        "missing_eight_hour_intervals": sum(
            max(0, (current - previous) // EIGHT_HOURS_MS - 1)
            for previous, current in zip(times, times[1:])
        ),
    }


def fetch_binance_funding_history() -> tuple[list[dict], dict]:
    start_ms, end_ms = boundary_times()
    cursor_ms = start_ms
    all_rows = []
    page_manifest = []
    for page in range(1, MAX_PAGES + 1):
        url = BINANCE_FUNDING_URL + "?" + urllib.parse.urlencode({
            "symbol": "BTCUSDT",
            "startTime": cursor_ms,
            "endTime": end_ms,
            "limit": PAGE_SIZE,
        })
        body = base.fetch_bytes(url, timeout=25)
        rows = parse_binance_funding_page(body, cursor_ms, end_ms)
        page_manifest.append({
            "page": page,
            "url": url,
            "response_sha256": hashlib.sha256(body).hexdigest(),
            "returned_rows": len(rows),
            "first_settlement_utc": rows[0]["settle_time_utc"] if rows else None,
            "last_settlement_utc": rows[-1]["settle_time_utc"] if rows else None,
        })
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE or rows[-1]["settle_time_ms"] >= end_ms:
            break
        next_cursor = rows[-1]["settle_time_ms"] + 1
        if next_cursor <= cursor_ms:
            raise ValueError("Binance funding pagination cursor did not advance")
        cursor_ms = next_cursor
    else:
        raise ValueError(f"Binance funding pagination exceeded {MAX_PAGES} pages")

    if not all_rows:
        raise ValueError("Binance funding history returned no rows")
    all_rows.sort(key=lambda row: row["settle_time_ms"])
    cadence = validate_eight_hour_history(all_rows, "Binance")
    manifest_payload = json.dumps(page_manifest, sort_keys=True, separators=(",", ":")).encode()
    return all_rows, {
        "endpoint": BINANCE_FUNDING_URL,
        "symbol": "BTCUSDT",
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "requested_start_ms": start_ms,
        "requested_end_ms": end_ms,
        "page_size": PAGE_SIZE,
        "retrieved_pages": page_manifest,
        "retrieved_rows": len(all_rows),
        "page_manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "cadence": cadence,
        "raw_funding_observations_saved": False,
    }


def validate_mexc_history(rows: list[dict]) -> tuple[list[dict], dict]:
    start_ms, end_ms = boundary_times()
    selected = [
        row for row in rows
        if start_ms <= int(row["settle_time_ms"]) <= end_ms
    ]
    coverage = validate_eight_hour_history(selected, "MEXC")
    if any(row.get("symbol") != "BTC_USDT" for row in selected):
        raise ValueError("MEXC funding history contains an unexpected contract symbol")
    return selected, coverage


def _max_missing_run(missing_dates: list[dt.date]) -> int:
    missing = set(missing_dates)
    longest = current = 0
    day = START_DATE
    while day <= END_DATE:
        if day in missing:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
        day += dt.timedelta(days=1)
    return longest


def match_funding_days(mexc_rows: list[dict], binance_rows: list[dict]) -> tuple[dict, dict]:
    expected_slots = set(SLOT_HOURS)
    mexc_by_day: dict[dt.date, dict[int, float]] = {}
    binance_by_day: dict[dt.date, dict[int, float]] = {}
    for row in mexc_rows:
        day = row["settle_date"]
        if START_DATE <= day <= END_DATE:
            slots = mexc_by_day.setdefault(day, {})
            hour = int(row["settle_hour"])
            if hour in slots:
                raise ValueError(f"Duplicate MEXC funding slot on {day} at {hour:02d}:00")
            slots[hour] = float(row["funding_rate"])
    for row in binance_rows:
        day = row["settle_date"]
        if START_DATE <= day <= END_DATE:
            slots = binance_by_day.setdefault(day, {})
            hour = int(row["settle_hour"])
            if hour in slots:
                raise ValueError(f"Duplicate Binance funding slot on {day} at {hour:02d}:00")
            slots[hour] = float(row["funding_rate"])

    complete_mexc = {day for day, slots in mexc_by_day.items() if set(slots) == expected_slots}
    complete_binance = {day for day, slots in binance_by_day.items() if set(slots) == expected_slots}
    matched = {}
    for day in sorted(complete_mexc & complete_binance):
        mexc_slots = mexc_by_day[day]
        binance_slots = binance_by_day[day]
        if set(mexc_slots) != set(binance_slots):
            continue
        spread_bps = math.fsum(
            abs(mexc_slots[hour] - binance_slots[hour]) for hour in SLOT_HOURS
        ) / 3.0 * 10_000.0
        matched[day] = {
            "mexc_rates": dict(sorted(mexc_slots.items())),
            "binance_rates": dict(sorted(binance_slots.items())),
            "mean_abs_funding_spread_bps": spread_bps,
        }

    expected_days = (END_DATE - START_DATE).days + 1
    all_days = {START_DATE + dt.timedelta(days=index) for index in range(expected_days)}
    missing_dates = sorted(all_days - set(matched))
    incomplete_share = len(missing_dates) / expected_days
    max_missing_run = _max_missing_run(missing_dates)
    coverage = {
        "frozen_start_date": START_DATE.isoformat(),
        "frozen_end_date": END_DATE.isoformat(),
        "candidate_utc_days": expected_days,
        "complete_mexc_days": len(complete_mexc),
        "complete_binance_days": len(complete_binance),
        "matched_days": len(matched),
        "incomplete_days": len(missing_dates),
        "incomplete_day_share": incomplete_share,
        "maximum_consecutive_incomplete_days": max_missing_run,
        "first_matched_date": min(matched).isoformat() if matched else None,
        "last_matched_date": max(matched).isoformat() if matched else None,
        "missing_dates": [day.isoformat() for day in missing_dates],
        "matching_rule": "exactly three same-timestamp settlements at 00:00, 08:00 and 16:00 UTC on both venues",
    }
    if len(matched) < MIN_MATCHED_DAYS:
        raise ValueError(f"Matched funding history has only {len(matched)} dates; need {MIN_MATCHED_DAYS}")
    if incomplete_share > MAX_INCOMPLETE_SHARE or max_missing_run > MAX_MISSING_RUN:
        raise ValueError(
            f"Cross-venue funding coverage fails: incomplete_share={incomplete_share:.4%}, "
            f"max_missing_run={max_missing_run}"
        )
    if min(matched) != START_DATE or max(matched) != END_DATE:
        raise ValueError(
            f"Matched funding dates do not span the frozen window: "
            f"{min(matched) if matched else None} to {max(matched) if matched else None}"
        )
    return matched, coverage


def build_events(matched: dict, prices: dict[dt.date, float]) -> tuple[list[dict], dict]:
    expected_price_days = (END_DATE - PRICE_START_DATE).days + 1
    expected_dates = {
        PRICE_START_DATE + dt.timedelta(days=index) for index in range(expected_price_days)
    }
    if set(prices) != expected_dates:
        missing = sorted(expected_dates - set(prices))
        extra = sorted(set(prices) - expected_dates)
        raise ValueError(
            f"Binance Spot price calendar mismatch: missing={len(missing)}, extra={len(extra)}"
        )
    returns = {}
    ordered_dates = sorted(prices)
    for previous, current in zip(ordered_dates, ordered_dates[1:]):
        if (current - previous).days != 1:
            raise ValueError(f"Unexpected Binance Spot date gap: {previous} to {current}")
        previous_close, current_close = float(prices[previous]), float(prices[current])
        if not all(math.isfinite(value) and value > 0 for value in (previous_close, current_close)):
            raise ValueError("Binance Spot close is non-finite or non-positive")
        returns[current] = math.log(current_close / previous_close)

    events = []
    skipped = {"insufficient_prior_history": 0, "missing_next_session": 0}
    for day, row in sorted(matched.items()):
        next_day = day + dt.timedelta(days=1)
        prior_days = [day - dt.timedelta(days=offset) for offset in range(4, -1, -1)]
        if any(value not in returns for value in prior_days):
            skipped["insufficient_prior_history"] += 1
            continue
        if next_day not in returns:
            skipped["missing_next_session"] += 1
            continue
        prior_returns = [returns[value] for value in prior_days]
        next_return = returns[next_day]
        if not all(math.isfinite(value) for value in prior_returns + [next_return]):
            raise ValueError(f"Non-finite return in accepted event around {day}")
        feature = float(row["mean_abs_funding_spread_bps"])
        if not math.isfinite(feature) or feature < 0:
            raise ValueError(f"Invalid cross-venue funding dispersion feature on {day}")
        target = btc.semi_var_pct2([next_return])
        events.append({
            "signal_date": day,
            "target_start_date": next_day,
            "target_end_date": next_day,
            "mean_abs_funding_spread_bps": feature,
            "target_downside_loss_pct2": target,
            "target_log1p": math.log1p(target),
            "pre_downside1_log": math.log1p(btc.semi_var_pct2([prior_returns[-1]])),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior_returns)),
            "pre_rv5_log": math.log1p(btc.total_var_pct2(prior_returns)),
        })
    if not events:
        raise ValueError("No complete cross-venue funding/Spot target events were constructed")
    feature_values = [row["mean_abs_funding_spread_bps"] for row in events]
    return events, {
        "candidate_matched_dates": len(matched),
        "accepted_events": len(events),
        "skipped": skipped,
        "first_signal_date": events[0]["signal_date"].isoformat(),
        "last_signal_date": events[-1]["signal_date"].isoformat(),
        "feature_definition": "mean absolute matched MEXC-minus-Binance funding-rate difference across three 8-hour settlements, multiplied by 10000",
        "feature_min_bps": min(feature_values),
        "feature_median_bps": statistics.median(feature_values),
        "feature_max_bps": max(feature_values),
        "target_rule": "max(-next Binance BTCUSDT Spot UTC daily log return, 0)^2 * 10000",
        "prior_history_rule": "five complete prior UTC daily returns; no filling",
    }


def run_source_preflight() -> dict:
    mexc_rows, mexc_source = mexc.fetch_funding_history()
    mexc_selected, mexc_cadence = validate_mexc_history(mexc_rows)
    binance_rows, binance_source = fetch_binance_funding_history()
    matched, matched_coverage = match_funding_days(mexc_selected, binance_rows)

    original_start = mexc.START_DATE
    try:
        mexc.START_DATE = PRICE_START_DATE
        prices, spot_source = mexc.fetch_binance_prices()
    finally:
        mexc.START_DATE = original_start

    events, event_metadata = build_events(matched, prices)
    if len(events) < MIN_ACCEPTED_EVENTS:
        raise ValueError(f"Only {len(events)} accepted daily events; need {MIN_ACCEPTED_EVENTS}")

    source_manifest = {
        "mexc_funding": mexc_source,
        "mexc_cadence": mexc_cadence,
        "binance_usdm_funding": binance_source,
        "matched_funding_coverage": matched_coverage,
        "binance_spot": spot_source,
        "raw_market_observations_saved": False,
    }
    hash_inputs = {
        "mexc_page_manifest_sha256": mexc_source["page_manifest_sha256"],
        "binance_page_manifest_sha256": binance_source["page_manifest_sha256"],
        "binance_spot_archive_manifest_sha256": spot_source["archive_manifest_sha256"],
        "matched_days": matched_coverage["matched_days"],
        "first_signal_date": event_metadata["first_signal_date"],
        "last_signal_date": event_metadata["last_signal_date"],
    }
    manifest_sha = hashlib.sha256(
        json.dumps(hash_inputs, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "source_preflight_only": True,
        "completed_backtest": False,
        "model_fit_executed": False,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "timebox": TIMEBOX,
        "source_manifest_sha256": manifest_sha,
        "source_manifest": source_manifest,
        "event_construction": event_metadata,
        "accepted_event_count": len(events),
        "raw_observations_saved": False,
    }


def main() -> int:
    result = run_source_preflight()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
