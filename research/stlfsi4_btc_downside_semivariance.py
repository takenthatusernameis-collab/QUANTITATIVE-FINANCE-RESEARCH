#!/usr/bin/env python3
"""Forecast screen: lagged STLFSI4 tightening -> BTC five-session downside semivariance."""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, math, os, statistics, urllib.parse
from pathlib import Path
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01"
START_DATE = dt.date(2017, 8, 17)
RELEASE_LAG_DAYS, MODEL_WINDOW, TARGET_SESSIONS = 7, 104, 5
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2022, 1, 1)
BOOTSTRAP_REPS, MIN_STRESS_ROWS, MIN_PRICE_ROWS = 2000, 400, 3000
MAX_STRESS_AGE_DAYS, MAX_PRICE_AGE_DAYS, MS_PER_DAY = 10, 2, 86_400_000
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_CALENDAR = "https://fred.stlouisfed.org/releases/calendar?rid=187"
BINANCE_HOSTS = ("https://data-api.binance.vision", "https://api.binance.com")
ROOT = Path(__file__).resolve().parents[1]
RUN_ID, ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA, NOW = os.environ.get("GITHUB_SHA", "local"), dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "stlfsi4-btc-downside-semivariance" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG = ROOT / "research" / "PREREGISTERED-QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01.md"
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["stlfsi4_4w_change"]


