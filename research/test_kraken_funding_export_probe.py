from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from kraken_funding_export_probe import (
    analyze_api_rows,
    analyze_archive,
    analyze_archive_api_union,
    analyze_csv_stream,
    asset_from_instrument,
    crosscheck_archive_api,
    compare_archive_anomalies_to_api,
    compact_instrument,
    expected_interval_hours,
    extract_api_extrema,
    extract_archive_interval_anomalies,
    is_perpetual_instrument,
    parse_timestamp_ms,
    rate_cap_assessment,
    run_api_cap_audit,
    timestamp_semantics_assessment,
)


class KrakenFundingExportProbeTests(unittest.TestCase):
    def test_timestamp_parser_accepts_iso_and_epoch_units(self):
        self.assertEqual(parse_timestamp_ms("2026-01-01T00:00:00.000Z"), 1767225600000)
        self.assertEqual(parse_timestamp_ms("1767225600000"), 1767225600000)
        self.assertEqual(parse_timestamp_ms("1767225600"), 1767225600000)
        self.assertIsNone(parse_timestamp_ms("not-a-timestamp"))

    def test_compact_instrument_flags_expired_but_tradeable_api_conflict(self):
        inverse = compact_instrument({
            "symbol": "PI_XBTUSD", "isExpired": True, "tradeable": True,
        })
        linear = compact_instrument({
            "symbol": "PF_XBTUSD", "isExpired": False, "tradeable": True,
        })
        self.assertEqual(inverse["lifecycle_status"], "EXPIRED")
        self.assertTrue(inverse["lifecycle_flag_conflict"])
        self.assertIn("official contract delisting", inverse["lifecycle_interpretation"])
        self.assertEqual(linear["lifecycle_status"], "ACTIVE")
        self.assertFalse(linear["lifecycle_flag_conflict"])

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

    def test_archive_anomaly_extraction_respects_historical_cutover_and_keeps_adjacent_rows(self):
        values = [
            "2022-09-29T08:00:00Z",
            "2022-09-29T12:00:00Z",
            "2022-09-29T13:00:00Z",
            "2022-09-29T15:00:00Z",
            "2022-09-29T18:00:00Z",
            "2022-09-29T19:00:00Z",
        ]
        rows = [
            {
                "timestamp": value,
                "timestamp_ms": parse_timestamp_ms(value),
                "rates": {"absolute_rate": str(index), "relative_rate": str(index / 1000)},
            }
            for index, value in enumerate(values)
        ]
        self.assertEqual(expected_interval_hours(rows[0]["timestamp_ms"]), 4)
        self.assertEqual(expected_interval_hours(rows[2]["timestamp_ms"]), 1)
        anomalies = extract_archive_interval_anomalies(rows)
        self.assertEqual(len(anomalies), 2)
        self.assertEqual(
            [(item["from_utc"], item["to_utc"], item["actual_interval_hours"],
              item["expected_interval_hours"]) for item in anomalies],
            [
                ("2022-09-29T13:00:00+00:00", "2022-09-29T15:00:00+00:00", 2.0, 1),
                ("2022-09-29T15:00:00+00:00", "2022-09-29T18:00:00+00:00", 3.0, 1),
            ],
        )
        self.assertEqual(len(anomalies[0]["adjacent_context_records"]), 4)
        self.assertEqual(anomalies[0]["missing_hourly_boundaries"], ["2022-09-29T14:00:00+00:00"])

    def test_api_extrema_keep_timestamped_matches_and_adjacent_rows(self):
        api = {
            "symbol": "PI_XBTUSD",
            "status": 200,
            "result": "success",
            "url": "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PI_XBTUSD",
            "serverTime": "2026-10-30T16:05:00Z",
            "response_sha256": "a" * 64,
            "rates": [
                {"timestamp": "2026-10-30T13:00:00Z", "fundingRate": "0.1", "relativeFundingRate": "0.001"},
                {"timestamp": "2026-10-30T14:00:00Z", "fundingRate": "0.2", "relativeFundingRate": "0.005"},
                {"timestamp": "2026-10-30T15:00:00Z", "fundingRate": "0.05", "relativeFundingRate": "-0.003"},
                {"timestamp": "2026-10-30T16:00:00Z", "fundingRate": "0.2", "relativeFundingRate": "0.005"},
            ],
        }
        result = extract_api_extrema(api)
        self.assertEqual(result["response_sha256"], "a" * 64)
        relative = result["extrema"]["relativeFundingRate"]
        self.assertEqual(relative["max"]["value"], 0.005)
        self.assertEqual(relative["max"]["match_count"], 2)
        self.assertEqual(relative["min"]["value"], -0.003)
        self.assertEqual(relative["max"]["matches"][0]["timestamp"], "2026-10-30T14:00:00Z")
        self.assertEqual(len(relative["max"]["matches"][0]["adjacent_context_records"]), 3)
        self.assertEqual(
            relative["max"]["matches"][0]["cap_assessment"]["cap_status"],
            "EXCEEDS_DOCUMENTED_CAP",
        )
        self.assertEqual(
            relative["max"]["matches"][1]["cap_assessment"]["delisting_observation_window_review"],
            "AT_OR_AFTER_2026-10-30T15:00:00Z; timestamp-to-accrual mapping remains unresolved",
        )
        self.assertEqual(
            relative["max"]["matches"][1]["cap_assessment"]["delisting_settlement_boundary_review"],
            "AT_OR_AFTER_2026-10-30T16:00:00Z",
        )
        self.assertEqual(
            result["extrema"]["fundingRate"]["max"]["matches"][0]["cap_assessment"]["cap_status"],
            "NOT_APPLICABLE",
        )

    def test_archive_anomaly_comparison_checks_api_endpoints_and_missing_boundaries(self):
        left_ms = parse_timestamp_ms("2026-01-01T00:00:00Z")
        right_ms = parse_timestamp_ms("2026-01-01T02:00:00Z")
        anomaly = {
            "from_utc": "2026-01-01T00:00:00+00:00",
            "to_utc": "2026-01-01T02:00:00+00:00",
            "actual_interval_hours": 2.0,
            "expected_interval_hours": 1,
            "missing_hourly_boundaries": ["2026-01-01T01:00:00+00:00"],
            "left_record": {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "timestamp_ms": left_ms,
                "rates": {"absolute_rate": 0.1, "relative_rate": 0.01},
            },
            "right_record": {
                "timestamp": "2026-01-01T02:00:00+00:00",
                "timestamp_ms": right_ms,
                "rates": {"absolute_rate": 0.2, "relative_rate": 0.02},
            },
        }
        api = {
            "symbol": "PF_XBTUSD",
            "response_sha256": "b" * 64,
            "rates": [
                {"timestamp": "2026-01-01T00:00:00Z", "fundingRate": 0.1, "relativeFundingRate": 0.01},
                {"timestamp": "2026-01-01T01:00:00Z", "fundingRate": 0.15, "relativeFundingRate": 0.015},
                {"timestamp": "2026-01-01T02:00:00Z", "fundingRate": 0.2, "relativeFundingRate": 0.02},
            ],
        }
        result = compare_archive_anomalies_to_api([anomaly], api)[0]["api_comparison"]
        self.assertEqual(result["comparison_status"], "API_CONTAINS_ARCHIVE_MISSING_BOUNDARIES")
        self.assertTrue(result["endpoint_checks"]["left_record"]["api_row_present"])
        self.assertTrue(
            result["endpoint_checks"]["left_record"]["rate_comparisons"]["absolute_rate"]["equal_with_tolerance"]
        )
        self.assertTrue(result["missing_boundary_checks"][0]["api_row_present"])
        self.assertIn("neither source's absence proves", result["interpretation"])

    def test_rate_cap_assessment_is_contract_and_date_specific(self):
        pre_cutover = parse_timestamp_ms("2022-09-29T11:00:00Z")
        post_cutover = parse_timestamp_ms("2026-10-30T15:00:00Z")
        self.assertEqual(
            rate_cap_assessment("PI_XBTUSD", "relativeFundingRate", pre_cutover, 0.0015)["applicable_absolute_cap"],
            0.001,
        )
        self.assertEqual(
            rate_cap_assessment("PI_ETHUSD", "relativeFundingRate", post_cutover, 0.003)["cap_status"],
            "EXCEEDS_DOCUMENTED_CAP",
        )
        self.assertEqual(
            rate_cap_assessment("PF_XBTUSD", "relativeFundingRate", pre_cutover, 0.004)["cap_status"],
            "HISTORICAL_LINEAR_CAP_UNVERIFIED",
        )
        self.assertEqual(
            rate_cap_assessment("PF_ETHUSD", "relativeFundingRate", post_cutover, 0.004)["cap_status"],
            "WITHIN_DOCUMENTED_CAP",
        )

    def test_api_quality_counts_every_relative_rate_cap_violation(self):
        api = {
            "symbol": "PI_XBTUSD",
            "rates": [
                {"timestamp": "2026-08-20T07:00:00Z", "fundingRate": "0.1", "relativeFundingRate": "0.005"},
                {"timestamp": "2026-08-20T08:00:00Z", "fundingRate": "0.1", "relativeFundingRate": "0.0025"},
                {"timestamp": "2026-08-20T09:00:00Z", "fundingRate": "0.1", "relativeFundingRate": "-0.003"},
                {"timestamp": "2026-08-20T10:00:00Z", "fundingRate": "0.1", "relativeFundingRate": "-0.0025"},
            ],
        }
        result = analyze_api_rows(api)
        assessment = result["relative_rate_cap_assessment"]
        self.assertEqual(assessment["rows_assessed"], 4)
        self.assertEqual(assessment["rows_unassessed"], 0)
        self.assertEqual(assessment["exceeds_documented_cap_count"], 2)
        self.assertEqual(
            [row["timestamp"] for row in assessment["exceeds_documented_cap_rows"]],
            ["2026-08-20T07:00:00Z", "2026-08-20T09:00:00Z"],
        )
        self.assertEqual(assessment["status_counts"]["WITHIN_DOCUMENTED_CAP"], 2)
        self.assertEqual(assessment["status_counts"]["EXCEEDS_DOCUMENTED_CAP"], 2)
        first_exception, second_exception = assessment["exceeds_documented_cap_rows"]
        self.assertEqual(first_exception["fundingRate"], 0.1)
        self.assertEqual(first_exception["relativeFundingRate"], 0.005)
        self.assertEqual(
            [row["timestamp"] for row in first_exception["adjacent_context_records"]],
            ["2026-08-20T07:00:00Z", "2026-08-20T08:00:00Z"],
        )
        self.assertEqual(
            [row["timestamp"] for row in second_exception["adjacent_context_records"]],
            [
                "2026-08-20T08:00:00Z",
                "2026-08-20T09:00:00Z",
                "2026-08-20T10:00:00Z",
            ],
        )
        self.assertEqual(
            second_exception["adjacent_context_records"][1]["rates"]["fundingRate"],
            0.1,
        )
        self.assertEqual(
            second_exception["adjacent_context_records"][2]["relative_rate_cap_assessment"]["cap_status"],
            "WITHIN_DOCUMENTED_CAP",
        )

    def test_api_cap_audit_is_api_only_manifest_and_counts_all_rows(self):
        symbols = ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD")
        instruments = [
            {"symbol": "PF_XBTUSD", "pair": "BTC:USD", "base": "BTC", "type": "flexible_futures", "isExpired": False, "tradeable": True},
            {"symbol": "PF_ETHUSD", "pair": "ETH:USD", "base": "ETH", "type": "flexible_futures", "isExpired": False, "tradeable": True},
            {"symbol": "PI_XBTUSD", "pair": "BTC:USD", "base": "BTC", "type": "futures_inverse", "isExpired": True, "tradeable": True},
            {"symbol": "PI_ETHUSD", "pair": "ETH:USD", "base": "ETH", "type": "futures_inverse", "isExpired": True, "tradeable": True},
        ]
        api_records = []
        for index, symbol in enumerate(symbols):
            api_records.append({
                "symbol": symbol,
                "url": f"https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol={symbol}",
                "status": 200, "content_type": "application/json",
                "response_sha256": str(index) * 64, "result": "success",
                "serverTime": "2026-11-23T02:00:00Z",
                "rates": [
                    {"timestamp": "2026-08-20T07:00:00Z", "fundingRate": "0.001", "relativeFundingRate": "0.005"},
                    {"timestamp": "2026-08-20T08:00:00Z", "fundingRate": "0.002", "relativeFundingRate": "0.001"},
                ],
            })
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "kraken_funding_export_probe.fetch_instruments",
                return_value={
                    "requests": [{"status": 200, "expired_filter": False}, {"status": 200, "expired_filter": True}],
                    "instruments": instruments,
                    "perpetual_btc_eth": [compact_instrument(item) for item in instruments],
                },
            ), patch(
                "kraken_funding_export_probe.fetch_historical_funding",
                side_effect=api_records,
            ):
                result = run_api_cap_audit(Path(directory))
            manifest = json.loads((Path(directory) / "manifest.json").read_text())
        self.assertEqual(result["status"], "api_cap_audit_complete")
        self.assertFalse(manifest["archive_download_attempted"])
        self.assertFalse(manifest["raw_api_rows_uploaded"])
        self.assertFalse(manifest["raw_api_rows_committed"])
        self.assertEqual(manifest["api_rate_cap_exception_count_by_symbol"], {
            "PF_XBTUSD": 0, "PF_ETHUSD": 0, "PI_XBTUSD": 1, "PI_ETHUSD": 1,
        })
        self.assertEqual(len(manifest["api_rate_cap_exceptions"]), 2)
        self.assertTrue(all(
            "adjacent_context_records" in row and "fundingRate" in row
            for row in manifest["api_rate_cap_exceptions"]
        ))
        self.assertTrue(manifest["targeted_acceptance_checks"]["all_relative_rate_rows_cap_assessed"])
        self.assertEqual(len(manifest["target_instrument_lifecycle"]), 4)
        self.assertTrue(manifest["target_instrument_lifecycle"][2]["lifecycle_flag_conflict"])
        self.assertTrue(all("rates" not in item for item in manifest["public_api_responses"]))

    def test_api_timestamp_mapping_remains_unresolved_without_explicit_field_semantics(self):
        result = timestamp_semantics_assessment()
        self.assertEqual(result["rate_period_mechanics"], "NEXT_PERIOD_RATE_SET_AT_PRIOR_BOUNDARY")
        self.assertEqual(result["api_timestamp_boundary_semantics"], "UNRESOLVED")
        self.assertEqual(result["backtest_alignment_status"], "BLOCKED_PENDING_API_FIELD_MAPPING")
        self.assertTrue(result["inference_prohibited"])

    def test_archive_target_filter_inspects_only_the_exact_requested_symbols(self):
        instruments = [
            {"symbol": "PI_XBTUSD", "base": "XBT", "quote": "USD", "type": "futures_inverse"},
            {"symbol": "PI_ETHUSD", "base": "ETH", "quote": "USD", "type": "futures_inverse"},
            {"symbol": "PF_SOLUSD", "base": "SOL", "quote": "USD", "type": "flexible_futures"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for symbol in ("PI_XBTUSD", "PI_ETHUSD", "PF_SOLUSD"):
                    archive.writestr(
                        f"{symbol}.csv",
                        "timestamp,fundingRate,relativeFundingRate\n"
                        "2026-01-01T00:00:00Z,0.001,0.01\n",
                    )
            result = analyze_archive(
                archive_path, instruments, target_symbols={"PI_XBTUSD"}
            )
        self.assertEqual(
            [item["symbol"] for item in result["perpetual_csv_summaries"]],
            ["PI_XBTUSD"],
        )
        self.assertEqual(result["target_symbols_found"], ["PI_XBTUSD"])
        self.assertEqual(result["target_symbols_missing"], [])

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
