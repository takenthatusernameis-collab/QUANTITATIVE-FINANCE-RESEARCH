#!/usr/bin/env python3
"""Preregistered forecast screen: prior-day MEXC BTC perpetual funding -> next-day BTC Spot downside loss."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import urllib.parse
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-26-MEXC-BTC-FUNDING-DOWNSIDE-01"
SYMBOL = "BTC_USDT"
START_DATE = dt.date(2025, 6, 15)
END_DATE = dt.date(2026, 11, 23)
PAGE_SIZE = 1000
MAX_PAGES = 10
MIN_FUNDING_ROWS = 1200
MIN_COMPLETE_DAYS = 400
MAX_INCOMPLETE_SHARE = 0.05
MAX_MISSING_RUN = 3
MIN_PRICE_ROWS = 500
MODEL_WINDOW = 104
VALIDATION_START = dt.date(2025, 10, 1)
TEST_START = dt.date(2026, 3, 1)
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 7, 20261126

TIMEBOX = {
    "difficulty": "MEDIUM",
    "start_utc": "2026-11-26T15:15:00Z",
    "max_substantive_cycles": 4,
    "implementation_deadline_utc": "2026-11-29T15:15:00Z",
    "final_conclusion_deadline_utc": "2026-12-01T15:15:00Z",
}

MEXC_HISTORY_URL = "https://contract.mexc.com/api/v1/contract/funding_rate/history"
BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "mexc-btc-funding-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-MEXC-BTC-FUNDING-DOWNSIDE-01.md"
BASE_FEATURES = ["pre_downside1_log", "pre_downside5_log", "pre_rv5_log"]
AUG_FEATURES = BASE_FEATURES + ["funding_24h_sum"]


def parse_funding_page(body: bytes, expected_page: int) -> tuple[dict, list[dict]]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"MEXC page {expected_page} is not valid UTF-8 JSON") from exc
    if payload.get("success") is not True or str(payload.get("code")) != "0":
        raise ValueError(f"MEXC funding API did not return success on page {expected_page}: {payload}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"MEXC funding page {expected_page} has no object data envelope")
    try:
        current_page = int(data.get("currentPage"))
        total_count = int(data.get("totalCount"))
        total_pages = int(data.get("totalPage"))
        page_size = int(data.get("pageSize"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"MEXC funding page {expected_page} has invalid pagination metadata") from exc
    rows = data.get("resultList")
    if current_page != expected_page or not isinstance(rows, list):
        raise ValueError(f"MEXC funding page progression mismatch: requested={expected_page}, returned={current_page}")
    if total_count < 1 or total_pages < 1 or total_pages > MAX_PAGES or not (1 <= page_size <= PAGE_SIZE):
        raise ValueError(f"MEXC funding pagination is outside the frozen bounds: {data}")
    if len(rows) > PAGE_SIZE or len(rows) == 0:
        raise ValueError(f"MEXC funding page {expected_page} has an invalid row count: {len(rows)}")
    parsed = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("symbol") != SYMBOL:
            raise ValueError(f"MEXC page {expected_page} row {index} has an unexpected symbol or shape")
        try:
            cycle = int(row.get("collectCycle"))
            settle_ms = int(row.get("settleTime"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"MEXC page {expected_page} row {index} lacks cycle or millisecond settlement time") from exc
        rate = base.parse_float(row.get("fundingRate"))
        if cycle != 8 or rate is None or settle_ms <= 0:
            raise ValueError(f"MEXC page {expected_page} row {index} violates the frozen 8-hour funding schema")
        stamp = dt.datetime.fromtimestamp(settle_ms / 1000.0, dt.timezone.utc)
        if stamp.minute or stamp.second or stamp.microsecond or stamp.hour not in (0, 8, 16):
            raise ValueError(f"MEXC settlement is not aligned to 00:00/08:00/16:00 UTC: {stamp.isoformat()}")
        parsed.append({
            "symbol": SYMBOL,
            "funding_rate": float(rate),
            "settle_time_ms": settle_ms,
            "settle_time_utc": stamp.isoformat(),
            "settle_date": stamp.date(),
            "settle_hour": stamp.hour,
            "collect_cycle_hours": cycle,
        })
    return {
        "current_page": current_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "page_size": page_size,
        "returned_rows": len(rows),
    }, parsed


def fetch_funding_history() -> tuple[list[dict], dict]:
    all_rows = []
    page_manifest = []
    frozen_meta = None
    for page in range(1, MAX_PAGES + 1):
        url = MEXC_HISTORY_URL + "?" + urllib.parse.urlencode({
            "symbol": SYMBOL, "page_num": page, "page_size": PAGE_SIZE,
        })
        body = base.fetch_bytes(url, timeout=25)
        meta, rows = parse_funding_page(body, page)
        if frozen_meta is None:
            frozen_meta = meta
            if frozen_meta["total_pages"] != math.ceil(frozen_meta["total_count"] / PAGE_SIZE):
                raise ValueError(f"MEXC totalPage is inconsistent with totalCount/page_size: {frozen_meta}")
        elif (meta["total_count"], meta["total_pages"]) != (frozen_meta["total_count"], frozen_meta["total_pages"]):
            raise ValueError("MEXC totalCount/totalPage changed during pagination")
        all_rows.extend(rows)
        page_manifest.append({
            "page": page,
            "url": url,
            "response_sha256": hashlib.sha256(body).hexdigest(),
            "returned_rows": len(rows),
            "first_settlement_utc": rows[0]["settle_time_utc"],
            "last_settlement_utc": rows[-1]["settle_time_utc"],
        })
        if page == frozen_meta["total_pages"]:
            break
    if frozen_meta is None:
        raise ValueError("MEXC funding history returned no pages")
    if len(page_manifest) != frozen_meta["total_pages"] or len(all_rows) != frozen_meta["total_count"]:
        raise ValueError(
            f"MEXC pagination incomplete: pages={len(page_manifest)}/{frozen_meta['total_pages']}, "
            f"rows={len(all_rows)}/{frozen_meta['total_count']}"
        )
    all_rows.sort(key=lambda row: row["settle_time_ms"])
    seen = set()
    for row in all_rows:
        if row["settle_time_ms"] in seen:
            raise ValueError(f"Duplicate MEXC funding settlement: {row['settle_time_utc']}")
        seen.add(row["settle_time_ms"])
        if row["settle_time_utc"] > NOW.isoformat():
            raise ValueError("MEXC funding source contains a future settlement")
    manifest_sha = hashlib.sha256(
        json.dumps(page_manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return all_rows, {
        "endpoint": MEXC_HISTORY_URL,
        "symbol": SYMBOL,
        "retrieved_at_utc": NOW.isoformat(),
        "requested_page_size": PAGE_SIZE,
        "reported_total_count": frozen_meta["total_count"],
        "reported_total_pages": frozen_meta["total_pages"],
        "retrieved_pages": page_manifest,
        "page_manifest_sha256": manifest_sha,
        "retrieved_rows": len(all_rows),
        "first_settlement_utc": all_rows[0]["settle_time_utc"],
        "last_settlement_utc": all_rows[-1]["settle_time_utc"],
        "collect_cycle_hours": 8,
        "raw_funding_observations_committed": False,
    }


def aggregate_complete_funding_days(rows: list[dict]) -> tuple[dict[dt.date, float], dict]:
    slots: dict[dt.date, dict[int, float]] = {}
    in_window = [
        row for row in rows
        if START_DATE <= row["settle_date"] <= END_DATE
    ]
    for row in in_window:
        day = row["settle_date"]
        hour = row["settle_hour"]
        if hour in slots.setdefault(day, {}):
            raise ValueError(f"Duplicate UTC funding slot on {day} at {hour:02d}:00")
        slots[day][hour] = row["funding_rate"]
    expected = {0, 8, 16}
    complete = {
        day: math.fsum(values[hour] for hour in (0, 8, 16))
        for day, values in slots.items()
        if set(values) == expected
    }
    candidate_days = (END_DATE - START_DATE).days + 1
    incomplete = candidate_days - len(complete)
    incomplete_share = incomplete / candidate_days
    missing_run = 0
    max_missing_run = 0
    day = START_DATE
    while day <= END_DATE:
        if day in complete:
            missing_run = 0
        else:
            missing_run += 1
            max_missing_run = max(max_missing_run, missing_run)
        day += dt.timedelta(days=1)
    if len(in_window) < MIN_FUNDING_ROWS:
        raise ValueError(f"MEXC has only {len(in_window)} funding settlements in the frozen window; need {MIN_FUNDING_ROWS}")
    if len(complete) < MIN_COMPLETE_DAYS:
        raise ValueError(f"MEXC has only {len(complete)} complete funding dates; need {MIN_COMPLETE_DAYS}")
    if incomplete_share > MAX_INCOMPLETE_SHARE or max_missing_run > MAX_MISSING_RUN:
        raise ValueError(
            f"MEXC funding coverage fails: incomplete_share={incomplete_share:.4%}, "
            f"max_missing_run={max_missing_run}"
        )
    first_complete, last_complete = min(complete), max(complete)
    if first_complete > START_DATE or last_complete < END_DATE:
        raise ValueError(
            f"MEXC complete funding dates do not span the frozen window: "
            f"{first_complete} to {last_complete}"
        )
    return dict(sorted(complete.items())), {
        "frozen_start_date": START_DATE.isoformat(),
        "frozen_end_date": END_DATE.isoformat(),
        "candidate_utc_days": candidate_days,
        "complete_utc_days": len(complete),
        "incomplete_utc_days": incomplete,
        "incomplete_day_share": incomplete_share,
        "maximum_consecutive_missing_days": max_missing_run,
        "settlements_in_window": len(in_window),
        "first_complete_date": first_complete.isoformat(),
        "last_complete_date": last_complete.isoformat(),
        "complete_day_rule": "exactly three settlements at 00:00, 08:00 and 16:00 UTC, each collectCycle=8",
    }


def fetch_binance_prices() -> tuple[dict[dt.date, float], dict]:
    info_url = BINANCE_EXCHANGE_INFO + "?" + urllib.parse.urlencode({"symbol": "BTCUSDT"})
    info_body = base.fetch_bytes(info_url, timeout=15)
    symbols = json.loads(info_body.decode("utf-8")).get("symbols", [])
    if len(symbols) != 1:
        raise ValueError("Binance exchangeInfo did not return exactly BTCUSDT")
    info = symbols[0]
    if (info.get("symbol"), info.get("status"), info.get("baseAsset"), info.get("quoteAsset")) != (
        "BTCUSDT", "TRADING", "BTC", "USDT"
    ):
        raise ValueError(f"BTCUSDT is not an active Binance Spot USDT market: {info}")
    specs = btc.build_archive_specs(START_DATE, END_DATE, as_of_date=NOW.date())
    results, failures = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=btc.ARCHIVE_WORKERS) as executor:
        futures = {
            executor.submit(btc.download_binance_archive, spec): (index, spec)
            for index, spec in enumerate(specs)
        }
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({
                    "kind": spec["kind"], "period": spec["tag"], "url": spec["url"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda row: (row["kind"], row["period"]))
        raise RuntimeError(
            f"Binance Vision ingestion failed for {len(failures)}/{len(specs)} archives: "
            f"{json.dumps(failures, sort_keys=True)}"
        )
    prices, archive_manifest, units = {}, [], set()
    for index in range(len(specs)):
        page, manifest_row = results[index]
        archive_manifest.append(manifest_row)
        units.add(manifest_row["timestamp_unit"])
        for day, close in page.items():
            if START_DATE <= day <= END_DATE:
                if day in prices:
                    raise ValueError(f"Duplicate Binance Spot daily candle: {day}")
                prices[day] = close
    prices = dict(sorted(prices.items()))
    expected_dates = []
    day = START_DATE
    while day <= END_DATE:
        expected_dates.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected_dates if day not in prices]
    if missing:
        raise ValueError(
            f"Binance Spot archive has {len(missing)} missing UTC dates; "
            f"first_missing={missing[0]}, last_missing={missing[-1]}"
        )
    if len(prices) < MIN_PRICE_ROWS or min(prices) != START_DATE or max(prices) != END_DATE:
        raise ValueError(f"Binance Spot price coverage fails: {len(prices)} rows, {min(prices)} to {max(prices)}")
    archive_sha = hashlib.sha256(
        json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return prices, {
        "symbol": "BTCUSDT",
        "venue": "Binance Spot",
        "market_status": info["status"],
        "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
        "interval": "1d",
        "timezone": "UTC",
        "rows": len(prices),
        "first_date": min(prices).isoformat(),
        "last_date": max(prices).isoformat(),
        "timestamp_units_observed": sorted(units),
        "archive_manifest_sha256": archive_sha,
        "archives": archive_manifest,
        "exchange_info_response_sha256": hashlib.sha256(info_body).hexdigest(),
        "incomplete_current_candle_excluded": True,
    }


def build_events(funding_daily: dict[dt.date, float], prices: dict[dt.date, float]) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns: dict[dt.date, float] = {}
    for previous, current in zip(dates, dates[1:]):
        if (current - previous).days != 1:
            raise ValueError(f"Unexpected Binance Spot date gap: {previous} to {current}")
        returns[current] = math.log(prices[current] / prices[previous])
    events, skipped = [], {
        "missing_signal_close": 0,
        "insufficient_price_history": 0,
        "missing_next_close": 0,
        "invalid_return_window": 0,
    }
    for day, funding_sum in sorted(funding_daily.items()):
        if day not in prices:
            skipped["missing_signal_close"] += 1
            continue
        next_day = day + dt.timedelta(days=1)
        if next_day not in prices:
            skipped["missing_next_close"] += 1
            continue
        history_days = [day - dt.timedelta(days=offset) for offset in range(4, -1, -1)]
        if any(value not in returns for value in history_days) or next_day not in returns:
            skipped["insufficient_price_history"] += 1
            continue
        prior5 = [returns[value] for value in history_days]
        prior1 = [returns[day]]
        future = [returns[next_day]]
        if any(not math.isfinite(value) for value in prior5 + future):
            skipped["invalid_return_window"] += 1
            continue
        target_loss = btc.semi_var_pct2(future)
        events.append({
            "signal_date": day,
            "target_start_date": next_day,
            "target_end_date": next_day,
            "funding_24h_sum": funding_sum,
            "target_downside_loss_pct2": target_loss,
            "target_bp": math.log1p(target_loss),
            "pre_downside1_log": math.log1p(btc.semi_var_pct2(prior1)),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior5)),
            "pre_rv5_log": math.log1p(btc.total_var_pct2(prior5)),
        })
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("One-session target windows overlap or are not fully matured")
    return events, {
        "candidate_funding_days": len(funding_daily),
        "accepted_events": len(events),
        "skipped": skipped,
        "signal_rule": "funding settlements at 00:00/08:00/16:00 UTC on day d, observed at the close of Binance Spot daily candle d",
        "target_rule": "next Binance Spot UTC daily close-to-close return only; downside squared loss in percentage-points squared",
        "feature_rule": "simple sum of the three exact 8-hour funding rates on day d; no compounding, scaling or filling",
    }


def walk_forward(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = [
            row for row in events
            if row["signal_date"] < current["signal_date"]
            and row["target_end_date"] < current["signal_date"]
        ][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "record_date": current["signal_date"],
            "signal_date": current["signal_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "target_downside_loss_pct2": current["target_downside_loss_pct2"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "funding_24h_sum": current["funding_24h_sum"],
            "train_n": len(train),
        })
    return predictions


def metrics(rows: list[dict]) -> dict:
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None
    if baseline and augmented and baseline["rmse_bp"] > 0:
        improvement = 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
    return {
        "n": len(rows),
        "baseline": baseline,
        "augmented": augmented,
        "rmse_improvement_pct": improvement,
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < 60 or test["n"] < 120 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient chronological forecast sample or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low_bp2"] > 0:
        return "BACKTESTED", "PROMISING SCREEN — validation and test RMSE both improve and the paired test-loss 95% lower bound is positive; independent validation and instrument-level evaluation remain necessary"
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high_bp2"] < 0:
        return "REJECTED", "REJECTED — validation and test RMSE both worsen and the paired test-loss 95% upper bound is negative"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"


def run_research() -> dict:
    sources = {}
    try:
        funding_rows, funding_source = fetch_funding_history()
        sources["MEXC_BTC_USDT_FUNDING"] = funding_source
        funding_daily, funding_coverage = aggregate_complete_funding_days(funding_rows)
        sources["MEXC_BTC_USDT_FUNDING"]["coverage"] = funding_coverage

        prices, price_source = fetch_binance_prices()
        sources["BINANCE_BTCUSDT_SPOT"] = price_source

        events, event_meta = build_events(funding_daily, prices)
        if len(events) < MODEL_WINDOW + 60:
            raise ValueError(f"Insufficient accepted funding/price events: {len(events)}")
        predictions = walk_forward(events)
        validation_rows = [
            row for row in predictions
            if VALIDATION_START <= row["signal_date"] < TEST_START
        ]
        test_rows = [row for row in predictions if row["signal_date"] >= TEST_START]
        validation, test = metrics(validation_rows), metrics(test_rows)
        base.BOOTSTRAP_BLOCK = BOOTSTRAP_BLOCK
        base.LOSS_BOOTSTRAP_SEED = BOOTSTRAP_SEED
        paired = base.bootstrap_paired_squared_loss_difference(test_rows, reps=BOOTSTRAP_REPS)
        status, disposition = decide(validation, test, paired)
        return {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": status,
            "disposition": disposition,
            "completed_backtest": True,
            "source_failure": None,
            "retrieved_at_utc": NOW.isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "timebox": TIMEBOX,
            "data_sources": sources,
            "event_construction": event_meta,
            "summary_metrics": {
                "accepted_events": len(events),
                "forecast_n": len(predictions),
                "validation_n": validation["n"],
                "test_n": test["n"],
                "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
                "test_rmse_improvement_pct": test["rmse_improvement_pct"],
            },
            "validation_metrics": validation,
            "test_metrics": test,
            "paired_squared_loss_bootstrap": paired,
            "methodology": {
                "baseline_features": BASE_FEATURES,
                "augmented_features": AUG_FEATURES,
                "training_window_events": MODEL_WINDOW,
                "training_maturity_rule": "training target_end_date must be strictly earlier than the current signal date",
                "validation": f"{VALIDATION_START.isoformat()} through {(TEST_START - dt.timedelta(days=1)).isoformat()}",
                "test": f"{TEST_START.isoformat()} onward through {END_DATE.isoformat()}",
                "bootstrap_reps": BOOTSTRAP_REPS,
                "bootstrap_block_events": BOOTSTRAP_BLOCK,
                "bootstrap_seed": BOOTSTRAP_SEED,
            },
            "limitations": [
                "MEXC funding history is one venue's perpetual market, not a consolidated global funding index.",
                "Positive funding is not a direct measure of net directional long exposure; arbitrage, hedging, basis and inventory can affect it.",
                "Binance Spot closes are a single venue's reference price, not MEXC index/fair price or executable perpetual P&L.",
                "The MEXC endpoint's currently available history may be limited; coverage is only the frozen 2025-06-15 to 2026-11-23 window.",
                "A one-session downside-loss forecast is not a causal result, position-sizing rule or trading strategy.",
                "No raw MEXC funding or Binance market observations are committed; page hashes, archive checksums and aggregate metrics are retained.",
            ],
        }
    except Exception as exc:
        return {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "disposition": f"INFEASIBLE — frozen source or implementation acceptance failed: {type(exc).__name__}: {exc}",
            "completed_backtest": False,
            "source_failure": f"{type(exc).__name__}: {exc}",
            "retrieved_at_utc": NOW.isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "timebox": TIMEBOX,
            "data_sources": sources,
            "limitations": [
                "No empirical performance conclusion is drawn because the frozen source/implementation gates did not pass.",
                "The original timebox remains in force; no source, sample, cadence, target or decision gate is relaxed.",
                "No raw market observations are committed.",
            ],
        }


def render_report(result: dict, report_path: str, manifest_path: str) -> str:
    lines = [
        "# Research session — MEXC BTC perpetual funding and next-session Spot downside risk",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Difficulty/timebox:** {TIMEBOX['difficulty']}; {TIMEBOX['max_substantive_cycles']} substantive cycles maximum.",
        f"- **Implementation deadline:** {TIMEBOX['implementation_deadline_utc']}.",
        f"- **Final research-conclusion deadline:** {TIMEBOX['final_conclusion_deadline_utc']}.",
        f"- **Registered/start:** {TIMEBOX['start_utc']}.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}.",
        f"- **Triggering commit:** {SOURCE_SHA}.",
        f"- **Completed real-data backtest:** {result.get('completed_backtest')}.",
        "",
        "## Frozen method",
        "",
        "- Predictor: sum of MEXC BTC_USDT perpetual funding settlements at 00:00, 08:00 and 16:00 UTC on day d.",
        "- Signal: close of Binance BTCUSDT Spot UTC daily candle d; no funding settlement from d+1 is used.",
        "- Baseline: prior-one-session downside loss, prior-five-session downside semivariance and prior-five-session realized variance.",
        "- Target: next one-session downside loss, in percentage-points squared, transformed with log1p.",
        "- Model: standardized, ridge-stabilized OLS with 104 prior fully matured daily events.",
        "- Validation/test: 2025-10-01 through 2026-02-28 / 2026-03-01 onward.",
        "- No tuning, causal claim, trading P&L or strategy promotion.",
        "",
        "## Source and coverage evidence",
        "",
        json.dumps(result.get("data_sources", {}), indent=2, sort_keys=True),
        "",
    ]
    if result.get("source_failure"):
        lines.extend(["## Source/implementation blocker", "", result["source_failure"], ""])
    if result.get("completed_backtest"):
        lines.extend([
            "## Walk-forward results",
            "",
            "| Metric | Validation | Test |",
            "|---|---:|---:|",
            f"| Forecasts | {result['validation_metrics']['n']} | {result['test_metrics']['n']} |",
            f"| Baseline RMSE | {result['validation_metrics']['baseline']['rmse_bp']:.8f} | {result['test_metrics']['baseline']['rmse_bp']:.8f} |",
            f"| Augmented RMSE | {result['validation_metrics']['augmented']['rmse_bp']:.8f} | {result['test_metrics']['augmented']['rmse_bp']:.8f} |",
            f"| RMSE improvement | {result['validation_metrics']['rmse_improvement_pct']:.6f}% | {result['test_metrics']['rmse_improvement_pct']:.6f}% |",
            "",
            "## Paired test-loss uncertainty",
            "",
            json.dumps(result["paired_squared_loss_bootstrap"], indent=2, sort_keys=True),
            "",
        ])
    else:
        lines.extend([
            "## Empirical result",
            "",
            "No empirical backtest was run. The hypothesis is closed as INCONCLUSIVE/INFEASIBLE under the frozen source or implementation gate; no performance conclusion is inferred from the blocker.",
            "",
        ])
    lines.extend([
        "## Event construction",
        "",
        json.dumps(result.get("event_construction", {}), indent=2, sort_keys=True),
        "",
        "## Limitations",
        "",
    ])
    for item in result.get("limitations", []):
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Durable evidence",
        "",
        f"- Report: {report_path}",
        f"- Manifest: {manifest_path}",
        "- Raw funding and price observations are not committed.",
    ])
    return "\n".join(lines) + "\n"


def write_artifacts(result: dict) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = (SESSION_DIR / f"{STAMP}_session-mexc-btc-funding-{RUN_ID}.md").relative_to(ROOT).as_posix()
    manifest_path = (OUTPUT_DIR / "manifest.json").relative_to(ROOT).as_posix()
    manifest = {
        **result,
        "report_path": report_path,
        "manifest_path": manifest_path,
        "raw_market_observations_committed": False,
    }
    (ROOT / manifest_path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (ROOT / report_path).write_text(render_report(result, report_path, manifest_path), encoding="utf-8")
    return report_path, manifest_path


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = str(result.get("disposition", "INCONCLUSIVE — no disposition established")).replace("|", "/")
    sources = result.get("data_sources", {})
    mexc = sources.get("MEXC_BTC_USDT_FUNDING", {})
    binance = sources.get("BINANCE_BTCUSDT_SPOT", {})
    scope = (
        f"MEXC BTC_USDT 8h funding {mexc.get('first_settlement_utc', 'coverage unverified')} to "
        f"{mexc.get('last_settlement_utc', 'coverage unverified')}; "
        f"Binance BTCUSDT Spot 1d UTC {binance.get('first_date', 'coverage unverified')} to "
        f"{binance.get('last_date', 'coverage unverified')}"
    )
    summary = result.get("summary_metrics", {})
    metric_text = (
        f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, "
        f"RMSE improvement={summary.get('validation_rmse_improvement_pct')}/"
        f"{summary.get('test_rmse_improvement_pct')}%"
        if result.get("completed_backtest") else str(result.get("source_failure"))
    )
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Prior UTC day's three MEXC BTC_USDT perpetual funding settlements "
        f"add information about next-session BTC Spot downside loss beyond lagged downside risk and realized variance. | "
        f"{scope} | {disposition}; {metric_text} | "
        f"[session report](../{report_path}) / [manifest](../{manifest_path}) |"
    )
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    registry_lines = registry.splitlines()
    matching = [i for i, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")]
    if matching:
        registry_lines[matching[0]] = row
        for index in reversed(matching[1:]):
            del registry_lines[index]
    else:
        heading = next((i for i, line in enumerate(registry_lines) if line.strip() == "## Disposition rules"), None)
        if heading is None:
            raise ValueError("Hypothesis registry has no Disposition rules insertion point")
        insert_at = heading
        while insert_at > 0 and not registry_lines[insert_at - 1].strip():
            insert_at -= 1
        registry_lines.insert(insert_at, row)
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    prereg = PREREG_PATH.read_text(encoding="utf-8")
    import re
    prereg, count = re.subn(r"(?m)^- \*\*Status:\*\* .+$", f"- **Status:** {status}", prereg, count=1)
    if count != 1:
        raise ValueError("Could not update preregistration status idempotently")
    disposition_section = [
        "## Empirical disposition",
        "",
        f"- **Status:** {status}",
        f"- **Disposition:** {disposition}",
        f"- **Completed real-data backtest:** {result.get('completed_backtest')}",
        f"- **Data scope:** {scope}",
        f"- **Summary metrics:** {json.dumps(summary, sort_keys=True)}",
        f"- **Paired test-loss bootstrap:** {json.dumps(result.get('paired_squared_loss_bootstrap'), sort_keys=True)}",
        f"- **Source/implementation blocker:** {result.get('source_failure')}",
        f"- **Report:** [{report_path}](../{report_path})",
        f"- **Manifest:** [{manifest_path}](../{manifest_path})",
        "- Forecast-only; no causal, executable-trading or deployment claim.",
    ]
    section = "\n".join(disposition_section) + "\n"
    if "## Empirical disposition" in prereg:
        prereg = prereg.split("## Empirical disposition", 1)[0].rstrip() + "\n\n" + section
    else:
        prereg = prereg.rstrip() + "\n\n" + section
    PREREG_PATH.write_text(prereg, encoding="utf-8")


def main() -> None:
    result = run_research()
    report_path, manifest_path = write_artifacts(result)
    print(f"QFR_STATUS={result['status']}")
    print(f"QFR_DISPOSITION={result['disposition']}")
    print(f"QFR_COMPLETED_BACKTEST={result['completed_backtest']}")
    print(f"QFR_REPORT={report_path}")
    print(f"QFR_MANIFEST={manifest_path}")
    print("=== RESEARCH REPORT ===")
    print(render_report(result, report_path, manifest_path))
    print("=== GENERATED MANIFEST ===")
    print(json.dumps({key: value for key, value in result.items() if key != "data_sources"}, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
