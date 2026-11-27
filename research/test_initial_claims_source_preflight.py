import datetime as dt
import json
import unittest

import initial_claims_source_preflight as model


def make_weekly(start, count, value=220.0):
    return {
        start + dt.timedelta(days=7 * index): value + index * 0.1
        for index in range(count)
    }


class InitialClaimsSourcePreflightTests(unittest.TestCase):
    def test_fred_url_uses_frozen_series_and_start(self):
        url = model.build_fred_url()
        self.assertIn("id=ICSA", url)
        self.assertIn("cosd=2017-08-19", url)

    def test_parser_accepts_fred_observation_date_schema(self):
        body = (
            b"observation_date,ICSA\n"
            b"2017-08-19,240000\n"
            b"2017-08-26,238000\n"
            b"2017-09-02,.\n"
        )
        parsed = model.parse_icsa(body)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[dt.date(2017, 8, 19)], 240000.0)

    def test_parser_rejects_missing_column_duplicate_dates_and_nonpositive_values(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            model.parse_icsa(b"observation_date,OTHER\n2017-08-19,1\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_icsa(b"observation_date,ICSA\n2017-08-19,2\n2017-08-19,3\n")
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_icsa(b"observation_date,ICSA\n2017-08-19,0\n")

    def test_coverage_accepts_regular_weekly_history(self):
        start = dt.date(2017, 8, 19)
        values = make_weekly(start, 500)
        as_of = max(values) + dt.timedelta(days=3)
        result = model.validate_icsa_coverage(values, as_of)
        self.assertEqual(result["rows"], 500)
        self.assertEqual(result["weekday_utc"], "Saturday")
        self.assertEqual(result["complete_five_observation_windows"], 496)

    def test_coverage_rejects_stale_inconsistent_or_gapped_history(self):
        start = dt.date(2017, 8, 19)
        values = make_weekly(start, 500)
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_icsa_coverage(values, max(values) + dt.timedelta(days=15))
        inconsistent = dict(values)
        inconsistent[start + dt.timedelta(days=1)] = 100.0
        with self.assertRaisesRegex(ValueError, "weekday is inconsistent"):
            model.validate_icsa_coverage(inconsistent, max(inconsistent) + dt.timedelta(days=1))
        gapped = dict(values)
        del gapped[start + dt.timedelta(days=7 * 50)]
        del gapped[start + dt.timedelta(days=7 * 51)]
        with self.assertRaisesRegex(ValueError, "non-weekly gap"):
            model.validate_icsa_coverage(gapped, max(gapped) + dt.timedelta(days=1))

    def test_binance_exchange_info_requires_active_spot_symbol(self):
        good = {"symbols": [{
            "symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC",
            "quoteAsset": "USDT", "isSpotTradingAllowed": True
        }]}
        self.assertEqual(model.validate_binance_exchange_info(json.dumps(good).encode())["symbol"], "BTCUSDT")
        bad = {"symbols": [{
            "symbol": "BTCUSDT", "status": "BREAK", "baseAsset": "BTC", "quoteAsset": "USDT"
        }]}
        with self.assertRaisesRegex(ValueError, "expected active"):
            model.validate_binance_exchange_info(json.dumps(bad).encode())


if __name__ == "__main__":
    unittest.main()
