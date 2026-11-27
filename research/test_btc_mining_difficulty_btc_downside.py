import datetime as dt
import json
import math
import unittest

import btc_mining_difficulty_btc_downside as study


class BitcoinMiningDifficultyDownsideTests(unittest.TestCase):
    def test_parse_firsthand_adjustments_validates_metadata_and_order(self):
        payload = {
            "source": "Firsthand Bitcoin",
            "url": "https://firsthandbitcoin.com/data",
            "license": "Free to use with attribution and a link to firsthandbitcoin.com/data",
            "generated": "2026-11-27T05:00:00Z",
            "key": "adj",
            "label": "Difficulty adjustment",
            "unit": "%",
            "from": "2026-01-01",
            "to": "2026-01-29",
            "points": 3,
            "data": [["2026-01-01", -2.5], ["2026-01-15", 1.25], ["2026-01-29", -0.75]],
        }
        records, metadata = study.parse_firsthand_adjustments(json.dumps(payload).encode())
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["adjustment_pct"], -2.5)
        self.assertEqual(metadata["last_date"], "2026-01-29")

    def test_parse_firsthand_rejects_duplicate_dates(self):
        payload = {
            "source": "Firsthand Bitcoin", "license": "free to use", "generated": "2026-11-27T05:00:00Z",
            "key": "adj", "label": "Difficulty adjustment", "unit": "%", "from": "2026-01-01",
            "to": "2026-01-01", "points": 2,
            "data": [["2026-01-01", 1.0], ["2026-01-01", 2.0]],
        }
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            study.parse_firsthand_adjustments(json.dumps(payload).encode())

    def test_parse_mempool_rows_and_percent_conversion(self):
        timestamps = [
            int(dt.datetime(2026, 1, day, tzinfo=dt.timezone.utc).timestamp())
            for day in (1, 15, 29)
        ]
        rows = [
            [timestamps[0], 900000, 1000.0, 0.975],
            [timestamps[1], 902016, 975.0, 1.0125],
            [timestamps[2], 904032, 987.1875, 0.99],
        ]
        records = study.parse_mempool_adjustments(json.dumps(rows).encode(), min_rows=3)
        self.assertEqual(len(records), 3)
        self.assertAlmostEqual(records[0]["adjustment_pct"], -2.5)
        self.assertAlmostEqual(records[1]["adjustment_pct"], 1.25)

    def test_crosscheck_requires_tight_series_consistency(self):
        dates = [dt.date(2026, 1, day) for day in (1, 15, 29)]
        primary = [
            {"date": dates[0], "adjustment_pct": -2.5},
            {"date": dates[1], "adjustment_pct": 1.25},
            {"date": dates[2], "adjustment_pct": -1.0},
        ]
        secondary = [
            {"date": dates[0], "adjustment_pct": -2.501},
            {"date": dates[1], "adjustment_pct": 1.251},
            {"date": dates[2], "adjustment_pct": -1.001},
        ]
        result = study.crosscheck_adjustments(primary, secondary, min_matches=3)
        self.assertEqual(result["matched_rows"], 3)
        self.assertGreaterEqual(result["coverage"], 0.95)
        secondary[1]["adjustment_pct"] = 1.5
        with self.assertRaisesRegex(ValueError, "mismatch"):
            study.crosscheck_adjustments(primary, secondary, min_matches=3)

    def test_build_events_uses_full_day_lag_and_nonoverlapping_targets(self):
        start = dt.date(2017, 8, 17)
        end = start + dt.timedelta(days=500)
        prices = {}
        for offset in range((end - start).days + 1):
            day = start + dt.timedelta(days=offset)
            close = 10000.0 * math.exp(0.0002 * offset + 0.01 * math.sin(offset / 7.0))
            prices[day] = {"close": close}
        adjustments = []
        for offset in range(35, 470, 14):
            day = start + dt.timedelta(days=offset)
            adjustments.append({"date": day, "adjustment_pct": -3.0 if len(adjustments) % 2 == 0 else 2.0})
        events, metadata = study.build_events(prices, adjustments, start, end, end - dt.timedelta(days=10))
        self.assertGreater(len(events), 20)
        self.assertEqual(metadata["accepted_events"], len(events))
        for event in events:
            self.assertEqual(event["signal_date"], event["adjustment_date"] + dt.timedelta(days=1))
            self.assertEqual(event["target_start_date"], event["signal_date"] + dt.timedelta(days=1))
            self.assertEqual(event["target_end_date"], event["signal_date"] + dt.timedelta(days=5))
            if event["difficulty_adjustment_pct"] < 0:
                self.assertGreater(event["difficulty_cut_pct"], 0)
            else:
                self.assertEqual(event["difficulty_cut_pct"], 0)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_decision_requires_both_periods_and_paired_interval(self):
        def period(n, improvement):
            return {
                "n": n,
                "rmse_improvement_pct": improvement,
                "baseline": {"rmse_bp": 1.0},
                "augmented": {"rmse_bp": 0.9},
            }
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.03}
        self.assertEqual(study.decide(period(60, 1.0), period(110, 0.5), paired)[0], "PROMISING")
        self.assertEqual(study.decide(period(60, -1.0), period(110, -0.5), {"ci_95_low": -0.03, "ci_95_high": -0.01})[0], "REJECTED")
        self.assertEqual(study.decide(period(20, 1.0), period(110, 0.5), paired)[0], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
