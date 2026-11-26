#!/usr/bin/env python3
"""Forecast screen: CME Bitcoin leveraged-fund gross-short crowding -> BTC downside semivariance."""
from __future__ import annotations
import bisect, datetime as dt, hashlib, json, math, os, random, statistics, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path
import treasury_auction_demand as base
import btc_real_yield_shock as price_model
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01"
CFTC_CODE, CFTC_DATASET = "133741", "gpe5-46if"
CFTC_START, PRICE_START = dt.date(2018, 4, 10), dt.date(2016, 11, 25)
ASOF_DATE, CFTC_END = dt.date(2026, 11, 26), dt.date(2026, 11, 17)
PUBLICATION_LAG_DAYS = 14
BACKLOG_START, BACKLOG_END = dt.date(2025, 9, 30), dt.date(2026, 1, 20)
CROWDING_LOOKBACK = MODEL_WINDOW = 52
TARGET_SESSIONS = 5
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2022, 1, 1)
HIGH_CROWDING_THRESHOLD = 0.90
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, RNG_SEED = 2000, 4, 20261126
MIN_CFTC_ROWS, MIN_PRICE_ROWS = 350, 3000

ROOT = Path(__file__).resolve().parents[1]
RUN_ID, RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
REPORT_PATH = SESSION_DIR / f"{STAMP}_session-cftc-bitcoin-carry-crowding-{RUN_ID}.md"
OUTPUT_DIR = ROOT / "reports" / "generated" / "cftc-bitcoin-carry-crowding" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md"
CFTC_BASE_URL = f"https://publicreporting.cftc.gov/resource/{CFTC_DATASET}.json"
FRED_URL, SERIES = "https://fred.stlouisfed.org/graph/fredgraph.csv", "CBBTCUSD"
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["gross_short_pct_oi_percentile"]


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": "QFR-Research/1.0 (public academic research; github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH)",
        "Accept": "application/json, text/csv, */*",
    })
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError(f"HTTP {response.status} or empty response for {url}")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after three bounded attempts: {url}: {last_error}")


