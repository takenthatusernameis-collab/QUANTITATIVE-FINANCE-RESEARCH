import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import baa10y_btc_downside_semivariance as model


class Baa10yBtcTests(unittest.TestCase):
    def make_market(self, weeks=180, extra_days=40):
        first_price = dt.date(2017, 8, 17)
        last_price = first_price + dt.timedelta(days=7 * weeks + extra_days)
        prices = {}
        day = first_price
        index = 0
        while day <= last_price:
            prices[day] = 10_000.0 * math.exp(
                0.0002 * index + 0.025 * math.sin(index / 8.0) + 0.01 * math.sin(index / 2.7)
            )
            day += dt.timedelta(days=1)
            index += 1

        spread = {}
        day = dt.date(2017, 8, 1)
        index = 0
        while day <= last_price:
            if day.weekday() < 5:
                spread[day] = 2.0 + 0.0005 * index
                index += 1
            day += dt.timedelta(days=1)
        return spread, prices

    def test_parse_baa10y_accepts_fred_schema_and_skips_missing(self):
        body = (
            b"observation_date,BAA10Y\n"
            b"1986-01-02,2.34\n"
            b"1986-01-03,2.30\n"
            b"1986-01-06,.\n"
        )
        parsed = model.parse_baa10y(body)
        self.assertEqual(len(parsed), 2)
        self.assertAlmostEqual(parsed[dt.date(1986, 1, 2)], 2.34)

    def test_parse_baa10y_rejects_duplicate_and_weekend_rows(self):
        duplicate = (
            b"observation_date,BAA10Y\n"
            b"1986-01-02,2.34\n"
            b"1986-01-02,2.30\n"
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_baa10y(duplicate)
        weekend = b"observation_date,BAA10Y\n1986-01-04,2.34\n"
        with self.assertRaisesRegex(ValueError, "business day"):
            model.parse_baa10y(weekend)

    def test_event_uses_only_spread_observations_before_five_day_cutoff(self):
        spread, prices = self.make_market()
        events, meta = model.build_events(spread, prices)
        self.assertGreater(len(events), 100)
        first = events[0]
        self.assertLessEqual(first["baa_observation_date"], first["baa_cutoff_date"])
        self.assertEqual(
            (first["signal_date"] - first["baa_cutoff_date"]).days,
            model.RELEASE_LAG_DAYS,
        )
        self.assertLessEqual(
            (first["baa_cutoff_date"] - first["baa_observation_date"]).days,
            model.MAX_BAA_CUTOFF_AGE_DAYS,
        )
        spread_dates = sorted(spread)
        index = spread_dates.index(first["baa_observation_date"])
        expected = (
            spread[first["baa_observation_date"]] - spread[spread_dates[index - 5]]
        ) * 100.0
        self.assertAlmostEqual(first["baa_spread_change_5obs_bps"], expected)
        self.assertGreater(first["baa_spread_change_5obs_bps"], 0.0)
        self.assertEqual(meta["publication_lag_calendar_days"], 5)

    def test_weekly_events_have_non_overlapping_matured_targets(self):
        spread, prices = self.make_market()
        events, _ = model.build_events(spread, prices)
        for left, right in zip(events, events[1:]):
            self.assertEqual((right["signal_date"] - left["signal_date"]).days, 7)
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_stale_spread_observation_is_skipped_not_forward_filled(self):
        spread, prices = self.make_market()
        signal = next(day for day in sorted(prices) if day.weekday() == 2)
        cutoff = signal - dt.timedelta(days=model.RELEASE_LAG_DAYS)
        stale_days = [
            day for day in spread
            if cutoff - dt.timedelta(days=6) < day <= cutoff
        ]
        for day in stale_days:
            del spread[day]
        events, meta = model.build_events(spread, prices)
        self.assertGreater(meta["skipped"]["stale_spread_at_cutoff"], 0)
        self.assertNotIn(signal, [row["signal_date"] for row in events])

    def test_walk_forward_requires_104_fully_matured_prior_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        first_wednesday = start + dt.timedelta(days=(2 - start.weekday()) % 7)
        for index in range(106):
            signal = first_wednesday + dt.timedelta(days=7 * index)
            events.append({
                "signal_date": signal,
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "baa_spread_change_5obs_bps": 2.0 * math.cos(index / 5.0),
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

    def test_update_documents_is_idempotent_and_preserves_other_rows(self):
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
                "# Preregistration\n\n- **Status:** FEASIBILITY_CHECKED\n",
                encoding="utf-8",
            )
            result = {
                "status": "INCONCLUSIVE",
                "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True,
                "data_scope": "synthetic test scope",
                "summary_metrics": {"validation_n": 40, "test_n": 80},
                "paired_squared_loss_bootstrap": {"ci95_low": -0.1, "ci95_high": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            registry_text = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING-ID | REJECTED |", registry_text)
            self.assertEqual(registry_text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE\n", prereg_text)
            self.assertNotIn("INCONCLUSIVE — INCONCLUSIVE", prereg_text)


if __name__ == "__main__":
    unittest.main()
