#!/usr/bin/env python3
"""Preregistered DeFiLlama stablecoin-supply -> BTC downside-semivariance forecast screen."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import re
import urllib.parse
from pathlib import Path

import stablecoin_supply_source_preflight as preflight
import stlfsi4_btc_downside_semivariance as btc
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-26-DEFILLAMA-STABLECOIN-SUPPLY-BTC-DOWNSIDE-01"
SAMPLE_START_DATE = dt.date(2021, 1, 1)
SAMPLE_END_DATE = dt.date(2026, 11, 24)
SUPPLY_LAG_DAYS, SUPPLY_LOOKBACK_DAYS = 2, 14
EVENT_STEP_DAYS, TARGET_SESSIONS, MODEL_WINDOW = 6, 5, 104
VALIDATION_START, TEST_START = dt.date(2022, 1, 1), dt.date(2024, 1, 1)
VALIDATION_END = dt.date(2023, 12, 31)
MIN_VALIDATION_N, MIN_TEST_N = 60, 100
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 4, 20261126
ARCHIVE_WORKERS = 6
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "stablecoin-supply-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-DEFILLAMA-STABLECOIN-SUPPLY-BTC-DOWNSIDE-01.md"
TIMEBOX = {
    "difficulty": "MEDIUM",
    "max_substantive_cycles": 4,
    "start_utc": "2026-11-26T15:46:57Z",
    "implementation_deadline_utc": "2026-11-29T15:46:57Z",
    "final_conclusion_deadline_utc": "2026-12-01T15:46:57Z",
}
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["stablecoin_supply_14d_log_change"]
STABLECOIN_URL = preflight.STABLECOIN_URL


def fetch_sources() -> tuple[dict[dt.date, float], dict[dt.date, float], dict]:
    stable_body = preflight.fetch_bytes(STABLECOIN_URL, timeout=40)
    stable = preflight.parse_stablecoin_history(stable_body)
    stable_coverage = preflight.validate_stablecoin_coverage(stable)

    info_url = btc.BINANCE_EXCHANGE_INFO + "?" + urllib.parse.urlencode({"symbol": "BTCUSDT"})
    info_body = base.fetch_bytes(info_url, timeout=20)
    market = preflight.validate_binance_exchange_info(info_body)

    specs = btc.build_archive_specs(SAMPLE_START_DATE, SAMPLE_END_DATE, as_of_date=NOW.date())
    results, failures = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as executor:
        futures = {executor.submit(btc.download_binance_archive, spec): (index, spec) for index, spec in enumerate(specs)}
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({"kind": spec["kind"], "period": spec["tag"], "url": spec["url"], "error": f"{type(exc).__name__}: {exc}"})
    if failures:
        failures.sort(key=lambda row: (row["kind"], row["period"]))
        raise RuntimeError(f"Binance Vision ingestion failed for {len(failures)}/{len(specs)} archives: {json.dumps(failures, sort_keys=True)}")

    prices, archive_manifest, timestamp_units = {}, [], set()
    for index in range(len(specs)):
        page, manifest_row = results[index]
        archive_manifest.append(manifest_row)
        timestamp_units.add(manifest_row["timestamp_unit"])
        for day, close in page.items():
            if SAMPLE_START_DATE <= day <= SAMPLE_END_DATE:
                if day in prices:
                    raise ValueError(f"Duplicate BTCUSDT date across archives: {day}")
                if not math.isfinite(close) or close <= 0:
                    raise ValueError(f"Invalid BTCUSDT close on {day}: {close}")
                prices[day] = close
    prices = dict(sorted(prices.items()))
    expected, day = [], SAMPLE_START_DATE
    while day <= SAMPLE_END_DATE:
        expected.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected if day not in prices]
    if missing:
        raise ValueError(f"Binance BTCUSDT history has {len(missing)} missing UTC dates; first={missing[0]}, last={missing[-1]}")
    archive_sha = hashlib.sha256(json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    sources = {
        "DEFILLAMA_USD_PEGGED_STABLECOIN_SUPPLY": {
            "endpoint": STABLECOIN_URL,
            "definition": "totalCirculatingUSD.peggedUSD; aggregate USD value of tracked USD-pegged stablecoins",
            "response_sha256": hashlib.sha256(stable_body).hexdigest(),
            "rows": len(stable),
            **stable_coverage,
            "vintage": "current API vintage; historical point-in-time revisions not reconstructed",
        },
        "BINANCE_BTCUSDT_SPOT": {
            "symbol": market["symbol"], "market_status": market["status"],
            "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
            "interval": "1d", "timezone": "UTC", "rows": len(prices),
            "first_date": min(prices).isoformat(), "last_date": max(prices).isoformat(),
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(row["kind"] == "monthly" for row in archive_manifest),
            "daily_archive_count": sum(row["kind"] == "daily" for row in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_sha,
            "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
        "BINANCE_EXCHANGE_INFO": {
            "endpoint": info_url, "response_sha256": hashlib.sha256(info_body).hexdigest(), **market,
        },
    }
    return stable, prices, sources


def build_events(stable: dict[dt.date, float], prices: dict[dt.date, float]) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    if not dates:
        raise ValueError("BTC price history is empty")
    if any((right - left).days != 1 for left, right in zip(dates, dates[1:])):
        raise ValueError("BTC price history contains a missing or duplicate UTC daily date")
    returns = {dates[i]: math.log(prices[dates[i]] / prices[dates[i - 1]]) for i in range(1, len(dates))}
    index_by_date = {day: index for index, day in enumerate(dates)}
    anchor = SAMPLE_START_DATE + dt.timedelta(days=20)
    events, skipped, candidates = [], {
        "missing_supply_feature_dates": 0,
        "missing_signal_close": 0,
        "insufficient_price_history": 0,
        "incomplete_target": 0,
        "invalid_return_window": 0,
    }, 0
    for day in dates:
        if day < anchor or (day - anchor).days % EVENT_STEP_DAYS:
            continue
        candidates += 1
        older_supply_date = day - dt.timedelta(days=SUPPLY_LOOKBACK_DAYS + SUPPLY_LAG_DAYS)
        newer_supply_date = day - dt.timedelta(days=SUPPLY_LAG_DAYS)
        if older_supply_date not in stable or newer_supply_date not in stable:
            skipped["missing_supply_feature_dates"] += 1
            continue
        j = index_by_date.get(day)
        if j is None:
            skipped["missing_signal_close"] += 1
            continue
        if j < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        prior5_dates = dates[j - 4:j + 1]
        prior20_dates = dates[j - 19:j + 1]
        future_dates = dates[j + 1:j + 1 + TARGET_SESSIONS]
        prior5 = [returns[value] for value in prior5_dates]
        prior20 = [returns[value] for value in prior20_dates]
        future = [returns[value] for value in future_dates]
        if any(not math.isfinite(value) for value in prior5 + prior20 + future):
            skipped["invalid_return_window"] += 1
            continue
        supply_change = math.log(stable[newer_supply_date] / stable[older_supply_date])
        target = btc.semi_var_pct2(future)
        events.append({
            "signal_date": day,
            "target_start_date": future_dates[0],
            "target_end_date": future_dates[-1],
            "stablecoin_supply_14d_log_change": supply_change,
            "target_semivariance_pct2": target,
            "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(prior20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(prior20)),
        })
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("Five-session target windows overlap or are not fully matured")
    return events, {
        "candidate_events": candidates,
        "accepted_events": len(events),
        "skipped": skipped,
        "signal_rule": "BTCUSDT UTC daily close d; stablecoin market-cap observations are taken exactly at d-2 and d-16",
        "feature_rule": "ln(totalCirculatingUSD.peggedUSD[d-2] / totalCirculatingUSD.peggedUSD[d-16]); no fill or interpolation",
        "target_rule": "next five BTCUSDT UTC daily close-to-close log returns; downside semivariance in percentage-points-squared",
        "event_step_calendar_days": EVENT_STEP_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "supply_lag_days": SUPPLY_LAG_DAYS,
        "supply_lookback_days": SUPPLY_LOOKBACK_DAYS,
    }


def walk_forward(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = [row for row in events if row["signal_date"] < current["signal_date"] and row["target_end_date"] < current["signal_date"]][-MODEL_WINDOW:]
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
            "stablecoin_supply_14d_log_change": current["stablecoin_supply_14d_log_change"],
            "train_n": len(train),
        })
    return predictions


def metrics(rows: list[dict]) -> dict:
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None
    if baseline and augmented and baseline["rmse_bp"] > 0:
        improvement = 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
    return {"n": len(rows), "baseline": baseline, "augmented": augmented, "rmse_improvement_pct": improvement}


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < MIN_VALIDATION_N or test["n"] < MIN_TEST_N or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient chronological forecast sample or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low_bp2"] > 0:
        return "BACKTESTED", "PROMISING FORECAST SCREEN — validation and test RMSE both improve and the paired test-loss 95% lower bound is positive; point-in-time data and independent validation remain necessary"
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high_bp2"] < 0:
        return "REJECTED", "REJECTED — validation and test RMSE both worsen and the paired test-loss 95% upper bound is negative"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"


def run_research() -> dict:
    sources = {}
    try:
        stable, prices, sources = fetch_sources()
        events, event_meta = build_events(stable, prices)
        predictions = walk_forward(events)
        validation_rows = [row for row in predictions if VALIDATION_START <= row["signal_date"] <= VALIDATION_END]
        test_rows = [row for row in predictions if TEST_START <= row["signal_date"] <= SAMPLE_END_DATE]
        validation, test = metrics(validation_rows), metrics(test_rows)
        base.BOOTSTRAP_BLOCK = BOOTSTRAP_BLOCK
        base.LOSS_BOOTSTRAP_SEED = BOOTSTRAP_SEED
        paired = base.bootstrap_paired_squared_loss_difference(test_rows, reps=BOOTSTRAP_REPS)
        status, disposition = decide(validation, test, paired)
        return {
            "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition,
            "completed_backtest": True, "source_failure": None,
            "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID, "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA, "timebox": TIMEBOX, "data_sources": sources,
            "event_construction": event_meta,
            "summary_metrics": {
                "accepted_events": len(events), "forecast_n": len(predictions),
                "validation_n": validation["n"], "test_n": test["n"],
                "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
                "test_rmse_improvement_pct": test["rmse_improvement_pct"],
            },
            "validation_metrics": validation, "test_metrics": test,
            "paired_squared_loss_bootstrap": paired,
            "methodology": {
                "baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
                "training_window_events": MODEL_WINDOW,
                "training_maturity_rule": "training target_end_date must be strictly earlier than the current signal date",
                "validation": f"{VALIDATION_START.isoformat()} through {VALIDATION_END.isoformat()}",
                "test": f"{TEST_START.isoformat()} through {SAMPLE_END_DATE.isoformat()}",
                "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block_events": BOOTSTRAP_BLOCK,
                "bootstrap_seed": BOOTSTRAP_SEED,
            },
            "limitations": [
                "DeFiLlama aggregate stablecoin history is a current-vintage series; historical point-in-time revisions and exact publication timestamps are not reconstructed.",
                "The two-day lag is an operational embargo, not proof of historical availability at each signal time.",
                "Aggregate stablecoin market capitalization is not exchange-resident liquidity, net inflow, collateral availability or investor positioning.",
                "USD-pegged stablecoins are aggregated across issuers and chains; design-specific effects are not identified.",
                "Binance BTCUSDT Spot is a single-venue reference series, not consolidated executable prices.",
                "This is a forecast-only screen, not causal evidence, strategy P&L or a live-trading signal.",
                "No raw DeFiLlama or Binance observations are committed; source response hashes and official archive checksums are retained.",
            ],
            "daily_kpi": "MET before this additional study by distinct 2026-11-26 real-data backtests; this study is incremental.",
        }
    except Exception as exc:
        return {
            "hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
            "disposition": f"INFEASIBLE — frozen source or implementation acceptance failed: {type(exc).__name__}: {exc}",
            "completed_backtest": False, "source_failure": f"{type(exc).__name__}: {exc}",
            "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID, "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA, "timebox": TIMEBOX, "data_sources": sources,
            "limitations": [
                "No empirical performance conclusion is drawn because the frozen source/implementation gates did not pass.",
                "The original timebox remains in force; no source, sample, cadence, target or decision gate is relaxed.",
                "No raw market observations are committed.",
            ],
            "daily_kpi": "MET before this additional study by distinct 2026-11-26 real-data backtests; this study is incremental.",
        }


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = str(result.get("disposition", "INCONCLUSIVE — no disposition established")).replace("|", "/")
    sources = result.get("data_sources", {})
    stable = sources.get("DEFILLAMA_USD_PEGGED_STABLECOIN_SUPPLY", {})
    binance = sources.get("BINANCE_BTCUSDT_SPOT", {})
    scope = (
        f"DeFiLlama USD-pegged stablecoin supply {stable.get('first_date', 'coverage unverified')} to {stable.get('last_date', 'coverage unverified')}; "
        f"Binance BTCUSDT Spot 1d UTC {binance.get('first_date', 'coverage unverified')} to {binance.get('last_date', 'coverage unverified')}"
    )
    summary = result.get("summary_metrics", {})
    metric_text = (
        f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, "
        f"RMSE improvement={summary.get('validation_rmse_improvement_pct')}/{summary.get('test_rmse_improvement_pct')}%"
        if result.get("completed_backtest") else str(result.get("source_failure"))
    )
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged 14-day change in aggregate USD-pegged stablecoin circulating market capitalization "
        f"adds information about next-five-session BTC downside semivariance beyond recent BTC downside risk and realized variance. | "
        f"{scope} | {disposition}; {metric_text} | [session report](../{report_path}) / [manifest](../{manifest_path}) |"
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
    prereg, count = re.subn(r"(?mi)^- \*\*(?:Initial )?status:\*\* .+$", f"- **Status:** {status}", prereg, count=1)
    if count != 1:
        raise ValueError("Could not update preregistration status idempotently")
    source_preflight_status = "PASS — source coverage was revalidated during the empirical run" if stable else "PASS on source-preflight run 45853947478; empirical retrieval failed or was incomplete"
    source_section = [
        "## Source-preflight disposition", "",
        f"- **Status:** {source_preflight_status}",
        f"- **DeFiLlama coverage:** {stable.get('first_date', 'unverified')} through {stable.get('last_date', 'unverified')}; {stable.get('rows', 0)} source rows; maximum gap {stable.get('maximum_gap_days', 'unverified')} days.",
        f"- **DeFiLlama response SHA-256:** {stable.get('response_sha256', 'unavailable')}.",
        f"- **Binance BTCUSDT:** {binance.get('first_date', 'unverified')} through {binance.get('last_date', 'unverified')}; {binance.get('archive_count', 0)} checksum-verified archives.",
        "- Read-only source feasibility preflight: [run 45853947478](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45853947478).", "",
    ]
    empirical_section = [
        "## Empirical disposition", "", f"- **Status:** {status}", f"- **Disposition:** {disposition}",
        f"- **Completed real-data backtest:** {result.get('completed_backtest')}",
        f"- **Data scope:** {scope}", f"- **Summary metrics:** {json.dumps(summary, sort_keys=True)}",
        f"- **Paired test-loss bootstrap:** {json.dumps(result.get('paired_squared_loss_bootstrap'), sort_keys=True)}",
        f"- **Source/implementation blocker:** {result.get('source_failure')}",
        f"- **Report:** [{report_path}](../{report_path})",
        f"- **Manifest:** [{manifest_path}](../{manifest_path})",
        "- Forecast-only; no causal, executable-trading or deployment claim.",
    ]
    prefix = prereg.split("## Source-preflight disposition", 1)[0].rstrip()
    prereg = prefix + "\n\n" + "\n".join(source_section) + "\n" + "\n".join(empirical_section) + "\n"
    PREREG_PATH.write_text(prereg, encoding="utf-8")


def render_report(result: dict, report_path: str, manifest_path: str) -> str:
    lines = [
        "# Research session — DeFiLlama stablecoin supply and BTC downside semivariance",
        "", f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Difficulty/timebox:** {TIMEBOX['difficulty']}; {TIMEBOX['max_substantive_cycles']} substantive cycles maximum.",
        f"- **Implementation deadline:** {TIMEBOX['implementation_deadline_utc']}.",
        f"- **Final research-conclusion deadline:** {TIMEBOX['final_conclusion_deadline_utc']}.",
        f"- **Registered/start:** {TIMEBOX['start_utc']}.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}.",
        f"- **Triggering commit:** {SOURCE_SHA}.",
        f"- **Completed real-data backtest:** {result.get('completed_backtest')}.",
        f"- **Daily KPI:** {result.get('daily_kpi')}.", "",
        "## Frozen method", "",
        "- Predictor: 14-calendar-day log change in DeFiLlama totalCirculatingUSD.peggedUSD, using exact observations d−2 and d−16.",
        "- Signal: close of Binance BTCUSDT Spot UTC daily candle d; two-day source embargo.",
        "- Baseline: prior-five-session downside semivariance, prior-twenty-session downside semivariance and prior-twenty-session realized variance.",
        "- Target: next-five-session BTC downside semivariance, in percentage-points-squared units and log1p transformed.",
        "- Event spacing: six calendar days; rolling training: 104 prior fully matured events.",
        "- Validation/test: 2022-01-01 through 2023-12-31 / 2024-01-01 through 2026-11-24.",
        "- No tuning, causal claim, trading P&L or strategy promotion.", "",
        "## Source and coverage evidence", "",
        json.dumps(result.get("data_sources", {}), indent=2, sort_keys=True), "",
    ]
    if result.get("source_failure"):
        lines.extend(["## Source/implementation blocker", "", result["source_failure"], ""])
    if result.get("completed_backtest"):
        v, t = result["validation_metrics"], result["test_metrics"]
        def fmt_metric(metrics_row, model_name):
            item = (metrics_row.get(model_name) or {}).get("rmse_bp")
            return f"{item:.8f}" if isinstance(item, (int, float)) and math.isfinite(item) else "N/A"
        def fmt_pct(value):
            return f"{value:.6f}%" if isinstance(value, (int, float)) and math.isfinite(value) else "N/A"
        lines.extend([
            "## Walk-forward results", "",
            "| Metric | Validation | Test |", "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE | {fmt_metric(v, 'baseline')} | {fmt_metric(t, 'baseline')} |",
            f"| Augmented RMSE | {fmt_metric(v, 'augmented')} | {fmt_metric(t, 'augmented')} |",
            f"| RMSE improvement | {fmt_pct(v['rmse_improvement_pct'])} | {fmt_pct(t['rmse_improvement_pct'])} |", "",
            "## Paired test-loss uncertainty", "",
            json.dumps(result.get("paired_squared_loss_bootstrap"), indent=2, sort_keys=True), "",
        ])
    else:
        lines.extend(["## Empirical result", "", "No valid empirical backtest was completed. No performance conclusion is inferred from the source/implementation blocker.", ""])
    lines.extend(["## Event construction", "", json.dumps(result.get("event_construction", {}), indent=2, sort_keys=True), "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in result.get("limitations", []))
    lines.extend(["", "## Durable evidence", "", f"- Report: {report_path}", f"- Manifest: {manifest_path}", "- Raw stablecoin and BTC observations are not committed."])
    return "\n".join(lines) + "\n"


def write_artifacts(result: dict) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = (SESSION_DIR / f"{STAMP}_session-stablecoin-supply-btc-downside-{RUN_ID}.md").relative_to(ROOT).as_posix()
    manifest_path = (OUTPUT_DIR / "manifest.json").relative_to(ROOT).as_posix()
    result["report_path"], result["manifest_path"] = report_path, manifest_path
    manifest = {**base.json_safe(result), "raw_market_observations_committed": False}
    (ROOT / manifest_path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / report_path).write_text(render_report(result, report_path, manifest_path), encoding="utf-8")
    update_documents(result, report_path, manifest_path)
    return report_path, manifest_path


def main() -> int:
    result = run_research()
    report_path, manifest_path = write_artifacts(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID, "status": result.get("status"),
        "completed_backtest": result.get("completed_backtest"),
        "report_path": report_path, "manifest_path": manifest_path,
        "summary_metrics": result.get("summary_metrics"),
        "source_failure": result.get("source_failure"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
