#!/usr/bin/env python3
"""Preregistered forecast screen: Bitcoin Wikipedia attention and BTC downside semivariance."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import statistics
import time
from pathlib import Path

import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc
import wikipedia_attention_source_preflight as source

HYPOTHESIS_ID = "QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01"
PAGEVIEW_START_DATE = dt.date(2017, 8, 17)
PAGEVIEW_END_DATE = dt.date(2026, 11, 18)
BTC_START_DATE = dt.date(2017, 8, 17)
BTC_END_DATE = dt.date(2026, 11, 25)
SIGNAL_END_DATE = dt.date(2026, 11, 20)
EVENT_STEP_DAYS = 6
TARGET_SESSIONS = 5
MODEL_WINDOW = 104
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2022, 1, 1)
MIN_VALIDATION_N = 60
MIN_TEST_N = 100
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
BOOTSTRAP_SEED = 20261126
ARCHIVE_WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "wikipedia-attention-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01.md"

BASE_FEATURES = [
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
]
AUG_FEATURES = BASE_FEATURES + ["wikipedia_attention_7d_log_change"]


def complete_pageview_calendar(values: dict[dt.date, int], start: dt.date, end: dt.date):
    """Reconstruct only Wikimedia-documented omitted zero-view days; reject longer gaps."""
    coverage = source.validate_pageview_coverage(values, start, end)
    expected = []
    day = start
    missing = []
    while day <= end:
        expected.append(day)
        if day not in values:
            missing.append(day)
        day += dt.timedelta(days=1)
    completed = {day: values.get(day, 0) for day in expected}
    if len(completed) != len(expected):
        raise ValueError("Wikimedia zero-view reconstruction did not produce a complete calendar")
    return completed, coverage, missing


def fetch_pageviews():
    """Fetch the frozen Wikimedia sample sequentially and preserve response digests."""
    values: dict[dt.date, int] = {}
    chunks = []
    for index, (chunk_start, chunk_end) in enumerate(
        source.iter_date_chunks(PAGEVIEW_START_DATE, PAGEVIEW_END_DATE), start=1
    ):
        url = source.build_pageviews_url(chunk_start, chunk_end)
        body = source.fetch_bytes(url, timeout=30)
        parsed = source.parse_pageviews(body, chunk_start, chunk_end)
        overlap = set(values).intersection(parsed)
        if overlap:
            raise ValueError(f"Overlapping Wikimedia chunk dates: {sorted(overlap)[:3]}")
        values.update(parsed)
        chunks.append({
            "chunk": index,
            "start": chunk_start.isoformat(),
            "end": chunk_end.isoformat(),
            "observed_rows": len(parsed),
            "response_sha256": hashlib.sha256(body).hexdigest(),
        })
        if chunk_end < PAGEVIEW_END_DATE:
            time.sleep(0.7)

    completed, coverage, missing = complete_pageview_calendar(
        values, PAGEVIEW_START_DATE, PAGEVIEW_END_DATE
    )
    combined_sha = hashlib.sha256(
        "\n".join(item["response_sha256"] for item in chunks).encode("ascii")
    ).hexdigest()
    metadata = {
        "endpoint": source.PAGEVIEWS_BASE,
        "project": source.PROJECT,
        "project_endpoint": source.PROJECT_PATH,
        "article": source.ARTICLE,
        "access": source.ACCESS,
        "agent": source.AGENT,
        "granularity": source.GRANULARITY,
        "first_date": PAGEVIEW_START_DATE.isoformat(),
        "last_date": PAGEVIEW_END_DATE.isoformat(),
        "observed_rows": len(values),
        "calendar_rows_after_zero_reconstruction": len(completed),
        "reconstructed_zero_view_dates": [day.isoformat() for day in missing],
        "chunk_count": len(chunks),
        "chunks": chunks,
        "combined_response_sha256": combined_sha,
        "coverage": coverage,
        "vintage": "current Wikimedia API response; historical point-in-time revisions and publication timestamps are not reconstructed",
    }
    return completed, metadata


def fetch_sources():
    pageviews, pageview_meta = fetch_pageviews()

    info_url = btc.BINANCE_EXCHANGE_INFO + "?symbol=BTCUSDT"
    info_body = base.fetch_bytes(info_url, timeout=20)
    market = source.validate_binance_exchange_info(info_body)

    specs = btc.build_archive_specs(
        BTC_START_DATE, BTC_END_DATE, as_of_date=NOW.date()
    )
    results: dict[int, tuple[dict, dict]] = {}
    failures = []
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
                    "kind": spec["kind"],
                    "period": spec["tag"],
                    "url": spec["url"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        failures.sort(key=lambda item: (item["kind"], item["period"]))
        raise RuntimeError(
            f"Binance Vision archive ingestion failed for {len(failures)}/{len(specs)} archives: "
            f"{json.dumps(failures, sort_keys=True)}"
        )

    prices: dict[dt.date, float] = {}
    archive_manifest = []
    timestamp_units = set()
    for index in range(len(specs)):
        page, manifest_row = results[index]
        archive_manifest.append(manifest_row)
        timestamp_units.add(manifest_row["timestamp_unit"])
        for day, close in page.items():
            if BTC_START_DATE <= day <= BTC_END_DATE:
                if day in prices:
                    raise ValueError(f"Duplicate BTCUSDT date across archives: {day}")
                prices[day] = close

    prices = dict(sorted(prices.items()))
    archive_manifest_sha = hashlib.sha256(
        json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    sources = {
        "WIKIMEDIA_PAGEVIEWS": pageview_meta,
        "BINANCE_EXCHANGE_INFO": {
            **market,
            "endpoint": info_url,
            "response_sha256": hashlib.sha256(info_body).hexdigest(),
        },
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "market_status": market["status"],
            "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
            "interval": "1d",
            "timezone": "UTC",
            "rows": len(prices),
            "first_date": min(prices).isoformat() if prices else None,
            "last_date": max(prices).isoformat() if prices else None,
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(item["kind"] == "monthly" for item in archive_manifest),
            "daily_archive_count": sum(item["kind"] == "daily" for item in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_manifest_sha,
            "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
    }
    return pageviews, prices, sources


def validate_coverage(pageviews: dict, prices: dict) -> dict:
    pageview_dates = sorted(pageviews)
    price_dates = sorted(prices)
    expected_pageview_rows = (PAGEVIEW_END_DATE - PAGEVIEW_START_DATE).days + 1
    expected_price_rows = (BTC_END_DATE - BTC_START_DATE).days + 1

    if len(pageviews) != expected_pageview_rows:
        raise ValueError(
            f"Wikimedia calendar coverage is incomplete: {len(pageviews)} != {expected_pageview_rows}"
        )
    if pageview_dates[0] != PAGEVIEW_START_DATE or pageview_dates[-1] != PAGEVIEW_END_DATE:
        raise ValueError(
            f"Wikimedia reconstructed coverage does not match frozen boundaries: "
            f"{pageview_dates[0]} to {pageview_dates[-1]}"
        )
    if len(prices) != expected_price_rows:
        raise ValueError(
            f"BTCUSDT archive row count is incomplete: {len(prices)} != {expected_price_rows}"
        )
    if price_dates[0] != BTC_START_DATE or price_dates[-1] != BTC_END_DATE:
        raise ValueError(
            f"BTCUSDT archive coverage does not match frozen boundaries: "
            f"{price_dates[0]} to {price_dates[-1]}"
        )
    pageview_gaps = [(b - a).days for a, b in zip(pageview_dates, pageview_dates[1:])]
    price_gaps = [(b - a).days for a, b in zip(price_dates, price_dates[1:])]
    if any(gap != 1 for gap in pageview_gaps):
        raise ValueError("Wikimedia reconstructed daily calendar has a gap")
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("Binance BTCUSDT daily archive history has a missing UTC date")
    if any(not math.isfinite(value) or value <= 0 for value in prices.values()):
        raise ValueError("BTCUSDT contains a non-positive or non-finite close")
    return {
        "WIKIMEDIA_PAGEVIEWS": {
            "rows": len(pageviews),
            "first_date": pageview_dates[0].isoformat(),
            "last_date": pageview_dates[-1].isoformat(),
            "observed_rows": len(pageviews) - sum(
                1 for value in pageviews.values() if value == 0
            ),
            "reconstructed_zero_view_days": sum(
                1 for value in pageviews.values() if value == 0
            ),
        },
        "BTCUSDT": {
            "rows": len(prices),
            "first_date": price_dates[0].isoformat(),
            "last_date": price_dates[-1].isoformat(),
        },
    }


def build_events(pageviews: dict[dt.date, int], prices: dict[dt.date, float]):
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
        else:
            returns.append(math.log(prices[dates[index]] / prices[dates[index - 1]]))

    index_by_date = {day: index for index, day in enumerate(dates)}
    anchor = BTC_START_DATE + dt.timedelta(days=20)
    events = []
    skipped = {
        "missing_pageview_feature_date": 0,
        "missing_signal_close": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_returns": 0,
    }
    candidates = 0

    for signal_date in dates:
        if signal_date < anchor or signal_date > SIGNAL_END_DATE:
            continue
        if (signal_date - anchor).days % EVENT_STEP_DAYS:
            continue
        candidates += 1

        recent_pageview_date = signal_date - dt.timedelta(days=2)
        prior_pageview_date = signal_date - dt.timedelta(days=9)
        if recent_pageview_date not in pageviews or prior_pageview_date not in pageviews:
            skipped["missing_pageview_feature_date"] += 1
            continue

        index = index_by_date[signal_date]
        if index < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if index + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue

        prior5 = returns[index - 4:index + 1]
        prior20 = returns[index - 19:index + 1]
        future = returns[index + 1:index + 1 + TARGET_SESSIONS]
        if any(value is None or not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue

        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = btc.semi_var_pct2(future_values)
        events.append({
            "signal_date": signal_date,
            "target_start_date": dates[index + 1],
            "target_end_date": dates[index + TARGET_SESSIONS],
            "pageview_recent_date": recent_pageview_date,
            "pageview_prior_date": prior_pageview_date,
            "pageview_recent_views": pageviews[recent_pageview_date],
            "pageview_prior_views": pageviews[prior_pageview_date],
            "wikipedia_attention_7d_log_change": (
                math.log1p(pageviews[recent_pageview_date])
                - math.log1p(pageviews[prior_pageview_date])
            ),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
        })

    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("BTC target windows overlap or are not fully matured")
    event_meta = {
        "candidate_origins": candidates,
        "accepted_events": len(events),
        "skipped": skipped,
        "event_step_calendar_days": EVENT_STEP_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "signal_start_rule": "first BTCUSDT UTC daily close after 20 complete prior returns",
        "signal_end_date": SIGNAL_END_DATE.isoformat(),
        "feature_rule": "log1p(pageviews[d-2]) - log1p(pageviews[d-9]); exact dates only after documented zero-view reconstruction",
        "target_rule": "mean(min(next-five UTC daily log return, 0)^2) * 10000",
        "first_accepted_signal": events[0]["signal_date"].isoformat() if events else None,
        "last_accepted_signal": events[-1]["signal_date"].isoformat() if events else None,
    }
    return events, event_meta


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
            "target_semivariance_pct2": current["target_semivariance_pct2"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "attention_feature": current["wikipedia_attention_7d_log_change"],
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


def bootstrap_paired_loss(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    loss_rows = []
    for row in rows:
        target = float(row["target_bp"])
        baseline = float(row["baseline_prediction_bp"])
        augmented = float(row["augmented_prediction_bp"])
        difference = (baseline - target) ** 2 - (augmented - target) ** 2
        if not all(math.isfinite(value) for value in (target, baseline, augmented, difference)):
            return None
        loss_rows.append({"loss_difference": difference})
    observed = statistics.fmean(row["loss_difference"] for row in loss_rows)
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap_means = []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(loss_rows, rng, BOOTSTRAP_BLOCK)
        bootstrap_means.append(statistics.fmean(row["loss_difference"] for row in sample))
    bootstrap_means.sort()
    return {
        "status": "COMPUTED",
        "observations": len(loss_rows),
        "reps": len(bootstrap_means),
        "block_size_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "observed_mean_baseline_minus_augmented_squared_loss": observed,
        "ci_95_low": bootstrap_means[int(0.025 * (len(bootstrap_means) - 1))],
        "ci_95_high": bootstrap_means[int(0.975 * (len(bootstrap_means) - 1))],
        "bootstrap_fraction_positive": sum(value > 0 for value in bootstrap_means) / len(bootstrap_means),
    }


def decide(validation: dict, test: dict, paired: dict | None):
    if (
        validation["n"] < MIN_VALIDATION_N
        or test["n"] < MIN_TEST_N
        or paired is None
        or validation["baseline"] is None
        or test["baseline"] is None
    ):
        return "INCONCLUSIVE", (
            "INCONCLUSIVE — the frozen minimum validation/test sample or paired-loss inference was not met"
        )
    validation_improvement = validation["rmse_improvement_pct"]
    test_improvement = test["rmse_improvement_pct"]
    if (
        validation_improvement is not None
        and test_improvement is not None
        and validation_improvement > 0
        and test_improvement > 0
        and paired["ci_95_low"] > 0
    ):
        return "BACKTESTED", (
            "PROMISING FORECAST SCREEN — validation and test RMSE both improve and the paired test-loss "
            "95% lower confidence bound is positive; independent validation remains necessary"
        )
    if (
        validation_improvement is not None
        and test_improvement is not None
        and validation_improvement < 0
        and test_improvement < 0
        and paired["ci_95_high"] < 0
    ):
        return "REJECTED", (
            "REJECTED — validation and test RMSE both worsen and the paired test-loss "
            "95% upper confidence bound is negative"
        )
    return "INCONCLUSIVE", (
        "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"
    )


def run_research() -> dict:
    pageviews, prices, sources = fetch_sources()
    coverage = validate_coverage(pageviews, prices)
    events, event_meta = build_events(pageviews, prices)
    predictions = walk_forward(events)
    validation_rows = [
        row for row in predictions
        if VALIDATION_START <= row["signal_date"] < TEST_START
    ]
    test_rows = [
        row for row in predictions
        if TEST_START <= row["signal_date"] <= SIGNAL_END_DATE
    ]
    validation = metrics(validation_rows)
    test = metrics(test_rows)
    paired = bootstrap_paired_loss(test_rows)
    status, disposition = decide(validation, test, paired)

    scope = (
        f"English-Wikipedia Bitcoin user pageviews {PAGEVIEW_START_DATE} to {PAGEVIEW_END_DATE} "
        f"({coverage['WIKIMEDIA_PAGEVIEWS']['rows']} calendar dates); "
        f"Binance BTCUSDT Spot 1d UTC {coverage['BTCUSDT']['first_date']} to "
        f"{coverage['BTCUSDT']['last_date']} ({coverage['BTCUSDT']['rows']} candles); "
        f"{len(events)} accepted six-day-spaced events; validation 2019-2021; test 2022-11-20"
    )
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
            "MET before this additional study by distinct 2026-11-26 real-data backtests, including "
            "MEXC BTC funding run 45850573983 and DeFiLlama stablecoin-supply run 45855398478."
        ),
        "coverage": coverage,
        "data_sources": sources,
        "event_construction": event_meta,
        "data_scope": scope,
        "methodology": {
            "baseline_features": BASE_FEATURES,
            "augmented_features": AUG_FEATURES,
            "predictor": "log1p(pageviews[d-2]) - log1p(pageviews[d-9])",
            "availability": (
                "Signal at the BTCUSDT UTC daily close on d; exact pageview dates d-2 and d-9 "
                "provide a two-calendar-day embargo"
            ),
            "target": "log1p(next-five-session BTC downside semivariance, percentage-points-squared units)",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "all training signals and target_end dates strictly precede the current signal",
            "event_step_calendar_days": EVENT_STEP_DAYS,
            "validation": "2019-01-01 through 2021-12-31",
            "test": "2022-01-01 through 2026-11-20",
            "minimum_validation_forecasts": MIN_VALIDATION_N,
            "minimum_test_forecasts": MIN_TEST_N,
            "bootstrap_reps": BOOTSTRAP_REPS,
            "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "summary_metrics": {
            "validation_n": validation["n"],
            "test_n": test["n"],
            "validation_baseline_rmse": (
                validation["baseline"]["rmse_bp"] if validation["baseline"] else None
            ),
            "validation_augmented_rmse": (
                validation["augmented"]["rmse_bp"] if validation["augmented"] else None
            ),
            "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
            "test_baseline_rmse": test["baseline"]["rmse_bp"] if test["baseline"] else None,
            "test_augmented_rmse": test["augmented"]["rmse_bp"] if test["augmented"] else None,
            "test_rmse_improvement_pct": test["rmse_improvement_pct"],
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "Wikipedia pageviews proxy public interest; they do not identify investors, sentiment, search intent or order flow.",
            "Pageview counts can be affected by news, article edits, platform changes and non-investor activity.",
            "The current API vintage is used. Historical point-in-time revisions and exact historical publication timestamps are not reconstructed; the two-day embargo is not proof of historical availability.",
            "The documented zero-view reconstruction applies only to omitted daily dates; no interpolation or forward-fill is performed.",
            "BTCUSDT is one venue's Spot series, not consolidated executable prices or derivatives P&L.",
            "This is an observational forecast screen, not causal evidence, a trading strategy or a live signal.",
            "No raw pageview or market observations are committed; response digests and Binance archive checksums are retained.",
        ],
    }


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = result.get("disposition", "INCONCLUSIVE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete")
    summary = result.get("summary_metrics") or {}
    completed = bool(result.get("completed_backtest"))
    metrics_text = (
        f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, "
        f"RMSE improvement={summary.get('validation_rmse_improvement_pct')}/"
        f"{summary.get('test_rmse_improvement_pct')} percent; forecast-only"
        if completed else "implementation/backtest attempt incomplete; no empirical performance conclusion"
    )
    report_link = "../" + report_path
    manifest_link = "../" + manifest_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged seven-calendar-day change in English-Wikipedia "
        f"Bitcoin-article user pageviews adds information about next-five-session BTC downside semivariance "
        f"beyond recent downside risk, realized variance and momentum. | {scope} | {disposition}; "
        f"{metrics_text} | [session report]({report_link}) / [manifest]({manifest_link}) |"
    )

    registry_lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next(
        (index for index, line in enumerate(registry_lines) if line.startswith(f"| {HYPOTHESIS_ID} |")),
        None,
    )
    if existing is None:
        separator = next(
            (index for index, line in enumerate(registry_lines) if line.startswith("|---")),
            None,
        )
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        registry_lines.insert(separator + 1, row)
    else:
        registry_lines[existing] = row
    REGISTRY_PATH.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")

    prereg_text = PREREG_PATH.read_text(encoding="utf-8")
    for marker in ("\n## Empirical disposition", "\n## Execution attempt"):
        if marker in prereg_text:
            prereg_text = prereg_text.split(marker, 1)[0]
    prereg_lines = prereg_text.splitlines()
    for index, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[index] = f"- **Status:** {status}"
            break
    prereg_text = "\n".join(prereg_lines).rstrip()

    if completed:
        section = (
            "\n\n## Empirical disposition\n\n"
            f"- **Final status:** {status}\n"
            f"- **Disposition:** {disposition}\n"
            "- **Completed real-data backtest:** yes\n"
            f"- **Data scope:** {scope}\n"
            f"- **Summary metrics:** {json.dumps(base.json_safe(summary), sort_keys=True)}\n"
            f"- **Paired test-loss bootstrap:** {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}\n"
            f"- **Report:** [{report_path}]({report_link})\n"
            f"- **Manifest:** [{manifest_path}]({manifest_link})\n"
            "- Forecast screen only; no causal, trading or deployment claim.\n"
        )
    else:
        section = (
            "\n\n## Execution attempt\n\n"
            "- **Disposition:** implementation/backtest attempt incomplete; the hypothesis remains "
            "FEASIBILITY_CHECKED and no performance conclusion is drawn.\n"
            f"- **Error:** {result.get('error', 'unspecified execution failure')}\n"
            f"- **Report:** [{report_path}]({report_link})\n"
            f"- **Manifest:** [{manifest_path}]({manifest_link})\n"
        )
    PREREG_PATH.write_text(prereg_text + section, encoding="utf-8")


def render_report(result: dict) -> str:
    lines = [
        "# Research session — Bitcoin Wikipedia attention and BTC downside semivariance",
        "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}",
        f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi')}",
        "- **Timebox:** LOW; two substantive cycles maximum; implementation deadline "
        "2026-11-27T19:02:30Z; final research-conclusion deadline 2026-11-28T19:02:30Z.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Triggering commit:** {SOURCE_SHA}",
        "",
    ]
    if not result.get("completed_backtest"):
        lines += [
            "## Execution blocker",
            "",
            f"- {result.get('error', 'No valid real-data backtest completed.')}",
            "- The source-feasibility preflight remains valid; this attempt did not produce a performance result.",
            "",
            "## Alternatives attempted",
            "",
        ]
        lines.extend(f"- {item}" for item in result.get("alternatives_attempted", []))
    else:
        validation = result["validation_metrics"]
        test = result["test_metrics"]
        pageviews = result["data_sources"]["WIKIMEDIA_PAGEVIEWS"]
        btc_source = result["data_sources"]["BTCUSDT"]
        lines += [
            "## Preregistered method",
            "",
            "- Signal: close of Binance BTCUSDT UTC daily candle on date d.",
            "- Feature: log1p(Wikipedia user pageviews[d-2]) minus log1p(pageviews[d-9]).",
            "- Baseline: prior-five and prior-twenty-session downside semivariance, prior-twenty-session realized variance, and prior-five/prior-twenty-session BTC log returns.",
            "- Augmented model: frozen baseline plus the single Wikipedia-attention feature.",
            "- Target: next-five-session BTC downside semivariance in percentage-points-squared units, forecast in log1p space.",
            "- Event spacing: six calendar days; 104 prior fully matured training events.",
            "- Validation: 2019-2021; test: 2022-11-20.",
            "",
            "## Source coverage and provenance",
            "",
            "| Source | First | Last | Rows | Digest / archive manifest |",
            "|---|---|---|---:|---|",
            f"| Wikimedia Bitcoin pageviews | {pageviews['first_date']} | {pageviews['last_date']} | {pageviews['calendar_rows_after_zero_reconstruction']} calendar; {pageviews['observed_rows']} observed | {pageviews['combined_response_sha256']} |",
            f"| Binance BTCUSDT Spot | {btc_source['first_date']} | {btc_source['last_date']} | {btc_source['rows']} | {btc_source['archive_count']} archives; {btc_source['archive_manifest_sha256']} |",
            "",
            f"- Reconstructed documented zero-view dates: {len(pageviews['reconstructed_zero_view_dates'])}.",
            f"- Pageview response chunks: {pageviews['chunk_count']}.",
            "- Raw pageviews and market observations are not committed.",
            "",
            "## Walk-forward results",
            "",
            "| Metric | Validation 2019-2021 | Test 2022 onward |",
            "|---|---:|---:|",
            f"| Forecasts | {validation['n']} | {test['n']} |",
            f"| Baseline RMSE, log1p semivariance | {validation['baseline']['rmse_bp'] if validation['baseline'] else None} | {test['baseline']['rmse_bp'] if test['baseline'] else None} |",
            f"| Augmented RMSE, log1p semivariance | {validation['augmented']['rmse_bp'] if validation['augmented'] else None} | {test['augmented']['rmse_bp'] if test['augmented'] else None} |",
            f"| RMSE improvement | {validation['rmse_improvement_pct']}% | {test['rmse_improvement_pct']}% |",
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
            "**VERIFIED:** current source schemas, frozen coverage, response digests, Binance archive checksums, feature embargo, non-overlapping targets, matured rolling training and computed forecast metrics.",
            "**UNVERIFIED:** historical point-in-time pageview revisions/publication timestamps, investor-specific interpretation, causality, independent replication and instrument-level economic value.",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    return "\n".join(lines) + "\n"


def write_outputs(result: dict):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-wikipedia-attention-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"] = str(report_path.relative_to(ROOT))
    result["manifest_path"] = str(manifest_path.relative_to(ROOT))
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    update_documents(result, result["report_path"], result["manifest_path"])
    return result["report_path"], result["manifest_path"]


def main() -> int:
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FEASIBILITY_CHECKED",
            "disposition": (
                "FEASIBILITY_CHECKED — source-feasibility preflight passed, but this implementation "
                "attempt did not complete a valid real-data backtest."
            ),
            "completed_backtest": False,
            "run_id": RUN_ID,
            "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": (
                "MET before this additional study by distinct 2026-11-26 real-data backtests; "
                "this incomplete attempt does not count."
            ),
            "error": f"{type(exc).__name__}: {exc}",
            "alternatives_attempted": [
                "Wikimedia official sequential pageviews API with descriptive User-Agent",
                "Binance exchangeInfo public market-status endpoint",
                "Binance Vision official checksummed monthly/daily Spot archive route",
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
