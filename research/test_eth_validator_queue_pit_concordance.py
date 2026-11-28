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
        self.assertEqual(parsed["first_date"], dt.date(2023, 5, 21))
        self.assertEqual(parsed["last_date"], dt.date(2023, 5, 23))

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
        broken = {"date": day.isoformat(), "entry_wait": 1.0}
        with self.assertRaisesRegex(audit.source.PreflightError, "Missing/invalid"):
            audit.parse_history(json.dumps([broken]).encode())

    def test_average_ranks_assigns_midranks_to_ties(self):
        self.assertEqual(audit.average_ranks([3.0, 1.0, 1.0, 4.0]), [3.0, 1.5, 1.5, 4.0])

    def test_comparison_summary_reports_error_and_rank_metrics(self):
        result = audit.comparison_summary([1.0, 2.0, 3.0], [1.1, 2.1, 3.1])
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["pearson_r"], 1.0)
        self.assertAlmostEqual(result["spearman_r"], 1.0)
        self.assertAlmostEqual(result["mae"], 0.1)
        self.assertAlmostEqual(result["mean_bias_observed_minus_reference"], 0.1)

    def test_cross_source_concordance_excludes_documented_pectra_bug_interval(self):
        dates = [
            dt.date(2025, 5, 6),
            dt.date(2025, 5, 7),
            dt.date(2025, 5, 21),
            dt.date(2025, 5, 22),
        ]
        history = {"rows": [{"date": day, "entry_wait": 5.0 + index, "exit_wait": 2.0 + index} for index, day in enumerate(dates)]}
        queue = {
            "entry_values": {day: 5.0 + index for index, day in enumerate(dates)},
            "exit_values": {day: 2.0 + index for index, day in enumerate(dates)},
        }
        result = audit.cross_source_concordance(history, queue)
        self.assertEqual(result["common_dates_before_known_bug_exclusion"], 4)
        self.assertEqual(result["known_pectra_bug_dates_excluded"], 2)
        self.assertEqual(result["clean_common_dates"], 2)
        self.assertEqual(result["regimes"]["pre_pectra"]["n"], 1)
        self.assertEqual(result["regimes"]["post_pectra"]["n"], 1)

    def test_commit_vintage_mapping_requires_one_commit_per_append_only_row(self):
        day1 = dt.date(2023, 5, 21)
        day2 = dt.date(2023, 5, 22)
        history = {"rows": [{"date": day1}, {"date": day2}]}
        commits = {
            "commits": [
                {"sha": "a", "timestamp": dt.datetime(2023, 5, 21, 3, 0, tzinfo=dt.timezone.utc),
                 "message": "Update index.html with latest validator queue data"},
                {"sha": "b", "timestamp": dt.datetime(2023, 5, 22, 3, 0, tzinfo=dt.timezone.utc),
                 "message": "Update index.html with latest validator queue data"},
            ],
            "sha256": "a" * 64,
            "rate_limit_remaining_min": 50,
        }
        result = audit.build_commit_vintages(history, commits)
        self.assertTrue(result["mapping_complete"])
        self.assertEqual(result["same_utc_date_commit_count"], 2)
        self.assertEqual(result["commit_times"][day1], commits["commits"][0]["timestamp"])

    def test_commit_vintage_mapping_fails_closed_on_count_mismatch(self):
        history = {"rows": [{"date": dt.date(2023, 5, 21)}]}
        result = audit.build_commit_vintages(
            history, {"commits": [], "sha256": "a" * 64, "rate_limit_remaining_min": None}
        )
        self.assertFalse(result["mapping_complete"])
        self.assertIn("Commit count does not equal", result["error"])

    def test_two_day_lag_checks_commit_upper_bound_at_origin_midnight(self):
        _, schedule = audit.make_origin_dates(6)
        origin = next(day for day in schedule if day - dt.timedelta(days=2) >= dt.date(2023, 5, 21))
        feature_day = origin - dt.timedelta(days=2)
        history = {"rows": [{"date": feature_day, "entry_wait": 1.0, "exit_wait": 1.0}]}
        commit_times = {
            feature_day: dt.datetime.combine(origin, dt.time.min, tzinfo=dt.timezone.utc) - dt.timedelta(seconds=1)
        }
        result = audit.schedule_feasibility(history, commit_times, step_days=6, min_train_events=0)
        self.assertEqual(result["not_published_by_origin"], 0)
        commit_times[feature_day] += dt.timedelta(seconds=2)
        result = audit.schedule_feasibility(history, commit_times, step_days=6, min_train_events=0)
        self.assertEqual(result["not_published_by_origin"], 1)

    def test_nonoverlapping_schedule_grid_marks_short_steps_as_overlapping(self):
        history = {
            "rows": [row(dt.date(2023, 5, 21) + dt.timedelta(days=index)) for index in range(1300)]
        }
        step5 = audit.schedule_feasibility(history, None, step_days=5, min_train_events=60)
        step4 = audit.schedule_feasibility(history, None, step_days=4, min_train_events=60)
        self.assertTrue(step5["target_windows_non_overlapping"])
        self.assertFalse(step4["target_windows_non_overlapping"])

    def test_schedule_grid_includes_frozen_design_and_does_not_fit_a_model(self):
        history = {
            "rows": [row(dt.date(2023, 5, 21) + dt.timedelta(days=index)) for index in range(1300)]
        }
        grid = audit.schedule_grid(history, None)
        self.assertEqual(grid[0]["origin_step_days"], 6)
        self.assertEqual(grid[0]["minimum_training_events"], 60)
        self.assertTrue(all("valid_validation_origins" in item for item in grid))


if __name__ == "__main__":
    unittest.main()
