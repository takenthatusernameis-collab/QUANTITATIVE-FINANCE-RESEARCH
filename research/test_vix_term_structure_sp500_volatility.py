from __future__ import annotations

import datetime as dt
import math
import unittest

import vix_term_structure_sp500_volatility as model


class VixTermStructureTests(unittest.TestCase):
    def test_parse_fred_series_accepts_observation_date_and_skips_missing(self):
        dates = []
        day = dt.date(2010, 1, 1)
        while len(dates) < 1501:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        body = "observation_date,VIXCLS\n" + "\n".join(
            f"{date.isoformat()},{'.' if i == 1 else 12.0 + i / 1000}" for i, date in enumerate(dates)
        )
        parsed = model.parse_fred_series(body.encode(), "VIXCLS")
        self.assertEqual(len(parsed), 1500)
        self.assertNotIn(dates[1], parsed)

    def test_parse_fred_series_rejects_duplicate_dates(self):
        dates = []
        day = dt.date(2010, 1, 1)
        while len(dates) < 1500:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        rows = [f"{date.isoformat()},20" for date in dates]
        rows.append(f"{dates[0].isoformat()},21")
        body = "observation_date,VIXCLS\n" + "\n".join(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(body.encode(), "VIXCLS")

    def test_daily_returns_break_after_long_market_closure(self):
        prices = {
            dt.date(2020, 9, 10): 100.0,
            dt.date(2020, 9, 11): 101.0,
            dt.date(2020, 9, 21): 99.0,
            dt.date(2020, 9, 22): 100.0,
        }
        dates, returns = model.daily_log_returns(prices)
        self.assertIsNone(returns[0])
        self.assertIsNotNone(returns[1])
        self.assertIsNone(returns[2])
        self.assertIsNotNone(returns[3])

    def test_event_uses_prior_close_and_next_five_sessions(self):
        dates = []
        day = dt.date(2017, 1, 2)
        while len(dates) < 500:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        prices = {date: 100.0 + i * 0.08 + math.sin(i / 7.0) for i, date in enumerate(dates)}
        vix = {date: 18.0 + 2.0 * math.sin(i / 17.0) for i, date in enumerate(dates)}
        vxv = {date: 20.0 + 1.5 * math.cos(i / 19.0) for i, date in enumerate(dates)}
        events, meta = model.build_events(prices, vix, vxv)
        self.assertGreater(len(events), 20)
        first = events[0]
        self.assertEqual(first["signal_date"], dates[20])
        self.assertEqual(first["target_start_date"], dates[21])
        self.assertEqual(first["target_end_date"], dates[25])
        self.assertEqual(first["inverted"], first["vix"] >= first["vxv"])
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["signal_date"])
            self.assertGreater(previous["target_end_date"], previous["target_start_date"])

    def test_missing_option_index_is_not_forward_filled(self):
        dates = []
        day = dt.date(2017, 1, 2)
        while len(dates) < 500:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        prices = {date: 100.0 + i * 0.05 + math.sin(i / 5.0) for i, date in enumerate(dates)}
        vix = {date: 20.0 for date in dates}
        vxv = {date: 22.0 for date in dates if date != dates[20]}
        events, meta = model.build_events(prices, vix, vxv)
        self.assertEqual(meta["skipped"]["missing_vxv_on_signal_date"], 1)
        self.assertNotEqual(events[0]["signal_date"], dates[20])

    def test_walk_forward_requires_104_fully_matured_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.1 + index * 0.001,
                "target_rv_pct": 1.0 + index * 0.01,
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "term_slope": -0.1 + (index % 9) * 0.02,
                "inverted": index % 5 == 0,
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
                "target_bp": 0.1 + index * 0.001,
                "target_rv_pct": 1.0 + index * 0.01,
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "term_slope": -0.1 + (index % 9) * 0.02,
                "inverted": index % 5 == 0,
            })
        current = {
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=5),
            "target_bp": 0.3,
            "target_rv_pct": 1.3,
            "pre_rv5_log": 0.3,
            "pre_rv20_log": 0.4,
            "log_vix": 2.8,
            "term_slope": 0.1,
            "inverted": True,
        }
        self.assertEqual(model.walk_forward_predictions(events + [current]), [])

    def test_decision_does_not_promote_without_minimum_sample(self):
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
        paired = {"ci_95_low": 0.1}
        inversion = {"high_minus_contango_mean_rv_pct": 0.5, "ci_95_low_rv_pct": 0.1}
        status, _ = model.decide(validation, test, paired, inversion)
        self.assertEqual(status, "INCONCLUSIVE")


    def test_source_coverage_rejects_stale_but_synchronized_sources(self):
        stale = {dt.date(2026, 11, 10): 1.0}
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_source_coverage({
                "SP500": stale,
                "VIXCLS": stale,
                "VXVCLS": stale,
            })

    def test_source_coverage_accepts_recent_synchronized_sources(self):
        recent = {dt.date(2026, 11, 23): 1.0}
        coverage = model.validate_source_coverage({
            "SP500": recent,
            "VIXCLS": recent,
            "VXVCLS": recent,
        })
        self.assertEqual(coverage["SP500"]["last_date"], "2026-11-23")


if __name__ == "__main__":
    unittest.main()
