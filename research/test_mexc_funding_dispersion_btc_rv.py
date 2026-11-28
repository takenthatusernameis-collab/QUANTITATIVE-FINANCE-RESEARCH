import datetime as dt
import unittest

import mexc_funding_dispersion_btc_rv as model


class MexcFundingDispersionBtcRvTests(unittest.TestCase):
    def make_closes(self, start, end):
        closes = {}
        value = 90000.0
        for timestamp in range(start, end, 3600):
            value *= 1.0 + ((timestamp // 3600) % 7 - 3) * 0.0001
            closes[timestamp] = value
        return closes

    def test_predict_one_uses_repository_standardized_ols_helper(self):
        train = []
        for i in range(model.TRAIN_WINDOW):
            row = {
                "pre_rv24_log": 0.5 + i * 0.013,
                "pre_rv168_log": 0.7 + (i % 19) * 0.021,
                "abs_return24_bps": 2.0 + (i % 11) * 0.37,
                "funding_mean_bps": -0.1 + (i % 7) * 0.025,
            }
            row["target"] = (
                0.2 * row["pre_rv24_log"]
                + 0.1 * row["pre_rv168_log"]
                + 0.001 * row["abs_return24_bps"]
                + 0.5 * row["funding_mean_bps"]
            )
            train.append(row)
        current = {
            "pre_rv24_log": 1.1, "pre_rv168_log": 0.9,
            "abs_return24_bps": 3.2, "funding_mean_bps": 0.03,
            "funding_dispersion_bps": 0.08, "target": 0.4,
        }
        prediction = model.predict_one(train, current, model.BASE_FEATURES)
        self.assertTrue(__import__("math").isfinite(prediction))

    def test_log_returns_use_only_completed_hourly_closes(self):
        start = int(dt.datetime(2026, 11, 26, 17, tzinfo=dt.timezone.utc).timestamp())
        closes = {start - 3600: 100.0, start: 101.0, start + 3600: 102.0}
        returns = model.log_returns(closes, start, 2)
        self.assertAlmostEqual(returns[0], __import__("math").log(1.01))
        self.assertAlmostEqual(returns[1], __import__("math").log(102.0 / 101.0))

    def test_build_events_freezes_three_settlements_and_target_window(self):
        date = dt.date(2026, 11, 26)
        signal = int(dt.datetime.combine(date, dt.time(17), tzinfo=dt.timezone.utc).timestamp())
        closes = self.make_closes(signal - 169 * 3600, signal + 24 * 3600)
        funding = [
            {"date": date, "hour": 0, "rate": 0.00001},
            {"date": date, "hour": 8, "rate": 0.00002},
            {"date": date, "hour": 16, "rate": 0.00004},
        ]
        events = model.build_events(funding, closes)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["signal_ts"], signal)
        self.assertEqual(events[0]["target_end_ts"], signal + 24 * 3600)
        self.assertGreater(events[0]["funding_dispersion_bps"], 0)

    def test_build_events_rejects_missing_settlement_instead_of_filling(self):
        date = dt.date(2026, 11, 26)
        signal = int(dt.datetime.combine(date, dt.time(17), tzinfo=dt.timezone.utc).timestamp())
        closes = self.make_closes(signal - 169 * 3600, signal + 24 * 3600)
        funding = [
            {"date": date, "hour": 0, "rate": 0.00001},
            {"date": date, "hour": 8, "rate": 0.00002},
        ]
        self.assertEqual(model.build_events(funding, closes), [])

    def test_training_sample_excludes_unmatured_target_equal_to_signal(self):
        events = [
            {"signal_ts": 100, "target_end_ts": 200},
            {"signal_ts": 200, "target_end_ts": 300},
            {"signal_ts": 300, "target_end_ts": 400},
        ]
        sample = model.training_sample(events, signal_ts=300, window=10)
        self.assertEqual([row["signal_ts"] for row in sample], [100])

    def test_bootstrap_is_deterministic_and_reports_ordered_interval(self):
        rows = [
            {"baseline_squared_error": 1.0 + i * 0.01, "augmented_squared_error": 0.8 + i * 0.01}
            for i in range(50)
        ]
        a = model.paired_loss_block_bootstrap(rows, reps=200, block_size=7, seed=7)
        b = model.paired_loss_block_bootstrap(rows, reps=200, block_size=7, seed=7)
        self.assertEqual(a, b)
        self.assertLessEqual(a["ci95_lower"], a["ci95_upper"])
        self.assertGreater(a["mean_baseline_minus_augmented_squared_loss"], 0)

    def test_disposition_requires_both_splits_and_confidence_interval(self):
        validation = {"baseline_rmse": 1.0, "augmented_rmse": 0.9}
        test = {"baseline_rmse": 1.0, "augmented_rmse": 0.9}
        interval = {"ci95_lower": 0.01, "ci95_upper": 0.10}
        self.assertEqual(model.disposition(validation, test, interval), "PROMISING")
        interval = {"ci95_lower": -0.01, "ci95_upper": 0.10}
        self.assertEqual(model.disposition(validation, test, interval), "INCONCLUSIVE")
        validation = {"baseline_rmse": 1.0, "augmented_rmse": 1.1}
        test = {"baseline_rmse": 1.0, "augmented_rmse": 1.1}
        interval = {"ci95_lower": -0.10, "ci95_upper": -0.01}
        self.assertEqual(model.disposition(validation, test, interval), "REJECTED")


if __name__ == "__main__":
    unittest.main()
