#!/usr/bin/env python3
"""Forecast screen: Treasury General Account and ON RRP reserve-drain impulse -> BTC downside semivariance."""
from __future__ import annotations
import concurrent.futures, csv, datetime as dt, hashlib, json, math, os, random, statistics, urllib.parse
from pathlib import Path
import treasury_auction_demand as base
import stlfsi4_btc_downside_semivariance as btc

HYPOTHESIS_ID = "QFR-2026-11-27-TREASURY-RRP-DRAIN-BTC-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 16)
BTC_START_DATE = dt.date(2017, 8, 17)
RELEASE_LAG_DAYS, MODEL_WINDOW, TARGET_SESSIONS = 7, 104, 5
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2022, 1, 1)
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 4, 20261127
MIN_DRAIN_ROWS, MIN_BTC_ROWS = 400, 3000
MAX_DRAIN_AGE_DAYS, MAX_BTC_AGE_DAYS = 10, 2
ARCHIVE_WORKERS = 6
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
WDTGAL_PAGE = "https://fred.stlouisfed.org/series/WDTGAL"
RRP_PAGE = "https://fred.stlouisfed.org/series/RRPONTSYD"
H41_RELEASES = "https://www.federalreserve.gov/releases/h41/"
BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID, ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA, NOW = os.environ.get("GITHUB_SHA", "local"), dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "treasury-rrp-drain-btc-downside" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-TREASURY-RRP-DRAIN-BTC-DOWNSIDE-01.md"
BASE_FEATURES = ["pre_downside5_log", "pre_downside20_log", "pre_rv20_log"]
AUG_FEATURES = BASE_FEATURES + ["treasury_rrp_drain_increase_4w_pct"]


def parse_treasury_rrp_drain(body: bytes) -> tuple[dict[dt.date, float], dict]:
    """Align Wednesday TGA and daily ON RRP observations; convert RRP billions to TGA millions."""
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or not {"WDTGAL", "RRPONTSYD"}.issubset(set(reader.fieldnames)):
        raise ValueError(f"Unexpected FRED TGA/RRP schema: {reader.fieldnames}")
    date_col = next((name for name in ("observation_date", "DATE") if name in reader.fieldnames), None)
    if date_col is None:
        raise ValueError("FRED TGA/RRP CSV has no recognized observation-date column")
    values, missing_components, non_wednesday = {}, 0, 0
    for row in reader:
        day = base.parse_date(row.get(date_col))
        if day is None:
            raise ValueError(f"Invalid FRED observation date: {row.get(date_col)!r}")
        if day.weekday() != 2:
            non_wednesday += 1
            continue
        tga = base.parse_float(row.get("WDTGAL"))
        rrp_billions = base.parse_float(row.get("RRPONTSYD"))
        if tga is None or rrp_billions is None:
            missing_components += 1
            continue
        if tga < 0 or rrp_billions < 0:
            raise ValueError(f"Negative TGA or ON RRP observation on {day}")
        drain = tga + 1000.0 * rrp_billions
        if not math.isfinite(drain) or drain <= 0:
            raise ValueError(f"Invalid combined Treasury/ON RRP drain on {day}: {drain}")
        if day in values:
            raise ValueError(f"Duplicate Wednesday TGA/RRP observation: {day}")
        values[day] = drain
    if not values:
        raise ValueError("No complete common Wednesday TGA/RRP observations")
    return dict(sorted(values.items())), {
        "complete_wednesday_rows": len(values),
        "wednesday_rows_missing_a_component": missing_components,
        "ignored_non_wednesday_rows": non_wednesday,
        "rrp_conversion": "RRPONTSYD billions of USD multiplied by 1000 to millions of USD",
        "combined_definition": "WDTGAL + 1000 * RRPONTSYD",
    }


