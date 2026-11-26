import datetime as dt
import math
import tempfile
import unittest
from unittest.mock import patch

import epu_btc_downside_semivariance as model


class EpuBtcDownsideTests(unittest.TestCase):
    def make_market(self, days=1800):
        epu_start = dt.date(2017, 8, 12)
        epu = {
            epu_start + dt.timedelta(days=i): 110.0 + 18.0 * math.sin(i / 19.0) + 0.02 * i
            for i in range(days)
        }
        prices = {
            model.BTC_START_DATE + dt.timedelta(days=i):
            10000.0 * math.exp(0.00015 * i + 0.025 * math.sin(i / 8.0) + 0.01 * math.sin(i / 2.7))
            for i in range(days - 5)
        }
        return epu, prices

    def test_parse_epu_accepts_fred_schema_and_skips_missing(self):
        body = (
            b"observation_date,USEPUINDXD\n"
            b"2017-08-12,112.5\n2017-08-13,.\n2017-08-14,109.2\n"
        )
        parsed = model.parse_epu(body)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[dt.date(2017, 8, 12)], 112.5)

    def test_parse_epu_rejects_duplicate_and_nonpositive_values(self):
        duplicate = b"observation_date,USEPUINDXD\n2017-08-12,112.5\n2017-08-12,110.0\n"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_epu(duplicate)
        nonpositive = b"observation_date,USEPUINDXD\n2017-08-12,0\n"
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_epu(nonpositive)

    def test_signal_uses_two_day_lag_and_five_day_log_change(self):
        epu, prices = self.make_market()
        events, meta = model.build_events(epu, prices)
        self.assertGreater(len(events), 100)
        first = events[0]
        self.assertEqual(first["signal_date"], first["epu_date"] + dt.timedelta(days=2))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        expected = math.log(epu[first["epu_date"]] / epu[first["epu_date"] - dt.timedelta(days=5)])
        self.assertAlmostEqual(first["epu_5d_log_change"], expected)
        self.assertEqual(meta["release_lag_days"], 2)
        self.assertEqual(meta["event_step_calendar_days"], 6)

    def test_missing_epu_feature_observation_is_skipped_not_filled(self):
        epu, prices = self.make_market()
        anchor = model.BTC_START_DATE + dt.timedelta(days=18)
        del epu[anchor - dt.timedelta(days=5)]
        _, meta = model.build_events(epu, prices)
        self.assertGreater(meta["skipped"]["missing_epu_feature_window"], 0)

    def test_event_targets_are_nonoverlapping_and_matured(self):
        epu, prices = self.make_market()
        events, _ = model.build_events(epu, prices)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_walk_forward_requires_104_prior_matured_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(106):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "epu_date": signal - dt.timedelta(days=2),
                "signal_date": signal, "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "epu_5d_log_change": 0.2 * math.cos(index / 5.0),
                "target_semivariance_pct2": 1.0 + 0.2 * math.sin(index / 3.0),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)

    def test_decision_requires_both_periods_and_paired_interval(self):
        paired = {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05}
        self.assertEqual(model.decide({"n": 50, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": 1.0}, paired)[0], "BACKTESTED")
        self.assertEqual(model.decide({"n": 50, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[0], "INCONCLUSIVE")
        rejected = {"ci_95_low_bp2": -0.2, "ci_95_high_bp2": -0.01}
        self.assertEqual(model.decide({"n": 50, "rmse_improvement_pct": -2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, rejected)[0], "REJECTED")

    def test_update_documents_is_idempotent_and_preserves_existing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = __import__("pathlib").Path(directory)
            registry, prereg = root / "HYPOTHESIS-REGISTRY.md", root / "PREREG.md"
            registry.write_text(
                "# Registry\n\n| Hypothesis ID | Status | Mechanism | Data | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n"
                "| EXISTING-ID | REJECTED | Preserve | Existing scope | Existing result | old.md |\n",
                encoding="utf-8",
            )
            prereg.write_text("# Preregistration\n\n- **Initial status:** PREREGISTERED\n", encoding="utf-8")
            result = {
                "status": "INCONCLUSIVE", "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True, "data_scope": "synthetic scope",
                "summary_metrics": {"validation_n": 40, "test_n": 80},
                "paired_squared_loss_bootstrap": {"ci_95_low_bp2": -0.1, "ci_95_high_bp2": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            content = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING-ID | REJECTED |", content)
            self.assertEqual(content.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Initial status:** INCONCLUSIVE\n", prereg_text)
            self.assertEqual(prereg_text.count("## Empirical disposition"), 1)


if __name__ == "__main__":
    unittest.main()