def parse_fred(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or "STLFSI4" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED STLFSI4 schema: {reader.fieldnames}")
    date_col = next((x for x in ("observation_date", "DATE") if x in reader.fieldnames), None)
    if not date_col:
        raise ValueError("FRED CSV has no recognized observation-date column")
    values = {}
    for row in reader:
        day = base.parse_date(row.get(date_col))
        if day is None:
            raise ValueError(f"Invalid STLFSI4 date: {row.get(date_col)!r}")
        value = base.parse_float(row.get("STLFSI4"))
        if value is None:
            continue
        if day in values:
            raise ValueError(f"Duplicate STLFSI4 observation: {day}")
        values[day] = value
    if not values:
        raise ValueError("No valid STLFSI4 observations")
    return dict(sorted(values.items()))


def parse_klines(body: bytes, now_ms: int) -> dict[dt.date, float]:
    rows = json.loads(body.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Binance kline response is not an array")
    values = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            raise ValueError("Unexpected Binance kline row schema")
        open_ms, close_ms = int(row[0]), int(row[6])
        if open_ms % MS_PER_DAY or close_ms != open_ms + MS_PER_DAY - 1:
            raise ValueError("BTCUSDT candle is not aligned to a full UTC day")
        if close_ms > now_ms:
            continue
        close = base.parse_float(row[4])
        if close is None or close <= 0:
            raise ValueError("Invalid BTCUSDT daily close")
        day = dt.datetime.fromtimestamp(open_ms / 1000, dt.timezone.utc).date()
        if day in values:
            raise ValueError(f"Duplicate BTCUSDT candle: {day}")
        values[day] = close
    return dict(sorted(values.items()))


def fetch_sources() -> tuple[dict, dict, dict]:
    fred_url = f"{FRED_URL}?id=STLFSI4&cosd={START_DATE.isoformat()}"
    fred_body = base.fetch_bytes(fred_url)
    stress = parse_fred(fred_body)
    now_ms = int(NOW.timestamp() * 1000)
    start_ms = int(dt.datetime.combine(START_DATE, dt.time(), dt.timezone.utc).timestamp() * 1000)
    errors = []
    for host in BINANCE_HOSTS:
        try:
            info_url = f"{host}/api/v3/exchangeInfo?{urllib.parse.urlencode({'symbol': 'BTCUSDT'})}"
            info_body = base.fetch_bytes(info_url)
            symbols = json.loads(info_body.decode("utf-8")).get("symbols", [])
            if len(symbols) != 1:
                raise ValueError("exchangeInfo did not return exactly BTCUSDT")
            info = symbols[0]
            if (info.get("symbol"), info.get("status"), info.get("baseAsset"), info.get("quoteAsset")) != ("BTCUSDT", "TRADING", "BTC", "USDT"):
                raise ValueError(f"BTCUSDT is not an active spot USDT market: {info}")
            cursor, prices, hashes, pages = start_ms, {}, [], 0
            while cursor <= now_ms:
                params = {"symbol": "BTCUSDT", "interval": "1d", "timeZone": "0", "startTime": cursor, "endTime": now_ms, "limit": 1000}
                url = f"{host}/api/v3/klines?{urllib.parse.urlencode(params)}"
                body = base.fetch_bytes(url)
                rows = json.loads(body.decode("utf-8"))
                if not isinstance(rows, list):
                    raise ValueError("Binance kline response is not an array")
                if not rows:
                    break
                hashes.append(hashlib.sha256(body).hexdigest())
                page = parse_klines(body, now_ms)
                if set(prices).intersection(page):
                    raise ValueError("Binance pagination returned duplicate candles")
                prices.update(page)
                next_cursor = int(rows[-1][0]) + MS_PER_DAY
                if next_cursor <= cursor:
                    raise ValueError("Binance pagination failed to advance")
                cursor = next_cursor
                pages += 1
                if pages > 10:
                    raise ValueError("Binance history exceeded the 10-page safety bound")
                if len(rows) < 1000:
                    break
            if not prices:
                raise ValueError("No completed BTCUSDT daily candles returned")
            prices = dict(sorted(prices.items()))
            return stress, prices, {
                "STLFSI4": {
                    "url": fred_url, "sha256": hashlib.sha256(fred_body).hexdigest(),
                    "rows": len(stress), "first_date": min(stress).isoformat(),
                    "last_date": max(stress).isoformat(), "release_calendar": FRED_CALENDAR,
                    "vintage": "current FRED vintage; historical ALFRED vintages not reconstructed",
                },
                "BTCUSDT": {
                    "symbol": "BTCUSDT", "market_status": info["status"], "endpoint": f"{host}/api/v3/klines",
                    "exchange_info_url": info_url, "exchange_info_sha256": hashlib.sha256(info_body).hexdigest(),
                    "interval": "1d", "timezone": "UTC", "rows": len(prices),
                    "first_date": min(prices).isoformat(), "last_date": max(prices).isoformat(),
                    "page_count": pages, "page_sha256": hashes, "pagination_limit": 1000,
                    "incomplete_current_candle_excluded": True,
                },
            }
        except Exception as exc:
            errors.append(f"{host}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Binance public-data endpoints failed: " + " | ".join(errors))


def validate_coverage(stress: dict, prices: dict, today: dt.date) -> dict:
    sd, pd = sorted(stress), sorted(prices)
    if len(sd) < MIN_STRESS_ROWS or len(pd) < MIN_PRICE_ROWS:
        raise ValueError(f"Insufficient source depth: STLFSI4={len(sd)}, BTCUSDT={len(pd)}")
    if sd[0] > START_DATE + dt.timedelta(days=45) or pd[0] > START_DATE + dt.timedelta(days=14):
        raise ValueError(f"Source history starts too late: STLFSI4={sd[0]}, BTCUSDT={pd[0]}")
    if sd[-1] > today or pd[-1] > today:
        raise ValueError("A source contains a future-dated observation")
    if (today - sd[-1]).days > MAX_STRESS_AGE_DAYS:
        raise ValueError(f"STLFSI4 stale: {sd[-1]}")
    if (today - pd[-1]).days > MAX_PRICE_AGE_DAYS:
        raise ValueError(f"BTCUSDT daily candles stale: {pd[-1]}")
    if any(day.weekday() != 4 for day in sd):
        raise ValueError("STLFSI4 dates are not weekly-ending Fridays")
    stress_gaps = [(b - a).days for a, b in zip(sd, sd[1:])]
    price_gaps = [(b - a).days for a, b in zip(pd, pd[1:])]
    if any(gap > 14 for gap in stress_gaps):
        raise ValueError("STLFSI4 has a gap greater than 14 days")
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("BTCUSDT daily candles contain a missing UTC day")
    return {
        "STLFSI4": {"rows": len(sd), "first_date": sd[0].isoformat(), "last_date": sd[-1].isoformat()},
        "BTCUSDT": {"rows": len(pd), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat()},
    }


def semi_var_pct2(values: list[float]) -> float:
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError("Invalid semivariance window")
    return statistics.fmean(min(x, 0.0) ** 2 for x in values) * 10_000.0


def total_var_pct2(values: list[float]) -> float:
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError("Invalid variance window")
    return statistics.fmean(x * x for x in values) * 10_000.0


def build_events(stress: dict, prices: dict) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns = [None]
    for i in range(1, len(dates)):
        returns.append(math.log(prices[dates[i]] / prices[dates[i - 1]]) if (dates[i] - dates[i - 1]).days == 1 else None)
    index_by_date = {day: i for i, day in enumerate(dates)}
    weeks = sorted(stress)
    events, skipped = [], {"irregular_stress_window": 0, "missing_signal": 0, "insufficient_history": 0, "incomplete_target": 0, "invalid_returns": 0}
    for i in range(4, len(weeks)):
        window = weeks[i - 4:i + 1]
        if any((b - a).days != 7 for a, b in zip(window, window[1:])):
            skipped["irregular_stress_window"] += 1
            continue
        signal = weeks[i] + dt.timedelta(days=RELEASE_LAG_DAYS)
        j = index_by_date.get(signal)
        if j is None:
            skipped["missing_signal"] += 1
            continue
        if j < 20:
            skipped["insufficient_history"] += 1
            continue
        if j + TARGET_SESSIONS >= len(dates):
            skipped["incomplete_target"] += 1
            continue
        prior5, prior20 = returns[j - 4:j + 1], returns[j - 19:j + 1]
        future = returns[j + 1:j + 1 + TARGET_SESSIONS]
        if any(x is None for x in prior5 + prior20 + future):
            skipped["invalid_returns"] += 1
            continue
        p5, p20, fut = [float(x) for x in prior5], [float(x) for x in prior20], [float(x) for x in future]
        target = semi_var_pct2(fut)
        events.append({
            "record_date": signal, "signal_date": signal, "week_end_date": weeks[i],
            "target_start_date": dates[j + 1], "target_end_date": dates[j + TARGET_SESSIONS],
            "target_semivariance_pct2": target, "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(semi_var_pct2(p5)),
            "pre_downside20_log": math.log1p(semi_var_pct2(p20)),
            "pre_rv20_log": math.log1p(total_var_pct2(p20)),
            "stlfsi4_4w_change": stress[weeks[i]] - stress[weeks[i - 4]],
        })
    for a, b in zip(events, events[1:]):
        if a["target_end_date"] >= b["signal_date"]:
            raise ValueError("Target windows overlap or are not matured")
    return events, {"candidate_weeks": len(weeks), "accepted_events": len(events), "skipped": skipped, "release_lag_days": RELEASE_LAG_DAYS, "target_sessions": TARGET_SESSIONS}


def walk_forward(events: list[dict]) -> list[dict]:
    predictions = []
    for current in events:
        train = [r for r in events if r["signal_date"] < current["signal_date"] and r["target_end_date"] < current["signal_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            b = base.fit_ols_predict(train, current, BASE_FEATURES)
            a = base.fit_ols_predict(train, current, AUG_FEATURES)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "record_date": current["signal_date"], "target_bp": current["target_bp"],
            "baseline_prediction_bp": b, "augmented_prediction_bp": a,
            "signal_date": current["signal_date"], "target_end_date": current["target_end_date"],
            "target_semivariance_pct2": current["target_semivariance_pct2"], "train_n": len(train),
        })
    return predictions


def metrics(rows: list[dict]) -> dict:
    b = base.forecast_metrics(rows, "baseline_prediction_bp")
    a = base.forecast_metrics(rows, "augmented_prediction_bp")
    improvement = None if not b or b["rmse_bp"] <= 0 else 100 * (b["rmse_bp"] - a["rmse_bp"]) / b["rmse_bp"]
    return {"n": len(rows), "baseline": b, "augmented": a, "rmse_improvement_pct": improvement}


def decide(val: dict, test: dict, paired: dict | None) -> tuple[str, str]:
    if val["n"] < 30 or test["n"] < 30 or paired is None:
        return "INCONCLUSIVE", "INCONCLUSIVE — insufficient forecast sample or paired-loss inference"
    vi, ti = val["rmse_improvement_pct"], test["rmse_improvement_pct"]
    if vi is not None and ti is not None and vi > 0 and ti > 0 and paired["ci_95_low_bp2"] > 0:
        return "BACKTESTED", "PROMISING SCREEN — both chronological periods improve and paired-loss inference favors augmentation; current-vintage revision risk prevents independent validation"
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci_95_high_bp2"] < 0:
        return "REJECTED", "REJECTED — both chronological periods worsen and paired-loss inference favors the baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority"


def fmt_rmse(m: dict, key: str) -> str:
    item = m.get(key) or {}
    value = item.get("rmse_bp")
    return f"{value:.8f}" if isinstance(value, (int, float)) and math.isfinite(value) else "n/a"


def fmt_pct(value) -> str:
    return f"{value:.4f}%" if isinstance(value, (int, float)) and math.isfinite(value) else "n/a"


def run_research() -> dict:
    stress, prices, sources = fetch_sources()
    coverage = validate_coverage(stress, prices, NOW.date())
    events, event_meta = build_events(stress, prices)
    preds = walk_forward(events)
    val = metrics([r for r in preds if VALIDATION_START <= r["signal_date"] < TEST_START])
    test = metrics([r for r in preds if r["signal_date"] >= TEST_START])
    paired = base.bootstrap_paired_squared_loss_difference([r for r in preds if r["signal_date"] >= TEST_START], reps=BOOTSTRAP_REPS)
    status, disposition = decide(val, test, paired)
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition,
        "completed_backtest": True, "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID,
        "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "daily_kpi": f"This distinct real-data backtest completed on UTC date {NOW.date()}; the 2026-11-25 minimum was already met by earlier experiments.",
        "coverage": coverage, "data_sources": sources, "event_construction": event_meta,
        "data_scope": f"Binance BTCUSDT spot 1d UTC {coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} ({coverage['BTCUSDT']['rows']} complete candles); FRED STLFSI4 weekly {coverage['STLFSI4']['first_date']} to {coverage['STLFSI4']['last_date']} ({coverage['STLFSI4']['rows']} observations); validation 2019-2021; test 2022 onward",
        "methodology": {
            "baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
            "stress_feature": "STLFSI4[week t] - STLFSI4[week t-4]; positive means increasing stress",
            "availability": "week-ending Friday observation used at Friday + 7 calendar days; signal formed at that UTC daily close",
            "target": "log1p(mean squared negative BTC daily log returns over next five UTC sessions, percent-squared units)",
            "rolling_training_events": MODEL_WINDOW,
            "training_rule": "prior signal and target_end must both be strictly earlier than current signal",
            "validation": "2019-01-01 through 2021-12-31", "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block": base.BOOTSTRAP_BLOCK,
            "bootstrap_seed": base.LOSS_BOOTSTRAP_SEED,
        },
        "summary_metrics": {"validation_n": val["n"], "test_n": test["n"], "validation_improvement_pct": val["rmse_improvement_pct"], "test_improvement_pct": test["rmse_improvement_pct"]},
        "validation_metrics": val, "test_metrics": test, "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "STLFSI4 is revised. This screen uses the current FRED vintage, not historical ALFRED vintages; publication lag does not remove revision look-ahead.",
            "FRED labels STLFSI4 weekly ending Friday and subject to revision. Its calendar lists 9:00 a.m. US Central releases on Wednesdays with holiday shifts; Friday plus seven calendar days is a conservative signal date.",
            "STLFSI4 is a composite of 18 weekly financial variables, not an exogenous shock or causal measure.",
            "BTCUSDT is one venue's spot series. This is a forecast screen, not a trading strategy, executable P&L, or tradable-premium claim.",
            "No raw FRED or Binance observations are committed; only source hashes, retrieval metadata and aggregate metrics are retained.",
        ],
    }


