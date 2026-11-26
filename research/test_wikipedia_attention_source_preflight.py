import datetime as dt
import json
import unittest

import wikipedia_attention_source_preflight as model


def item(day, views=1000, **overrides):
    row = {
        "project": model.PROJECT,
        "article": model.ARTICLE,
        "granularity": model.GRANULARITY,
        "timestamp": day.strftime("%Y%m%d") + "00",
        "access": model.ACCESS,
        "agent": model.AGENT,
        "views": views,
    }
    row.update(overrides)
    return row


class WikipediaAttentionSourcePreflightTests(unittest.TestCase):
    def test_date_chunks_cover_inclusive_range_without_overlap(self):
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 4, 15)
        chunks = list(model.iter_date_chunks(start, end, chunk_days=30))
        self.assertEqual(chunks[0][0], start)
        self.assertEqual(chunks[-1][1], end)
        for left, right in zip(chunks, chunks[1:]):
            self.assertEqual(left[1] + dt.timedelta(days=1), right[0])
        self.assertEqual(sum((b - a).days + 1 for a, b in chunks), (end - start).days + 1)

    def test_url_uses_documented_pageviews_route_and_inclusive_dates(self):
        url = model.build_pageviews_url(dt.date(2024, 1, 1), dt.date(2024, 1, 31))
        self.assertIn("/en.wikipedia.org/all-access/user/Bitcoin/daily/20240101/20240131", url)

    def test_parser_reads_documented_items_and_daily_utc_timestamps(self):
        body = json.dumps({"items": [item(dt.date(2024, 1, 1), 1234), item(dt.date(2024, 1, 2), 5678)]}).encode()
        parsed = model.parse_pageviews(body, dt.date(2024, 1, 1), dt.date(2024, 1, 2))
        self.assertEqual(parsed[dt.date(2024, 1, 1)], 1234)
        self.assertEqual(parsed[dt.date(2024, 1, 2)], 5678)

    def test_parser_rejects_wrong_dimensions_duplicate_dates_and_bad_counts(self):
        wrong = item(dt.date(2024, 1, 1), project="fr.wikipedia")
        with self.assertRaisesRegex(ValueError, "unexpected project"):
            model.parse_pageviews(json.dumps({"items": [wrong]}).encode(), dt.date(2024, 1, 1), dt.date(2024, 1, 1))
        duplicate = {"items": [item(dt.date(2024, 1, 1)), item(dt.date(2024, 1, 1))]}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_pageviews(json.dumps(duplicate).encode(), dt.date(2024, 1, 1), dt.date(2024, 1, 1))
        negative = {"items": [item(dt.date(2024, 1, 1), -1)]}
        with self.assertRaisesRegex(ValueError, "invalid views"):
            model.parse_pageviews(json.dumps(negative).encode(), dt.date(2024, 1, 1), dt.date(2024, 1, 1))

    def test_parser_rejects_malformed_envelopes_and_out_of_window_rows(self):
        with self.assertRaisesRegex(ValueError, "items array"):
            model.parse_pageviews(b'{"data": []}', dt.date(2024, 1, 1), dt.date(2024, 1, 1))
        outside = {"items": [item(dt.date(2024, 1, 2))]}
        with self.assertRaisesRegex(ValueError, "outside requested"):
            model.parse_pageviews(json.dumps(outside).encode(), dt.date(2024, 1, 1), dt.date(2024, 1, 1))

    def test_coverage_reconstructs_single_omitted_zero_view_day(self):
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 1, 4)
        values = {start: 100, start + dt.timedelta(days=2): 200, end: 300}
        old_min = model.MIN_NONZERO_ROWS
        try:
            model.MIN_NONZERO_ROWS = 3
            result = model.validate_pageview_coverage(values, start, end)
        finally:
            model.MIN_NONZERO_ROWS = old_min
        self.assertEqual(result["expected_calendar_days"], 4)
        self.assertEqual(result["documented_zero_view_days_reconstructed"], 1)
        self.assertEqual(result["maximum_consecutive_omitted_days"], 1)

    def test_coverage_rejects_long_gaps_stale_ends_and_insufficient_rows(self):
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 1, 5)
        long_gap = {start: 100, end: 200}
        with self.assertRaisesRegex(ValueError, "consecutive dates"):
            model.validate_pageview_coverage(long_gap, start, end)
        old_min = model.MIN_NONZERO_ROWS
        try:
            model.MIN_NONZERO_ROWS = 5
            sufficient_shape = {start + dt.timedelta(days=i): 100 + i for i in (0, 1, 3, 4)}
            with self.assertRaisesRegex(ValueError, "Insufficient"):
                model.validate_pageview_coverage(sufficient_shape, start, end)
        finally:
            model.MIN_NONZERO_ROWS = old_min

    def test_binance_exchange_info_requires_exact_active_spot_symbol(self):
        good = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "isSpotTradingAllowed": True}]}
        result = model.validate_binance_exchange_info(json.dumps(good).encode())
        self.assertEqual(result["symbol"], "BTCUSDT")
        bad = {"symbols": [{"symbol": "BTCUSDT", "status": "BREAK", "baseAsset": "BTC", "quoteAsset": "USDT"}]}
        with self.assertRaisesRegex(ValueError, "expected active"):
            model.validate_binance_exchange_info(json.dumps(bad).encode())


if __name__ == "__main__":
    unittest.main()
