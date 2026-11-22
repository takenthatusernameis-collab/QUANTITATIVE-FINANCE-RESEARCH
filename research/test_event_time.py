from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from event_time import (
    SECONDS_PER_YEAR,
    add_event_time_features,
    elapsed_seconds,
    event_time_backtest,
    event_time_benchmark_backtest,
    event_time_metrics,
    event_time_pooled_oos_summary,
    make_event_time_positions,
    validate_event_time_frame,
)


def make_frame(index: pd.DatetimeIndex, eth_open=None, btc_open=None) -> pd.DataFrame:
    n = len(index)
    eth = np.asarray(eth_open if eth_open is not None else [100.0] * n, dtype=float)
    btc = np.asarray(btc_open if btc_open is not None else [50.0] * n, dtype=float)
    return pd.DataFrame({
        "eth_open": eth,
        "btc_open": btc,
        "eth_close": eth,
        "btc_close": btc,
    }, index=index)


class EventTimeAccountingTests(unittest.TestCase):
    def test_six_hour_gap_remains_six_elapsed_hours(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T12:00:00Z",
        ])
        frame = make_frame(index, [100, 110, 121], [50, 50, 50])
        position = pd.Series([0.0, 1.0, 1.0], index=index)
        beta = pd.Series(1.0, index=index)
        result = event_time_backtest(frame, position, beta, 0, 0, 0, 1)
        self.assertEqual(result["elapsed_seconds"].tolist(), [0.0, 21600.0, 21600.0])
        self.assertAlmostEqual(result.loc[index[1], "gross_return"], 0.0)
        self.assertAlmostEqual(result.loc[index[2], "gross_return"], 0.05)
        metrics = event_time_metrics(result)
        self.assertAlmostEqual(metrics["elapsed_years"], 12 * 3600 / SECONDS_PER_YEAR)

    def test_close_signal_executes_at_next_observed_open_only(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T07:00:00Z",
            "2026-01-01T13:00:00Z",
        ])
        z = pd.Series([-2.5, -2.4, -0.1, 0.1], index=index)
        beta = pd.Series(1.0, index=index)
        position, trades = make_event_time_positions(
            z, beta, index[0], index[-1] + pd.Timedelta(hours=1)
        )
        self.assertEqual(position.tolist(), [0.0, 1.0, 1.0, 0.0])
        self.assertEqual(position.index.tolist(), index.tolist())
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["hold_seconds"], 7 * 3600)
        self.assertEqual(trades[0]["exit_reason"], "mean_reversion_exit")

    def test_max_hold_uses_elapsed_time_and_records_execution_delay(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-08T01:00:00Z",
            "2026-01-08T02:00:00Z",
        ])
        z = pd.Series([-3.0, -3.0, 1.0, 1.0], index=index)
        beta = pd.Series(1.0, index=index)
        position, trades = make_event_time_positions(
            z, beta, index[0], index[-1] + pd.Timedelta(hours=1),
            max_hold=pd.Timedelta(days=7),
        )
        self.assertEqual(position.tolist(), [0.0, 1.0, 1.0, 0.0])
        self.assertAlmostEqual(trades[0]["hold_days"], 7 + 1 / 24)
        self.assertEqual(trades[0]["exit_reason"], "max_hold")

    def test_borrow_cost_is_prorated_by_actual_elapsed_time(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T12:00:00Z",
        ])
        frame = make_frame(index)
        position = pd.Series([0.0, -1.0, -1.0], index=index)
        beta = pd.Series(1.0, index=index)
        result = event_time_backtest(
            frame, position, beta, 0, 0, 0, 1, borrow_bps_per_day=100
        )
        # Borrow accrues over the six hours after the short is actually opened.
        self.assertAlmostEqual(result.loc[index[2], "borrow_cost"], 0.00125)

    def test_funding_inside_gap_uses_position_held_at_settlement(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T12:00:00Z",
        ])
        frame = make_frame(index)
        position = pd.Series([0.0, 1.0, 1.0], index=index)
        beta = pd.Series(1.0, index=index)
        eth_funding = pd.Series(
            [0.001], index=pd.to_datetime(["2026-01-01T09:00:00Z"])
        )
        btc_funding = pd.Series(
            [0.002], index=pd.to_datetime(["2026-01-01T09:00:00Z"])
        )
        result = event_time_backtest(
            frame, position, beta, 0, 0, 0, 1,
            funding_eth=eth_funding, funding_btc=btc_funding,
        )
        self.assertAlmostEqual(result.loc[index[1], "funding_pnl"], 0.0)
        self.assertAlmostEqual(result.loc[index[2], "funding_pnl"], 0.0005)

    def test_funding_after_last_observation_is_rejected(self):
        index = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T06:00:00Z"])
        frame = make_frame(index)
        position = pd.Series([0.0, 0.0], index=index)
        beta = pd.Series(1.0, index=index)
        funding = pd.Series(
            [0.001], index=pd.to_datetime(["2026-01-01T07:00:00Z"])
        )
        with self.assertRaisesRegex(ValueError, "after the last observed"):
            event_time_backtest(
                frame, position, beta, 0, 0, 0, 1, funding_eth=funding
            )

    def test_calendar_time_annualization_is_not_observation_count_annualization(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T12:00:00Z",
        ])
        frame = make_frame(index, [100, 110, 121], [50, 50, 50])
        position = pd.Series([0.0, 0.0, 0.0], index=index)
        beta = pd.Series(1.0, index=index)
        result = event_time_backtest(frame, position, beta, 0, 0, 0, 1)
        result.loc[index[1], "net_return"] = 0.10
        result.loc[index[2], "net_return"] = 0.10
        metrics = event_time_metrics(result)
        elapsed_years = 12 * 3600 / SECONDS_PER_YEAR
        expected_cagr = np.expm1(2 * np.log1p(0.10) / elapsed_years)
        self.assertAlmostEqual(metrics["elapsed_years"], elapsed_years)
        self.assertAlmostEqual(metrics["CAGR"], expected_cagr)

    def test_time_window_features_do_not_use_future_observations(self):
        index = pd.date_range("2026-01-01", periods=24 * 40, freq="h", tz="UTC")
        index = index.delete([100, 101, 102])
        rng = np.random.default_rng(19)
        btc = 50_000 * np.exp(np.cumsum(rng.normal(0, 0.001, len(index))))
        eth = btc * 0.07 * np.exp(np.cumsum(rng.normal(0, 0.001, len(index))))
        frame = make_frame(index, eth, btc)
        first = add_event_time_features(frame, lookback_days=2, min_observation_fraction=0.9)
        changed = frame.copy()
        cutoff = index[24 * 20]
        changed.loc[changed.index > cutoff, "eth_close"] *= 3.0
        changed.loc[changed.index > cutoff, "eth_open"] *= 3.0
        second = add_event_time_features(changed, lookback_days=2, min_observation_fraction=0.9)
        for key in ("fixed_z", "dynamic_z", "beta", "alpha"):
            pd.testing.assert_series_equal(
                first[key].loc[:cutoff], second[key].loc[:cutoff],
                check_names=False,
            )

    def test_duplicate_unsorted_and_missing_price_observations_fail_closed(self):
        index = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])
        frame = make_frame(index)
        duplicate = pd.concat([frame, frame.iloc[[1]]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_event_time_frame(duplicate)
        unsorted = frame.iloc[::-1]
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            validate_event_time_frame(unsorted)
        missing = frame.copy()
        missing.loc[index[1], "eth_open"] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_event_time_frame(missing)

    def test_elapsed_seconds_rejects_naive_timestamps(self):
        naive = pd.date_range("2026-01-01", periods=2, freq="h")
        with self.assertRaisesRegex(ValueError, "timezone-aware UTC"):
            elapsed_seconds(naive)


    def test_event_time_benchmark_uses_elapsed_borrow_and_funding(self):
        index = pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T06:00:00Z",
            "2026-01-01T12:00:00Z",
        ])
        frame = make_frame(index)
        funding_eth = pd.Series([0.001], index=pd.to_datetime(["2026-01-01T09:00:00Z"]))
        funding_btc = pd.Series([0.002], index=pd.to_datetime(["2026-01-01T09:00:00Z"]))
        result = event_time_benchmark_backtest(
            frame, index, (0.5, -0.5), False,
            fee_bps=10, slippage_bps=0, spread_bps=0,
            funding_eth=funding_eth, funding_btc=funding_btc,
            borrow_bps_per_day=100,
        )
        self.assertEqual(result["elapsed_seconds"].tolist(), [0.0, 21600.0, 21600.0])
        self.assertAlmostEqual(result.loc[index[1], "borrow_cost"], 0.00125)
        final_short_notional = (
            max(-result.loc[index[2], "held_w_eth"], 0.0)
            + max(-result.loc[index[2], "held_w_btc"], 0.0)
        )
        expected_final_borrow = final_short_notional * 100 / 10_000 * 6 / 24
        self.assertAlmostEqual(
            result.loc[index[2], "borrow_cost"], expected_final_borrow
        )
        expected_funding_pnl = -(
            result.loc[index[2], "held_w_eth"] * 0.001
            + result.loc[index[2], "held_w_btc"] * 0.002
        )
        self.assertAlmostEqual(
            result.loc[index[2], "funding_pnl"], expected_funding_pnl
        )
        self.assertAlmostEqual(result.loc[index[0], "cost"], 0.001)
        stats = event_time_metrics(result)
        expected = np.prod(1.0 + result["net_return"].to_numpy()) - 1.0
        self.assertAlmostEqual(stats["total_return"], expected)
        self.assertLess(stats["total_return"], 0.0)

    def test_event_time_metrics_include_zero_duration_entry_cost(self):
        sample = pd.DataFrame({
            "elapsed_seconds": [0.0, 3600.0],
            "net_return": [-0.01, 0.0],
            "turnover": [1.0, 0.0],
        })
        stats = event_time_metrics(sample)
        elapsed_years = 3600.0 / SECONDS_PER_YEAR
        self.assertAlmostEqual(stats["total_return"], -0.01)
        self.assertAlmostEqual(
            stats["CAGR"], np.expm1(np.log(0.99) / elapsed_years)
        )
        self.assertAlmostEqual(stats["turnover_per_year"], 1.0 / elapsed_years)


