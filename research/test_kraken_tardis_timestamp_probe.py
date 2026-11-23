import csv
import gzip
import io
import json
import unittest
from datetime import datetime, timezone

from kraken_tardis_timestamp_probe import compare, parse_api, parse_tardis


def us(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * 1_000_000)


def make_tardis(symbol, events, lead_seconds=30):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "exchange", "symbol", "timestamp", "local_timestamp",
        "funding_timestamp", "funding_rate",
    ])
    writer.writeheader()
    for event_time, rate in events:
        event_us = us(event_time)
        observed_us = event_us - int(lead_seconds * 1_000_000)
        writer.writerow({
            "exchange": "cryptofacilities",
            "symbol": symbol,
            "timestamp": observed_us,
            "local_timestamp": observed_us,
            "funding_timestamp": event_us,
            "funding_rate": rate,
        })
    return gzip.compress(output.getvalue().encode())


def make_api(rows):
    return json.dumps({
        "result": "success",
        "rates": [
            {"timestamp": stamp, "fundingRate": absolute, "relativeFundingRate": relative}
            for stamp, absolute, relative in rows
        ],
    }).encode()


class KrakenTardisTimestampTests(unittest.TestCase):
    def setUp(self):
        self.symbol = "PI_ETHUSD"
        self.events = [
            ("2026-10-01T01:00:00Z", 0.000010),
            ("2026-10-01T02:00:00Z", 0.000020),
            ("2026-10-01T03:00:00Z", 0.000030),
        ]

    def test_extracts_next_event_and_last_pre_event_rate(self):
        result = parse_tardis(make_tardis(self.symbol, self.events), self.symbol, "2026-10-01")
        self.assertEqual(len(result["events"]), 3)
        self.assertEqual(result["events"][0]["event_utc"], "2026-10-01T01:00:00Z")
        self.assertEqual(result["events"][0]["pre_event_rate"], 0.000010)
        self.assertEqual(result["events"][0]["seconds_before_event"], 30.0)
        self.assertTrue(result["events"][0]["usable"])

    def test_accepts_non_first_of_month_sample(self):
        events = [("2026-10-02T01:00:00Z", 0.000010)]
        result = parse_tardis(make_tardis(self.symbol, events), self.symbol, "2026-10-02")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_utc"], "2026-10-02T01:00:00Z")

    def test_pre_event_observation_older_than_five_minutes_is_not_usable(self):
        events = [("2026-10-01T01:00:00Z", 0.000010)]
        result = parse_tardis(make_tardis(self.symbol, events, lead_seconds=301), self.symbol, "2026-10-01")
        self.assertFalse(result["events"][0]["usable"])
        self.assertEqual(result["events"][0]["seconds_before_event"], 301.0)

    def test_rejects_wrong_symbol(self):
        with self.assertRaisesRegex(ValueError, "Unexpected Tardis"):
            parse_tardis(make_tardis("PI_XBTUSD", self.events), self.symbol, "2026-10-01")

    def test_api_parser_rejects_failed_response(self):
        with self.assertRaisesRegex(ValueError, "successful"):
            parse_api(b'{"result":"error","rates":[]}', self.symbol)

    def test_api_parser_counts_duplicate_and_out_of_order_rows(self):
        result = parse_api(make_api([
            ("2026-10-01T00:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T01:00:00Z", 2e-8, 0.0002),
            ("2026-10-01T01:00:00Z", 2e-8, 0.0002),
            ("2026-10-01T00:30:00Z", 3e-8, 0.0003),
        ]), self.symbol)
        self.assertEqual(result["duplicate_timestamp_count"], 1)
        self.assertEqual(result["out_of_order_timestamp_count"], 1)

    def test_event_boundary_when_pre_event_rate_matches_api_row_at_event(self):
        tardis = parse_tardis(make_tardis(self.symbol, self.events), self.symbol, "2026-10-01")
        rates = [rate for _, rate in self.events]
        api = parse_api(make_api([
            ("2026-10-01T00:00:00Z", 0.001, 0.01),
            ("2026-10-01T01:00:00Z", rates[0], rates[0] + 0.01),
            ("2026-10-01T02:00:00Z", rates[1], rates[1] + 0.01),
            ("2026-10-01T03:00:00Z", rates[2], rates[2] + 0.01),
        ]), self.symbol)
        result = compare(tardis, api, min_events=3)
        self.assertEqual(result["candidate_api_timestamp_semantics"], "EVENT_BOUNDARY")
        self.assertEqual(result["api_timestamp_to_funding_event_offset_hours"], 0)
        self.assertEqual(result["best_matching_api_rate_field"], "fundingRate")
        self.assertEqual(result["api_event_timestamp_row_count"], 3)
        self.assertEqual(result["api_expected_rate_timestamp_coverage"], 1.0)
        self.assertEqual(result["api_exact_expected_rate_match_count"], 3)

    def test_rate_setting_window_start_when_pre_event_rate_matches_api_row_one_hour_prior(self):
        tardis = parse_tardis(make_tardis(self.symbol, self.events), self.symbol, "2026-10-01")
        rates = [rate for _, rate in self.events]
        api = parse_api(make_api([
            ("2026-10-01T00:00:00Z", rates[0], rates[0] + 0.01),
            ("2026-10-01T01:00:00Z", rates[1], rates[1] + 0.01),
            ("2026-10-01T02:00:00Z", rates[2], rates[2] + 0.01),
            ("2026-10-01T03:00:00Z", 0.001, 0.01),
        ]), self.symbol)
        result = compare(tardis, api, min_events=3)
        self.assertEqual(result["candidate_api_timestamp_semantics"], "RATE_SETTING_WINDOW_START")
        self.assertEqual(result["api_timestamp_to_funding_event_offset_hours"], 1)
        self.assertEqual(result["best_matching_api_rate_field"], "fundingRate")
        self.assertEqual(result["api_expected_rate_timestamp_coverage"], 1.0)
        self.assertEqual(result["api_exact_expected_rate_match_count"], 3)

    def test_inverse_relative_rate_field_is_selected_with_exact_expected_row_coverage(self):
        tardis = parse_tardis(make_tardis(self.symbol, self.events), self.symbol, "2026-10-01")
        rates = [rate for _, rate in self.events]
        api = parse_api(make_api([
            ("2026-10-01T00:00:00Z", 1e-8, rates[0]),
            ("2026-10-01T01:00:00Z", 2e-8, rates[1]),
            ("2026-10-01T02:00:00Z", 3e-8, rates[2]),
            ("2026-10-01T03:00:00Z", 4e-8, 0.009),
        ]), self.symbol)
        result = compare(tardis, api, min_events=3)
        self.assertEqual(result["candidate_api_timestamp_semantics"], "RATE_SETTING_WINDOW_START")
        self.assertEqual(result["best_matching_api_rate_field"], "relativeFundingRate")
        self.assertEqual(result["api_event_timestamp_row_coverage"], 1.0)
        self.assertEqual(result["api_expected_rate_timestamp_coverage"], 1.0)
        self.assertEqual(result["api_exact_expected_rate_match_count"], 3)
        self.assertEqual(result["api_expected_rate_exact_match_fraction"], 1.0)
        self.assertEqual(result["event_comparisons"][0]["expected_api_rate_timestamp_utc"], "2026-10-01T00:00:00Z")

    def test_equal_adjacent_rates_leave_mapping_inconclusive(self):
        tardis = parse_tardis(make_tardis(self.symbol, self.events), self.symbol, "2026-10-01")
        api = parse_api(make_api([
            ("2026-10-01T00:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T01:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T02:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T03:00:00Z", 1e-8, 0.0001),
        ]), self.symbol)
        self.assertEqual(compare(tardis, api, min_events=3)["candidate_api_timestamp_semantics"], "INCONCLUSIVE")

    def test_zero_rate_is_valid_not_missing(self):
        payload = make_tardis(self.symbol, [("2026-10-01T01:00:00Z", 0.0)])
        result = parse_tardis(payload, self.symbol, "2026-10-01")
        self.assertEqual(result["events"][0]["pre_event_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
