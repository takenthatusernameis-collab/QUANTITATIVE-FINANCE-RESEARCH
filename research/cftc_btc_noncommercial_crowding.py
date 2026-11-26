#!/usr/bin/env python3
"""Forecast screen: CFTC Bitcoin non-commercial net-long positioning -> BTC downside semivariance."""
from __future__ import annotations
import concurrent.futures, datetime as dt, hashlib, json, math, os, random, statistics, urllib.parse
from pathlib import Path
import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-26-CFTC-BTC-NONCOMM-CROWDING-DOWNSIDE-01"
CFTC_DATASET, CFTC_CODE = "6dca-aqww", "133741"
CFTC_START, CFTC_END = dt.date(2017, 12, 1), dt.date(2026, 11, 10)
BTC_START = dt.date(2017, 8, 17)
PUBLICATION_LAG_DAYS = 14
BACKLOG_START, BACKLOG_END = dt.date(2025, 9, 30), dt.date(2026, 1, 20)
MODEL_WINDOW, TARGET_SESSIONS = 104, 5
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2022, 1, 1)
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 4, 20261126
MIN_CFTC_ROWS, MIN_BTC_ROWS = 300, 3000
MAX_CFTC_AGE_DAYS, MAX_BTC_AGE_DAYS = 21, 2
ARCHIVE_WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID, ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA, NOW = os.environ.get("GITHUB_SHA", "local"), dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "cftc-btc-noncommercial-crowding" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-CFTC-BTC-NONCOMM-CROWDING-DOWNSIDE-01.md"
CFTC_API = f"https://publicreporting.cftc.gov/resource/{CFTC_DATASET}.json"
EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["cftc_noncomm_net_long_share"]


def build_cftc_url() -> str:
    params = {
        "$select": ",".join(["report_date_as_yyyy_mm_dd", "market_and_exchange_names", "cftc_contract_market_code",
                             "open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all"]),
        "$where": (f"cftc_contract_market_code='{CFTC_CODE}' "
                   f"AND report_date_as_yyyy_mm_dd >= '{CFTC_START.isoformat()}' "
                   f"AND report_date_as_yyyy_mm_dd <= '{CFTC_END.isoformat()}'"),
        "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "50000",
    }
    return CFTC_API + "?" + urllib.parse.urlencode(params)


