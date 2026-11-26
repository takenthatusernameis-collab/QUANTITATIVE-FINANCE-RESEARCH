from __future__ import annotations
import datetime as dt
import hashlib
import io
import json
import math
import unittest
import zipfile
from unittest.mock import patch
import stlfsi4_btc_downside_semivariance as model


class STLFSI4BitcoinTests(unittest.TestCase):
    def test_fred_parser_accepts_negative_values_and_skips_missing(self):
        body = b"observation_date,STLFSI4\n2026-10-30,-0.48\n2026-11-06,.\n2026-11-13,0.12\n"
        values = model.parse_fred(body)
        self.assertEqual(len(values), 2)
        self.assertAlmostEqual(values[dt.date(2026, 10, 30)], -0.48)

    def test_fred_parser_rejects_duplicate_dates(self):
        body = b"observation_date,STLFSI4\n2026-10-30,-0.4\n2026-10-30,-0.3\n"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred(body)

    def archive_row(self, day, close, unit="ms"):
        scale = 1_000_000 if unit == "us" else 1_000
        day_units = 86_400_000_000 if unit == "us" else 86_400_000
        open_time = int(dt.datetime.combine(day, dt.time(), dt.timezone.utc).timestamp() * scale)
        close_time = open_time + day_units - 1
        return f"{open_time},{close},{close},{close},{close},1,{close_time},1,1,1,1,0"

    def test_archive_parser_accepts_millisecond_and_microsecond_eras(self):
        old_day = dt.date(2024, 12, 31)
        new_day = dt.date(2025, 1, 1)
        old, old_unit = model.parse_archive_klines(
            (self.archive_row(old_day, "93000", "ms") + "\n").encode()
        )
        new, new_unit = model.parse_archive_klines(
            (self.archive_row(new_day, "94000", "us") + "\n").encode()
        )
        self.assertEqual(old_unit, "milliseconds")
        self.assertEqual(new_unit, "microseconds")
        self.assertEqual(old[old_day], 93000.0)
        self.assertEqual(new[new_day], 94000.0)

    def test_archive_parser_accepts_optional_header_and_rejects_bad_daily_bounds(self):
        day = dt.date(2026, 11, 24)
        csv_body = (
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,"
            "number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore\n"
            + self.archive_row(day, "91000", "us") + "\n"
        ).encode()
        parsed, unit = model.parse_archive_klines(csv_body)
        self.assertEqual(unit, "microseconds")
        self.assertEqual(parsed, {day: 91000.0})
        bad = self.archive_row(day, "91000", "us").split(",")
        bad[6] = str(int(bad[6]) - 1)
        with self.assertRaisesRegex(ValueError, "complete UTC day"):
            model.parse_archive_klines((",".join(bad) + "\n").encode())

    def test_checksum_sidecar_must_match_filename_and_sha256_shape(self):
        digest = "a" * 64
        self.assertEqual(
            model.parse_checksum(
                f"{digest}  BTCUSDT-1d-2026-11-24.zip\n".encode(),
                "BTCUSDT-1d-2026-11-24.zip",
            ),
            digest,
        )
        with self.assertRaisesRegex(ValueError, "different archive"):
            model.parse_checksum(
                f"{digest}  OTHER.zip\n".encode(), "BTCUSDT-1d-2026-11-24.zip"
            )
        with self.assertRaisesRegex(ValueError, "Invalid SHA-256"):
            model.parse_checksum(b"not-a-checksum", "file.zip")

    def test_archive_spec_uses_monthly_history_and_daily_current_month(self):
        specs = model.build_archive_specs(dt.date(2017, 8, 17), dt.date(2026, 11, 24))
        self.assertEqual(specs[0]["kind"], "monthly")
        self.assertEqual(specs[0]["tag"], "2017-08")
        self.assertEqual(specs[-1]["kind"], "daily")
        self.assertEqual(specs[-1]["tag"], "2026-11-24")
        self.assertEqual(sum(item["kind"] == "daily" for item in specs), 24)
        self.assertIn("/data/spot/monthly/klines/BTCUSDT/1d/", specs[0]["url"])
        self.assertIn("/data/spot/daily/klines/BTCUSDT/1d/", specs[-1]["url"])

    def test_archive_planner_uses_daily_files_until_first_monday_release(self):
        specs = model.build_archive_specs(
            dt.date(2017, 8, 17), dt.date(2026, 11, 30), dt.date(2026, 12, 2)
        )
        november = [x for x in specs if x["tag"].startswith("2026-11")]
        self.assertEqual(len(november), 30)
        self.assertTrue(all(x["kind"] == "daily" for x in november))
        specs_after_release = model.build_archive_specs(
            dt.date(2017, 8, 17), dt.date(2026, 11, 30), dt.date(2026, 12, 7)
        )
        november_after_release = [x for x in specs_after_release if x["tag"] == "2026-11"]
        self.assertEqual(len(november_after_release), 1)
        self.assertEqual(november_after_release[0]["kind"], "monthly")

    def test_archive_download_requires_checksum_and_single_csv(self):
        day = dt.date(2026, 11, 24)
        filename = "BTCUSDT-1d-2026-11-24.zip"
        csv_body = (self.archive_row(day, "90000", "us") + "\n").encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(filename.replace(".zip", ".csv"), csv_body)
        payload = buffer.getvalue()
        checksum = f"{hashlib.sha256(payload).hexdigest()}  {filename}\n".encode()
        spec = {
            "kind": "daily", "tag": day.isoformat(), "expected_date": day.isoformat(),
            "filename": filename, "url": "https://data.binance.vision/example/" + filename,
        }
        with patch.object(model.base, "fetch_bytes", side_effect=[payload, checksum]) as fetch:
            prices, manifest = model.download_binance_archive(spec)
        self.assertEqual(prices, {day: 90000.0})
        self.assertTrue(manifest["checksum_verified"])
        self.assertEqual(fetch.call_count, 2)
        bad_checksum = b"0" * 64 + b"  " + filename.encode()
        with patch.object(model.base, "fetch_bytes", side_effect=[payload, bad_checksum]):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                model.download_binance_archive(spec)

    def test_downside_semivariance_is_one_sided_and_percent_squared(self):
        self.assertAlmostEqual(model.semi_var_pct2([-0.01, 0.02, -0.03, 0.0, 0.01]), 2.0)
        self.assertEqual(model.semi_var_pct2([0.01, 0.02]), 0.0)

    def make_market(self, days=1200, weeks=150):
        start = dt.date(2017, 8, 17)
        prices = {
            start + dt.timedelta(days=i):
            10000.0 * math.exp(0.0002 * i + 0.03 * math.sin(i / 9.0) + 0.01 * math.sin(i / 2.7))
            for i in range(days)
        }
        first_friday = dt.date(2017, 8, 18)
        stress = {
            first_friday + dt.timedelta(days=7 * i):
            -0.5 + i * 0.001 + 0.04 * math.sin(i / 4.0)
            for i in range(weeks)
        }
        return stress, prices

    def test_event_alignment_uses_seven_day_lag_and_next_five_returns(self):
        stress, prices = self.make_market()
        events, meta = model.build_events(stress, prices)
        self.assertGreater(len(events), 40)
        first = events[0]
        self.assertEqual(first["signal_date"], first["week_end_date"] + dt.timedelta(days=7))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        week_dates = sorted(stress)
        wi = week_dates.index(first["week_end_date"])
        self.assertAlmostEqual(first["stlfsi4_4w_change"], stress[week_dates[wi]] - stress[week_dates[wi - 4]])
        self.assertEqual(meta["release_lag_days"], 7)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_irregular_stress_week_is_skipped(self):
        stress, prices = self.make_market()
        stress.pop(sorted(stress)[30])
        _, meta = model.build_events(stress, prices)
        self.assertGreater(meta["skipped"]["irregular_stress_window"], 0)

    def test_walk_forward_uses_104_fully_matured_events(self):
        events, start = [], dt.date(2020, 1, 3)
        for i in range(106):
            signal = start + dt.timedelta(days=7 * i)
            events.append({
                "signal_date": signal, "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(i / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(i / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(i / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(i / 9.0),
                "stlfsi4_4w_change": 0.05 * math.cos(i / 5.0),
                "target_semivariance_pct2": 1.0,
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)

    def test_decision_requires_both_periods_and_paired_interval(self):
        val, test = {"n": 50, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": 1.0}
        paired = {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05}
        self.assertEqual(model.decide(val, test, paired)[0], "BACKTESTED")
        self.assertEqual(model.decide(val, {"n": 100, "rmse_improvement_pct": -1.0}, paired)[0], "INCONCLUSIVE")
        self.assertEqual(model.decide({"n": 50, "rmse_improvement_pct": -2.0}, {"n": 100, "rmse_improvement_pct": -1.0}, {"ci_95_low_bp2": -0.2, "ci_95_high_bp2": -0.01})[0], "REJECTED")

    def test_coverage_rejects_daily_price_gap(self):
        stress, prices = self.make_market(days=3388, weeks=484)
        del prices[sorted(prices)[100]]
        with self.assertRaisesRegex(ValueError, "missing UTC day"):
            model.validate_coverage(stress, prices, dt.date(2026, 11, 25))


if __name__ == "__main__":
    unittest.main()
