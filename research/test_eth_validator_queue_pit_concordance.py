import datetime as dt
import json
import unittest

import eth_validator_queue_pit_concordance as audit


def row(day, entry=5.0, exit_=2.0):
    return {"date": day.isoformat(), "entry_wait": entry, "exit_wait": exit_}


class EthereumValidatorQueuePitConcordanceTests(unittest.TestCase):
    def test_history_parser_checks_order_gaps_and_numeric_values(self):
        payload = [row(dt.date(2023, 5, 21)), row(dt.date(2023, 5, 23))]
        parsed = audit.parse_history(json.dumps(payload).encode())
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["missing_days"], 1)
        self.assertEqual(parsed["gap_count"], 1)

    def test_history_parser_rejects_duplicate_or_nonchronological_dates(self):
        day = dt.date(2023, 5, 21)
        with self.assertRaisesRegex(audit.AuditError, "strictly increasing"):
            audit.parse_history(json.dumps([row(day), row(day)]).encode())
        with self.assertRaisesRegex(audit.AuditError, "strictly increasing"):
            audit.parse_history(json.dumps([row(day + dt.timedelta(days=1)), row(day)]).encode())

    def test_history_parser_rejects_negative_or_missing_wait_values(self):
        day = dt.date(2023, 5, 21)
        with self.assertRaisesRegex(audit.source.PreflightError, "Out-of-range"):
            audit.parse_history(json.dumps([row(day, entry=-1)]).encode())
        with self.assertRaisesRegex(audit.source.PreflightError, "Missing/invalid"):
            audit.parse_history(json.dumps([{"date": day.isoformat(), "entry_wait": 1.0}]).encode())

    def test_average_ranks_assigns_midranks_to_ties(self):
        self.assertEqual(audit.average_ranks([3.0, 1.0, 1.0, 4.0]), [3.0, 1.5, 1.5, 4.0])

    def test_comparison_summary_reports_error_and_rank_metrics(self):
        result = audit.comparison_summary([1.0, 2.0, 3.0], [1.1, 2.1, 3.1])
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["pearson_r"], 1.0)
        self.assertAlmostEqual(result["spearman_r"], 1.0)
        self.assertAlmostEqual(result["mae"], 0.1)

    def test_cross_source_concordance_excludes_documented_pectra_bug_interval(self):
        dates = [dt.date(2025, 5, 6), dt.date(2025, 5, 7), dt.date(2025, 5, 21), dt.date(2025, 5, 22)]
        history = {"rows": [{"date": day, "entry_wait": 5.0 + i, "exit_wait": 2.0 + i} for i, day in enumerate(dates)]}
        queue = {
            "entry_values": {day: 5.0 + i for i, day in enumerate(dates)},
            "exit_values": {day: 2.0 + i for i, day in enumerate(dates)},
        }
        result = audit.cross_source_concordance(history, queue)
        self.assertEqual(result["common_dates_before_known_bug_exclusion"], 4)
        self.assertEqual(result["known_pectra_bug_dates_excluded"], 2)
        self.assertEqual(result["clean_common_dates"], 2)
        self.assertEqual(result["regimes"]["pre_pectra"]["n"], 1)
        self.assertEqual(result["regimes"]["post_pectra"]["n"], 1)

    def test_git_history_reconstruction_preserves_first_seen_and_revised_values(self):
        early = dt.date(2023, 5, 21)
        later = dt.date(2023, 5, 22)
        t1 = dt.datetime(2023, 5, 30, 16, 27, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2023, 6, 3, 23, 42, tzinfo=dt.timezone.utc)
        snapshots = [
            {"sha": "b", "timestamp": t2, "rows": {
                early: {"entry_wait": 31.58, "exit_wait": 0.0, "entry_queue": 2002464, "exit_queue": 0},
                later: {"entry_wait": 32.79, "exit_wait": 0.0, "entry_queue": 2087200, "exit_queue": 0},
            }},
            {"sha": "a", "timestamp": t1, "rows": {
                early: {"entry_wait": 34.76, "exit_wait": 0.0, "entry_queue": 62577, "exit_queue": 0},
                later: {"entry_wait": 36.24, "exit_wait": 0.0, "entry_queue": 65225, "exit_queue": 0},
            }},
        ]
        current = {"rows": [
            {"date": early, "entry_wait": 31.58, "exit_wait": 0.0},
            {"date": later, "entry_wait": 32.79, "exit_wait": 0.0},
        ]}
        git_history = {"snapshots": snapshots, "commit_count": 2, "sha256": "a" * 64, "head_sha": "b" * 40}
        result = audit.build_vintage_history(git_history, current)
        self.assertTrue(result["mapping_complete"])
        self.assertEqual(result["wait_revision_events"], 2)
        self.assertEqual(result["queue_balance_revision_events"], 2)
        before = audit.value_as_of(result["version_history"], early, dt.date(2023, 6, 2))
        after = audit.value_as_of(result["version_history"], early, dt.date(2023, 6, 4))
        self.assertEqual(before["entry_wait"], 34.76)
        self.assertEqual(after["entry_wait"], 31.58)

    def test_value_as_of_uses_latest_revision_committed_before_origin(self):
        day = dt.date(2025, 5, 22)
        versions = {day: [
            {"timestamp": dt.datetime(2025, 5, 22, 2, 0, tzinfo=dt.timezone.utc), "entry_wait": 0.04, "exit_wait": 0.06},
            {"timestamp": dt.datetime(2025, 5, 23, 17, 25, tzinfo=dt.timezone.utc), "entry_wait": 1.83, "exit_wait": 1.54},
        ]}
        self.assertEqual(audit.value_as_of(versions, day, dt.date(2025, 5, 23))["entry_wait"], 0.04)
        self.assertEqual(audit.value_as_of(versions, day, dt.date(2025, 5, 24))["entry_wait"], 1.83)

    def test_value_as_of_selects_latest_eligible_timestamp_when_versions_are_unsorted(self):
        day = dt.date(2025, 5, 22)
        versions = {day: [
            {"timestamp": dt.datetime(2025, 5, 23, 17, 25, tzinfo=dt.timezone.utc), "entry_wait": 2.10, "exit_wait": 1.90},
            {"timestamp": dt.datetime(2025, 5, 22, 17, 25, tzinfo=dt.timezone.utc), "entry_wait": 1.83, "exit_wait": 1.54},
            {"timestamp": dt.datetime(2025, 5, 22, 2, 0, tzinfo=dt.timezone.utc), "entry_wait": 0.04, "exit_wait": 0.06},
        ]}
        self.assertEqual(audit.value_as_of(versions, day, dt.date(2025, 5, 23))["entry_wait"], 1.83)
        self.assertEqual(audit.value_as_of(versions, day, dt.date(2025, 5, 24))["entry_wait"], 2.10)

    def test_validatorqueue_raw_history_is_pinned_to_the_git_snapshot(self):
        self.assertEqual(len(audit.VALIDATORQUEUE_SOURCE_SHA), 40)
        self.assertIn(audit.VALIDATORQUEUE_SOURCE_SHA, audit.VALIDATORQUEUE_RAW_URL)

    def test_two_day_lag_excludes_rows_not_published_by_origin_midnight(self):
        _, schedule = audit.make_origin_dates(6)
        origin = next(day for day in schedule if day - dt.timedelta(days=2) >= dt.date(2023, 5, 21))
        feature_day = origin - dt.timedelta(days=2)
        history = {"rows": [{"date": feature_day, "entry_wait": 1.0, "exit_wait": 1.0}]}
        versions = {feature_day: [{
            "timestamp": dt.datetime.combine(origin, dt.time.min, tzinfo=dt.timezone.utc) - dt.timedelta(seconds=1),
            "entry_wait": 1.0, "exit_wait": 1.0,
        }]}
        result = audit.schedule_feasibility(history, versions, step_days=6, min_train_events=0)
        self.assertEqual(result["not_committed_by_origin"], 0)
        self.assertFalse(result["public_availability_verified"])
        self.assertIsNone(result["pit_accepted_validation_origins"])
        versions[feature_day][0]["timestamp"] += dt.timedelta(seconds=2)
        result = audit.schedule_feasibility(history, versions, step_days=6, min_train_events=0)
        self.assertEqual(result["not_committed_by_origin"], 1)

    def test_nonoverlapping_schedule_grid_marks_short_steps_as_overlapping(self):
        start = dt.date(2023, 5, 21)
        history = {"rows": [{"date": start + dt.timedelta(days=i), "entry_wait": 5.0, "exit_wait": 2.0} for i in range(1300)]}
        versions = {start + dt.timedelta(days=i): [{
            "timestamp": dt.datetime.combine(start + dt.timedelta(days=i), dt.time.min, tzinfo=dt.timezone.utc),
            "entry_wait": 5.0, "exit_wait": 2.0,
        }] for i in range(1300)}
        self.assertTrue(audit.schedule_feasibility(history, versions, step_days=5, min_train_events=60)["target_windows_non_overlapping"])
        self.assertFalse(audit.schedule_feasibility(history, versions, step_days=4, min_train_events=60)["target_windows_non_overlapping"])

    def test_schedule_grid_includes_frozen_design_and_does_not_fit_a_model(self):
        start = dt.date(2023, 5, 21)
        history = {"rows": [{"date": start + dt.timedelta(days=i), "entry_wait": 5.0, "exit_wait": 2.0} for i in range(1300)]}
        versions = {start + dt.timedelta(days=i): [{
            "timestamp": dt.datetime.combine(start + dt.timedelta(days=i), dt.time.min, tzinfo=dt.timezone.utc),
            "entry_wait": 5.0, "exit_wait": 2.0,
        }] for i in range(1300)}
        grid = audit.schedule_grid(history, versions)
        self.assertEqual(grid[0]["origin_step_days"], 6)
        self.assertEqual(grid[0]["minimum_training_events"], 60)
        self.assertTrue(all("commit_timestamp_proxy_validation_origins" in item for item in grid))


if __name__ == "__main__":
    unittest.main()
