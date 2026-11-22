import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_eth_btc as research


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def response(status_code, content=b"ok"):
    item = requests.Response()
    item.status_code = status_code
    item.url = "https://example.test/resource"
    item._content = content
    item.encoding = "utf-8"
    return item


def zip_csv(csv_text, filename="sample.csv"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, csv_text)
    return buffer.getvalue()


class ResearchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
        self.frame = pd.DataFrame({
            "eth_open": [100.0, 110.0, 121.0, 121.0],
            "btc_open": [100.0, 100.0, 100.0, 100.0],
            "eth_close": [100.0, 110.0, 121.0, 121.0],
            "btc_close": [100.0, 100.0, 100.0, 100.0],
        }, index=self.index)


    def metric_frame(self, returns, positions=None, w_eth=None, w_btc=None):
        n = len(returns)
        index = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
        positions = np.zeros(n) if positions is None else np.asarray(positions, dtype=float)
        w_eth = positions / 2.0 if w_eth is None else np.asarray(w_eth, dtype=float)
        w_btc = -positions / 2.0 if w_btc is None else np.asarray(w_btc, dtype=float)
        held_eth = pd.Series(w_eth, index=index).shift(1).fillna(0.0)
        held_btc = pd.Series(w_btc, index=index).shift(1).fillna(0.0)
        return pd.DataFrame({
            "net_return": np.asarray(returns, dtype=float), "position": positions, "turnover": np.zeros(n),
            "w_eth": w_eth, "w_btc": w_btc,
            "held_w_eth": held_eth, "held_w_btc": held_btc,
        }, index=index)

    def test_bounded_retry_recovers_from_transient_503(self):
        session = FakeSession([response(503), response(200)])
        with patch.object(research.time, "sleep"):
            result = research.request_with_retry(session, "https://example.test/resource")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(session.calls, 2)

    def test_kline_archive_parser_accepts_recognized_header_and_millisecond_timestamps(self):
        header = ",".join(research.COLUMNS)
        row = (
            "1640995200000,100,101,99,100.5,10,1640998799999,"
            "1000,5,4,400,0"
        )
        parsed = research.parse_kline_archive(
            zip_csv(header + "\n" + row + "\n"), "fixture-header.zip"
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed.iloc[0]["timestamp"], pd.Timestamp("2022-01-01T00:00:00Z"))
        self.assertEqual(parsed.attrs["timestamp_unit"], "ms")
        self.assertTrue(parsed.attrs["header_detected"])

    def test_kline_archive_parser_accepts_documented_header_aliases_and_microseconds(self):
        header = (
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore"
        )
        row = (
            "1735689600000000,100,101,99,100.5,10,1735693199999999,"
            "1000,5,4,400,0"
        )
        parsed = research.parse_kline_archive(
            zip_csv(header + "\n" + row + "\n"), "fixture-microseconds.zip"
        )
        self.assertEqual(parsed.iloc[0]["timestamp"], pd.Timestamp("2025-01-01T00:00:00Z"))
        self.assertEqual(parsed.attrs["timestamp_unit"], "us")
        self.assertTrue(parsed.attrs["header_detected"])

    def test_kline_archive_parser_rejects_malformed_rows_instead_of_dropping_them(self):
        header = ",".join(research.COLUMNS)
        good = "1640995200000,100,101,99,100.5,10,1640998799999,1000,5,4,400,0"
        bad = "not-a-timestamp,100,101,99,100.5,10,1640998799999,1000,5,4,400,0"
        with self.assertRaisesRegex(ValueError, "Invalid open_time"):
            research.parse_kline_archive(
                zip_csv(header + "\n" + good + "\n" + bad + "\n"),
                "fixture-invalid.zip",
            )

    def test_aggregate_trade_probe_requires_timestamp_inside_requested_hour(self):
        timestamp = pd.Timestamp("2024-01-01T01:00:00Z")
        trade = {
            "a": 123, "p": "100.0", "q": "0.5", "f": 123, "l": 123,
            "T": int(timestamp.timestamp() * 1000) + 1000, "m": True, "M": True,
        }
        session = FakeSession([response(200, json.dumps([trade]).encode("utf-8"))])
        result = research.query_aggregate_trades(session, "ETHUSDT", timestamp)
        self.assertTrue(result["trade_found"])
        self.assertEqual(result["rows_returned"], 1)
        self.assertEqual(result["request"]["limit"], 1)
        self.assertEqual(result["sample_trade"]["aggregate_trade_id"], 123)

    def test_hourly_quality_reports_all_missing_hours_intervals_and_archive_provenance(self):
        observed = self.index.delete(2)
        archive_manifest = [{
            "month": "2024-01", "url": "https://data.binance.vision/month.zip",
            "archive_sha256": "abc123", "checksum_verified": True, "status": "downloaded",
        }]
        result = research.hourly_quality(
            observed, "2024-01-01", "2024-01-01", archive_manifest
        )
        self.assertEqual(result["missing_hourly_bars"], 21)
        self.assertEqual(result["longest_gap_hours"], 2.0)
        self.assertEqual(len(result["missing_hour_timestamps"]), 21)
        self.assertEqual(len(result["missing_hour_details"]), 21)
        self.assertEqual([item["hours"] for item in result["missing_hour_intervals"]], [1, 20])
        self.assertEqual(result["missing_hour_details"][0]["archive_sha256"], "abc123")
        self.assertTrue(result["missing_hour_details"][0]["archive_checksum_verified"])
        self.assertFalse(result["complete"])

    def test_gap_reconciliation_classifies_only_one_source_as_unresolved(self):
        self.assertEqual(
            research.classify_gap_reconciliation(True, True, True),
            "confirmed_monthly_archive_omission",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(True, True, False),
            "official_source_value_mismatch",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(True, False),
            "single_official_representation_only",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(False, False),
            "both_kline_sources_empty_trade_status_unverified",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(
                False, False, api_request_succeeded=False
            ),
            "api_request_failed_daily_archive_absent_unresolved",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(
                False, False, agg_trades_found=False,
                agg_trades_request_succeeded=True, positive_control_passed=True,
            ),
            "confirmed_no_trade_interval",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(
                False, False, agg_trades_found=False,
                agg_trades_request_succeeded=True, positive_control_passed=False,
            ),
            "aggregate_trade_positive_control_failed_unresolved",
        )
        self.assertEqual(
            research.classify_gap_reconciliation(
                False, False, agg_trades_found=True,
                agg_trades_request_succeeded=True, positive_control_passed=False,
            ),
            "aggregate_trades_present_kline_missing",
        )

    def test_all_series_audit_continues_after_first_price_series_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(
                research, "download_klines",
                side_effect=[RuntimeError("spot ETH gap"), None, None, None],
            ) as prices, patch.object(
                research, "download_funding", return_value=root / "funding.csv"
            ) as funding:
                summary = research.audit_all_inputs(
                    "2024-01-01", "2024-01-01", root / "data", root / "out"
                )
            self.assertEqual(prices.call_count, 4)
            self.assertEqual(funding.call_count, 2)
            self.assertEqual(summary["price_series"]["spot_ETHUSDT"]["status"], "failed")
            # The mocked successful calls emitted no manifests, so the audit must
            # fail closed and create explicit artifact-ready failure records.
            self.assertEqual(summary["price_series"]["spot_BTCUSDT"]["status"], "failed")
            self.assertEqual(summary["price_series"]["um_ETHUSDT"]["status"], "failed")
            self.assertEqual(summary["price_series"]["um_BTCUSDT"]["status"], "failed")
            self.assertFalse(summary["complete"])
            self.assertTrue(summary["all_six_manifests_present"])
            self.assertEqual(summary["input_manifest_count"], 6)
            self.assertEqual(len(list((root / "data" / "raw").glob("*_archive_manifest.json"))), 4)
            self.assertEqual(len(list((root / "data" / "raw").glob("*_funding_manifest.json"))), 2)
            self.assertTrue((root / "out" / "data_audit_summary.json").exists())

    def test_all_series_audit_reconciles_both_spot_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(research, "download_klines"), patch.object(
                research, "download_funding"
            ), patch.object(
                research, "reconcile_spot_gaps",
                side_effect=[
                    {"symbol": "ETHUSDT", "reconciliation_complete": True},
                    {"symbol": "BTCUSDT", "reconciliation_complete": True},
                ],
            ) as reconcile:
                summary = research.audit_all_inputs(
                    "2024-01-01", "2024-01-01", root / "data", root / "out",
                    reconcile_gaps=True,
                )
            self.assertEqual(
                set(summary["gap_reconciliation"]), {"ETHUSDT", "BTCUSDT"}
            )
            self.assertEqual(reconcile.call_count, 2)
            self.assertTrue(summary["reconciliation_complete"])

    def test_gap_reconciliation_matches_rest_and_daily_archive_without_repairing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            all_hours = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
            missing = all_hours[2]
            source_csv = raw_dir / "spot_ETHUSDT_1h.csv"
            pd.DataFrame({
                "timestamp": [str(ts) for ts in all_hours if ts != missing],
                "volume": [10.0 for ts in all_hours if ts != missing],
            }).to_csv(source_csv, index=False)

            daily_rows = []
            for ts in all_hours:
                open_time = int(ts.timestamp() * 1000)
                daily_rows.append([
                    open_time, "100", "101", "99", "100.5", "10",
                    open_time + 3599999, "1000", "1", "5", "500", "0",
                ])
            daily_csv = pd.DataFrame(daily_rows).to_csv(index=False, header=False)
            archive_buffer = io.BytesIO()
            with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("ETHUSDT-1h-2024-01-01.csv", daily_csv)

            api_response = requests.Response()
            api_response.status_code = 200
            api_response.url = "https://api.binance.com/api/v3/klines"
            api_response._content = json.dumps([daily_rows[2]]).encode("utf-8")
            api_response.encoding = "utf-8"

            with patch.object(
                research, "_download_archive",
                return_value=(archive_buffer.getvalue(), True, None),
            ), patch.object(
                research.requests, "Session",
                return_value=FakeSession([api_response]),
            ):
                result = research.reconcile_spot_gaps(
                    "ETHUSDT", "2024-01-01", "2024-01-01", root
                )

            self.assertEqual(result["gap_count"], 1)
            self.assertEqual(result["rest_endpoint"], "https://data-api.binance.vision/api/v3/klines")
            self.assertEqual(result["daily_archives"]["2024-01-01"]["status"], "downloaded")
            self.assertEqual(
                result["gaps"][0]["classification"],
                "confirmed_monthly_archive_omission",
            )
            self.assertTrue(result["reconciliation_complete"])
            self.assertEqual(len(pd.read_csv(source_csv)), 23)

    def test_reconcile_spot_gaps_confirms_no_trade_only_after_same_day_positive_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            all_hours = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
            missing = all_hours[2]
            source_csv = raw_dir / "spot_ETHUSDT_1h.csv"
            pd.DataFrame({
                "timestamp": [str(ts) for ts in all_hours if ts != missing],
                "volume": [10.0 for ts in all_hours if ts != missing],
            }).to_csv(source_csv, index=False)

            daily_rows = []
            for ts in all_hours.delete(2):
                open_time = int(ts.timestamp() * 1000)
                daily_rows.append([
                    open_time, "100", "101", "99", "100.5", "10",
                    open_time + 3599999, "1000", "1", "5", "500", "0",
                ])
            daily_csv = pd.DataFrame(daily_rows).to_csv(index=False, header=False)
            archive_buffer = zip_csv(daily_csv, "ETHUSDT-1h-2024-01-01.csv")

            empty_kline = response(200, b"[]")
            control_time = int(all_hours[1].timestamp() * 1000) + 1000
            control_trade = {
                "a": 123, "p": "100.0", "q": "0.5", "f": 123, "l": 123,
                "T": control_time, "m": True, "M": True,
            }
            active_control = response(200, json.dumps([control_trade]).encode("utf-8"))
            empty_gap = response(200, b"[]")

            with patch.object(
                research, "_download_archive",
                return_value=(archive_buffer, True, None),
            ), patch.object(
                research.requests, "Session",
                return_value=FakeSession([empty_kline, active_control, empty_gap]),
            ):
                result = research.reconcile_spot_gaps(
                    "ETHUSDT", "2024-01-01", "2024-01-01", root
                )

            self.assertTrue(
                result["aggregate_trade_positive_controls"]["2024-01-01"]["positive_control_passed"]
            )
            self.assertEqual(
                result["gaps"][0]["classification"], "confirmed_no_trade_interval"
            )
            self.assertTrue(result["reconciliation_complete"])
            self.assertEqual(len(pd.read_csv(source_csv)), 23)

    def test_reconcile_spot_gaps_ignores_zero_volume_nearest_candle_for_positive_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            all_hours = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
            missing = all_hours[2]
            source_csv = raw_dir / "spot_ETHUSDT_1h.csv"
            pd.DataFrame({
                "timestamp": [str(ts) for ts in all_hours if ts != missing],
                "volume": [10.0 for ts in all_hours if ts != missing],
            }).to_csv(source_csv, index=False)

            daily_rows = []
            for ts in all_hours.delete(2):
                open_time = int(ts.timestamp() * 1000)
                volume = "10" if ts == all_hours[20] else "0"
                daily_rows.append([
                    open_time, "100", "101", "99", "100.5", volume,
                    open_time + 3599999, "1000", "1", "5", "500", "0",
                ])
            daily_csv = pd.DataFrame(daily_rows).to_csv(index=False, header=False)
            archive_buffer = zip_csv(daily_csv, "ETHUSDT-1h-2024-01-01.csv")

            control_time = int(all_hours[20].timestamp() * 1000) + 1000
            control_trade = {
                "a": 456, "p": "100.0", "q": "0.5", "f": 456, "l": 456,
                "T": control_time, "m": True, "M": True,
            }
            with patch.object(
                research, "_download_archive",
                return_value=(archive_buffer, True, None),
            ), patch.object(
                research.requests, "Session",
                return_value=FakeSession([
                    response(200, b"[]"),
                    response(200, json.dumps([control_trade]).encode("utf-8")),
                    response(200, b"[]"),
                ]),
            ):
                result = research.reconcile_spot_gaps(
                    "ETHUSDT", "2024-01-01", "2024-01-01", root
                )

            control = result["aggregate_trade_positive_controls"]["2024-01-01"]
            self.assertEqual(control["control_timestamp"], str(all_hours[20]))
            self.assertEqual(control["control_volume"], 10.0)
            self.assertEqual(control["candidate_source"], "daily_archive")
            self.assertTrue(control["positive_control_passed"])
            self.assertEqual(
                result["gaps"][0]["classification"], "confirmed_no_trade_interval"
            )

    def test_reconcile_spot_gaps_keeps_empty_trade_response_unresolved_when_control_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            all_hours = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
            missing = all_hours[2]
            source_csv = raw_dir / "spot_ETHUSDT_1h.csv"
            pd.DataFrame({
                "timestamp": [str(ts) for ts in all_hours if ts != missing],
                "volume": [10.0 for ts in all_hours if ts != missing],
            }).to_csv(source_csv, index=False)

            daily_rows = []
            for ts in all_hours.delete(2):
                open_time = int(ts.timestamp() * 1000)
                daily_rows.append([
                    open_time, "100", "101", "99", "100.5", "10",
                    open_time + 3599999, "1000", "1", "5", "500", "0",
                ])
            daily_csv = pd.DataFrame(daily_rows).to_csv(index=False, header=False)
            archive_buffer = zip_csv(daily_csv, "ETHUSDT-1h-2024-01-01.csv")
            unrelated_ms = int(
                pd.Timestamp("2024-01-01 12:05:00", tz="UTC").timestamp() * 1000
            )
            agg_csv = (
                "aggTradeId,price,quantity,firstTradeId,lastTradeId,timestamp,isBuyerMaker,isBestMatch\n"
                f"999,100.0,0.5,999,999,{unrelated_ms},true,true\n"
            )
            agg_archive = zip_csv(
                agg_csv, "ETHUSDT-aggTrades-2024-01-01.csv"
            )

            with patch.object(
                research, "_download_archive",
                side_effect=[
                    (archive_buffer, True, None),
                    (agg_archive, True, None),
                ],
            ), patch.object(
                research.requests, "Session",
                return_value=FakeSession([
                    response(200, b"[]"),
                    response(200, b"[]"),
                    response(200, b"[]"),
                ]),
            ):
                result = research.reconcile_spot_gaps(
                    "ETHUSDT", "2024-01-01", "2024-01-01", root
                )

            self.assertFalse(
                result["aggregate_trade_positive_controls"]["2024-01-01"]["positive_control_passed"]
            )
            self.assertEqual(
                result["gaps"][0]["classification"],
                "aggregate_trade_archive_positive_control_failed_unresolved",
            )
            self.assertFalse(result["reconciliation_complete"])

    def test_inspect_aggtrades_archive_counts_gap_and_positive_control(self):
        day = "2024-01-01"
        control = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")
        gap = pd.Timestamp("2024-01-01 02:00:00", tz="UTC")
        control_ms = int(pd.Timestamp("2024-01-01 01:05:00", tz="UTC").timestamp() * 1000)
        gap_ms = int(pd.Timestamp("2024-01-01 02:10:00", tz="UTC").timestamp() * 1000)
        csv_text = (
            "aggTradeId,price,quantity,firstTradeId,lastTradeId,timestamp,isBuyerMaker,isBestMatch\n"
            f"1,100.0,0.5,1,1,{control_ms},true,true\n"
            f"2,101.0,0.25,2,2,{gap_ms},false,true\n"
        )
        payload = zip_csv(csv_text, "ETHUSDT-aggTrades-2024-01-01.csv")

        result = research.inspect_aggtrades_archive(payload, day, [gap], control)

        self.assertEqual(result["status"], "PARSED")
        self.assertTrue(result["header_detected"])
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["gap_trade_counts"][str(gap)], 1)
        self.assertEqual(result["positive_control_trade_count"], 1)
        self.assertEqual(result["gap_trade_samples"][str(gap)]["aggregate_trade_id"], 2)

    def test_reconcile_spot_gaps_uses_checksum_verified_daily_aggtrades_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            all_hours = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")
            missing = all_hours[2]
            source_csv = raw_dir / "spot_ETHUSDT_1h.csv"
            pd.DataFrame({
                "timestamp": [str(ts) for ts in all_hours if ts != missing],
                "volume": [10.0 for ts in all_hours if ts != missing],
            }).to_csv(source_csv, index=False)

            daily_rows = []
            for ts in all_hours.delete(2):
                open_time = int(ts.timestamp() * 1000)
                daily_rows.append([
                    open_time, "100", "101", "99", "100.5", "10",
                    open_time + 3599999, "1000", "1", "5", "500", "0",
                ])
            daily_csv = pd.DataFrame(daily_rows).to_csv(index=False, header=False)
            kline_archive = zip_csv(daily_csv, "ETHUSDT-1h-2024-01-01.csv")

            control_ms = int(pd.Timestamp("2024-01-01 01:05:00", tz="UTC").timestamp() * 1000)
            agg_csv = (
                "aggTradeId,price,quantity,firstTradeId,lastTradeId,timestamp,isBuyerMaker,isBestMatch\n"
                f"123,100.0,0.5,123,123,{control_ms},true,true\n"
            )
            agg_archive = zip_csv(agg_csv, "ETHUSDT-aggTrades-2024-01-01.csv")

            with patch.object(
                research, "_download_archive",
                side_effect=[
                    (kline_archive, True, None),
                    (agg_archive, True, None),
                ],
            ), patch.object(
                research.requests, "Session",
                return_value=FakeSession([response(200, b"[]")]),
            ), patch.object(
                research, "query_aggregate_trades",
                return_value={"trade_found": False, "rows_returned": 0},
            ):
                result = research.reconcile_spot_gaps(
                    "ETHUSDT", "2024-01-01", "2024-01-01", root
                )

            entry = result["gaps"][0]
            self.assertTrue(
                result["daily_aggtrades_archives"]["2024-01-01"]["checksum_verified"]
            )
            self.assertEqual(
                result["daily_aggtrades_archives"]["2024-01-01"]["status"], "PARSED"
            )
            self.assertTrue(
                result["aggregate_trade_positive_controls"]["2024-01-01"][
                    "archive_positive_control_passed"
                ]
            )
            self.assertEqual(entry["aggregate_trade_archive"]["trade_count"], 0)
            self.assertEqual(entry["classification"], "confirmed_no_trade_interval")
            self.assertTrue(result["reconciliation_complete"])
            self.assertEqual(len(pd.read_csv(source_csv)), 23)

    def test_close_signal_executes_next_open_and_pnl_starts_after_that_open(self):
        close_signal = pd.Series([1.0, 0.0, 0.0, 0.0], index=self.index)
        executed = research.shift_signal_to_next_open(close_signal)
        self.assertEqual(executed.tolist(), [0.0, 1.0, 0.0, 0.0])
        bt = research.backtest(
            self.frame, executed, pd.Series(1.0, index=self.index),
            0.0, 0.0, 0.0, 1.0,
        )
        self.assertAlmostEqual(bt.loc[self.index[1], "gross_return"], 0.0)
        self.assertAlmostEqual(bt.loc[self.index[2], "gross_return"], 0.05)

    def test_entry_and_exit_turnover_costs_are_charged_on_both_legs(self):
        position = pd.Series([0.0, 1.0, 1.0, 0.0], index=self.index)
        bt = research.backtest(
            self.frame, position, pd.Series(1.0, index=self.index),
            10.0, 2.0, 1.0, 1.0,
        )
        self.assertAlmostEqual(bt["turnover"].sum(), 2.0)
        self.assertAlmostEqual(bt["cost"].sum(), 0.0026)

    def test_funding_ingestion_uses_checksum_verified_archive_and_fails_closed_on_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_text = "\n".join([
                "calc_time,funding_interval_hours,last_funding_rate",
                "1704067200000,8,0.0001",
            ]) + "\n"
            payload = zip_csv(csv_text, "ETHUSDT-fundingRate-2024-01.csv")
            with patch.object(
                research, "_download_archive",
                return_value=(payload, True, None),
            ) as download:
                with self.assertRaisesRegex(RuntimeError, "event semantics"):
                    research.download_funding(
                        "ETHUSDT", "2024-01-01", "2024-01-01", root
                    )
            self.assertEqual(download.call_count, 1)
            self.assertIn(
                "https://data.binance.vision/data/futures/um/monthly/fundingRate/"
                "ETHUSDT/ETHUSDT-fundingRate-2024-01.zip",
                download.call_args.args[0],
            )
            manifest = json.loads(
                (root / "raw" / "um_ETHUSDT_funding_manifest.json").read_text()
            )
            self.assertEqual(manifest["event_semantics"], "UNVERIFIED")
            self.assertEqual(manifest["completeness_status"], "PROVISIONAL_NOT_ACCEPTED")
            self.assertTrue(manifest["archives"][0]["checksum_verified"])
            self.assertEqual(manifest["rows"], 1)
            stored = pd.read_csv(root / "raw" / "um_ETHUSDT_funding.csv")
            self.assertIn("fundingRate", stored.columns)
            self.assertIn("funding_interval_hours", stored.columns)
            self.assertNotIn("last_funding_rate", stored.columns)

    def test_funding_ingestion_rejects_unverified_archive_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = zip_csv(
                "calc_time,funding_interval_hours,last_funding_rate\\n"
                "1704067200000,8,0.0001\\n"
            )
            with patch.object(
                research, "_download_archive",
                return_value=(payload, False, "checksum unavailable"),
            ):
                with self.assertRaisesRegex(RuntimeError, "failed_months=1"):
                    research.download_funding(
                        "ETHUSDT", "2024-01-01", "2024-01-01", root
                    )
            manifest = json.loads(
                (root / "raw" / "um_ETHUSDT_funding_manifest.json").read_text()
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["failed_months"][0]["month"], "2024-01")

    def test_funding_event_is_aligned_to_next_bar_when_off_grid(self):
        events = pd.Series(
            [0.001, 0.002],
            index=[self.index[0] + pd.Timedelta(minutes=30), self.index[3]],
        )
        aligned, quality = research.align_funding_events(events, self.index, "TEST")
        self.assertAlmostEqual(aligned.loc[self.index[1]], 0.001)
        self.assertAlmostEqual(aligned.loc[self.index[3]], 0.002)
        self.assertEqual(quality["off_grid_events"], 1)
        self.assertEqual(quality["max_alignment_lag_minutes"], 30.0)

    def test_funding_settlement_uses_position_held_before_settlement(self):
        position = pd.Series([1.0, 1.0, 1.0, 0.0], index=self.index)
        funding_eth = pd.Series([0.0, 0.001, 0.0, 0.0], index=self.index)
        funding_btc = pd.Series(0.0, index=self.index)
        bt = research.backtest(
            self.frame, position, pd.Series(1.0, index=self.index),
            0.0, 0.0, 0.0, 1.0, funding_eth, funding_btc,
        )
        self.assertAlmostEqual(bt.loc[self.index[1], "funding_pnl"], -0.0005)

    def test_funding_gap_is_not_mistaken_for_zero_funding(self):
        stamps = pd.DatetimeIndex([
            self.index[0],
            self.index[0] + pd.Timedelta(hours=8),
            self.index[0] + pd.Timedelta(hours=40),
        ])
        quality = research.funding_quality(
            stamps, self.index[0], self.index[0] + pd.Timedelta(hours=48)
        )
        self.assertFalse(quality["max_gap_ok"])
        self.assertFalse(quality["complete"])

    def test_missing_funding_file_fails_instead_of_returning_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                research.load_funding("ETHUSDT", self.index, Path(directory))

    def test_buy_hold_and_rebalanced_benchmarks_include_real_turnover(self):
        moving = self.frame.copy()
        moving["eth_open"] = [100.0, 120.0, 120.0, 120.0]
        moving["btc_open"] = [100.0, 100.0, 100.0, 110.0]
        buy_hold = research.benchmark_backtest(
            moving, self.index, (0.5, 0.5), False, 10.0, 0.0, 0.0
        )
        rebalanced = research.benchmark_backtest(
            moving, self.index, (0.5, 0.5), True, 10.0, 0.0, 0.0
        )
        self.assertGreater(rebalanced["turnover"].sum(), buy_hold["turnover"].sum())
        self.assertAlmostEqual(buy_hold.iloc[0]["cost"], 0.001)
        self.assertEqual(buy_hold.iloc[-1]["position"], 0.0)
        self.assertEqual(rebalanced.iloc[-1]["position"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[0]["held_w_eth"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[0]["held_w_btc"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[1]["held_w_eth"], 0.5)
        self.assertAlmostEqual(buy_hold.iloc[1]["held_w_btc"], 0.5)

    def test_flat_buy_hold_charges_one_entry_and_one_exit(self):
        flat = self.frame.copy()
        flat[["eth_open", "btc_open"]] = 100.0
        bt = research.benchmark_backtest(
            flat, self.index, (0.5, 0.5), False, 10.0, 0.0, 0.0
        )
        self.assertAlmostEqual(bt["turnover"].sum(), 2.0)
        self.assertAlmostEqual(bt["cost"].sum(), 0.002)

    def test_half_life_reports_exact_discrete_ar1_formula(self):
        rng = np.random.default_rng(123)
        n = 1200
        log_btc = np.cumsum(rng.normal(0.0, 0.002, n))
        spread = np.zeros(n)
        noise = rng.normal(0.0, 0.003, n)
        for i in range(1, n):
            spread[i] = 0.85 * spread[i - 1] + noise[i]
        idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
        frame = pd.DataFrame({
            "eth_close": np.exp(log_btc + spread),
            "btc_close": np.exp(log_btc),
        }, index=idx)
        result = research.diagnostics(frame)
        phi = result["ar1_phi"]
        if 0.0 < phi < 1.0:
            expected = -np.log(2.0) / np.log(phi)
            self.assertAlmostEqual(result["half_life_exact_ar1_bars"], expected)
            self.assertTrue(result["half_life_exact_valid"])
        self.assertEqual(result["diagnostic_scope"], "shared_static_ols_relationship")


    def test_sortino_downside_deviation_uses_all_observations_mixed(self):
        returns = pd.Series([0.10, -0.10, -0.10])
        expected = np.sqrt((0.0 + 0.01 + 0.01) / 3.0)
        self.assertAlmostEqual(research.downside_deviation(returns), expected)
        bt = self.metric_frame(returns)
        result = research.metrics(bt, 1)
        self.assertAlmostEqual(result["Sortino"], returns.mean() / expected)

    def test_sortino_downside_deviation_all_negative(self):
        returns = pd.Series([-0.10, -0.20])
        expected = np.sqrt((0.01 + 0.04) / 2.0)
        self.assertAlmostEqual(research.downside_deviation(returns), expected)

    def test_max_drawdown_includes_initial_nav(self):
        result = research.metrics(self.metric_frame([-0.10, 0.05]), 1)
        self.assertAlmostEqual(result["max_drawdown"], -0.10)

    def test_average_gross_exposure_aligns_with_returns(self):
        bt = self.metric_frame(
            [0.0, 0.0, 0.0], positions=[1.0, 1.0, 2.0],
            w_eth=[0.5, 0.5, 1.0], w_btc=[-0.5, -0.5, -1.0],
        )
        result = research.metrics(bt, 1)
        self.assertAlmostEqual(result["avg_gross_exposure"], 2.0 / 3.0)

    def test_funding_stress_is_um_only_and_rates_are_explicit(self):
        spot = research.stress_scenarios_for_market("spot")
        um = research.stress_scenarios_for_market("um")
        self.assertFalse(any("funding" in name.lower() for name in spot))
        funding_name = "UM funding: +10bp per leg for 3 settlements"
        self.assertIn(funding_name, um)
        self.assertIn("hypothetical, not observed", um[funding_name][3])
        self.assertAlmostEqual(um[funding_name][2], 0.003)

    def test_sharpe_interval_is_explicitly_exploratory_at_150_reps(self):
        result = research.metrics(self.metric_frame([0.01, -0.01, 0.0]), 1)
        self.assertEqual(result["Sharpe_CI_replications"], 150)
        self.assertIn("exploratory", result["Sharpe_CI_interpretation"])


if __name__ == "__main__":
    unittest.main()
