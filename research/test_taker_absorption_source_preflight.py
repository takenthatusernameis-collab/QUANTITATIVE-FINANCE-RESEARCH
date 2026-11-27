from __future__ import annotations

import datetime as dt
import hashlib
import io
import unittest
import zipfile
from unittest.mock import patch

import taker_absorption_source_preflight as model


class TakerAbsorptionSourcePreflightTests(unittest.TestCase):
    def row(self, day=dt.date(2026, 11, 25), taker_buy=0.6, volume=1.0, unit="ms"):
        scale = 1_000_000 if unit == "us" else 1_000
        day_units = 86_400_000_000 if unit == "us" else 86_400_000
        open_time = int(
            dt.datetime.combine(day, dt.time(), dt.timezone.utc).timestamp() * scale
        )
        close_time = open_time + day_units - 1
        return ",".join([
            str(open_time), "100", "110", "90", "105", str(volume),
            str(close_time), "105", "100", str(taker_buy), str(taker_buy * 105), "0"
        ])

    def test_parser_reads_documented_taker_fields_in_millisecond_and_microsecond_eras(self):
        day = dt.date(2024, 12, 31)
        rows_ms, unit_ms = model.parse_kline_archive((self.row(day, 0.6, 1.0, "ms") + "\n").encode())
        rows_us, unit_us = model.parse_kline_archive((self.row(day, 0.4, 1.0, "us") + "\n").encode())
        self.assertEqual(unit_ms, "milliseconds")
        self.assertEqual(unit_us, "microseconds")
        self.assertAlmostEqual(rows_ms[day]["taker_imbalance"], 0.2)
        self.assertAlmostEqual(rows_us[day]["taker_imbalance"], -0.2)

    def test_parser_accepts_optional_documented_header(self):
        day = dt.date(2026, 11, 25)
        header = (
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,"
            "number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore\n"
        )
        rows, _ = model.parse_kline_archive((header + self.row(day) + "\n").encode())
        self.assertIn(day, rows)

    def test_parser_rejects_non_twelve_column_schema(self):
        bad = self.row().split(",")[:-1]
        with self.assertRaisesRegex(ValueError, "12 Binance kline columns"):
            model.parse_kline_archive((",".join(bad) + "\n").encode())

    def test_parser_rejects_taker_buy_volume_above_total(self):
        with self.assertRaisesRegex(ValueError, "outside total base volume"):
            model.parse_kline_archive((self.row(taker_buy=1.2, volume=1.0) + "\n").encode())

    def test_parser_rejects_incomplete_utc_daily_candle(self):
        fields = self.row().split(",")
        fields[6] = str(int(fields[6]) - 1)
        with self.assertRaisesRegex(ValueError, "complete UTC daily candle"):
            model.parse_kline_archive((",".join(fields) + "\n").encode())

    def test_parser_preserves_zero_volume_as_missing_flow_not_zero_imbalance(self):
        row = self.row(taker_buy=0.0, volume=0.0)
        rows, _ = model.parse_kline_archive((row + "\n").encode())
        self.assertIsNone(rows[dt.date(2026, 11, 25)]["taker_imbalance"])

    def test_checksum_sidecar_and_archive_are_both_required(self):
        day = dt.date(2026, 11, 25)
        filename = "BTCUSDT-1d-2026-11-25.zip"
        csv_body = (self.row(day) + "\n").encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(filename.replace(".zip", ".csv"), csv_body)
        payload = buffer.getvalue()
        checksum = f"{hashlib.sha256(payload).hexdigest()}  {filename}\n".encode()
        spec = {
            "kind": "daily", "tag": day.isoformat(), "expected_date": day.isoformat(),
            "filename": filename, "url": "https://data.binance.vision/example/" + filename,
        }
        with patch.object(model.market.base, "fetch_bytes", side_effect=[payload, checksum]) as fetch:
            rows, manifest = model.download_archive(spec)
        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(manifest["checksum_verified"])
        self.assertEqual(rows[day]["taker_imbalance"], 0.2)

        bad_checksum = b"0" * 64 + b"  " + filename.encode()
        with patch.object(model.market.base, "fetch_bytes", side_effect=[payload, bad_checksum]):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                model.download_archive(spec)

    def test_coverage_rejects_missing_daily_rows(self):
        start = dt.date(2026, 11, 24)
        rows = {
            start: {"volume": 1.0, "taker_imbalance": 0.2},
            start + dt.timedelta(days=2): {"volume": 1.0, "taker_imbalance": -0.2},
        }
        with self.assertRaisesRegex(ValueError, "missing=1"):
            model.validate_coverage(rows, start, start + dt.timedelta(days=2))

    def test_coverage_accepts_exact_complete_daily_population(self):
        start = dt.date(2026, 11, 24)
        rows = {
            start + dt.timedelta(days=i): {"volume": 1.0, "taker_imbalance": (-1) ** i * 0.2}
            for i in range(3)
        }
        result = model.validate_coverage(rows, start, start + dt.timedelta(days=2))
        self.assertEqual(result["observed_daily_rows"], 3)
        self.assertEqual(result["missing_dates"], [])


if __name__ == "__main__":
    unittest.main()
