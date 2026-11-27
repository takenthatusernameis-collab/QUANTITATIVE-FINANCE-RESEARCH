import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import initial_claims_btc_downside as model


class InitialClaimsBtcDownsideTests(unittest.TestCase):
    def make_market(self, weeks=180, extra_days=40):
        first_week = dt.date(2017, 8, 19)
        claims = {
            first_week + dt.timedelta(days=7 * i):
            220_000.0 * math.exp(0.0007 * i + 0.04 * math.sin(i / 8.0))
            for i in range(weeks)
        }
        first_price = dt.date(2017, 8, 17)
        last_week = first_week + dt.timedelta(days=7 * (weeks - 1))
        days = (last_week + dt.timedelta(days=7) - first_price).days + extra_days
        prices = {
            first_price + dt.timedelta(days=i):
            10_000.0 * math.exp(0.0002 * i + 0.025 * math.sin(i / 8.0) + 0.01 * math.sin(i / 2.7))
            for i in range(days + 1)
        }
        return claims, prices

    def test_weekly_claims_feature_is_strictly_lagged_and_target_starts_after_signal(self):
        claims, prices = self.make_market()
        events, meta = model.build_events(claims, prices)
        self.assertGreater(len(events), 100)
        first = events[0]
        self.assertEqual(first["signal_date"], first["observation_date"] + dt.timedelta(days=7))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        weeks = sorted(claims)
        index = weeks.index(first["observation_date"])
        expected = 100.0 * math.log(claims[weeks[index]] / claims[weeks[index - 4]])
        self.assertAlmostEqual(first["icsa_change_4w_pct"], expected)
        self.assertEqual(meta["release_lag_days"], 7)

    def test_five_session_target_windows_do_not_overlap(self):
        claims, prices = self.make_market()
        events, _ = model.build_events(claims, prices)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_irregular_weekly_window_is_skipped_not_filled(self):
        claims, prices = self.make_market()
        del claims[sorted(claims)[30]]
        _, meta = model.build_events(claims, prices)
        self.assertGreater(meta["skipped"]["irregular_weekly_window"], 0)

    def test_future_price_changes_do_not_change_pre_signal_features(self):
        claims, prices = self.make_market()
        events_a, _ = model.build_events(claims, prices)
        target_event = events_a[40]
        altered = dict(prices)
        signal = target_event["signal_date"]
        for day in sorted(altered):
            if day > signal:
                altered[day] *= 0.5
        events_b, _ = model.build_events(claims, altered)
        by_signal = {row["signal_date"]: row for row in events_b}
        changed = by_signal[signal]
        for field in model.BASE_FEATURES + ["icsa_change_4w_pct"]:
            self.assertAlmostEqual(target_event[field], changed[field])
        self.assertNotAlmostEqual(
            target_event["target_log1p_semivariance"],
            changed["target_log1p_semivariance"],
        )

    def test_walk_forward_requires_104_fully_matured_prior_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(106):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "observation_date": signal - dt.timedelta(days=7),
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "pre_return5": 0.01 * math.sin(index / 2.0),
                "pre_return20": 0.02 * math.cos(index / 5.0),
                "icsa_change_4w_pct": 0.2 * math.cos(index / 5.0),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)

    def test_decision_requires_both_periods_and_positive_paired_interval(self):
        validation = {"n": 50, "rmse_improvement_pct": 2.0}
        test = {"n": 100, "rmse_improvement_pct": 1.0}
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.05}
        self.assertEqual(model.decide(validation, test, paired)[1], "PROMISING")
        self.assertEqual(
            model.decide(validation, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[1],
            "INCONCLUSIVE",
        )
        rejected = {"ci_95_low": -0.2, "ci_95_high": -0.01}
        self.assertEqual(
            model.decide(
                {"n": 50, "rmse_improvement_pct": -2.0},
                {"n": 100, "rmse_improvement_pct": -1.0},
                rejected,
            )[1],
            "REJECTED",
        )

    def test_metrics_and_bootstrap_are_deterministic(self):
        rows = []
        for index in range(60):
            target = 0.3 + 0.1 * math.sin(index / 4.0)
            rows.append({
                "target_log1p_semivariance": target,
                "baseline_prediction": target + 0.03 * math.cos(index / 3.0),
                "augmented_prediction": target + 0.02 * math.cos(index / 3.0),
            })
        first = model.paired_loss_bootstrap(rows)
        second = model.paired_loss_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["observations"], 60)
        metrics = model.forecast_metrics(rows)
        self.assertEqual(metrics["n"], 60)
        self.assertGreater(metrics["rmse_improvement_pct"], 0)

    def test_update_documents_is_idempotent_and_preserves_other_registry_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "HYPOTHESIS-REGISTRY.md"
            prereg = root / "PREREG.md"
            registry.write_text(
                "# Registry\n\n| Hypothesis ID | Status | Mechanism | Data | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n"
                "| EXISTING-ID | REJECTED | Existing row | Existing data | Preserve | existing.md |\n",
                encoding="utf-8",
            )
            prereg.write_text(
                "# Preregistration\n\n- **Hypothesis ID:** `TEST-ID`\n"
                "- **Status:** FEASIBILITY_CHECKED\n\n## Source preflight evidence\n\nFrozen evidence.\n",
                encoding="utf-8",
            )
            result = {
                "status": "INCONCLUSIVE",
                "decision": "INCONCLUSIVE",
                "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True,
                "data_scope": "synthetic test scope",
                "validation_metrics": {"n": 40, "rmse_improvement_pct": 0.2},
                "test_metrics": {"n": 80, "rmse_improvement_pct": -0.1},
                "paired_test_loss_bootstrap": {"ci_95_low": -0.1, "ci_95_high": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/report.md", "reports/manifest.json", "reports/forecasts.csv")
                model.update_documents(result, "reports/report.md", "reports/manifest.json", "reports/forecasts.csv")
            registry_text = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING-ID | REJECTED |", registry_text)
            self.assertEqual(registry_text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE; decision=INCONCLUSIVE.", prereg_text)
            self.assertIn("Frozen evidence.", prereg_text)
            self.assertEqual(prereg_text.count("## Empirical disposition"), 1)


if __name__ == "__main__":
    unittest.main()
