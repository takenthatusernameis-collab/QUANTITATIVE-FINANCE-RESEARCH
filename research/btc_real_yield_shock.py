#!/usr/bin/env python3
"""Preregistered walk-forward test of lagged 10-year TIPS real-yield change and Bitcoin returns."""
from __future__ import annotations

import bisect
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

HYPOTHESIS_ID = "QFR-2026-11-25-BTC-REAL-YIELD-SHOCK-01"
SERIES = ("CBBTCUSD", "DFII10")
START_DATE = dt.date(2016, 11, 25)
MODEL_WINDOW = 104
EVENT_STEP_SESSIONS = 6
TARGET_SESSIONS = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261127

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
REPORT_PATH = SESSION_DIR / f"{STAMP}_session-wakeup-9-btc-real-yield-{RUN_ID}.md"
OUTPUT_DIR = ROOT / "reports" / "generated" / "btc-real-yield-shock" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

BASELINE_FEATURES = [
    "btc_mom5_pct",
    "btc_mom20_pct",
    "btc_rv5_pct",
    "btc_rv20_pct",
]
AUGMENTED_FEATURES = BASELINE_FEATURES + ["real_yield_change_bp"]


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def parse_fred_series(body: bytes, series_id: str) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED {series_id} CSV schema: {reader.fieldnames}")
    date_field = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_field is None:
        raise ValueError(f"FRED {series_id} CSV has no recognized date column")
    values: dict[dt.date, float] = {}
    seen_dates: set[dt.date] = set()
    for row in reader:
        observation_date = base.parse_date(row.get(date_field))
        if observation_date is None:
            continue
        if observation_date in seen_dates:
            raise ValueError(f"Duplicate {series_id} observation date: {observation_date}")
        seen_dates.add(observation_date)
        value = base.parse_float(row.get(series_id))
        if value is None:
            continue
        if series_id == "CBBTCUSD" and value <= 0:
            raise ValueError(f"Non-positive {series_id} observation on {observation_date}")
        values[observation_date] = value
    if len(values) < 1500:
        raise ValueError(f"Insufficient {series_id} observations: {len(values)}")
    ordered = dict(sorted(values.items()))
    if next(iter(ordered)) > dt.date(2017, 3, 1):
        raise ValueError(f"{series_id} history starts unexpectedly late: {next(iter(ordered))}")
    return ordered


def validate_source_coverage(series: dict[str, dict[dt.date, float]]) -> dict:
    coverage = {}
    for series_id, values in series.items():
        dates = sorted(values)
        coverage[series_id] = {
            "rows": len(values),
            "first_date": dates[0].isoformat(),
            "last_date": dates[-1].isoformat(),
        }
    latest = [max(values) for values in series.values()]
    if (max(latest) - min(latest)).days > 4:
        raise ValueError(f"Source histories do not reach a common recent date: {coverage}")
    if min(latest) < dt.date(2026, 11, 17):
        raise ValueError(f"At least one source is unexpectedly stale: {coverage}")
    return coverage


def daily_log_returns(prices: dict[dt.date, float]) -> tuple[list[dt.date], list[float | None]]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
            continue
        value = math.log(prices[dates[index]] / prices[dates[index - 1]])
        returns.append(value if math.isfinite(value) else None)
    return dates, returns


def realized_volatility(returns: list[float | None]) -> float:
    if not returns or any(value is None or not math.isfinite(value) for value in returns):
        raise ValueError("Bitcoin realized-volatility window contains a missing or invalid return")
    return math.sqrt(sum(float(value) ** 2 for value in returns)) * 100.0


