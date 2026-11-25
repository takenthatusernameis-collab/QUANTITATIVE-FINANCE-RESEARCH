from __future__ import annotations

import datetime as dt
import math
import unittest

import treasury_auction_volatility as qfr


class TreasuryAuctionVolatilityTests(unittest.TestCase):
    def test_realized_variation_is_root_sum_square_of_five_changes(self):
        values = [1.00, 1.01, 0.99, 1.00, 1.02, 1.01]
        self.assertAlmostEqual(qfr.realized_variation_bp(values), math.sqrt(11.0), places=12)

    def test_realized_variation_requires_six_finite_observations(self):
        with self.assertRaisesRegex(ValueError, "six"):
            qfr.realized_variation_bp([1.0, 1.01])
        with self.assertRaisesRegex(ValueError, "finite"):
            qfr.realized_variation_bp([1.0, 1.01, 1.02, float("nan"), 1.03, 1.04])

    def test_post_window_starts_strictly_after_record_date(self):
        start = dt.date(2020, 1, 1)
        dates = [start + dt.timedelta(days=i) for i in range(30)]
        yields = {d: 2.0 + (i % 7) * 0.01 for i, d in enumerate(dates)}
        auction = {"record_date": dates[10], "auction_date": dates[8], "cusip": "A",
                   "bid_to_cover": 2.4, "dealer_share": 0.2}
        events, skipped = qfr.build_events([auction], yields)
        self.assertEqual(skipped["no_complete_post_window"], 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["pre_yield_end_date"], dates[10])
        self.assertEqual(events[0]["yield_start_date"], dates[11])
        self.assertEqual(events[0]["yield_end_date"], dates[16])
        self.assertAlmostEqual(events[0]["pre_variation_bp"], qfr.realized_variation_bp([yields[d] for d in dates[5:11]]))
        self.assertAlmostEqual(events[0]["target_variation_bp"], qfr.realized_variation_bp([yields[d] for d in dates[11:17]]))

    def test_incomplete_post_window_is_not_filled(self):
        start = dt.date(2020, 1, 1)
        dates = [start + dt.timedelta(days=i) for i in range(15)]
        yields = {d: 2.0 + i * 0.01 for i, d in enumerate(dates)}
        auction = {"record_date": dates[10], "auction_date": dates[9], "cusip": "B",
                   "bid_to_cover": 2.5, "dealer_share": 0.3}
        events, skipped = qfr.build_events([auction], yields)
        self.assertEqual(events, [])
        self.assertEqual(skipped["no_complete_post_window"], 1)

    def test_prequential_stress_score_uses_prior_26_events(self):
        start = dt.date(2020, 1, 1)
        events = [{"record_date": start + dt.timedelta(days=i), "dealer_share": 0.2 + (i % 5) * 0.01,
                   "bid_to_cover": 2.0 + (i % 5) * 0.1} for i in range(27)]
        qfr.add_stress_scores(events)
        self.assertIsNone(events[25]["weak_score"])
        self.assertIsNotNone(events[26]["weak_score"])
        self.assertIsInstance(events[26]["weak_demand"], bool)

    def test_walk_forward_requires_52_fully_completed_prior_targets(self):
        start = dt.date(2020, 1, 1)
        events = []
        for i in range(53):
            record = start + dt.timedelta(days=3 * i)
            events.append({"record_date": record, "yield_end_date": record + dt.timedelta(days=1),
                "cusip": f"C{i:03d}", "target_bp": math.log1p(2.0 + i % 4),
                "target_variation_bp": 2.0 + i % 4, "pre_vol_log": math.log1p(1.0 + i % 3),
                "bid_to_cover": 2.2 + (i % 5) * 0.1, "dealer_share": 0.15 + (i % 4) * 0.02})
        calls = []
        def fake_fit(train, current, features):
            calls.append((len(train), tuple(features)))
            return 0.0
        predictions = qfr.walk_forward(events, fake_fit)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1], ("pre_vol_log", "bid_to_cover"))
        self.assertEqual(calls[1][1], ("pre_vol_log", "bid_to_cover", "dealer_share"))
        events[51]["yield_end_date"] = events[52]["record_date"]
        calls.clear()
        self.assertEqual(qfr.walk_forward(events, fake_fit), [])
        self.assertEqual(calls, [])

    def test_metrics_report_log_and_original_scale_errors(self):
        rows = [{"target_bp": math.log1p(2.0), "target_variation_bp": 2.0,
                 "baseline_prediction_bp": math.log1p(2.0), "augmented_prediction_bp": math.log1p(3.0)},
                {"target_bp": math.log1p(4.0), "target_variation_bp": 4.0,
                 "baseline_prediction_bp": math.log1p(4.0), "augmented_prediction_bp": math.log1p(5.0)}]
        result = qfr.metrics(rows, "baseline_prediction_bp")
        self.assertEqual(result["n"], 2)
        self.assertAlmostEqual(result["rmse_log1p"], 0.0)
        self.assertAlmostEqual(result["rmse_variation_bp"], 0.0)

    def test_paired_bootstrap_is_deterministic_and_favors_better_augmented_model(self):
        start = dt.date(2023, 1, 1)
        rows = []
        for i in range(40):
            target = math.log1p(2.0 + (i % 5) * 0.2)
            rows.append({"record_date": start + dt.timedelta(days=3 * i), "cusip": f"C{i:03d}",
                "target_bp": target, "baseline_prediction_bp": target + 0.5,
                "augmented_prediction_bp": target + 0.1})
        first = qfr.paired_bootstrap(rows)
        second = qfr.paired_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertGreater(first["ci_95_low"], 0)

    def test_stress_bootstrap_requires_minimum_group_sizes(self):
        start = dt.date(2023, 1, 1)
        rows = [{"record_date": start + dt.timedelta(days=3 * i), "cusip": f"C{i:03d}",
                 "weak_demand": i < 10, "target_variation_bp": 5.0 if i < 10 else 2.0}
                for i in range(40)]
        result = qfr.stress_bootstrap(rows)
        self.assertIsNotNone(result)
        self.assertGreater(result["difference_bp"], 0)
        self.assertIsNone(qfr.stress_bootstrap(rows[:25]))


if __name__ == "__main__":
    unittest.main()