def parse_cftc(body: bytes) -> list[dict]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("CFTC response is not a non-empty JSON row list")
    if len(payload) >= 50000:
        raise ValueError("CFTC response reached the 50,000-row limit; pagination is required")
    rows = []
    for raw in payload:
        if str(raw.get("cftc_contract_market_code") or "").strip() != CFTC_CODE:
            continue
        day = base.parse_date(raw.get("report_date_as_yyyy_mm_dd"))
        market = str(raw.get("market_and_exchange_names") or "").strip()
        oi = base.parse_float(raw.get("open_interest_all"))
        long_pos = base.parse_float(raw.get("noncomm_positions_long_all"))
        short_pos = base.parse_float(raw.get("noncomm_positions_short_all"))
        if day is None:
            raise ValueError("CFTC Bitcoin row has an invalid report date")
        if day.weekday() != 1:
            raise ValueError(f"Unexpected non-Tuesday report date in frozen weekly sample: {day}")
        if "BITCOIN" not in market.upper() or "CHICAGO MERCANTILE EXCHANGE" not in market.upper():
            raise ValueError(f"Unexpected CFTC market name for code {CFTC_CODE}: {market!r}")
        if oi is None or oi <= 0:
            raise ValueError(f"Invalid CFTC open interest for {day}")
        if long_pos is None or short_pos is None or long_pos < 0 or short_pos < 0:
            raise ValueError(f"Invalid CFTC non-commercial outright positions for {day}")
        net = long_pos - short_pos
        if abs(net) > oi:
            raise ValueError(f"CFTC non-commercial net position exceeds open interest for {day}")
        rows.append({"report_date": day, "market_name": market, "open_interest": oi,
                     "noncomm_long": long_pos, "noncomm_short": short_pos, "noncomm_net": net,
                     "cftc_noncomm_net_long_share": net / oi})
    if not rows:
        raise ValueError(f"No CFTC rows found for exact Bitcoin contract code {CFTC_CODE}")
    rows.sort(key=lambda row: row["report_date"])
    dates = [row["report_date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate CFTC Bitcoin report dates")
    return rows


def fetch_sources() -> tuple[list[dict], dict, dict]:
    cftc_url = build_cftc_url()
    cftc_body = base.fetch_bytes(cftc_url, timeout=30)
    cot = parse_cftc(cftc_body)
    info_url = EXCHANGE_INFO + "?" + urllib.parse.urlencode({"symbol": "BTCUSDT"})
    symbols = json.loads(base.fetch_bytes(info_url, timeout=15).decode("utf-8")).get("symbols", [])
    if len(symbols) != 1 or (symbols[0].get("symbol"), symbols[0].get("status"), symbols[0].get("baseAsset"), symbols[0].get("quoteAsset")) != ("BTCUSDT", "TRADING", "BTC", "USDT"):
        raise ValueError("Binance exchangeInfo did not confirm active BTCUSDT Spot market")
    end_date = NOW.date() - dt.timedelta(days=2)
    specs = btc.build_archive_specs(BTC_START, end_date, as_of_date=NOW.date())
    results, failures = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as pool:
        futures = {pool.submit(btc.download_binance_archive, spec): (i, spec) for i, spec in enumerate(specs)}
        for future in concurrent.futures.as_completed(futures):
            i, spec = futures[future]
            try:
                results[i] = future.result()
            except Exception as exc:
                failures.append({"period": spec["tag"], "url": spec["url"], "error": f"{type(exc).__name__}: {exc}"})
    if failures:
        raise RuntimeError(f"Binance Vision ingestion failed for {len(failures)}/{len(specs)} archives: {json.dumps(sorted(failures, key=lambda x: x['period']))}")
    prices, archives, units = {}, [], set()
    for i in range(len(specs)):
        page, item = results[i]
        archives.append(item)
        units.add(item["timestamp_unit"])
        for day, close in page.items():
            if BTC_START <= day <= end_date:
                if day in prices:
                    raise ValueError(f"Duplicate BTCUSDT date across archives: {day}")
                prices[day] = close
    prices = dict(sorted(prices.items()))
    expected, day = [], BTC_START
    while day <= end_date:
        expected.append(day)
        day += dt.timedelta(days=1)
    missing = [day for day in expected if day not in prices]
    if missing:
        raise ValueError(f"BTCUSDT has {len(missing)} missing UTC dates; first={missing[0]}, last={missing[-1]}")
    sources = {
        "CFTC": {"url": cftc_url, "dataset_id": CFTC_DATASET, "report_type": "Legacy Futures Only",
                 "contract_market_code": CFTC_CODE, "rows": len(cot),
                 "first_report_date": cot[0]["report_date"].isoformat(), "last_report_date": cot[-1]["report_date"].isoformat(),
                 "sha256": hashlib.sha256(cftc_body).hexdigest(), "retrieved_at_utc": NOW.isoformat(),
                 "raw_data_policy": "No raw CFTC observations are committed; only source hash, coverage and aggregate metrics are retained."},
        "BTCUSDT": {"symbol": "BTCUSDT", "market_status": symbols[0]["status"], "endpoint": "Binance Vision official Spot 1d archives",
                    "interval": "1d", "timezone": "UTC", "rows": len(prices),
                    "first_date": min(prices).isoformat(), "last_date": max(prices).isoformat(),
                    "archive_count": len(archives), "timestamp_units_observed": sorted(units),
                    "archive_manifest_sha256": hashlib.sha256(json.dumps(archives, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                    "archives": archives, "incomplete_current_candle_excluded": True},
    }
    return cot, prices, sources


def validate_coverage(cot: list[dict], prices: dict, today: dt.date) -> dict:
    cd, pd = [x["report_date"] for x in cot], sorted(prices)
    if len(cd) < MIN_CFTC_ROWS or len(pd) < MIN_BTC_ROWS:
        raise ValueError(f"Insufficient source depth: CFTC={len(cd)}, BTCUSDT={len(pd)}")
    if cd[0] > CFTC_START + dt.timedelta(days=90) or cd[-1] > CFTC_END:
        raise ValueError(f"CFTC history violates frozen coverage: {cd[0]} to {cd[-1]}")
    if (today - cd[-1]).days > MAX_CFTC_AGE_DAYS:
        raise ValueError(f"CFTC positions are stale: {cd[-1]}")
    if pd[0] > BTC_START + dt.timedelta(days=2) or pd[-1] > today or (today - pd[-1]).days > MAX_BTC_AGE_DAYS:
        raise ValueError(f"BTCUSDT history start/end is invalid or stale: {pd[0]} to {pd[-1]}")
    gaps = [(b-a).days for a,b in zip(cd, cd[1:])]
    if any(g <= 0 or g % 7 or g > 14 for g in gaps):
        raise ValueError("CFTC report dates have duplicate, irregular or greater-than-14-day gaps")
    if any((b-a).days != 1 for a,b in zip(pd, pd[1:])):
        raise ValueError("BTCUSDT daily candles contain a missing UTC date")
    return {"CFTC": {"rows": len(cd), "first_report_date": cd[0].isoformat(), "last_report_date": cd[-1].isoformat(),
                     "max_report_gap_days": max(gaps) if gaps else None},
            "BTCUSDT": {"rows": len(pd), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat()}}


def build_events(cot: list[dict], prices: dict[dt.date, float]) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    index_by_date = {day: i for i, day in enumerate(dates)}
    returns = [None] + [math.log(prices[dates[i]] / prices[dates[i-1]]) if (dates[i]-dates[i-1]).days == 1 else None for i in range(1, len(dates))]
    events = []
    skipped = {"known_publication_backlog": 0, "signal_after_latest_btc_date": 0, "missing_signal_close": 0,
               "insufficient_pre_history": 0, "incomplete_target": 0, "invalid_return_window": 0}
    for row in cot:
        report = row["report_date"]
        if BACKLOG_START <= report <= BACKLOG_END:
            skipped["known_publication_backlog"] += 1
            continue
        signal = report + dt.timedelta(days=PUBLICATION_LAG_DAYS)
        if signal > dates[-1]:
            skipped["signal_after_latest_btc_date"] += 1
            continue
        j = index_by_date.get(signal)
        if j is None:
            skipped["missing_signal_close"] += 1
            continue
        if j < 20:
            skipped["insufficient_pre_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        p5, p20, future = returns[j-4:j+1], returns[j-19:j+1], returns[j+1:j+TARGET_SESSIONS+1]
        if any(x is None or not math.isfinite(x) for x in p5+p20+future):
            skipped["invalid_return_window"] += 1
            continue
        p5, p20, future = [float(x) for x in p5], [float(x) for x in p20], [float(x) for x in future]
        target = btc.semi_var_pct2(future)
        events.append({
            "report_date": report, "record_date": signal, "signal_date": signal, "availability_date": signal,
            "target_start_date": dates[j+1], "target_end_date": dates[j+TARGET_SESSIONS],
            "target_semivariance_pct2": target, "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "cftc_noncomm_net_long_share": row["cftc_noncomm_net_long_share"],
        })
    for left, right in zip(events, events[1:]):
        gap = (right["signal_date"]-left["signal_date"]).days
        if gap <= 0 or gap % 7 or left["target_end_date"] >= right["signal_date"]:
            raise ValueError("CFTC events are not weekly or BTC target windows overlap/not matured")
    return events, {"candidate_reports": len(cot), "accepted_events": len(events), "skipped": skipped,
                    "publication_lag_calendar_days": PUBLICATION_LAG_DAYS,
                    "backlog_exclusion": [BACKLOG_START.isoformat(), BACKLOG_END.isoformat()],
                    "target_sessions": TARGET_SESSIONS, "nominal_report_spacing_days": 7}


def walk_forward(events: list[dict]) -> list[dict]:
    output = []
    for current in events:
        train = [r for r in events if r["signal_date"] < current["signal_date"] and r["target_end_date"] < current["signal_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            b = base.fit_ols_predict(train, current, BASE_FEATURES)
            a = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        output.append({"report_date": current["report_date"], "signal_date": current["signal_date"],
                       "target_end_date": current["target_end_date"], "target_bp": current["target_bp"],
                       "baseline_prediction_bp": b, "augmented_prediction_bp": a, "train_n": len(train)})
    return output


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "baseline_rmse_log1p_semivariance": None, "augmented_rmse_log1p_semivariance": None, "rmse_improvement_pct": None}
    be = [r["baseline_prediction_bp"]-r["target_bp"] for r in rows]
    ae = [r["augmented_prediction_bp"]-r["target_bp"] for r in rows]
    br, ar = math.sqrt(statistics.fmean(x*x for x in be)), math.sqrt(statistics.fmean(x*x for x in ae))
    return {"n": len(rows), "baseline_rmse_log1p_semivariance": br, "augmented_rmse_log1p_semivariance": ar,
            "baseline_mae_log1p_semivariance": statistics.fmean(abs(x) for x in be),
            "augmented_mae_log1p_semivariance": statistics.fmean(abs(x) for x in ae),
            "rmse_improvement_pct": 100.0*(br-ar)/br if br > 0 else None}


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    diffs = [{"loss_difference": (r["baseline_prediction_bp"]-r["target_bp"])**2-(r["augmented_prediction_bp"]-r["target_bp"])**2} for r in rows]
    if any(not math.isfinite(x["loss_difference"]) for x in diffs):
        return None
    observed, rng, samples = statistics.fmean(x["loss_difference"] for x in diffs), random.Random(BOOTSTRAP_SEED), []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(diffs, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(x["loss_difference"] for x in sample))
    samples.sort()
    return {"status": "COMPUTED", "observations": len(diffs), "reps": len(samples), "block_size_events": BOOTSTRAP_BLOCK,
            "mean_baseline_minus_augmented_squared_loss": observed,
            "ci_95_low": samples[int(.025*(len(samples)-1))], "ci_95_high": samples[int(.975*(len(samples)-1))],
            "bootstrap_fraction_positive": sum(x > 0 for x in samples)/len(samples)}


def decide(validation: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if validation["n"] < 30 or test["n"] < 30 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient validation/test forecasts or paired-loss inference"
    vi, ti = validation["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low"] > 0:
        return "BACKTESTED", "PROMISING SCREEN — both periods improve and paired-loss inference favors augmentation; independent validation and tradable evaluation remain required"
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high"] < 0:
        return "REJECTED", "REJECTED — both periods worsen and paired-loss inference favors the BTC-only baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority"


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status = result.get("status", "INCONCLUSIVE")
    disposition = str(result.get("disposition", "INCONCLUSIVE")).replace("|", "/")
    scope = str(result.get("data_scope", "source acceptance incomplete")).replace("|", "/")
    summary = result.get("summary_metrics") or {}
    row = (f"| {HYPOTHESIS_ID} | {status} | A strictly lagged CFTC Legacy Futures Only non-commercial net-long share of CME Bitcoin futures open interest adds information about next-five-session BTC downside semivariance beyond recent BTC downside semivariance and realized variance. | "
           f"{scope} | {disposition}; validation/test n={summary.get('validation_n')}/{summary.get('test_n')}, RMSE improvement={summary.get('validation_improvement_pct')}/{summary.get('test_improvement_pct')}%; forecast-only | [{report_path}](../{report_path}) |")
    lines = REGISTRY.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is None:
        header = next((i for i, line in enumerate(lines) if line.startswith("|---")), None)
        if header is None:
            raise ValueError("Hypothesis registry table header not found")
        lines.insert(header+1, row)
    else:
        lines[existing] = row
    REGISTRY.write_text("\n".join(lines)+"\n", encoding="utf-8")
    p = PREREG.read_text(encoding="utf-8")
    status_line = f"- **Status:** {status}. {disposition}. {'One bounded real-data forecast screen completed.' if result.get('completed_backtest') else 'No valid empirical backtest completed; source acceptance or execution failed.'}"
    p_lines = p.splitlines()
    for i, line in enumerate(p_lines):
        if line.startswith("- **Status:**"):
            p_lines[i] = status_line
            break
    p = "\n".join(p_lines).split("\n## Empirical disposition")[0].rstrip()
    p += ("\n\n## Empirical disposition\n\n"
          f"- **Final status:** {status} — {disposition}.\n"
          f"- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}.\n"
          f"- **Data scope:** {scope}.\n"
          f"- **Summary metrics:** {json.dumps(base.json_safe(summary), sort_keys=True)}.\n"
          f"- **Report:** [{report_path}](../{report_path}).\n"
          f"- **Manifest:** [{manifest_path}](../{manifest_path}).\n"
          "- Forecast-only; no trading P&L, causal claim, strategy promotion or live deployment.\n")
    PREREG.write_text(p+"\n", encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    lines = [f"# Research session — CFTC Bitcoin non-commercial positioning and downside semivariance ({NOW.isoformat()})", "",
             f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result.get('status', 'INCONCLUSIVE')}",
             f"- **Disposition:** {result.get('disposition', 'INCONCLUSIVE')}",
             "- **Timebox:** MEDIUM; 4 cycles; implementation deadline 2026-11-29T11:54:59Z; final conclusion deadline 2026-12-01T11:54:59Z.",
             f"- **Daily KPI:** {result.get('daily_kpi', 'not met by this study')}",
             f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}", f"- **Triggering commit:** {SOURCE_SHA}", ""]
    if error:
        lines += ["## Blocker", "", f"- {error}", "- No valid real-data backtest completed; this attempt does not count toward the daily minimum.", ""]
    else:
        v, t = result["validation_metrics"], result["test_metrics"]
        lines += [
            "## Preregistered method", "",
            "- CFTC source: Legacy Futures Only dataset 6dca-aqww, exact Bitcoin CME contract code 133741.",
            "- Predictor: (non-commercial long - non-commercial short) / total open interest; positive values indicate non-commercial net-long positioning. Spreading positions are excluded from the directional numerator; the signed feature has no ex-ante coefficient-sign constraint.",
            "- Signal: BTCUSDT UTC daily close exactly 14 calendar days after the CFTC report date. The ordinary Tuesday-to-Friday release timing and 2025-09-30 through 2026-01-20 backlog are handled by the frozen buffer and exclusion.",
            "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.",
            "- Target: log1p of next-five-session BTC downside semivariance. Targets do not overlap.",
            "- Rolling training window: 104 prior events; each training target must end strictly before the current signal.",
            "- Validation: 2019–2021. Test: 2022 onward. Paired inference: 2,000 circular-block bootstrap replications, four accepted events per block.", "",
            "## Data provenance", "", "| Source | First | Last | Rows | SHA-256 |", "|---|---|---:|---:|---|",
            f"| CFTC Legacy Futures Only, code {CFTC_CODE} | {result['coverage']['CFTC']['first_report_date']} | {result['coverage']['CFTC']['last_report_date']} | {result['coverage']['CFTC']['rows']} | {result['data_sources']['CFTC']['sha256']} |",
            f"| Binance BTCUSDT Spot 1d UTC | {result['coverage']['BTCUSDT']['first_date']} | {result['coverage']['BTCUSDT']['last_date']} | {result['coverage']['BTCUSDT']['rows']} | archive manifest {result['data_sources']['BTCUSDT']['archive_manifest_sha256']} |", "",
            "## Frozen results", "", "| Metric | Validation 2019–2021 | Test 2022 onward |", "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE (log1p semivariance) | {v['baseline_rmse_log1p_semivariance']} | {t['baseline_rmse_log1p_semivariance']} |",
            f"| Augmented RMSE (log1p semivariance) | {v['augmented_rmse_log1p_semivariance']} | {t['augmented_rmse_log1p_semivariance']} |",
            f"| RMSE improvement | {v['rmse_improvement_pct']}% | {t['rmse_improvement_pct']}% |",
            "", f"- Accepted events: {result['event_construction']['accepted_events']} of {result['event_construction']['candidate_reports']}; skipped: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- Paired test squared-loss bootstrap: {json.dumps(base.json_safe(result['paired_squared_loss_bootstrap']), sort_keys=True)}.",
            "", "## Literature boundary", "",
            "Shi (2022), Bitcoin futures risk premia, already studies position-based predictors of subsequent Bitcoin futures price changes. This is a narrower test of a CFTC Legacy non-commercial net-long ratio against next-five-session BTC Spot downside semivariance, not a first-discovery claim.",
            "Reference: https://doi.org/10.1002/fut.22373.", "",
            "## Verified / unverified", "",
            "**VERIFIED:** exact dataset and contract filter; source schema and coverage; 14-day availability buffer; documented backlog exclusion; Binance archive checksums and daily continuity; non-overlapping targets; walk-forward maturity and metrics under this code/data vintage.",
            "", "**UNVERIFIED:** exact historical release timestamps for every CFTC report, future semiweekly CFTC schema/cadence, cross-venue BTC replication, causal transmission, future-regime stability and instrument-level economic value.", "",
            "## Limitations", ""]
        lines += [f"- {x}" for x in result["limitations"]]
        lines += ["", "## Reproducibility", "", f"- Workflow: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{RUN_ID}",
                  "- Source: research/cftc_btc_noncommercial_crowding.py", "- Tests: research/test_cftc_btc_noncommercial_crowding.py"]
    return "\n".join(lines)+"\n"


def run_research() -> dict:
    cot, prices, sources = fetch_sources()
    coverage = validate_coverage(cot, prices, NOW.date())
    events, event_meta = build_events(cot, prices)
    predictions = walk_forward(events)
    val = summarize([r for r in predictions if VALIDATION_START <= r["signal_date"] < TEST_START])
    test = summarize([r for r in predictions if r["signal_date"] >= TEST_START])
    paired = paired_loss_bootstrap([r for r in predictions if r["signal_date"] >= TEST_START])
    status, disposition = decide(val, test, paired)
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition, "completed_backtest": True,
        "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "daily_kpi": "The 2026-11-26 minimum was already met by distinct real-data forecast screens; this is an additional materially distinct positioning-risk screen.",
        "coverage": coverage, "data_sources": sources, "event_construction": event_meta,
        "data_scope": f"CFTC Legacy Futures Only Bitcoin code {CFTC_CODE} {coverage['CFTC']['first_report_date']} to {coverage['CFTC']['last_report_date']} ({coverage['CFTC']['rows']} reports); Binance BTCUSDT Spot 1d UTC {coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} ({coverage['BTCUSDT']['rows']} candles); validation 2019-2021; test 2022 onward",
        "methodology": {"baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
                        "predictor": "(non-commercial long - non-commercial short) / open_interest_all",
                        "availability": "CFTC report date + 14 calendar days; historical release timestamps are not reconstructed", "coefficient_sign_constraint": "none; the signed feature mapping is estimated on training data only",
                        "target": "log1p next-five-UTC-session BTC downside semivariance",
                        "rolling_training_events": MODEL_WINDOW, "training_rule": "signal and target_end strictly before current signal",
                        "validation": "2019-01-01 through 2021-12-31", "test": "2022-01-01 onward",
                        "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block_events": BOOTSTRAP_BLOCK, "bootstrap_seed": BOOTSTRAP_SEED},
        "summary_metrics": {"validation_n": val["n"], "test_n": test["n"], "validation_improvement_pct": val["rmse_improvement_pct"], "test_improvement_pct": test["rmse_improvement_pct"]},
        "validation_metrics": val, "test_metrics": test, "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "CFTC non-commercial is a business-purpose classification, not a pure speculative-intent, leveraged-fund, leverage or liquidation-risk measure; the Commission does not publish trader identities or individual motives.",
            "CFTC reports normally contain Tuesday positions and are released Friday at 3:30 p.m. ET; historical release timestamps are not available for the full sample. The 14-day buffer is conservative, not exact point-in-time reconstruction.",
            "The 2025-09-30 through 2026-01-20 publication backlog is excluded because ordinary lag assumptions were invalid.",
            "The CFTC announced a plan on 2026-10-27 to move to semiweekly reporting by year-end. This run freezes Tuesday weekly observations through 2026-11-10; later reports require a new source/timing specification.",
            "CFTC category composition can change when traders enter, leave or update business-purpose classifications; the ratio is not an exogenous shock.",
            "BTCUSDT is one venue's Spot history; checksums establish file integrity, not consolidated-market representativeness.",
            "Forecast-only: no strategy P&L, costs, causal claim, profitability, live trading or capital deployment is established.",
            "No raw CFTC or Binance observations are committed; only source hashes, coverage, archive hashes and aggregate metrics are retained.",
        ],
    }


def main() -> int:
    try:
        result, error = run_research(), None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {"hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
                  "disposition": f"INCONCLUSIVE/INFEASIBLE — bounded source or execution failure: {error}",
                  "completed_backtest": False, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
                  "daily_kpi": f"No valid real-data backtest completed on UTC date {NOW.date()}; this attempt does not count toward the daily minimum.",
                  "data_scope": "source acceptance incomplete", "error": error}
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-cftc-btc-noncommercial-crowding-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    report_path.write_text(render_report(result, error), encoding="utf-8")
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True)+"\n", encoding="utf-8")
    rel_report, rel_manifest = str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))
    update_documents(result, rel_report, rel_manifest)
    print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "status": result["status"],
                      "completed_backtest": result.get("completed_backtest", False), "disposition": result["disposition"],
                      "daily_kpi": result["daily_kpi"], "report_path": rel_report, "manifest_path": rel_manifest,
                      "summary_metrics": result.get("summary_metrics"), "error": result.get("error")},
                     indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
