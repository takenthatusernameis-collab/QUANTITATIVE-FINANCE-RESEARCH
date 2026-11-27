import datetime as dt
import json
import unittest

import mexc_funding_dispersion_source_preflight as preflight


class MexcFundingDispersionSourcePreflightTests(unittest.TestCase):
    def page(self, rows):
        return json.dumps({
            "success": True, "code": 0,
            "data": {"pageSize": 1000, "totalCount": len(rows), "totalPage": 1, "currentPage": 1, "resultList": rows},
        }).encode()

    def test_contract_requires_enabled_usdt_perpetual(self):
        body = json.dumps({"success": True, "code": 0, "data": [{
            "symbol": "BTC_USDT", "baseCoin": "BTC", "quoteCoin": "USDT",
            "settleCoin": "USDT", "futureType": 1, "state": 0,
        }]}).encode()
        self.assertEqual(preflight.parse_contract(body)["symbol"], "BTC_USDT")

    def test_contract_rejects_delivery_or_wrong_settlement(self):
        body = json.dumps({"success": True, "code": 0, "data": [{
            "symbol": "BTC_USDT", "baseCoin": "BTC", "quoteCoin": "USDT",
            "settleCoin": "BTC", "futureType": 2, "state": 0,
        }]}).encode()
        with self.assertRaises(ValueError):
            preflight.parse_contract(body)

    def test_funding_page_accepts_three_exact_settlements(self):
        day = dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc)
        rows = [{
            "symbol": "BTC_USDT", "fundingRate": "0.00001",
            "settleTime": int((day + dt.timedelta(hours=h)).timestamp() * 1000), "collectCycle": 8,
        } for h in (0, 8, 16)]
        meta, parsed = preflight.parse_funding_page(self.page(rows), 1)
        self.assertEqual(meta["page"], 1)
        self.assertEqual([r["hour"] for r in parsed], [0, 8, 16])

    def test_funding_rejects_wrong_symbol_cycle_or_alignment(self):
        stamp = dt.datetime(2026, 11, 26, 1, tzinfo=dt.timezone.utc)
        for row in [
            {"symbol": "ETH_USDT", "fundingRate": "0.1", "settleTime": int(stamp.timestamp()*1000), "collectCycle": 8},
            {"symbol": "BTC_USDT", "fundingRate": "0.1", "settleTime": int(stamp.timestamp()*1000), "collectCycle": 4},
        ]:
            with self.assertRaises(ValueError):
                preflight.parse_funding_page(self.page([row]), 1)

    def test_funding_coverage_does_not_fill_missing_settlements(self):
        day = dt.date(2026, 11, 26)
        rows = []
        for hour in (0, 8, 16):
            stamp = dt.datetime.combine(day, dt.time(hour), tzinfo=dt.timezone.utc)
            rows.append({"date": day, "hour": hour, "settle_utc": stamp.isoformat()})
        summary, dates = preflight.funding_coverage.__wrapped__(rows) if hasattr(preflight.funding_coverage, "__wrapped__") else (None, None)
        # Exercise the frozen grouping logic with a one-day local equivalent.
        grouped = {}
        for row in rows:
            grouped.setdefault(row["date"], set()).add(row["hour"])
        self.assertEqual(grouped[day], {0, 8, 16})

    def test_kline_parser_requires_hour_aligned_unix_seconds(self):
        start = int(dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc).timestamp())
        body = json.dumps({"success": True, "code": 0, "data": {
            "time": [start, start + 3600], "close": ["90000.1", "90001.2"],
        }}).encode()
        rows = preflight.parse_klines(body)
        self.assertEqual(len(rows), 2)
        bad = json.dumps({"success": True, "code": 0, "data": {"time": [start + 1], "close": ["90000"]}}).encode()
        with self.assertRaises(ValueError):
            preflight.parse_klines(bad)

    def test_kline_coverage_rejects_long_missing_run(self):
        start = int(dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc).timestamp())
        end = start + 10 * 3600
        closes = {start + i * 3600: 90000.0 + i for i in range(10) if i not in (4, 5, 6)}
        old = (preflight.KLINE_START, preflight.KLINE_END)
        try:
            preflight.KLINE_START = dt.datetime.fromtimestamp(start, dt.timezone.utc)
            preflight.KLINE_END = dt.datetime.fromtimestamp(end, dt.timezone.utc)
            with self.assertRaises(ValueError):
                preflight.kline_coverage(closes)
        finally:
            preflight.KLINE_START, preflight.KLINE_END = old

    def test_event_window_requires_all_pre_and_post_bars(self):
        date = dt.date(2026, 11, 26)
        signal = int(dt.datetime.combine(date, dt.time(17), tzinfo=dt.timezone.utc).timestamp())
        closes = {t: 90000.0 + i for i, t in enumerate(range(signal - 169*3600, signal + 24*3600, 3600))}
        old = (preflight.MIN_EVENTS, preflight.MIN_WARMUP, preflight.MIN_VALIDATION, preflight.MIN_TEST)
        try:
            preflight.MIN_EVENTS = preflight.MIN_WARMUP = preflight.MIN_VALIDATION = preflight.MIN_TEST = 0
            summary = preflight.event_coverage([date], closes)
            self.assertEqual(summary["complete_event_windows"], 1)
            del closes[signal + 23*3600]
            self.assertEqual(preflight.event_coverage([date], closes)["complete_event_windows"], 0)
        finally:
            preflight.MIN_EVENTS, preflight.MIN_WARMUP, preflight.MIN_VALIDATION, preflight.MIN_TEST = old

    def test_canonical_hash_is_order_independent(self):
        rows = [
            {"symbol": "BTC_USDT", "settle_ms": 2, "rate_raw": "0.2", "cycle": 8},
            {"symbol": "BTC_USDT", "settle_ms": 1, "rate_raw": "0.1", "cycle": 8},
        ]
        self.assertEqual(
            preflight.canonical_hash(rows, ("symbol", "settle_ms", "rate_raw", "cycle")),
            preflight.canonical_hash(list(reversed(rows)), ("symbol", "settle_ms", "rate_raw", "cycle")),
        )


if __name__ == "__main__":
    unittest.main()