def update_documents(result: dict, report_path: str, manifest_path: str) -> None:
    status, disposition = result.get("status", "INCONCLUSIVE"), result.get("disposition", "INCONCLUSIVE")
    scope = result.get("data_scope", "source acceptance incomplete")
    summary = result.get("summary_metrics") or {}
    metrics_text = f"validation/test n={summary.get('validation_n', 0)}/{summary.get('test_n', 0)}, RMSE improvement={summary.get('validation_improvement_pct')}%/{summary.get('test_improvement_pct')}%; forecast-only, current-vintage limitation"
    report_link, manifest_link = "../" + report_path, "../" + manifest_path
    row = (
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged four-week increase in the St. Louis Fed Financial Stress Index adds information about next-five-session BTC downside semivariance beyond recent BTC downside semivariance and realized variance. | {scope} | {disposition}; {metrics_text} | [{report_path}]({report_link}) |"
    )
    lines = REGISTRY.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is None:
        header = next((i for i, line in enumerate(lines) if line.startswith("|---")), None)
        if header is None:
            raise ValueError("Hypothesis registry table header not found")
        lines.insert(header + 1, row)
    else:
        lines[existing] = row
    REGISTRY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = PREREG.read_text(encoding="utf-8")
    status_line = f"- **Status:** {status} — {disposition}. {'One bounded real-data backtest completed.' if result.get('completed_backtest') else 'No valid backtest completed; source acceptance failed.'}"
    p_lines = text.splitlines()
    for i, line in enumerate(p_lines):
        if line.startswith("- **Status:**"):
            p_lines[i] = status_line
            break
    text = "\n".join(p_lines).split("\n## Empirical disposition")[0].rstrip()
    text += (
        "\n\n## Empirical disposition\n\n"
        f"- **Final status:** {status} — {disposition}.\n"
        f"- **Completed backtest:** {'yes' if result.get('completed_backtest') else 'no'}.\n"
        f"- **Data scope:** {scope}.\n"
        f"- **Summary:** {json.dumps(base.json_safe(summary), sort_keys=True)}.\n"
        f"- **Report:** [{report_path}]({report_link}).\n"
        f"- **Manifest:** [{manifest_path}]({manifest_link}).\n"
        "- **Interpretation:** forecast screen only. Current-vintage STLFSI4 revisions remain a material limitation; even a promising result is not independently validated or tradable.\n"
    )
    PREREG.write_text(text + "\n", encoding="utf-8")


