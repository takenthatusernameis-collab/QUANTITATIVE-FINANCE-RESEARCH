#!/usr/bin/env python3
"""Preregistered forecast screen: news-based US economic-policy uncertainty -> BTC downside semivariance."""
from __future__ import annotations
import concurrent.futures, csv, datetime as dt, hashlib, json, math, os, statistics, urllib.parse
from pathlib import Path
import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-26-EPU-BTC-DOWNSIDE-SEMIVARIANCE-01"
EPU_START_DATE = dt.date(2017, 8, 12)
BTC_START_DATE = dt.date(2017, 8, 17)
SAMPLE_END_DATE = dt.date(2026, 11, 24)
RELEASE_LAG_DAYS, EVENT_STEP_DAYS, TARGET_SESSIONS = 2, 6, 5
MODEL_WINDOW = 104
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2022, 1, 1)
BOOTSTRAP_REPS, BOOTSTRAP_SEED = 2000, 20261127
MIN_EPU_ROWS, MIN_BTC_ROWS, MAX_EPU_GAP_DAYS = 3000, 3000, 2
ROOT = Path(__file__).resolve().parents[1]
RUN_ID, ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA, NOW = os.environ.get("GITHUB_SHA", "local"), dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "epu-btc-downside-semivariance" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-EPU-BTC-DOWNSIDE-SEMIVARIANCE-01.md"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["epu_5d_log_change"]