def fetch_sources() -> tuple[dict, dict, dict]:
    fred_url = f"{FRED_URL}?id=WDTGAL%2CRRPONTSYD&cosd={START_DATE.isoformat()}"
    fred_body = base.fetch_bytes(fred_url, timeout=25)
    drain, parse_meta = parse_treasury_rrp_drain(fred_body)
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
    fred_sha = hashlib.sha256(fred_body).hexdigest()
    sources = {
        "FRED": {
            "url": fred_url, "sha256": fred_sha, "series": ["WDTGAL", "RRPONTSYD"],
            "retrieved_at_utc": NOW.isoformat(),
            "common_wednesday_rows": len(drain),
            "first_date": min(drain).isoformat(), "last_date": max(drain).isoformat(),
            "parse_diagnostics": parse_meta,
        },
        "WDTGAL": {
            "series_page": WDTGAL_PAGE, "source": "Board of Governors H.4.1",
            "units": "millions of US dollars, not seasonally adjusted",
            "frequency": "weekly, Wednesday level", "common_wednesday_rows": len(drain),
        },
        "RRPONTSYD": {
            "series_page": RRP_PAGE, "source": "Federal Reserve Bank of New York",
            "units": "billions of US dollars, not seasonally adjusted",
            "frequency": "daily; sampled only on exact common Wednesdays",
            "common_wednesday_rows": len(drain),
        },
        "TREASURY_RRP_DRAIN": {
            "definition": "WDTGAL + 1000 * RRPONTSYD",
            "units": "millions of US dollars",
            "rows": len(drain), "first_date": min(drain).isoformat(),
            "last_date": max(drain).isoformat(),
        },
        "BTCUSDT": {
            "symbol": "BTCUSDT", "market_status": info["status"],
            "endpoint": "Binance Vision official Spot monthly/daily 1d kline archives",
            "interval": "1d", "timezone": "UTC", "rows": len(prices),
            "first_date": min(prices).isoformat(), "last_date": max(prices).isoformat(),
            "archive_count": len(archive_manifest),
            "monthly_archive_count": sum(row["kind"] == "monthly" for row in archive_manifest),
            "daily_archive_count": sum(row["kind"] == "daily" for row in archive_manifest),
            "timestamp_units_observed": sorted(timestamp_units),
            "archive_manifest_sha256": archive_sha, "archives": archive_manifest,
            "incomplete_current_candle_excluded": True,
        },
    }
    return drain, prices, sources


def validate_coverage(drain: dict, prices: dict, today: dt.date) -> dict:
    dd, pd = sorted(drain), sorted(prices)
    if len(dd) < MIN_DRAIN_ROWS or len(pd) < MIN_BTC_ROWS:
        raise ValueError(f"Insufficient source depth: common TGA/RRP Wednesdays={len(dd)}, BTCUSDT={len(pd)}")
    if dd[0] > START_DATE + dt.timedelta(days=14) or pd[0] > BTC_START_DATE + dt.timedelta(days=2):
        raise ValueError(f"Source history starts too late: drain={dd[0]}, BTCUSDT={pd[0]}")
    if dd[-1] > today or pd[-1] > today:
        raise ValueError("A source contains a future-dated observation")
    if (today - dd[-1]).days > MAX_DRAIN_AGE_DAYS:
        raise ValueError(f"TGA/RRP common Wednesday series is stale: {dd[-1]}")
    if (today - pd[-1]).days > MAX_BTC_AGE_DAYS:
        raise ValueError(f"BTCUSDT daily candles are stale: {pd[-1]}")
    if any(day.weekday() != 2 for day in dd):
        raise ValueError("TGA/RRP series contains a non-Wednesday observation")
    drain_gaps = [(right - left).days for left, right in zip(dd, dd[1:])]
    price_gaps = [(right - left).days for left, right in zip(pd, pd[1:])]
    if any(gap > 14 for gap in drain_gaps):
        raise ValueError("TGA/RRP common Wednesday series has a gap greater than 14 days")
    if any(gap != 1 for gap in price_gaps):
        raise ValueError("BTCUSDT daily candles contain a missing UTC day")
    return {
        "TREASURY_RRP_DRAIN": {"rows": len(dd), "first_date": dd[0].isoformat(), "last_date": dd[-1].isoformat()},
        "BTCUSDT": {"rows": len(pd), "first_date": pd[0].isoformat(), "last_date": pd[-1].isoformat()},
    }