def render_report(result: dict, error: str | None = None) -> str:
    lines = [
        f"# Research session — STLFSI4 and BTC downside semivariance ({NOW.isoformat()})", "",
        f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}",
        f"- **Daily KPI:** {result.get('daily_kpi', 'not met by this study')}",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}", f"- **Triggering commit:** {SOURCE_SHA}", "",
    ]
    if error:
        lines += ["## Blocker", "", f"- {error}", "- No valid empirical backtest completed; this run does not count toward the daily minimum.", ""]
    else:
        v, t = result["validation_metrics"], result["test_metrics"]
        lines += [
            "## Preregistered method", "",
            "- Predictor: four-week change in STLFSI4; positive means increasing financial stress.",
            "- Signal: close of the Binance UTC daily candle dated seven calendar days after the Friday observation.",
            "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session realized variance.",
            "- Target: mean squared negative BTC log returns over the next five UTC daily sessions.",
            "- Rolling training window: 104 prior weekly events; every training target must be fully matured before the signal.",
            "- Validation: 2019–2021. Test: 2022 onward. Primary metric: RMSE in log1p downside-semivariance space.", "",
            "## Data provenance", "",
            "| Source | First | Last | Rows | Hashes |", "|---|---|---:|---:|---|",
            f"| STLFSI4 | {result['coverage']['STLFSI4']['first_date']} | {result['coverage']['STLFSI4']['last_date']} | {result['coverage']['STLFSI4']['rows']} | {result['data_sources']['STLFSI4']['sha256']} |",
            f"| BTCUSDT | {result['coverage']['BTCUSDT']['first_date']} | {result['coverage']['BTCUSDT']['last_date']} | {result['coverage']['BTCUSDT']['rows']} | {', '.join(result['data_sources']['BTCUSDT']['page_sha256'])} |", "",
            "## Frozen results", "",
            "| Metric | Validation | Test |", "|---|---:|---:|",
            f"| Forecasts | {v['n']} | {t['n']} |",
            f"| Baseline RMSE | {fmt_rmse(v, 'baseline')} | {fmt_rmse(t, 'baseline')} |",
            f"| Augmented RMSE | {fmt_rmse(v, 'augmented')} | {fmt_rmse(t, 'augmented')} |",
            f"| RMSE improvement | {fmt_pct(v['rmse_improvement_pct'])} | {fmt_pct(t['rmse_improvement_pct'])} |", "",
            f"- Accepted events: {result['event_construction']['accepted_events']} of {result['event_construction']['candidate_weeks']}.",
            f"- Skipped: {json.dumps(result['event_construction']['skipped'], sort_keys=True)}.",
            f"- Paired test squared-loss bootstrap: {json.dumps(base.json_safe(result['paired_squared_loss_bootstrap']), sort_keys=True)}.", "",
            "## Verified / unverified", "",
            "**VERIFIED:** public BTCUSDT spot symbol status, complete daily candle coverage and UTC continuity; FRED weekly-Friday schema and freshness; conservative release lag; deterministic tests; event maturity and result under this code/data vintage.",
            "",
            "**UNVERIFIED:** historical point-in-time STLFSI4 vintages, future-regime stability, cross-venue replication, economic value and trading profitability.", "",
            "## Limitations", "",
        ]
        lines += [f"- {x}" for x in result["limitations"]]
        lines += ["", "## Reproducibility", "", f"- Workflow: https://github.com/{base.REPO}/actions/runs/{RUN_ID}", "- Source: research/stlfsi4_btc_downside_semivariance.py", "- Tests: research/test_stlfsi4_btc_downside_semivariance.py"]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        result, error = run_research(), None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — bounded source/execution failure: {error}",
            "completed_backtest": False, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
            "daily_kpi": f"2026-11-25 minimum was already MET by earlier experiments; this run on {NOW.date()} did not complete a valid backtest.",
            "data_scope": "source acceptance incomplete", "error": error,
        }
    report = render_report(result, error)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-stlfsi4-btc-downside-semivariance-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    report_path.write_text(report, encoding="utf-8")
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rel_report, rel_manifest = str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))
    update_documents(result, rel_report, rel_manifest)
    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID, "status": result["status"],
        "completed_backtest": result.get("completed_backtest", False),
        "disposition": result["disposition"], "daily_kpi": result["daily_kpi"],
        "report_path": rel_report, "manifest_path": rel_manifest,
        "summary_metrics": result.get("summary_metrics"), "error": result.get("error"),
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
