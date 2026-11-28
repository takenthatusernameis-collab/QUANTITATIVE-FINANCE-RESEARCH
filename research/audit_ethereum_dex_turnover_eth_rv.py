#!/usr/bin/env python3
"""Independent, read-only audit of the persisted Ethereum DEX/ETH RV evidence bundle."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HYPOTHESIS_ID = "QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01"
BACKTEST_RUN_ID = "46098199964"
BACKTEST_SOURCE_SHA = "024f91ba2e8ec039bc53d9ccd1b3540c3fb4d350"
PREFLIGHT_RUN_ID = "46097000508"
PREFLIGHT_SOURCE_SHA = "aa59537e1a7938bddd8b4fd0b64bad4c73f271be"
PREFLIGHT_SHA256 = "1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6"
PREFLIGHT_ARTIFACT_ID = 15243896011
PREFLIGHT_ARTIFACT_SHA256 = "5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49"
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 7
BOOTSTRAP_SEED = 20261128

BASE = ROOT / "reports/generated/ethereum-dex-turnover-eth-rv" / f"{BACKTEST_RUN_ID}-attempt-1"
MANIFEST_PATH = BASE / "manifest.json"
FORECASTS_PATH = BASE / "forecast_rows.csv"
PREFLIGHT_PATH = ROOT / "reports/generated/ethereum-dex-turnover-eth-rv-source-preflight" / f"{PREFLIGHT_RUN_ID}-attempt-1/preflight.json"
REPORT_PATH = ROOT / "reports/sessions/2026-11-28/2026-11-28T022812Z_session-ethereum-dex-turnover-eth-rv-46098199964.md"
PREREG_PATH = ROOT / "research/PREREGISTERED-QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01.md"


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def close(actual: float, expected: float, *, rel: float = 1e-11, abs_: float = 1e-12) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_)


def parse_forecasts(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError(f"forecast CSV is not UTF-8: {exc}") from exc
    rows = list(csv.DictReader(text.splitlines()))
    require(bool(rows), "forecast CSV contains no rows")
    return rows


def numeric(row: dict, key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError(f"invalid numeric field {key!r}: {exc}") from exc
    require(math.isfinite(value), f"non-finite numeric field {key!r}")
    return value


def validate_forecasts(rows: list[dict]) -> dict:
    expected_columns = {
        "date", "signal_ts", "target_start_ts", "target_end_ts",
        "feature_start_date", "feature_end_date", "split", "train_n",
        "train_start_date", "train_end_date", "target", "target_rv_bp2",
        "baseline_prediction", "augmented_prediction",
        "baseline_squared_error", "augmented_squared_error",
        "pre_rv24_log", "pre_rv168_log", "abs_return24_bps",
        "dex_volume_7d_usd", "mean_tvl_7d_usd",
        "dex_turnover_7d", "dex_turnover_7d_log",
    }
    require(expected_columns.issubset(rows[0]), "forecast CSV is missing required columns")
    dates = []
    train_lags = []
    previous = None

    for index, row in enumerate(rows):
        try:
            day = dt.date.fromisoformat(row["date"])
            feature_start = dt.date.fromisoformat(row["feature_start_date"])
            feature_end = dt.date.fromisoformat(row["feature_end_date"])
            train_start = dt.date.fromisoformat(row["train_start_date"])
            train_end = dt.date.fromisoformat(row["train_end_date"])
        except (KeyError, ValueError) as exc:
            raise AuditError(f"row {index + 2}: invalid date: {exc}") from exc

        signal = int(numeric(row, "signal_ts"))
        target_start = int(numeric(row, "target_start_ts"))
        target_end = int(numeric(row, "target_end_ts"))
        expected_signal = int(dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
        require(signal == expected_signal, f"{day}: signal is not 00:00 UTC")
        require(target_start == signal, f"{day}: target does not begin at signal")
        require(target_end - target_start == 24 * 3600, f"{day}: target horizon is not exactly 24 hours")
        require(feature_start == day - dt.timedelta(days=8), f"{day}: feature start is not t-8")
        require(feature_end == day - dt.timedelta(days=2), f"{day}: feature end is not t-2")
        require((feature_end - feature_start).days == 6, f"{day}: feature window is not seven inclusive dates")

        train_n = int(numeric(row, "train_n"))
        require(180 <= train_n <= 252, f"{day}: training count outside frozen 180..252 range")
        require(train_start <= train_end < day, f"{day}: invalid training date range")
        # A training target ends at midnight one day after its origin. Strict maturity
        # therefore requires the last training origin to be at least two dates earlier.
        lag = (day - train_end).days
        require(lag >= 2, f"{day}: last training target is not strictly matured")
        train_lags.append(lag)

        target = numeric(row, "target")
        target_rv = numeric(row, "target_rv_bp2")
        baseline_prediction = numeric(row, "baseline_prediction")
        augmented_prediction = numeric(row, "augmented_prediction")
        require(target_rv >= 0, f"{day}: negative realized variance")
        require(close(math.log1p(target_rv), target), f"{day}: target is not log1p(RV)")
        dex_volume = numeric(row, "dex_volume_7d_usd")
        mean_tvl = numeric(row, "mean_tvl_7d_usd")
        turnover = numeric(row, "dex_turnover_7d")
        turnover_log = numeric(row, "dex_turnover_7d_log")
        require(dex_volume >= 0 and mean_tvl > 0, f"{day}: invalid DEX volume or TVL")
        require(close(dex_volume / mean_tvl, turnover), f"{day}: DEX turnover ratio does not reconcile")
        require(close(math.log1p(turnover), turnover_log), f"{day}: log DEX turnover does not reconcile")

        baseline_squared = (target - baseline_prediction) ** 2
        augmented_squared = (target - augmented_prediction) ** 2
        require(close(baseline_squared, numeric(row, "baseline_squared_error"), rel=1e-9, abs_=1e-10),
                f"{day}: stored baseline squared error does not reconcile")
        require(close(augmented_squared, numeric(row, "augmented_squared_error"), rel=1e-9, abs_=1e-10),
                f"{day}: stored augmented squared error does not reconcile")

        split = row["split"]
        expected_split = "validation" if dt.date(2023, 1, 1) <= day <= dt.date(2024, 12, 31) else (
            "test" if dt.date(2025, 1, 1) <= day <= dt.date(2026, 10, 31) else None
        )
        require(split == expected_split, f"{day}: split label does not match frozen date boundaries")
        if previous is not None:
            require(day > previous[0], f"{day}: forecasts are not strictly chronological")
            require(target_start >= previous[2], f"{day}: forecast target overlaps its predecessor")
        previous = (day, signal, target_end)
        dates.append(day)

    require(len(dates) == len(set(dates)), "duplicate forecast dates")
    require(dates[0] == dt.date(2023, 1, 1) and dates[-1] == dt.date(2026, 10, 31),
            "forecast date boundaries differ from the frozen sample")
    validation_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]
    require(len(validation_rows) >= 300 and len(test_rows) >= 300,
            "post-exclusion validation/test minimum of 300 was not met")
    require(all(int(row["train_n"]) == 252 for row in rows),
            "persisted forecast training windows are not consistently capped at 252")
    return {
        "rows": len(rows),
        "unique_dates": len(set(dates)),
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "validation_n": len(validation_rows),
        "test_n": len(test_rows),
        "train_n_min": min(int(row["train_n"]) for row in rows),
        "train_n_max": max(int(row["train_n"]) for row in rows),
        "strict_maturity_lag_days_min": min(train_lags),
        "strict_maturity_lag_days_max": max(train_lags),
        "chronological_and_non_overlapping": True,
        "feature_and_target_timing": True,
        "stored_losses_reconciled": True,
        "turnover_and_target_transforms_reconciled": True,
    }


def forecast_metrics(rows: list[dict]) -> dict:
    baseline = np.asarray([
        numeric(row, "target") - numeric(row, "baseline_prediction") for row in rows
    ], dtype=float)
    augmented = np.asarray([
        numeric(row, "target") - numeric(row, "augmented_prediction") for row in rows
    ], dtype=float)
    baseline_rmse = float(np.sqrt(np.mean(baseline ** 2)))
    augmented_rmse = float(np.sqrt(np.mean(augmented ** 2)))
    baseline_mae = float(np.mean(np.abs(baseline)))
    augmented_mae = float(np.mean(np.abs(augmented)))
    return {
        "n": int(len(rows)),
        "baseline_rmse": baseline_rmse,
        "augmented_rmse": augmented_rmse,
        "baseline_mae": baseline_mae,
        "augmented_mae": augmented_mae,
        "rmse_improvement_pct": (baseline_rmse - augmented_rmse) / baseline_rmse * 100.0,
        "mae_improvement_pct": (baseline_mae - augmented_mae) / baseline_mae * 100.0,
    }


def paired_loss_block_bootstrap(rows: list[dict]) -> dict:
    differences = np.asarray([
        (numeric(row, "target") - numeric(row, "baseline_prediction")) ** 2
        - (numeric(row, "target") - numeric(row, "augmented_prediction")) ** 2
        for row in rows
    ], dtype=float)
    n = len(differences)
    require(n >= BOOTSTRAP_BLOCK, "test sample is too short for the frozen block bootstrap")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = np.empty(BOOTSTRAP_REPS, dtype=float)
    for rep in range(BOOTSTRAP_REPS):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, n))
            indices.extend((start + offset) % n for offset in range(BOOTSTRAP_BLOCK))
        means[rep] = float(np.mean(differences[np.asarray(indices[:n], dtype=int)]))
    lower, upper = np.quantile(means, [0.025, 0.975])
    return {
        "reps": BOOTSTRAP_REPS,
        "block_size_daily_events": BOOTSTRAP_BLOCK,
        "seed": BOOTSTRAP_SEED,
        "observations": n,
        "mean_baseline_minus_augmented_squared_loss": float(np.mean(differences)),
        "ci95_lower": float(lower),
        "ci95_upper": float(upper),
        "bootstrap_fraction_positive": float(np.mean(means > 0)),
    }


def disposition(validation: dict, test: dict, bootstrap: dict) -> str:
    if (validation["augmented_rmse"] < validation["baseline_rmse"]
            and test["augmented_rmse"] < test["baseline_rmse"]
            and bootstrap["ci95_lower"] > 0):
        return "PROMISING"
    if (validation["augmented_rmse"] > validation["baseline_rmse"]
            and test["augmented_rmse"] > test["baseline_rmse"]
            and bootstrap["ci95_upper"] < 0):
        return "REJECTED"
    return "INCONCLUSIVE"


def verify_bundle() -> dict:
    manifest_raw = MANIFEST_PATH.read_bytes()
    preflight_raw = PREFLIGHT_PATH.read_bytes()
    csv_raw = FORECASTS_PATH.read_bytes()
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    prereg_text = PREREG_PATH.read_text(encoding="utf-8")
    manifest = json.loads(manifest_raw)
    preflight = json.loads(preflight_raw)
    rows = parse_forecasts(csv_raw)

    require(manifest["hypothesis_id"] == HYPOTHESIS_ID, "manifest hypothesis ID mismatch")
    require(manifest["run_id"] == BACKTEST_RUN_ID, "backtest run ID mismatch")
    require(manifest["source_commit_sha"] == BACKTEST_SOURCE_SHA, "backtest source commit mismatch")
    require(manifest["status"] == "COMPLETED" and manifest["completed_backtest"] is True,
            "manifest does not record a completed empirical backtest")
    require(manifest["backtest_run"] is True and manifest["model_fit_performed"] is True,
            "manifest does not record model fitting and backtest execution")
    require(manifest["raw_observations_saved"] is False, "raw observations should not have been committed")
    require(manifest["timebox"]["cycle"] == 3 and manifest["timebox"]["maximum_substantive_cycles"] == 4,
            "backtest timebox/cycle identity differs from preregistration")
    require(sha256(preflight_raw) == PREFLIGHT_SHA256, "accepted preflight manifest SHA-256 mismatch")
    require(manifest["source"]["preflight_manifest_sha256"] == PREFLIGHT_SHA256,
            "backtest manifest does not pin the accepted preflight manifest")
    require(manifest["source"]["preflight_run_id"] == PREFLIGHT_RUN_ID,
            "backtest manifest references a different preflight run")
    require(manifest["source"]["preflight_artifact_id"] == PREFLIGHT_ARTIFACT_ID,
            "backtest manifest references a different preflight artifact")
    require(manifest["source"]["preflight_artifact_zip_sha256"] == PREFLIGHT_ARTIFACT_SHA256,
            "backtest manifest references a different preflight artifact digest")
    require(preflight["status"] == "PASS" and preflight["hypothesis_id"] == HYPOTHESIS_ID,
            "source preflight is not an accepted PASS for this hypothesis")
    require(str(preflight["workflow_run_id"]) == PREFLIGHT_RUN_ID,
            "preflight run ID mismatch")
    require(preflight["source_commit_sha"] == PREFLIGHT_SOURCE_SHA,
            "preflight source commit mismatch")
    require(preflight["backtest_run"] is False and preflight["raw_observations_saved"] is False,
            "preflight was not source-only")

    source = manifest["source"]
    require(source["dex"]["canonical_daily_sha256"] == preflight["dex_source"]["canonical_daily_sha256"],
            "DEX canonical hash differs from accepted preflight")
    require(source["tvl"]["canonical_daily_sha256"] == preflight["tvl_source"]["canonical_daily_sha256"],
            "TVL canonical hash differs from accepted preflight")
    require(source["hourly_klines"]["canonical_close_sha256"]
            == preflight["binance_hourly_archives"]["canonical_close_sha256"],
            "ETHUSDT close hash differs from accepted preflight")
    require(source["binance_market"]["status"] == "TRADING"
            and source["binance_market"]["spot_trading_allowed"] is True,
            "ETHUSDT Spot market is not verified active")
    hourly = preflight["binance_hourly_archives"]
    require(hourly["monthly_archive_count"] == 70 and hourly["daily_gap_repair_archive_count"] == 7,
            "archive population differs from the accepted preflight")
    require(hourly["expected_hourly_rows"] == 51120 and hourly["observed_hourly_rows"] == 51106,
            "hourly coverage differs from the accepted preflight")
    require(hourly["missing_hours"] == 14 and hourly["maximum_consecutive_missing_hours"] == 4,
            "missing-hour population differs from the accepted preflight")
    require(all(item["checksum_verified"] is True for item in hourly["monthly_archives"]),
            "one or more monthly archive checksums were not verified")
    require(all(item["checksum_verified"] is True for item in hourly["daily_gap_repairs"]),
            "one or more daily cross-check archive checksums were not verified")
    require(all(item["filled_hour_count"] == 0 for item in hourly["daily_gap_repairs"]),
            "a missing hourly observation was filled")
    require(all(item["filled_hour_count"] == 0 for item in source["hourly_klines"]["daily_gap_repairs"]),
            "the backtest source record reports a filled hourly observation")
    require(source["dex"]["rows_in_frozen_window"] == 2128
            and source["tvl"]["rows_in_frozen_window"] == 2128,
            "DEX/TVL sample counts differ from the accepted preflight")
    require(source["dex"]["last_date"] == "2026-10-29"
            and source["tvl"]["last_date"] == "2026-10-29",
            "DEX/TVL coverage end differs from the accepted preflight")

    require(HYPOTHESIS_ID in prereg_text and "Cycle 4" in prereg_text,
            "frozen preregistration or independent-audit cycle is missing")
    require("**Status:** COMPLETED" in report_text
            and "**Decision:** INCONCLUSIVE" in report_text
            and "**Completed real-data backtest:** True" in report_text,
            "persisted session report does not agree with the completed INCONCLUSIVE manifest")

    row_checks = validate_forecasts(rows)
    validation_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]
    require(len(rows) == manifest["forecast_count"] == 1392, "forecast row count mismatch")
    require(len(validation_rows) == manifest["forecast_counts_by_split"]["validation"] == 723,
            "validation forecast count mismatch")
    require(len(test_rows) == manifest["forecast_counts_by_split"]["test"] == 669,
            "test forecast count mismatch")

    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    bootstrap = paired_loss_block_bootstrap(test_rows)
    for label, actual, expected in (
        ("validation", validation, manifest["validation_metrics"]),
        ("test", test, manifest["test_metrics"]),
        ("paired bootstrap", bootstrap, manifest["paired_test_loss_bootstrap"]),
    ):
        for key, value in actual.items():
            require(key in expected and close(value, expected[key], rel=1e-10, abs_=1e-12),
                    f"{label} metric mismatch for {key}: reconstructed={value}, persisted={expected.get(key)}")
    decision = disposition(validation, test, bootstrap)
    require(decision == manifest["decision"] == "INCONCLUSIVE",
            f"frozen disposition mismatch: reconstructed={decision}, persisted={manifest['decision']}")

    return {
        "status": "PASS",
        "hypothesis_id": HYPOTHESIS_ID,
        "backtest_run_id": BACKTEST_RUN_ID,
        "backtest_source_sha": BACKTEST_SOURCE_SHA,
        "audit_source_sha": os.environ.get("GITHUB_SHA", "local"),
        "csv_sha256": sha256(csv_raw),
        "csv_bytes": len(csv_raw),
        "manifest_sha256": sha256(manifest_raw),
        "preflight_sha256": sha256(preflight_raw),
        "preflight_artifact_id": PREFLIGHT_ARTIFACT_ID,
        "preflight_artifact_zip_sha256": PREFLIGHT_ARTIFACT_SHA256,
        "row_checks": row_checks,
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_test_loss_bootstrap": bootstrap,
        "reconstructed_decision": decision,
        "source_checks": {
            "preflight_and_run_ids_pinned": True,
            "source_hashes_match_preflight": True,
            "monthly_and_daily_archive_checksums_verified": True,
            "missing_hours_preserved_without_filling": True,
            "DEX_and_TVL_sample_coverage_matches": True,
            "spot_market_active": True,
        },
        "limitations": [
            "This is an independent artifact-level reconstruction, not a second-venue replication.",
            "The audit verifies persisted source hashes and manifests; it does not re-download historical market data.",
            "DeFiLlama history is current-vintage and may be revised; aggregate DEX volume is not ETH-specific.",
            "The result is a forecast-only screen, not causal evidence, trading P&L, execution validation or strategy authorization.",
        ],
    }


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H%M%SZ")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    out_dir = ROOT / "reports/generated/ethereum-dex-turnover-eth-rv-independent-audit" / f"{run_id}-attempt-{attempt}"
    session_dir = ROOT / "reports/sessions" / now.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)
    audit_json = out_dir / "audit.json"
    report = session_dir / f"{stamp}_session-ethereum-dex-turnover-eth-rv-independent-audit-{run_id}.md"
    try:
        result = verify_bundle()
        result.update({
            "audit_run_id": run_id,
            "audit_attempt": attempt,
            "audit_timestamp_utc": now.isoformat(),
            "audit_script_sha256": sha256(Path(__file__).read_bytes()),
        })
        audit_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        lines = [
            "# Ethereum DEX turnover / ETH RV — independent evidence audit",
            "",
            f"- **Hypothesis:** {HYPOTHESIS_ID}",
            "- **Audit status:** PASS",
            "- **Backtest disposition:** INCONCLUSIVE",
            f"- **Backtest run:** {BACKTEST_RUN_ID}",
            f"- **Backtest source commit:** {BACKTEST_SOURCE_SHA}",
            f"- **Audit run:** {run_id}, attempt {attempt}",
            f"- **Audit timestamp:** {now.isoformat()}",
            "",
            "## Reconstructed empirical result",
            "",
            "| Split | N | Baseline RMSE | Augmented RMSE | RMSE change | Baseline MAE | Augmented MAE |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for label, metrics in (("Validation", result["validation_metrics"]), ("Test", result["test_metrics"])):
            lines.append(
                f"| {label} | {metrics['n']} | {metrics['baseline_rmse']:.12f} | "
                f"{metrics['augmented_rmse']:.12f} | {metrics['rmse_improvement_pct']:.6f}% | "
                f"{metrics['baseline_mae']:.12f} | {metrics['augmented_mae']:.12f} |"
            )
        boot = result["paired_test_loss_bootstrap"]
        lines += [
            "",
            "## Paired test-loss block bootstrap",
            "",
            f"- Mean baseline-minus-augmented squared loss: {boot['mean_baseline_minus_augmented_squared_loss']:.12f}.",
            f"- 95% circular seven-event block-bootstrap interval: [{boot['ci95_lower']:.12f}, {boot['ci95_upper']:.12f}].",
            f"- Replications / seed: {boot['reps']} / {boot['seed']}.",
            "- The interval crosses zero; the frozen PROMISING and REJECTED criteria are both unmet.",
            "",
            "## Independent integrity checks",
            "",
            f"- Forecast rows: {result['row_checks']['rows']}; validation/test: {result['row_checks']['validation_n']}/{result['row_checks']['test_n']}.",
            f"- Training windows: {result['row_checks']['train_n_min']}–{result['row_checks']['train_n_max']} rows; strict maturity lag: {result['row_checks']['strict_maturity_lag_days_min']}–{result['row_checks']['strict_maturity_lag_days_max']} days.",
            "- Reconstructed UTC signal times, 24-hour targets, non-overlap, seven-day feature dates, turnover transforms, target transforms and squared losses.",
            "- Recomputed validation/test RMSE and MAE from persisted targets and predictions.",
            "- Recomputed the exact NumPy default_rng circular block bootstrap from persisted forecasts and matched the original manifest.",
            "- Matched DEX, TVL and hourly-close canonical hashes to the pinned source-preflight manifest.",
            "- Verified all 70 monthly and seven daily archive checksum flags; all seven daily gap checks report zero filled hours.",
            "",
            "## Source and artifact digests",
            "",
            f"- Forecast CSV SHA-256: {result['csv_sha256']}.",
            f"- Backtest manifest SHA-256: {result['manifest_sha256']}.",
            f"- Preflight manifest SHA-256: {result['preflight_sha256']}.",
            f"- Preflight artifact: {result['preflight_artifact_id']}; ZIP SHA-256 {result['preflight_artifact_zip_sha256']}.",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in result["limitations"])
        lines += ["", f"Machine-readable audit: {audit_json.relative_to(ROOT)}.", ""]
        report.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps({"status": "PASS", "audit_json": str(audit_json.relative_to(ROOT)),
                          "report": str(report.relative_to(ROOT)), "result": result}, indent=2, sort_keys=True))
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "hypothesis_id": HYPOTHESIS_ID,
            "backtest_run_id": BACKTEST_RUN_ID,
            "audit_run_id": run_id,
            "audit_attempt": attempt,
            "audit_timestamp_utc": now.isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        audit_json.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report.write_text(
            "# Ethereum DEX turnover / ETH RV — independent evidence audit\n\n"
            f"- **Audit status:** FAIL\n- **Hypothesis:** {HYPOTHESIS_ID}\n"
            f"- **Backtest run:** {BACKTEST_RUN_ID}\n- **Error:** {failure['error']}\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, indent=2, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
