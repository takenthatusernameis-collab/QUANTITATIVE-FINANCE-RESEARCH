from __future__ import annotations

import csv
import datetime as dt
import io
import unittest

import sp500_weekend_btc_source_preflight as model


UTC = dt.timezone.utc


def sp500_csv(
    end: dt.date = dt.date(2026, 11, 27),
    start: dt.date = dt.date(2017, 8, 18),
) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["observation_date", "SP500"])
    day = start
    count = 0
    while day <= end:
        if day.weekday() < 5:
            writer.writerow([day.isoformat(), 2400.0 + count])
            count += 1
        day += dt.timedelta(days=1)
    return output.getvalue().encode("utf-8")


def hourly_row(open_time: int, close_time: int) -> str:
    return ",".join([
        str(open_time), "100", "110", "90", "105", "1",
        str(close_time), "105", "10", "0.5", "52.5", "0",
    ])


class Sp500WeekendBtcSourcePreflightTests(unittest.TestCase):
    def test_parse_sp500_csv_sorts_and_preserves_positive_daily_closes(self):
        body = (
            b"observation_date,SP500\n"
            b"2017-08-21,2428.37\n"
            b"2017-08-18,2425.55\n"
            b"2017-08-22,.\n"
        )
        values = model.parse_sp500_csv(body)
        self.assertEqual(list(values), [dt.date(2017, 8, 18), dt.date(2017, 8, 21)])
        self.assertEqual(values[dt.date(2017, 8, 18)], 2425.55)

    def test_parse_sp500_rejects_duplicate_dates_and_nonpositive_values(self):
        duplicate = (
            b"observation_date,SP500\n"
            b"2017-08-18,2425.55\n"
            b"2017-08-18,2426.00\n"
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_sp500_csv(duplicate)
        nonpositive = b"observation_date,SP500\n2017-08-18,0\n"
        with self.assertRaisesRegex(ValueError, "positive and finite"):
            model.parse_sp500_csv(nonpositive)

    def test_sp500_coverage_rejects_stale_and_future_observations(self):
        values = model.parse_sp500_csv(sp500_csv())
        now = dt.datetime(2026, 11, 28, 12, tzinfo=UTC)
        summary = model.validate_sp500_coverage(values, now)
        self.assertGreaterEqual(summary["rows"], 2200)
        self.assertEqual(summary["first_date"], "2017-08-18")
        stale = {day: close for day, close in values.items() if day < dt.date(2026, 11, 20)}
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_sp500_coverage(stale, now)
        future = dict(values)
        future[dt.date(2026, 11, 30)] = 5000.0
        with self.assertRaisesRegex(ValueError, "future-dated"):
            model.validate_sp500_coverage(future, now)

    def test_btc_hourly_parser_records_off_grid_and_invalid_close_rows_without_rounding(self):
        step = 3_600_000
        start = 1_700_000_000_000
        aligned = start - (start % step)
        rows = [
            hourly_row(aligned, aligned + step - 1),
            hourly_row(aligned + step, aligned + 2 * step),
            hourly_row(aligned + 2 * step + 1234, aligned + 3 * step),
            hourly_row(aligned + 3 * step, aligned + 3 * step - 1000),
        ]
        parsed, unit, stats = model.parse_btc_hourly_archive(("\n".join(rows) + "\n").encode())
        self.assertEqual(unit, "milliseconds")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(stats["row_count"], 4)
        self.assertEqual(stats["valid_row_count"], 2)
        self.assertEqual(stats["invalid_row_count"], 2)
        self.assertEqual(
            [row["kind"] for row in stats["anomalies"]],
            ["off_grid_open_time", "invalid_close_time"],
        )
        self.assertEqual(stats["close_time_equal_to_open_plus_interval_rows"], 1)
        self.assertNotIn(
            dt.datetime.fromtimestamp((aligned + 2 * step) / 1000, UTC),
            parsed,
        )

    def test_archive_spec_builders_use_official_btcusdt_hourly_paths(self):
        monthly = model.build_monthly_archive_specs(
            dt.date(2017, 8, 18), dt.date(2026, 11, 22)
        )
        daily = model.build_daily_archive_specs(dt.date(2026, 11, 22))
        gap_daily = model.build_daily_archive_specs_for_dates([
            dt.date(2018, 2, 9), dt.date(2018, 2, 10)
        ])
        self.assertEqual(monthly[0]["filename"], "BTCUSDT-1h-2017-08.zip")
        self.assertEqual(monthly[-1]["filename"], "BTCUSDT-1h-2026-10.zip")
        self.assertEqual(daily[0]["filename"], "BTCUSDT-1h-2026-11-01.zip")
        self.assertEqual(daily[-1]["filename"], "BTCUSDT-1h-2026-11-22.zip")
        self.assertEqual(
            [row["filename"] for row in gap_daily],
            ["BTCUSDT-1h-2018-02-09.zip", "BTCUSDT-1h-2018-02-10.zip"],
        )
        self.assertTrue(all("/data/spot/" in row["url"] for row in monthly + daily + gap_daily))

    def test_daily_archive_reconciliation_fills_only_missing_hours_and_checks_overlaps(self):
        start = dt.datetime(2020, 1, 1, tzinfo=UTC)
        primary = {
            start: 100.0,
            start + dt.timedelta(hours=2): 102.0,
        }
        daily = {
            start: 100.0,
            start + dt.timedelta(hours=1): 101.0,
            start + dt.timedelta(hours=2): 102.0,
        }
        record = {
            "period": "2020-01-01",
            "url": "https://data.binance.vision/BTCUSDT-1h-2020-01-01.zip",
            "checksum_url": "https://data.binance.vision/BTCUSDT-1h-2020-01-01.zip.CHECKSUM",
            "archive_sha256": "a" * 64,
            "checksum_sha256": "b" * 64,
            "checksum_verified": True,
            "rows": 24,
            "timestamp_unit": "milliseconds",
            "invalid_row_count": 0,
        }
        merged, summary = model.reconcile_daily_archive_rows(
            primary, [(daily, record)], start, start + dt.timedelta(hours=3)
        )
        self.assertEqual(merged[start + dt.timedelta(hours=1)], 101.0)
        self.assertEqual(merged[start + dt.timedelta(hours=2)], 102.0)
        self.assertEqual(summary["recovered_hour_count"], 1)
        self.assertEqual(summary["matching_overlap_count"], 2)
        self.assertEqual(summary["conflict_count"], 0)

    def test_daily_archive_conflict_removes_the_hour_and_fails_closed(self):
        start = dt.datetime(2020, 1, 1, tzinfo=UTC)
        primary = {start: 100.0}
        daily = {start: 100.01}
        record = {
            "period": "2020-01-01",
            "url": "https://data.binance.vision/BTCUSDT-1h-2020-01-01.zip",
            "checksum_url": "https://data.binance.vision/BTCUSDT-1h-2020-01-01.zip.CHECKSUM",
            "archive_sha256": "a" * 64,
            "checksum_sha256": "b" * 64,
            "checksum_verified": True,
            "rows": 24,
            "timestamp_unit": "milliseconds",
            "invalid_row_count": 0,
        }
        merged, summary = model.reconcile_daily_archive_rows(
            primary, [(daily, record)], start, start + dt.timedelta(hours=1)
        )
        self.assertNotIn(start, merged)
        self.assertEqual(summary["conflict_count"], 1)
        self.assertEqual(summary["conflicts"][0]["timestamp"], start.isoformat())

    def test_anomaly_hours_are_scoped_to_required_window_and_deduplicated(self):
        start = dt.datetime(2026, 1, 1, tzinfo=UTC)
        end = start + dt.timedelta(hours=10)
        same_hour = start + dt.timedelta(hours=3)
        archive_results = [
            ({}, {
                "anomalies": [
                    {"timestamp": (same_hour + dt.timedelta(milliseconds=1234)).isoformat()},
                    {"timestamp": (same_hour + dt.timedelta(milliseconds=5678)).isoformat()},
                    {"timestamp": (start - dt.timedelta(hours=1)).isoformat()},
                    {"timestamp": end.isoformat()},
                ]
            })
        ]
        self.assertEqual(
            model.anomaly_hour_timestamps(archive_results, start, end),
            {same_hour},
        )

    def test_hourly_coverage_unions_anomaly_hours_with_actual_gaps(self):
        start = dt.datetime(2020, 1, 1, tzinfo=UTC)
        hours = 100_000
        end = start + dt.timedelta(hours=hours)
        rows = {
            start + dt.timedelta(hours=index): 50_000.0 + index
            for index in range(hours)
        }
        first = start + dt.timedelta(hours=1000)
        second = start + dt.timedelta(hours=1001)
        rows.pop(first)
        summary = model.validate_hourly_coverage(
            rows, start, end,
            anomaly_hours={first, second},
            enforce_limits=False,
        )
        self.assertEqual(summary["observed_missing_hours"], 1)
        self.assertEqual(summary["anomaly_affected_hours"], 2)
        self.assertEqual(summary["effective_missing_hours"], 2)
        self.assertEqual(summary["missing_hours"], 2)
        self.assertTrue(summary["within_limits"])

    def test_hourly_coverage_rejects_more_than_24_distinct_anomaly_hours(self):
        start = dt.datetime(2020, 1, 1, tzinfo=UTC)
        hours = 100_000
        end = start + dt.timedelta(hours=hours)
        rows = {
            start + dt.timedelta(hours=index): 50_000.0 + index
            for index in range(hours)
        }
        anomalies = {
            start + dt.timedelta(hours=1000 + 5 * index)
            for index in range(25)
        }
        diagnostic = model.validate_hourly_coverage(
            rows, start, end, anomaly_hours=anomalies, enforce_limits=False
        )
        self.assertFalse(diagnostic["within_limits"])
        self.assertIn("missing_hour_count", diagnostic["limit_failures"])
        with self.assertRaisesRegex(ValueError, "gaps exceed frozen limits"):
            model.validate_hourly_coverage(rows, start, end, anomaly_hours=anomalies)

    def test_hourly_coverage_rejects_missing_or_out_of_window_hours(self):
        start = dt.datetime(2026, 1, 1, tzinfo=UTC)
        end = start + dt.timedelta(hours=2000)
        rows = {
            start + dt.timedelta(hours=index): 50_000.0 + index
            for index in range(2000)
        }
        summary = model.validate_hourly_coverage(rows, start, end)
        self.assertEqual(summary["missing_hours"], 0)
        missing = dict(rows)
        missing.pop(start + dt.timedelta(hours=1000))
        missing.pop(start + dt.timedelta(hours=1001))
        with self.assertRaisesRegex(ValueError, "gaps exceed"):
            model.validate_hourly_coverage(missing, start, end)
        outside = dict(rows)
        outside[start - dt.timedelta(hours=1)] = 1.0
        with self.assertRaisesRegex(ValueError, "out-of-window"):
            model.validate_hourly_coverage(outside, start, end)

    def test_weekly_event_feasibility_requires_matured_nonoverlapping_targets(self):
        first_friday = dt.date(2017, 8, 18)
        fridays = [first_friday + dt.timedelta(days=7 * index) for index in range(260)]
        sp500 = {day: 2400.0 + index for index, day in enumerate(fridays)}
        start = dt.datetime(2017, 8, 11, tzinfo=UTC)
        end = dt.datetime(2022, 9, 1, tzinfo=UTC)
        returns = {}
        cursor = start
        while cursor < end:
            returns[int(cursor.timestamp())] = 0.0001
            cursor += dt.timedelta(hours=1)
        summary = model.event_feasibility(
            sp500,
            returns,
            latest_friday=fridays[-1],
            validation_start=fridays[120],
            test_start=fridays[180],
            minimum_training_events=104,
        )
        self.assertGreater(summary["accepted_weekly_events"], 250)
        self.assertGreater(summary["eligible_validation_forecasts"], 0)
        self.assertGreater(summary["eligible_test_forecasts"], 0)
        self.assertTrue(summary["forecast_windows_are_exactly_24h"])
        self.assertTrue(summary["target_windows_non_overlapping_by_weekly_schedule"])

    def test_weekly_event_feasibility_excludes_incomplete_hourly_windows(self):
        friday = dt.date(2020, 1, 3)
        signal = dt.datetime(2020, 1, 4, 12, tzinfo=UTC)
        signal_ts = int(signal.timestamp())
        returns = {
            signal_ts - 168 * 3600 + index * 3600: 0.001
            for index in range(168 + 24)
        }
        returns.pop(signal_ts + 5 * 3600)
        summary = model.event_feasibility(
            {friday: 3000.0},
            returns,
            latest_friday=friday,
            validation_start=dt.date(2019, 1, 1),
            test_start=dt.date(2022, 1, 1),
            minimum_training_events=1,
        )
        self.assertEqual(summary["accepted_weekly_events"], 0)

    def test_latest_matured_friday_excludes_unfinished_weekend_target(self):
        values = {
            dt.date(2026, 11, 20): 6800.0,
            dt.date(2026, 11, 27): 6900.0,
        }
        now = dt.datetime(2026, 11, 28, 7, 46, tzinfo=UTC)
        day, signal_ts, target_end_ts = model.latest_matured_friday(values, now)
        self.assertEqual(day, dt.date(2026, 11, 20))
        self.assertEqual(
            dt.datetime.fromtimestamp(signal_ts, UTC),
            dt.datetime(2026, 11, 21, 12, tzinfo=UTC),
        )
        self.assertEqual(
            dt.datetime.fromtimestamp(target_end_ts, UTC),
            dt.datetime(2026, 11, 22, 12, tzinfo=UTC),
        )

    def test_preflight_is_explicitly_source_only_and_does_not_fit_a_model(self):
        values = model.parse_sp500_csv(sp500_csv())
        coverage = model.validate_sp500_coverage(
            values, dt.datetime(2026, 11, 28, 12, tzinfo=UTC)
        )
        self.assertEqual(coverage["series_id"], "SP500")
        self.assertFalse(coverage["historical_intraday_publication_timestamps_available"])


    def test_closed_hypothesis_execution_guard_blocks_source_retrieval(self):
        with self.assertRaisesRegex(RuntimeError, "closed INCONCLUSIVE/INFEASIBLE"):
            model.assert_empirical_execution_allowed()
        with self.assertRaisesRegex(RuntimeError, "closed INCONCLUSIVE/INFEASIBLE"):
            model.run_preflight()


if __name__ == "__main__":
    unittest.main()
