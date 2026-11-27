from __future__ import annotations

import datetime as dt
import json
import urllib.error
import unittest
from unittest.mock import patch

import btc_blockspace_fee_rate_source_preflight as model


UTC = dt.timezone.utc
AS_OF = dt.datetime(2026, 11, 27, 13, 55, 51, tzinfo=UTC)


def sample_rows(days: int = 901, start: dt.date = dt.date(2024, 6, 9)) -> list[dict]:
    rows = []
    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        midnight = dt.datetime.combine(day, dt.time(), UTC)
        for block_offset in (300, 600):
            timestamp = int((midnight + dt.timedelta(seconds=block_offset)).timestamp())
            rows.append({
                "timestamp": timestamp,
                "avgFee_0": 0.1,
                "avgFee_10": 1.0,
                "avgFee_25": 2.0,
                "avgFee_50": 3.0,
                "avgFee_75": 10.0 + offset % 7 + block_offset / 1000.0,
                "avgFee_90": 20.0,
                "avgFee_100": 40.0,
                "avgHeight": 800_000 + offset * 144 + block_offset / 600.0,
            })
    return rows


class BitcoinBlockspaceFeeRatePreflightTests(unittest.TestCase):
    def test_parser_aggregates_per_block_p75_to_daily_medians(self):
        rows = sample_rows()
        daily, summary = model.parse_fee_rate_payload(json.dumps(rows).encode())
        first = dt.date(2024, 6, 9)
        expected = (10.0 + 300 / 1000.0 + 10.0 + 600 / 1000.0) / 2
        self.assertAlmostEqual(daily[first], expected)
        self.assertEqual(summary["row_count"], 1802)
        self.assertEqual(summary["unique_utc_dates"], 901)
        self.assertEqual(summary["response_schema"], sorted(rows[0].keys()))

    def test_parser_accepts_documented_data_wrapper(self):
        rows = sample_rows()
        daily, summary = model.parse_fee_rate_payload(json.dumps({"data": rows}).encode())
        self.assertEqual(summary["row_count"], len(rows))
        self.assertEqual(len(daily), 901)

    def test_parser_rejects_non_object_rows(self):
        with self.assertRaisesRegex(ValueError, "Expected object row"):
            model.parse_fee_rate_payload(json.dumps([[1, 2, 3]]).encode())

    def test_parser_rejects_missing_p75_schema_field(self):
        rows = sample_rows()
        del rows[0]["avgFee_75"]
        with self.assertRaisesRegex(ValueError, "missing=.*avgFee_75"):
            model.parse_fee_rate_payload(json.dumps(rows).encode())

    def test_parser_rejects_nonfinite_or_negative_p75(self):
        for value in (float("nan"), float("inf"), -0.01):
            rows = sample_rows(days=2)
            rows[0]["avgFee_75"] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "avgFee_75"):
                    model.parse_fee_rate_payload(json.dumps(rows, allow_nan=True).encode())

    def test_parser_rejects_out_of_order_timestamps(self):
        rows = sample_rows(days=2)
        rows[0], rows[-1] = rows[-1], rows[0]
        with self.assertRaisesRegex(ValueError, "oldest-to-newest"):
            model.parse_fee_rate_payload(json.dumps(rows).encode())

    def test_coverage_accepts_minimum_900_day_span_and_recent_end(self):
        daily, _ = model.parse_fee_rate_payload(json.dumps(sample_rows()).encode())
        coverage = model.validate_coverage(daily, AS_OF)
        self.assertEqual(coverage["unique_utc_dates"], 901)
        self.assertEqual(coverage["span_calendar_days_inclusive"], 901)
        self.assertEqual(coverage["publication_lag_calendar_days"], 1)

    def test_coverage_rejects_short_history(self):
        daily, _ = model.parse_fee_rate_payload(json.dumps(sample_rows(days=899)).encode())
        with self.assertRaisesRegex(ValueError, "Insufficient unique UTC dates"):
            model.validate_coverage(daily, AS_OF)

    def test_coverage_rejects_stale_latest_date(self):
        rows = sample_rows(start=dt.date(2024, 6, 1))
        stale_cutoff = dt.date(2026, 11, 20)
        rows = [row for row in rows if dt.datetime.fromtimestamp(row["timestamp"], UTC).date() <= stale_cutoff]
        daily, _ = model.parse_fee_rate_payload(json.dumps(rows).encode())
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_coverage(daily, AS_OF)

    def test_fetcher_does_not_retry_rate_limit_or_attempt_payment(self):
        error = urllib.error.HTTPError(model.ENDPOINT, 429, "Too Many Requests", {}, None)
        with patch.object(model, "urlopen", side_effect=error) as mocked:
            with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
                model.fetch_fee_rate_payload()
        self.assertEqual(mocked.call_count, 1)

        payment = urllib.error.HTTPError(model.ENDPOINT, 402, "Payment Required", {}, None)
        with patch.object(model, "urlopen", side_effect=payment) as mocked:
            with self.assertRaisesRegex(RuntimeError, "no payment was attempted"):
                model.fetch_fee_rate_payload()
        self.assertEqual(mocked.call_count, 1)

    def test_run_preflight_makes_one_read_only_request_and_never_backtests(self):
        rows = sample_rows()
        body = json.dumps(rows).encode()
        response = (body, 200, model.ENDPOINT, {"x-ratelimit-remaining": "10"})
        fetcher = unittest.mock.Mock(return_value=response)
        result = model.run_preflight(fetcher=fetcher, now=AS_OF)
        fetcher.assert_called_once_with()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["api_requests"], 1)
        self.assertEqual(result["retry_count"], 0)
        self.assertFalse(result["payment_attempted"])
        self.assertFalse(result["raw_observations_saved"])
        self.assertFalse(result["backtest_run"])
        self.assertEqual(result["source_summary"]["unique_utc_dates"], 901)


if __name__ == "__main__":
    unittest.main()
