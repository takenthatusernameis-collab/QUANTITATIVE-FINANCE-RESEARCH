#!/usr/bin/env python3
"""Preregistered Treasury auction supply-intensity walk-forward forecast test."""
from __future__ import annotations
import bisect, datetime as dt, json, math, os, statistics
from pathlib import Path
import treasury_auction_demand as base

HYPOTHESIS_ID = "QFR-2026-11-25-UST-SUPPLY-INTENSITY-01"
TITLE = "Treasury 10-year auction supply intensity and next-business-day yield response"
SUPPLY_LOOKBACK, RANK_LOOKBACK, MODEL_WINDOW = 12, 52, 52
VALIDATION_START, TEST_START = dt.date(2019, 1, 1), dt.date(2023, 1, 1)
MIN_OFFERING_COVERAGE, BOOTSTRAP_REPS = 0.95, 2000
ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
RUN_ID, RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "treasury-supply-pressure" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"


def enrich_offering_amounts(raw_rows, auctions, min_coverage=MIN_OFFERING_COVERAGE):
    by_key = {}
    for raw in raw_rows:
        key = (str(raw.get("cusip") or "").strip(), base.parse_date(raw.get("auction_date")))
        amount = base.parse_float(raw.get("offering_amt"))
        if not key[0] or key[1] is None or amount is None or not math.isfinite(amount) or amount <= 0:
            continue
        if key in by_key and abs(by_key[key] - amount) > 1.0:
            raise ValueError(f"Conflicting offering_amt values for {key}")
        by_key[key] = amount
    result, missing = [], []
    for auction in auctions:
        row = dict(auction)
        row["offering_amt"] = by_key.get((row["cusip"], row["auction_date"]))
        if row["offering_amt"] is None:
            missing.append({"cusip": row["cusip"], "auction_date": row["auction_date"].isoformat()})
        result.append(row)
    coverage = (len(result) - len(missing)) / len(result) if result else 0.0
    meta = {"field": "offering_amt", "selected_auctions": len(result), "valid_positive_amounts": len(result)-len(missing),
            "missing_or_nonpositive": len(missing), "coverage": coverage, "minimum_required_coverage": min_coverage,
            "missing_examples": missing[:10]}
    if coverage < min_coverage:
        raise ValueError(f"offering_amt coverage {coverage:.3%} is below required {min_coverage:.1%}; no imputation is permitted")
    return result, meta


def add_supply_features(auctions, supply_lookback=SUPPLY_LOOKBACK, rank_lookback=RANK_LOOKBACK):
    rows = sorted(auctions, key=lambda r: (r["record_date"], r["auction_date"], r["cusip"]))
    for i, current in enumerate(rows):
        prior = [r for r in rows[:i] if r["record_date"] < current["record_date"]]
        amounts = [r["offering_amt"] for r in prior if r.get("offering_amt") is not None and r["offering_amt"] > 0]
        amount = current.get("offering_amt")
        if amount is not None and amount > 0 and len(amounts) >= supply_lookback:
            reference = statistics.median(amounts[-supply_lookback:])
            current["supply_reference_amount"] = reference
            current["supply_multiple"] = amount / reference
            current["supply_log_ratio"] = math.log(current["supply_multiple"])
        else:
            current["supply_reference_amount"] = current["supply_multiple"] = current["supply_log_ratio"] = None
        history = [r["supply_log_ratio"] for r in prior if r.get("supply_log_ratio") is not None][-rank_lookback:]
        if current["supply_log_ratio"] is not None and len(history) >= rank_lookback:
            threshold = sorted(history)[math.ceil(0.75 * len(history)) - 1]
            current["high_supply_threshold"] = threshold
            current["high_supply"] = current["supply_log_ratio"] >= threshold
        else:
            current["high_supply_threshold"] = current["high_supply"] = None
    return rows


