from __future__ import annotations

import datetime as dt
import math
import unittest

import anfci_tightening_sp500_volatility as model


class AnfciTighteningTests(unittest.TestCase):
    def business_dates(self, start: dt.date, count: int) -> list[dt.date]:
        dates = []
        day = start
        while len(dates) < count:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        return dates

    def test_parse_fred_accepts_negative_anfci_and_skips_missing(self):
        body = (
            "observation_date,ANFCI\n"
            "2026-10-30,-0.48\n"
            "2026-11-06,.\n"
            "2026-11-13,-0.50\n"
        ).encode()
        parsed = model.parse_fred_series(body, "ANFCI")
        self.assertEqual(len(parsed), 2)
        self.assertAlmostEqual(parsed[dt.date(2026, 10, 30)], -0.48)

    def test_parse_fred_rejects_duplicate_dates(self):
        body = (
            "observation_date,ANFCI\n"
            "2026-10-30,-0.48\n"
            "2026-10-30,-0.49\n"
        ).encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(body, "ANFCI")

    def test_weekly_release_lag_and_next_five_sessions(self):
        prices_dates = self.business_dates(dt.date(2016, 11, 1), 1200)
        prices = {date: 100.0 + i * 0.03 + math.sin(i / 7.0) for i, date in enumerate(prices_dates)}
        vix = {date: 18.0 + 2.0 * math.sin(i / 17.0) for i, date in enumerate(prices_dates)}
        first_friday = dt.date(2017, 1, 6)
        week_ends = [first_friday + dt.timedelta(days=7 * i) for i in range(60)]
        anfci = {date: -0.5 + 0.02 * math.sin(i / 3.0) + i * 0.0005 for i, date in enumerate(week_ends)}
        events, meta = model.build_events(anfci, prices, vix)
        self.assertGreater(len(events), 40)
        first = events[0]
        self.assertEqual(first["signal_date"], week_ends[4] + dt.timedelta(days=7))
        signal_index = prices_dates.index(first["signal_date"])
        self.assertEqual(first["target_start_date"], prices_dates[signal_index + 1])
        self.assertEqual(first["target_end_date"], prices_dates[signal_index + 5])
        self.assertAlmostEqual(first["anfci_4w_change"], anfci[week_ends[4]] - anfci[week_ends[0]])
        for previous, current in zip(events, events[1:]):
            self.assertLessEqual(previous["target_end_date"], current["signal_date"])
        self.assertEqual(meta["release_lag_days"], 7)

    def test_missing_vix_is_not_forward_filled(self):
        prices_dates = self.business_dates(dt.date(2016, 11, 1), 1000)
        prices = {date: 100.0 + i * 0.02 + math.sin(i / 9.0) for i, date in enumerate(prices_dates)}
        vix = {date: 20.0 for date in prices_dates}
        first_friday = dt.date(2017, 1, 6)
        week_ends = [first_friday + dt.timedelta(days=7 * i) for i in range(30)]
        anfci = {date: -0.4 + 0.01 * math.sin(i) for i, date in enumerate(week_ends)}
        missing_signal = week_ends[10] + dt.timedelta(days=7)
        vix.pop(missing_signal)
        events, meta = model.build_events(anfci, prices, vix)
        self.assertEqual(meta["skipped"]["missing_vix_on_signal_date"], 1)
        self.assertNotIn(missing_signal, [row["signal_date"] for row in events])

    def test_irregular_weekly_gap_does_not_create_four_week_feature(self):
        prices_dates = self.business_dates(dt.date(2016, 11, 1), 1200)
        prices = {date: 100.0 + i * 0.02 + math.sin(i / 11.0) for i, date in enumerate(prices_dates)}
        vix = {date: 19.0 for date in prices_dates}
        first_friday = dt.date(2017, 1, 6)
        week_ends = [first_friday + dt.timedelta(days=7 * i) for i in range(50)]
        anfci = {date: -0.3 + 0.01 * math.sin(i / 2.0) for i, date in enumerate(week_ends) if i != 20}
        _, meta = model.build_events(anfci, prices, vix)
        self.assertGreater(meta["skipped"]["irregular_weekly_feature_window"], 0)

    def make_events(self, count: int) -> list[dict]:
        events = []
        start = dt.date(2020, 1, 3)
        for index in range(count):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "week_end_date": signal - dt.timedelta(days=7),
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=3),
                "target_end_date": signal + dt.timedelta(days=7),
                "target_bp": 0.2 + 0.01 * math.sin(index / 3.0) + index * 0.0001,
                "target_rv_pct": 1.0 + 0.02 * math.sin(index / 4.0),
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "anfci_4w_change": 0.05 * math.sin(index / 5.0) + (index % 3) * 0.002,
            })
        return events

    def test_walk_forward_requires_104_fully_matured_events(self):
        events = self.make_events(model.MODEL_WINDOW + 2)
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_target_ending_on_current_signal(self):
        events = self.make_events(model.MODEL_WINDOW + 1)
        self.assertEqual(model.walk_forward_predictions(events), [])

    def test_decision_does_not_promote_without_minimum_sample(self):
        validation = {"n": 29, "baseline": {"rmse_log1p_rv": 1.0}, "augmented": {"rmse_log1p_rv": 0.5}}
        test = {"n": 29, "baseline": {"rmse_log1p_rv": 1.0}, "augmented": {"rmse_log1p_rv": 0.5}}
        status, _ = model.decide(validation, test, {"ci_95_low": 0.1})
        self.assertEqual(status, "INCONCLUSIVE")

    def test_source_coverage_accepts_fresh_weekly_index_and_synchronized_prices(self):
        weekly_dates = []
        day = dt.date(2017, 2, 17)
        while day <= dt.date(2026, 11, 20):
            weekly_dates.append(day)
            day += dt.timedelta(days=7)
        daily_dates = []
        day = dt.date(2016, 11, 25)
        while day <= dt.date(2026, 11, 25):
            if day.weekday() < 5:
                daily_dates.append(day)
            day += dt.timedelta(days=1)
        series = {
            "ANFCI": {date: -0.5 for date in weekly_dates},
            "SP500": {date: 100.0 + i for i, date in enumerate(daily_dates)},
            "VIXCLS": {date: 20.0 for date in daily_dates},
        }
        coverage = model.validate_source_coverage(series, dt.date(2026, 11, 26))
        self.assertEqual(coverage["ANFCI"]["last_date"], "2026-11-20")
        self.assertEqual(coverage["SP500"]["last_date"], "2026-11-25")

    def test_source_coverage_rejects_non_friday_weekly_observation(self):
        weekly_dates = []
        day = dt.date(2017, 2, 17)
        while day <= dt.date(2026, 11, 20):
            weekly_dates.append(day)
            day += dt.timedelta(days=7)
        daily_dates = []
        day = dt.date(2016, 11, 25)
        while day <= dt.date(2026, 11, 25):
            if day.weekday() < 5:
                daily_dates.append(day)
            day += dt.timedelta(days=1)
        series = {
            "ANFCI": {date: -0.5 for date in weekly_dates},
            "SP500": {date: 100.0 + i for i, date in enumerate(daily_dates)},
            "VIXCLS": {date: 20.0 for date in daily_dates},
        }
        series["ANFCI"][dt.date(2026, 11, 19)] = -0.4
        with self.assertRaisesRegex(ValueError, "weekly-ending-Friday"):
            model.validate_source_coverage(series, dt.date(2026, 11, 26))

    def test_source_coverage_rejects_stale_weekly_index(self):
        weekly_dates = []
        day = dt.date(2017, 2, 17)
        while day <= dt.date(2026, 11, 13):
            weekly_dates.append(day)
            day += dt.timedelta(days=7)
        daily_dates = self.business_dates(dt.date(2016, 11, 25), 2600)
        daily_dates = [date for date in daily_dates if date <= dt.date(2026, 11, 24)]
        series = {
            "ANFCI": {date: -0.5 for date in weekly_dates},
            "SP500": {date: 100.0 + i for i, date in enumerate(daily_dates)},
            "VIXCLS": {date: 20.0 for date in daily_dates},
        }
        with self.assertRaisesRegex(ValueError, "ANFCI is stale"):
            model.validate_source_coverage(series, dt.date(2026, 11, 26))


if __name__ == "__main__":
    unittest.main()
