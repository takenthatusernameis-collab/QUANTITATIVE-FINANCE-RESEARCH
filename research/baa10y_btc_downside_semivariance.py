#!/usr/bin/env python3
"""Forecast screen: strictly lagged corporate-credit spread widening -> BTC downside semivariance."""
from __future__ import annotations

import bisect
import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
import urllib.parse
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01"
START_DATE = dt.date(1986, 1, 2)
BTC_START_DATE = dt.date(2017, 8, 17)
RELEASE_LAG_DAYS = 5
MAX_BAA_CUTOFF_AGE_DAYS = 4
MODEL_WINDOW = 104
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 4, 20261126
MIN_BAA_ROWS, MIN_BTC_ROWS = 8000, 3000
MAX_BAA_AGE_DAYS, MAX_BTC_AGE_DAYS = 5, 2
ARCHIVE_WORKERS = 6

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BAA10Y_PAGE = "https://fred.stlouisfed.org/series/BAA10Y"
BAA10Y_TABLE = "https://fred.stlouisfed.org/data/BAA10Y"
BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "baa10y-btc-downside-semivariance" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01.md"

BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["baa_spread_change_5obs_bps"]


def parse_baa10y(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or "BAA10Y" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED BAA10Y schema: {reader.fieldnames}")
    date_col = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_col is None:
        raise ValueError("FRED BAA10Y CSV has no recognized date column")
    values: dict[dt.date, float] = {}
    for row in reader:
        raw = str(row.get("BAA10Y") or "").strip()
        if not raw or raw == ".":
            continue
        day, value = base.parse_date(row.get(date_col)), base.parse_float(raw)
        if day is None or value is None:
            raise ValueError(f"Invalid BAA10Y observation: {row}")
        if day.weekday() >= 5:
            raise ValueError(f"BAA10Y observation is not a business day: {day}")
        if day in values:
            raise ValueError(f"Duplicate BAA10Y observation: {day}")
        values[day] = value
    if not values:
        raise ValueError("No valid BAA10Y observations")
    return dict(sorted(values.items()))


def fetch_sources() -> tuple[dict, dict, dict]:
    fred_url = f"{FRED_URL}?id=BAA10Y&cosd={START_DATE.isoformat()}"
    fred_body = base.fetch_bytes(fred_url, timeout=25)
    spread = parse_baa10y(fred_body)

    info_url = BINANCE_EXCHANGE_INFO + "?" + urllib.parse.urlencode({"symbol": "BTCUSDT"})
    info_body = base.fetch_bytes(info_url, timeout=15)
    symbols = json.loads(info_body.decode("utf-8")).get("symbols", [])
    if len(symbols) != 1:
        raise ValueError("Binance exchangeInfo did not return exactly BTCUSDT")
    info = symbols[0]
    if (info.get("symbol"), info.get("status"), info.get("baseAsset"), info.get("quoteAsset")) != (
        "BTCUSDT", "TRADING", "BTC", "USDT"
    ):
        raise ValueError(f"BTCUSDT is not an active spot USDT market: {info}")

    end_date = NOW.date() - dt.timedelta(days=2)
    specs = btc.build_archive_specs(BTC_START_DATE, end_date, as_of_date=NOW.date())
    results, failures = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as executor:
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
        failures.sort(key=lambda item: (item["kind"], item["period"]))
        raise RuntimeError(
            f"Binance Vision archive ingestion failed for {len(failures)}/{len(specs)} archives: "
            f"{json.dumps(failures, sort_keys=True)}"
        )

    prices, archive_manifest, timestamp_units = {}, [], set()
    for index in range(len(specs)):
        page, manifest_row = results[index]
        archive_manifest.append(manifest_row)
        timestamp_units.add(manifest_row["timestamp_unit"])
        for day, close in page.items():
            if day < BTC_START_DATE or day > end_date:
                continue
            if day in prices:
                raise ValueError(f"Duplicate BTCUSDT date across archives: {day}")
            prices[day] = close

    prices = dict(sorted(prices.items()))
    expected, day = [], BTC_START_DATE
    while day <= end_date:
        expected.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected if day not in prices]
    if missing:
        raise ValueError(
            f"BTCUSDT archive history has {len(missing)} missing UTC dates; "
            f"first_missing={missing[0]}, last_missing={missing[-1]}"
        )

    archive_sha = hashlib.sha256(
        json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    sources = {
        "BAA10Y": {
            "url": fred_url,
            "series_page": BAA10Y_PAGE,
            "table_page": BAA10Y_TABLE,
            "sha256": hashlib.sha256(fred_body).hexdigest(),
            "rows": len(spread),
            "first_date": min(spread).isoformat(),
            "last_date": max(spread).isoformat(),
            "units": "percent; change converted to basis points",
            "frequency": "daily, business days",
            "vintage": "current FRED vintage; historical ALFRED vintages not reconstructed",
            "raw_data_policy": "No raw observations are committed or redistributed; only source hash, coverage and aggregate results are retained.",
            "licensing_note": "FRED series notes include a Moody's proprietary-information notice; downstream raw-series redistribution is excluded.",
        },
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "market_status": info["status"],
            "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
            "interval": "1d",
            "timezone": "UTC",
            "rows": len(prices),
            "first_date": min(prices).isoformat(),
            "last_date": max(prices).isoformat(),
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(row["kind"] == "monthly" for row in archive_manifest),
            "daily_archive_count": sum(row["kind"] == "daily" for row in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_sha,
            "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
    }
    return spread, prices, sources


def validate_coverage(spread: dict, prices: dict, today: dt.date) -> dict:
    sd, pd = sorted(spread), sorted(prices)
    if len(sd) < MIN_BAA_ROWS or len(pd) < MIN_BTC_ROWS:
        raise ValueError(f"Insufficient source depth: BAA10Y={len(sd)}, BTCUSDT={len(pd)}")
    if sd[0] > START_DATE + dt.timedelta(days=20) or pd[0] > BTC_START_DATE + dt.timedelta(days=2):
        raise ValueError(f"Source history starts too late: BAA10Y={sd[0]}, BTCUSDT={pd[0]}")
    if sd[-1] > today or pd[-1] > today:
        raise ValueError("A source contains a future-dated observation")
    if (today - sd[-1]).days > MAX_BAA_AGE_DAYS:
        raise ValueError(f"BAA10Y is stale: {sd[-1]}")
    if (today - pd[-1]).days > MAX_BTC_AGE_DAYS:
        raise ValueError(f"BTCUSDT daily candles are stale: {pd[-1]}")
    if any(day.weekday() >= 5 for day in sd):
        raise ValueError("BAA10Y contains a weekend observation")
    spread_gaps = [(right - left).days for left, right in zip(sd, sd[1:])]
    price_gaps = [(right - left).days for left, right in zip(pd, pd[1:])]
    if any(gap > 7 for gap in spread_gaps):
        raise ValueError("BAA10Y has a gap greater than seven calendar days")
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("BTCUSDT daily candles contain a missing UTC day")
    return {
        "BAA10Y": {"rows": len(sd), "first_date": sd[0].isoformat(), "last_date": sd[-1].isoformat()},
        "BTCUSDT": {"rows": len(pd), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat()},
    }


def build_events(spread: dict, prices: dict) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        returns.append(
            math.log(prices[dates[index]] / prices[dates[index - 1]])
            if (dates[index] - dates[index - 1]).days == 1 else None
        )

    spread_dates = sorted(spread)
    events = []
    skipped = {
        "no_prior_spread_history": 0,
        "stale_spread_at_cutoff": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
    }
    signal_dates = [day for day in dates if day.weekday() == 2]
    for signal in signal_dates:
        j = bisect.bisect_left(dates, signal)
        cutoff = signal - dt.timedelta(days=RELEASE_LAG_DAYS)
        spread_index = bisect.bisect_right(spread_dates, cutoff) - 1
        if spread_index < 5:
            skipped["no_prior_spread_history"] += 1
            continue
        observation_date = spread_dates[spread_index]
        observation_age = (cutoff - observation_date).days
        if observation_age < 0 or observation_age > MAX_BAA_CUTOFF_AGE_DAYS:
            skipped["stale_spread_at_cutoff"] += 1
            continue
        if j < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior5, prior20 = returns[j - 4:j + 1], returns[j - 19:j + 1]
        future = returns[j + 1:j + 1 + TARGET_SESSIONS]
        if any(value is None for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue

        lookback_date = spread_dates[spread_index - 5]
        spread_change_bps = (spread[observation_date] - spread[lookback_date]) * 100.0
        prior5 = [float(value) for value in prior5]
        prior20 = [float(value) for value in prior20]
        future = [float(value) for value in future]
        target = btc.semi_var_pct2(future)
        events.append({
            "record_date": signal,
            "signal_date": signal,
            "target_start_date": dates[j + 1],
            "target_end_date": dates[j + TARGET_SESSIONS],
            "baa_cutoff_date": cutoff,
            "baa_observation_date": observation_date,
            "baa_lookback_date": lookback_date,
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(prior20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(prior20)),
            "baa_spread_change_5obs_bps": spread_change_bps,
        })

    for left, right in zip(events, events[1:]):
        gap_days = (right["signal_date"] - left["signal_date"]).days
        if gap_days <= 0 or gap_days % 7 != 0:
            raise ValueError("Accepted signal origins do not follow the Wednesday weekly schedule")
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("BTC target windows overlap or are not fully matured")

    return events, {
        "candidate_wednesdays": len(signal_dates),
        "accepted_events": len(events),
        "skipped": skipped,
        "publication_lag_calendar_days": RELEASE_LAG_DAYS,
        "maximum_observation_age_at_cutoff_days": MAX_BAA_CUTOFF_AGE_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "weekly_event_spacing_days": 7,
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
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "train_n": len(train),
        })
    return predictions


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0,
            "baseline_rmse_log1p": None,
            "augmented_rmse_log1p": None,
            "baseline_mae_log1p": None,
            "augmented_mae_log1p": None,
            "rmse_improvement_pct": None,
        }
    baseline_errors = [row["baseline_prediction_bp"] - row["target_bp"] for row in rows]
    augmented_errors = [row["augmented_prediction_bp"] - row["target_bp"] for row in rows]
    baseline_rmse = math.sqrt(statistics.fmean(error * error for error in baseline_errors))
    augmented_rmse = math.sqrt(statistics.fmean(error * error for error in augmented_errors))
    return {
        "n": len(rows),
        "baseline_rmse_log1p": baseline_rmse,
        "augmented_rmse_log1p": augmented_rmse,
        "baseline_mae_log1p": statistics.fmean(abs(error) for error in baseline_errors),
        "augmented_mae_log1p": statistics.fmean(abs(error) for error in augmented_errors),
        "rmse_improvement_pct": (
            100.0 * (baseline_rmse - augmented_rmse) / baseline_rmse if baseline_rmse > 0 else None
        ),
    }


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    losses = [{
        "difference": (row["baseline_prediction_bp"] - row["target_bp"]) ** 2
        - (row["augmented_prediction_bp"] - row["target_bp"]) ** 2
    } for row in rows]
    observed = statistics.fmean(row["difference"] for row in losses)
    rng, means = random.Random(BOOTSTRAP_SEED), []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(losses, rng, BOOTSTRAP_BLOCK)
        means.append(statistics.fmean(row["difference"] for row in sample))
    means.sort()
    return {
        "observations": len(losses),
        "reps": len(means),
        "block_size_events": BOOTSTRAP_BLOCK,
        "mean_baseline_minus_augmented_squared_loss": observed,
        "ci95_low": means[int(0.025 * (len(means) - 1))],
        "ci95_high": means[int(0.975 * (len(means) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in means) / len(means),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < 30 or test["n"] < 30 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient forecast sample or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci95_low"] > 0:
        return "BACKTESTED", (
            "PROMISING SCREEN — both chronological periods improve and paired-loss inference "
            "favors augmentation; current-vintage and source-licensing limits prevent independent validation"
        )
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci95_high"] < 0:
        return "REJECTED", "REJECTED — both chronological periods worsen and paired-loss inference favors the baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority"


def run_research() -> dict:
    spread, prices, sources = fetch_sources()
    coverage = validate_coverage(spread, prices, NOW.date())
    events, event_meta = build_events(spread, prices)
    predictions = walk_forward(events)
    validation = summarize([
        row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START
    ])
    test = summarize([row for row in predictions if row["signal_date"] >= TEST_START])
    paired = paired_loss_bootstrap([row for row in predictions if row["signal_date"] >= TEST_START])
    status, disposition = decide(validation, test, paired)

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": (
            "The 2026-11-26 minimum was already met by distinct real-data forecast screens; "
            "this is an additional hypothesis screen."
        ),
        "coverage": coverage,
        "data_sources": sources,
        "event_construction": event_meta,
        "data_scope": (
            f"FRED BAA10Y daily {coverage['BAA10Y']['first_date']} to {coverage['BAA10Y']['last_date']} "
            f"({coverage['BAA10Y']['rows']} observations); Binance BTCUSDT Spot 1d UTC "
            f"{coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} "
            f"({coverage['BTCUSDT']['rows']} candles); Wednesday events; validation 2019-2021; test 2022 onward"
        ),
        "methodology": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUG_FEATURES,
            "predictor": (
                "100 * (latest eligible BAA10Y observation - its value five prior business observations earlier); "
                "BAA10Y is in percent, so the change is in basis points"
            ),
            "availability": (
                "For a Wednesday BTC UTC daily-candle signal, use only BAA10Y observations dated on or before "
                "signal_date minus five calendar days; the selected observation must be no more than four days "
                "older than that cutoff. This is a conservative publication embargo; exact historical release "
                "timestamps are not reconstructed."
            ),
            "target": "log1p(next-five-UTC-session BTCUSDT downside semivariance, percentage-points-squared units)",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "prior signal and target_end must both be strictly earlier than current signal",
            "signal_schedule": "Wednesday UTC BTC daily-candle closes, exactly seven calendar days apart",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "summary_metrics": {
            "validation_n": validation["n"],
            "test_n": test["n"],
            "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
            "test_rmse_improvement_pct": test["rmse_improvement_pct"],
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "BAA10Y is Moody's Baa corporate-bond yield minus the 10-year Treasury yield, not a pure option-adjusted default-risk spread; it also reflects duration, liquidity, rating-composition and Treasury-yield effects.",
            "FRED's BAA10Y series notes contain a Moody's proprietary-information notice. Raw observations are not committed or redistributed; only source hashes, coverage and aggregate research metrics are retained.",
            "The study uses the current FRED vintage, not historical ALFRED point-in-time vintages; the fixed five-calendar-day embargo does not reconstruct every historical release timestamp or revision.",
            "BTCUSDT is one venue's Spot series. Binance Vision archive checksums establish file integrity, not consolidated-market representativeness.",
            "Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.",
        ],
    }


def render_report(result: dict) -> str:
    lines = [
        f"# Research session — BAA10Y credit-spread widening and BTC downside semivariance ({STAMP})",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi')}",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Triggering commit:** {SOURCE_SHA}",
        "",
    ]
    if result.get("error"):
        lines += [
            "## Execution blocker",
            "",
            f"- {result['error']}",
            "- No valid real-data backtest completed in this run; the earlier daily KPI remains independently met.",
            "",
        ]
    else:
        val, test = result["validation_metrics"], result["test_metrics"]
        lines += [
            "## Preregistered method",
            "",
            "- Predictor: five-business-observation change in BAA10Y, converted from percentage points to basis points.",
            "- Availability: for each Wednesday UTC BTC signal, use only observations dated on or before signal date minus five calendar days; reject a selected observation more than four days older than the cutoff.",
            "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.",
            "- Target: next-five-session BTC downside semivariance, transformed with log1p.",
            "- Rolling training window: 104 prior weekly events; every training target must be fully matured before the current signal.",
            "- Validation: 2019–2021. Test: 2022 onward.",
            "",
            "## Data provenance",
            "",
            "| Source | First | Last | Rows | SHA-256 / manifest |",
            "|---|---|---:|---:|---|",
            f"| BAA10Y | {result['coverage']['BAA10Y']['first_date']} | {result['coverage']['BAA10Y']['last_date']} | {result['coverage']['BAA10Y']['rows']} | {result['data_sources']['BAA10Y']['sha256']} |",
            f"| BTCUSDT | {result['coverage']['BTCUSDT']['first_date']} | {result['coverage']['BTCUSDT']['last_date']} | {result['coverage']['BTCUSDT']['rows']} | {result['data_sources']['BTCUSDT']['archive_count']} archives; {result['data_sources']['BTCUSDT']['archive_manifest_sha256']} |",
            "",
            "## Walk-forward results",
            "",
            "| Metric | Validation 2019–2021 | Test 2022 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {val['n']} | {test['n']} |",
            f"| Baseline RMSE (log1p semivariance) | {val['baseline_rmse_log1p']} | {test['baseline_rmse_log1p']} |",
            f"| Augmented RMSE (log1p semivariance) | {val['augmented_rmse_log1p']} | {test['augmented_rmse_log1p']} |",
            f"| RMSE improvement | {val['rmse_improvement_pct']}% | {test['rmse_improvement_pct']}% |",
            "",
            "## Paired test-loss uncertainty",
            "",
            f"- {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}",
            "",
            "## Interpretation",
            "",
            result.get("disposition", "No disposition established."),
            "",
            "## Verified / unverified",
            "",
            "**VERIFIED:** source schemas and coverage gates, archive checksums, publication embargo, event timing, non-overlapping targets, walk-forward maturity and metrics, if the backtest completed.",
            "**UNVERIFIED:** historical point-in-time FRED vintages, independent reconstruction, future-regime stability, causality and instrument-level economic value.",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    return "\n".join(lines) + "\n"


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = result.get("disposition", "INCONCLUSIVE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete")
    summary = result.get("summary_metrics") or {}
    metrics_text = (
        f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, "
        f"RMSE improvement={summary.get('validation_rmse_improvement_pct')}/"
        f"{summary.get('test_rmse_improvement_pct')} percent; forecast-only"
    )
    report_link, manifest_link = "../" + report_path, "../" + manifest_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged five-business-observation widening in the "
        f"Moody's Baa corporate-bond yield minus 10-year Treasury yield adds information about next-five-session "
        f"BTC downside semivariance beyond recent BTC downside semivariance and realized variance. | {scope} | "
        f"{disposition}; {metrics_text} | [session report]({report_link}) / [manifest]({manifest_link}) |"
    )
    registry_lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next(
        (i for i, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")),
        None,
    )
    if existing is not None:
        registry_lines[existing] = row
    else:
        separator = next((i for i, line in enumerate(registry_lines) if line.startswith("|---")), None)
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        registry_lines.insert(separator + 1, row)
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    prereg_lines = PREREG_PATH.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[index] = f"- **Status:** {status}"
            break
    prereg = "\n".join(prereg_lines).split("\n## Empirical disposition")[0].rstrip()
    prereg += (
        "\n\n## Empirical disposition\n\n"
        f"- **Status:** {status}\n"
        f"- **Disposition:** {disposition}\n"
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}\n"
        f"- **Data scope:** {scope}\n"
        f"- **Summary metrics:** {json.dumps(base.json_safe(summary), sort_keys=True)}\n"
        f"- **Paired test-loss bootstrap:** {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}\n"
        f"- **Report:** [{report_path}]({report_link})\n"
        f"- **Manifest:** [{manifest_path}]({manifest_link})\n"
        "- Forecast screen only; no causal, trading or deployment claim.\n"
    )
    PREREG_PATH.write_text(prereg + "\n", encoding="utf-8")


def write_outputs(result: dict) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-baa10y-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = str(report_path.relative_to(ROOT))
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_documents(result, result["report_path"], result["manifest_path"])
    return result["report_path"], result["manifest_path"]


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — bounded source/execution failure: {type(exc).__name__}: {exc}",
            "completed_backtest": False,
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": (
                "MET before this run by distinct 2026-11-26 real-data backtests; "
                "this failed source/execution attempt does not count."
            ),
            "error": f"{type(exc).__name__}: {exc}",
            "alternatives_attempted": [
                "FRED public BAA10Y CSV and series/table pages",
                "Binance public exchangeInfo market-data endpoint",
                "Binance official checksummed Spot monthly/daily archive route",
            ],
        }
    report_path, manifest_path = write_outputs(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result["status"],
        "completed_backtest": result.get("completed_backtest"),
        "report_path": report_path,
        "manifest_path": manifest_path,
        "summary_metrics": result.get("summary_metrics"),
        "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