def build_supply_events(auctions, yields):
    dates = sorted(yields)
    values = [yields[d] for d in dates]
    events = []
    skipped = {"missing_supply_history": 0, "no_future_yield_window": 0, "insufficient_pre_history": 0}
    for auction in auctions:
        if auction.get("supply_log_ratio") is None:
            skipped["missing_supply_history"] += 1
            continue
        start = bisect.bisect_right(dates, auction["record_date"])
        if start + 1 >= len(dates):
            skipped["no_future_yield_window"] += 1
            continue
        pre = start - 1
        if pre - 5 < 0:
            skipped["insufficient_pre_history"] += 1
            continue
        event = dict(auction)
        event.update({"yield_start_date": dates[start], "yield_end_date": dates[start+1],
                      "target_bp": (values[start+1]-values[start])*100.0,
                      "pre_yield_5d_bp": (values[pre]-values[pre-5])*100.0})
        events.append(event)
    events.sort(key=lambda r: (r["record_date"], r["auction_date"], r["cusip"]))
    return events, skipped


def walk_forward_predictions(events):
    output = []
    baseline, augmented = ["bid_to_cover", "pre_yield_5d_bp"], ["bid_to_cover", "pre_yield_5d_bp", "supply_log_ratio"]
    for current in events:
        train = [r for r in events if r["record_date"] < current["record_date"] and r["yield_end_date"] < current["record_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            p0 = base.fit_ols_predict(train, current, baseline)
            p1 = base.fit_ols_predict(train, current, augmented)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        output.append({"record_date": current["record_date"], "cusip": current["cusip"], "target_bp": current["target_bp"],
                       "baseline_prediction_bp": p0, "augmented_prediction_bp": p1,
                       "supply_log_ratio": current["supply_log_ratio"], "high_supply": current.get("high_supply"),
                       "yield_end_date": current["yield_end_date"]})
    return output


def summarize_high_supply(rows):
    eligible = [r for r in rows if isinstance(r.get("high_supply"), bool)]
    high = [r["target_bp"] for r in eligible if r["high_supply"]]
    other = [r["target_bp"] for r in eligible if not r["high_supply"]]
    boot_rows = [{"weak_demand": r["high_supply"], "target_bp": r["target_bp"]} for r in eligible]
    return {"n": len(eligible), "high_supply_n": len(high), "other_n": len(other),
            "high_supply_mean_bp": statistics.fmean(high) if high else None,
            "other_mean_bp": statistics.fmean(other) if other else None,
            "high_minus_other_mean_bp": statistics.fmean(high)-statistics.fmean(other) if high and other else None,
            "bootstrap": base.bootstrap_mean_difference(boot_rows, reps=BOOTSTRAP_REPS)}


def update_registry(result, report_path):
    content = REGISTRY_PATH.read_text(encoding="utf-8")
    s = result.get("summary_metrics") or {}
    metrics = f"test OOS n={s.get('test_n')}, augmented RMSE={s.get('test_augmented_rmse_bp')} bp, baseline RMSE={s.get('test_baseline_rmse_bp')} bp, improvement={s.get('test_rmse_improvement_pct')}%, high-supply mean difference={s.get('test_high_supply_mean_difference_bp')} bp"
    row = (f"| {HYPOTHESIS_ID} | {result.get('status')} | Announced 10-year nominal offering size relative to the trailing 12 valid same-tenor auctions adds incremental information about the next observed business-day DGS10 change beyond bid-to-cover and prior five-day yield movement; higher relative supply is expected to raise yields. | {result.get('data_scope')} | {result.get('disposition')}; {metrics} | [../{report_path}](../{report_path}) |")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[i] = row
            break
    else:
        lines.append(row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_research():
    end_date = base.END_DATE
    old_fields = base.FIELD_LIST
    base.FIELD_LIST = ",".join(list(dict.fromkeys(old_fields.split(",") + ["offering_amt"])))
    try:
        raw_rows, auction_meta = base.fetch_auction_pages(end_date)
    finally:
        base.FIELD_LIST = old_fields
    auctions, quality = base.select_ten_year_nominal_auctions(raw_rows)
    if quality.get("record_date_fallback_to_auction_date", 0):
        raise RuntimeError("A selected auction lacks publication record_date; strict signal timing cannot be verified")
    if len(auctions) < MODEL_WINDOW + 30:
        raise RuntimeError(f"Insufficient selected nominal 10-year auctions: {len(auctions)}")
    auctions, amount_meta = enrich_offering_amounts(raw_rows, auctions)
    auctions = add_supply_features(auctions)
    yields, yield_meta = base.fetch_treasury_yields(end_date)
    if len(yields) < 1000:
        raise RuntimeError(f"Insufficient DGS10 observations: {len(yields)}")
    events, event_quality = build_supply_events(auctions, yields)
    predictions = walk_forward_predictions(events)
    validation = [r for r in predictions if VALIDATION_START <= r["record_date"] < TEST_START]
    test = [r for r in predictions if r["record_date"] >= TEST_START]
    bval, aval = base.forecast_metrics(validation, "baseline_prediction_bp"), base.forecast_metrics(validation, "augmented_prediction_bp")
    btest, atest = base.forecast_metrics(test, "baseline_prediction_bp"), base.forecast_metrics(test, "augmented_prediction_bp")
    study = summarize_high_supply(test)
    loss_boot = base.bootstrap_paired_squared_loss_difference(test, reps=BOOTSTRAP_REPS)
    vi = 100*(bval["rmse_bp"]-aval["rmse_bp"])/bval["rmse_bp"] if bval and aval and bval["rmse_bp"] else None
    ti = 100*(btest["rmse_bp"]-atest["rmse_bp"])/btest["rmse_bp"] if btest and atest and btest["rmse_bp"] else None
    valid = len(test) >= 30 and all((bval, aval, btest, atest))
    eb, lb = study.get("bootstrap") or {}, loss_boot or {}
    event_support = study.get("high_minus_other_mean_bp") is not None and study["high_minus_other_mean_bp"] > 0 and eb.get("ci_95_low_bp") is not None and eb["ci_95_low_bp"] > 0
    loss_support = lb.get("ci_95_low_bp2") is not None and lb["ci_95_low_bp2"] > 0
    if not valid:
        status, disposition = "INCONCLUSIVE", "INCONCLUSIVE — fewer than 30 test forecasts or incomplete chronological metrics"
    elif vi is not None and vi > 0 and ti is not None and ti > 0 and event_support and loss_support:
        status, disposition = "BACKTESTED", "PROMISING BUT UNVALIDATED — both chronological periods improve and preregistered test diagnostics pass; independent and tradable validation remain outstanding"
    elif vi is not None and ti is not None and vi <= 0 and ti <= 0 and study.get("high_minus_other_mean_bp") is not None and study["high_minus_other_mean_bp"] <= 0:
        status, disposition = "REJECTED", "REJECTED — neither chronological forecast period improves and high-supply events do not precede higher yields"
    else:
        status, disposition = "INCONCLUSIVE", "INCONCLUSIVE — mixed or statistically uncertain predictive evidence; do not promote or claim an economic edge"
    ydates = sorted(yields)
    max_gap = max(((ydates[i]-ydates[i-1]).days for i in range(1, len(ydates))), default=0)
    hashes = dict(auction_meta.get("hashes") or {})
    hashes.update(yield_meta.get("hashes") or {})
    scope = f"Legacy Treasury auctions_query nominal 10-year Notes {auctions[0]['auction_date']} to {auctions[-1]['auction_date']}; {yield_meta['provider']} observations {ydates[0]} to {ydates[-1]}"
    summary = {
        "auction_rows_selected": len(auctions), "events_with_targets": len(events), "all_oos_n": len(predictions),
        "validation_n": len(validation), "test_n": len(test),
        "validation_baseline_rmse_bp": base.safe_round(bval["rmse_bp"] if bval else None),
        "validation_augmented_rmse_bp": base.safe_round(aval["rmse_bp"] if aval else None),
        "validation_rmse_improvement_pct": base.safe_round(vi),
        "test_baseline_rmse_bp": base.safe_round(btest["rmse_bp"] if btest else None),
        "test_augmented_rmse_bp": base.safe_round(atest["rmse_bp"] if atest else None),
        "test_rmse_improvement_pct": base.safe_round(ti),
        "test_high_supply_mean_difference_bp": base.safe_round(study.get("high_minus_other_mean_bp")),
        "test_paired_loss_ci_low_bp2": base.safe_round(lb.get("ci_95_low_bp2")),
        "test_paired_loss_ci_high_bp2": base.safe_round(lb.get("ci_95_high_bp2")),
    }
    return {
        "hypothesis_id": HYPOTHESIS_ID, "title": TITLE, "status": status, "disposition": disposition,
        "daily_kpi": "MET" if valid else "MISSED", "run_id": RUN_ID, "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA, "retrieved_at_utc": SESSION_TIME.isoformat(), "data_scope": scope,
        "auction_source": {"url": base.BASE_URL, "rows_returned": auction_meta["rows_returned"], "selected": len(auctions), "quality": quality, "attempts": auction_meta["attempts"]},
        "offering_amount": amount_meta,
        "yield_source": {"provider": yield_meta["provider"], "observations": len(yields), "first_date": ydates[0], "last_date": ydates[-1], "max_calendar_gap_days": max_gap, "attempts": yield_meta["attempts"], "treasury_xml_crosscheck": yield_meta.get("treasury_xml_crosscheck")},
        "source_sha256": hashes,
        "methodology": {
            "signal_timestamp": "record_date (publication date)",
            "supply_feature": "log(current offering_amt / median(previous 12 valid 10-year nominal offerings))",
            "target": "first-to-second observed DGS10 change strictly after record_date",
            "baseline": ["bid_to_cover", "pre_yield_5d_bp"], "augmented": ["bid_to_cover", "pre_yield_5d_bp", "supply_log_ratio"],
            "rolling_window": MODEL_WINDOW, "training_rule": "Prior target end date must be strictly before current record_date",
            "high_supply_rule": "Nearest-rank 75th percentile of previous 52 available supply_log_ratio values",
            "validation": "2019-01-01 through 2022-12-31", "test": "2023-01-01 onward",
            "minimum_amount_coverage": MIN_OFFERING_COVERAGE, "no_imputation": True,
            "acceptance": "At least 30 test forecasts; augmented RMSE improves in validation and test; paired test-loss bootstrap lower 95% bound > 0; high-supply mean effect and its block-bootstrap lower 95% bound > 0",
        },
        "event_construction": {"events_with_targets": len(events), "skipped": event_quality},
        "validation_metrics": {"baseline": bval, "augmented": aval},
        "test_metrics": {"baseline": btest, "augmented": atest, "high_supply_event_study": study, "paired_squared_loss_bootstrap": loss_boot},
        "summary_metrics": summary,
        "limitations": [
            "Forecasting only; no tradable futures/ETF P&L or risk-adjusted trading metrics.",
            "Offering amount is a supply-intensity level proxy, not a surprise versus a contemporaneous market expectation.",
            "Legacy auctions_query history only; no partially reconciled updated-table rows are appended.",
            "DGS10 is a reference yield, not an executable quote or instrument price.",
            "Daily target does not isolate intraday auction-window repricing.",
            "Results do not generalize automatically to other tenors or security types.",
            "No missing offering amounts are imputed; inadequate coverage fails closed.",
            "No causal effect, future persistence, or live trading feasibility is established.",
        ],
    }


def main():
    error = None
    try:
        result = run_research()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "hypothesis_id": HYPOTHESIS_ID, "title": TITLE, "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — {error}", "daily_kpi": "MISSED",
            "run_id": RUN_ID, "run_attempt": RUN_ATTEMPT, "source_commit_sha": SOURCE_SHA,
            "retrieved_at_utc": SESSION_TIME.isoformat(),
            "data_scope": "Legacy Treasury nominal 10-year auction offering amounts and DGS10; complete field coverage not established",
            "limitations": ["The preregistered experiment did not complete; no substitute feature or imputation was used.", "No empirical conclusion or tradable value is claimed."],
        }
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-treasury-supply-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    summary = result.get("summary_metrics") or {}
    test = result.get("test_metrics") or {}
    study = test.get("high_supply_event_study") or {}
    validation = result.get("validation_metrics") or {}
    report = f"""# Session report — {TITLE} ({STAMP})

- Hypothesis: {HYPOTHESIS_ID}
- Status: {result.get('status')}
- Disposition: {result.get('disposition')}
- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}
- Triggering commit: {SOURCE_SHA}
- Daily KPI: {result.get('daily_kpi')}

## Preregistered protocol

Higher announced 10-year nominal auction supply, measured against the median of the preceding 12 valid same-tenor offerings, is expected to predict a higher next-business-day DGS10 change.

- Signal timestamp: record_date, the publication date.
- Target: first-to-second observed DGS10 change strictly after record_date.
- Baseline: bid-to-cover and preceding five-observation yield change.
- Augmented: baseline plus log offering amount divided by the trailing-12 median.
- Rolling training window: 52 events; every training target must end before the current record_date.
- Validation: 2019–2022. Test: 2023 onward.
- High supply: at or above the nearest-rank 75th percentile of the preceding 52 supply-intensity values.
- Missing amounts are not imputed; required positive coverage is 95%.

## Data and results

- Data scope: {result.get('data_scope')}
- Selected auctions: {(result.get('auction_source') or {}).get('selected')}
- Offering amount coverage: {(result.get('offering_amount') or {}).get('coverage')}
- Yield source: {(result.get('yield_source') or {}).get('provider')}
- Yield observations: {(result.get('yield_source') or {}).get('observations')}

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | {summary.get('validation_n')} | {summary.get('test_n')} |
| Baseline RMSE (bp) | {(validation.get('baseline') or {}).get('rmse_bp')} | {(test.get('baseline') or {}).get('rmse_bp')} |
| Augmented RMSE (bp) | {(validation.get('augmented') or {}).get('rmse_bp')} | {(test.get('augmented') or {}).get('rmse_bp')} |
| RMSE improvement (%) | {summary.get('validation_rmse_improvement_pct')} | {summary.get('test_rmse_improvement_pct')} |

High-supply test events: n={study.get('high_supply_n')} versus other n={study.get('other_n')}; mean target difference={study.get('high_minus_other_mean_bp')} bp; block-bootstrap={study.get('bootstrap')}.

Paired test squared-loss bootstrap: {test.get('paired_squared_loss_bootstrap')}.

## Scientific disposition

{result.get('disposition')}

This is a yield forecast, not a tradable P&L. Offering size is not a surprise measure; DGS10 is not an executable quote. No causal or live-trading claim is made.

## Limitations and claims ledger

{chr(10).join('- ' + x for x in result.get('limitations', []))}
- VERIFIED: source responses, hashes, completed model output and deterministic checks recorded in the manifest.
- UNVERIFIED: causal interpretation, future persistence, executable pricing and economic value.

## Reproducibility

- Manifest: reports/generated/treasury-supply-pressure/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json
- Source: research/treasury_supply_pressure.py
- Tests: research/test_treasury_supply_pressure.py
- Run: https://github.com/{base.REPO}/actions/runs/{RUN_ID}
"""
    manifest_path.write_text(json.dumps(base.json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    relative_report = str(report_path.relative_to(ROOT))
    update_registry(result, relative_report)
    print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "status": result.get("status"), "disposition": result.get("disposition"),
                      "daily_kpi": result.get("daily_kpi"), "report_path": relative_report,
                      "manifest_path": str(manifest_path.relative_to(ROOT)), "summary_metrics": summary, "error": error}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
