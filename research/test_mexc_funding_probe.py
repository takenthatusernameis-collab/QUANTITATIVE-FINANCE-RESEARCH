import unittest

from mexc_funding_probe import fetch_symbol, parse_page_payload


def row(symbol, rate, timestamp, cycle=8):
    return {
        "symbol": symbol,
        "fundingRate": rate,
        "settleTime": timestamp,
        "collectCycle": cycle,
    }


def payload(symbol, page, rows, total_count=3, total_pages=2, page_size=2):
    return {
        "success": True,
        "code": 0,
        "data": {
            "pageSize": page_size,
            "totalCount": total_count,
            "totalPage": total_pages,
            "currentPage": page,
            "resultList": rows,
        },
    }


class MexcFundingProbeTests(unittest.TestCase):
    def test_parses_valid_page(self):
        meta, rows = parse_page_payload(
            payload("BTC_USDT", 1, [row("BTC_USDT", "0.0001", 1000), row("BTC_USDT", "-0.0002", 2000)]),
            "BTC_USDT", 1, 2,
        )
        self.assertEqual(meta["total_count"], 3)
        self.assertEqual(meta["total_pages"], 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["funding_rate"], 0.0001)
        self.assertEqual(rows[1]["settle_time_ms"], 2000)

    def test_accepts_string_zero_code(self):
        data = payload("ETH_USDT", 1, [row("ETH_USDT", "0", 1000)], 1, 1, 2)
        data["code"] = "0"
        meta, rows = parse_page_payload(data, "ETH_USDT", 1, 2)
        self.assertEqual(meta["total_count"], 1)
        self.assertEqual(rows[0]["funding_rate"], 0.0)

    def test_rejects_symbol_mismatch(self):
        with self.assertRaisesRegex(ValueError, "symbol mismatch"):
            parse_page_payload(payload("BTC_USDT", 1, [row("ETH_USDT", "0.1", 1000), row("ETH_USDT", "0.1", 2000)]),
                              "BTC_USDT", 1, 2)

    def test_rejects_nonfinite_rate(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_page_payload(payload("BTC_USDT", 1, [row("BTC_USDT", "nan", 1000), row("BTC_USDT", "0.1", 2000)]),
                              "BTC_USDT", 1, 2)

    def test_rejects_bad_page_number(self):
        with self.assertRaisesRegex(ValueError, "pagination metadata"):
            parse_page_payload(payload("BTC_USDT", 1, [row("BTC_USDT", "0.1", 1000), row("BTC_USDT", "0.1", 2000)]),
                              "BTC_USDT", 2, 2)

    def test_empty_history_is_not_reported_as_observed_complete(self):
        empty = payload("BTC_USDT", 1, [], total_count=0, total_pages=0, page_size=2)
        with self.assertRaisesRegex(ValueError, "no funding history rows returned"):
            fetch_symbol(
                "BTC_USDT", 2, 3, 10,
                lambda *_: (empty, b"empty-response"),
                sleeper=lambda _: None,
            )

    def test_fetches_all_pages_and_sorts_records(self):
        page1 = payload("BTC_USDT", 1, [row("BTC_USDT", "0.0001", 3000), row("BTC_USDT", "0.0002", 1000)])
        page2 = payload("BTC_USDT", 2, [row("BTC_USDT", "0.0003", 2000)], 3, 2, 2)
        calls = []

        def fetcher(symbol, page_num, page_size):
            calls.append((symbol, page_num, page_size))
            return (page1 if page_num == 1 else page2), b"page-" + str(page_num).encode()

        result = fetch_symbol("BTC_USDT", 2, 3, 10, fetcher, sleeper=lambda _: None)
        self.assertEqual(calls, [("BTC_USDT", 1, 2), ("BTC_USDT", 2, 2)])
        self.assertEqual(result["status"], "OBSERVED_COMPLETE")
        self.assertTrue(result["pagination_complete"])
        self.assertEqual(result["records_fetched"], 3)
        self.assertEqual(result["earliest_settlement_utc"], "1970-01-01T00:00:01+00:00")
        self.assertEqual(result["latest_settlement_utc"], "1970-01-01T00:00:03+00:00")
        self.assertEqual(result["duplicate_settlement_timestamps"], 0)

    def test_duplicate_timestamps_fail_closed(self):
        page1 = payload("BTC_USDT", 1, [row("BTC_USDT", "0.1", 1000), row("BTC_USDT", "0.2", 2000)])
        page2 = payload("BTC_USDT", 2, [row("BTC_USDT", "0.3", 2000)], 3, 2, 2)
        def fetcher(symbol, page_num, page_size):
            return (page1 if page_num == 1 else page2), b"raw"

        with self.assertRaisesRegex(ValueError, "duplicate"):
            fetch_symbol("BTC_USDT", 2, 3, 10, fetcher, sleeper=lambda _: None)

    def test_bounded_page_limit_fails_before_more_requests(self):
        page1 = payload("BTC_USDT", 1, [row("BTC_USDT", "0.1", 1000), row("BTC_USDT", "0.2", 2000)], 7, 4, 2)
        with self.assertRaisesRegex(ValueError, "bounded probe exceeded"):
            fetch_symbol("BTC_USDT", 2, 3, 10, lambda *_: (page1, b"raw"), sleeper=lambda _: None)

    def test_unsupported_symbol_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported symbol"):
            fetch_symbol("DOGE_USDT", page_fetcher=lambda *_: (None, b""), sleeper=lambda _: None)


if __name__ == "__main__":
    unittest.main()
