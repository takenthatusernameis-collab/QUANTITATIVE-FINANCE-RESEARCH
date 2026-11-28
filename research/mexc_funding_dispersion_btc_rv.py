#!/usr/bin/env python3
"""Frozen walk-forward forecast: MEXC intraday funding dispersion -> BTC perpetual realized variance."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import statistics

import numpy as np
import treasury_auction_demand as base
import mexc_funding_dispersion_source_preflight as preflight

HYPOTHESIS_ID = "QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01"
PRELIGHT_MANIFEST = Path(__file__).resolve().parents[1] / "reports/generated/mexc-funding-dispersion-source-preflight/46085255885-attempt-1/preflight.json"
EXPECTED_PREFLIGHT_SOURCE_SHA = "aa76af09051a7b5b7482eafa3a0b86896a378569"
VALIDATION_START = dt.date(2025, 11, 1)
TEST_START = dt.date(2026, 1, 1)
TRAIN_WINDOW = 120
BOOTSTRAP_REPS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED = 2000, 7, 20261127
IMPLEMENTATION_DEADLINE = dt.datetime(2026, 12, 1, 23, 39, 43, tzinfo=dt.timezone.utc)
FINAL_DEADLINE = dt.datetime(2026, 12, 2, 23, 39, 43, tzinfo=dt.timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "mexc-funding-dispersion-btc-rv" / f"{RUN_ID}-attempt-{ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
README_PATH = ROOT / "README.md"

BASE_FEATURES = ("pre_rv24_log", "pre_rv168_log", "abs_return24_bps", "funding_mean_bps")
AUG_FEATURES = BASE_FEATURES + ("funding_dispersion_bps",)
SECONDS_PER_HOUR = 3600


class SourceMismatchError(RuntimeError):
    pass


def log_returns(closes: dict[int, float], start_ts: int, periods: int) -> list[float]:
    result = []
    for i in range(periods):
        timestamp = start_ts + i * SECONDS_PER_HOUR
        previous = closes.get(timestamp - SECONDS_PER_HOUR)
        current = closes.get(timestamp)
        if previous is None or current is None or previous <= 0 or current <= 0:
            raise ValueError(f"missing/non-positive close for hourly return at {timestamp}")
        result.append(math.log(current / previous))
    return result


def rv_bps2(returns: list[float]) -> float:
    return sum((value * 10_000.0) ** 2 for value in returns)


def build_events(funding_rows: list[dict], closes: dict[int, float]) -> list[dict]:
    grouped: dict[dt.date, dict[int, float]] = {}
    for row in funding_rows:
        grouped.setdefault(row["date"], {})
        if row["hour"] in grouped[row["date"]]:
            raise ValueError(f"duplicate funding settlement on {row['date']} hour {row['hour']}")
        grouped[row["date"]][row["hour"]] = row["rate"]

    events = []
    for date in sorted(grouped):
        rates = grouped[date]
        if set(rates) != {0, 8, 16}:
            continue
        signal_ts = int(dt.datetime.combine(date, dt.time(17), tzinfo=dt.timezone.utc).timestamp())
        prior24 = log_returns(closes, signal_ts - 24 * SECONDS_PER_HOUR, 24)
        prior168 = log_returns(closes, signal_ts - 168 * SECONDS_PER_HOUR, 168)
        future24 = log_returns(closes, signal_ts, 24)
        mean_funding_bps = statistics.mean(rates[h] for h in (0, 8, 16)) * 10_000.0
        dispersion_bps = statistics.pstdev([rates[h] for h in (0, 8, 16)]) * 10_000.0
        events.append({
            "date": date,
            "signal_ts": signal_ts,
            "target_end_ts": signal_ts + 24 * SECONDS_PER_HOUR,
            "pre_rv24_log": math.log1p(rv_bps2(prior24)),
            "pre_rv168_log": math.log1p(rv_bps2(prior168)),
            "abs_return24_bps": abs(sum(prior24)) * 10_000.0,
            "funding_mean_bps": mean_funding_bps,
            "funding_dispersion_bps": dispersion_bps,
            "target": math.log1p(rv_bps2(future24)),
        })
    return events


def training_sample(events: list[dict], signal_ts: int, window: int = TRAIN_WINDOW) -> list[dict]:
    matured = [row for row in events if row["target_end_ts"] < signal_ts]
    return matured[-window:]


def predict_one(train: list[dict], test: dict, feature_names: tuple[str, ...]) -> float:
    if len(train) != TRAIN_WINDOW:
        raise ValueError(f"expected exactly {TRAIN_WINDOW} matured training events, received {len(train)}")
    train_rows = [
        {**{name: row[name] for name in feature_names}, "target_bp": row["target"]}
        for row in train
    ]
    test_row = {**{name: test[name] for name in feature_names}, "target_bp": test["target"]}
    prediction = base.fit_ols_predict(train_rows, test_row, list(feature_names))
    if not math.isfinite(float(prediction)):
        raise ValueError("non-finite forecast")
    return float(prediction)

def rolling_forecasts(events: list[dict]) -> list[dict]:
    forecasts = []
    for event in events:
        if event["date"] < VALIDATION_START:
            continue
        train = training_sample(events, event["signal_ts"])
        if len(train) != TRAIN_WINDOW:
            continue
        baseline = predict_one(train, event, BASE_FEATURES)
        augmented = predict_one(train, event, AUG_FEATURES)
        split = "validation" if event["date"] < TEST_START else "test"
        forecasts.append({
            "date": event["date"].isoformat(),
            "signal_ts": event["signal_ts"],
            "target_end_ts": event["target_end_ts"],
            "split": split,
            "train_n": len(train),
            "target": event["target"],
            "baseline_prediction": baseline,
            "augmented_prediction": augmented,
            "baseline_squared_error": (event["target"] - baseline) ** 2,
            "augmented_squared_error": (event["target"] - augmented) ** 2,
            "pre_rv24_log": event["pre_rv24_log"],
            "pre_rv168_log": event["pre_rv168_log"],
            "abs_return24_bps": event["abs_return24_bps"],
            "funding_mean_bps": event["funding_mean_bps"],
            "funding_dispersion_bps": event["funding_dispersion_bps"],
        })
    return forecasts


def metrics(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("no forecasts for requested split")
    baseline_errors = np.asarray([r["target"] - r["baseline_prediction"] for r in rows], dtype=float)
    augmented_errors = np.asarray([r["target"] - r["augmented_prediction"] for r in rows], dtype=float)
    return {
        "n": int(len(rows)),
        "baseline_rmse": float(np.sqrt(np.mean(baseline_errors ** 2))),
        "augmented_rmse": float(np.sqrt(np.mean(augmented_errors ** 2))),
        "baseline_mae": float(np.mean(np.abs(baseline_errors))),
        "augmented_mae": float(np.mean(np.abs(augmented_errors))),
        "rmse_improvement_fraction": float(
            (np.sqrt(np.mean(baseline_errors ** 2)) - np.sqrt(np.mean(augmented_errors ** 2)))
            / np.sqrt(np.mean(baseline_errors ** 2))
        ),
    }


def paired_loss_block_bootstrap(rows: list[dict], reps: int = BOOTSTRAP_REPS,
                                block_size: int = BOOTSTRAP_BLOCK, seed: int = BOOTSTRAP_SEED) -> dict:
    differences = np.asarray([
        r["baseline_squared_error"] - r["augmented_squared_error"] for r in rows
    ], dtype=float)
    n = len(differences)
    if n < block_size:
        raise ValueError("paired test sample is shorter than the preregistered bootstrap block")
    rng = np.random.default_rng(seed)
    means = np.empty(reps, dtype=float)
    for rep in range(reps):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, n))
            indices.extend((start + offset) % n for offset in range(block_size))
        means[rep] = float(np.mean(differences[np.asarray(indices[:n], dtype=int)]))
    lower, upper = np.quantile(means, [0.025, 0.975])
    return {
        "reps": reps, "block_size_daily_events": block_size, "seed": seed,
        "mean_baseline_minus_augmented_squared_loss": float(np.mean(differences)),
        "ci95_lower": float(lower), "ci95_upper": float(upper),
    }


def disposition(validation: dict, test: dict, interval: dict) -> str:
    if (
        validation["augmented_rmse"] < validation["baseline_rmse"]
        and test["augmented_rmse"] < test["baseline_rmse"]
        and interval["ci95_lower"] > 0
    ):
        return "PROMISING"
    if (
        validation["augmented_rmse"] > validation["baseline_rmse"]
        and test["augmented_rmse"] > test["baseline_rmse"]
        and interval["ci95_upper"] < 0
    ):
        return "REJECTED"
    return "INCONCLUSIVE"


def verify_frozen_sources() -> tuple[list[dict], dict[int, float], dict]:
    if not PRELIGHT_MANIFEST.is_file():
        raise SourceMismatchError(f"frozen source-preflight manifest missing: {PRELIGHT_MANIFEST}")
    frozen = json.loads(PRELIGHT_MANIFEST.read_text(encoding="utf-8"))
    if frozen.get("status") != "PASS" or frozen.get("hypothesis_id") != HYPOTHESIS_ID:
        raise SourceMismatchError("frozen source-preflight manifest is not a PASS for this hypothesis")
    if frozen.get("source_commit_sha") != EXPECTED_PREFLIGHT_SOURCE_SHA:
        raise SourceMismatchError("source-preflight manifest commit does not match the preregistered accepted run")
    funding, funding_pages, funding_host, funding_attempts = preflight.fetch_funding()
    closes, raw_closes, kline_segments, kline_host, kline_attempts = preflight.fetch_klines()
    funding_hash = preflight.canonical_hash(funding, ("symbol", "settle_ms", "rate_raw", "cycle"))
    kline_serial = [{"time": t, "close": raw_closes[t]} for t in sorted(raw_closes)]
    kline_hash = hashlib.sha256(
        json.dumps(kline_serial, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    provenance = frozen["provenance"]
    if funding_hash != provenance["funding"]["canonical_sha256"]:
        raise SourceMismatchError("current MEXC funding rows differ from the accepted canonical source hash")
    if kline_hash != provenance["hourly_klines"]["canonical_sha256"]:
        raise SourceMismatchError("current MEXC hourly closes differ from the accepted canonical source hash")
    if funding_host != provenance["funding"]["host"] or kline_host != provenance["hourly_klines"]["host"]:
        raise SourceMismatchError("MEXC API host differs from the accepted source-preflight host")
    if funding_attempts or kline_attempts:
        raise SourceMismatchError("MEXC compatibility fallback was used after source acceptance")
    return funding, closes, {
        "preflight_manifest": str(PRELIGHT_MANIFEST.relative_to(ROOT)),
        "preflight_run_id": frozen.get("run_id"),
        "preflight_source_commit_sha": frozen.get("source_commit_sha"),
        "funding_canonical_sha256": funding_hash,
        "kline_canonical_sha256": kline_hash,
        "funding_host": funding_host,
        "kline_host": kline_host,
        "funding_pages_refetched": len(funding_pages),
        "kline_segments_refetched": len(kline_segments),
        "funding_coverage": frozen.get("funding_coverage"),
        "kline_coverage": frozen.get("kline_coverage"),
        "event_coverage": frozen.get("event_coverage"),
    }


def write_csv(path: Path, forecasts: list[dict]) -> None:
    fields = [
        "date", "signal_ts", "target_end_ts", "split", "train_n", "target",
        "baseline_prediction", "augmented_prediction", "baseline_squared_error",
        "augmented_squared_error", "pre_rv24_log", "pre_rv168_log",
        "abs_return24_bps", "funding_mean_bps", "funding_dispersion_bps",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(forecasts)


def update_registry_and_readme(decision: str, manifest_path: str, report_path: str, forecast_path: str,
                               validation: dict, test: dict) -> None:
    status = "REJECTED" if decision == "REJECTED" else "BACKTESTED" if decision == "PROMISING" else "INCONCLUSIVE"
    evidence = f"[report]({report_path}); [manifest]({manifest_path}); [forecast rows]({forecast_path})"
    scope = "MEXC BTC_USDT perpetual; 530 complete funding days; 12,929 hourly bars; frozen 2025-06-15–2026-11-26 sample"
    disposition_text = (
        f"{decision}; validation RMSE baseline/augmented={validation['baseline_rmse']:.6f}/{validation['augmented_rmse']:.6f}; "
        f"test RMSE baseline/augmented={test['baseline_rmse']:.6f}/{test['augmented_rmse']:.6f}"
    )
    lines = REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[i] = f"| {HYPOTHESIS_ID} | {status} | Within-day dispersion of three MEXC BTC_USDT 8-hour funding settlements may add information about next-24-hour same-contract realized variance beyond recent realized variance and mean funding. | {scope} | {disposition_text} | {evidence} |"
            replaced = True
            break
    if not replaced:
        raise ValueError("hypothesis registry row not found")
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme_lines = README_PATH.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(readme_lines):
        if line.startswith("Hypothesis ") and HYPOTHESIS_ID in line:
            readme_lines[index] = (
                f"Hypothesis {HYPOTHESIS_ID}: MEXC source feasibility PASSED; "
                f"the frozen walk-forward backtest disposition is {decision}. "
                f"See [session report]({report_path}) and [forecast rows]({forecast_path})."
            )
            break
    readme = "\n".join(readme_lines) + "\n"
    README_PATH.write_text(readme, encoding="utf-8")

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    forecast_path = OUTPUT_DIR / "forecast_rows.csv"
    report_path = SESSION_DIR / f"{STAMP}_session-mexc-funding-dispersion-btc-rv-{RUN_ID}.md"
    forecasts: list[dict] = []
    manifest = {
        "hypothesis_id": HYPOTHESIS_ID, "status": "ERROR", "decision": None,
        "completed_backtest": False, "model_fit_performed": False,
        "retrieved_at_utc": NOW.isoformat(), "run_id": RUN_ID,
        "run_attempt": ATTEMPT, "source_commit_sha": SOURCE_SHA,
        "timebox": {
            "cycle": 3, "maximum_substantive_cycles": 4,
            "implementation_deadline_utc": IMPLEMENTATION_DEADLINE.isoformat(),
            "final_conclusion_deadline_utc": FINAL_DEADLINE.isoformat(),
        },
    }
    try:
        if NOW > IMPLEMENTATION_DEADLINE or NOW > FINAL_DEADLINE:
            raise SourceMismatchError("preregistered implementation/final deadline has expired")
        funding, closes, source_info = verify_frozen_sources()
        events = build_events(funding, closes)
        if len(events) < 400:
            raise SourceMismatchError(f"only {len(events)} complete model events remain after deterministic construction")
        forecasts = rolling_forecasts(events)
        validation_rows = [r for r in forecasts if r["split"] == "validation"]
        test_rows = [r for r in forecasts if r["split"] == "test"]
        if len(validation_rows) < 30 or len(test_rows) < 100:
            raise SourceMismatchError(
                f"insufficient forecasts after 120-event warm-up: validation={len(validation_rows)}, test={len(test_rows)}"
            )
        validation_metrics = metrics(validation_rows)
        test_metrics = metrics(test_rows)
        bootstrap = paired_loss_block_bootstrap(test_rows)
        decision = disposition(validation_metrics, test_metrics, bootstrap)
        manifest.update({
            "status": "COMPLETED", "decision": decision,
            "completed_backtest": True, "model_fit_performed": True,
            "source": source_info,
            "event_count": len(events),
            "forecast_count": len(forecasts),
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
            "paired_test_loss_bootstrap": bootstrap,
            "model": {
                "baseline_features": list(BASE_FEATURES),
                "augmented_features": list(AUG_FEATURES),
                "training_window": TRAIN_WINDOW,
                "estimator": "repository standardized OLS helper; fixed ridge stabilization 1e-8",
                "target": "log1p(next_24h_realized_variance_bp2)",
            },
        })
    except SourceMismatchError as exc:
        manifest["status"] = "INCONCLUSIVE/INFEASIBLE"
        manifest["error"] = str(exc)
    except Exception as exc:
        manifest["status"] = "ERROR"
        manifest["error"] = f"{type(exc).__name__}: {exc}"

    write_csv(forecast_path, forecasts)
    manifest["manifest_path"] = str(manifest_path.relative_to(ROOT))
    manifest["forecast_rows_path"] = str(forecast_path.relative_to(ROOT))
    manifest["report_path"] = str(report_path.relative_to(ROOT))
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        f"# MEXC funding dispersion / BTC realized variance — {NOW.isoformat()}",
        "", f"- **Hypothesis:** {HYPOTHESIS_ID}", f"- **Status:** {manifest['status']}",
        f"- **Decision:** {manifest.get('decision') or 'None'}",
        f"- **GitHub run:** {RUN_ID}, attempt {ATTEMPT}", f"- **Source commit:** {SOURCE_SHA}",
        "", "## Source provenance", json.dumps(manifest.get("source", {}), indent=2, sort_keys=True),
        "", "## Validation metrics", json.dumps(manifest.get("validation_metrics", {}), indent=2, sort_keys=True),
        "", "## Test metrics", json.dumps(manifest.get("test_metrics", {}), indent=2, sort_keys=True),
        "", "## Paired test-loss bootstrap", json.dumps(manifest.get("paired_test_loss_bootstrap", {}), indent=2, sort_keys=True),
        "", "## Model", json.dumps(manifest.get("model", {}), indent=2, sort_keys=True),
        "", "## Error", str(manifest.get("error") or "None"),
        "", "Forecast-only study. No strategy P&L, live orders, capital deployment or trading authorization.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if manifest["completed_backtest"]:
        update_registry_and_readme(
            manifest["decision"], str(manifest_path.relative_to(ROOT)),
            str(report_path.relative_to(ROOT)), str(forecast_path.relative_to(ROOT)),
            manifest["validation_metrics"], manifest["test_metrics"],
        )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