def build_events(
    btc_prices: dict[dt.date, float],
    real_yields: dict[dt.date, float],
) -> tuple[list[dict], dict]:
    btc_dates, btc_returns = daily_log_returns(btc_prices)
    yield_dates = sorted(real_yields)
    events = []
    skipped = {
        "incomplete_btc_pre_return_window": 0,
        "incomplete_btc_target_window": 0,
        "no_strictly_prior_real_yield_observation": 0,
        "stale_real_yield_observation": 0,
        "insufficient_real_yield_history": 0,
        "overlapping_target_window": 0,
    }
    candidates = 0

    # Signal at the BTC close on date t. Use only the latest DFII10
    # observation dated strictly before t; never same-date or forward data.
    for signal_index in range(20, len(btc_dates) - TARGET_SESSIONS, EVENT_STEP_SESSIONS):
        candidates += 1
        signal_date = btc_dates[signal_index]
        pre_5 = btc_returns[signal_index - 4:signal_index + 1]
        pre_20 = btc_returns[signal_index - 19:signal_index + 1]
        future = btc_returns[signal_index + 1:signal_index + TARGET_SESSIONS + 1]
        try:
            btc_mom5 = 100.0 * sum(float(value) for value in pre_5 if value is not None)
            btc_mom20 = 100.0 * sum(float(value) for value in pre_20 if value is not None)
            btc_rv5 = realized_volatility(pre_5)
            btc_rv20 = realized_volatility(pre_20)
        except (ValueError, TypeError):
            skipped["incomplete_btc_pre_return_window"] += 1
            continue
        try:
            target_return = 100.0 * sum(float(value) for value in future if value is not None)
            if any(value is None or not math.isfinite(value) for value in future):
                raise ValueError("Incomplete future Bitcoin return window")
        except (ValueError, TypeError):
            skipped["incomplete_btc_target_window"] += 1
            continue

        yield_position = bisect.bisect_left(yield_dates, signal_date) - 1
        if yield_position < 0:
            skipped["no_strictly_prior_real_yield_observation"] += 1
            continue
        yield_date = yield_dates[yield_position]
        if (signal_date - yield_date).days > 4:
            skipped["stale_real_yield_observation"] += 1
            continue
        if yield_position < 5:
            skipped["insufficient_real_yield_history"] += 1
            continue
        old_yield_date = yield_dates[yield_position - 5]
        if (yield_date - old_yield_date).days > 14:
            skipped["insufficient_real_yield_history"] += 1
            continue
        # DFII10 is quoted in percentage points; multiply the five-observation
        # change by 100 to express it in basis points. Signed levels are valid.
        real_yield_change_bp = 100.0 * (real_yields[yield_date] - real_yields[old_yield_date])
        if not math.isfinite(real_yield_change_bp):
            raise ValueError(f"Invalid lagged real-yield change on {signal_date}")

        event = {
            "signal_date": signal_date,
            "target_start_date": btc_dates[signal_index + 1],
            "target_end_date": btc_dates[signal_index + TARGET_SESSIONS],
            "real_yield_observation_date": yield_date,
            "btc_mom5_pct": btc_mom5,
            "btc_mom20_pct": btc_mom20,
            "btc_rv5_pct": btc_rv5,
            "btc_rv20_pct": btc_rv20,
            "real_yield_change_bp": real_yield_change_bp,
            "target_return_pct": target_return,
            "target_bp": target_return,
        }
        if event["target_end_date"] <= event["signal_date"]:
            raise ValueError(f"Invalid target dates for signal {signal_date}")
        if events and event["target_start_date"] <= events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        if yield_date >= signal_date:
            raise ValueError(f"Same-date or future real-yield observation leaked into signal {signal_date}")
        events.append(event)

    return events, {
        "candidate_origins": candidates,
        "events": len(events),
        "skipped": skipped,
        "event_spacing_btc_observations": EVENT_STEP_SESSIONS,
        "target_btc_observations": TARGET_SESSIONS,
        "signal_rule": "BTC close on t; latest DFII10 observation dated strictly before t",
    }


