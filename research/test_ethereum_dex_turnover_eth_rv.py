import datetime as dt
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ethereum_dex_turnover_eth_rv as model


def hourly_closes(start: dt.datetime, hours: int, missing: set[int] | None = None) -> dict:
    missing = missing or set()
    return {
        start + dt.timedelta(hours=index): 2000.0 * math.exp(0.0001 * index)
        for index in range(hours)
        if index not in missing
    }


def daily_values(start: dt.date, days: int, base_value: float, increment: float) -> dict:
    return {
        start + dt.timedelta(days=index): base_value + increment * index
        for index in range(days)
    }


class EthereumDexTurnoverEthRvTests(unittest.TestCase):
    def test_hourly_returns_require_adjacent_candles_and_never_bridge_gaps(self):
        start = dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc)
        closes = {
            start: 100.0,
            start + dt.timedelta(hours=1): 101.0,
            start + dt.timedelta(hours=3): 103.0,
            start + dt.timedelta(hours=4): 104.0,
        }
        returns = model.hourly_returns(closes)
        expected = {
            int((start + dt.timedelta(hours=1)).timestamp()),
            int((start + dt.timedelta(hours=4)).timestamp()),
        }
        self.assertEqual(set(returns), expected)
        self.assertNotIn(int((start + dt.timedelta(hours=2)).timestamp()), returns)
        self.assertNotIn(int((start + dt.timedelta(hours=3)).timestamp()), returns)

    def test_window_returns_rejects_any_missing_hour_without_interpolation(self):
        start = int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp())
        returns = {start: 0.001, start + 2 * 3600: -0.002}
        self.assertIsNone(model.window_returns(returns, start, 3))
        self.assertEqual(model.window_returns(returns, start, 1), [0.001])

    def test_build_events_uses_exact_t_minus_8_through_t_minus_2_turnover_window(self):
        start_day = dt.date(2021, 1, 1)
        start_dt = dt.datetime.combine(start_day, dt.time.min, tzinfo=dt.timezone.utc)
        closes = hourly_closes(start_dt, 24 * 20)
        dex = daily_values(start_day, 20, 1000.0, 10.0)
        tvl = daily_values(start_day, 20, 1_000_000.0, 10_000.0)
        with patch.object(model.preflight, "SAMPLE_START", start_day), patch.object(
            model.preflight, "SAMPLE_END", start_day + dt.timedelta(days=19)
        ):
            events, skipped = model.build_events(dex, tvl, closes)
        first = next(row for row in events if row["date"] == start_day + dt.timedelta(days=8))
        expected_dates = [start_day + dt.timedelta(days=i) for i in range(7)]
        expected_volume = sum(dex[day] for day in expected_dates)
        expected_mean_tvl = sum(tvl[day] for day in expected_dates) / 7.0
        self.assertEqual(first["feature_start_date"], "2021-01-01")
        self.assertEqual(first["feature_end_date"], "2021-01-07")
        self.assertAlmostEqual(first["dex_volume_7d_usd"], expected_volume)
        self.assertAlmostEqual(first["mean_tvl_7d_usd"], expected_mean_tvl)
        self.assertAlmostEqual(first["dex_turnover_7d"], expected_volume / expected_mean_tvl)
        self.assertAlmostEqual(first["dex_turnover_7d_log"], math.log1p(expected_volume / expected_mean_tvl))
        self.assertEqual(skipped, {})

    def test_build_events_excludes_every_window_affected_by_missing_hourly_returns(self):
        start_day = dt.date(2021, 1, 1)
        start_dt = dt.datetime.combine(start_day, dt.time.min, tzinfo=dt.timezone.utc)
        missing_index = 11 * 24 + 13
        closes = hourly_closes(start_dt, 24 * 25, {missing_index})
        dex = daily_values(start_day, 25, 1_000_000.0, 1000.0)
        tvl = daily_values(start_day, 25, 1_000_000_000.0, 100_000.0)
        with patch.object(model.preflight, "SAMPLE_START", start_day), patch.object(
            model.preflight, "SAMPLE_END", start_day + dt.timedelta(days=24)
        ):
            events, skipped = model.build_events(dex, tvl, closes)
        accepted_dates = {row["date"] for row in events}
        self.assertNotIn(start_day + dt.timedelta(days=11), accepted_dates)
        self.assertGreaterEqual(skipped.get("incomplete_target_returns", 0), 1)
        self.assertGreaterEqual(skipped.get("incomplete_pre_rv24_returns", 0), 1)
        self.assertGreaterEqual(skipped.get("incomplete_pre_rv168_returns", 0), 1)

    def test_build_events_excludes_incomplete_daily_dex_feature_windows(self):
        start_day = dt.date(2021, 1, 1)
        start_dt = dt.datetime.combine(start_day, dt.time.min, tzinfo=dt.timezone.utc)
        closes = hourly_closes(start_dt, 24 * 20)
        dex = daily_values(start_day, 20, 1_000_000.0, 1000.0)
        tvl = daily_values(start_day, 20, 1_000_000_000.0, 100_000.0)
        dex.pop(start_day + dt.timedelta(days=4))
        with patch.object(model.preflight, "SAMPLE_START", start_day), patch.object(
            model.preflight, "SAMPLE_END", start_day + dt.timedelta(days=19)
        ):
            events, skipped = model.build_events(dex, tvl, closes)
        accepted_dates = {row["date"] for row in events}
        self.assertNotIn(start_day + dt.timedelta(days=8), accepted_dates)
        self.assertGreater(skipped.get("missing_dex_feature_date", 0), 0)

    def test_training_sample_uses_strictly_matured_events_and_caps_at_252(self):
        start = dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc)
        events = []
        for index in range(300):
            signal = int((start + dt.timedelta(days=index)).timestamp())
            events.append({
                "date": start.date() + dt.timedelta(days=index),
                "signal_ts": signal,
                "target_end_ts": signal + 24 * 3600,
            })
        current_signal = int((start + dt.timedelta(days=300)).timestamp())
        train = model.training_sample(events, current_signal)
        self.assertEqual(len(train), 252)
        self.assertEqual(train[-1]["date"], start.date() + dt.timedelta(days=298))
        shorter = model.training_sample(events, int((start + dt.timedelta(days=200)).timestamp()))
        self.assertEqual(len(shorter), 199)

    def test_predict_one_uses_the_shared_standardized_ols_helper(self):
        train = []
        for index in range(180):
            train.append({
                "pre_rv24_log": 0.1 + index / 1000,
                "pre_rv168_log": 0.2 + index / 900,
                "abs_return24_bps": 5.0 + index / 10,
                "dex_turnover_7d_log": 0.01 + index / 10000,
                "target": 0.5 + index / 100,
            })
        current = {
            "pre_rv24_log": 0.3,
            "pre_rv168_log": 0.4,
            "abs_return24_bps": 10.0,
            "dex_turnover_7d_log": 0.02,
            "target": 0.6,
        }
        with patch.object(model.base, "fit_ols_predict", return_value=0.75) as fit:
            result = model.predict_one(train, current, model.AUG_FEATURES)
        self.assertEqual(result, 0.75)
        self.assertEqual(fit.call_args.args[2], list(model.AUG_FEATURES))
        self.assertEqual(len(fit.call_args.args[0]), 180)

    def test_forecast_targets_may_touch_but_never_overlap(self):
        valid = [
            {"signal_ts": 0, "target_end_ts": 86400},
            {"signal_ts": 86400, "target_end_ts": 172800},
        ]
        model.assert_non_overlapping_forecasts(valid)
        invalid = [
            {"signal_ts": 0, "target_end_ts": 86401},
            {"signal_ts": 86400, "target_end_ts": 172800},
        ]
        with self.assertRaisesRegex(ValueError, "overlap"):
            model.assert_non_overlapping_forecasts(invalid)

    def test_frozen_disposition_rules_are_applied_without_tuning(self):
        validation = {"baseline_rmse": 2.0, "augmented_rmse": 1.8}
        test = {"baseline_rmse": 2.0, "augmented_rmse": 1.9}
        self.assertEqual(
            model.disposition(validation, test, {"ci95_lower": 0.01, "ci95_upper": 0.5}),
            "PROMISING",
        )
        self.assertEqual(
            model.disposition(
                {"baseline_rmse": 1.0, "augmented_rmse": 1.1},
                {"baseline_rmse": 1.0, "augmented_rmse": 1.2},
                {"ci95_lower": -0.5, "ci95_upper": -0.01},
            ),
            "REJECTED",
        )
        self.assertEqual(
            model.disposition(
                validation,
                {"baseline_rmse": 1.0, "augmented_rmse": 1.1},
                {"ci95_lower": -0.1, "ci95_upper": 0.1},
            ),
            "INCONCLUSIVE",
        )

    def test_paired_loss_bootstrap_is_deterministic_and_positive_means_augmented_better(self):
        rows = [
            {"baseline_squared_error": 2.0, "augmented_squared_error": 1.0}
            for _ in range(30)
        ]
        first = model.paired_loss_block_bootstrap(rows, reps=25, block_size=7, seed=123)
        second = model.paired_loss_block_bootstrap(rows, reps=25, block_size=7, seed=123)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["mean_baseline_minus_augmented_squared_loss"], 1.0)
        self.assertAlmostEqual(first["ci95_lower"], 1.0)
        self.assertAlmostEqual(first["ci95_upper"], 1.0)
        self.assertEqual(first["bootstrap_fraction_positive"], 1.0)

    def test_frozen_manifest_requires_exact_run_commit_and_content_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.json"
            payload = {
                "status": "PASS",
                "hypothesis_id": model.HYPOTHESIS_ID,
                "workflow_run_id": model.EXPECTED_PREFLIGHT_RUN_ID,
                "source_commit_sha": model.EXPECTED_PREFLIGHT_SOURCE_SHA,
                "backtest_run": False,
                "raw_observations_saved": False,
                "binance_hourly_archives": {
                    "monthly_archive_count": 70,
                    "daily_gap_repair_archive_count": 7,
                    "expected_hourly_rows": 51120,
                    "observed_hourly_rows": 51106,
                    "missing_hours": 14,
                    "maximum_consecutive_missing_hours": 4,
                },
            }
            raw = json.dumps(payload, sort_keys=True).encode()
            path.write_bytes(raw)
            with patch.object(model, "PREFLIGHT_MANIFEST", path), patch.object(
                model, "EXPECTED_PREFLIGHT_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest()
            ):
                frozen, digest = model.load_frozen_manifest()
            self.assertEqual(frozen["workflow_run_id"], model.EXPECTED_PREFLIGHT_RUN_ID)
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            with patch.object(model, "PREFLIGHT_MANIFEST", path), patch.object(
                model, "EXPECTED_PREFLIGHT_MANIFEST_SHA256", "0" * 64
            ):
                with self.assertRaisesRegex(model.SourceMismatchError, "SHA-256 mismatch"):
                    model.load_frozen_manifest()

    def test_archive_provenance_comparison_rejects_any_hash_or_schema_change(self):
        frozen = {
            "period_type": "monthly",
            "period": "2021-01",
            "url": "https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2021-01.zip",
            "checksum_url": "https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2021-01.zip.CHECKSUM",
            "archive_sha256": "a" * 64,
            "checksum_sha256": "b" * 64,
            "checksum_verified": True,
            "rows": 744,
            "timestamp_unit": "milliseconds",
            "close_time_validation": "within_hourly_interval; open_time_is_grid_anchor",
            "first_timestamp": "2021-01-01T00:00:00+00:00",
            "last_timestamp": "2021-01-31T23:00:00+00:00",
        }
        model.assert_archive_record_matches(dict(frozen), frozen)
        changed = dict(frozen, archive_sha256="c" * 64)
        with self.assertRaisesRegex(model.SourceMismatchError, "archive_sha256"):
            model.assert_archive_record_matches(changed, frozen)


if __name__ == "__main__":
    unittest.main()
