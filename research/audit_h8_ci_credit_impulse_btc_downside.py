#!/usr/bin/env python3
"""Independent reconstruction of the frozen H.8 C&I / BTC forecast screen.

Source transport and checksum adapters are reused from the admitted implementation;
event construction, rolling fits, forecast comparisons, metrics and inference are
recomputed independently here.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
import statistics
from pathlib import Path

import numpy as np

import h8_ci_credit_impulse_btc_downside as admitted

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUN_ID = 46119814521
ORIGINAL_DIR = ROOT / "reports/generated/h8-ci-credit-impulse-btc-downside/46119814521-attempt-1"
ORIGINAL_MANIFEST = ORIGINAL_DIR / "manifest.json"
ORIGINAL_FORECASTS = ORIGINAL_DIR / "forecast_rows.csv"
ORIGINAL_REPORT = ROOT / "reports/sessions/2026-11-28/2026-11-28T070841Z_session-h8-ci-credit-impulse-btc-downside-46119814521.md"
BASE_FEATURES = (
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
)
AUGMENTED_FEATURES = BASE_FEATURES + ("totci_change_4w_pct",)
DATE_FIELDS = ("observation_date", "signal_date", "target_start_date", "target_end_date")
NUMERIC_FIELDS = (
    "target_log1p_semivariance",
    "baseline_prediction",
    "augmented_prediction",
    "baseline_squared_error",
    "augmented_squared_error",
    "totci_change_4w_pct",
    "pre_downside5_log",
    "pre_downside20_log",
    "pre_rv20_log",
    "pre_return5",
    "pre_return20",
)
COMPARE_TOLERANCE = 2e-7


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close_enough(actual: float, expected: float, tolerance: float = COMPARE_TOLERANCE) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)


def parse_forecast_csv(path: Path = ORIGINAL_FORECASTS) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = set(DATE_FIELDS) | set(NUMERIC_FIELDS) | {"train_n"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"forecast CSV schema is incomplete: {reader.fieldnames}")
        for line_number, raw in enumerate(reader, start=2):
            row = {key: raw[key] for key in DATE_FIELDS}
            for key in NUMERIC_FIELDS:
                row[key] = float(raw[key])
            row["train_n"] = int(raw["train_n"])
            if not all(math.isfinite(row[key]) for key in NUMERIC_FIELDS):
                raise ValueError(f"non-finite forecast value at CSV line {line_number}")
            rows.append(row)
    if not rows:
        raise ValueError("persisted forecast CSV is empty")
    return rows


def validate_forecast_rows(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("forecast rows are empty")
    previous_signal = None
    previous_target_end = None
    for index, row in enumerate(rows):
        signal = dt.date.fromisoformat(row["signal_date"])
        observation = dt.date.fromisoformat(row["observation_date"])
        target_start = dt.date.fromisoformat(row["target_start_date"])
        target_end = dt.date.fromisoformat(row["target_end_date"])
        if observation != signal or signal.weekday() != 6:
            raise ValueError(f"row {index}: observation/signal must be the same Sunday UTC date")
        if target_start != signal + dt.timedelta(days=1):
            raise ValueError(f"row {index}: target must start on Monday after the Sunday signal")
        if target_end != signal + dt.timedelta(days=5):
            raise ValueError(f"row {index}: target must end on Friday after five UTC sessions")
        if row["train_n"] != 104:
            raise ValueError(f"row {index}: expected 104 matured training events")
        baseline_error = (row["target_log1p_semivariance"] - row["baseline_prediction"]) ** 2
        augmented_error = (row["target_log1p_semivariance"] - row["augmented_prediction"]) ** 2
        if not close_enough(row["baseline_squared_error"], baseline_error):
            raise ValueError(f"row {index}: baseline squared error does not reconcile")
        if not close_enough(row["augmented_squared_error"], augmented_error):
            raise ValueError(f"row {index}: augmented squared error does not reconcile")
        if previous_signal is not None:
            gap_days = (signal - previous_signal).days
            if gap_days < 7 or gap_days % 7 != 0:
                raise ValueError(f"row {index}: forecast origins are not on the weekly Sunday grid")
            if previous_target_end >= signal:
                raise ValueError(f"row {index}: a prior target overlaps or remains immature")
        previous_signal = signal
        previous_target_end = target_end


def _feature_from_vintage(vintage: str, observations: dict[dt.date, float]) -> float | None:
    vintage_date = dt.date.fromisoformat(vintage)
    if not observations:
        return None
    dates = sorted(observations)
    if dates[-1] > vintage_date:
        return None
    latest = dates[-1]
    age = (vintage_date - latest).days
    if age < 3 or age > 14 or latest.weekday() != 2 or len(dates) < 5:
        return None
    tail = dates[-5:]
    gaps = [(right - left).days for left, right in zip(tail, tail[1:])]
    span = (tail[-1] - tail[0]).days
    if any(gap < 5 or gap > 9 for gap in gaps) or not 21 <= span <= 35:
        return None
    latest_value, lag_value = observations[tail[-1]], observations[tail[0]]
    if latest_value <= 0 or lag_value <= 0:
        return None
    result = 100.0 * math.log(latest_value / lag_value)
    return result if math.isfinite(result) else None


def _semi_variance(values: list[float]) -> float:
    return math.fsum(min(value, 0.0) ** 2 for value in values) / len(values) * 10_000.0


def _total_variance(values: list[float]) -> float:
    return math.fsum(value * value for value in values) / len(values) * 10_000.0


def reconstruct_events(
    panel: dict[str, dict[dt.date, float]],
    prices: dict[dt.date, float],
) -> list[dict]:
    dates = sorted(prices)
    returns: list[float | None] = [None]
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days != 1:
            returns.append(None)
        else:
            previous, current = prices[dates[index - 1]], prices[dates[index]]
            returns.append(math.log(current / previous) if previous > 0 and current > 0 else None)
    index_by_date = {day: index for index, day in enumerate(dates)}
    events = []
    for vintage in sorted(panel):
        signal = dt.date.fromisoformat(vintage)
        if signal < admitted.FIRST_SIGNAL_DATE or signal > admitted.LAST_SIGNAL_DATE:
            continue
        if signal.weekday() != 6:
            raise ValueError(f"non-Sunday ALFRED vintage: {vintage}")
        credit_change = _feature_from_vintage(vintage, panel[vintage])
        if credit_change is None:
            continue
        index = index_by_date.get(signal)
        if index is None or index < 20 or index + admitted.TARGET_SESSIONS >= len(dates):
            continue
        prior5 = returns[index - 4:index + 1]
        prior20 = returns[index - 19:index + 1]
        future = returns[index + 1:index + 1 + admitted.TARGET_SESSIONS]
        if any(value is None or not math.isfinite(float(value)) for value in prior5 + prior20 + future):
            continue
        p5 = [float(value) for value in prior5]
        p20 = [float(value) for value in prior20]
        future_values = [float(value) for value in future]
        target = _semi_variance(future_values)
        events.append({
            "observation_date": signal,
            "signal_date": signal,
            "target_start_date": dates[index + 1],
            "target_end_date": dates[index + admitted.TARGET_SESSIONS],
            "totci_change_4w_pct": credit_change,
            "pre_downside5_log": math.log1p(_semi_variance(p5)),
            "pre_downside20_log": math.log1p(_semi_variance(p20)),
            "pre_rv20_log": math.log1p(_total_variance(p20)),
            "pre_return5": math.fsum(p5),
            "pre_return20": math.fsum(p20),
            "target_log1p_semivariance": math.log1p(target),
            "target_bp": math.log1p(target),
        })
    for left, right in zip(events, events[1:]):
        if left["target_end_date"] >= right["signal_date"]:
            raise ValueError("reconstructed five-session targets overlap")
    return events


def _fit_ols_predict(train: list[dict], current: dict, feature_names: tuple[str, ...]) -> float:
    matrix = np.asarray([[float(row[name]) for name in feature_names] for row in train], dtype=np.float64)
    means = np.asarray([statistics.fmean(row[name] for row in train) for name in feature_names])
    scales = np.asarray([
        statistics.pstdev(row[name] for row in train) or 1.0
        for name in feature_names
    ])
    scales = np.where(scales > 1e-9, scales, 1.0)
    design = np.column_stack((np.ones(len(train)), (matrix - means) / scales))
    targets = np.asarray([row["target_bp"] for row in train], dtype=np.float64)
    gram = design.T @ design
    gram[1:, 1:] += np.eye(len(feature_names), dtype=np.float64) * 1e-8
    coefficients = np.linalg.solve(gram, design.T @ targets)
    current_features = np.asarray([float(current[name]) for name in feature_names])
    current_design = np.concatenate(([1.0], (current_features - means) / scales))
    return float(current_design @ coefficients)


def reconstruct_forecasts(events: list[dict]) -> list[dict]:
    forecasts = []
    for current in events:
        matured = [
            row for row in events
            if row["signal_date"] < current["signal_date"]
            and row["target_end_date"] < current["signal_date"]
        ]
        train = matured[-104:]
        if len(train) != 104:
            continue
        baseline = _fit_ols_predict(train, current, BASE_FEATURES)
        augmented = _fit_ols_predict(train, current, AUGMENTED_FEATURES)
        target = float(current["target_log1p_semivariance"])
        forecasts.append({
            "observation_date": current["observation_date"].isoformat(),
            "signal_date": current["signal_date"].isoformat(),
            "target_start_date": current["target_start_date"].isoformat(),
            "target_end_date": current["target_end_date"].isoformat(),
            "target_log1p_semivariance": target,
            "baseline_prediction": baseline,
            "augmented_prediction": augmented,
            "baseline_squared_error": (target - baseline) ** 2,
            "augmented_squared_error": (target - augmented) ** 2,
            "totci_change_4w_pct": current["totci_change_4w_pct"],
            "pre_downside5_log": current["pre_downside5_log"],
            "pre_downside20_log": current["pre_downside20_log"],
            "pre_rv20_log": current["pre_rv20_log"],
            "pre_return5": current["pre_return5"],
            "pre_return20": current["pre_return20"],
            "train_n": len(train),
        })
    return forecasts


def compare_forecasts(reconstructed: list[dict], persisted: list[dict]) -> dict:
    if len(reconstructed) != len(persisted):
        raise ValueError(f"forecast row count differs: reconstructed={len(reconstructed)}, persisted={len(persisted)}")
    maxima = {field: 0.0 for field in NUMERIC_FIELDS}
    for index, (expected, actual) in enumerate(zip(reconstructed, persisted)):
        for field in DATE_FIELDS:
            if expected[field] != actual[field]:
                raise ValueError(f"forecast row {index} {field} differs: {expected[field]} != {actual[field]}")
        if expected["train_n"] != actual["train_n"]:
            raise ValueError(f"forecast row {index} training-window size differs")
        for field in NUMERIC_FIELDS:
            difference = abs(float(expected[field]) - float(actual[field]))
            maxima[field] = max(maxima[field], difference)
            if not close_enough(expected[field], actual[field]):
                raise ValueError(
                    f"forecast row {index} {field} differs: "
                    f"reconstructed={expected[field]!r}, persisted={actual[field]!r}, abs_diff={difference}"
                )
    return maxima


def forecast_metrics(rows: list[dict]) -> dict:
    baseline_errors = [row["baseline_prediction"] - row["target_log1p_semivariance"] for row in rows]
    augmented_errors = [row["augmented_prediction"] - row["target_log1p_semivariance"] for row in rows]
    baseline_rmse = math.sqrt(math.fsum(value * value for value in baseline_errors) / len(rows))
    augmented_rmse = math.sqrt(math.fsum(value * value for value in augmented_errors) / len(rows))
    return {
        "n": len(rows),
        "baseline_rmse": baseline_rmse,
        "augmented_rmse": augmented_rmse,
        "baseline_mae": math.fsum(abs(value) for value in baseline_errors) / len(rows),
        "augmented_mae": math.fsum(abs(value) for value in augmented_errors) / len(rows),
        "rmse_improvement_pct": 100.0 * (baseline_rmse - augmented_rmse) / baseline_rmse,
    }


def paired_loss_bootstrap(rows: list[dict]) -> dict:
    differences = np.asarray([
        row["baseline_squared_error"] - row["augmented_squared_error"] for row in rows
    ], dtype=np.float64)
    if len(differences) < admitted.BOOTSTRAP_BLOCK or not np.isfinite(differences).all():
        raise ValueError("insufficient or non-finite paired test losses")
    rng = np.random.default_rng(admitted.BOOTSTRAP_SEED)
    samples = np.empty(admitted.BOOTSTRAP_REPS, dtype=np.float64)
    count = len(differences)
    for replication in range(admitted.BOOTSTRAP_REPS):
        indices = []
        while len(indices) < count:
            start = int(rng.integers(0, count))
            indices.extend((start + offset) % count for offset in range(admitted.BOOTSTRAP_BLOCK))
        samples[replication] = float(np.mean(differences[np.asarray(indices[:count], dtype=int)]))
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "status": "COMPUTED",
        "observations": count,
        "replications": admitted.BOOTSTRAP_REPS,
        "block_size_events": admitted.BOOTSTRAP_BLOCK,
        "seed": admitted.BOOTSTRAP_SEED,
        "mean_baseline_minus_augmented_squared_loss": float(np.mean(differences)),
        "ci_95_low": float(lower),
        "ci_95_high": float(upper),
        "bootstrap_fraction_positive": float(np.mean(samples > 0)),
    }


def _assert_metric_match(actual: dict, expected: dict, label: str) -> None:
    for key in ("n", "baseline_rmse", "augmented_rmse", "baseline_mae", "augmented_mae", "rmse_improvement_pct"):
        if key == "n":
            if actual[key] != expected[key]:
                raise ValueError(f"{label} metric {key} differs: {actual[key]} != {expected[key]}")
        elif not close_enough(actual[key], expected[key], 1e-8):
            raise ValueError(f"{label} metric {key} differs: {actual[key]} != {expected[key]}")


def _assert_bootstrap_match(actual: dict, expected: dict) -> None:
    for key in ("status", "observations", "replications", "block_size_events", "seed"):
        if actual[key] != expected[key]:
            raise ValueError(f"bootstrap field {key} differs")
    for key in (
        "mean_baseline_minus_augmented_squared_loss",
        "ci_95_low",
        "ci_95_high",
        "bootstrap_fraction_positive",
    ):
        if not close_enough(actual[key], expected[key], 1e-8):
            raise ValueError(f"bootstrap field {key} differs: {actual[key]} != {expected[key]}")


def _decision(validation: dict, test: dict, paired: dict) -> str:
    if (
        validation["rmse_improvement_pct"] >= 1.0
        and test["rmse_improvement_pct"] >= 1.0
        and paired["ci_95_low"] > 0
    ):
        return "PROMISING"
    if (
        validation["rmse_improvement_pct"] <= 0
        and test["rmse_improvement_pct"] <= 0
        and paired["ci_95_high"] < 0
    ):
        return "REJECTED"
    return "INCONCLUSIVE"


def run_audit() -> dict:
    original = json.loads(ORIGINAL_MANIFEST.read_text(encoding="utf-8"))
    if str(original.get("run_id")) != str(ORIGINAL_RUN_ID) or original.get("completed_backtest") is not True:
        raise ValueError("original manifest identity or completion status is invalid")
    if original.get("hypothesis_id") != admitted.HYPOTHESIS_ID:
        raise ValueError("original manifest hypothesis identity differs")

    preflight_manifest, btc_manifest, frozen_hashes = admitted.verify_frozen_preflights()
    actual_prereg_sha = sha256_file(admitted.PREREG_PATH)
    if actual_prereg_sha != original.get("prereg_sha256"):
        raise ValueError("preregistration content hash differs from the frozen empirical manifest")
    if frozen_hashes != original.get("frozen_file_hashes"):
        raise ValueError("frozen source-manifest file hashes differ from the empirical manifest")

    panel, alfred_source = admitted.fetch_alfred_panel()
    prices, btc_source = admitted.fetch_btc_prices(btc_manifest)

    original_alfred = original["data_sources"]["ALFRED"]
    original_canonical = [row["canonical_batch_sha256"] for row in original_alfred["batch_records"]]
    current_canonical = [row["canonical_batch_sha256"] for row in alfred_source["batch_records"]]
    if current_canonical != original_canonical:
        raise ValueError("re-fetched ALFRED canonical batch hashes differ from the original run")
    if len(panel) != 484 or len(alfred_source["batch_records"]) != 41:
        raise ValueError("re-fetched ALFRED vintage or batch count differs from the frozen sample")
    if preflight_manifest["canonical_panel_sha256"] != original["source_preflight"]["canonical_panel_sha256"]:
        raise ValueError("ALFRED preflight sample hash differs")
    if btc_source["archive_manifest_sha256"] != original["data_sources"]["BTCUSDT"]["archive_manifest_sha256"]:
        raise ValueError("re-fetched Binance archive manifest hash differs")
    if len(prices) != 3388 or btc_source["archive_count"] != 136:
        raise ValueError("re-fetched BTC archive coverage differs")

    events = reconstruct_events(panel, prices)
    if len(events) != original["event_construction"]["accepted_events"]:
        raise ValueError("independently reconstructed event count differs")
    if events[0]["signal_date"].isoformat() != original["event_construction"]["first_signal"]:
        raise ValueError("first reconstructed event differs")
    if events[-1]["signal_date"].isoformat() != original["event_construction"]["last_signal"]:
        raise ValueError("last reconstructed event differs")
    if events[-1]["target_end_date"].isoformat() != original["event_construction"]["target_end_last_event"]:
        raise ValueError("last reconstructed target end differs")

    reconstructed = reconstruct_forecasts(events)
    persisted = parse_forecast_csv()
    validate_forecast_rows(persisted)
    max_differences = compare_forecasts(reconstructed, persisted)

    manifest_rows = original.get("forecast_rows", [])
    if len(manifest_rows) != len(persisted):
        raise ValueError("manifest forecast-row count differs from CSV")
    compare_forecasts(
        [{key: row[key] for key in DATE_FIELDS + NUMERIC_FIELDS + ("train_n",)} for row in manifest_rows],
        persisted,
    )

    validation_rows = [
        row for row in reconstructed
        if dt.date.fromisoformat(row["signal_date"]) >= admitted.VALIDATION_START
        and dt.date.fromisoformat(row["signal_date"]) < admitted.TEST_START
    ]
    test_rows = [
        row for row in reconstructed
        if dt.date.fromisoformat(row["signal_date"]) >= admitted.TEST_START
    ]
    validation = forecast_metrics(validation_rows)
    test = forecast_metrics(test_rows)
    paired = paired_loss_bootstrap(test_rows)
    _assert_metric_match(validation, original["validation_metrics"], "validation")
    _assert_metric_match(test, original["test_metrics"], "test")
    _assert_bootstrap_match(paired, original["paired_test_loss_bootstrap"])
    decision = _decision(validation, test, paired)
    if decision != original["decision"]:
        raise ValueError(f"independent decision differs: {decision} != {original['decision']}")

    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H%M%SZ")
    audit_path = (
        Path("reports/generated/h8-ci-credit-impulse-btc-downside/independent-audit")
        / f"{run_id}-attempt-{attempt}"
        / "audit.json"
    )
    report_path = (
        Path("reports/sessions")
        / now.strftime("%Y-%m-%d")
        / f"{stamp}_session-h8-ci-credit-impulse-independent-audit-{run_id}.md"
    )

    result = {
        "audit_status": "PASS",
        "audit_type": "independent_model_and_forecast_reconstruction",
        "hypothesis_id": admitted.HYPOTHESIS_ID,
        "original_backtest_run_id": ORIGINAL_RUN_ID,
        "audit_run_id": run_id,
        "audit_run_attempt": int(attempt),
        "audited_at_utc": now.isoformat(),
        "source_reconstruction": {
            "alfred_vintages": len(panel),
            "alfred_batches": len(alfred_source["batch_records"]),
            "alfred_sample_canonical_sha256": alfred_source["accepted_sample_canonical_sha256"],
            "alfred_batch_canonical_hashes_match_original": True,
            "binance_rows": len(prices),
            "binance_archives": btc_source["archive_count"],
            "binance_archive_manifest_sha256": btc_source["archive_manifest_sha256"],
            "frozen_file_hashes_match_original": True,
        },
        "event_reconstruction": {
            "accepted_events": len(events),
            "first_signal": events[0]["signal_date"].isoformat(),
            "last_signal": events[-1]["signal_date"].isoformat(),
            "last_target_end": events[-1]["target_end_date"].isoformat(),
        },
        "forecast_reconstruction": {
            "forecast_rows": len(reconstructed),
            "validation_rows": len(validation_rows),
            "test_rows": len(test_rows),
            "all_training_windows_equal_104": all(row["train_n"] == 104 for row in reconstructed),
            "all_forecast_rows_match_persisted_within_tolerance": True,
            "maximum_absolute_numeric_differences": max_differences,
        },
        "validation_metrics": validation,
        "test_metrics": test,
        "paired_test_loss_bootstrap": paired,
        "decision": decision,
        "disposition": (
            "INCONCLUSIVE — both validation and test RMSE worsen, but the paired test-loss "
            "95% interval crosses zero; the preregistered rejection rule is not met."
        ),
        "preregistration_sha256": actual_prereg_sha,
        "original_source_commit_sha": original["source_commit_sha"],
        "original_backtest_manifest_sha256": sha256_file(ORIGINAL_MANIFEST),
        "limitations": [
            "ALFRED and Binance data were re-fetched and their canonical source/archive hashes revalidated; the original raw observations were not retained as repository files.",
            "The audit reuses the admitted source transport and archive adapters but independently reconstructs vintage features, events, matured training windows, OLS fits, every forecast, metrics, and bootstrap inference.",
            "ALFRED vintage dates have day-level rather than intraday first-publication resolution.",
            "The study is a single-venue BTCUSDT forecast screen, not causal identification, executable P&L, profitability, or strategy promotion.",
            "The nominal paired bootstrap does not correct repository-wide multiple testing or research-selection bias.",
        ],
        "audit_path": audit_path.as_posix(),
        "report_path": report_path.as_posix(),
    }

    audit_file = ROOT / audit_path
    report_file = ROOT / report_path
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_file.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "audit_status": result["audit_status"],
        "original_backtest_run_id": ORIGINAL_RUN_ID,
        "audit_path": result["audit_path"],
        "report_path": result["report_path"],
        "source_reconstruction": result["source_reconstruction"],
        "event_reconstruction": result["event_reconstruction"],
        "forecast_reconstruction": result["forecast_reconstruction"],
        "decision": decision,
    }, indent=2))
    return result


def render_report(result: dict) -> str:
    validation = result["validation_metrics"]
    test = result["test_metrics"]
    paired = result["paired_test_loss_bootstrap"]
    lines = [
        "# Independent audit — H.8 C&I credit impulse / BTC downside semivariance",
        "",
        f"- **Audit status:** {result['audit_status']}",
        f"- **Hypothesis:** {result['hypothesis_id']}",
        f"- **Original backtest:** #{result['original_backtest_run_id']}",
        f"- **Audit run:** #{result['audit_run_id']}",
        f"- **Audited at:** {result['audited_at_utc']}",
        f"- **Decision:** {result['decision']}",
        "",
        "## Source and event reconstruction",
        "",
        f"- ALFRED: {result['source_reconstruction']['alfred_vintages']} weekly vintages across {result['source_reconstruction']['alfred_batches']} requests; canonical batch hashes match the original run.",
        f"- Binance Spot: {result['source_reconstruction']['binance_rows']} BTCUSDT daily candles across {result['source_reconstruction']['binance_archives']} checksum-verified archives; archive-manifest hash matches.",
        f"- Events: {result['event_reconstruction']['accepted_events']} accepted weekly Sunday events, from {result['event_reconstruction']['first_signal']} to {result['event_reconstruction']['last_signal']}; final target ends {result['event_reconstruction']['last_target_end']}.",
        "",
        "## Independent forecast reconstruction",
        "",
        f"- Reconstructed {result['forecast_reconstruction']['forecast_rows']} forecasts: {result['forecast_reconstruction']['validation_rows']} validation and {result['forecast_reconstruction']['test_rows']} test.",
        "- Every training window contains 104 fully matured prior events.",
        "- Independently recomputed OLS predictions, target values, squared errors, validation/test metrics and paired moving-block bootstrap match the persisted evidence within the recorded numerical tolerance.",
        "",
        "| Metric | Validation | Test |",
        "|---|---:|---:|",
        f"| Forecasts | {validation['n']} | {test['n']} |",
        f"| Baseline RMSE | {validation['baseline_rmse']:.12f} | {test['baseline_rmse']:.12f} |",
        f"| Augmented RMSE | {validation['augmented_rmse']:.12f} | {test['augmented_rmse']:.12f} |",
        f"| RMSE improvement | {validation['rmse_improvement_pct']:.6f}% | {test['rmse_improvement_pct']:.6f}% |",
        "",
        f"- Paired test-loss 95% CI: [{paired['ci_95_low']:.12f}, {paired['ci_95_high']:.12f}].",
        f"- Bootstrap: {paired['replications']} circular moving-block replications, block size {paired['block_size_events']}, seed {paired['seed']}.",
        "",
        "## Disposition",
        "",
        result["disposition"],
        "",
        "This confirms the preregistered INCONCLUSIVE forecast-screen result. It does not establish a causal credit shock, economic value after costs, trading profitability, or permission to promote a strategy.",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in result["limitations"])
    lines += [
        "",
        "## Reproducibility",
        "",
        f"- Original manifest: `{ORIGINAL_MANIFEST.relative_to(ROOT).as_posix()}`",
        f"- Original forecast rows: `{ORIGINAL_FORECASTS.relative_to(ROOT).as_posix()}`",
        f"- Independent audit JSON: `{result['audit_path']}`",
        "",
    ]
    return "\n".join(lines)


def update_documents(result: dict, report_path: str, audit_path: str) -> None:
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start_candidates = [
        "## Active workstream — H.8 C&I bank-credit impulse / BTC downside (independent audit pending)",
        "## Closed workstream — H.8 C&I bank-credit impulse / BTC downside",
    ]
    starts = [readme.find(marker) for marker in start_candidates if readme.find(marker) >= 0]
    end = readme.find("## Non-negotiable boundaries")
    if not starts or end < 0:
        raise ValueError("README H.8 section or its end marker was not found")
    start = min(starts)
    if start >= end:
        raise ValueError("README H.8 section boundaries are invalid")

    validation = result["validation_metrics"]
    test = result["test_metrics"]
    paired = result["paired_test_loss_bootstrap"]
    body = [
        "## Closed workstream — H.8 C&I bank-credit impulse / BTC downside",
        "",
        f"Hypothesis {result['hypothesis_id']} completed its frozen real-data forecast screen and passed an independent reconstruction. **Status: BACKTESTED; decision: {result['decision']}.** Close this identity without retuning.",
        "",
        f"- **Source reconstruction:** re-fetched {result['source_reconstruction']['alfred_vintages']} ALFRED weekly vintages in {result['source_reconstruction']['alfred_batches']} batches and {result['source_reconstruction']['binance_archives']} official Binance Spot archives ({result['source_reconstruction']['binance_rows']} daily BTCUSDT candles). Canonical ALFRED batch hashes, frozen source-file hashes and Binance archive-manifest hash match the original run.",
        f"- **Event/forecast reconstruction:** {result['event_reconstruction']['accepted_events']} accepted Sunday events; {result['forecast_reconstruction']['forecast_rows']} forecasts ({result['forecast_reconstruction']['validation_rows']} validation / {result['forecast_reconstruction']['test_rows']} test). Every 104-event matured training window, feature, target, prediction and squared error was independently reconstructed and matched the persisted rows within tolerance.",
        f"- **Validation:** baseline/augmented RMSE {validation['baseline_rmse']:.9f}/{validation['augmented_rmse']:.9f}; improvement {validation['rmse_improvement_pct']:.4f}%.",
        f"- **Test:** baseline/augmented RMSE {test['baseline_rmse']:.9f}/{test['augmented_rmse']:.9f}; improvement {test['rmse_improvement_pct']:.4f}%.",
        f"- **Paired inference:** {paired['replications']} circular moving-block bootstrap replications, block {paired['block_size_events']}, seed {paired['seed']}; 95% CI [{paired['ci_95_low']:.9f}, {paired['ci_95_high']:.9f}].",
        f"- **Disposition:** {result['disposition']} Both RMSE improvements are negative, but the paired interval crosses zero, so the preregistered REJECTED rule is not met.",
        f"- **Canonical evidence:** [preregistration](research/PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md) · [original report](reports/sessions/2026-11-28/2026-11-28T070841Z_session-h8-ci-credit-impulse-btc-downside-46119814521.md) · [original manifest](reports/generated/h8-ci-credit-impulse-btc-downside/46119814521-attempt-1/manifest.json) · [original forecasts](reports/generated/h8-ci-credit-impulse-btc-downside/46119814521-attempt-1/forecast_rows.csv) · [independent audit report]({report_path}) · [audit JSON]({audit_path}).",
        "- **Limitations:** ALFRED vintage dates are day-level rather than intraday publication timestamps; raw observations were re-fetched and hash-checked rather than retained in the original repository run. This remains a single-venue forecast screen, not causal evidence or trading P&L.",
        "- **Next:** do not retune or reopen this hypothesis ID. A materially different bank-credit mechanism requires a new identity and preregistered timebox.",
        "",
    ]
    readme_path.write_text(readme[:start] + "\n".join(body) + readme[end:], encoding="utf-8")

    registry_path = ROOT / "research/HYPOTHESIS-REGISTRY.md"
    registry = registry_path.read_text(encoding="utf-8")
    matches = [
        index for index, line in enumerate(registry.splitlines())
        if line.startswith(f"| {result['hypothesis_id']} |")
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one H.8 registry row, found {len(matches)}")
    registry_lines = registry.splitlines()
    row = registry_lines[matches[0]]
    audit_link = f"[independent audit]({('../' + audit_path)})"
    if audit_link not in row:
        registry_lines[matches[0]] = row[:-1] + f" / {audit_link} |"
        registry_path.write_text("\n".join(registry_lines) + "\n", encoding="utf-8")


def main() -> int:
    run_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
