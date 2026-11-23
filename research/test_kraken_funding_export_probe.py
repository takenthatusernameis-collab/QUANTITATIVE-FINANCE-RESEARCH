from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from kraken_funding_export_probe import (
    analyze_api_rows,
    analyze_archive,
    analyze_archive_api_union,
    analyze_csv_stream,
    asset_from_instrument,
    crosscheck_archive_api,
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
        self.assertIsNone(asset_from_instrument({"symbol": "PF_ETHFIUSD", "base": "ETHFI"}))
        self.assertIsNone(asset_from_instrument({"symbol": "PF_AIXBTUSD", "base": "AIXBT"}))
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
        self.assertEqual(result["null_counts"]["timestamp"], 0)
        self.assertEqual(result["null_counts"]["note"], 1)
        self.assertIn({"hours": 4.0, "count": 1}, result["cadence_hours_top"])
        self.assertEqual(len(result["crosscheck_samples"]), 4)

    def test_csv_summary_keeps_kraken_export_absolute_and_relative_rate_columns(self):
        csv_text = (
            "timestamp,tradeable,absolute_rate,relative_rate\n"
            "2026-01-01 00:00:00,PF_XBTUSD,0.0000001,0.001\n"
            "2026-01-01 01:00:00,PF_XBTUSD,-0.0000002,-0.002\n"
        )
        result = analyze_csv_stream(io.StringIO(csv_text))
        self.assertEqual(result["rate_fields"]["absolute_rate"]["min"], -0.0000002)
        self.assertEqual(result["rate_fields"]["relative_rate"]["max"], 0.001)
        self.assertEqual(result["categorical_value_counts"]["tradeable"], {"PF_XBTUSD": 2})
        self.assertEqual(
            result["column_semantics"]["tradeable"],
            "Observed values are Kraken instrument symbols, not boolean flags; "
            "preserve the raw values verbatim.",
        )
        self.assertEqual(result["null_counts"]["tradeable"], 0)

    def test_archive_to_api_overlap_crosscheck_maps_both_rate_fields_without_merging_them(self):
        archive = {
            "symbol": "PF_XBTUSD",
            "data_summary": {
                "first_timestamp": "2026-01-01 00:00:00",
                "last_timestamp": "2026-01-01 01:00:00",
                "_api_crosscheck_rows": [
                    {"timestamp": "2026-01-01 00:00:00", "timestamp_ms": 1767225600000,
                     "rates": {"absolute_rate": "0.0001", "relative_rate": "0.01"}},
                    {"timestamp": "2026-01-01 01:00:00", "timestamp_ms": 1767229200000,
                     "rates": {"absolute_rate": "-0.0002", "relative_rate": "-0.02"}},
                ],
            },
        }
        api = {
            "symbol": "PF_XBTUSD", "status": 200, "result": "success", "rate_count": 2,
            "first_timestamp": "2026-01-01T00:00:00Z", "last_timestamp": "2026-01-01T01:00:00Z",
            "rates": [
                {"timestamp": "2026-01-01T00:00:00Z", "fundingRate": 0.0001, "relativeFundingRate": 0.01},
                {"timestamp": "2026-01-01T01:00:00Z", "fundingRate": -0.0002, "relativeFundingRate": -0.02},
            ],
        }
        result = crosscheck_archive_api(archive, api)
        self.assertEqual(result["matched_timestamps"], 2)
        self.assertTrue(result["timestamp_sets_equal"])
        self.assertTrue(result["rate_field_comparisons"]["absolute_rate -> fundingRate"]["all_compared_values_equal_with_tolerance"])
        self.assertTrue(result["rate_field_comparisons"]["relative_rate -> relativeFundingRate"]["all_compared_values_equal_with_tolerance"])

    def test_api_quality_checks_every_row_and_reports_nulls_order_duplicates_and_gaps(self):
        api = {
            "status": 200,
            "result": "success",
            "rates": [
                {"timestamp": "2026-01-01T00:00:00Z", "fundingRate": "0.001", "relativeFundingRate": "0.01"},
                {"timestamp": "2026-01-01T08:00:00Z", "fundingRate": "", "relativeFundingRate": "0.02"},
                {"timestamp": "2026-01-01T08:00:00Z", "fundingRate": "bad", "relativeFundingRate": "0.03"},
                {"timestamp": "2026-01-01T04:00:00Z", "fundingRate": "0.004", "relativeFundingRate": "0.04"},
                {"timestamp": "2026-01-02T00:00:00Z", "fundingRate": "0.005", "relativeFundingRate": None},
                {"timestamp": "not-a-timestamp", "fundingRate": "0.006", "relativeFundingRate": "0.06"},
            ],
        }
        result = analyze_api_rows(api)
        self.assertEqual(result["row_count"], 6)
        self.assertEqual(result["valid_timestamp_count"], 5)
        self.assertEqual(result["invalid_timestamp_count"], 1)
        self.assertEqual(result["unique_timestamp_count"], 4)
        self.assertEqual(result["duplicate_timestamp_count"], 1)
        self.assertEqual(result["out_of_order_timestamp_count"], 1)
        self.assertFalse(result["source_order_non_decreasing"])
        self.assertEqual(result["null_counts"]["fundingRate"], 1)
        self.assertEqual(result["null_counts"]["relativeFundingRate"], 1)
        self.assertEqual(result["rate_fields"]["fundingRate"]["invalid_count"], 2)
        self.assertEqual(result["rate_fields"]["relativeFundingRate"]["invalid_count"], 1)
        self.assertEqual(result["gaps_over_4h_count"], 1)
        self.assertEqual(result["max_positive_gap_hours"], 16.0)
        self.assertEqual(result["non_hourly_gap_count"], 3)
        self.assertEqual(
            [sample["hours"] for sample in result["non_hourly_gap_samples"]],
            [4.0, 4.0, 16.0],
        )
        self.assertEqual(result["history_completeness_status"], "PROVISIONAL_NOT_ACCEPTED")

    def test_archive_api_union_counts_full_api_only_tail_without_merging_contract_values(self):
        archive_rows = [
            {"timestamp_ms": 1767225600000},
            {"timestamp_ms": 1767254400000},
            {"timestamp_ms": 1767312000000},
        ]
        api_rows = [
            {"timestamp": "2026-01-01T08:00:00Z"},
            {"timestamp": "2026-01-02T00:00:00Z"},
            {"timestamp": "2026-01-02T08:00:00Z"},
            {"timestamp": "2026-01-03T00:00:00Z"},
        ]
        result = analyze_archive_api_union(archive_rows, api_rows)
        self.assertEqual(result["archive_unique_timestamps"], 3)
        self.assertEqual(result["api_unique_timestamps"], 4)
        self.assertEqual(result["overlap_timestamps"], 2)
        self.assertEqual(result["archive_only_timestamps"], 1)
        self.assertEqual(result["api_only_timestamps"], 2)
        self.assertEqual(result["api_only_tail_timestamps"], 2)
        self.assertEqual(result["union_unique_timestamps"], 5)
        self.assertEqual(result["union_start_utc"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(result["union_end_utc"], "2026-01-03T00:00:00+00:00")
        self.assertFalse(result["rate_values_merged"])
        self.assertEqual(result["union_gaps_over_4h_count"], 4)
        self.assertEqual(result["history_completeness_status"], "PROVISIONAL_NOT_ACCEPTED")

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
                    "PF_ETHFIUSD.csv",
                    "timestamp,fundingRate\\n2026-01-01T00:00:00.000Z,0.003\\n",
                )
                archive.writestr(
                    "__MACOSX/exports/._PF_XBTUSD.csv",
                    "not,a,real,csv\\n",
                )
                archive.writestr(
                    "PF_ETHUSD.csv",
                    "timestamp,fundingRate\n2026-01-01T00:00:00.000Z,0.003\n",
                )
            result = analyze_archive(archive_path, instruments)
        self.assertTrue(result["zip_valid"])
        self.assertEqual(result["archive_member_count"], 5)
        self.assertEqual(len(result["perpetual_csv_summaries"]), 2)
        self.assertEqual(result["ignored_macos_metadata_members"], 1)
        symbols = {item["symbol"] for item in result["perpetual_csv_summaries"]}
        self.assertEqual(symbols, {"PI_XBTUSD", "PF_ETHUSD"})
        self.assertEqual(
            {item["asset"] for item in result["perpetual_csv_summaries"]},
            {"BTC", "ETH"},
        )


if __name__ == "__main__":
    unittest.main()
