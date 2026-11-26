import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import stablecoin_supply_btc_downside_semivariance as model


class StablecoinSupplyBtcTests(unittest.TestCase):
    def make_market(self, days=900):
        start = model.SAMPLE_START_DATE
        stable = {start + dt.timedelta(days=i): 100_000_000_000.0 * math.exp(0.0002 * i + 0.02 * math.sin(i / 31.0)) for i in range(days)}
        prices = {start + dt.timedelta(days=i): 30000.0 * math.exp(0.0003 * i + 0.04 * math.sin(i / 8.0) + 0.015 * math.sin(i / 2.9)) for i in range(days)}
        return stable, prices

    def test_feature_uses_exact_d_minus_2_and_d_minus_16_observations(self):
        stable, prices = self.make_market()
        events, meta = model.build_events(stable, prices)
        self.assertGreater(len(events), 100)
        first = events[0]
        self.assertEqual(first["signal_date"], model.SAMPLE_START_DATE + dt.timedelta(days=20))
        expected = math.log(stable[first["signal_date"] - dt.timedelta(days=2)] / stable[first["signal_date"] - dt.timedelta(days=16)])
        self.assertAlmostEqual(first["stablecoin_supply_14d_log_change"], expected)
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        self.assertEqual(meta["supply_lag_days"], 2)
        self.assertEqual(meta["supply_lookback_days"], 14)

    def test_missing_exact_supply_date_is_skipped_without_filling(self):
        stable, prices = self.make_market()
        first_signal = model.SAMPLE_START_DATE + dt.timedelta(days=20)
        del stable[first_signal - dt.timedelta(days=2)]
        events, meta = model.build_events(stable, prices)
        self.assertGreater(meta["skipped"]["missing_supply_feature_dates"], 0)
        self.assertNotEqual(events[0]["signal_date"], first_signal)

    def test_five_session_targets_are_nonoverlapping(self):
        stable, prices = self.make_market()
        events, _ = model.build_events(stable, prices)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_walk_forward_requires_104_prior_fully_matured_events(self):
        events = []
        start = dt.date(2021, 1, 1)
        for index in range(106):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal, "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.4 + 0.03 * math.sin(index / 3.0),
                "target_semivariance_pct2": 0.5 + 0.1 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "stablecoin_supply_14d_log_change": 0.01 * math.cos(index / 5.0),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)
        self.assertEqual(predictions[0]["record_date"], predictions[0]["signal_date"])

    def test_decision_requires_both_periods_and_paired_interval(self):
        paired = {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05}
        self.assertEqual(model.decide({"n": 60, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": 1.0}, paired)[0], "BACKTESTED")
        self.assertEqual(model.decide({"n": 60, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[0], "INCONCLUSIVE")
        rejected = {"ci_95_low_bp2": -0.2, "ci_95_high_bp2": -0.01}
        self.assertEqual(model.decide({"n": 60, "rmse_improvement_pct": -2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, rejected)[0], "REJECTED")

    def test_update_documents_is_idempotent_and_preserves_existing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, prereg = root / "HYPOTHESIS-REGISTRY.md", root / "PREREG.md"
            registry.write_text("# Registry\n\n| Hypothesis ID | Status | Mechanism | Data | Disposition | Evidence |\n|---|---|---|---|---|---|\n| EXISTING-ID | REJECTED | Preserve | Existing scope | Existing result | old.md |\n| " + model.HYPOTHESIS_ID + " | PREREGISTERED | pending | pending | pending | prereg.md |\n\n## Disposition rules\n", encoding="utf-8")
            prereg.write_text("# Preregistration\n\n- **Initial status:** PREREGISTERED\n\n## Source-preflight disposition\n\n- pending\n", encoding="utf-8")
            result = {
                "status": "INCONCLUSIVE", "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True, "data_sources": {},
                "summary_metrics": {"validation_n": 60, "test_n": 100},
                "paired_squared_loss_bootstrap": {"ci_95_low_bp2": -0.1, "ci_95_high_bp2": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            content = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING-ID | REJECTED |", content)
            self.assertEqual(content.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE", prereg_text)
            self.assertEqual(prereg_text.count("## Empirical disposition"), 1)


if __name__ == "__main__":
    unittest.main()
