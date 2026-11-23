import csv
import gzip
import io
import json
import unittest
from datetime import datetime

from kraken_tardis_gap_probe import audit_delisting_context, audit_gap_context
from kraken_tardis_timestamp_probe import parse_api, parse_tardis


def us(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * 1_000_000)


def make_tardis(symbol, events):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "exchange", "symbol", "timestamp", "local_timestamp",
        "funding_timestamp", "funding_rate",
    ])
    writer.writeheader()
    for event_time, rate in events:
        event_us = us(event_time)
        observed_us = event_us - 30_000_000
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


class KrakenTardisGapTests(unittest.TestCase):
    def setUp(self):
        self.symbol = "PI_ETHUSD"

    def test_missing_api_row_with_tardis_event_and_next_schedule_is_not_settlement_proof(self):
        events = [
            ("2026-10-01T09:00:00Z", 0.0001),
            ("2026-10-01T10:00:00Z", 0.0002),
            ("2026-10-01T11:00:00Z", 0.0003),
        ]
        tardis = parse_tardis(make_tardis(self.symbol, events), self.symbol, "2026-10-01")
        api = parse_api(make_api([
            ("2026-10-01T08:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T10:00:00Z", 3e-8, 0.0003),
        ]), self.symbol)
        result = audit_gap_context(api, tardis, {
            "gap_start_utc": "2026-10-01T08:00:00Z",
            "gap_end_utc": "2026-10-01T10:00:00Z",
        })
        self.assertEqual(result["classification"], "MISSING_API_ROW_WITH_TARDIS_EVENT_AND_NEXT_EVENT_SCHEDULE")
        self.assertFalse(result["api_missing_row_present"])
        self.assertIsNone(result["api_missing_row_relativeFundingRate"])
        self.assertTrue(result["tardis_gap_event_observed"])
        self.assertTrue(result["tardis_next_event_pre_event_after_gap_event"])
        self.assertTrue(result["left_api_boundary_mapping"]["exact_relative_rate_match"])
        self.assertTrue(result["right_api_boundary_mapping"]["exact_relative_rate_match"])
        self.assertFalse(result["settlement_observed"])
        self.assertFalse(result["settlement_population_complete"])

    def test_gap_without_tardis_event_is_unresolved_not_zero_filled(self):
        tardis = parse_tardis(make_tardis(self.symbol, [
            ("2026-10-01T09:00:00Z", 0.0001),
        ]), self.symbol, "2026-10-01")
        api = parse_api(make_api([
            ("2026-10-01T08:00:00Z", 1e-8, 0.0001),
            ("2026-10-01T10:00:00Z", 3e-8, 0.0003),
        ]), self.symbol)
        result = audit_gap_context(api, tardis, {
            "gap_start_utc": "2026-10-01T08:00:00Z",
            "gap_end_utc": "2026-10-01T10:00:00Z",
        })
        self.assertEqual(result["classification"], "MISSING_API_ROW_WITHOUT_TARDIS_EVENT_OBSERVATION")
        self.assertIsNone(result["api_missing_row_relativeFundingRate"])
        self.assertFalse(result["settlement_observed"])

    def test_delisting_api_row_at_16_maps_to_17_event_not_16_event(self):
        events = [
            ("2026-10-30T15:00:00Z", 0.0001),
            ("2026-10-30T16:00:00Z", 0.0002),
        ]
        tardis = parse_tardis(make_tardis(self.symbol, events), self.symbol, "2026-10-30")
        api = parse_api(make_api([
            ("2026-10-30T14:00:00Z", 1e-8, 0.0001),
            ("2026-10-30T15:00:00Z", 2e-8, 0.0002),
            ("2026-10-30T16:00:00Z", 3e-8, 0.0003),
        ]), self.symbol)
        result = audit_delisting_context(api, tardis)
        rows = result["api_row_to_next_event_mappings"]
        self.assertEqual(rows[1]["expected_funding_event_utc"], "2026-10-30T16:00:00Z")
        self.assertTrue(rows[1]["tardis_event_observed"])
        self.assertTrue(rows[1]["exact_relative_rate_match"])
        self.assertEqual(rows[2]["expected_funding_event_utc"], "2026-10-30T17:00:00Z")
        self.assertFalse(rows[2]["tardis_event_observed"])
        self.assertFalse(result["api_16_utc_row_has_tardis_17_utc_event"])
        self.assertFalse(result["settlement_observed"])

    def test_gap_must_be_exactly_two_hours(self):
        api = {"by_time": {}}
        with self.assertRaisesRegex(ValueError, "exactly two hours"):
            audit_gap_context(api, {"events": []}, {
                "gap_start_utc": "2026-10-01T08:00:00Z",
                "gap_end_utc": "2026-10-01T09:00:00Z",
            })


if __name__ == "__main__":
    unittest.main()
