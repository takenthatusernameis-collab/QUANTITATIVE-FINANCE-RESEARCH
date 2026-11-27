#!/usr/bin/env python3
"""Forecast screen: lagged U.S. initial-claims deterioration -> BTC downside semivariance."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc
import initial_claims_source_preflight as source

HYPOTHESIS_ID = "QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 19)
BTC_START_DATE = dt.date(2017, 8, 17)
RELEASE_LAG_DAYS = 7
MODEL_WINDOW = 104
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261127
MIN_CLAIMS_ROWS = 450
MIN_BTC_ROWS = 3000
MAX_CLAIMS_AGE_DAYS = 14
MAX_BTC_AGE_DAYS = 2
ARCHIVE_WORKERS = 6
FRED_PREFLIGHT_SHA256 = "2bcf8c35377a4280459bc015dc53cba21cbcd992a916a7fd0d29bd5d09aed0bb"
BINANCE_SAMPLE_DATE = dt.date(2026, 11, 23)
BINANCE_SAMPLE_ARCHIVE_SHA256 = "d778c53e3a42ec9e6ae13f39401b530028a37c78b94be1cfd80aec7706e3d96a"
BINANCE_SAMPLE_CHECKSUM_SHA256 = "c042ab4efd94ff8117026fc7a817ac7ad887f83a7b19323cfcfe8eb3659a3d4f"
FRED_PREFLIGHT_RUN_ID = "46028463525"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "initial-claims-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01.md"

BASE_FEATURES = [
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
]
AUG_FEATURES = BASE_FEATURES + ["icsa_change_4w_pct"]


def fetch_sources() -> tuple[dict, dict, dict]:
    fred_url = source.build_fred_url(START_DATE)
    fred_body = base.fetch_bytes(fred_url, timeout=25)
    fred_sha = hashlib.sha256(fred_body).hexdigest()
    if fred_sha != FRED_PREFLIGHT_SHA256:
        raise ValueError(
            "FRED ICSA current-vintage response changed after frozen source preflight: "
            f"expected={FRED_PREFLIGHT_SHA256}, actual={fred_sha}"
        )
    claims = source.parse_icsa(fred_body)
    claims_coverage = source.validate_icsa_coverage(claims, NOW.date(), min_rows=MIN_CLAIMS_ROWS)

    exchange_url = BINANCE_EXCHANGE_INFO + "?symbol=BTCUSDT"
    exchange_body = base.fetch_bytes(exchange_url, timeout=20)
    market = source.validate_binance_exchange_info(exchange_body)

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
    expected_dates = []
    cursor = BTC_START_DATE
    while cursor <= end_date:
        expected_dates.append(cursor)
        cursor += dt.timedelta(days=1)
    missing = [day for day in expected_dates if day not in prices]
    if missing:
        raise ValueError(
            f"BTCUSDT archive history has {len(missing)} missing UTC dates; "
            f"first_missing={missing[0]}, last_missing={missing[-1]}"
        )

    sample_row = next(
        (
            row for row in archive_manifest
            if row.get("kind") == "daily" and row.get("period") == BINANCE_SAMPLE_DATE.isoformat()
        ),
        None,
    )
    if sample_row is None:
        raise ValueError("Frozen Binance source-preflight sample archive is absent from the full model archive set")
    if sample_row.get("archive_sha256") != BINANCE_SAMPLE_ARCHIVE_SHA256:
        raise ValueError("Frozen Binance sample archive SHA-256 differs from source preflight")
    if sample_row.get("checksum_sha256") != BINANCE_SAMPLE_CHECKSUM_SHA256:
        raise ValueError("Frozen Binance sample checksum-sidecar SHA-256 differs from source preflight")

    archive_manifest_sha = hashlib.sha256(
        json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    sources = {
        "ICSA": {
            "url": fred_url,
            "series_page": "https://fred.stlouisfed.org/series/ICSA",
            "response_sha256": fred_sha,
            **claims_coverage,
            "source": "U.S. Employment and Training Administration via FRED",
            "release": "Unemployment Insurance Weekly Claims Report",
            "revision_policy": "current FRED vintage; historical ALFRED vintages not reconstructed",
        },
        "BTCUSDT": {
            "exchange_info_url": exchange_url,
            "exchange_info_response_sha256": hashlib.sha256(exchange_body).hexdigest(),
            "symbol": market["symbol"],
            "market_status": market["status"],
            "spot_trading_allowed": market["spot_trading_allowed"],
            "endpoint": "Binance Vision official Spot 1d UTC kline archives",
            "first_date": min(prices).isoformat(),
            "last_date": max(prices).isoformat(),
            "rows": len(prices),
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(row["kind"] == "monthly" for row in archive_manifest),
            "daily_archive_count": sum(row["kind"] == "daily" for row in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_manifest_sha,
            "frozen_sample_archive": sample_row,
            "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
    }
    return claims, prices, sources


def validate_coverage(claims: dict, prices: dict, today: dt.date) -> dict:
    claim_dates, price_dates = sorted(claims), sorted(prices)
    if len(claim_dates) < MIN_CLAIMS_ROWS or len(price_dates) < MIN_BTC_ROWS:
        raise ValueError(f"Insufficient source depth: ICSA={len(claim_dates)}, BTCUSDT={len(price_dates)}")
    if claim_dates[0] > START_DATE + dt.timedelta(days=14):
        raise ValueError(f"ICSA history starts too late: {claim_dates[0]}")
    if price_dates[0] > BTC_START_DATE + dt.timedelta(days=2):
        raise ValueError(f"BTCUSDT history starts too late: {price_dates[0]}")
    if claim_dates[-1] > today or price_dates[-1] > today:
        raise ValueError("A source contains a future-dated observation")
    if (today - claim_dates[-1]).days > MAX_CLAIMS_AGE_DAYS:
        raise ValueError(f"ICSA is stale: latest={claim_dates[-1]}")
    if (today - price_dates[-1]).days > MAX_BTC_AGE_DAYS:
        raise ValueError(f"BTCUSDT daily candles are stale: latest={price_dates[-1]}")
    if len({day.weekday() for day in claim_dates}) != 1:
        raise ValueError("ICSA observation weekday is inconsistent")
    claim_gaps = [(right - left).days for left, right in zip(claim_dates, claim_dates[1:])]
    if any(gap not in (7, 14) for gap in claim_gaps):
        raise ValueError("ICSA contains a non-weekly gap other than an isolated 14-day omission")
    price_gaps = [(right - left).days for left, right in zip(price_dates, price_dates[1:])]
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("BTCUSDT archive history contains a missing UTC date")
    return {
        "ICSA": {
            "rows": len(claim_dates),
            "first_date": claim_dates[0].isoformat(),
            "last_date": claim_dates[-1].isoformat(),
            "weekday": claim_dates[0].strftime("%A"),
        },
        "BTCUSDT": {
            "rows": len(price_dates),
            "first_date": price_dates[0].isoformat(),
            "last_date": price_dates[-1].isoformat(),
        },
    }


def build_events(claims: dict, prices: dict) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
            continue
        previous_close, current_close = prices[dates[index - 1]], prices[dates[index]]
        if previous_close <= 0 or current_close <= 0:
            returns.append(None)
        else:
            value = math.log(current_close / previous_close)
            returns.append(value if math.isfinite(value) else None)

    index_by_date = {day: index for index, day in enumerate(dates)}
    weeks = sorted(claims)
    events = []
    skipped = {
        "irregular_weekly_window": 0,
        "missing_signal_anchor": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
        "invalid_claims_feature": 0,
    }
    for index in range(4, len(weeks)):
        window = weeks[index - 4:index + 1]
        if any((right - left).days != 7 for left, right in zip(window, window[1:])):
            skipped["irregular_weekly_window"] += 1
            continue
        signal_date = weeks[index] + dt.timedelta(days=RELEASE_LAG_DAYS)
        j = index_by_date.get(signal_date)
        if j is None:
            skipped["missing_signal_anchor"] += 1
            continue
        if j < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior5 = returns[j - 4:j + 1]
        prior20 = returns[j - 19:j + 1]
        future = returns[j + 1:j + 1 + TARGET_SESSIONS]
        if any(value is None or not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue

        old_claims, current_claims = claims[weeks[index - 4]], claims[weeks[index]]
        if old_claims <= 0 or current_claims <= 0:
            skipped["invalid_claims_feature"] += 1
            continue
        claims_change = 100.0 * math.log(current_claims / old_claims)
        if not math.isfinite(claims_change):
            skipped["invalid_claims_feature"] += 1
            continue

        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        if not math.isfinite(target) or target < 0:
            skipped["invalid_returns"] += 1
            continue

        events.append({
            "observation_date": weeks[index],
            "signal_date": signal_date,
            "target_start_date": dates[j + 1],
            "target_end_date": dates[j + TARGET_SESSIONS],
            "icsa_change_4w_pct": claims_change,
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_semivariance_pct2": target,
            # Shared OLS helper expects the legacy target_bp key; its value here is log1p semivariance.
            "target_bp": math.log1p(target),
            "target_log1p_semivariance": math.log1p(target),
        })

    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("Five-session target windows overlap or are not matured before the next signal")

    return events, {
        "candidate_weekly_windows": max(0, len(weeks) - 4),
        "accepted_events": len(events),
        "skipped": skipped,
        "release_lag_days": RELEASE_LAG_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "event_frequency": "weekly; five-session target windows must not overlap",
        "first_signal": events[0]["signal_date"].isoformat() if events else None,
        "last_signal": events[-1]["signal_date"].isoformat() if events else None,
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
            baseline_prediction = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented_prediction = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "observation_date": current["observation_date"].isoformat(),
            "signal_date": current["signal_date"].isoformat(),
            "target_start_date": current["target_start_date"].isoformat(),
            "target_end_date": current["target_end_date"].isoformat(),
            "target_log1p_semivariance": current["target_bp"],
            "baseline_prediction": baseline_prediction,
            "augmented_prediction": augmented_prediction,
            "icsa_change_4w_pct": current["icsa_change_4w_pct"],
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0, "baseline_rmse": None, "augmented_rmse": None,
            "baseline_mae": None, "augmented_mae": None, "rmse_improvement_pct": None,
        }
    baseline_errors = [row["baseline_prediction"] - row["target_log1p_semivariance"] for row in rows]
    augmented_errors = [row["augmented_prediction"] - row["target_log1p_semivariance"] for row in rows]
    baseline_rmse = math.sqrt(statistics.fmean(value * value for value in baseline_errors))
    augmented_rmse = math.sqrt(statistics.fmean(value * value for value in augmented_errors))
    return {
        "n": len(rows),
        "baseline_rmse": baseline_rmse,
        "augmented_rmse": augmented_rmse,
        "baseline_mae": statistics.fmean(abs(value) for value in baseline_errors),
        "augmented_mae": statistics.fmean(abs(value) for value in augmented_errors),
        "rmse_improvement_pct": (
            100.0 * (baseline_rmse - augmented_rmse) / baseline_rmse if baseline_rmse > 0 else None
        ),
    }


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    loss_rows = []
    for row in rows:
        target = row["target_log1p_semivariance"]
        baseline = row["baseline_prediction"]
        augmented = row["augmented_prediction"]
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not all(math.isfinite(value) for value in (target, baseline, augmented, difference)):
            return None
        loss_rows.append({"difference": difference})
    observed = statistics.fmean(row["difference"] for row in loss_rows)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(loss_rows, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["difference"] for row in sample))
    samples.sort()
    return {
        "status": "COMPUTED",
        "observations": len(loss_rows),
        "replications": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "mean_baseline_minus_augmented_squared_loss": observed,
        "ci_95_low": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str, str]:
    if validation["n"] < 30 or test["n"] < 30 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE", (
            "INCONCLUSIVE — the frozen minimum validation/test sample or paired-loss inference was not met"
        )
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low"] > 0:
        return "BACKTESTED", "PROMISING", (
            "PROMISING forecast screen — validation and test RMSE both improve and paired test-loss inference favors augmentation; independent validation and strategy economics remain untested"
        )
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high"] < 0:
        return "REJECTED", "REJECTED", (
            "REJECTED — validation and test RMSE both worsen and paired test-loss inference favors the baseline"
        )
    return "INCONCLUSIVE", "INCONCLUSIVE", (
        "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"
    )


def run_research() -> dict:
    claims, prices, sources = fetch_sources()
    coverage = validate_coverage(claims, prices, NOW.date())
    events, event_meta = build_events(claims, prices)
    predictions = walk_forward(events)
    validation_rows = [
        row for row in predictions
        if VALIDATION_START <= dt.date.fromisoformat(row["signal_date"]) < TEST_START
    ]
    test_rows = [
        row for row in predictions
        if dt.date.fromisoformat(row["signal_date"]) >= TEST_START
    ]
    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    paired = paired_loss_bootstrap(test_rows)
    status, decision, disposition = decide(validation, test, paired)

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "decision": decision,
        "disposition": disposition,
        "completed_backtest": True,
        "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "The 2026-11-27 minimum was already met by the distinct ETF-relative-flow and BTC blockspace-fee-rate real-data screens; this is an additional hypothesis backtest.",
        "coverage": coverage,
        "data_sources": sources,
        "event_construction": event_meta,
        "data_scope": (
            f"FRED ICSA weekly {coverage['ICSA']['first_date']} to {coverage['ICSA']['last_date']} "
            f"({coverage['ICSA']['rows']} observations); Binance BTCUSDT Spot 1d UTC "
            f"{coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} "
            f"({coverage['BTCUSDT']['rows']} candles, {sources['BTCUSDT']['archive_count']} checksummed archives); "
            "weekly events; validation 2019-2021; test 2022 onward"
        ),
        "methodology": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUG_FEATURES,
            "predictor": "100 * ln(ICSA[w] / ICSA[w-4]); positive means initial claims rose over four weekly observations",
            "availability": "ICSA observation date is weekly ending Saturday; signal is the BTC UTC daily close exactly seven calendar days later",
            "target": "log1p(mean(min(next-five BTC daily log return, 0)^2) * 10000; downside semivariance in percent-squared units)",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "latest 104 prior events whose signal date and five-session target end are both strictly earlier than the current signal",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_replications": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_test_loss_bootstrap": paired,
        "forecast_rows": predictions,
        "limitations": [
            "FRED ICSA is current-vintage data; historical ALFRED vintages and exact historical publication timestamps were not reconstructed. The seven-day lag is conservative but does not eliminate revision look-ahead.",
            "ICSA measures weekly initial unemployment-insurance claims, not layoffs alone, unemployment stocks or real-time labor-market expectations.",
            "The feature is one four-week log change in a single national series; no alternative transformations, lags, series or parameters were tested.",
            "This is one of many exploratory repository hypothesis screens; nominal paired-loss intervals do not correct for repository-wide multiple testing or selection bias. Any promising result requires independent confirmation.",
            "BTCUSDT is one venue's Spot close. Binance archive checksums establish file integrity, not exchange-independent consolidated prices.",
            "This is a forecast-only screen, not an executable strategy, trading P&L, causal claim or live deployment recommendation.",
            "No raw ICSA observations or raw BTC price rows are committed; the manifest contains source hashes, coverage and derived forecast rows only.",
        ],
    }


def render_report(result: dict) -> str:
    lines = [
        f"# Research session — U.S. initial claims and BTC downside semivariance ({STAMP})",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Decision:** {result.get('decision')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi')}",
        "- **Implementation timebox:** LOW; 2 substantive cycles maximum; implementation deadline 2026-11-28T15:40:06Z; final research-conclusion deadline 2026-11-29T15:40:06Z.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Triggering commit:** {SOURCE_SHA}",
        "",
    ]
    if result.get("error"):
        lines += [
            "## Source/implementation blocker",
            "",
            f"- {result['error']}",
            "- No valid empirical backtest completed; this attempt does not count as a new backtest.",
            "",
        ]
    else:
        v, t = result["validation_metrics"], result["test_metrics"]
        icsa = result["data_sources"]["ICSA"]
        btc_source = result["data_sources"]["BTCUSDT"]
        lines += [
            "## Cycle accounting",
            "",
            f"- Cycle 1 source feasibility: PASS; preflight run #{FRED_PREFLIGHT_RUN_ID}.",
            "- Cycle 2 implementation, deterministic validation, real-data backtest and independent audit: see linked evidence.",
            "",
            "## Frozen method",
            "",
            "- Predictor: 100 × ln(ICSA[w] / ICSA[w−4]); positive means initial claims rose over four weekly observations.",
            "- Availability: FRED weekly observation ending Saturday, signal at the BTC UTC close seven calendar days later.",
            "- Baseline: prior 5/20-session downside semivariance, prior 20-session realized variance and prior 5/20-session cumulative log returns.",
            "- Augmented model: baseline plus exactly one four-week initial-claims change feature.",
            "- Target: log1p of next-five-session BTC downside semivariance; signal-day return excluded.",
            "- Rolling training: latest 104 fully matured weekly events. Validation: 2019–2021. Test: 2022 onward.",
            "- Estimator: existing standardized OLS helper; no parameter tuning.",
            "",
            "## Data provenance",
            "",
            "| Source | Coverage | Rows / archives | SHA-256 |",
            "|---|---|---:|---|",
            f"| FRED ICSA | {icsa['first_date']} to {icsa['last_date']} | {icsa['rows']} weekly observations | {icsa['response_sha256']} |",
            f"| Binance BTCUSDT Spot | {btc_source['first_date']} to {btc_source['last_date']} | {btc_source['rows']} candles; {btc_source['archive_count']} archives | {btc_source['archive_manifest_sha256']} |",
            f"| Frozen Binance sample archive | {BINANCE_SAMPLE_DATE} | SHA-256 verified | {BINANCE_SAMPLE_ARCHIVE_SHA256} |",
            "",
            "## Event construction",
            "",
            f"- Accepted events: {result['event_construction']['accepted_events']}",
            f"- First/last signal: {result['event_construction']['first_signal']} / {result['event_construction']['last_signal']}",
            f"- Skipped events: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}",
            "- Every five-session target was fully matured before the next weekly signal.",
            "",
            "## Walk-forward results",
            "",
            "| Metric | Validation 2019–2021 | Test 2022 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE | {v['baseline_rmse']} | {t['baseline_rmse']} |",
            f"| Augmented RMSE | {v['augmented_rmse']} | {t['augmented_rmse']} |",
            f"| RMSE improvement | {v['rmse_improvement_pct']}% | {t['rmse_improvement_pct']}% |",
            "",
            "## Paired test-loss uncertainty",
            "",
            f"- {json.dumps(result.get('paired_test_loss_bootstrap'), sort_keys=True)}",
            "",
            "## Interpretation",
            "",
            result.get("disposition", "No disposition established."),
            "",
            "## Verified / unverified",
            "",
            "**VERIFIED:** ICSA schema and weekly coverage, frozen FRED response hash, active BTCUSDT Spot status, Binance archive checksum integrity, event timing, non-overlapping target windows, walk-forward sample construction and arithmetic in the persisted forecast output.",
            "**UNVERIFIED:** historical point-in-time FRED revisions/publication timing, independent data-source replication, causal interpretation, future-regime stability and instrument-level economic value.",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines += [
        "",
        "## Reproducibility",
        "",
        f"- Source preflight: https://github.com/{base.REPO}/actions/runs/{FRED_PREFLIGHT_RUN_ID}",
        f"- Empirical workflow: https://github.com/{base.REPO}/actions/runs/{RUN_ID}",
        "- Implementation: research/initial_claims_btc_downside.py",
        "- Tests: research/test_initial_claims_btc_downside.py",
        "",
    ]
    return "\n".join(lines)


def update_documents(result: dict, report_path: str, manifest_path: str, forecast_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE/INFEASIBLE")
    decision = result.get("decision", status)
    disposition = result.get("disposition", "INCONCLUSIVE/INFEASIBLE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete")
    v = result.get("validation_metrics") or {}
    t = result.get("test_metrics") or {}
    paired = result.get("paired_test_loss_bootstrap")
    summary = (
        f"decision={decision}; validation/test n={v.get('n', 0)}/{t.get('n', 0)}, "
        f"RMSE improvement={v.get('rmse_improvement_pct')}/{t.get('rmse_improvement_pct')} percent; forecast-only"
    )
    report_link, manifest_link, forecast_link = "../" + report_path, "../" + manifest_path, "../" + forecast_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged four-week log change in U.S. seasonally adjusted initial jobless claims may add information about next-five-UTC-session BTC downside semivariance beyond recent downside risk, realized variance and momentum. | "
        f"{scope} | {disposition}; {summary} | [preregistration](PREREGISTERED-QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01.md) / [report]({report_link}) / [manifest]({manifest_link}) / [forecasts]({forecast_link}) |"
    )
    registry_lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is None:
        separator = next((i for i, line in enumerate(registry_lines) if line.startswith("|---")), None)
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        registry_lines.insert(separator + 1, row)
    else:
        registry_lines[existing] = row
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    prereg_lines = PREREG_PATH.read_text(encoding="utf-8").splitlines()
    status_line = (
        f"- **Status:** {status}; decision={decision}. "
        f"{'One frozen real-data backtest completed.' if result.get('completed_backtest') else 'No valid empirical backtest completed.'}"
    )
    found = False
    for index, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[index] = status_line
            found = True
            break
    if not found:
        raise ValueError("Preregistration has no status line")
    prereg_text = "\n".join(prereg_lines).split("\n## Empirical disposition")[0].rstrip()
    prereg_text += (
        "\n\n## Empirical disposition\n\n"
        f"- **Final status:** {status}; decision={decision}.\n"
        f"- **Disposition:** {disposition}.\n"
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}.\n"
        f"- **Data scope:** {scope}.\n"
        f"- **Validation metrics:** {json.dumps(v, sort_keys=True)}.\n"
        f"- **Test metrics:** {json.dumps(t, sort_keys=True)}.\n"
        f"- **Paired test-loss bootstrap:** {json.dumps(paired, sort_keys=True)}.\n"
        f"- **Report:** [{report_path}]({report_link}).\n"
        f"- **Manifest:** [{manifest_path}]({manifest_link}).\n"
        f"- **Forecast rows:** [{forecast_path}]({forecast_link}).\n"
        "- Forecast-only; no causal, trading or deployment claim.\n"
    )
    PREREG_PATH.write_text(prereg_text + "\n", encoding="utf-8")


def write_outputs(result: dict) -> tuple[str, str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-initial-claims-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    forecast_path = OUTPUT_DIR / "forecast_rows.csv"
    result["report_path"] = str(report_path.relative_to(ROOT))
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    result["forecast_path"] = str(forecast_path.relative_to(ROOT))
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    with forecast_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "observation_date", "signal_date", "target_start_date", "target_end_date",
            "target_log1p_semivariance", "baseline_prediction", "augmented_prediction",
            "icsa_change_4w_pct", "train_n",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result.get("forecast_rows", []))
    update_documents(result, result["report_path"], result["manifest_path"], result["forecast_path"])
    return result["report_path"], result["manifest_path"], result["forecast_path"]


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE/INFEASIBLE",
            "decision": "INCONCLUSIVE/INFEASIBLE",
            "disposition": f"INCONCLUSIVE/INFEASIBLE — frozen source or implementation acceptance failed: {error}",
            "completed_backtest": False,
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "The 2026-11-27 minimum was already met by two distinct real-data forecast screens; this failed attempt does not count as another backtest.",
            "data_scope": "source acceptance incomplete",
            "error": error,
            "forecast_rows": [],
        }
    report_path, manifest_path, forecast_path = write_outputs(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": result["status"],
        "decision": result.get("decision"),
        "completed_backtest": result.get("completed_backtest", False),
        "report_path": report_path,
        "manifest_path": manifest_path,
        "forecast_path": forecast_path,
        "validation_n": (result.get("validation_metrics") or {}).get("n"),
        "test_n": (result.get("test_metrics") or {}).get("n"),
        "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
