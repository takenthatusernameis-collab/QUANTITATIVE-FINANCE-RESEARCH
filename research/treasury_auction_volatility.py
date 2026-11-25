#!/usr/bin/env python3
"""Walk-forward forecast of Treasury auction demand stress and daily yield variation."""
from __future__ import annotations
import bisect
import datetime as dt
import json
import math
import os
import random
import statistics
from pathlib import Path

HYPOTHESIS_ID = "QFR-2026-11-25-UST-AUCTION-VOLATILITY-01"
MODEL_WINDOW = 52
LOOKBACK = 26
TARGET_CHANGES = 5
VALIDATION_START = dt.date(2019, 1, 1)
TEST_START = dt.date(2023, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
SEED = 2026112501
ROOT = Path(__file__).resolve().parents[1]
STAMP = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "treasury-auction-volatility" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"


def realized_variation_bp(values):
    if len(values) != TARGET_CHANGES + 1:
        raise ValueError("Exactly six yield observations are required")
    changes = [(b - a) * 100.0 for a, b in zip(values, values[1:])]
    if any(not math.isfinite(x) for x in changes):
        raise ValueError("Yield changes must be finite")
    return math.sqrt(sum(x * x for x in changes))


def add_stress_scores(events):
    for i, row in enumerate(events):
        prior = events[max(0, i - LOOKBACK):i]
        if len(prior) < LOOKBACK:
            row["weak_score"] = row["weak_demand"] = None
            continue
        dealer_pct = sum(x["dealer_share"] <= row["dealer_share"] for x in prior) / LOOKBACK
        low_btc_pct = sum(x["bid_to_cover"] >= row["bid_to_cover"] for x in prior) / LOOKBACK
        row["weak_score"] = 0.5 * (dealer_pct + low_btc_pct)
        row["weak_demand"] = row["weak_score"] >= 0.75


def build_events(auctions, yields):
    dates = sorted(yields)
    values = [yields[d] for d in dates]
    events = []
    skipped = {"no_complete_post_window": 0, "insufficient_pre_history": 0, "invalid_window": 0}
    for auction in auctions:
        start = bisect.bisect_right(dates, auction["record_date"])
        pre_end = start - 1
        if start + TARGET_CHANGES >= len(dates):
            skipped["no_complete_post_window"] += 1
            continue
        if pre_end - TARGET_CHANGES < 0:
            skipped["insufficient_pre_history"] += 1
            continue
        try:
            pre = realized_variation_bp(values[pre_end - TARGET_CHANGES:pre_end + 1])
            target = realized_variation_bp(values[start:start + TARGET_CHANGES + 1])
        except ValueError:
            skipped["invalid_window"] += 1
            continue
        event = dict(auction)
        event.update({
            "pre_yield_end_date": dates[pre_end],
            "yield_start_date": dates[start],
            "yield_end_date": dates[start + TARGET_CHANGES],
            "pre_variation_bp": pre,
            "target_variation_bp": target,
            "pre_vol_log": math.log1p(pre),
            "target_bp": math.log1p(target),
        })
        events.append(event)
    events.sort(key=lambda x: (x["record_date"], x["auction_date"], x["cusip"]))
    add_stress_scores(events)
    return events, skipped


def walk_forward(events, fit_predict):
    output = []
    base_features = ["pre_vol_log", "bid_to_cover"]
    augmented_features = ["pre_vol_log", "bid_to_cover", "dealer_share"]
    for current in events:
        train = [x for x in events if x["record_date"] < current["record_date"]
                 and x["yield_end_date"] < current["record_date"]][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            p0 = fit_predict(train, current, base_features)
            p1 = fit_predict(train, current, augmented_features)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        if not (math.isfinite(p0) and math.isfinite(p1)):
            continue
        output.append({
            "record_date": current["record_date"], "cusip": current["cusip"],
            "yield_end_date": current["yield_end_date"], "target_bp": current["target_bp"],
            "target_variation_bp": current["target_variation_bp"],
            "baseline_prediction_bp": p0, "augmented_prediction_bp": p1,
            "weak_score": current.get("weak_score"), "weak_demand": current.get("weak_demand"),
        })
    return output


def metrics(rows, key):
    if not rows:
        return None
    actual = [x["target_bp"] for x in rows]
    pred = [x[key] for x in rows]
    err = [p - a for p, a in zip(pred, actual)]
    actual_bp = [x["target_variation_bp"] for x in rows]
    pred_bp = [max(0.0, math.expm1(p)) for p in pred]
    err_bp = [p - a for p, a in zip(pred_bp, actual_bp)]
    mean = statistics.fmean(actual)
    sse = sum(e * e for e in err)
    denom = sum((x - mean) ** 2 for x in actual)
    return {
        "n": len(rows), "mae_log1p": statistics.fmean(abs(e) for e in err),
        "rmse_log1p": math.sqrt(sse / len(err)),
        "oos_r2_vs_mean_log1p": 1 - sse / denom if denom > 1e-12 else None,
        "mae_variation_bp": statistics.fmean(abs(e) for e in err_bp),
        "rmse_variation_bp": math.sqrt(sum(e * e for e in err_bp) / len(err_bp)),
        "mean_actual_variation_bp": statistics.fmean(actual_bp),
    }


def block_sample(rows, rng):
    out = []
    while len(out) < len(rows):
        start = rng.randrange(len(rows))
        for j in range(BOOTSTRAP_BLOCK):
            out.append(rows[(start + j) % len(rows)])
            if len(out) == len(rows):
                break
    return out


def paired_bootstrap(rows):
    if len(rows) < 30:
        return None
    ordered = sorted(rows, key=lambda x: (x["record_date"], x["cusip"]))
    diffs = [(x["baseline_prediction_bp"] - x["target_bp"]) ** 2
             - (x["augmented_prediction_bp"] - x["target_bp"]) ** 2 for x in ordered]
    data = [{"d": x} for x in diffs]
    rng = random.Random(SEED + 1)
    samples = [statistics.fmean(x["d"] for x in block_sample(data, rng)) for _ in range(BOOTSTRAP_REPS)]
    samples.sort()
    return {"observations": len(diffs), "reps": len(samples), "block_size_events": BOOTSTRAP_BLOCK,
            "mean_baseline_minus_augmented": statistics.fmean(diffs),
            "ci_95_low": samples[int(.025 * (len(samples)-1))],
            "ci_95_high": samples[int(.975 * (len(samples)-1))]}


def stress_bootstrap(rows):
    eligible = [x for x in rows if isinstance(x.get("weak_demand"), bool)]
    high = [x for x in eligible if x["weak_demand"]]
    other = [x for x in eligible if not x["weak_demand"]]
    if len(eligible) < 30 or len(high) < 5 or len(other) < 5:
        return None
    observed = statistics.fmean(x["target_variation_bp"] for x in high) - statistics.fmean(x["target_variation_bp"] for x in other)
    data = [{"weak": x["weak_demand"], "target": x["target_variation_bp"]} for x in sorted(eligible, key=lambda x: (x["record_date"], x["cusip"]))]
    rng = random.Random(SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPS):
        sample = block_sample(data, rng)
        h = [x["target"] for x in sample if x["weak"]]
        o = [x["target"] for x in sample if not x["weak"]]
        if h and o:
            samples.append(statistics.fmean(h) - statistics.fmean(o))
    samples.sort()
    return {"high_n": len(high), "other_n": len(other), "difference_bp": observed,
            "reps": len(samples), "block_size_events": BOOTSTRAP_BLOCK,
            "ci_95_low_bp": samples[int(.025 * (len(samples)-1))],
            "ci_95_high_bp": samples[int(.975 * (len(samples)-1))]}


def safe_round(x):
    return round(x, 6) if isinstance(x, (int, float)) and math.isfinite(x) else None


def json_safe(x):
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): json_safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [json_safe(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def run_research():
    import treasury_auction_demand as base
    end = base.END_DATE
    raw, auction_meta = base.fetch_auction_pages(end)
    auctions, quality = base.select_ten_year_nominal_auctions(raw)
    legacy_n = len(auctions)
    probe = base.fetch_updated_auction_probe(end, legacy_auctions=auctions)
    auctions, hybrid = base.merge_updated_auction_samples(auctions, probe)
    yields, yield_meta = base.fetch_treasury_yields(end)
    if len(auctions) < MODEL_WINDOW + 30 or len(yields) < 1000:
        raise RuntimeError(f"Insufficient coverage: {len(auctions)} auctions, {len(yields)} yield observations")
    events, skipped = build_events(auctions, yields)
    predictions = walk_forward(events, base.fit_ols_predict)
    validation = [x for x in predictions if VALIDATION_START <= x["record_date"] < TEST_START]
    test = [x for x in predictions if x["record_date"] >= TEST_START]
    bval, aval = metrics(validation, "baseline_prediction_bp"), metrics(validation, "augmented_prediction_bp")
    btest, atest = metrics(test, "baseline_prediction_bp"), metrics(test, "augmented_prediction_bp")
    paired, stress = paired_bootstrap(test), stress_bootstrap(test)
    vi = 100 * (bval["rmse_log1p"] - aval["rmse_log1p"]) / bval["rmse_log1p"] if bval and aval and bval["rmse_log1p"] else None
    ti = 100 * (btest["rmse_log1p"] - atest["rmse_log1p"]) / btest["rmse_log1p"] if btest and atest and btest["rmse_log1p"] else None
    valid = len(test) >= 30 and all((bval, aval, btest, atest))
    effect = stress.get("difference_bp") if stress else None
    if not valid:
        status, disposition = "INCONCLUSIVE", "INCONCLUSIVE — fewer than 30 test forecasts or incomplete metrics"
    elif vi > 0 and ti > 0 and paired and paired["ci_95_low"] > 0 and stress and effect > 0 and stress["ci_95_low_bp"] > 0:
        status, disposition = "BACKTESTED", "PROMISING BUT UNVALIDATED — demand stress improves both chronological volatility forecasts and preregistered uncertainty checks pass"
    elif vi <= 0 and ti <= 0 and effect is not None and effect <= 0:
        status, disposition = "REJECTED", "REJECTED — bidder absorption does not improve either period and high-stress events do not show greater subsequent yield variation"
    else:
        status, disposition = "INCONCLUSIVE", "INCONCLUSIVE — mixed or statistically uncertain volatility-forecast evidence"
    dates = sorted(yields)
    hashes = dict(auction_meta.get("hashes") or {})
    hashes.update(yield_meta.get("hashes") or {})
    if probe.get("sha256"):
        hashes["updated_auction_probe"] = probe["sha256"]
    summary = {
        "auction_rows": len(auctions), "legacy_rows": legacy_n, "updated_rows_appended": hybrid.get("appended_rows", 0),
        "complete_events": len(events), "oos_forecasts": len(predictions), "validation_n": len(validation), "test_n": len(test),
        "validation_improvement_pct_log1p": safe_round(vi), "test_improvement_pct_log1p": safe_round(ti),
        "test_baseline_rmse_log1p": safe_round(btest["rmse_log1p"] if btest else None),
        "test_augmented_rmse_log1p": safe_round(atest["rmse_log1p"] if atest else None),
        "test_baseline_rmse_variation_bp": safe_round(btest["rmse_variation_bp"] if btest else None),
        "test_augmented_rmse_variation_bp": safe_round(atest["rmse_variation_bp"] if atest else None),
        "test_stress_difference_bp": safe_round(effect),
        "paired_ci_low": safe_round(paired.get("ci_95_low") if paired else None),
        "paired_ci_high": safe_round(paired.get("ci_95_high") if paired else None),
        "stress_ci_low_bp": safe_round(stress.get("ci_95_low_bp") if stress else None),
        "stress_ci_high_bp": safe_round(stress.get("ci_95_high_bp") if stress else None),
    }
    return {
        "hypothesis_id": HYPOTHESIS_ID, "status": status, "disposition": disposition,
        "daily_kpi": "MET" if valid else "MISSED", "run_id": RUN_ID, "run_attempt": ATTEMPT,
        "source_commit_sha": SOURCE_SHA, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "data_scope": f"10-year nominal Treasury Notes {auctions[0]['auction_date']} to {auctions[-1]['auction_date']}; {yield_meta.get('provider')} {dates[0]} to {dates[-1]}",
        "auction_source": {"rows_returned": auction_meta.get("rows_returned"), "quality": quality, "attempts": auction_meta.get("attempts")},
        "updated_auction": {"status": probe.get("status"), "page_complete": probe.get("page_complete"),
            "candidate_population": probe.get("candidate_population"), "legacy_overlap": probe.get("legacy_overlap"), "hybrid_merge": hybrid},
        "yield_source": {"provider": yield_meta.get("provider"), "observations": len(yields), "first_date": dates[0],
            "last_date": dates[-1], "treasury_xml_crosscheck": yield_meta.get("treasury_xml_crosscheck"), "attempts": yield_meta.get("attempts")},
        "source_sha256": hashes,
        "methodology": {"target": "root-sum-square of five consecutive observed daily DGS10 changes strictly after record_date, bp",
            "target_transform": "log1p", "baseline": ["pre_vol_log", "bid_to_cover"],
            "augmented": ["pre_vol_log", "bid_to_cover", "dealer_share"], "rolling_window": MODEL_WINDOW,
            "training_rule": "prior target end date strictly before current record_date",
            "stress": "mean trailing-26-event dealer-share percentile and reverse bid-to-cover percentile; threshold 0.75",
            "validation": "2019–2022", "test": "2023 onward", "bootstrap_reps": BOOTSTRAP_REPS, "block_size": BOOTSTRAP_BLOCK},
        "event_construction": {"complete_events": len(events), "skipped": skipped},
        "summary_metrics": summary, "validation_metrics": {"baseline": bval, "augmented": aval},
        "test_metrics": {"baseline": btest, "augmented": atest, "paired_bootstrap": paired, "stress_event_study": stress},
        "forecasts": predictions,
        "limitations": ["Daily DGS10 is a reference yield, not an executable price.",
            "Five-observation root-sum-square variation cannot identify intraday futures volatility.",
            "Aggregate bidder classes are not individual bids or a structural elasticity estimate.",
            "record_date is a conservative signal-time convention; no intraday publication timestamp is used.",
            "No missing yield observations are filled; no causal or live-trading claim is made."],
    }


def update_registry(result, report_path):
    text = REGISTRY.read_text(encoding="utf-8")
    s = result.get("summary_metrics") or {}
    metrics_text = f"test OOS n={s.get('test_n')}, augmented RMSE(log1p)={s.get('test_augmented_rmse_log1p')}, baseline RMSE(log1p)={s.get('test_baseline_rmse_log1p')}, improvement={s.get('test_improvement_pct_log1p')}%, high-stress variation difference={s.get('test_stress_difference_bp')} bp"
    row = f"| {HYPOTHESIS_ID} | {result.get('status')} | Low bid-to-cover plus high primary-dealer absorption predicts greater next-five-observation daily 10-year yield variation beyond pre-auction variation. | {result.get('data_scope', 'scope unresolved')} | {result.get('disposition')}; {metrics_text} | [../{report_path}](../{report_path}) |"
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[i] = row
            break
    else:
        at = next((i for i, line in enumerate(lines) if line.strip() == "## Disposition rules"), len(lines))
        lines.insert(at, row)
    REGISTRY.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_report(result, error=None):
    s = result.get("summary_metrics") or {}
    v, t = result.get("validation_metrics") or {}, result.get("test_metrics") or {}
    lines = [
        f"# Session report — Treasury auction demand and yield volatility ({STAMP})", "",
        f"- Hypothesis: {HYPOTHESIS_ID}", f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'INCONCLUSIVE')}", f"- Daily real-data backtest KPI: {result.get('daily_kpi', 'MISSED')}",
        f"- GitHub run: {RUN_ID}, attempt {ATTEMPT}", f"- Triggering commit: {SOURCE_SHA}",
        f"- Data scope: {result.get('data_scope', 'not established')}", "",
        "## Preregistered method", "",
        "Target: root-sum-square of five consecutive observed daily DGS10 changes strictly after record_date, transformed with log1p. Baseline: pre-event five-change variation plus bid-to-cover. Augmented: baseline plus primary-dealer accepted share. Rolling 52-event OLS; training targets must end strictly before the forecast record_date. High-stress labels use only the preceding 26 auctions.", "",
        "## Data provenance", "",
        f"- Auction rows returned: {(result.get('auction_source') or {}).get('rows_returned')}",
        f"- Selected nominal 10-year auctions: {(result.get('auction_source') or {}).get('quality', {}).get('selected')}",
        f"- Updated API merge: {(result.get('updated_auction') or {}).get('hybrid_merge', {}).get('status')}; appended={(result.get('updated_auction') or {}).get('hybrid_merge', {}).get('appended_rows')}",
        f"- Yield source: {(result.get('yield_source') or {}).get('provider')}",
        f"- Yield observations: {(result.get('yield_source') or {}).get('observations')}",
        f"- Yield coverage: {(result.get('yield_source') or {}).get('first_date')} to {(result.get('yield_source') or {}).get('last_date')}",
        f"- Treasury XML cross-check: {(result.get('yield_source') or {}).get('treasury_xml_crosscheck', {}).get('status')}", "",
        "## Forecast results", "", "| Metric | Validation 2019–2022 | Test 2023 onward |", "|---|---:|---:|",
        f"| Forecast count | {s.get('validation_n')} | {s.get('test_n')} |",
        f"| Baseline RMSE, log1p | {safe_round((v.get('baseline') or {}).get('rmse_log1p'))} | {safe_round((t.get('baseline') or {}).get('rmse_log1p'))} |",
        f"| Augmented RMSE, log1p | {safe_round((v.get('augmented') or {}).get('rmse_log1p'))} | {safe_round((t.get('augmented') or {}).get('rmse_log1p'))} |",
        f"| RMSE improvement | {s.get('validation_improvement_pct_log1p')}% | {s.get('test_improvement_pct_log1p')}% |",
        f"| Baseline RMSE, variation bp | {safe_round((v.get('baseline') or {}).get('rmse_variation_bp'))} | {safe_round((t.get('baseline') or {}).get('rmse_variation_bp'))} |",
        f"| Augmented RMSE, variation bp | {safe_round((v.get('augmented') or {}).get('rmse_variation_bp'))} | {safe_round((t.get('augmented') or {}).get('rmse_variation_bp'))} |", "",
        "## Test-period uncertainty", "",
        f"- Paired squared-log-loss 95% block interval: [{s.get('paired_ci_low')}, {s.get('paired_ci_high')}]",
        f"- High-stress events: {((t.get('stress_event_study') or {}).get('high_n'))}; other events: {((t.get('stress_event_study') or {}).get('other_n'))}",
        f"- High-stress minus other variation: {s.get('test_stress_difference_bp')} bp",
        f"- Event-study 95% block interval: [{s.get('stress_ci_low_bp')}, {s.get('stress_ci_high_bp')}] bp", "",
        "## Scientific disposition", "", result.get("disposition", "No disposition established."), "",
        "This is a daily reference-yield variation forecast, not a tradable strategy backtest. It does not measure intraday Treasury futures volatility. No causal or live-trading claim is made.", "",
        "## Limitations", "",
        "- No missing yield observations are filled; each window requires six actual observations.",
        "- Aggregate bidder classes are not individual bidder identities or structural demand curves.",
        "- Updated API rows are admitted only through the existing reconciled, overlap-verified adapter.",
        "- DGS10 is not an executable quote; no P&L or risk-adjusted trading claim is permitted.", "",
        "## Reproducibility", "",
        f"- Manifest: reports/generated/treasury-auction-volatility/{RUN_ID}-attempt-{ATTEMPT}/manifest.json",
        "- Source: research/treasury_auction_volatility.py", "- Tests: research/test_treasury_auction_volatility.py",
    ]
    if error:
        lines.extend(["", "## Execution error", "", error])
    return "\n".join(lines) + "\n"


def write_outputs(result, report):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{STAMP}_session-treasury-volatility-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    relative = str(report_path.relative_to(ROOT))
    update_registry(result, relative)
    return relative, str(manifest_path.relative_to(ROOT))


def main():
    try:
        result = run_research()
        report = render_report(result)
        report_path, manifest_path = write_outputs(result, report)
        print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "status": result["status"], "daily_kpi": result["daily_kpi"], "report_path": report_path, "manifest_path": manifest_path, "summary_metrics": result["summary_metrics"]}, indent=2))
    except Exception as exc:
        result = {"hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — {type(exc).__name__}: {exc}", "daily_kpi": "MISSED",
            "run_id": RUN_ID, "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "error": f"{type(exc).__name__}: {exc}"}
        report_path, manifest_path = write_outputs(result, render_report(result, result["error"]))
        print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "status": "INCONCLUSIVE", "daily_kpi": "MISSED", "error": result["error"], "report_path": report_path, "manifest_path": manifest_path}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
