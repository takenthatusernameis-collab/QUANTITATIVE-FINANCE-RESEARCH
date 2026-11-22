from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from kraken_funding_export_probe import (
    analyze_archive,
    analyze_csv_stream,
    asset_from_instrument,
    is_perpetual_instrument,
    parse_timestamp_ms,
)


class KrakenFundingExportProbeTests(unittest.TestCase):
    def test_timestamp_parser_accepts_iso_and_epoch_units(self):
        self.assertEqual(parse_timestamp_ms("2026-01-01T00:00:00.000Z"), 1767225600000)
        self.assertEqual(parse_timestamp_ms("1767225600000"), 1767225600000)
        self.assertEqual(parse_timestamp_ms("1767225600"), 1767225600000)
        self.assertIsNone(parse_timestamp_ms("not-a-timestamp"))

    def test_instrument_classification_keeps_btc_and_eth_perpetuals_distinct(self):
        inverse = {"symbol": "PI_XBTUSD", "base": "XBT", "type": "futures_inverse"}
        linear = {"symbol": "PF_ETHUSD", "base": "ETH", "type": "flexible_futures"}
        dated = {"symbol": "FI_XBTUSD_260101", "base": "XBT", "type": "futures_inverse",
                 "lastTradingTime": "2026-01-01T00:00:00.000Z"}
        self.assertEqual(asset_from_instrument(inverse), "BTC")
        self.assertEqual(asset_from_instrument(linear), "ETH")
        self.assertTrue(is_perpetual_instrument(inverse))
        self.assertTrue(is_perpetual_instrument(linear))
        self.assertFalse(is_perpetual_instrument(dated))

    def test_csv_summary_counts_duplicates_order_gaps_nulls_and_separate_rates(self):
        csv_text = (
            "timestamp,fundingRate,relativeFundingRate,note\n"
            "2026-01-01T00:00:00.000Z,0.001,0.01,ok\n"
            "2026-01-01T04:00:00.000Z,0.002,0.02,\n"
            "2026-01-01T04:00:00.000Z,0.002,0.02,duplicate\n"
            "2026-01-01T02:00:00.000Z,-0.001,-0.01,out-of-order\n"
        )
        result = analyze_csv_stream(io.StringIO(csv_text))
        self.assertEqual(result["row_count"], 4)
        self.assertEqual(result["duplicate_timestamp_count"], 1)
        self.assertEqual(result["out_of_order_timestamp_count"], 1)
        self.assertEqual(result["rate_fields"]["fundingRate"]["min"], -0.001)
        self.assertEqual(result["rate_fields"]["relativeFundingRate"]["max"], 0.02)
        self.assertEqual(result["null_counts"]["note"], 1)
        self.assertIn({"hours": 4.0, "count": 1}, result["cadence_hours_top"])
        self.assertEqual(len(result["crosscheck_samples"]), 4)

    def test_archive_only_analyzes_identified_perpetual_csvs(self):
        instruments = [
            {"symbol": "PI_XBTUSD", "base": "XBT", "quote": "USD",
             "type": "futures_inverse", "contractSize": 1},
            {"symbol": "FI_XBTUSD_260101", "base": "XBT", "quote": "USD",
             "type": "futures_inverse", "lastTradingTime": "2026-01-01T00:00:00.000Z"},
            {"symbol": "PF_ETHUSD", "base": "ETH", "quote": "USD",
             "type": "flexible_futures", "contractSize": 1},
        ]
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "PI_XBTUSD.csv",
                    "timestamp,fundingRate,relativeFundingRate\n"
                    "2026-01-01T00:00:00.000Z,0.001,0.01\n"
                    "2026-01-01T04:00:00.000Z,0.002,0.02\n",
                )
                archive.writestr(
                    "FI_XBTUSD_260101.csv",
                    "timestamp,fundingRate\n2026-01-01T00:00:00.000Z,0.001\n",
                )
                archive.writestr(
                    "PF_ETHUSD.csv",
                    "timestamp,fundingRate\n2026-01-01T00:00:00.000Z,0.003\n",
                )
            result = analyze_archive(archive_path, instruments)
        self.assertTrue(result["zip_valid"])
        self.assertEqual(result["archive_member_count"], 3)
        self.assertEqual(len(result["perpetual_csv_summaries"]), 2)
        symbols = {item["symbol"] for item in result["perpetual_csv_summaries"]}
        self.assertEqual(symbols, {"PI_XBTUSD", "PF_ETHUSD"})
        self.assertEqual(
            {item["asset"] for item in result["perpetual_csv_summaries"]},
            {"BTC", "ETH"},
        )


if __name__ == "__main__":
    unittest.main()
