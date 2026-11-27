from __future__ import annotations

import datetime as dt
import unittest
from unittest.mock import patch

import etf_relative_flow_source_preflight as model


class ETFRelativeFlowSourcePreflightTests(unittest.TestCase):
    def test_parser_reads_btc_table_and_skips_all_dash_holiday(self):
        html = b"""
        <html><body><table>
          <tr><th>Date</th><th>IBIT</th><th>FBTC</th><th>GBTC</th><th>Total</th></tr>
          <tr><td>23 Jul 2024</td><td>10.0</td><td>2.0</td><td>(5.0)</td><td>7.0</td></tr>
          <tr><td>24 Jul 2024</td><td>-</td><td>-</td><td>-</td><td>0.0</td></tr>
        </table></body></html>
        """
        values, meta = model.parse_farside_html(html, "fixture BTC")
        self.assertEqual(values, {dt.date(2024, 7, 23): 7.0})
        self.assertEqual(meta["numeric_flow_rows"], 1)
        self.assertEqual(meta["fund_columns"], ["IBIT", "FBTC", "GBTC"])

    def test_parser_accepts_blank_first_header_cell_on_eth_table(self):
        html = b"""
        <table>
          <tr><th></th><th>ETHA</th><th>FETH</th><th>ETHE</th><th>Total</th></tr>
          <tr><td>23 Jul 2024</td><td>266.5</td><td>71.3</td><td>(484.1)</td><td>(146.3)</td></tr>
        </table>
        """
        values, meta = model.parse_farside_html(html, "fixture ETH")
        self.assertEqual(values[dt.date(2024, 7, 23)], -146.3)
        self.assertEqual(meta["header"][0], "Date")

    def test_parser_handles_parentheses_and_commas(self):
        self.assertEqual(model.parse_flow_value("(1,234.5)"), -1234.5)
        self.assertEqual(model.parse_flow_value("1,234.5"), 1234.5)
        self.assertIsNone(model.parse_flow_value("-"))

    def test_parser_rejects_total_that_does_not_reconcile(self):
        html = b"""
        <table>
          <tr><th>Date</th><th>A</th><th>B</th><th>Total</th></tr>
          <tr><td>23 Jul 2024</td><td>10.0</td><td>2.0</td><td>99.0</td></tr>
        </table>
        """
        with self.assertRaisesRegex(ValueError, "do not reconcile"):
            model.parse_farside_html(html, "fixture")

    def test_parser_rejects_duplicate_flow_dates(self):
        html = b"""
        <table>
          <tr><th>Date</th><th>A</th><th>B</th><th>Total</th></tr>
          <tr><td>23 Jul 2024</td><td>10.0</td><td>2.0</td><td>12.0</td></tr>
          <tr><td>23 Jul 2024</td><td>8.0</td><td>2.0</td><td>10.0</td></tr>
        </table>
        """
        with self.assertRaisesRegex(ValueError, "duplicate flow date"):
            model.parse_farside_html(html, "fixture")

    def test_flow_panel_hash_is_canonical_and_cutoff_is_enforced(self):
        btc = {
            dt.date(2024, 7, 23): 100.0,
            dt.date(2024, 7, 24): -50.0,
            dt.date(2024, 7, 25): 12.5,
        }
        eth = {
            dt.date(2024, 7, 23): 25.0,
            dt.date(2024, 7, 24): -10.0,
            dt.date(2024, 7, 26): 5.0,
        }
        panel, meta = model.build_flow_panel(
            btc, eth, dt.date(2024, 7, 25), min_rows=2, max_unmatched=2
        )
        self.assertEqual([row["date"] for row in panel], [dt.date(2024, 7, 23), dt.date(2024, 7, 24)])
        self.assertEqual(meta["rows"], 2)
        self.assertEqual(len(meta["sha256"]), 64)
        self.assertEqual(len(meta["unmatched_dates"]), 1)

    def test_flow_panel_fails_closed_on_excess_unmatched_dates(self):
        btc = {dt.date(2024, 7, 23) + dt.timedelta(days=i): float(i) for i in range(4)}
        eth = {dt.date(2024, 7, 23): 0.0}
        with self.assertRaisesRegex(ValueError, "do not align"):
            model.build_flow_panel(btc, eth, dt.date(2024, 7, 26), min_rows=1, max_unmatched=1)

    def test_archive_spec_builder_uses_requested_symbol(self):
        base_spec = {
            "kind": "daily",
            "tag": "2026-11-26",
            "expected_date": "2026-11-26",
            "filename": "BTCUSDT-1d-2026-11-26.zip",
            "url": "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2026-11-26.zip",
        }
        with patch.object(model.market, "build_archive_specs", return_value=[base_spec]):
            specs = model.build_archive_specs_for_symbol(
                "ETHUSDT", dt.date(2026, 11, 26), dt.date(2026, 11, 26), dt.date(2026, 11, 27)
            )
        self.assertIn("ETHUSDT", specs[0]["filename"])
        self.assertIn("/ETHUSDT/1d/", specs[0]["url"])


if __name__ == "__main__":
    unittest.main()
