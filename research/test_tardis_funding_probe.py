import csv
import io
import unittest
from datetime import datetime, timedelta, timezone

from tardis_funding_probe import parse_derivative_ticker_csv


def sample_csv(sample_date="2024-01-01", symbol="ETHUSDT", omit_minutes=()):
    start = datetime.fromisoformat(sample_date).replace(tzinfo=timezone.utc)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "exchange", "symbol", "timestamp", "local_timestamp",
        "funding_timestamp", "funding_rate", "predicted_funding_rate",
        "open_interest", "last_price", "index_price", "mark_price",
    ])
    for minute in range(24 * 60):
        if minute in omit_minutes:
            continue
        exchange_time = start + timedelta(minutes=minute)
        if minute < 8 * 60:
            next_event = start + timedelta(hours=8)
        elif minute < 16 * 60:
            next_event = start + timedelta(hours=16)
        else:
            next_event = start + timedelta(days=1)
        exchange_us = int(exchange_time.timestamp() * 1_000_000)
        local_us = exchange_us + 500_000
        next_event_us = int(next_event.timestamp() * 1_000_000)
        writer.writerow([
            "binance-futures", symbol, exchange_us, local_us, next_event_us,
            f"{0.0001 + minute / 1_000_000:.9f}", "0.0002",
            "1000000", "42000.0", "42001.0", f"{42000 + minute / 100:.2f}",
        ])
    return output.getvalue()


class TardisFundingProbeTests(unittest.TestCase):
    def test_extracts_upcoming_event_schedule_and_last_pre_event_estimates(self):
        result = parse_derivative_ticker_csv(sample_csv(), "ETHUSDT", "2024-01-01")

        self.assertEqual(result["status"], "SAMPLE_VALID")
        self.assertEqual(result["row_count"], 1440)
        self.assertEqual(len(result["unique_next_funding_timestamps_utc"]), 3)
        self.assertEqual(len(result["pre_event_observations"]), 3)
        self.assertTrue(all(item["seconds_before_event"] <= 60 for item in result["pre_event_observations"]))
        self.assertEqual(result["pre_event_observations"][0]["next_funding_timestamp_utc"],
                         "2024-01-01T08:00:00+00:00")
        self.assertFalse(result["settled_funding_rate_available"])
        self.assertFalse(result["settlement_population_complete"])

    def test_large_local_timestamp_gap_fails_sample_quality_gate(self):
        result = parse_derivative_ticker_csv(
            sample_csv(omit_minutes=range(100, 105)), "ETHUSDT", "2024-01-01"
        )

        self.assertEqual(result["status"], "SAMPLE_INCOMPLETE")
        self.assertGreater(result["local_timestamp_gap_seconds"]["maximum"], 60)
        self.assertFalse(result["settlement_population_complete"])

    def test_rejects_wrong_exchange_or_symbol(self):
        bad = sample_csv(symbol="BTCUSDT")
        with self.assertRaisesRegex(ValueError, "Unexpected exchange/symbol"):
            parse_derivative_ticker_csv(bad, "ETHUSDT", "2024-01-01")

    def test_rejects_non_first_day_free_sample_date(self):
        with self.assertRaisesRegex(ValueError, "first day of a month"):
            parse_derivative_ticker_csv(sample_csv(sample_date="2024-01-02"), "ETHUSDT", "2024-01-02")

    def test_rejects_missing_required_schema_column(self):
        rows = sample_csv().splitlines()
        header = rows[0].replace("funding_rate,", "")
        with self.assertRaisesRegex(ValueError, "Missing required"):
            parse_derivative_ticker_csv("\n".join([header] + rows[1:]), "ETHUSDT", "2024-01-01")


if __name__ == "__main__":
    unittest.main()
