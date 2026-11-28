from __future__ import annotations

import datetime as dt
import math
import unittest

import audit_h8_ci_credit_impulse_btc_downside as audit


class H8IndependentAuditTests(unittest.TestCase):
    def row(self, signal: str, target: float = 1.0) -> dict:
        day = dt.date.fromisoformat(signal)
        baseline = target + 0.25
        augmented = target + 0.5
        return {
            "observation_date": signal,
            "signal_date": signal,
            "target_start_date": (day + dt.timedelta(days=1)).isoformat(),
            "target_end_date": (day + dt.timedelta(days=5)).isoformat(),
            "target_log1p_semivariance": target,
            "baseline_prediction": baseline,
            "augmented_prediction": augmented,
            "baseline_squared_error": (target - baseline) ** 2,
            "augmented_squared_error": (target - augmented) ** 2,
            "totci_change_4w_pct": 0.1,
            "pre_downside5_log": 0.2,
            "pre_downside20_log": 0.3,
            "pre_rv20_log": 0.4,
            "pre_return5": 0.01,
            "pre_return20": 0.02,
            "train_n": 104,
        }

    def test_valid_weekly_matured_forecast_rows_pass_integrity_gate(self):
        rows = [
            self.row("2026-10-04", 1.0),
            self.row("2026-10-11", 1.2),
            self.row("2026-10-18", 0.8),
        ]
        audit.validate_forecast_rows(rows)

    def test_rejects_nonweekly_forecast_origins(self):
        rows = [self.row("2026-10-04"), self.row("2026-10-18")]
        with self.assertRaisesRegex(ValueError, "not weekly"):
            audit.validate_forecast_rows(rows)

    def test_rejects_unmatured_or_wrong_sized_training_window(self):
        rows = [self.row("2026-10-04")]
        rows[0]["train_n"] = 103
        with self.assertRaisesRegex(ValueError, "104 matured"):
            audit.validate_forecast_rows(rows)

    def test_rejects_corrupted_squared_error(self):
        rows = [self.row("2026-10-04")]
        rows[0]["baseline_squared_error"] += 0.1
        with self.assertRaisesRegex(ValueError, "squared error"):
            audit.validate_forecast_rows(rows)

    def test_independent_ols_reconstructs_known_linear_relationship(self):
        train = []
        for index in range(20):
            x = float(index)
            train.append({
                "x": x,
                "target_bp": 2.0 + 3.0 * x,
            })
        current = {"x": 20.0}
        prediction = audit._fit_ols_predict(train, current, ("x",))
        self.assertTrue(math.isclose(prediction, 62.0, rel_tol=1e-8, abs_tol=1e-8))

    def test_paired_bootstrap_is_deterministic(self):
        rows = []
        for index in range(40):
            target = 0.1 + 0.01 * index
            baseline = target + 0.02
            augmented = target + (0.01 if index % 2 else 0.03)
            rows.append({
                "target_log1p_semivariance": target,
                "baseline_prediction": baseline,
                "augmented_prediction": augmented,
                "baseline_squared_error": (baseline - target) ** 2,
                "augmented_squared_error": (augmented - target) ** 2,
            })
        first = audit.paired_loss_bootstrap(rows)
        second = audit.paired_loss_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["observations"], 40)
        self.assertEqual(first["replications"], 2000)
        self.assertEqual(first["block_size_events"], 4)
        self.assertEqual(first["seed"], 20261128)


if __name__ == "__main__":
    unittest.main()
