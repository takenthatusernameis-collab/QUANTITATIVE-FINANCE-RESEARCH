#!/usr/bin/env python3
"""One-request, read-only Mempool.space 12-hour-bin source feasibility probe."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import statistics
import urllib.error
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01"
ENDPOINT = "https://mempool.space/api/v1/mining/blocks/fee-rates/3y"
REQUIRED_FIELDS = {
    "timestamp", "avgFee_0", "avgFee_10", "avgFee_25", "avgFee_50",
    "avgFee_75", "avgFee_90", "avgFee_100", "avgHeight",
}
EXPECTED_HALF_DAY_BINS = 2
MIN_UNIQUE_UTC_DAYS = 900
MIN_SPAN_DAYS = 900
MAX_PUBLICATION_LAG_DAYS = 3
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
OUTPUT_DIR = ROOT / "reports" / "generated" / "btc-blockspace-fee-rate-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"


def _utc_timestamp(value: object, row_number: int) -> dt.datetime:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        if isinstance(value, str):
            try:
                parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"Invalid timestamp at row {row_number}") from exc
            if parsed.tzinfo is None:
                raise ValueError(f"Naive timestamp at row {row_number}")
            return parsed.astimezone(dt.timezone.utc)
        raise ValueError(f"Invalid timestamp at row {row_number}")
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"Invalid Unix timestamp at row {row_number}")
    if numeric >= 1_000_000_000_000:
        numeric /= 1_000.0
    if numeric < 1_000_000_000 or numeric >= 100_000_000_000:
        raise ValueError(f"Unsupported Unix timestamp magnitude at row {row_number}")
    return dt.datetime.fromtimestamp(numeric, dt.timezone.utc)


def _finite_nonnegative(value: object, field: str, row_number: int) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field} at row {row_number}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid nonnegative finite {field} at row {row_number}")
    return number


def parse_fee_rate_payload(body: bytes) -> tuple[dict[dt.date, list[tuple[dt.datetime, float]]], dict]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Mempool fee-rate response is not valid UTF-8 JSON") from exc

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a non-empty 12-hour-bin JSON array")

    daily_bins: dict[dt.date, list[tuple[dt.datetime, float]]] = defaultdict(list)
    timestamps: list[int] = []
    p75_values: list[float] = []
    heights: list[float] = []

    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Expected object row {row_number}; found {type(row).__name__}")
        missing = REQUIRED_FIELDS.difference(row)
        if missing:
            raise ValueError(
                f"Unexpected fee-rate schema at row {row_number}; missing={sorted(missing)}"
            )

        timestamp = _utc_timestamp(row["timestamp"], row_number)
        p75 = _finite_nonnegative(row["avgFee_75"], "avgFee_75", row_number)
        try:
            height = float(row["avgHeight"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid avgHeight at row {row_number}") from exc
        if not math.isfinite(height) or height <= 0:
            raise ValueError(f"Invalid avgHeight at row {row_number}")

        epoch = int(timestamp.timestamp())
        timestamps.append(epoch)
        heights.append(height)
        if p75 is not None:
            p75_values.append(p75)
            daily_bins[timestamp.date()].append((timestamp, p75))

    if any(right < left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("Mempool observations are not ordered oldest-to-newest")
    if not daily_bins:
        raise ValueError("No usable avgFee_75 observations were returned")

    raw_dates = sorted(daily_bins)
    bin_counts = [len(daily_bins[day]) for day in raw_dates]
    return daily_bins, {
        "row_count": len(rows),
        "first_timestamp_utc": dt.datetime.fromtimestamp(timestamps[0], dt.timezone.utc).isoformat(),
        "last_timestamp_utc": dt.datetime.fromtimestamp(timestamps[-1], dt.timezone.utc).isoformat(),
        "raw_first_utc_date": raw_dates[0].isoformat(),
        "raw_last_utc_date": raw_dates[-1].isoformat(),
        "raw_unique_utc_dates": len(raw_dates),
        "raw_bin_count_min": min(bin_counts),
        "raw_bin_count_max": max(bin_counts),
        "valid_avgFee_75_rows": len(p75_values),
        "avgFee_75_min_sat_vb": min(p75_values),
        "avgFee_75_median_sat_vb": statistics.median(p75_values),
        "avgFee_75_max_sat_vb": max(p75_values),
        "avgHeight_min": min(heights),
        "avgHeight_max": max(heights),
        "response_schema": sorted(rows[0].keys()),
        "source_bucket_seconds": 43_200,
        "daily_aggregation": (
            "median of the two 12-hour-bin avgFee_75 averages by UTC date; "
            "each bin avgFee_75 is the mean of underlying block p75 values"
        ),
    }


def validate_coverage(
    daily_bins: dict[dt.date, list[tuple[dt.datetime, float]]],
    now: dt.datetime,
) -> tuple[dict[dt.date, float], dict]:
    if now.tzinfo is None:
        raise ValueError("Coverage validation requires an offset-aware UTC time")
    now_utc = now.astimezone(dt.timezone.utc)
    raw_dates = sorted(daily_bins)
    if len(raw_dates) < 3:
        raise ValueError("Insufficient raw UTC dates to exclude partial window boundaries")

    first_boundary, last_boundary = raw_dates[0], raw_dates[-1]
    completed_dates = raw_dates[1:-1]
    completed_daily: dict[dt.date, float] = {}

    for day in completed_dates:
        entries = daily_bins[day]
        if len(entries) != EXPECTED_HALF_DAY_BINS:
            raise ValueError(
                f"UTC date {day} has {len(entries)} 12-hour bins; expected {EXPECTED_HALF_DAY_BINS}"
            )
        halves = sorted(0 if timestamp.hour < 12 else 1 for timestamp, _ in entries)
        if halves != [0, 1]:
            raise ValueError(
                f"UTC date {day} does not contain one 00:00-11:59 and one 12:00-23:59 bin"
            )
        completed_daily[day] = statistics.median(value for _, value in entries)

    if not completed_daily:
        raise ValueError("No complete UTC dates remain after excluding partial boundaries")

    completed_dates_sorted = sorted(completed_daily)
    first_day, last_day = completed_dates_sorted[0], completed_dates_sorted[-1]
    unique_days = len(completed_dates_sorted)
    span_days = (last_day - first_day).days + 1
    if unique_days != span_days:
        raise ValueError("Missing UTC dates remain inside the completed source window")
    if unique_days < MIN_UNIQUE_UTC_DAYS:
        raise ValueError(
            f"Insufficient completed UTC dates: {unique_days} < {MIN_UNIQUE_UTC_DAYS}"
        )
    if span_days < MIN_SPAN_DAYS:
        raise ValueError(f"Insufficient completed calendar span: {span_days} < {MIN_SPAN_DAYS}")

    lag_days = (now_utc.date() - last_day).days
    if lag_days < 1:
        raise ValueError("Latest included date is not a completed UTC date")
    if lag_days > MAX_PUBLICATION_LAG_DAYS:
        raise ValueError(
            f"Completed fee-rate source is stale by {lag_days} days; maximum is {MAX_PUBLICATION_LAG_DAYS}"
        )

    return completed_daily, {
        "first_utc_date": first_day.isoformat(),
        "last_utc_date": last_day.isoformat(),
        "unique_utc_dates": unique_days,
        "span_calendar_days_inclusive": span_days,
        "publication_lag_calendar_days": lag_days,
        "minimum_unique_utc_dates": MIN_UNIQUE_UTC_DAYS,
        "minimum_span_calendar_days": MIN_SPAN_DAYS,
        "maximum_publication_lag_days": MAX_PUBLICATION_LAG_DAYS,
        "expected_12h_bins_per_complete_date": EXPECTED_HALF_DAY_BINS,
        "boundary_dates_excluded": [first_boundary.isoformat(), last_boundary.isoformat()],
        "missing_utc_dates_not_interpolated": True,
        "partial_current_utc_date_excluded": last_boundary == now_utc.date(),
    }


def fetch_fee_rate_payload() -> tuple[bytes, int, str, dict]:
    request = Request(
        ENDPOINT,
        headers={
            "Accept": "application/json",
            "User-Agent": "QUANTITATIVE-FINANCE-RESEARCH/1.0 (read-only source feasibility)",
        },
        method="GET",
    )
    try:
        response = urlopen(request, timeout=45)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RuntimeError("Mempool API returned HTTP 429; no retry was attempted") from exc
        if exc.code == 402:
            raise RuntimeError("Mempool API requires payment; no payment was attempted") from exc
        raise RuntimeError(f"Mempool API returned HTTP {exc.code}; no retry was attempted") from exc
    except Exception as exc:
        raise RuntimeError(f"Mempool API request failed; no retry was attempted: {exc}") from exc

    with response:
        status = getattr(response, "status", 200)
        final_url = response.geturl()
        headers = dict(response.headers.items())
        body = response.read()

    if status != 200:
        raise RuntimeError(f"Mempool API returned HTTP {status}; no retry was attempted")
    if final_url.rstrip("/") != ENDPOINT.rstrip("/"):
        raise RuntimeError(f"Mempool API redirected to an unapproved URL: {final_url}")
    return body, status, final_url, headers


def run_preflight(
    fetcher=fetch_fee_rate_payload,
    now: dt.datetime | None = None,
) -> dict:
    retrieved_at = now or dt.datetime.now(dt.timezone.utc)
    body, status, final_url, headers = fetcher()
    daily_bins, source_summary = parse_fee_rate_payload(body)
    completed_daily, coverage = validate_coverage(daily_bins, retrieved_at)
    total_days = sorted(completed_daily)
    source_summary["completed_unique_utc_dates"] = len(completed_daily)
    source_summary["completed_first_utc_date"] = total_days[0].isoformat()
    source_summary["completed_last_utc_date"] = total_days[-1].isoformat()
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": retrieved_at.astimezone(dt.timezone.utc).isoformat(),
        "source": "Mempool Open Source Project REST API",
        "endpoint": ENDPOINT,
        "http_status": status,
        "final_url": final_url,
        "api_requests": 1,
        "retry_count": 0,
        "payment_attempted": False,
        "rate_limit_header": headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining"),
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "response_bytes": len(body),
        "source_summary": source_summary,
        "coverage": coverage,
        "feature_definition": (
            "daily median of two 12-hour-bin avgFee_75 averages (sat/vB), then "
            "log1p(value[t-1]) - log1p(value[t-8]); one full UTC-day embargo"
        ),
        "first_daily_value": {
            "date": total_days[0].isoformat(),
            "avgFee_75_median_sat_vb": completed_daily[total_days[0]],
        },
        "last_daily_value": {
            "date": total_days[-1].isoformat(),
            "avgFee_75_median_sat_vb": completed_daily[total_days[-1]],
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
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": "Mempool Open Source Project REST API",
            "endpoint": ENDPOINT,
            "api_requests": 1,
            "retry_count": 0,
            "payment_attempted": False,
            "raw_observations_saved": False,
            "backtest_run": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "preflight.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("# Bitcoin blockspace fee-rate source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: `{HYPOTHESIS_ID}`\n")
            handle.write("- Backtest executed: **No**\n")
            handle.write("- API requests / retries: **1 / 0**\n\n")
            handle.write(rendered + "\n")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
