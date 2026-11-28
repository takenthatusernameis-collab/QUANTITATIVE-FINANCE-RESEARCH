from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import unittest

import h8_ci_credit_impulse_btc_downside as model


class H8CICreditImpulseBTCDownsideTests(unittest.TestCase):
    def wednesday_values(self):
        dates = [
            dt.date(2026, 10, 14),
            dt.date(2026, 10, 21),
            dt.date(2026, 10, 28),
            dt.date(2026, 11, 4),
            dt.date(2026, 11, 11),
        ]
        return {day: 1000.0 + index * 10.0 for index, day in enumerate(dates)}

    def test_feature_uses_latest_and_fourth_prior_from_same_sunday_vintage(self):
        values = self.wednesday_values()
        feature, reason, meta = model.feature_from_vintage("2026-11-22", values)
        self.assertIsNone(reason)
        self.assertAlmostEqual(feature, 100.0 * math.log(1040.0 / 1000.0))
        self.assertEqual(meta["latest_observation_date"], "2026-11-11")
        self.assertEqual(meta["fourth_prior_observation_date"], "2026-10-14")
        self.assertEqual(meta["latest_observation_age_days"], 11)

    def test_feature_rejects_future_observation_in_vintage(self):
        values = self.wednesday_values()
        values[dt.date(2026, 11, 25)] = 1050.0
        feature, reason, _ = model.feature_from_vintage("2026-11-22", values)
        self.assertIsNone(feature)
        self.assertEqual(reason, "future_observation")

    def test_feature_rejects_stale_vintage_instead_of_forward_filling(self):
        values = {
            dt.date(2026, 10, 7): 1000.0,
            dt.date(2026, 10, 14): 1010.0,
            dt.date(2026, 10, 21): 1020.0,
            dt.date(2026, 10, 28): 1030.0,
            dt.date(2026, 11, 4): 1040.0,
        }
        feature, reason, meta = model.feature_from_vintage("2026-11-22", values)
        self.assertIsNone(feature)
        self.assertEqual(reason, "stale_or_early_latest_observation")
        self.assertEqual(meta["latest_observation_age_days"], 18)

    def test_feature_rejects_irregular_weekly_history(self):
        values = {
            dt.date(2026, 10, 7): 1000.0,
            dt.date(2026, 10, 14): 1010.0,
            dt.date(2026, 10, 29): 1020.0,
            dt.date(2026, 11, 4): 1030.0,
            dt.date(2026, 11, 11): 1040.0,
        }
        feature, reason, _ = model.feature_from_vintage("2026-11-22", values)
        self.assertIsNone(feature)
        self.assertEqual(reason, "irregular_weekly_history")

    def test_feature_rejects_non_wednesday_latest_observation(self):
        values = self.wednesday_values()
        values[dt.date(2026, 11, 12)] = values.pop(dt.date(2026, 11, 11))
        feature, reason, _ = model.feature_from_vintage("2026-11-22", values)
        self.assertIsNone(feature)
        self.assertEqual(reason, "latest_observation_not_wednesday")

    def test_vintage_batches_are_bounded_and_sunday_only(self):
        vintages = model.sunday_dates(dt.date(2026, 1, 4), dt.date(2026, 6, 28))
        batches = model.chunk_vintages(vintages, 12)
        self.assertEqual([len(batch) for batch in batches], [12, 12, 2])
        with self.assertRaises(ValueError):
            model.chunk_vintages(vintages[:2] + vintages[:1], 12)
        with self.assertRaises(ValueError):
            model.chunk_vintages(["2026-01-05"], 12)
        with self.assertRaises(ValueError):
            model.chunk_vintages(vintages, 13)

    def test_build_events_uses_sunday_close_and_monday_friday_target(self):
        start = dt.date(2017, 8, 17)
        end = dt.date(2017, 10, 20)
        prices = {}
        cursor = start
        index = 0
        while cursor <= end:
            prices[cursor] = 10000.0 * math.exp(0.001 * index + 0.0002 * math.sin(index))
            cursor += dt.timedelta(days=1)
            index += 1

        panel = {}
        for signal in (
            dt.date(2017, 9, 10),
            dt.date(2017, 9, 17),
            dt.date(2017, 9, 24),
            dt.date(2017, 10, 1),
            dt.date(2017, 10, 8),
        ):
            latest = signal - dt.timedelta(days=4)
            values = {}
            for offset in range(4, -1, -1):
                day = latest - dt.timedelta(days=7 * offset)
                values[day] = 2000.0 + 5.0 * (4 - offset)
            panel[signal.isoformat()] = values

        events, metadata = model.build_events(panel, prices)
        self.assertEqual(metadata["accepted_events"], 5)
        self.assertEqual(events[0]["signal_date"], dt.date(2017, 9, 10))
        self.assertEqual(events[0]["target_start_date"], dt.date(2017, 9, 11))
        self.assertEqual(events[0]["target_end_date"], dt.date(2017, 9, 15))
        self.assertTrue(all(event["signal_date"].weekday() == 6 for event in events))
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_training_sample_excludes_unmatured_target_and_current_event(self):
        events = []
        start = dt.date(2020, 1, 5)
        for index in range(106):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "signal_date": signal,
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": float(index),
            })
        current_signal = start + dt.timedelta(days=7 * 105)
        train = model.training_sample(events, current_signal)
        self.assertEqual(len(train), 104)
        self.assertEqual(train[-1]["signal_date"], current_signal - dt.timedelta(days=7))
        self.assertTrue(all(row["target_end_date"] < current_signal for row in train))

    def test_archive_manifest_requires_exact_ordered_hashes_and_coverage(self):
        expected = [
            {
                "kind": "monthly", "period": "2026-09", "url": "https://x/2026-09.zip",
                "checksum_url": "https://x/2026-09.zip.CHECKSUM", "archive_sha256": "a" * 64,
                "checksum_sha256": "b" * 64, "checksum_verified": True, "rows": 30,
                "timestamp_unit": "microseconds", "first_date": "2026-09-01", "last_date": "2026-09-30",
            },
            {
                "kind": "daily", "period": "2026-10-01", "url": "https://x/2026-10-01.zip",
                "checksum_url": "https://x/2026-10-01.zip.CHECKSUM", "archive_sha256": "c" * 64,
                "checksum_sha256": "d" * 64, "checksum_verified": True, "rows": 1,
                "timestamp_unit": "microseconds", "first_date": "2026-10-01", "last_date": "2026-10-01",
            },
        ]
        digest = hashlib.sha256(
            json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(model.verify_archive_manifest(expected, expected, digest), digest)
        changed = [dict(row) for row in expected]
        changed[1]["archive_sha256"] = "e" * 64
        with self.assertRaises(model.FrozenSourceMismatch):
            model.verify_archive_manifest(changed, expected, digest)
        with self.assertRaises(model.FrozenSourceMismatch):
            model.verify_archive_manifest(expected[:1], expected, digest)

    def test_metrics_and_frozen_decision_thresholds(self):
        validation = {"n": 120, "baseline_rmse": 1.0, "augmented_rmse": 0.988, "rmse_improvement_pct": 1.2}
        test = {"n": 140, "baseline_rmse": 1.0, "augmented_rmse": 0.985, "rmse_improvement_pct": 1.5}
        paired = {"ci_95_low": 0.001, "ci_95_high": 0.02}
        self.assertEqual(model.decide(validation, test, paired)[0], "PROMISING")
        validation["rmse_improvement_pct"] = 0.9
        self.assertEqual(model.decide(validation, test, paired)[0], "INCONCLUSIVE")
        validation["rmse_improvement_pct"] = -0.2
        test["rmse_improvement_pct"] = -0.1
        paired = {"ci_95_low": -0.03, "ci_95_high": -0.001}
        self.assertEqual(model.decide(validation, test, paired)[0], "REJECTED")

    def test_bootstrap_is_deterministic_and_uses_frozen_settings(self):
        rows = []
        for index in range(40):
            target = 0.1 + 0.01 * index
            rows.append({
                "target_log1p_semivariance": target,
                "baseline_prediction": target + 0.02,
                "augmented_prediction": target + (0.01 if index % 2 else 0.03),
                "baseline_squared_error": 0.02 ** 2,
                "augmented_squared_error": (0.01 if index % 2 else 0.03) ** 2,
            })
        first = model.paired_loss_bootstrap(rows)
        second = model.paired_loss_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["replications"], 2000)
        self.assertEqual(first["block_size_events"], 4)
        self.assertEqual(first["seed"], 20261128)

    def test_source_constants_pin_accepted_runs_and_timebox(self):
        self.assertEqual(model.PREFLIGHT_RUN_ID, 46115128898)
        self.assertEqual(model.PREFLIGHT_SOURCE_SHA, "3d76c559ae41c92b1befa0bfccc296a5469eb514")
        self.assertEqual(model.BTC_SOURCE_PREFLIGHT_RUN_ID, 45925248340)
        self.assertEqual(model.MODEL_WINDOW, 104)
        self.assertEqual(model.MIN_FORECASTS, 100)
        self.assertEqual(model.BOOTSTRAP_REPS, 2000)
        self.assertEqual(model.BOOTSTRAP_BLOCK, 4)
        self.assertEqual(model.BOOTSTRAP_SEED, 20261128)


if __name__ == "__main__":
    unittest.main()
