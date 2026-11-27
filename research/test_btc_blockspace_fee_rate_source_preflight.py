from __future__ import annotations

import datetime as dt
import json
import urllib.error
import unittest
from unittest.mock import patch

import btc_blockspace_fee_rate_source_preflight as model


UTC = dt.timezone.utc
AS_OF = dt.datetime(2026, 11, 27, 14, 8, 3, tzinfo=UTC)


def sample_rows(days: int = 903, start: dt.date = dt.date(2024, 6, 8)) -> list[dict]:
    rows = []
    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        midnight = dt.datetime.combine(day, dt.time(), UTC)
        for hour in (6, 18):
            timestamp = int((midnight + dt.timedelta(hours=hour)).timestamp())
            rows.append({
                "timestamp": timestamp,
                "avgFee_0": 0.1,
                "avgFee_10": 1.0,
                "avgFee_25": 2.0,
                "avgFee_50": 3.0,
                "avgFee_75": 10.0 + offset % 7 + hour / 100.0,
                "avgFee_90": 20.0,
                "avgFee_100": 40.0,
                "avgHeight": 800_000 + offset * 144 + hour,
            })
    return rows


class BitcoinBlockspaceFeeRatePreflightTests(unittest.TestCase):
    def test_parser_retains_two_12h_bins_and_daily_median(self):
        rows = sample_rows()
        daily_bins, summary = model.parse_fee_rate_payload(json.dumps(rows).encode())
        first = dt.date(2024, 6, 8)
        values = [value for _, value in daily_bins[first]]
        expected = (10.0 + 6 / 100.0 + 10.0 + 18 / 100.0) / 2
        self.assertAlmostEqual(__import__("statistics").median(values), expected)
        self.assertEqual(len(daily_bins[first]), 2)
        self.assertEqual(summary["row_count"], 1806)
        self.assertEqual(summary["raw_unique_utc_dates"], 903)
        self.assertEqual(summary["source_bucket_seconds"], 43_200)

    def test_parser_accepts_documented_data_wrapper(self):
        rows = sample_rows()
        daily_bins, summary = model.parse_fee_rate_payload(json.dumps({"data": rows}).encode())
        self.assertEqual(summary["row_count"], len(rows))
        self.assertEqual(len(daily_bins), 903)

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
            rows = sample_rows(days=4)
            rows[0]["avgFee_75"] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "avgFee_75"):
                    model.parse_fee_rate_payload(json.dumps(rows, allow_nan=True).encode())

    def test_parser_rejects_out_of_order_timestamps(self):
        rows = sample_rows(days=4)
        rows[0], rows[-1] = rows[-1], rows[0]
        with self.assertRaisesRegex(ValueError, "oldest-to-newest"):
            model.parse_fee_rate_payload(json.dumps(rows).encode())

    def test_coverage_excludes_partial_first_and_last_dates(self):
        daily_bins, _ = model.parse_fee_rate_payload(json.dumps(sample_rows()).encode())
        completed, coverage = model.validate_coverage(daily_bins, AS_OF)
        self.assertEqual(len(completed), 901)
        self.assertEqual(coverage["first_utc_date"], "2024-06-09")
        self.assertEqual(coverage["last_utc_date"], "2026-11-26")
        self.assertEqual(coverage["span_calendar_days_inclusive"], 901)
        self.assertEqual(coverage["publication_lag_calendar_days"], 1)
        self.assertEqual(coverage["boundary_dates_excluded"], ["2024-06-08", "2026-11-27"])

    def test_coverage_rejects_short_completed_history(self):
        daily_bins, _ = model.parse_fee_rate_payload(json.dumps(sample_rows(days=901)).encode())
        with self.assertRaisesRegex(ValueError, "Insufficient completed UTC dates"):
            model.validate_coverage(daily_bins, AS_OF)

    def test_coverage_rejects_stale_latest_completed_date(self):
        rows = sample_rows(days=903, start=dt.date(2024, 6, 1))
        stale_cutoff = dt.date(2026, 11, 20)
        rows = [
            row for row in rows
            if dt.datetime.fromtimestamp(row["timestamp"], UTC).date() <= stale_cutoff
        ]
        daily_bins, _ = model.parse_fee_rate_payload(json.dumps(rows).encode())
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_coverage(daily_bins, AS_OF)

    def test_coverage_rejects_missing_half_day_bin(self):
        rows = sample_rows()
        target_day = dt.date(2025, 1, 1)
        rows = [
            row for row in rows
            if not (
                dt.datetime.fromtimestamp(row["timestamp"], UTC).date() == target_day
                and dt.datetime.fromtimestamp(row["timestamp"], UTC).hour >= 12
            )
        ]
        daily_bins, _ = model.parse_fee_rate_payload(json.dumps(rows).encode())
        with self.assertRaisesRegex(ValueError, "expected 2"):
            model.validate_coverage(daily_bins, AS_OF)

    def test_coverage_rejects_missing_calendar_date(self):
        rows = sample_rows()
        target_day = dt.date(2025, 1, 1)
        rows = [
            row for row in rows
            if dt.datetime.fromtimestamp(row["timestamp"], UTC).date() != target_day
        ]
        daily_bins, _ = model.parse_fee_rate_payload(json.dumps(rows).encode())
        with self.assertRaisesRegex(ValueError, "Missing UTC dates"):
            model.validate_coverage(daily_bins, AS_OF)

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
        self.assertEqual(result["coverage"]["unique_utc_dates"], 901)
        self.assertEqual(result["coverage"]["last_utc_date"], "2026-11-26")
        self.assertEqual(result["source_summary"]["raw_last_utc_date"], "2026-11-27")


if __name__ == "__main__":
    unittest.main()
