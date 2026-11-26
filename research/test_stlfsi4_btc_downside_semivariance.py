from __future__ import annotations
import datetime as dt
import json
import math
import unittest
import stlfsi4_btc_downside_semivariance as model


class STLFSI4BitcoinTests(unittest.TestCase):
    def test_fred_parser_accepts_negative_values_and_skips_missing(self):
        body = b"observation_date,STLFSI4\n2026-10-30,-0.48\n2026-11-06,.\n2026-11-13,0.12\n"
        values = model.parse_fred(body)
        self.assertEqual(len(values), 2)
        self.assertAlmostEqual(values[dt.date(2026, 10, 30)], -0.48)

    def test_fred_parser_rejects_duplicate_dates(self):
        body = b"observation_date,STLFSI4\n2026-10-30,-0.4\n2026-10-30,-0.3\n"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred(body)

    def kline(self, day, close, complete=True):
        open_ms = int(dt.datetime.combine(day, dt.time(), dt.timezone.utc).timestamp() * 1000)
        close_ms = open_ms + model.MS_PER_DAY - 1
        return [open_ms, str(close), str(close), str(close), str(close), "1", close_ms, "1", 1, "1", "1", "0"]

    def test_binance_parser_excludes_incomplete_current_candle(self):
        day = dt.date(2026, 11, 24)
        body = json.dumps([self.kline(day, 90000), self.kline(day + dt.timedelta(days=1), 91000, False)]).encode()
        now_ms = int(dt.datetime(2026, 11, 25, 12, tzinfo=dt.timezone.utc).timestamp() * 1000)
        self.assertEqual(list(model.parse_klines(body, now_ms)), [day])

    def test_binance_parser_rejects_non_utc_aligned_candle(self):
        row = self.kline(dt.date(2026, 11, 24), 90000)
        row[0] += 1
        with self.assertRaisesRegex(ValueError, "UTC day"):
            model.parse_klines(json.dumps([row]).encode(), 2_000_000_000_000)

    def test_downside_semivariance_is_one_sided_and_percent_squared(self):
        self.assertAlmostEqual(model.semi_var_pct2([-0.01, 0.02, -0.03, 0.0, 0.01]), 2.0)
        self.assertEqual(model.semi_var_pct2([0.01, 0.02]), 0.0)

    def make_market(self, days=1200, weeks=150):
        start = dt.date(2017, 8, 17)
        prices = {
            start + dt.timedelta(days=i):
            10000.0 * math.exp(0.0002 * i + 0.03 * math.sin(i / 9.0) + 0.01 * math.sin(i / 2.7))
            for i in range(days)
        }
        first_friday = dt.date(2017, 8, 18)
        stress = {
            first_friday + dt.timedelta(days=7 * i):
            -0.5 + i * 0.001 + 0.04 * math.sin(i / 4.0)
            for i in range(weeks)
        }
        return stress, prices

    def test_event_alignment_uses_seven_day_lag_and_next_five_returns(self):
        stress, prices = self.make_market()
        events, meta = model.build_events(stress, prices)
        self.assertGreater(len(events), 40)
        first = events[0]
        self.assertEqual(first["signal_date"], first["week_end_date"] + dt.timedelta(days=7))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        week_dates = sorted(stress)
        wi = week_dates.index(first["week_end_date"])
        self.assertAlmostEqual(first["stlfsi4_4w_change"], stress[week_dates[wi]] - stress[week_dates[wi - 4]])
        self.assertEqual(meta["release_lag_days"], 7)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_irregular_stress_week_is_skipped(self):
        stress, prices = self.make_market()
        stress.pop(sorted(stress)[30])
        _, meta = model.build_events(stress, prices)
        self.assertGreater(meta["skipped"]["irregular_stress_window"], 0)

    def test_walk_forward_uses_104_fully_matured_events(self):
        events, start = [], dt.date(2020, 1, 3)
        for i in range(106):
            signal = start + dt.timedelta(days=7 * i)
            events.append({
                "signal_date": signal, "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(i / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(i / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(i / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(i / 9.0),
                "stlfsi4_4w_change": 0.05 * math.cos(i / 5.0),
                "target_semivariance_pct2": 1.0,
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)

    def test_decision_requires_both_periods_and_paired_interval(self):
        val, test = {"n": 50, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": 1.0}
        paired = {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05}
        self.assertEqual(model.decide(val, test, paired)[0], "BACKTESTED")
        self.assertEqual(model.decide(val, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[0], "INCONCLUSIVE")
        self.assertEqual(model.decide({"n": 50, "rmse_improvement_pct": -2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, {"ci_95_low_bp2": -0.2, "ci_95_high_bp2": -0.01})[0], "REJECTED")

    def test_coverage_rejects_daily_price_gap(self):
        stress, prices = self.make_market(days=3388, weeks=484)
        del prices[sorted(prices)[100]]
        with self.assertRaisesRegex(ValueError, "missing UTC day"):
            model.validate_coverage(stress, prices, dt.date(2026, 11, 25))


if __name__ == "__main__":
    unittest.main()
