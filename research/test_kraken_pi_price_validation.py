from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from kraken_pi_price_validation import (
    CONTROL_TIMESTAMP,
    EXCEPTIONS,
    WINDOWS,
    epoch_seconds,
    parse_candle_payload,
    run_probe,
)


class KrakenPiPriceValidationTests(unittest.TestCase):
    def fake_fetcher(self, drop_candle: tuple[str, int] | None = None, product_override: dict | None = None):
        def fetch(url: str):
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            if parts[-1] != "candles":
                product_id = parts[-1]
                base = product_id.split("-", 1)[0]
                payload = {
                    "id": product_id,
                    "base_currency": base,
                    "quote_currency": "USD",
                    "status": "online",
                    "trading_disabled": False,
                }
                if product_override and product_id in product_override:
                    payload.update(product_override[product_id])
                return {
                    "url": url, "http_status": 200, "response_sha256": "a" * 64,
                    "error": None, "raw_response_retained": False,
                }, payload

            product_id = parts[-2]
            query = parse_qs(parsed.query)
            start = epoch_seconds(query["start"][0])
            end = epoch_seconds(query["end"][0])
            base = 71500 if product_id == "BTC-USD" else 2250
            rows = []
            for timestamp in range(start, end, 3600):
                if drop_candle == (product_id, timestamp):
                    continue
                rows.append([timestamp, base - 10, base + 10, base, base, 100])
            return {
                "url": url, "http_status": 200, "response_sha256": "b" * 64,
                "error": None, "raw_response_retained": False,
            }, rows
        return fetch

    def test_all_nine_exception_windows_and_both_positive_controls_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = run_probe(Path(directory), fetcher=self.fake_fetcher())
            saved = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["status"], "coinbase_spot_crosscheck_complete")
        self.assertEqual(manifest["summary"]["exceptions_total"], 9)
        self.assertEqual(manifest["summary"]["exceptions_with_exact_hour_candle"], 9)
        self.assertEqual(manifest["summary"]["exceptions_with_complete_three_hour_window"], 9)
        self.assertEqual(manifest["summary"]["known_active_controls_passed"], 2)
        self.assertEqual(len(manifest["exception_comparisons"]), len(EXCEPTIONS))
        self.assertTrue(all(
            item["comparison_status"] == "COMPLETE_3H_WINDOW"
            and len(item["comparison_candles"]) == 3
            and item["candle_window_response_sha256"] == "b" * 64
            for item in manifest["exception_comparisons"]
        ))
        self.assertTrue(all(item["control_passed"] for item in manifest["known_active_controls"]))
        self.assertEqual(saved["retention"]["raw_coinbase_responses_retained"], False)
        self.assertTrue(all("candles" not in item for item in saved["candle_windows"]))
        self.assertEqual(saved["research_gate"]["kraken_funding_status"], "PROVISIONAL_NOT_ACCEPTED")
        self.assertFalse(saved["research_gate"]["backtest_authorized"])

    def test_missing_exact_hour_fails_closed_without_forward_fill(self):
        missing = ("BTC-USD", epoch_seconds("2026-08-20T09:00:00Z"))
        with tempfile.TemporaryDirectory() as directory:
            manifest = run_probe(Path(directory), fetcher=self.fake_fetcher(drop_candle=missing))

        btc = next(item for item in manifest["exception_comparisons"] if item["symbol"] == "PI_XBTUSD")
        self.assertEqual(manifest["status"], "coinbase_spot_crosscheck_incomplete")
        self.assertFalse(btc["exact_timestamp_candle_present"])
        self.assertEqual(btc["comparison_status"], "MISSING_EXACT_HOUR")
        self.assertEqual(btc["same_hour_close_basis_vs_implied_pct"], None)
        self.assertIn("one_or_more_exact_exception_hour_candles_missing", manifest["failure_reasons"])

    def test_wrong_or_offline_product_metadata_blocks_the_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = run_probe(
                Path(directory),
                fetcher=self.fake_fetcher(product_override={"ETH-USD": {"status": "offline"}}),
            )
        self.assertEqual(manifest["status"], "coinbase_spot_crosscheck_incomplete")
        eth = manifest["product_controls"]["ETH-USD"]["validation"]
        self.assertFalse(eth["online_control_passed"])
        self.assertIn("product_not_online", eth["errors"])
        self.assertFalse(manifest["research_gate"]["cap_exceptions_accepted"])

    def test_candle_parser_detects_duplicates_invalid_ohlc_and_out_of_window_rows(self):
        start = epoch_seconds("2026-01-01T00:00:00Z")
        end = epoch_seconds("2026-01-01T03:00:00Z")
        payload = [
            [start, 99, 101, 100, 100, 5],
            [start, 99, 101, 100, 100, 5],
            [start + 3600, 99, 98, 100, 100, 5],
            [end, 99, 101, 100, 100, 5],
        ]
        candles, validation = parse_candle_payload(payload, start, end)
        self.assertEqual(len(candles), 2)
        self.assertEqual(validation["duplicate_timestamp_count"], 1)
        self.assertEqual(validation["invalid_row_count"], 2)
        self.assertEqual(validation["out_of_window_count"], 1)
        self.assertIn("ohlc_invariant", validation["errors"])
        self.assertIn("out_of_window", validation["errors"])

    def test_each_fixed_window_is_bounded_and_includes_its_target_timestamps(self):
        self.assertEqual(len(EXCEPTIONS), 9)
        self.assertEqual(len(WINDOWS), 4)
        for window in WINDOWS:
            hours = (epoch_seconds(window["end"]) - epoch_seconds(window["start"])) // 3600
            self.assertGreater(hours, 0)
            self.assertLess(hours, 300)
        for exception in EXCEPTIONS:
            timestamp = epoch_seconds(exception["timestamp"])
            matching = [
                window for window in WINDOWS
                if window["product_id"] == exception["product_id"]
                and epoch_seconds(window["start"]) <= timestamp < epoch_seconds(window["end"])
            ]
            self.assertEqual(len(matching), 1, exception)
        self.assertTrue(any(
            item["product_id"] == "BTC-USD"
            and item["timestamp"] == CONTROL_TIMESTAMP
            for item in (
                {"product_id": product, "timestamp": CONTROL_TIMESTAMP}
                for product in ("BTC-USD", "ETH-USD")
            )
        ))


if __name__ == "__main__":
    unittest.main()
