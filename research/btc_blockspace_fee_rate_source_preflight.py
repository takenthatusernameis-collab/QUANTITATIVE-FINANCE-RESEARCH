#!/usr/bin/env python3
"""One-request, read-only Mempool.space block-feerate source feasibility probe."""
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


def parse_fee_rate_payload(body: bytes) -> tuple[dict[dt.date, float], dict]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Mempool fee-rate response is not valid UTF-8 JSON") from exc

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a non-empty per-block JSON array")

    daily_values: dict[dt.date, list[float]] = defaultdict(list)
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
            daily_values[timestamp.date()].append(p75)

    if any(right < left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("Mempool observations are not ordered oldest-to-newest")
    if not daily_values:
        raise ValueError("No usable avgFee_75 observations were returned")

    daily_medians = {
        day: statistics.median(values)
        for day, values in sorted(daily_values.items())
        if values
    }
    first_day, last_day = min(daily_medians), max(daily_medians)
    return daily_medians, {
        "row_count": len(rows),
        "first_timestamp_utc": dt.datetime.fromtimestamp(timestamps[0], dt.timezone.utc).isoformat(),
        "last_timestamp_utc": dt.datetime.fromtimestamp(timestamps[-1], dt.timezone.utc).isoformat(),
        "first_utc_date": first_day.isoformat(),
        "last_utc_date": last_day.isoformat(),
        "unique_utc_dates": len(daily_medians),
        "span_calendar_days_inclusive": (last_day - first_day).days + 1,
        "valid_avgFee_75_rows": len(p75_values),
        "avgFee_75_min_sat_vb": min(p75_values),
        "avgFee_75_median_sat_vb": statistics.median(p75_values),
        "avgFee_75_max_sat_vb": max(p75_values),
        "avgHeight_min": min(heights),
        "avgHeight_max": max(heights),
        "response_schema": sorted(rows[0].keys()),
        "daily_aggregation": "median of per-block avgFee_75 values by UTC date",
    }


def validate_coverage(
    daily_medians: dict[dt.date, float],
    now: dt.datetime,
) -> dict:
    if now.tzinfo is None:
        raise ValueError("Coverage validation requires an offset-aware UTC time")
    now_utc = now.astimezone(dt.timezone.utc)
    first_day, last_day = min(daily_medians), max(daily_medians)
    unique_days = len(daily_medians)
    span_days = (last_day - first_day).days + 1
    lag_days = (now_utc.date() - last_day).days

    if unique_days < MIN_UNIQUE_UTC_DAYS:
        raise ValueError(
            f"Insufficient unique UTC dates: {unique_days} < {MIN_UNIQUE_UTC_DAYS}"
        )
    if span_days < MIN_SPAN_DAYS:
        raise ValueError(f"Insufficient calendar span: {span_days} < {MIN_SPAN_DAYS}")
    if lag_days < 0:
        raise ValueError(f"Future-dated fee-rate observations: latest={last_day}")
    if lag_days > MAX_PUBLICATION_LAG_DAYS:
        raise ValueError(
            f"Fee-rate source is stale by {lag_days} days; maximum is {MAX_PUBLICATION_LAG_DAYS}"
        )

    return {
        "first_utc_date": first_day.isoformat(),
        "last_utc_date": last_day.isoformat(),
        "unique_utc_dates": unique_days,
        "span_calendar_days_inclusive": span_days,
        "publication_lag_calendar_days": lag_days,
        "minimum_unique_utc_dates": MIN_UNIQUE_UTC_DAYS,
        "minimum_span_calendar_days": MIN_SPAN_DAYS,
        "maximum_publication_lag_days": MAX_PUBLICATION_LAG_DAYS,
        "missing_utc_dates_not_interpolated": True,
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
    daily_medians, source_summary = parse_fee_rate_payload(body)
    coverage = validate_coverage(daily_medians, retrieved_at)
    total_days = sorted(daily_medians)
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
            "daily median of per-block avgFee_75 (sat/vB), then "
            "log1p(value[t-1]) - log1p(value[t-8]); one full UTC-day embargo"
        ),
        "first_daily_value": {"date": total_days[0].isoformat(), "avgFee_75_median_sat_vb": daily_medians[total_days[0]]},
        "last_daily_value": {"date": total_days[-1].isoformat(), "avgFee_75_median_sat_vb": daily_medians[total_days[-1]]},
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