def parse_cftc(body: bytes) -> list[dict]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("CFTC response is not a non-empty JSON row list")
    rows = []
    for raw in payload:
        if str(raw.get("cftc_contract_market_code") or "").strip() != CFTC_CODE:
            continue
        report_date = base.parse_date(raw.get("report_date_as_yyyy_mm_dd"))
        oi = base.parse_float(raw.get("open_interest_all"))
        short = base.parse_float(raw.get("lev_money_positions_short"))
        market = str(raw.get("contract_market_name") or "").strip()
        if report_date is None:
            raise ValueError("CFTC Bitcoin row has an invalid report date")
        if "BITCOIN" not in market.upper():
            raise ValueError(f"Unexpected market name for Bitcoin contract code {CFTC_CODE}: {market!r}")
        if oi is None or oi <= 0:
            raise ValueError(f"Invalid open interest for CFTC report {report_date}")
        if short is None or short < 0 or short > oi:
            raise ValueError(f"Invalid leveraged-fund gross short position for CFTC report {report_date}")
        rows.append({"report_date": report_date, "market_name": market, "cftc_contract_market_code": CFTC_CODE,
                     "open_interest": oi, "lev_money_short": short, "gross_short_pct_oi": short / oi})
    if not rows:
        raise ValueError(f"No CFTC TFF futures-only rows found for exact Bitcoin contract code {CFTC_CODE}")
    rows.sort(key=lambda row: row["report_date"])
    dates = [row["report_date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate CFTC Bitcoin report dates")
    report_gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    if report_gaps and min(report_gaps) < 6:
        raise ValueError("CFTC report-date interval below six days indicates a changed semiweekly cadence or duplicate weekly snapshots")
    return rows


def is_backlog_report(day: dt.date) -> bool:
    return BACKLOG_START <= day <= BACKLOG_END


def validate_coverage(rows: list[dict], prices: dict[dt.date, float], today: dt.date) -> dict:
    cd, pd = [r["report_date"] for r in rows], sorted(prices)
    if len(rows) < MIN_CFTC_ROWS or cd[0] > CFTC_START + dt.timedelta(days=90):
        raise ValueError(f"Insufficient or late-starting CFTC Bitcoin history: n={len(rows)}, first={cd[0]}")
    if cd[-1] > today or (today - cd[-1]).days > 21:
        raise ValueError(f"CFTC Bitcoin TFF history is future-dated or stale: {cd[-1]}")
    if len(prices) < MIN_PRICE_ROWS or pd[0] > dt.date(2017, 3, 1):
        raise ValueError(f"Insufficient or late-starting Coinbase BTCUSD history: n={len(prices)}, first={pd[0]}")
    if pd[-1] > today or (today - pd[-1]).days > 3:
        raise ValueError(f"Coinbase BTCUSD history is future-dated or stale: {pd[-1]}")
    gaps = [(b - a).days for a, b in zip(pd, pd[1:])]
    if gaps and max(gaps) > 4:
        raise ValueError(f"Coinbase BTCUSD contains a calendar gap greater than four days: {max(gaps)}")
    return {
        "CFTC_TFF_BTC": {"rows": len(rows), "first_date": cd[0].isoformat(), "last_date": cd[-1].isoformat()},
        "CBBTCUSD": {"rows": len(prices), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat(),
                     "maximum_calendar_gap_days": max(gaps) if gaps else 0},
    }


def build_crowding_features(rows: list[dict]) -> list[dict]:
    """Rank gross leveraged-fund short/OI against prior 52 non-backlog reports only."""
    result, prior_values, prior_dates = [], [], []
    for row in sorted(rows, key=lambda x: x["report_date"]):
        if is_backlog_report(row["report_date"]):
            result.append({**row, "gross_short_pct_oi_percentile": None, "high_crowding": False,
                           "excluded_publication_backlog": True, "percentile_history_n": 0,
                           "percentile_history_start": None})
            continue
        if len(prior_values) >= CROWDING_LOOKBACK:
            history, current = prior_values[-CROWDING_LOOKBACK:], row["gross_short_pct_oi"]
            less, equal = sum(v < current for v in history), sum(v == current for v in history)
            percentile = (less + 0.5 * equal) / len(history)
            result.append({**row, "gross_short_pct_oi_percentile": percentile,
                           "high_crowding": percentile >= HIGH_CROWDING_THRESHOLD,
                           "excluded_publication_backlog": False, "percentile_history_n": len(history),
                           "percentile_history_start": prior_dates[-CROWDING_LOOKBACK].isoformat()})
        else:
            result.append({**row, "gross_short_pct_oi_percentile": None, "high_crowding": False,
                           "excluded_publication_backlog": False, "percentile_history_n": len(prior_values),
                           "percentile_history_start": prior_dates[0].isoformat() if prior_dates else None})
        prior_values.append(row["gross_short_pct_oi"])
        prior_dates.append(row["report_date"])
    return result


def build_events(cot_features: list[dict], prices: dict[dt.date, float], today: dt.date) -> tuple[list[dict], dict]:
    price_dates, returns = price_model.daily_log_returns(prices)
    events = []
    skipped = {k: 0 for k in (
        "known_publication_backlog", "insufficient_prior_position_history", "availability_date_not_reached",
        "no_signal_close", "signal_close_too_far_after_lag", "insufficient_btc_pre_history",
        "incomplete_btc_return_window", "overlapping_target_window")}
    for row in sorted(cot_features, key=lambda x: x["report_date"]):
        report_date = row["report_date"]
        if row.get("excluded_publication_backlog") or is_backlog_report(report_date):
            skipped["known_publication_backlog"] += 1
            continue
        percentile = row.get("gross_short_pct_oi_percentile")
        if percentile is None:
            skipped["insufficient_prior_position_history"] += 1
            continue
        available = report_date + dt.timedelta(days=PUBLICATION_LAG_DAYS)
        if available > today:
            skipped["availability_date_not_reached"] += 1
            continue
        j = bisect.bisect_left(price_dates, available)
        if j >= len(price_dates):
            skipped["no_signal_close"] += 1
            continue
        signal = price_dates[j]
        if (signal - available).days > 1:
            skipped["signal_close_too_far_after_lag"] += 1
            continue
        if j < 20 or j + TARGET_SESSIONS >= len(price_dates):
            skipped["insufficient_btc_pre_history"] += 1
            continue
        pre5, pre20 = returns[j - 4:j + 1], returns[j - 19:j + 1]
        future = returns[j + 1:j + TARGET_SESSIONS + 1]
        if any(x is None or not math.isfinite(float(x)) for x in pre5 + pre20 + future):
            skipped["incomplete_btc_return_window"] += 1
            continue
        p5, p20, fut = [float(x) for x in pre5], [float(x) for x in pre20], [float(x) for x in future]
        target = btc.semi_var_pct2(fut)
        event = {
            "report_date": report_date, "availability_date": available, "signal_date": signal,
            "target_start_date": price_dates[j + 1], "target_end_date": price_dates[j + TARGET_SESSIONS],
            "gross_short_pct_oi_percentile": float(percentile), "high_crowding": bool(row.get("high_crowding")),
            "target_semivariance_pct2": target, "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(p20)),
            "percentile_history_n": row.get("percentile_history_n"),
            "percentile_history_start": row.get("percentile_history_start"),
        }
        if event["target_end_date"] <= signal:
            raise ValueError(f"Invalid target dates for CFTC signal {report_date}")
        if events and event["target_start_date"] <= events[-1]["target_end_date"]:
            skipped["overlapping_target_window"] += 1
            continue
        events.append(event)
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("A prior BTC downside-semivariance target was not mature before the next signal")
    return events, {
        "candidate_cftc_rows": len(cot_features), "events": len(events), "skipped": skipped,
        "publication_lag_days": PUBLICATION_LAG_DAYS, "crowding_lookback_prior_reports": CROWDING_LOOKBACK,
        "high_crowding_percentile": HIGH_CROWDING_THRESHOLD, "target_sessions": TARGET_SESSIONS,
        "weekly_report_design": "Tuesday report dates; first Coinbase BTCUSD close on or after report_date + 14 calendar days",
    }


def walk_forward_predictions(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = [r for r in events if r["signal_date"] < current["signal_date"]
                 and r["target_end_date"] < current["signal_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = base.fit_ols_predict(train, current, BASE_FEATURES)
            augmented = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "report_date": current["report_date"], "signal_date": current["signal_date"],
            "target_start_date": current["target_start_date"], "target_end_date": current["target_end_date"],
            "target_bp": current["target_bp"], "target_semivariance_pct2": current["target_semivariance_pct2"],
            "gross_short_pct_oi_percentile": current["gross_short_pct_oi_percentile"],
            "high_crowding": current["high_crowding"], "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented, "train_n": len(train),
        })
    return predictions


def forecast_metrics(rows: list[dict], prediction_key: str) -> dict:
    if not rows:
        return {"n": 0, "rmse_log1p_semivariance": None, "mae_log1p_semivariance": None}
    errors = [r[prediction_key] - r["target_bp"] for r in rows]
    return {"n": len(rows), "rmse_log1p_semivariance": math.sqrt(statistics.fmean(e * e for e in errors)),
            "mae_log1p_semivariance": statistics.fmean(abs(e) for e in errors)}


def improvement_pct(baseline: dict, augmented: dict) -> float | None:
    b, a = baseline.get("rmse_log1p_semivariance"), augmented.get("rmse_log1p_semivariance")
    if not isinstance(b, (int, float)) or not isinstance(a, (int, float)) or b <= 0:
        return None
    return 100.0 * (b - a) / b


def paired_loss_bootstrap(rows: list[dict]) -> dict | None:
    if len(rows) < 30:
        return None
    differences = []
    for r in rows:
        d = (r["baseline_prediction_bp"] - r["target_bp"]) ** 2 - (r["augmented_prediction_bp"] - r["target_bp"]) ** 2
        if not math.isfinite(d):
            return None
        differences.append({"difference": d})
    observed, rng, samples = statistics.fmean(x["difference"] for x in differences), random.Random(RNG_SEED), []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(differences, rng, BOOTSTRAP_BLOCK)
        samples.append(statistics.fmean(x["difference"] for x in sample))
    samples.sort()
    return {"observations": len(differences), "reps": len(samples), "block_size_events": BOOTSTRAP_BLOCK,
            "mean_baseline_minus_augmented_squared_loss": observed,
            "ci95_low": samples[int(0.025 * (len(samples) - 1))],
            "ci95_high": samples[int(0.975 * (len(samples) - 1))],
            "bootstrap_fraction_positive": sum(x > 0 for x in samples) / len(samples)}


def crowding_event_study(rows: list[dict]) -> dict | None:
    high = [r["target_semivariance_pct2"] for r in rows if r["high_crowding"]]
    other = [r["target_semivariance_pct2"] for r in rows if not r["high_crowding"]]
    if len(rows) < 30 or len(high) < 5 or len(other) < 5:
        return None
    observed, rng, samples = statistics.fmean(high) - statistics.fmean(other), random.Random(RNG_SEED + 1), []
    for _ in range(BOOTSTRAP_REPS):
        sample = base.circular_block_sample(rows, rng, BOOTSTRAP_BLOCK)
        h = [r["target_semivariance_pct2"] for r in sample if r["high_crowding"]]
        o = [r["target_semivariance_pct2"] for r in sample if not r["high_crowding"]]
        if h and o:
            samples.append(statistics.fmean(h) - statistics.fmean(o))
    if len(samples) < BOOTSTRAP_REPS // 2:
        return None
    samples.sort()
    return {"high_n": len(high), "other_n": len(other), "mean_high_semivariance_pct2": statistics.fmean(high),
            "mean_other_semivariance_pct2": statistics.fmean(other),
            "high_minus_other_mean_semivariance_pct2": observed, "reps": len(samples),
            "block_size_events": BOOTSTRAP_BLOCK, "ci95_low": samples[int(0.025 * (len(samples) - 1))],
            "ci95_high": samples[int(0.975 * (len(samples) - 1))]}


def decide(validation: dict, test: dict, paired: dict | None, event: dict | None) -> tuple[str, str]:
    vi = improvement_pct(validation.get("baseline", {}), validation.get("augmented", {}))
    ti = improvement_pct(test.get("baseline", {}), test.get("augmented", {}))
    enough = validation.get("n", 0) >= 30 and test.get("n", 0) >= 30 and paired is not None and event is not None
    if (enough and vi is not None and ti is not None and vi > 0 and ti > 0
            and paired.get("ci95_low") is not None and paired["ci95_low"] > 0
            and event.get("high_minus_other_mean_semivariance_pct2", 0) > 0
            and event.get("ci95_low") is not None and event["ci95_low"] > 0):
        return "BACKTESTED", "PROMISING SCREEN — both chronological RMSE periods improve, paired test-loss inference favors augmentation, and high-crowding events have higher subsequent downside semivariance; independent validation is still required"
    if (vi is not None and ti is not None and vi <= 0 and ti <= 0 and paired is not None
            and paired.get("ci95_high") is not None and paired["ci95_high"] < 0 and event is not None
            and event.get("high_minus_other_mean_semivariance_pct2", 0) <= 0
            and event.get("ci95_high") is not None and event["ci95_high"] < 0):
        return "REJECTED", "REJECTED — neither chronological period improves, paired-loss inference favors the baseline, and high-crowding events do not show higher subsequent downside semivariance"
    return "INCONCLUSIVE", "INCONCLUSIVE — the frozen validation/test and paired-event criteria do not establish incremental predictive value or decisive inferiority"


def update_registry(result: dict, report_relative: str) -> None:
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    summary, test = result.get("summary_metrics") or {}, result.get("test_metrics") or {}
    event = test.get("crowding_event_study") or {}
    scope = str(result.get("data_scope", "not established")).replace("|", "/")
    disposition = str(result.get("disposition", "not established")).replace("|", "/")
    evidence = f"[session report](../{report_relative}) / [preregistration](PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md)"
    row = (
        f"| {HYPOTHESIS_ID} | {result.get('status', 'INCONCLUSIVE')} | "
        "Prior-only percentile of CME Bitcoin futures leveraged-fund gross shorts as a share of open interest proxies short-side/cash-and-carry crowding and may add information about next-five-session BTC downside semivariance beyond BTC's own recent downside semivariance and realized variance. | "
        f"{scope} | {disposition}; validation/test n={summary.get('validation_n')}/{summary.get('test_n')}; RMSE improvement={summary.get('validation_improvement_pct')}/{summary.get('test_improvement_pct')}%; high-crowding semivariance difference={event.get('high_minus_other_mean_semivariance_pct2')} pct² | {evidence} |"
    )
    lines, prefix = content.splitlines(), f"| {HYPOTHESIS_ID} |"
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) > 1:
        raise ValueError(f"Duplicate registry rows for {HYPOTHESIS_ID}")
    if matches:
        lines[matches[0]] = row
    else:
        marker = "## Disposition rules"
        if marker not in lines:
            raise ValueError("Hypothesis registry disposition marker missing")
        lines.insert(lines.index(marker), row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_preregistration(result: dict, report_relative: str, manifest_relative: str) -> None:
    content = PREREG_PATH.read_text(encoding="utf-8")
    marker = "\n## Empirical disposition"
    if marker in content:
        content = content.split(marker, 1)[0].rstrip()
    summary = result.get("summary_metrics") or {}
    validation, test = result.get("validation_metrics") or {}, result.get("test_metrics") or {}
    lines = [
        "", "## Empirical disposition", "",
        f"- **Status:** {result.get('status', 'INCONCLUSIVE')}",
        f"- **Disposition:** {result.get('disposition', 'not established')}",
        f"- **Completed real-data backtest:** {result.get('completed_backtest', False)}",
        f"- **Data scope:** {result.get('data_scope', 'not established')}",
        f"- **Validation/test forecasts:** {summary.get('validation_n')}/{summary.get('test_n')}",
        f"- **RMSE improvement:** {summary.get('validation_improvement_pct')}% validation; {summary.get('test_improvement_pct')}% test",
        f"- **Validation metrics:** {json.dumps(base.json_safe(validation), sort_keys=True)}",
        f"- **Test metrics:** {json.dumps(base.json_safe(test), sort_keys=True)}",
        f"- **Report:** [{report_relative}](../{report_relative})",
        f"- **Manifest:** [{manifest_relative}](../{manifest_relative})",
    ]
    if result.get("error"):
        lines.extend(["", f"- **Execution blocker:** {result['error']}"])
    PREREG_PATH.write_text(content + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    summary, validation, test = result.get("summary_metrics") or {}, result.get("validation_metrics") or {}, result.get("test_metrics") or {}
    cftc, price, meta = result.get("cftc_source") or {}, result.get("price_source") or {}, result.get("event_construction") or {}
    lines = [
        f"# Session report — CFTC Bitcoin futures short crowding and BTC downside semivariance ({STAMP})", "",
        f"- Hypothesis: {HYPOTHESIS_ID}", f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'not established')}",
        f"- Completed real-data backtest: {result.get('completed_backtest', False)}",
        f"- Daily research KPI: {result.get('daily_kpi', 'not established')}",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}", f"- Triggering commit: {SOURCE_SHA}",
        f"- Data scope: {result.get('data_scope', 'not established')}", "",
        "## Preregistered method", "",
        f"- CFTC market: Bitcoin, CME, contract code {CFTC_CODE}, TFF futures-only dataset {CFTC_DATASET}; report-date cutoff {CFTC_END}.",
        f"- Availability: first Coinbase BTCUSD close on or after the CFTC report date plus {PUBLICATION_LAG_DAYS} calendar days; sample as-of date {ASOF_DATE}.",
        f"- Feature: gross leveraged-fund short positions / total open interest, ranked against the prior {CROWDING_LOOKBACK} non-backlog reports only; high crowding is a prior-only percentile at or above {HIGH_CROWDING_THRESHOLD:.0%}.",
        "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.",
        "- Target: log1p of next-five-observation BTC downside semivariance.",
        f"- Rolling training window: {MODEL_WINDOW} prior events with target_end_date strictly earlier than the current signal.",
        "- Validation: 2019–2021. Test: 2022 onward. Paired loss and event-study uncertainty use 2,000 four-event circular-block bootstrap replications.", "",
        "## Data provenance", "",
        f"- CFTC rows: {cftc.get('rows')}; coverage: {cftc.get('first_date')} to {cftc.get('last_date')}; SHA-256: {cftc.get('sha256')}",
        f"- Coinbase CBBTCUSD rows: {price.get('rows')}; coverage: {price.get('first_date')} to {price.get('last_date')}; SHA-256: {price.get('sha256')}",
        f"- Accepted events: {meta.get('events')}; skipped: {meta.get('skipped')}", "",
        "## Walk-forward results", "",
        "| Metric | Validation 2019–2021 | Test 2022 onward |", "|---|---:|---:|",
        f"| Forecasts | {summary.get('validation_n')} | {summary.get('test_n')} |",
        f"| Baseline RMSE, log1p semivariance | {(validation.get('baseline') or {}).get('rmse_log1p_semivariance')} | {(test.get('baseline') or {}).get('rmse_log1p_semivariance')} |",
        f"| Augmented RMSE, log1p semivariance | {(validation.get('augmented') or {}).get('rmse_log1p_semivariance')} | {(test.get('augmented') or {}).get('rmse_log1p_semivariance')} |",
        f"| RMSE improvement | {summary.get('validation_improvement_pct')}% | {summary.get('test_improvement_pct')}% |", "",
        "## Test-period uncertainty and event study", "",
        f"- Paired squared-loss bootstrap: {test.get('paired_loss_bootstrap')}",
        f"- High-crowding event study: {test.get('crowding_event_study')}", "",
        "## Scientific interpretation", "", result.get("disposition", "No disposition established."), "",
        "The leveraged-fund category is not a direct measure of bearish intent. CME Bitcoin futures shorts may include cash-and-carry basis positions as well as directional and other strategies. This study tests a predictive association, not trader intent, causality or a tradable strategy.", "",
        "## Limitations", "",
        "- CFTC classifications are based on predominant business purpose and do not reveal the intent of each position.",
        "- CFTC data cover CME Bitcoin futures only, not offshore perpetual swaps or the global derivatives market.",
        "- A fixed 14-day lag is conservative for the historical weekly Tuesday/Friday schedule; the 2025 shutdown catch-up reports are excluded. CFTC announced a move toward twice-weekly publication by the end of 2026, so a future schedule change requires a new timing specification.",
        "- Current CFTC data can reflect revised historical classifications and positions; exact historical publication timestamps are not available for the full history.",
        "- CBBTCUSD is Coinbase's daily 5 p.m. Pacific price series distributed by FRED; raw observations are not committed or redistributed.",
        "- Current FRED vintage is used; historical ALFRED vintages are not reconstructed.",
        "- Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.", "",
        "## Reproducibility", "",
        f"- Manifest: reports/generated/cftc-bitcoin-carry-crowding/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        "- Source: research/cftc_btc_carry_crowding.py",
        "- Tests: research/test_cftc_btc_carry_crowding.py",
        "- Preregistration: research/PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md",
    ]
    if error:
        lines.extend(["", "## Execution error", "", error])
    return "\n".join(lines) + "\n"


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    report_rel, manifest_rel = REPORT_PATH.relative_to(ROOT).as_posix(), manifest_path.relative_to(ROOT).as_posix()
    update_registry(result, report_rel)
    update_preregistration(result, report_rel, manifest_rel)
    return report_rel, manifest_rel