def build_events(drain: dict, prices: dict) -> tuple[list[dict], dict]:
    dates = sorted(prices)
    returns = [None]
    for index in range(1, len(dates)):
        returns.append(
            math.log(prices[dates[index]] / prices[dates[index - 1]])
            if (dates[index] - dates[index - 1]).days == 1 else None
        )
    index_by_date = {day: index for index, day in enumerate(dates)}
    weeks = sorted(drain)
    events = []
    skipped = {
        "irregular_weekly_window": 0, "missing_signal": 0,
        "insufficient_price_history": 0, "incomplete_target": 0, "invalid_returns": 0,
    }
    for index in range(4, len(weeks)):
        window = weeks[index - 4:index + 1]
        if any((right - left).days != 7 for left, right in zip(window, window[1:])):
            skipped["irregular_weekly_window"] += 1
            continue
        signal = weeks[index] + dt.timedelta(days=RELEASE_LAG_DAYS)
        j = index_by_date.get(signal)
        if j is None:
            skipped["missing_signal"] += 1
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
        prior5 = [float(value) for value in prior5]
        prior20 = [float(value) for value in prior20]
        future = [float(value) for value in future]
        target = btc.semi_var_pct2(future)
        drain_increase = 100.0 * math.log(drain[weeks[index]] / drain[weeks[index - 4]])
        events.append({
            "record_date": signal, "signal_date": signal, "drain_week": weeks[index],
            "target_start_date": dates[j + 1], "target_end_date": dates[j + TARGET_SESSIONS],
            "target_semivariance_pct2": target, "target_bp": math.log1p(target),
            "pre_downside5_log": math.log1p(btc.semi_var_pct2(prior5)),
            "pre_downside20_log": math.log1p(btc.semi_var_pct2(prior20)),
            "pre_rv20_log": math.log1p(btc.total_var_pct2(prior20)),
            "treasury_rrp_drain_increase_4w_pct": drain_increase,
        })
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("BTC target windows overlap or are not fully matured")
    return events, {
        "candidate_weeks": max(0, len(weeks) - 4), "accepted_events": len(events),
        "skipped": skipped, "release_lag_days": RELEASE_LAG_DAYS,
        "target_sessions": TARGET_SESSIONS, "weekly_event_spacing_days": 7,
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
            "record_date": current["signal_date"], "signal_date": current["signal_date"],
            "target_end_date": current["target_end_date"], "target_bp": current["target_bp"],
            "baseline_prediction_bp": baseline, "augmented_prediction_bp": augmented,
            "train_n": len(train),
        })
    return predictions


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0, "baseline_rmse_log1p": None, "augmented_rmse_log1p": None,
            "baseline_mae_log1p": None, "augmented_mae_log1p": None,
            "rmse_improvement_pct": None,
        }
    baseline_errors = [row["baseline_prediction_bp"] - row["target_bp"] for row in rows]
    augmented_errors = [row["augmented_prediction_bp"] - row["target_bp"] for row in rows]
    baseline_rmse = math.sqrt(statistics.fmean(error * error for error in baseline_errors))
    augmented_rmse = math.sqrt(statistics.fmean(error * error for error in augmented_errors))
    return {
        "n": len(rows), "baseline_rmse_log1p": baseline_rmse,
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
        "observations": len(losses), "reps": len(means), "block_size_events": BOOTSTRAP_BLOCK,
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
            "favors augmentation; current-vintage revision risk prevents independent validation"
        )
    if vi is not None and ti is not None and vi < 0 and ti < 0 and paired["ci95_high"] < 0:
        return "REJECTED", "REJECTED — both chronological periods worsen and paired-loss inference favors the baseline"
    return "INCONCLUSIVE", "INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority"


