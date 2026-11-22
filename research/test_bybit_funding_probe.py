import unittest
from bybit_funding_probe import parse_payload, probe_symbol, MAX_REQUESTS, MAX_LIMIT, RETRY_ATTEMPTS


def row(symbol="BTCUSDT", rate="0.0001", ts=1000):
    return {"symbol": symbol, "fundingRate": rate, "fundingRateTimestamp": str(ts)}


def payload(items=None, code=0, category="linear"):
    return {"retCode": code, "retMsg": "OK", "result": {"category": category, "list": items or []}}


class BybitFundingProbeTests(unittest.TestCase):
    def test_constants_bound_probe(self):
        self.assertEqual(MAX_REQUESTS, 6)
        self.assertEqual(MAX_LIMIT, 200)
        self.assertEqual(RETRY_ATTEMPTS, 3)

    def test_valid_records_sorted_gap_distribution(self):
        r = parse_payload(payload([row(ts=2000), row(ts=1000)]), "BTCUSDT", 3000, 2)
        self.assertEqual(r["status"], "OBSERVED")
        self.assertEqual(r["earliest_record_utc"], "1970-01-01T00:00:01+00:00")
        self.assertEqual(r["observed_timestamp_gap_hours_distribution"], {0.000278: 1})

    def test_empty_records_explicit(self):
        r = parse_payload(payload([]), "BTCUSDT", 1000, 200)
        self.assertEqual(r["status"], "NO_RECORDS")
        self.assertIsNone(r["earliest_record_utc"])

    def test_nonzero_code_rejected(self):
        with self.assertRaisesRegex(ValueError, "API rejected"):
            parse_payload(payload([], code=10001), "BTCUSDT", 1000, 200)

    def test_nonobject_rejected(self):
        with self.assertRaisesRegex(ValueError, "object"):
            parse_payload([], "BTCUSDT", 1000, 200)

    def test_wrong_category_rejected(self):
        with self.assertRaisesRegex(ValueError, "category"):
            parse_payload(payload([], category="inverse"), "BTCUSDT", 1000, 200)

    def test_symbol_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "symbol mismatch"):
            parse_payload(payload([row("ETHUSDT")]), "BTCUSDT", 1000, 200)

    def test_nonfinite_rate_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid rate or timestamp"):
            parse_payload(payload([row(rate="nan")]), "BTCUSDT", 1000, 200)

    def test_timestamp_after_end_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            parse_payload(payload([row(ts=2000)]), "BTCUSDT", 1000, 200)

    def test_duplicate_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_payload(payload([row(ts=1000), row(ts=1000)]), "BTCUSDT", 2000, 200)

    def test_limit_enforced(self):
        with self.assertRaisesRegex(ValueError, "exceeded requested limit"):
            parse_payload(payload([row(ts=1000), row(ts=2000)]), "BTCUSDT", 3000, 1)

    def test_symbol_allowlist(self):
        with self.assertRaisesRegex(ValueError, "unsupported symbol"):
            probe_symbol("DOGEUSDT", fetcher=lambda *_: (None, b""), sleeper=lambda _: None)

    def test_three_samples_are_bounded(self):
        calls, sleeps = [], []
        def fetcher(symbol, end_ms, limit):
            calls.append((symbol, end_ms, limit))
            return payload([row(symbol, ts=end_ms)]), b"fixture"
        m = probe_symbol("BTCUSDT", 2, fetcher=fetcher, sleeper=sleeps.append)
        self.assertEqual(len(calls), 3)
        self.assertEqual(m["sample_count"], 3)
        self.assertFalse(m["pagination_attempted"])
        self.assertEqual(len(sleeps), 2)
        self.assertEqual(m["samples"][0]["status"], "OBSERVED")


if __name__ == "__main__":
    unittest.main()
