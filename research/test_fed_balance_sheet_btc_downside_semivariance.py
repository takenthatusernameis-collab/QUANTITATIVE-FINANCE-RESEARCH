import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fed_balance_sheet_btc_downside_semivariance as model


class FedBalanceSheetBtcTests(unittest.TestCase):
    def make_market(self, weeks=180, extra_days=40):
        first_week = dt.date(2017, 8, 16)
        assets = {
            first_week + dt.timedelta(days=7 * i):
            4_500_000.0 * math.exp(-0.0003 * i + 0.002 * math.sin(i / 9.0))
            for i in range(weeks)
        }
        first_price = dt.date(2017, 8, 17)
        days = (first_week + dt.timedelta(days=7 * (weeks - 1)) - first_price).days + extra_days
        prices = {
            first_price + dt.timedelta(days=i):
            10_000.0 * math.exp(0.0002 * i + 0.025 * math.sin(i / 8.0) + 0.01 * math.sin(i / 2.7))
            for i in range(days + 1)
        }
        return assets, prices

    def test_parse_walcl_accepts_fred_schema_and_skips_missing(self):
        body = (
            b"observation_date,WALCL\n"
            b"2017-08-16,4500000\n"
            b"2017-08-23,4490000\n"
            b"2017-08-30,.\n"
        )
        parsed = model.parse_walcl(body)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[dt.date(2017, 8, 16)], 4_500_000.0)

    def test_parse_walcl_rejects_duplicate_or_non_wednesday_rows(self):
        duplicate = b"observation_date,WALCL\n2017-08-16,4500000\n2017-08-16,4490000\n"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_walcl(duplicate)
        wrong_day = b"observation_date,WALCL\n2017-08-17,4500000\n"
        with self.assertRaisesRegex(ValueError, "Wednesday"):
            model.parse_walcl(wrong_day)

    def test_four_week_contraction_is_positive_and_strictly_lagged(self):
        assets, prices = self.make_market()
        events, meta = model.build_events(assets, prices)
        self.assertGreater(len(events), 100)
        first = events[0]
        self.assertEqual(first["signal_date"], first["balance_sheet_week"] + dt.timedelta(days=7))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        week_dates = sorted(assets)
        index = week_dates.index(first["balance_sheet_week"])
        expected = -100.0 * math.log(assets[week_dates[index]] / assets[week_dates[index - 4]])
        self.assertAlmostEqual(first["fed_assets_contraction_4w_pct"], expected)
        self.assertGreater(first["fed_assets_contraction_4w_pct"], 0.0)
        self.assertEqual(meta["release_lag_days"], 7)

    def test_event_targets_do_not_overlap_and_are_matured(self):
        assets, prices = self.make_market()
        events, _ = model.build_events(assets, prices)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_irregular_weekly_window_is_skipped_not_filled(self):
        assets, prices = self.make_market()
        del assets[sorted(assets)[30]]
        _, meta = model.build_events(assets, prices)
        self.assertGreater(meta["skipped"]["irregular_weekly_window"], 0)

    def test_walk_forward_requires_104_fully_matured_prior_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(106):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "signal_date": signal, "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "fed_assets_contraction_4w_pct": 0.2 * math.cos(index / 5.0),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)

    def test_decision_requires_both_periods_and_paired_interval(self):
        validation = {"n": 50, "rmse_improvement_pct": 2.0}
        test = {"n": 100, "rmse_improvement_pct": 1.0}
        paired = {"ci95_low": 0.01, "ci95_high": 0.05}
        self.assertEqual(model.decide(validation, test, paired)[0], "BACKTESTED")
        self.assertEqual(
            model.decide(validation, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[0],
            "INCONCLUSIVE",
        )
        rejected = {"ci95_low": -0.2, "ci95_high": -0.01}
        self.assertEqual(
            model.decide(
                {"n": 50, "rmse_improvement_pct": -2.0},
                {"n": 100, "rmse_improvement_pct": -1.0},
                rejected,
            )[0],
            "REJECTED",
        )

    def test_update_documents_is_idempotent_and_preserves_other_registry_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, prereg = root / "HYPOTHESIS-REGISTRY.md", root / "PREREG.md"
            registry.write_text(
                "# Registry\n\n| Hypothesis ID | Status | Mechanism | Data | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n"
                "| EXISTING-ID | REJECTED | Existing row | Existing data | Preserve | existing.md |\n",
                encoding="utf-8",
            )
            prereg.write_text("# Preregistration\n\n- **Status:** FEASIBILITY_CHECKED\n", encoding="utf-8")
            result = {
                "status": "INCONCLUSIVE", "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True, "data_scope": "synthetic test scope",
                "summary_metrics": {"validation_n": 40, "test_n": 80},
                "paired_squared_loss_bootstrap": {"ci95_low": -0.1, "ci95_high": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            text = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING-ID | REJECTED |", text)
            self.assertEqual(text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE\n", prereg_text)
            self.assertNotIn("INCONCLUSIVE — INCONCLUSIVE", prereg_text)


if __name__ == "__main__":
    unittest.main()
