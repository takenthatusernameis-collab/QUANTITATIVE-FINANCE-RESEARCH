from __future__ import annotations
import datetime as dt
import math
import unittest
from unittest.mock import patch
import treasury_supply_pressure as qfr


class TreasurySupplyPressureTests(unittest.TestCase):
    def auctions(self, n):
        start = dt.date(2010, 1, 1)
        return [{"cusip": f"C{i:04d}", "auction_date": start + dt.timedelta(days=30*i),
                 "record_date": start + dt.timedelta(days=30*i), "offering_amt": 100.0,
                 "bid_to_cover": 2.4 + (i % 5) * 0.01} for i in range(n)]

    def test_supply_ratio_uses_only_previous_twelve_valid_auctions(self):
        rows = self.auctions(13)
        rows[-1]["offering_amt"] = 150.0
        result = qfr.add_supply_features(rows)
        self.assertAlmostEqual(result[-1]["supply_log_ratio"], math.log(1.5), places=12)
        future = rows + [{"cusip": "FUTURE", "auction_date": dt.date(2012, 1, 1),
                          "record_date": dt.date(2012, 1, 1), "offering_amt": 1_000_000.0, "bid_to_cover": 2.5}]
        later = qfr.add_supply_features(future)
        self.assertAlmostEqual(later[-2]["supply_log_ratio"], result[-1]["supply_log_ratio"], places=12)

    def test_missing_offering_amount_is_not_imputed(self):
        auctions = [{"cusip": "A", "auction_date": dt.date(2020, 1, 1), "record_date": dt.date(2020, 1, 1)},
                    {"cusip": "B", "auction_date": dt.date(2020, 2, 1), "record_date": dt.date(2020, 2, 1)}]
        raw = [{"cusip": "A", "auction_date": "2020-01-01", "offering_amt": "100"},
               {"cusip": "B", "auction_date": "2020-02-01", "offering_amt": "null"}]
        with self.assertRaisesRegex(ValueError, "coverage"):
            qfr.enrich_offering_amounts(raw, auctions, min_coverage=0.95)

    def test_conflicting_duplicate_amounts_fail_closed(self):
        auction = {"cusip": "A", "auction_date": dt.date(2020, 1, 1), "record_date": dt.date(2020, 1, 1)}
        raw = [{"cusip": "A", "auction_date": "2020-01-01", "offering_amt": "100"},
               {"cusip": "A", "auction_date": "2020-01-01", "offering_amt": "101.5"}]
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            qfr.enrich_offering_amounts(raw, [auction], min_coverage=0.0)

    def test_target_is_first_to_second_observation_after_record_date(self):
        start = dt.date(2020, 1, 1)
        dates = [start + dt.timedelta(days=i) for i in range(12)]
        yields = {d: 2.0 + i * 0.01 for i, d in enumerate(dates)}
        auction = {"cusip": "A", "auction_date": dates[4], "record_date": dates[5],
                   "offering_amt": 120.0, "bid_to_cover": 2.5, "supply_log_ratio": math.log(1.2), "high_supply": True}
        events, skipped = qfr.build_supply_events([auction], yields)
        self.assertEqual(skipped["no_future_yield_window"], 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["yield_start_date"], dates[6])
        self.assertEqual(events[0]["yield_end_date"], dates[7])
        self.assertAlmostEqual(events[0]["target_bp"], 1.0, places=10)

    def test_missing_supply_feature_is_skipped(self):
        dates = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(12)]
        yields = {d: 2.0 + i * 0.01 for i, d in enumerate(dates)}
        auction = {"cusip": "A", "auction_date": dates[4], "record_date": dates[4],
                   "offering_amt": None, "bid_to_cover": 2.5, "supply_log_ratio": None}
        events, skipped = qfr.build_supply_events([auction], yields)
        self.assertEqual(events, [])
        self.assertEqual(skipped["missing_supply_history"], 1)

    def test_walk_forward_requires_fully_completed_prior_targets(self):
        start = dt.date(2020, 1, 1)
        events = []
        for i in range(53):
            date = start + dt.timedelta(days=3*i)
            events.append({"cusip": f"C{i:03d}", "record_date": date, "yield_end_date": date + dt.timedelta(days=1),
                           "target_bp": float(i % 7 - 3), "bid_to_cover": 2.4 + (i % 5) * 0.01,
                           "pre_yield_5d_bp": float(i % 9 - 4), "supply_log_ratio": math.log(1 + (i % 4) * 0.01),
                           "high_supply": bool(i % 4 == 0)})
        with patch.object(qfr.base, "fit_ols_predict", return_value=0.0) as fit:
            predictions = qfr.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(fit.call_count, 2)
        events[51]["yield_end_date"] = events[52]["record_date"]
        with patch.object(qfr.base, "fit_ols_predict", return_value=0.0) as fit:
            self.assertEqual(qfr.walk_forward_predictions(events), [])
        self.assertEqual(fit.call_count, 0)


if __name__ == "__main__":
    unittest.main()
