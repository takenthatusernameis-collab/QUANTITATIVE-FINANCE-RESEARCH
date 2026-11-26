from __future__ import annotations

import datetime as dt
import math
import unittest

import sofr_effr_repo_premium_sp500_rv as model


class SofrEffrRepoPremiumTests(unittest.TestCase):
    def business_dates(self, start: dt.date, end: dt.date) -> list[dt.date]:
        dates = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        return dates

    def test_parse_fred_accepts_missing_observations_and_positive_rates(self):
        body = (
            "observation_date,SOFR\n"
            "2026-11-20,3.92\n"
            "2026-11-23,.\n"
            "2026-11-24,3.91\n"
        ).encode()
        parsed = model.parse_fred_series(body, "SOFR", positive_required=True)
        self.assertEqual(len(parsed), 2)
        self.assertAlmostEqual(parsed[dt.date(2026, 11, 20)], 3.92)

    def test_parse_fred_rejects_duplicate_dates_and_nonpositive_rates(self):
        duplicate = (
            "observation_date,EFFR\n"
            "2026-11-20,3.88\n"
            "2026-11-20,3.89\n"
        ).encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(duplicate, "EFFR", positive_required=True)
        nonpositive = (
            "observation_date,SOFR\n"
            "2026-11-20,0\n"
        ).encode()
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_fred_series(nonpositive, "SOFR", positive_required=True)

    def make_market(self, count=500):
        dates = []
        day = dt.date(2018, 4, 3)
        while len(dates) < count:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        prices = {
            date: 2500.0 + i * 0.2 + 8.0 * math.sin(i / 13.0)
            for i, date in enumerate(dates)
        }
        vix = {
            date: 18.0 + 2.5 * math.sin(i / 17.0) + 0.3 * math.cos(i / 7.0)
            for i, date in enumerate(dates)
        }
        sofr = {date: 4.0 + i * 0.001 + 0.05 * math.sin(i / 8.0) for i, date in enumerate(dates)}
        effr = {date: 3.9 + i * 0.0007 + 0.03 * math.cos(i / 11.0) for i, date in enumerate(dates)}
        return dates, prices, vix, sofr, effr

    def test_signal_uses_strictly_prior_common_rate_and_five_observation_change(self):
        dates, prices, vix, sofr, effr = self.make_market()
        events, meta = model.build_events(sofr, effr, prices, vix)
        self.assertGreater(len(events), 50)
        first = events[0]
        signal_index = dates.index(first["signal_date"])
        self.assertEqual(first["rate_observation_date"], dates[signal_index - 1])
        self.assertLess(first["rate_observation_date"], first["signal_date"])
        start_rate_date = dates[signal_index - 6]
        self.assertEqual(first["rate_feature_start_date"], start_rate_date)
        spread_now = (sofr[dates[signal_index - 1]] - effr[dates[signal_index - 1]]) * 100.0
        spread_then = (sofr[start_rate_date] - effr[start_rate_date]) * 100.0
        self.assertAlmostEqual(first["repo_spread_5obs_change_bp"], spread_now - spread_then)
        self.assertEqual(meta["event_spacing_sp500_observations"], 6)

    def test_signal_does_not_use_same_date_rates_even_when_present(self):
        dates, prices, vix, sofr, effr = self.make_market()
        events, _ = model.build_events(sofr, effr, prices, vix)
        self.assertTrue(events)
        for event in events:
            self.assertLess(event["rate_observation_date"], event["signal_date"])

    def test_unmatched_rate_dates_are_not_forward_filled(self):
        dates, prices, vix, sofr, effr = self.make_market()
        effr.pop(dates[19])
        events, _ = model.build_events(sofr, effr, prices, vix)
        self.assertTrue(events)
        self.assertEqual(events[0]["signal_date"], dates[20])
        self.assertEqual(events[0]["rate_observation_date"], dates[18])

    def test_stale_prior_rate_observations_are_skipped(self):
        dates, prices, vix, sofr, effr = self.make_market()
        for day in dates[15:]:
            sofr.pop(day, None)
            effr.pop(day, None)
        events, meta = model.build_events(sofr, effr, prices, vix)
        self.assertEqual(events, [])
        self.assertGreater(meta["skipped"]["stale_common_rate_observation"], 0)

    def test_missing_vix_is_not_forward_filled(self):
        dates, prices, vix, sofr, effr = self.make_market()
        missing_signal = dates[20]
        vix.pop(missing_signal)
        events, meta = model.build_events(sofr, effr, prices, vix)
        self.assertEqual(meta["skipped"]["missing_vix_on_signal_date"], 1)
        self.assertNotIn(missing_signal, [row["signal_date"] for row in events])

    def test_event_target_windows_do_not_overlap(self):
        dates, prices, vix, sofr, effr = self.make_market()
        events, _ = model.build_events(sofr, effr, prices, vix)
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["signal_date"])
            self.assertEqual(
                (dates.index(current["signal_date"]) - dates.index(previous["signal_date"])),
                6,
            )

    def test_source_coverage_accepts_fresh_synchronized_daily_series(self):
        dates = self.business_dates(dt.date(2018, 4, 3), dt.date(2026, 11, 25))
        series = {
            name: {date: 3.0 + i * 0.0001 for i, date in enumerate(dates)}
            for name in model.SERIES
        }
        coverage = model.validate_source_coverage(series, dt.date(2026, 11, 26))
        self.assertEqual(coverage["SOFR"]["last_date"], "2026-11-25")
        self.assertEqual(coverage["EFFR"]["last_date"], "2026-11-25")
        self.assertEqual(coverage["SP500"]["last_date"], "2026-11-25")

    def test_source_coverage_rejects_stale_funding_data(self):
        dates = self.business_dates(dt.date(2018, 4, 3), dt.date(2026, 11, 25))
        rates = [date for date in dates if date <= dt.date(2026, 11, 10)]
        prices = [date for date in dates if date <= dt.date(2026, 11, 25)]
        series = {
            "SOFR": {date: 4.0 for date in rates},
            "EFFR": {date: 3.9 for date in rates},
            "SP500": {date: 5000.0 for date in prices},
            "VIXCLS": {date: 20.0 for date in prices},
        }
        with self.assertRaisesRegex(ValueError, "SOFR/EFFR common observations are stale"):
            model.validate_source_coverage(series, dt.date(2026, 11, 26))

    def make_events(self, count: int) -> list[dict]:
        events = []
        start = dt.date(2020, 1, 3)
        for index in range(count):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "signal_date": signal,
                "rate_observation_date": signal - dt.timedelta(days=1),
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=7),
                "target_bp": 0.2 + 0.01 * math.sin(index / 3.0) + index * 0.0001,
                "target_rv_pct": 1.0 + 0.02 * math.sin(index / 4.0),
                "pre_rv5_log": 0.1 + (index % 11) * 0.01,
                "pre_rv20_log": 0.2 + (index % 13) * 0.01,
                "log_vix": 2.5 + (index % 7) * 0.03,
                "repo_spread_5obs_change_bp": 0.05 * math.sin(index / 5.0) + (index % 3) * 0.002,
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
        status, _ = model.decide(validation, test, {"ci_95_low": 0.1})
        self.assertEqual(status, "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
