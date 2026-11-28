import datetime as dt
import math
import unittest

import audit_ethereum_dex_turnover_eth_rv as audit


def synthetic_row(day: dt.date, split: str) -> dict:
    signal = int(dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    target = math.log1p(100.0)
    baseline = target + 1.0
    augmented = target + 0.5
    return {
        "date": day.isoformat(),
        "signal_ts": str(signal),
        "target_start_ts": str(signal),
        "target_end_ts": str(signal + 86400),
        "feature_start_date": (day - dt.timedelta(days=8)).isoformat(),
        "feature_end_date": (day - dt.timedelta(days=2)).isoformat(),
        "split": split,
        "train_n": "252",
        "train_start_date": (day - dt.timedelta(days=300)).isoformat(),
        "train_end_date": (day - dt.timedelta(days=2)).isoformat(),
        "target": repr(target),
        "target_rv_bp2": "100.0",
        "baseline_prediction": repr(baseline),
        "augmented_prediction": repr(augmented),
        "baseline_squared_error": "1.0",
        "augmented_squared_error": "0.25",
        "pre_rv24_log": "1.0",
        "pre_rv168_log": "2.0",
        "abs_return24_bps": "3.0",
        "dex_volume_7d_usd": "200.0",
        "mean_tvl_7d_usd": "100.0",
        "dex_turnover_7d": "2.0",
        "dex_turnover_7d_log": repr(math.log1p(2.0)),
    }


class IndependentEvidenceAuditTests(unittest.TestCase):
    def test_valid_rows_reconstruct_timing_maturity_and_feature_transforms(self):
        rows = [
            synthetic_row(dt.date(2023, 1, 1), "validation"),
            synthetic_row(dt.date(2025, 1, 1), "test"),
        ]
        result = audit.validate_forecasts(rows, require_full_sample=False)
        self.assertEqual(result["rows"], 2)
        self.assertTrue(result["chronological_and_non_overlapping"])
        self.assertTrue(result["feature_and_target_timing"])
        self.assertEqual(result["strict_maturity_lag_days_min"], 2)

    def test_rejects_training_target_that_is_not_strictly_matured(self):
        row = synthetic_row(dt.date(2023, 1, 1), "validation")
        row["train_end_date"] = "2022-12-31"
        with self.assertRaisesRegex(audit.AuditError, "strictly matured"):
            audit.validate_forecasts([row], require_full_sample=False)

    def test_rejects_incorrect_feature_window(self):
        row = synthetic_row(dt.date(2023, 1, 1), "validation")
        row["feature_end_date"] = "2022-12-31"
        with self.assertRaisesRegex(audit.AuditError, "feature end"):
            audit.validate_forecasts([row], require_full_sample=False)

    def test_rejects_overlapping_targets(self):
        first = synthetic_row(dt.date(2023, 1, 1), "validation")
        second = synthetic_row(dt.date(2023, 1, 2), "validation")
        second["target_start_ts"] = str(int(second["signal_ts"]) - 1)
        with self.assertRaisesRegex(audit.AuditError, "target does not begin at signal"):
            audit.validate_forecasts([first, second], require_full_sample=False)

    def test_recomputes_metrics_from_targets_and_predictions(self):
        rows = [
            synthetic_row(dt.date(2023, 1, 1), "validation"),
            synthetic_row(dt.date(2023, 1, 2), "validation"),
        ]
        metrics = audit.forecast_metrics(rows)
        self.assertEqual(metrics["n"], 2)
        self.assertAlmostEqual(metrics["baseline_rmse"], 1.0)
        self.assertAlmostEqual(metrics["augmented_rmse"], 0.5)
        self.assertAlmostEqual(metrics["rmse_improvement_pct"], 50.0)

    def test_frozen_circular_block_bootstrap_is_deterministic(self):
        rows = [
            synthetic_row(dt.date(2023, 1, 1) + dt.timedelta(days=index), "test")
            for index in range(30)
        ]
        first = audit.paired_loss_block_bootstrap(rows)
        second = audit.paired_loss_block_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["reps"], 2000)
        self.assertEqual(first["block_size_daily_events"], 7)
        self.assertEqual(first["seed"], 20261128)
        self.assertAlmostEqual(first["mean_baseline_minus_augmented_squared_loss"], 0.75)
        self.assertAlmostEqual(first["ci95_lower"], 0.75)
        self.assertAlmostEqual(first["ci95_upper"], 0.75)

    def test_frozen_disposition_requires_both_splits_and_confident_interval(self):
        promising = {"baseline_rmse": 2.0, "augmented_rmse": 1.8}
        rejected = {"baseline_rmse": 2.0, "augmented_rmse": 2.2}
        self.assertEqual(
            audit.disposition(promising, promising, {"ci95_lower": 0.01, "ci95_upper": 0.5}),
            "PROMISING",
        )
        self.assertEqual(
            audit.disposition(rejected, rejected, {"ci95_lower": -0.5, "ci95_upper": -0.01}),
            "REJECTED",
        )
        self.assertEqual(
            audit.disposition(promising, rejected, {"ci95_lower": -0.1, "ci95_upper": 0.1}),
            "INCONCLUSIVE",
        )


if __name__ == "__main__":
    unittest.main()