def run_research() -> dict:
    today = ASOF_DATE
    params = {
        "$select": ",".join(["report_date_as_yyyy_mm_dd", "contract_market_name", "cftc_contract_market_code",
                             "open_interest_all", "lev_money_positions_short"]),
        "$where": (f"cftc_contract_market_code='{CFTC_CODE}' "
                   f"AND report_date_as_yyyy_mm_dd >= '{CFTC_START.isoformat()}' "
                   f"AND report_date_as_yyyy_mm_dd <= '{CFTC_END.isoformat()}'"),
        "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "50000",
    }
    cftc_url = CFTC_BASE_URL + "?" + urllib.parse.urlencode(params)
    price_url = FRED_URL + "?" + urllib.parse.urlencode({"id": SERIES, "cosd": PRICE_START.isoformat(), "coed": ASOF_DATE.isoformat()})
    cftc_body, price_body = fetch_bytes(cftc_url), fetch_bytes(price_url)
    cot_rows = parse_cftc(cftc_body)
    prices = price_model.parse_fred_series(price_body, SERIES)
    coverage = validate_coverage(cot_rows, prices, today)
    features = build_crowding_features(cot_rows)
    events, event_meta = build_events(features, prices, today)
    predictions = walk_forward_predictions(events)
    val_rows = [r for r in predictions if VALIDATION_START <= r["signal_date"] < TEST_START]
    test_rows = [r for r in predictions if r["signal_date"] >= TEST_START]
    validation = {"n": len(val_rows), "baseline": forecast_metrics(val_rows, "baseline_prediction_bp"),
                  "augmented": forecast_metrics(val_rows, "augmented_prediction_bp")}
    test = {"n": len(test_rows), "baseline": forecast_metrics(test_rows, "baseline_prediction_bp"),
            "augmented": forecast_metrics(test_rows, "augmented_prediction_bp"),
            "paired_loss_bootstrap": paired_loss_bootstrap(test_rows),
            "crowding_event_study": crowding_event_study(test_rows)}
    val_imp, test_imp = improvement_pct(validation["baseline"], validation["augmented"]), improvement_pct(test["baseline"], test["augmented"])
    status, disposition = decide(validation, test, test["paired_loss_bootstrap"], test["crowding_event_study"])
    cd, pd = [r["report_date"] for r in cot_rows], sorted(prices)
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition, "completed_backtest": True,
        "daily_kpi": "MET before this additional study by distinct real-data hypothesis backtests on 2026-11-26; this run is additional research, not a quota claim",
        "run_id": RUN_ID, "run_attempt": RUN_ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "data_scope": (f"CFTC TFF futures-only Bitcoin CME contract {CFTC_CODE}, {cd[0]} to {cd[-1]} "
                       f"({len(cot_rows)} rows; known 2025-09-30 to 2026-01-20 catch-up period excluded from events/history); "
                       f"FRED/Coinbase CBBTCUSD {pd[0]} to {pd[-1]} ({len(prices)} daily observations); {len(events)} accepted weekly events"),
        "coverage": coverage,
        "cftc_source": {"url": cftc_url, "dataset": CFTC_DATASET, "contract_code": CFTC_CODE,
                        "rows": len(cot_rows), "first_date": cd[0].isoformat(), "last_date": cd[-1].isoformat(),
                        "fields": ["report_date_as_yyyy_mm_dd", "contract_market_name", "cftc_contract_market_code",
                                   "open_interest_all", "lev_money_positions_short"], "sha256": sha256(cftc_body)},
        "price_source": {"url": price_url, "series": SERIES,
                         "source": "Coinbase daily BTCUSD close distributed by FRED, 5 p.m. Pacific Time",
                         "rows": len(prices), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat(),
                         "sha256": sha256(price_body)},
        "event_construction": event_meta,
        "methodology": {"publication_lag_days": PUBLICATION_LAG_DAYS,
                        "known_publication_backlog_exclusion": [BACKLOG_START.isoformat(), BACKLOG_END.isoformat()],
                        "crowding_feature": "gross leveraged-fund short positions divided by total open interest",
                        "crowding_percentile_lookback": f"prior {CROWDING_LOOKBACK} non-backlog reports only; current report excluded",
                        "high_crowding_threshold": HIGH_CROWDING_THRESHOLD, "rolling_training_events": MODEL_WINDOW,
                        "target_sessions": TARGET_SESSIONS, "baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
                        "target": "log1p(next-five-observation BTC downside semivariance in percentage-points squared)",
                        "validation": f"{VALIDATION_START} through {TEST_START - dt.timedelta(days=1)}",
                        "test": f"{TEST_START} through {ASOF_DATE}",
                        "data_asof_date": ASOF_DATE.isoformat(), "cftc_report_end_date": CFTC_END.isoformat(),
                        "training_rule": "training signal_date and target_end_date must both be strictly earlier than current signal_date",
                        "overlap_rule": "no overlapping five-observation target windows",
                        "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block_events": BOOTSTRAP_BLOCK, "bootstrap_seed": RNG_SEED},
        "summary_metrics": {"validation_n": len(val_rows), "test_n": len(test_rows),
                            "validation_improvement_pct": val_imp, "test_improvement_pct": test_imp},
        "validation_metrics": validation, "test_metrics": test,
        "limitations": [
            "CFTC leveraged-fund classifications do not reveal the intent of individual positions; gross shorts may include cash-and-carry basis trades, directional positions and other strategies.",
            "CFTC code 133741 represents CME Bitcoin futures only, not offshore perpetual swaps or the global derivatives market.",
            "A fixed 14-day lag is conservative for the historical weekly schedule; known 2025 shutdown catch-up reports are excluded. Holiday-shifted report dates are retained, but any interval below six days fails closed as a cadence change. The sample is frozen at the 2026-11-26 as-of date.",
            "Current CFTC history may reflect revised positions and trader classifications; exact historical release timestamps are unavailable for the full history.",
            "Coinbase CBBTCUSD is a single-venue daily 5 p.m. Pacific price series; raw observations are not committed or redistributed.",
            "Current FRED vintage is used; historical ALFRED point-in-time vintages are not reconstructed.",
            "Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.",
        ],
    }


def main() -> int:
    try:
        result = run_research()
        report = render_report(result)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {"hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
                  "disposition": f"INCONCLUSIVE/INFEASIBLE — bounded source, timing or execution gate failed: {error}",
                  "completed_backtest": False,
                  "daily_kpi": "MET before this additional study by distinct real-data hypothesis backtests on 2026-11-26; this run did not count toward the KPI",
                  "run_id": RUN_ID, "run_attempt": RUN_ATTEMPT, "source_commit_sha": SOURCE_SHA,
                  "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "error": error}
        report = render_report(result, error)
    report_rel, manifest_rel = write_outputs(result, report)
    print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "status": result["status"],
                      "completed_backtest": result.get("completed_backtest", False),
                      "daily_kpi": result.get("daily_kpi"), "report_path": report_rel,
                      "manifest_path": manifest_rel, "summary_metrics": result.get("summary_metrics"),
                      "error": result.get("error")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