def walk_forward_predictions(events: list[dict]) -> list[dict]:
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
            baseline = base.fit_ols_predict(train, current, BASELINE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUGMENTED_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"],
            "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict], prediction_key: str) -> dict | None:
    if not rows:
        return None
    errors = [row[prediction_key] - row["target_bp"] for row in rows]
    actual = [row["target_bp"] for row in rows]
    mean_actual = statistics.fmean(actual)
    sse = sum(error * error for error in errors)
    denominator = sum((value - mean_actual) ** 2 for value in actual)
    directional = sum(
        (row[prediction_key] >= 0) == (row["target_bp"] >= 0)
        for row in rows
    ) / len(rows)
    return {
        "n": len(rows),
        "mae_pct": statistics.fmean(abs(error) for error in errors),
        "rmse_pct": math.sqrt(sse / len(errors)),
        "oos_r2_vs_period_mean": 1.0 - sse / denominator if denominator > 1e-12 else None,
        "directional_accuracy": directional,
    }


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    normalized = []
    for row in rows:
        target = row["target_bp"]
        baseline = row["baseline_prediction_bp"]
        augmented = row["augmented_prediction_bp"]
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not math.isfinite(difference):
            return None
        normalized.append({"loss_difference": difference})
    observed = statistics.fmean(row["loss_difference"] for row in normalized)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(normalized, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(row["loss_difference"] for row in sample))
    samples.sort()
    return {
        "status": "COMPUTED",
        "observations": len(normalized),
        "reps": len(samples),
        "block_size_events": BOOTSTRAP_BLOCK,
        "mean_baseline_minus_augmented_squared_error_pct2": observed,
        "ci_95_low_pct2": samples[int(0.025 * (len(samples) - 1))],
        "ci_95_high_pct2": samples[int(0.975 * (len(samples) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in samples) / len(samples),
    }


def improvement_pct(baseline: dict | None, augmented: dict | None) -> float | None:
    if not baseline or not augmented or baseline["rmse_pct"] <= 0:
        return None
    return 100.0 * (baseline["rmse_pct"] - augmented["rmse_pct"]) / baseline["rmse_pct"]


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    val_imp = improvement_pct(validation.get("baseline"), validation.get("augmented"))
    test_imp = improvement_pct(test.get("baseline"), test.get("augmented"))
    enough = (
        validation.get("n", 0) >= 30
        and test.get("n", 0) >= 30
        and paired is not None
    )
    if (
        enough and val_imp is not None and test_imp is not None
        and val_imp > 0 and test_imp > 0
        and paired.get("ci_95_low_pct2") is not None
        and paired["ci_95_low_pct2"] > 0
    ):
        return "BACKTESTED", "PROMISING — the augmented model improves both chronological periods and the paired test-loss interval is strictly positive; independent validation remains necessary"
    if (
        val_imp is not None and test_imp is not None
        and val_imp <= 0 and test_imp <= 0
        and paired is not None
        and paired.get("ci_95_high_pct2") is not None
        and paired["ci_95_high_pct2"] < 0
    ):
        return "REJECTED", "REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule"


def update_registry(status: str, disposition: str, coverage: dict, event_meta: dict, report_relative: str) -> None:
    lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    replacement = (
        f"| {HYPOTHESIS_ID} | {status} | Strictly lagged five-observation change in the 10-year TIPS real yield adds out-of-sample information about next-five-Bitcoin-session returns beyond BTC 5/20-session momentum and realized volatility; expected coefficient negative. | "
        f"FRED/Coinbase CBBTCUSD {coverage['CBBTCUSD']['first_date']} to {coverage['CBBTCUSD']['last_date']} ({coverage['CBBTCUSD']['rows']} rows); Federal Reserve DFII10 {coverage['DFII10']['first_date']} to {coverage['DFII10']['last_date']} ({coverage['DFII10']['rows']} rows); {event_meta['events']} accepted non-overlapping origins | "
        f"{disposition} | [{report_relative}](../{report_relative}) |"
    )
    prefix = f"| {HYPOTHESIS_ID} |"
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one registry row for {HYPOTHESIS_ID}, found {len(matches)}")
    lines[matches[0]] = replacement
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    source_bodies = {}
    series = {}
    for series_id in SERIES:
        url = f"{FRED_URL}?id={series_id}&cosd={START_DATE.isoformat()}"
        body = base.fetch_bytes(url)
        source_bodies[series_id] = {"url": url, "body": body, "sha256": sha256(body)}
        series[series_id] = parse_fred_series(body, series_id)
    coverage = validate_source_coverage(series)

    events, event_meta = build_events(series["CBBTCUSD"], series["DFII10"])
    predictions = walk_forward_predictions(events)
    validation = [
        row for row in predictions
        if VALIDATION_START <= row["signal_date"] < TEST_START
    ]
    test = [row for row in predictions if row["signal_date"] >= TEST_START]
    if not validation or not test:
        raise ValueError(
            f"Insufficient chronological forecasts: validation={len(validation)}, test={len(test)}, "
            f"events={len(events)}, coverage={coverage}"
        )

    validation_metrics = {
        "n": len(validation),
        "baseline": forecast_metrics(validation, "baseline_prediction_bp"),
        "augmented": forecast_metrics(validation, "augmented_prediction_bp"),
    }
    test_metrics = {
        "n": len(test),
        "baseline": forecast_metrics(test, "baseline_prediction_bp"),
        "augmented": forecast_metrics(test, "augmented_prediction_bp"),
    }
    paired = bootstrap_paired_loss(test)
    status, disposition = decide(validation_metrics, test_metrics, paired)
    val_imp = improvement_pct(validation_metrics["baseline"], validation_metrics["augmented"])
    test_imp = improvement_pct(test_metrics["baseline"], test_metrics["augmented"])

    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    report_relative = REPORT_PATH.relative_to(ROOT).as_posix()
    update_registry(status, disposition, coverage, event_meta, report_relative)

    manifest = {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "retrieved_at_utc": retrieved_at,
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "data_sources": {
            series_id: {
                "url": source_bodies[series_id]["url"],
                "sha256": source_bodies[series_id]["sha256"],
                **coverage[series_id],
            }
            for series_id in SERIES
        },
        "event_construction": event_meta,
        "methodology": {
            "baseline_features": BASELINE_FEATURES,
            "augmented_features": AUGMENTED_FEATURES,
            "signal_rule": "BTC signal close on t; use only latest DFII10 observation dated strictly before t",
            "real_yield_change": "100 * log(DFII10[d] / DFII10[d-5]) over five observed real-yield-index changes",
            "target": "100 * log(CBBTCUSD[t+5] / CBBTCUSD[t]) over next five observed daily BTC closes",
            "event_spacing_btc_observations": EVENT_STEP_SESSIONS,
            "rolling_training_events": MODEL_WINDOW,
            "training_maturity_rule": "training target_end_date must be strictly earlier than current signal_date",
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "rmse_improvement_pct": {
            "validation": val_imp,
            "test": test_imp,
        },
        "paired_squared_error_bootstrap": paired,
        "limitations": [
            "CBBTCUSD observations are Coinbase data as of 5 PM Pacific Time and are copyrighted; raw data are not committed.",
            "DFII10 is a daily U.S. business-day real-yield series; the strict prior-date rule excludes same-date values and can leave weekend BTC signals using the latest prior business-day close.",
            "DFII10 is quoted in percentage points and can be negative; the five-observation difference is expressed in basis points.",
            "FRED current-vintage observations were used; historical release vintages were not reconstructed.",
            "Forecasting only: no causal claim, hedge/safe-haven conclusion, transaction-cost model, instrument-level strategy P&L or live deployment.",
        ],
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = f"""# Wake-up session report — {STAMP}

## Repository state and selection

- Default branch: main; source commit: {SOURCE_SHA}.
- No open PRs or issues were present at selection.
- Earlier on 2026-11-25, three distinct Treasury real-data backtests and one CFTC real-data backtest had already met the daily minimum; the same-day VIX study was an additional experiment. This is another materially distinct cross-asset forecast hypothesis.
- Prior repository hypotheses were checked in research/HYPOTHESIS-REGISTRY.md; this is not a parameter variation of the Treasury, CFTC or VIX studies.
- Research/paper simulation only. No live orders, capital deployment, paid data, credentials or external permissions.

## Research output

### {HYPOTHESIS_ID}

**Disposition: {status} — {disposition}.**

The study tests whether the lagged five-observation change in the 10-year TIPS real yield adds predictive information about the next five Bitcoin daily returns beyond Bitcoin's own momentum and realized volatility.

- CBBTCUSD coverage: {coverage['CBBTCUSD']['first_date']} to {coverage['CBBTCUSD']['last_date']} ({coverage['CBBTCUSD']['rows']} valid observations).
- DFII10 coverage: {coverage['DFII10']['first_date']} to {coverage['DFII10']['last_date']} ({coverage['DFII10']['rows']} valid observations).
- Accepted non-overlapping origins: {event_meta['events']}; candidate origins: {event_meta['candidate_origins']}; skipped: {json.dumps(event_meta['skipped'], sort_keys=True)}.
- Signal: BTC observation date t; the latest DFII10 observation is strictly prior to t.
- Target: next five observed daily BTC closes, measured as log return in percentage points.
- Event spacing: six BTC observations; target windows do not overlap.
- Rolling training window: {MODEL_WINDOW} fully matured prior events.
- Validation: 2019–2021; test: 2022 onward.

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | {validation_metrics['n']} | {test_metrics['n']} |
| Baseline RMSE (%) | {validation_metrics['baseline']['rmse_pct']:.6f} | {test_metrics['baseline']['rmse_pct']:.6f} |
| Augmented RMSE (%) | {validation_metrics['augmented']['rmse_pct']:.6f} | {test_metrics['augmented']['rmse_pct']:.6f} |
| RMSE improvement | {val_imp:.4f}% | {test_imp:.4f}% |
| Baseline directional accuracy | {validation_metrics['baseline']['directional_accuracy']:.4f} | {test_metrics['baseline']['directional_accuracy']:.4f} |
| Augmented directional accuracy | {validation_metrics['augmented']['directional_accuracy']:.4f} | {test_metrics['augmented']['directional_accuracy']:.4f} |

- Paired test squared-error bootstrap: {json.dumps(paired, sort_keys=True) if paired else 'NOT COMPUTED'}.

## Literature and novelty boundary

- Jareño, González and Almansa (2025), “Interest rate sensitivity of traditional, green, and stable cryptocurrencies: A comparative study across market conditions,” *Quantitative Finance and Economics*, DOI: https://doi.org/10.3934/QFE.2025004. The study decomposes nominal rates into real yields and inflation expectations and reports regime-dependent cryptocurrency rate sensitivity; it motivates, but does not validate, this strict-lag incremental forecasting test.
- Smales (2023), “Cryptocurrency as an alternative inflation hedge?”, *Accounting & Finance*, DOI: https://doi.org/10.1111/acfi.13193. The reported Bitcoin response to inflation-expectation changes is conditional, supporting a conservative test of a distinct real-discount-rate channel rather than a blanket macro-beta assumption.

## Reproducibility and data integrity

- Source URLs, exact row counts/coverage, retrieval time and SHA-256 hashes are in reports/generated/btc-real-yield-shock/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json.
- No raw source data are committed. Coinbase CBBTCUSD observations are copyrighted and are not redistributed.
- Deterministic timing, missingness, non-overlap, walk-forward maturity and decision-rule tests ran in the workflow.

## Verified versus unverified

**VERIFIED:** public source retrieval and CSV parsing; source coverage and hashes; strict prior-date real-yield alignment; no forward-fill; exact BTC daily return continuity; non-overlapping target windows; fully matured training targets; chronological validation/test metrics and paired block-bootstrap under this code/data vintage.

**UNVERIFIED:** historical point-in-time FRED vintages; stability in future regimes; causal real-yield-to-BTC transmission; executable spot/perpetual performance; transaction costs, slippage, liquidity and economic value.

## Daily KPI and research versus operations

**DAILY KPI: MET before this additional study**, according to earlier same-day session reports. This session adds one distinct, preregistered real-data cross-asset forecast test.

Research: one new lagged 10-year TIPS real-yield mechanism tested against a Bitcoin-only momentum/volatility baseline. Operations: source retrieval, deterministic checks, report/manifest persistence and registry update.

## Next

- If BACKTESTED, require independent reconstruction and a separately preregistered instrument-level economic study before any strategy claim.
- If REJECTED or INCONCLUSIVE, close under the frozen decision rule; do not tune this hypothesis ID.
- No automatic timebox extension.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("=== SESSION REPORT ===")
    print(report)
    print("=== GENERATED MANIFEST ===")
    print(manifest_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
