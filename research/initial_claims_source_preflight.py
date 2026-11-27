#!/usr/bin/env python3
"""Read-only source feasibility check for weekly U.S. initial claims and BTC Spot."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 19)
SAMPLE_BTC_DATE = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=4)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = "ICSA"
BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
MIN_ROWS = 450
MAX_AGE_DAYS = 14
USER_AGENT = "QFR-Research/1.0 (public academic research; github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
NOW = dt.datetime.now(dt.timezone.utc)


def build_fred_url(start: dt.date = START_DATE) -> str:
    return FRED_URL + "?" + "id=ICSA&cosd=" + start.isoformat()


def parse_icsa(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or "ICSA" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED ICSA schema: {reader.fieldnames}")
    date_col = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_col is None:
        raise ValueError("FRED ICSA CSV has no recognized observation-date column")
    values: dict[dt.date, float] = {}
    for row_number, row in enumerate(reader, start=2):
        day = base.parse_date(row.get(date_col))
        if day is None:
            raise ValueError(f"Invalid ICSA observation date on row {row_number}")
        value = base.parse_float(row.get("ICSA"))
        if value is None:
            continue
        if value <= 0:
            raise ValueError(f"Non-positive ICSA value on {day}")
        if day in values:
            raise ValueError(f"Duplicate ICSA observation date: {day}")
        values[day] = value
    if not values:
        raise ValueError("FRED ICSA returned no numeric observations")
    return dict(sorted(values.items()))


def validate_icsa_coverage(
    values: dict[dt.date, float],
    as_of_date: dt.date,
    min_rows: int = MIN_ROWS,
) -> dict:
    if len(values) < min_rows:
        raise ValueError(f"Insufficient ICSA observations: {len(values)} < {min_rows}")
    dates = sorted(values)
    if dates[0] > START_DATE + dt.timedelta(days=14):
        raise ValueError(f"ICSA history starts too late: {dates[0]}")
    if dates[-1] > as_of_date:
        raise ValueError("ICSA contains a future-dated observation")
    age = (as_of_date - dates[-1]).days
    if age > MAX_AGE_DAYS:
        raise ValueError(f"ICSA is stale: latest={dates[-1]}, age_days={age}")
    weekdays = {day.weekday() for day in dates}
    if len(weekdays) != 1:
        raise ValueError(f"ICSA observation weekday is inconsistent: {sorted(weekdays)}")
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    if any(gap not in (7, 14) for gap in gaps):
        raise ValueError("ICSA has a non-weekly gap other than an isolated 14-day omission")
    regular_windows = sum(
        all((right - left).days == 7 for left, right in zip(dates[i - 4:i + 1], dates[i - 3:i + 1]))
        for i in range(4, len(dates))
    )
    if regular_windows < 400:
        raise ValueError(f"Too few complete five-observation weekly windows: {regular_windows}")
    return {
        "rows": len(dates),
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "weekday_utc": dates[0].strftime("%A"),
        "latest_age_days": age,
        "max_gap_days": max(gaps, default=0),
        "complete_five_observation_windows": regular_windows,
        "units": "persons, seasonally adjusted",
        "frequency": "weekly",
        "vintage": "current FRED vintage; historical ALFRED vintages not reconstructed",
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
    fred_url = build_fred_url()
    fred_body = base.fetch_bytes(fred_url, timeout=25)
    claims = parse_icsa(fred_body)
    claims_coverage = validate_icsa_coverage(claims, NOW.date())

    exchange_url = BINANCE_EXCHANGE_INFO + "?symbol=BTCUSDT"
    exchange_body = base.fetch_bytes(exchange_url, timeout=20)
    market = validate_binance_exchange_info(exchange_body)

    specs = btc.build_archive_specs(SAMPLE_BTC_DATE, SAMPLE_BTC_DATE, as_of_date=NOW.date())
    if len(specs) != 1 or specs[0].get("kind") != "daily":
        raise ValueError(f"Expected one daily BTC archive for sample date {SAMPLE_BTC_DATE}: {specs}")
    prices, archive_row = btc.download_binance_archive(specs[0])
    if set(prices) != {SAMPLE_BTC_DATE}:
        raise ValueError(f"BTC sample archive does not contain exactly {SAMPLE_BTC_DATE}: {sorted(prices)}")

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": NOW.isoformat(),
        "fred_icsa": {
            "url": fred_url,
            "response_sha256": hashlib.sha256(fred_body).hexdigest(),
            **claims_coverage,
        },
        "binance_market": {
            "url": exchange_url,
            "response_sha256": hashlib.sha256(exchange_body).hexdigest(),
            **market,
        },
        "binance_archive_sample": {
            "sample_date": SAMPLE_BTC_DATE.isoformat(),
            **archive_row,
        },
        "frozen_model_preview": {
            "feature": "100 * ln(ICSA[w] / ICSA[w-4])",
            "availability_rule": "signal at weekly observation date + 7 calendar days",
            "target": "next five complete BTCUSDT UTC daily returns",
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
    output_dir = ROOT / "reports" / "generated" / "initial-claims-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "preflight.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## U.S. initial-claims source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: `{HYPOTHESIS_ID}`\n")
            handle.write("- Backtest executed: **No**\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
