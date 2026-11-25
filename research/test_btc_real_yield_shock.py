from __future__ import annotations

import datetime as dt
import math
import unittest

import btc_real_yield_shock as model


class BitcoinRealYieldShockTests(unittest.TestCase):
    def test_parse_fred_series_accepts_observation_date_and_skips_missing(self):
        rows = ["observation_date,CBBTCUSD"]
        day = dt.date(2016, 11, 25)
        count = 0
        while count < 1501:
            rows.append(f"{day.isoformat()},{'.' if count == 1 else 10000 + count}")
            day += dt.timedelta(days=1)
            count += 1
        parsed = model.parse_fred_series(("\n".join(rows) + "\n").encode(), "CBBTCUSD")
        self.assertEqual(len(parsed), 1500)
        self.assertNotIn(dt.date(2016, 11, 26), parsed)

    def test_parse_fred_series_accepts_negative_real_yields(self):
        rows = ["observation_date,DFII10"]
        day = dt.date(2016, 11, 25)
        for index in range(1501):
            value = 1.5 - index * 0.002
            rows.append(f"{day.isoformat()},{'.' if index == 1 else value}")
            day += dt.timedelta(days=1)
        parsed = model.parse_fred_series(("\n".join(rows) + "\n").encode(), "DFII10")
        self.assertEqual(len(parsed), 1500)
        self.assertLess(min(parsed.values()), 0.0)

    def test_parse_fred_series_rejects_duplicate_dates(self):
        rows = ["observation_date,DFII10"]
        day = dt.date(2016, 11, 25)
        for index in range(1500):
            rows.append(f"{day.isoformat()},{100 + index / 1000}")
            day += dt.timedelta(days=1)
        rows.append("2016-11-25,101")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(("\n".join(rows) + "\n").encode(), "DFII10")

    def test_parse_fred_series_rejects_nonpositive_bitcoin_observations(self):
        rows = ["observation_date,CBBTCUSD", "2016-11-25,0"]
        day = dt.date(2016, 11, 26)
        for index in range(1500):
            rows.append(f"{day.isoformat()},{100 + index / 1000}")
            day += dt.timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_fred_series(("\n".join(rows) + "\n").encode(), "CBBTCUSD")

    def test_bitcoin_returns_do_not_bridge_missing_calendar_days(self):
        prices = {
            dt.date(2020, 9, 10): 100.0,
            dt.date(2020, 9, 11): 101.0,
            dt.date(2020, 9, 13): 102.0,
            dt.date(2020, 9, 14): 103.0,
        }
        dates, returns = model.daily_log_returns(prices)
        self.assertIsNone(returns[0])
        self.assertIsNotNone(returns[1])
        self.assertIsNone(returns[2])
        self.assertIsNotNone(returns[3])

    def _synthetic_prices(self, count=500):
        start = dt.date(2017, 1, 1)
        return {
            start + dt.timedelta(days=index):
                10000.0 * math.exp(0.0005 * index + 0.025 * math.sin(index / 13.0) + 0.01 * math.cos(index / 5.0))
            for index in range(count)
        }

    def _synthetic_real_yields(self, start=dt.date(2017, 1, 1), end=dt.date(2018, 6, 1)):
        values = {}
        day = start
        index = 0
        while day <= end:
            if day.weekday() < 5:
                values[day] = 1.0 - 0.006 * index + 0.002 * math.sin(index / 4.0)
                index += 1
            day += dt.timedelta(days=1)
        return values

    def test_event_uses_strictly_prior_real_yield_observation_and_nonoverlapping_targets(self):
        prices = self._synthetic_prices()
        real_yields = self._synthetic_real_yields()
        events, meta = model.build_events(prices, real_yields)
        self.assertGreater(len(events), 20)
        self.assertEqual(events[0]["signal_date"], dt.date(2017, 1, 21))
        self.assertEqual(events[0]["real_yield_observation_date"], dt.date(2017, 1, 20))
        for event in events:
            self.assertLess(event["real_yield_observation_date"], event["signal_date"])
            yield_dates = sorted(real_yields)
            position = yield_dates.index(event["real_yield_observation_date"])
            old_date = yield_dates[position - 5]
            expected_change_bp = 100.0 * (real_yields[event["real_yield_observation_date"]] - real_yields[old_date])
            self.assertAlmostEqual(event["real_yield_change_bp"], expected_change_bp)
            self.assertLess(event["target_start_date"], event["target_end_date"])
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["target_start_date"])
        self.assertEqual(meta["events"], len(events))
        self.assertEqual(meta["skipped"]["overlapping_target_window"], 0)

    def test_stale_real_yield_observations_are_rejected(self):
        prices = self._synthetic_prices()
        all_yields = self._synthetic_real_yields()
        cutoff = dt.date(2017, 1, 13)
        stale_yields = {day: value for day, value in all_yields.items() if day <= cutoff}
        events, meta = model.build_events(prices, stale_yields)
        self.assertGreater(meta["skipped"]["stale_real_yield_observation"], 0)
        self.assertEqual(events, [])

    def test_same_date_real_yield_observation_is_never_used(self):
        prices = self._synthetic_prices()
        real_yields = self._synthetic_real_yields()
        events, _ = model.build_events(prices, real_yields)
        same_date_candidates = [
            event for event in events
            if event["signal_date"].weekday() < 5
            and event["signal_date"] in real_yields
        ]
        self.assertTrue(same_date_candidates)
        for event in same_date_candidates:
            self.assertLess(event["real_yield_observation_date"], event["signal_date"])

    def test_walk_forward_requires_104_fully_matured_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=6 * index)
            x1 = math.sin(index * 0.37)
            x2 = math.cos(index * 0.19)
            x3 = 1.0 + (index % 11) * 0.03
            x4 = 2.0 + (index % 13) * 0.02
            x5 = math.sin(index * 0.13) + math.cos(index * 0.07) * 0.2
            target = 0.4 * x1 - 0.2 * x2 + 0.3 * x3 + 0.1 * x4 - 0.5 * x5
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": target,
                "btc_mom5_pct": x1,
                "btc_mom20_pct": x2,
                "btc_rv5_pct": x3,
                "btc_rv20_pct": x4,
                "real_yield_change_bp": x5,
            })
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_target_ending_on_current_signal(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": float(index % 7),
                "btc_mom5_pct": math.sin(index * 0.37),
                "btc_mom20_pct": math.cos(index * 0.19),
                "btc_rv5_pct": 1.0 + (index % 11) * 0.03,
                "btc_rv20_pct": 2.0 + (index % 13) * 0.02,
                "real_yield_change_bp": math.sin(index * 0.13) + math.cos(index * 0.07) * 0.2,
            })
        current_signal = start + dt.timedelta(days=6 * model.MODEL_WINDOW)
        events[-1]["target_end_date"] = current_signal
        events.append({
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=5),
            "target_bp": 1.0,
            "btc_mom5_pct": 0.2,
            "btc_mom20_pct": -0.1,
            "btc_rv5_pct": 1.2,
            "btc_rv20_pct": 2.1,
            "real_yield_change_bp": 0.05,
        })
        self.assertEqual(model.walk_forward_predictions(events), [])

    def test_paired_loss_bootstrap_is_reproducible_and_favors_augmented(self):
        rows = []
        for index in range(60):
            target = float((index % 9) - 4)
            baseline_error = 2.0 + (index % 3) * 0.1
            augmented_error = 0.5 + (index % 2) * 0.1
            rows.append({
                "target_bp": target,
                "baseline_prediction_bp": target + baseline_error,
                "augmented_prediction_bp": target + augmented_error,
            })
        first = model.bootstrap_paired_loss(rows)
        second = model.bootstrap_paired_loss(rows)
        self.assertEqual(first, second)
        self.assertGreater(first["mean_baseline_minus_augmented_squared_error_pct2"], 0)
        self.assertGreater(first["ci_95_low_pct2"], 0)

    def test_decision_does_not_promote_when_paired_interval_crosses_zero(self):
        validation = {
            "n": 100,
            "baseline": {"rmse_pct": 2.0},
            "augmented": {"rmse_pct": 1.8},
        }
        test = {
            "n": 100,
            "baseline": {"rmse_pct": 2.0},
            "augmented": {"rmse_pct": 1.9},
        }
        paired = {"ci_95_low_pct2": -0.1, "ci_95_high_pct2": 0.2}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_decision_rejects_only_with_consistent_negative_evidence(self):
        validation = {
            "n": 100,
            "baseline": {"rmse_pct": 1.8},
            "augmented": {"rmse_pct": 2.0},
        }
        test = {
            "n": 100,
            "baseline": {"rmse_pct": 1.9},
            "augmented": {"rmse_pct": 2.1},
        }
        paired = {"ci_95_low_pct2": -0.4, "ci_95_high_pct2": -0.1}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "REJECTED")


if __name__ == "__main__":
    unittest.main()