def run_research() -> dict:
    drain, prices, sources = fetch_sources()
    coverage = validate_coverage(drain, prices, NOW.date())
    events, event_meta = build_events(drain, prices)
    predictions = walk_forward(events)
    validation = summarize([
        row for row in predictions if VALIDATION_START <= row["signal_date"] < TEST_START
    ])
    test = summarize([row for row in predictions if row["signal_date"] >= TEST_START])
    paired = paired_loss_bootstrap([row for row in predictions if row["signal_date"] >= TEST_START])
    status, disposition = decide(validation, test, paired)
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition,
        "completed_backtest": True, "retrieved_at_utc": NOW.isoformat(),
        "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "daily_kpi": (
            "The 2026-11-27 minimum was already met by distinct ETF-relative-flow and BTC blockspace-fee-rate real-data screens; "
            "this is an additional hypothesis backtest. If execution falls on a later UTC date, this distinct completed screen "
            "may count toward that date's minimum."
        ),
        "coverage": coverage, "data_sources": sources, "event_construction": event_meta,
        "data_scope": (
            f"FRED WDTGAL + RRPONTSYD common Wednesday observations {coverage['TREASURY_RRP_DRAIN']['first_date']} to "
            f"{coverage['TREASURY_RRP_DRAIN']['last_date']} ({coverage['TREASURY_RRP_DRAIN']['rows']} rows; "
            f"combined TGA + ON RRP in millions USD); Binance BTCUSDT spot 1d UTC "
            f"{coverage['BTCUSDT']['first_date']} to {coverage['BTCUSDT']['last_date']} "
            f"({coverage['BTCUSDT']['rows']} candles); validation 2019-2021; test 2022 onward"
        ),
        "methodology": {
            "baseline_features": BASE_FEATURES, "augmented_features": AUG_FEATURES,
            "predictor": "100 * ln((WDTGAL[t] + 1000*RRPONTSYD[t]) / (WDTGAL[t-4] + 1000*RRPONTSYD[t-4])); positive means four-week increase in Treasury cash plus ON RRP absorption",
            "availability": (
                "Exact common Wednesday WDTGAL and RRPONTSYD observations are used only at the close of the UTC BTC candle "
                "dated seven calendar days later; H.4.1 is normally released Thursday afternoon, and no missing component is filled."
            ),
            "target": "log1p(next-five-UTC-session BTCUSDT downside semivariance, percent-squared units)",
            "training_window_events": MODEL_WINDOW,
            "training_rule": "prior signal and target_end must both be strictly earlier than current signal",
            "validation": "2019-01-01 through 2021-12-31", "test": "2022-01-01 onward",
            "bootstrap_reps": BOOTSTRAP_REPS, "bootstrap_block_events": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "summary_metrics": {
            "validation_n": validation["n"], "test_n": test["n"],
            "validation_rmse_improvement_pct": validation["rmse_improvement_pct"],
            "test_rmse_improvement_pct": test["rmse_improvement_pct"],
        },
        "validation_metrics": validation, "test_metrics": test,
        "paired_squared_loss_bootstrap": paired,
        "limitations": [
            "WDTGAL plus ON RRP is a narrow liability-side reserve-drain proxy, not total net liquidity, bank reserves or a complete measure of dollar funding conditions.",
            "WDTGAL is a weekly Wednesday level and RRPONTSYD is a daily transaction-balance series; only exact common Wednesdays are used and missing components are not filled.",
            "The screen uses the current FRED vintage, not historical ALFRED vintages; the conservative seven-day lag does not remove historical revision/look-ahead risk.",
            "The fixed seven-day signal lag is conservative but does not reconstruct every historical release timestamp or revision.",
            "BTCUSDT is one venue's spot series. Binance Vision archives are checksum-verified, but this is not an exchange-independent consolidated market history.",
            "Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.",
            "No raw FRED or Binance observations are committed; source hashes and aggregate metrics are retained.",
        ],
    }


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
        f"| {HYPOTHESIS_ID} | {status} | A strictly lagged four-week increase in the combined "
        f"Treasury General Account and ON RRP balances may add information about next-five-session "
        f"BTC downside semivariance beyond recent downside risk and realized variance. | {scope} | "
        f"{disposition}; {metrics_text} | [preregistration]({PREREG_PATH.name}) / "
        f"[session report]({report_link}) / [manifest]({manifest_link}) |"
    )
    lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    existing = next((i for i, line in enumerate(lines) if line.startswith(f"| {HYPOTHESIS_ID} |")), None)
    if existing is not None:
        lines[existing] = row
    else:
        separator = next((i for i, line in enumerate(lines) if line.startswith("|---")), None)
        if separator is None:
            raise ValueError("Hypothesis registry table separator not found")
        lines.insert(separator + 1, row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

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


def render_report(result: dict) -> str:
    lines = [
        f"# Research session — Treasury/ON RRP drain and BTC downside semivariance ({STAMP})",
        "", f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {result.get('status')}",
        f"- **Disposition:** {result.get('disposition')}", f"- **Daily KPI:** {result.get('daily_kpi')}",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}", f"- **Triggering commit:** {SOURCE_SHA}", "",
    ]
    if result.get("error"):
        lines += [
            "## Execution blocker", "", f"- {result['error']}",
            "- No valid real-data backtest completed in this run; the previously met 2026-11-27 KPI remains independent.", "",
        ]
    else:
        val, test = result["validation_metrics"], result["test_metrics"]
        fred = result["data_sources"]["FRED"]
        btc_source = result["data_sources"]["BTCUSDT"]
        lines += [
            "## Preregistered method", "",
            "- Predictor: four-week log increase in WDTGAL plus ON RRP; RRP billions are converted to millions before addition.",
            "- Availability: exact common Wednesday observations are used only at the close of the UTC BTC candle dated seven calendar days later.",
            "- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.",
            "- Target: next-five-session BTC downside semivariance, transformed with log1p.",
            "- Rolling training window: 104 prior weekly events; each training target must be fully matured before the current signal.",
            "- Validation: 2019–2021. Test: 2022 onward.", "",
            "## Data provenance", "",
            "| Source | First | Last | Rows | SHA-256 / manifest |", "|---|---|---|---:|---|",
            f"| FRED WDTGAL + RRPONTSYD | {fred['first_date']} | {fred['last_date']} | {fred['common_wednesday_rows']} common Wednesdays | {fred['sha256']} |",
            f"| BTCUSDT | {btc_source['first_date']} | {btc_source['last_date']} | {btc_source['rows']} candles | {btc_source['archive_count']} checksummed archives; {btc_source['archive_manifest_sha256']} |",
            "", "## Walk-forward results", "",
            "| Metric | Validation 2019–2021 | Test 2022 onward |", "|---|---:|---:|",
            f"| Forecasts | {val['n']} | {test['n']} |",
            f"| Baseline RMSE (log1p semivariance) | {val['baseline_rmse_log1p']} | {test['baseline_rmse_log1p']} |",
            f"| Augmented RMSE (log1p semivariance) | {val['augmented_rmse_log1p']} | {test['augmented_rmse_log1p']} |",
            f"| RMSE improvement | {val['rmse_improvement_pct']}% | {test['rmse_improvement_pct']}% |",
            "", "## Paired test-loss uncertainty", "",
            f"- {json.dumps(base.json_safe(result.get('paired_squared_loss_bootstrap')), sort_keys=True)}",
            "", "## Interpretation", "", result.get("disposition", "No disposition established."),
            "", "## Verified / unverified", "",
            "**VERIFIED:** FRED schemas, exact Wednesday alignment, source coverage, Binance archive checksums, event timing, non-overlapping target windows, walk-forward maturity and metrics, if the backtest completed.",
            "**UNVERIFIED:** historical point-in-time FRED vintages, independent replication, future-regime stability, causality and instrument-level economic value.",
            "", "## Limitations", "",
        ]
        lines.extend(f"- {item}" for item in result.get("limitations", []))
    return "\n".join(lines) + "\n"


def write_outputs(result: dict) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-treasury-rrp-drain-btc-{RUN_ID}.md"
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
            "hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE/INFEASIBLE — bounded source/execution failure: {type(exc).__name__}: {exc}",
            "completed_backtest": False, "run_id": RUN_ID, "run_attempt": ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "daily_kpi": "The 2026-11-27 minimum was already met by distinct real-data screens; this failed source/execution attempt does not count.",
            "error": f"{type(exc).__name__}: {exc}",
            "alternatives_attempted": [
                "FRED public combined WDTGAL/RRPONTSYD CSV",
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