def parse_epu(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or "USEPUINDXD" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED USEPUINDXD schema: {reader.fieldnames}")
    date_col = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_col is None:
        raise ValueError("FRED USEPUINDXD CSV has no recognized date column")
    values = {}
    for row in reader:
        raw = str(row.get("USEPUINDXD") or "").strip()
        if not raw or raw == ".":
            continue
        day, value = base.parse_date(row.get(date_col)), base.parse_float(raw)
        if day is None or value is None:
            raise ValueError(f"Invalid USEPUINDXD row: {row}")
        if value <= 0:
            raise ValueError(f"Non-positive USEPUINDXD value on {day}")
        if day in values:
            raise ValueError(f"Duplicate USEPUINDXD observation: {day}")
        values[day] = value
    if not values:
        raise ValueError("No valid USEPUINDXD observations")
    return dict(sorted(values.items()))


def fetch_sources():
    epu_url = f"{FRED_URL}?id=USEPUINDXD&cosd={EPU_START_DATE.isoformat()}&coed={SAMPLE_END_DATE.isoformat()}"
    epu_body = base.fetch_bytes(epu_url, timeout=25)
    epu = parse_epu(epu_body)
    info_url = btc.BINANCE_EXCHANGE_INFO + "?" + urllib.parse.urlencode({"symbol": "BTCUSDT"})
    info_body = base.fetch_bytes(info_url, timeout=15)
    symbols = json.loads(info_body.decode("utf-8")).get("symbols", [])
    if len(symbols) != 1:
        raise ValueError("Binance exchangeInfo did not return exactly BTCUSDT")
    info = symbols[0]
    if (info.get("symbol"), info.get("status"), info.get("baseAsset"), info.get("quoteAsset")) != ("BTCUSDT", "TRADING", "BTC", "USDT"):
        raise ValueError(f"BTCUSDT is not an active Spot USDT market: {info}")
    specs = btc.build_archive_specs(BTC_START_DATE, SAMPLE_END_DATE, as_of_date=NOW.date())
    results, failures = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=btc.ARCHIVE_WORKERS) as executor:
        futures = {executor.submit(btc.download_binance_archive, spec): (index, spec) for index, spec in enumerate(specs)}
        for future in concurrent.futures.as_completed(futures):
            index, spec = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                failures.append({"kind": spec["kind"], "period": spec["tag"], "url": spec["url"], "error": f"{type(exc).__name__}: {exc}"})
    if failures:
        failures.sort(key=lambda item: (item["kind"], item["period"]))
        raise RuntimeError(f"Binance Vision ingestion failed for {len(failures)}/{len(specs)} archives: {json.dumps(failures, sort_keys=True)}")
    prices, archive_manifest, timestamp_units = {}, [], set()
    for index in range(len(specs)):
        page, manifest_row = results[index]
        archive_manifest.append(manifest_row)
        timestamp_units.add(manifest_row["timestamp_unit"])
        for day, close in page.items():
            if BTC_START_DATE <= day <= SAMPLE_END_DATE:
                if day in prices:
                    raise ValueError(f"Duplicate BTCUSDT date across archives: {day}")
                prices[day] = close
    prices = dict(sorted(prices.items()))
    expected, day = [], BTC_START_DATE
    while day <= SAMPLE_END_DATE:
        expected.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected if day not in prices]
    if missing:
        raise ValueError(f"BTCUSDT archive history has {len(missing)} missing UTC dates; first={missing[0]}, last={missing[-1]}")
    archive_sha = hashlib.sha256(json.dumps(archive_manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    sources = {
        "USEPUINDXD": {
            "url": epu_url, "series_page": "https://fred.stlouisfed.org/series/USEPUINDXD",
            "sha256": hashlib.sha256(epu_body).hexdigest(), "rows": len(epu),
            "first_date": min(epu).isoformat(), "last_date": max(epu).isoformat(),
            "frequency": "daily, 7-day", "units": "index, not seasonally adjusted",
            "source": "Baker, Bloom and Davis; US newspaper-based economic policy uncertainty",
            "vintage": "current FRED vintage; historical ALFRED vintages not reconstructed",
        },
        "BTCUSDT": {
            "symbol": "BTCUSDT", "market_status": info["status"],
            "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
            "interval": "1d", "timezone": "UTC", "rows": len(prices),
            "first_date": min(prices).isoformat(), "last_date": max(prices).isoformat(),
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(x["kind"] == "monthly" for x in archive_manifest),
            "daily_archive_count": sum(x["kind"] == "daily" for x in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_sha, "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
    }
    return epu, prices, sources


def validate_coverage(epu, prices):
    ed, pd = sorted(epu), sorted(prices)
    if len(ed) < MIN_EPU_ROWS or len(pd) < MIN_BTC_ROWS:
        raise ValueError(f"Insufficient source depth: USEPUINDXD={len(ed)}, BTCUSDT={len(pd)}")
    if ed[0] > EPU_START_DATE + dt.timedelta(days=2):
        raise ValueError(f"USEPUINDXD starts too late: {ed[0]}")
    if ed[-1] > SAMPLE_END_DATE or (SAMPLE_END_DATE - ed[-1]).days > 2:
        raise ValueError(f"USEPUINDXD does not reach frozen sample cutoff: {ed[-1]}")
    if pd[0] != BTC_START_DATE or pd[-1] != SAMPLE_END_DATE:
        raise ValueError(f"BTCUSDT does not match frozen sample boundaries: {pd[0]} to {pd[-1]}")
    epu_gaps = [(b - a).days for a, b in zip(ed, ed[1:])]
    price_gaps = [(b - a).days for a, b in zip(pd, pd[1:])]
    if any(gap > MAX_EPU_GAP_DAYS for gap in epu_gaps):
        raise ValueError("USEPUINDXD has a gap greater than two days; no filling is allowed")
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("BTCUSDT daily candles contain a missing UTC date")
    return {
        "USEPUINDXD": {"rows": len(ed), "first_date": ed[0].isoformat(), "last_date": ed[-1].isoformat(), "max_gap_days": max(epu_gaps, default=0)},
        "BTCUSDT": {"rows": len(pd), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat()},
    }


def build_events(epu, prices):
    dates = sorted(prices)
    returns = [None]
    for i in range(1, len(dates)):
        returns.append(math.log(prices[dates[i]] / prices[dates[i - 1]]) if (dates[i] - dates[i - 1]).days == 1 else None)
    index_by_date = {day: i for i, day in enumerate(dates)}
    anchor = BTC_START_DATE + dt.timedelta(days=20 - RELEASE_LAG_DAYS)
    events = []
    skipped = {"missing_epu_feature_window": 0, "missing_signal_close": 0, "insufficient_price_history": 0, "incomplete_target": 0, "invalid_returns": 0}
    candidates = 0
    for epu_date in sorted(epu):
        if epu_date < anchor or (epu_date - anchor).days % EVENT_STEP_DAYS:
            continue
        candidates += 1
        prior_epu_date = epu_date - dt.timedelta(days=5)
        if prior_epu_date not in epu:
            skipped["missing_epu_feature_window"] += 1
            continue
        signal_date = epu_date + dt.timedelta(days=RELEASE_LAG_DAYS)
        j = index_by_date.get(signal_date)
        if j is None:
            skipped["missing_signal_close"] += 1
            continue
        if j < 20:
            skipped["insufficient_price_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        prior5, prior20 = returns[j - 4:j + 1], returns[j - 19:j + 1]
        future = returns[j + 1:j + 1 + TARGET_SESSIONS]
        if any(x is None or not math.isfinite(x) for x in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue
        p5, p20, fut = [float(x) for x in prior5], [float(x) for x in prior20], [float(x) for x in future]
        target = btc.semi_var_pct2(fut)
        events.append({
            "epu_date": epu_date, "signal_date": signal_date,
            "target_start_date": dates[j + 1], "target_end_date": dates[j + TARGET_SESSIONS],
            "epu_5d_log_change": math.log(epu[epu_date] / epu[prior_epu_date]),
            "target_semivariance_pct2": target, "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
        })
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("BTC target windows overlap or are not fully matured")
    return events, {
        "candidate_origins": candidates, "accepted_events": len(events), "skipped": skipped,
        "release_lag_days": RELEASE_LAG_DAYS, "event_step_calendar_days": EVENT_STEP_DAYS,
        "target_sessions": TARGET_SESSIONS,
        "signal_rule": "EPU observation date plus two calendar days; signal at that BTCUSDT UTC daily close",
        "feature_rule": "ln(EPU[d] / EPU[d-5]); exact daily observations only, no interpolation",
    }


def walk_forward(events):
    predictions = []
    for current in events:
        train = [r for r in events if r["signal_date"] < current["signal_date"] and r["target_end_date"] < current["signal_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "record_date": current["signal_date"],
            "epu_date": current["epu_date"], "signal_date": current["signal_date"],
            "target_end_date": current["target_end_date"], "target_bp": current["target_bp"],
            "target_semivariance_pct2": current["target_semivariance_pct2"],
            "baseline_prediction_bp": baseline, "augmented_prediction_bp": augmented,
            "train_n": len(train),
        })
    return predictions


def metrics(rows):
    baseline = base.forecast_metrics(rows, "baseline_prediction_bp")
    augmented = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None if not baseline or baseline["rmse_bp"] <= 0 else 100.0 * (baseline["rmse_bp"] - augmented["rmse_bp"]) / baseline["rmse_bp"]
    return {"n": len(rows), "baseline": baseline, "augmented": augmented, "rmse_improvement_pct": improvement}


def decide(validation, test, paired):
    if validation["n"] < 30 or test["n"] < 30 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient chronological forecast sample or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low_bp2"] > 0:
        return "BACKTESTED", "PROMISING SCREEN — validation and test RMSE both improve and the paired test-loss 95% lower bound is positive; independent validation and instrument-level evaluation remain necessary"
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high_bp2"] < 0:
        return "REJECTED", "REJECTED — validation and test RMSE both worsen and the paired test-loss 95% upper bound is negative"
    return "INCONCLUSIVE", "INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule"


def run_research():
    epu, prices, sources = fetch_sources()
    coverage = validate_coverage(epu, prices)
    events, event_meta = build_events(epu, prices)
    if len(events) < MODEL_WINDOW + 60:
        raise ValueError(f"Insufficient accepted non-overlapping events: {len(events)}")
    predictions = walk_forward(events)
    val_rows = [r for r in predictions if VALIDATION_START <= r["signal_date"] < TEST_START]
    test_rows = [r for r in predictions if r["signal_date"] >= TEST_START]
    validation, test = metrics(val_rows), metrics(test_rows)
    base.LOSS_BOOTSTRAP_SEED = BOOTSTRAP_SEED
    paired = base.bootstrap_paired_squared_loss_difference(test_rows, reps=BOOTSTRAP_REPS)
    status, disposition = decide(validation, test, paired)
    scope = (
        f"FRED USEPUINDXD daily 7-day {coverage['USEPUINDXD']['first_date']} to {coverage['USEPUINDXD']['last_date']} ({coverage['USEPUINDXD']['rows']} observations); "
        f"Binance BTCUSDT Spot 1d UTC {coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} ({coverage['BTCUSDT']['rows']} candles); "
        f"{len(events)} accepted six-day-spaced events; validation 2019-2021; test 2022 onward"
    )
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition,
        "completed_backtest": True, "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "MET before this additional study by distinct 2026-11-26 real-data backtests; this is an additional hypothesis screen.",
        "coverage": coverage, "data_sources": sources, "event_construction": event_meta, "data_scope": scope,
        "methodology": {
            "baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
            "predictor": "ln(USEPUINDXD[d] / USEPUINDXD[d-5]); positive means rising news-based US policy uncertainty",
            "availability": "EPU observation d is used at the BTCUSDT UTC daily close dated d+2; two-calendar-day buffer, historical intraday release timestamps not reconstructed",
            "target": "log1p(next-five-UTC-session BTCUSDT downside semivariance, percent-squared units)",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "all training signals and target_end dates strictly precede the current signal",
            "validation": "2019-01-01 through 2021-12-31", "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block_events": 4, "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "summary_metrics": {
            "validation_n": validation["n"], "test_n": test["n"],
            "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
            "test_rmse_improvement_pct": test["rmse_improvement_pct"],
        },
        "validation_metrics": validation, "test_metrics": test, "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "USEPUINDXD is a newspaper-based composite, not a direct policy shock, policy-rate surprise, investor-positioning measure or market-implied risk price; it can move with broad political and economic news.",
            "The current FRED vintage is used. Historical point-in-time ALFRED revisions and historical intraday publication timestamps are not reconstructed; the two-day lag does not remove all vintage/revision look-ahead risk.",
            "The daily 7-day EPU series is aligned to UTC BTC daily closes by calendar date. No missing observations are filled.",
            "BTCUSDT is one venue's Spot series, not a consolidated executable price or derivatives P&L series.",
            "Forecast-only: no causal claim, trading strategy, transaction-cost model, profitability, live deployment or capital allocation conclusion.",
            "No raw EPU or Binance observations are committed; source hashes, archive checksums and aggregate metrics are retained.",
        ],
    }


def update_documents(result, report_path, manifest_path):
    status = result.get("status", "INCONCLUSIVE")
    disposition = result.get("disposition", "INCONCLUSIVE — no disposition established")
    scope = result.get("data_scope", "source acceptance incomplete")
    summary = result.get("summary_metrics") or {}
    metrics_text = f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, RMSE improvement={summary.get('validation_rmse_improvement_pct')}/{summary.get('test_rmse_improvement_pct')} percent; forecast-only"
    report_link, manifest_link = "../" + report_path, "../" + manifest_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged five-calendar-day increase in the US news-based Economic Policy Uncertainty Index adds information about next-five-session BTC downside semivariance beyond recent BTC downside semivariance and realized variance. | "
        f"{scope} | {disposition}; {metrics_text} | [session report]({report_link}) / [manifest]({manifest_link}) |"
    )
    lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is None:
        separator = next((i for i, line in enumerate(lines) if line.startswith("|---")), None)
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        lines.insert(separator + 1, row)
    else:
        lines[existing] = row
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    prereg_lines = PREREG_PATH.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[i] = f"- **Status:** {status}"
            break
    prereg = "\n".join(prereg_lines).split("\n## Empirical disposition")[0].rstrip()
    prereg += (
        "\n\n## Empirical disposition\n\n"
        f"- **Final status:** {status}\n- **Disposition:** {disposition}\n"
        f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}\n"
        f"- **Data scope:** {scope}\n"
        f"- **Summary metrics:** {json.dumps(base.json_safe(summary), sort_keys=True)}\n"
        f"- **Paired test-loss bootstrap:** {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}\n"
        f"- **Report:** [{report_path}]({report_link})\n- **Manifest:** [{manifest_path}]({manifest_link})\n"
        "- Forecast screen only; no causal, trading or deployment claim.\n"
    )
    PREREG_PATH.write_text(prereg + "\n", encoding="utf-8")


def render_report(result):
    lines = [
        f"# Research session — news-based policy uncertainty and BTC downside semivariance ({STAMP})",
        "", f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}", f"- **Daily KPI:** {result.get('daily_kpi')}",
        "- **Implementation timebox:** LOW; two substantive cycles maximum; implementation deadline 2026-11-27T14:43:43Z; final conclusion deadline 2026-11-28T14:43:43Z.",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}", f"- **Triggering commit:** {SOURCE_SHA}", "",
    ]
    if result.get("error"):
        lines += ["## Execution blocker", "", f"- {result['error']}", "- No valid real-data backtest completed in this run; the earlier daily KPI remains independently met.", ""]
    else:
        v, t = result["validation_metrics"], result["test_metrics"]
        lines += [
            "## Preregistered method", "",
            "- Predictor: five-calendar-day log change in the US news-based Economic Policy Uncertainty Index.",
            "- Availability: EPU observation date plus two calendar days, at the close of the corresponding BTCUSDT UTC daily candle.",
            "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.",
            "- Target: next-five-session BTC downside semivariance, percentage-points-squared units, transformed with log1p.",
            "- Event spacing: six calendar days; target windows do not overlap.",
            "- Rolling training window: 104 prior fully matured events. Validation: 2019-2021. Test: 2022 onward.", "",
            "## Data provenance", "",
            "| Source | First | Last | Rows | SHA-256 / archive manifest |", "|---|---|---|---:|---|",
            f"| USEPUINDXD | {result['coverage']['USEPUINDXD']['first_date']} | {result['coverage']['USEPUINDXD']['last_date']} | {result['coverage']['USEPUINDXD']['rows']} | {result['data_sources']['USEPUINDXD']['sha256']} |",
            f"| BTCUSDT | {result['coverage']['BTCUSDT']['first_date']} | {result['coverage']['BTCUSDT']['last_date']} | {result['coverage']['BTCUSDT']['rows']} | {result['data_sources']['BTCUSDT']['archive_count']} archives; {result['data_sources']['BTCUSDT']['archive_manifest_sha256']} |", "",
            "## Walk-forward results", "", "| Metric | Validation 2019-2021 | Test 2022 onward |", "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE, log1p semivariance | {v['baseline']['rmse_bp']} | {t['baseline']['rmse_bp']} |",
            f"| Augmented RMSE, log1p semivariance | {v['augmented']['rmse_bp']} | {t['augmented']['rmse_bp']} |",
            f"| RMSE improvement | {v['rmse_improvement_pct']}% | {t['rmse_improvement_pct']}% |", "",
            "## Paired test-loss uncertainty", "",
            f"- {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}", "",
            "## Interpretation", "", result.get("disposition", "No disposition established."), "",
            "## Verified / unverified", "",
            "**VERIFIED:** retrieved source schemas, accepted coverage, archive checksums, frozen timing, non-overlapping targets, walk-forward maturity and metrics, if the backtest completed.",
            "**UNVERIFIED:** historical point-in-time FRED vintages, exact historical release timestamps, independent replication, causal interpretation and instrument-level economic value.", "",
            "## Limitations", "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    return "\n".join(lines) + "\n"


def write_outputs(result):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-epu-btc-downside-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    result["report_path"], result["manifest_path"] = str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))
    report_path.write_text(render_report(result), encoding="utf-8")
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_documents(result, result["report_path"], result["manifest_path"])
    return result["report_path"], result["manifest_path"]


def main():
    try:
        result = run_research()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — bounded source/execution failure: {type(exc).__name__}: {exc}",
            "completed_backtest": False, "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "MET before this run by distinct 2026-11-26 real-data backtests; this failed source/execution attempt does not count.",
            "error": f"{type(exc).__name__}: {exc}",
            "alternatives_attempted": [
                "FRED public USEPUINDXD series and CSV route",
                "Binance public exchangeInfo market-data endpoint",
                "Binance official checksummed Spot monthly/daily archive route",
            ],
        }
    report_path, manifest_path = write_outputs(result)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID, "status": result["status"],
        "completed_backtest": result.get("completed_backtest"),
        "report_path": report_path, "manifest_path": manifest_path,
        "summary_metrics": result.get("summary_metrics"), "error": result.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
