from __future__ import annotations

import datetime as dt
import math
import unittest

import jpy_carry_unwind_sp500_volatility as model


class JpyCarryUnwindVolatilityTests(unittest.TestCase):
    @staticmethod
    def business_dates(start: dt.date, count: int) -> list[dt.date]:
        dates = []
        day = start
        while len(dates) < count:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        return dates

    def test_parser_accepts_positive_fx_values_and_skips_missing(self):
        dates = self.business_dates(dt.date(2010, 1, 1), 1501)
        rows = [f"{date.isoformat()},{100 + i / 100}" for i, date in enumerate(dates)]
        rows[1] = f"{dates[1].isoformat()},."
        parsed = model.parse_fred_series(
            ("observation_date,DEXJPUS\n" + "\n".join(rows)).encode(),
            "DEXJPUS",
            positive_required=True,
        )
        self.assertEqual(len(parsed), 1500)
        self.assertNotIn(dates[1], parsed)

    def test_parser_rejects_duplicate_dates(self):
        dates = self.business_dates(dt.date(2010, 1, 1), 1500)
        rows = [f"{date.isoformat()},100" for date in dates]
        rows.append(f"{dates[0].isoformat()},101")
        body = "observation_date,DEXJPUS\n" + "\n".join(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(body.encode(), "DEXJPUS")

    def test_parser_rejects_nonpositive_fx(self):
        dates = self.business_dates(dt.date(2010, 1, 1), 1500)
        rows = [f"{date.isoformat()},{0 if i == 0 else 100}" for i, date in enumerate(dates)]
        body = "observation_date,DEXJPUS\n" + "\n".join(rows)
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_fred_series(body.encode(), "DEXJPUS")

    def test_falling_jpy_per_usd_quote_is_positive_yen_appreciation(self):
        dates = self.business_dates(dt.date(2020, 1, 1), 6)
        fx = {date: 150.0 - i * 0.5 for i, date in enumerate(dates)}
        shock, source_date, error = model.yen_appreciation_shock(fx, dates[-1] + dt.timedelta(days=1))
        self.assertIsNone(error)
        self.assertEqual(source_date, dates[-1])
        self.assertGreater(shock, 0.0)
        self.assertAlmostEqual(shock, -100.0 * math.log(147.5 / 150.0), places=10)

    def test_rising_jpy_per_usd_quote_has_zero_yen_appreciation_shock(self):
        dates = self.business_dates(dt.date(2020, 1, 1), 6)
        fx = {date: 145.0 + i * 0.5 for i, date in enumerate(dates)}
        shock, _, error = model.yen_appreciation_shock(fx, dates[-1] + dt.timedelta(days=1))
        self.assertIsNone(error)
        self.assertEqual(shock, 0.0)

    def test_fx_feature_excludes_same_date_observation(self):
        dates = self.business_dates(dt.date(2020, 1, 1), 7)
        fx = {date: 150.0 for date in dates[:6]}
        fx[dates[6]] = 100.0
        shock, source_date, error = model.yen_appreciation_shock(fx, dates[6])
        self.assertIsNone(error)
        self.assertEqual(source_date, dates[5])
        self.assertEqual(shock, 0.0)

    def test_fx_feature_rejects_insufficient_history(self):
        dates = self.business_dates(dt.date(2020, 1, 1), 5)
        fx = {date: 150.0 for date in dates}
        shock, source_date, error = model.yen_appreciation_shock(fx, dates[-1] + dt.timedelta(days=1))
        self.assertIsNone(shock)
        self.assertEqual(source_date, dates[-1])
        self.assertEqual(error, "insufficient_fx_history")

    def test_fx_feature_rejects_large_observation_gaps(self):
        dates = self.business_dates(dt.date(2020, 1, 1), 10)
        fx = {date: 150.0 + i for i, date in enumerate(dates) if i not in {3, 4, 5}}
        shock, _, error = model.yen_appreciation_shock(fx, dates[-1] + dt.timedelta(days=1))
        self.assertIsNone(shock)
        self.assertIn(error, {"fx_window_too_wide", "fx_observation_gap"})

    def test_event_uses_prior_fx_data_and_next_five_sessions(self):
        dates = self.business_dates(dt.date(2017, 1, 2), 500)
        prices = {date: 100.0 + i * 0.08 + math.sin(i / 7.0) for i, date in enumerate(dates)}
        vix = {date: 18.0 + 2.0 * math.sin(i / 17.0) for i, date in enumerate(dates)}
        fx_dates = self.business_dates(dt.date(2016, 11, 1), 650)
        fx = {date: 115.0 + i * 0.02 + 0.2 * math.sin(i / 9.0) for i, date in enumerate(fx_dates)}
        events, meta = model.build_events(prices, vix, fx)
        self.assertGreater(len(events), 20)
        first = events[0]
        self.assertLess(first["fx_source_date"], first["signal_date"])
        self.assertEqual(first["target_start_date"], dates[21])
        self.assertEqual(first["target_end_date"], dates[25])
        self.assertGreaterEqual(first["yen_appreciation_5_pct"], 0.0)
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["signal_date"])

    def test_missing_vix_is_not_forward_filled(self):
        dates = self.business_dates(dt.date(2017, 1, 2), 500)
        prices = {date: 100.0 + i * 0.05 + math.sin(i / 5.0) for i, date in enumerate(dates)}
        vix = {date: 20.0 for date in dates if date != dates[20]}
        fx_dates = self.business_dates(dt.date(2016, 11, 1), 650)
        fx = {date: 150.0 + i * 0.01 for i, date in enumerate(fx_dates)}
        _, meta = model.build_events(prices, vix, fx)
        self.assertGreater(meta["skipped"]["missing_vix_on_signal_date"], 0)

    def test_walk_forward_requires_104_fully_matured_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_log_rv": 0.1 + index * 0.001,
                "target_rv_pct": 1.0 + index * 0.01,
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "yen_appreciation_5_log": 0.1 + (index % 9) * 0.02,
                "yen_appreciation_5_pct": 1.0 + (index % 9) * 0.1,
            })
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_target_ending_on_current_signal(self):
        events = []
        start = dt.date(2020, 1, 1)
        current_signal = start + dt.timedelta(days=6 * model.MODEL_WINDOW)
        for index in range(model.MODEL_WINDOW):
            signal = start + dt.timedelta(days=6 * index)
            end = current_signal if index == model.MODEL_WINDOW - 1 else signal + dt.timedelta(days=5)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": end,
                "target_log_rv": 0.1 + index * 0.001,
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "yen_appreciation_5_log": 0.1 + (index % 9) * 0.02,
                "yen_appreciation_5_pct": 1.0 + (index % 9) * 0.1,
                "target_rv_pct": 1.2,
            })
        current = {
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=5),
            "target_log_rv": 0.3,
            "target_rv_pct": 1.3,
            "pre_rv5_log": 0.3,
            "pre_rv20_log": 0.4,
            "log_vix": 2.8,
            "yen_appreciation_5_log": 0.1,
            "yen_appreciation_5_pct": 1.2,
        }
        self.assertEqual(model.walk_forward_predictions(events + [current]), [])

    def test_decision_requires_minimum_sample_and_positive_inference(self):
        validation = {
            "n": 29,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.5},
        }
        test = {
            "n": 29,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.5},
        }
        paired = {"ci_95_low": 0.1, "ci_95_high": 0.2}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_source_coverage_rejects_stale_synchronized_sources(self):
        stale = {dt.date(2026, 11, 10): 1.0}
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_source_coverage({"SP500": stale, "VIXCLS": stale, "DEXJPUS": stale})

    def test_source_coverage_accepts_recent_synchronized_sources(self):
        recent = {dt.date(2026, 11, 23): 1.0}
        coverage = model.validate_source_coverage({"SP500": recent, "VIXCLS": recent, "DEXJPUS": recent})
        self.assertEqual(coverage["DEXJPUS"]["last_date"], "2026-11-23")


if __name__ == "__main__":
    unittest.main()
