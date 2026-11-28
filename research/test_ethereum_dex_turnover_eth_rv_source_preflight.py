import datetime as dt
import json
import unittest
from unittest.mock import patch

import ethereum_dex_turnover_eth_rv_source_preflight as model


def unix(day):
    return int(dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc).timestamp())


def dex_row(day, volume=1_000_000.0):
    return {"date": unix(day), "totalVolume": volume}


def tvl_row(day, tvl=50_000_000_000.0):
    return {"date": unix(day), "tvl": tvl}


def hourly_row(stamp, close=2000.0, volume=10.0, unit="milliseconds"):
    scale = 1_000_000 if unit == "microseconds" else 1_000
    interval = model.INTERVAL_MS * (1_000 if unit == "microseconds" else 1)
    open_time = int(stamp.timestamp() * scale)
    return [
        str(open_time), str(close), str(close + 2), str(close - 2), str(close + 1),
        str(volume), str(open_time + interval - 1), str(volume * close),
        "100", str(volume / 2), str(volume * close / 2), "0",
    ]


class EthereumDexTurnoverSourcePreflightTests(unittest.TestCase):
    def test_dex_parser_reads_documented_total_data_chart_field(self):
        day = dt.date(2021, 1, 1)
        body = json.dumps({"totalDataChart": [
            [unix(day), 1_000_000.0],
            [unix(day + dt.timedelta(days=1)), 2_000_000.0],
        ]}).encode()
        parsed = model.parse_dex_history(body)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[day], 1_000_000.0)

    def test_tvl_parser_reads_daily_date_and_tvl(self):
        day = dt.date(2021, 1, 1)
        parsed = model.parse_tvl_history(json.dumps([tvl_row(day)]).encode())
        self.assertEqual(parsed[day], 50_000_000_000.0)

    def test_parsers_reject_missing_fields_duplicates_and_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "unix_timestamp"):
            model.parse_dex_history(b'{"totalDataChart":[[1609459200]]}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_dex_history(json.dumps({"totalDataChart": [
                [unix(dt.date(2021, 1, 1)), 1.0],
                [unix(dt.date(2021, 1, 1)), 2.0],
            ]}).encode())
        zero_tvl = model.parse_tvl_history(
            json.dumps([tvl_row(dt.date(2017, 1, 1), 0)]).encode()
        )
        self.assertEqual(zero_tvl[dt.date(2017, 1, 1)], 0.0)
        with self.assertRaisesRegex(ValueError, "must be \\[unix_timestamp, USD_volume\\]"):
            model.parse_dex_history(b'{"totalDataChart":[1]}')

    def test_daily_coverage_requires_depth_freshness_and_bounded_gaps(self):
        values = {}
        day = model.SAMPLE_START
        while day <= model.MIN_LATEST_DATE:
            values[day] = 1_000_000.0
            day += dt.timedelta(days=1)
        result = model.validate_daily_coverage(values, "DEX")
        self.assertGreaterEqual(result["rows_in_frozen_window"], model.MIN_DAILY_ROWS)
        self.assertEqual(result["last_date"], model.MIN_LATEST_DATE.isoformat())
        gap = dict(values)
        for offset in range(10, 14):
            gap.pop(model.SAMPLE_START + dt.timedelta(days=offset))
        with self.assertRaisesRegex(ValueError, "gap"):
            model.validate_daily_coverage(gap, "DEX")
        zero_tvl = dict(values)
        zero_tvl[model.SAMPLE_START + dt.timedelta(days=20)] = 0.0
        with self.assertRaisesRegex(ValueError, "non-positive"):
            model.validate_daily_coverage(zero_tvl, "TVL", require_positive=True)

    def test_daily_coverage_rejects_stale_or_shallow_series(self):
        short = {model.SAMPLE_START + dt.timedelta(days=i): 1.0 for i in range(100)}
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            model.validate_daily_coverage(short, "TVL")
        stale = {}
        day = model.SAMPLE_START
        cutoff = model.MIN_LATEST_DATE - dt.timedelta(days=20)
        while day <= cutoff:
            stale[day] = 1.0
            day += dt.timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "ends before"):
            model.validate_daily_coverage(stale, "TVL")

    def test_exchange_info_requires_exact_active_ethusdt_spot(self):
        body = json.dumps({"symbols": [{
            "symbol": "ETHUSDT", "status": "TRADING", "baseAsset": "ETH",
            "quoteAsset": "USDT", "isSpotTradingAllowed": True,
        }]}).encode()
        self.assertEqual(model.validate_exchange_info(body)["symbol"], "ETHUSDT")
        inactive = json.dumps({"symbols": [{
            "symbol": "ETHUSDT", "status": "BREAK", "baseAsset": "ETH",
            "quoteAsset": "USDT",
        }]}).encode()
        with self.assertRaisesRegex(ValueError, "expected active"):
            model.validate_exchange_info(inactive)

    def test_archive_checksum_parser_requires_sha256_and_matching_filename(self):
        digest = "a" * 64
        self.assertEqual(
            model.parse_archive_checksum(f"{digest}  ETHUSDT-1h-2021-01.zip".encode(), "ETHUSDT-1h-2021-01.zip"),
            digest,
        )
        with self.assertRaisesRegex(ValueError, "different archive"):
            model.parse_archive_checksum(f"{digest}  other.zip".encode(), "ETHUSDT-1h-2021-01.zip")
        with self.assertRaisesRegex(ValueError, "Invalid SHA-256"):
            model.parse_archive_checksum(b"not-a-checksum", "ETHUSDT-1h-2021-01.zip")
    def test_monthly_archive_specs_cover_exact_complete_months(self):
        specs = model.build_monthly_archive_specs(dt.date(2021, 1, 1), dt.date(2021, 3, 31))
        self.assertEqual([item["tag"] for item in specs], ["2021-01", "2021-02", "2021-03"])
        self.assertIn("/ETHUSDT/1h/ETHUSDT-1h-2021-02.zip", specs[1]["url"])
        with self.assertRaisesRegex(ValueError, "complete UTC calendar months"):
            model.build_monthly_archive_specs(dt.date(2021, 1, 2), dt.date(2021, 3, 31))

    def test_hourly_parser_validates_12_column_rows_and_timestamp_units(self):
        start = dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc)
        rows = [hourly_row(start), hourly_row(start + dt.timedelta(hours=1), close=2001.0)]
        body = ("\n".join(",".join(row) for row in rows) + "\n").encode()
        parsed, unit = model.parse_hourly_archive(body)
        self.assertEqual(unit, "milliseconds")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[start], 2001.0)

    def test_hourly_parser_accepts_microsecond_timestamp_archives(self):
        start = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
        row = hourly_row(start, unit="microseconds")
        parsed, unit = model.parse_hourly_archive((",".join(row) + "\n").encode())
        self.assertEqual(unit, "microseconds")
        self.assertEqual(parsed[start], 2001.0)

    def test_hourly_parser_accepts_last_trade_close_time_inside_bar(self):
        start = dt.datetime(2023, 3, 24, 20, tzinfo=dt.timezone.utc)
        row = hourly_row(start)
        row[6] = str(int(row[0]) + 2_383_061)
        parsed, unit = model.parse_hourly_archive((",".join(row) + "\n").encode())
        self.assertEqual(unit, "milliseconds")
        self.assertEqual(parsed[start], 2001.0)

    def test_hourly_parser_rejects_close_time_outside_bar(self):
        start = dt.datetime(2023, 3, 24, 20, tzinfo=dt.timezone.utc)
        row = hourly_row(start)
        row[6] = str(int(row[0]) + model.INTERVAL_MS)
        with self.assertRaisesRegex(ValueError, "invalid UTC hourly bounds"):
            model.parse_hourly_archive((",".join(row) + "\n").encode())
    def test_hourly_parser_rejects_bad_interval_and_invalid_ohlc(self):
        start = dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc)
        row = hourly_row(start)
        row[0] = str(int(row[0]) + 1)
        with self.assertRaisesRegex(ValueError, "invalid UTC hourly bounds"):
            model.parse_hourly_archive((",".join(row) + "\n").encode())
        bad = hourly_row(start)
        bad[3] = "3000"
        with self.assertRaisesRegex(ValueError, "OHLC relationship"):
            model.parse_hourly_archive((",".join(bad) + "\n").encode())

    def test_archive_merge_accepts_millisecond_and_microsecond_months(self):
        ms_stamp = dt.datetime(2024, 12, 31, 23, tzinfo=dt.timezone.utc)
        us_stamp = dt.datetime(2025, 1, 1, 0, tzinfo=dt.timezone.utc)
        ms_rows, ms_unit = model.parse_hourly_archive((
            ",".join(hourly_row(ms_stamp, unit="milliseconds")) + "\\n"
        ).encode())
        us_rows, us_unit = model.parse_hourly_archive((
            ",".join(hourly_row(us_stamp, unit="microseconds")) + "\\n"
        ).encode())
        merged, units = model.merge_hourly_archive_parts([(ms_rows, ms_unit), (us_rows, us_unit)])
        self.assertEqual(len(merged), 2)
        self.assertEqual(units, ["microseconds", "milliseconds"])
        with self.assertRaisesRegex(ValueError, "Duplicate ETHUSDT hourly timestamps"):
            model.merge_hourly_archive_parts([(ms_rows, ms_unit), (ms_rows, ms_unit)])

    def test_daily_archive_specs_are_official_and_date_scoped(self):
        day = dt.date(2021, 2, 11)
        specs = model.build_daily_archive_specs([day, day])
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["kind"], "daily")
        self.assertEqual(specs[0]["tag"], "2021-02-11")
        self.assertIn("/data/spot/daily/klines/ETHUSDT/1h/ETHUSDT-1h-2021-02-11.zip", specs[0]["url"])

    def test_daily_archive_gap_repair_fills_only_missing_hours_and_reconciles_overlaps(self):
        day = dt.date(2021, 2, 11)
        start = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc)
        daily = {start + dt.timedelta(hours=i): 2000.0 + i for i in range(24)}
        monthly = dict(daily)
        missing = start + dt.timedelta(hours=4)
        monthly.pop(missing)
        merged, record = model.reconcile_daily_gap_patch(monthly, daily, day)
        self.assertEqual(merged, daily)
        self.assertEqual(record["filled_hour_count"], 1)
        self.assertEqual(record["filled_hours"], [missing.isoformat()])
        self.assertEqual(record["overlap_match_count"], 23)

    def test_daily_archive_gap_repair_rejects_mismatch_and_records_remaining_daily_gap(self):
        day = dt.date(2021, 2, 11)
        start = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc)
        daily = {start + dt.timedelta(hours=i): 2000.0 + i for i in range(24)}
        monthly = dict(daily)
        monthly.pop(start + dt.timedelta(hours=4))
        mismatch = dict(daily)
        mismatch[start + dt.timedelta(hours=5)] += 0.01
        with self.assertRaisesRegex(ValueError, "close mismatch"):
            model.reconcile_daily_gap_patch(monthly, mismatch, day)
        incomplete = dict(daily)
        incomplete.pop(start + dt.timedelta(hours=6))
        merged, record = model.reconcile_daily_gap_patch(monthly, incomplete, day)
        self.assertEqual(merged, daily)
        self.assertEqual(record["filled_hour_count"], 1)
        self.assertEqual(record["daily_missing_hours"], [(start + dt.timedelta(hours=6)).isoformat()])

    def test_hourly_coverage_reports_sparse_gaps_without_filling_them(self):
        start_day = dt.date(2021, 1, 1)
        stamps = [
            dt.datetime(2021, 1, 1, hour, tzinfo=dt.timezone.utc)
            for hour in range(24)
        ]
        rows = {stamp: 2000.0 + index for index, stamp in enumerate(stamps)}
        rows.pop(stamps[5])
        with patch.object(model, "SAMPLE_START", start_day), patch.object(model, "SAMPLE_END", start_day), patch.object(model, "MAX_MISSING_FRACTION", 0.05):
            result = model.validate_hourly_coverage(rows)
        self.assertEqual(result["missing_hours"], 1)
        self.assertEqual(result["missing_timestamps"], [stamps[5].isoformat()])
        self.assertEqual(result["maximum_consecutive_missing_hours"], 1)
        self.assertEqual(len(rows), 23)

    def test_hourly_coverage_rejects_too_many_or_consecutive_gaps(self):
        start_day = dt.date(2021, 1, 1)
        stamps = [
            dt.datetime(2021, 1, 1, hour, tzinfo=dt.timezone.utc)
            for hour in range(24)
        ]
        rows = {stamp: 2000.0 + index for index, stamp in enumerate(stamps)}
        for stamp in stamps[5:8]:
            rows.pop(stamp)
        with patch.object(model, "SAMPLE_START", start_day), patch.object(model, "SAMPLE_END", start_day), patch.object(model, "MAX_MISSING_FRACTION", 0.2):
            with self.assertRaisesRegex(ValueError, "sparse-gap limits"):
                model.validate_hourly_coverage(rows)

    def test_hourly_coverage_rejects_out_of_window_rows(self):
        start_day = dt.date(2021, 1, 1)
        stamps = [
            dt.datetime(2021, 1, 1, hour, tzinfo=dt.timezone.utc)
            for hour in range(24)
        ]
        rows = {stamp: 2000.0 + index for index, stamp in enumerate(stamps)}
        rows[dt.datetime(2021, 1, 2, 0, tzinfo=dt.timezone.utc)] = 2100.0
        with patch.object(model, "SAMPLE_START", start_day), patch.object(model, "SAMPLE_END", start_day):
            with self.assertRaisesRegex(ValueError, "out-of-window"):
                model.validate_hourly_coverage(rows)



if __name__ == "__main__":
    unittest.main()