class PooledEventTimeOOSTests(unittest.TestCase):
    def make_oos_returns(self):
        rows = []
        base = pd.Timestamp("2024-01-01T00:00:00Z")
        for fold, offset_days in ((1, 0), (2, 100)):
            timestamps = [
                base + pd.Timedelta(days=offset_days + day)
                for day in (0, 1, 2)
            ]
            gross = [0.0, 0.01, -0.005]
            cost = [0.001, 0.0005, 0.0]
            funding = [0.0, 0.0, 0.0]
            borrow = [0.0, 0.0, 0.0]
            for i, timestamp in enumerate(timestamps):
                rows.append({
                    "timestamp": timestamp,
                    "market": "spot",
                    "interval": "1h",
                    "fold": fold,
                    "variant": "fixed_1x1",
                    "elapsed_seconds": 0.0 if i == 0 else 86400.0,
                    "gross_return": gross[i],
                    "cost": cost[i],
                    "funding_pnl": funding[i],
                    "borrow_cost": borrow[i],
                    "net_return": gross[i] - cost[i] + funding[i] - borrow[i],
                    "turnover": 1.0 if i == 0 else 0.0,
                })
        return pd.DataFrame(rows)

    def test_pooled_oos_excludes_inter_fold_calendar_gaps_and_derives_cost_cases(self):
        summary = event_time_pooled_oos_summary(
            self.make_oos_returns(), block_days=1.0, n_bootstrap=30, seed=17
        )
        self.assertEqual(set(summary["cost_multiplier"]), {1.0, 1.5, 2.0})
        base = summary.loc[summary["cost_multiplier"] == 1.0].iloc[0]
        self.assertAlmostEqual(base["elapsed_days"], 4.0)
        self.assertEqual(base["fold_count"], 2)
        self.assertEqual(base["bootstrap_status"], "COMPUTED")
        self.assertEqual(base["bootstrap_replicates"], 30)
        self.assertTrue(np.isfinite(base["continuous_time_sharpe_ci_lower"]))
        self.assertTrue(np.isfinite(base["continuous_time_sharpe_ci_upper"]))
        total_returns = summary.set_index("cost_multiplier")["total_return"]
        self.assertGreater(total_returns.loc[1.0], total_returns.loc[1.5])
        self.assertGreater(total_returns.loc[1.5], total_returns.loc[2.0])

    def test_pooled_oos_bootstrap_is_deterministic_for_a_fixed_seed(self):
        frame = self.make_oos_returns()
        first = event_time_pooled_oos_summary(
            frame, block_days=1.0, n_bootstrap=25, seed=123
        )
        second = event_time_pooled_oos_summary(
            frame, block_days=1.0, n_bootstrap=25, seed=123
        )
        columns = [
            "CAGR_ci_lower", "CAGR_ci_upper",
            "continuous_time_sharpe_ci_lower", "continuous_time_sharpe_ci_upper",
            "max_drawdown_ci_lower", "max_drawdown_ci_upper",
        ]
        pd.testing.assert_frame_equal(first[columns], second[columns])

    def test_pooled_oos_rejects_elapsed_time_that_does_not_match_utc_timestamps(self):
        frame = self.make_oos_returns()
        frame.loc[1, "elapsed_seconds"] = 7200.0
        with self.assertRaisesRegex(ValueError, "do not match observed UTC timestamps"):
            event_time_pooled_oos_summary(
                frame, block_days=1.0, n_bootstrap=10
            )

    def test_pooled_oos_requires_block_duration_to_cover_largest_observation_gap(self):
        with self.assertRaisesRegex(ValueError, "increase block_days"):
            event_time_pooled_oos_summary(
                self.make_oos_returns(), block_days=0.5, n_bootstrap=10
            )


if __name__ == "__main__":
    unittest.main()
