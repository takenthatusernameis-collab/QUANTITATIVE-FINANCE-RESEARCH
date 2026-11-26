import datetime as dt
import json
import unittest

import stablecoin_supply_source_preflight as model


def row(day, market_cap=100_000_000_000.0):
    timestamp = int(dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc).timestamp())
    return {"date": str(timestamp), "totalCirculatingUSD": {"peggedUSD": market_cap}}


class StablecoinSourcePreflightTests(unittest.TestCase):
    def test_parser_reads_documented_usd_pegged_circulating_field(self):
        body = json.dumps([row(dt.date(2021, 1, 1), 1.0e11), row(dt.date(2021, 1, 2), 1.01e11)]).encode()
        parsed = model.parse_stablecoin_history(body)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[dt.date(2021, 1, 1)], 1.0e11)

    def test_parser_accepts_iso_dates_but_rejects_duplicate_utc_days(self):
        body = json.dumps([{"date": "2021-01-01", "totalCirculatingUSD": {"peggedUSD": 100.0}}, {"date": str(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp())), "totalCirculatingUSD": {"peggedUSD": 101.0}}]).encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_stablecoin_history(body)

    def test_parser_rejects_missing_field_and_nonpositive_values(self):
        missing = json.dumps([{"date": "1609459200", "totalCirculatingUSD": {"peggedEUR": 10.0}}]).encode()
        with self.assertRaisesRegex(ValueError, "peggedUSD"):
            model.parse_stablecoin_history(missing)
        zero = json.dumps([row(dt.date(2021, 1, 1), 0.0)]).encode()
        with self.assertRaisesRegex(ValueError, "non-positive"):
            model.parse_stablecoin_history(zero)

    def test_parser_rejects_malformed_rows_and_non_array_envelopes(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            model.parse_stablecoin_history(b'{"data":[]}')
        with self.assertRaisesRegex(ValueError, "not an object"):
            model.parse_stablecoin_history(b'[1]')

    def test_coverage_requires_frozen_depth_freshness_and_gap_limit(self):
        values = {}
        day = model.SAMPLE_START
        last = model.SAMPLE_END - dt.timedelta(days=model.SUPPLY_LAG_DAYS)
        while day <= last:
            values[day] = 100_000_000_000.0 + (day - model.SAMPLE_START).days
            day += dt.timedelta(days=1)
        result = model.validate_stablecoin_coverage(values)
        self.assertGreaterEqual(result["rows_in_frozen_window"], model.MIN_ROWS)
        self.assertEqual(result["last_date"], last.isoformat())
        gap_values = dict(values)
        del gap_values[model.SAMPLE_START + dt.timedelta(days=10)]
        del gap_values[model.SAMPLE_START + dt.timedelta(days=11)]
        with self.assertRaisesRegex(ValueError, "gap"):
            model.validate_stablecoin_coverage(gap_values)

    def test_coverage_rejects_insufficient_history_and_stale_end(self):
        short = {model.SAMPLE_START + dt.timedelta(days=i): 100.0 for i in range(100)}
        with self.assertRaisesRegex(ValueError, "ends before"):
            model.validate_stablecoin_coverage(short)
        stale = {model.SAMPLE_START + dt.timedelta(days=i): 100.0 for i in range((model.SAMPLE_END - model.SAMPLE_START).days - 10)}
        with self.assertRaisesRegex(ValueError, "ends before"):
            model.validate_stablecoin_coverage(stale)

    def test_exchange_info_requires_exact_active_btcusdt_spot(self):
        body = json.dumps({"symbols": [{"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "isSpotTradingAllowed": True}]}).encode()
        result = model.validate_binance_exchange_info(body)
        self.assertEqual(result["symbol"], "BTCUSDT")
        inactive = json.dumps({"symbols": [{"symbol": "BTCUSDT", "status": "BREAK", "baseAsset": "BTC", "quoteAsset": "USDT"}]}).encode()
        with self.assertRaisesRegex(ValueError, "expected active"):
            model.validate_binance_exchange_info(inactive)


if __name__ == "__main__":
    unittest.main()
