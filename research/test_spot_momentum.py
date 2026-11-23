from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import spot_momentum as momentum


def make_frame(index: pd.DatetimeIndex, eth_open=None, btc_open=None) -> pd.DataFrame:
    n = len(index)
    eth = np.asarray(eth_open if eth_open is not None else np.full(n, 100.0), dtype=float)
    btc = np.asarray(btc_open if btc_open is not None else np.full(n, 50.0), dtype=float)
    return pd.DataFrame({
        "eth_open": eth,
        "btc_open": btc,
        "eth_close": eth,
        "btc_close": btc,
    }, index=index)


class SpotMomentumTests(unittest.TestCase):
    def test_daily_signal_uses_200_valid_closes_and_current_close(self):
        index = pd.date_range("2020-01-01T00:00:00Z", periods=24 * 205, freq="h")
        ratio = np.full(len(index), 2.0)
        ratio[-24:] = 3.0
        frame = make_frame(index, eth_open=ratio * 50.0, btc_open=np.full(len(index), 50.0))
        daily = momentum.build_daily_signals(frame)
        last = daily.iloc[-1]
        self.assertEqual(last["signal"], "ETH")
        self.assertAlmostEqual(last["sma_200"], (199 * 2.0 + 3.0) / 200.0)
        self.assertEqual(last["close_staleness_hours"], 0.0)

    def test_stale_daily_close_is_skipped_without_forward_fill(self):
        index = pd.date_range("2020-01-01T00:00:00Z", periods=24 * 205, freq="h")
        missing = pd.to_datetime([
            "2020-07-22T22:00:00Z", "2020-07-22T23:00:00Z"
        ])
        index = index[~index.isin(missing)]
        frame = make_frame(index)
        daily = momentum.build_daily_signals(frame)
        row = daily.loc[
            daily["utc_date"] == pd.Timestamp("2020-07-22T00:00:00Z")
        ].iloc[0]
        self.assertEqual(row["close_staleness_hours"], 2.0)
        self.assertTrue(pd.isna(row["ratio"]))
        self.assertTrue(pd.isna(row["signal"]))

    def test_stale_day_does_not_reset_200_valid_close_sma_window(self):
        index = pd.date_range("2020-01-01T00:00:00Z", periods=24 * 205, freq="h")
        missing = pd.to_datetime([
            "2020-07-19T22:00:00Z", "2020-07-19T23:00:00Z"
        ])
        index = index[~index.isin(missing)]
        frame = make_frame(index)
        daily = momentum.build_daily_signals(frame)
        stale = daily.loc[
            daily["utc_date"] == pd.Timestamp("2020-07-19T00:00:00Z")
        ].iloc[0]
        next_day = daily.loc[
            daily["utc_date"] == pd.Timestamp("2020-07-20T00:00:00Z")
        ].iloc[0]
        self.assertTrue(pd.isna(stale["ratio"]))
        self.assertTrue(pd.notna(next_day["sma_200"]))
        self.assertIn(next_day["signal"], ("ETH", "BTC"))

    def test_signal_executes_at_first_observed_open_after_midnight(self):
        index = pd.date_range("2020-01-01T00:00:00Z", periods=24 * 230, freq="h")
        missing_open = pd.Timestamp("2020-07-19T00:00:00Z")
        index = index[index != missing_open]
        frame = make_frame(index)
        targets, signals = momentum.build_target_schedule(
            frame,
            oos_start=pd.Timestamp("2020-07-20T00:00:00Z"),
            oos_end_exclusive=pd.Timestamp("2020-08-01T00:00:00Z"),
        )
        previous_day = signals.loc[
            signals["signal_date"] == pd.Timestamp("2020-07-18T00:00:00Z")
        ].iloc[0]
        self.assertEqual(
            previous_day["execution_timestamp"],
            pd.Timestamp("2020-07-19T01:00:00Z"),
        )
        self.assertEqual(targets.index[0], pd.Timestamp("2020-07-20T00:00:00Z"))

    def test_eth_to_btc_rotation_charges_two_one_way_legs(self):
        index = pd.date_range("2022-01-01T00:00:00Z", periods=4, freq="h")
        frame = make_frame(index)
        targets = pd.DataFrame(
            {"w_eth": [1.0, 0.0, 0.0, 0.0], "w_btc": [0.0, 1.0, 1.0, 1.0]},
            index=index,
        )
        result = momentum.portfolio_backtest(frame, targets, 10.0)
        self.assertAlmostEqual(result.iloc[0]["turnover"], 1.0)
        self.assertAlmostEqual(result.iloc[0]["cost"], 0.001)
        self.assertAlmostEqual(result.iloc[1]["turnover"], 2.0)
        self.assertAlmostEqual(result.iloc[1]["cost"], 0.002)
        self.assertAlmostEqual(result.iloc[-1]["turnover"], 1.0)

    def test_buy_and_hold_does_not_rebalance_after_price_drift(self):
        index = pd.date_range("2022-01-01T00:00:00Z", periods=4, freq="h")
        frame = make_frame(
            index,
            eth_open=[100.0, 120.0, 120.0, 120.0],
            btc_open=[100.0, 100.0, 100.0, 100.0],
        )
        targets = momentum.benchmark_target_schedule(index, "50_50_ETH_BTC_buy_hold")
        result = momentum.portfolio_backtest(frame, targets, 10.0)
        self.assertAlmostEqual(result.iloc[1]["gross_return"], 0.10)
        self.assertAlmostEqual(result.iloc[1]["turnover"], 0.0)
        self.assertAlmostEqual(result.iloc[2]["held_w_eth"], 0.5454545454545454)

    def test_monthly_rebalanced_benchmark_has_one_target_per_month(self):
        index = pd.date_range("2022-01-01T01:00:00Z", periods=24 * 40, freq="h")
        targets = momentum.benchmark_target_schedule(
            index, "50_50_ETH_BTC_monthly_rebalanced"
        )
        finite = targets.dropna()
        self.assertEqual(len(finite), 2)
        self.assertEqual(finite.index[0], index[0])
        self.assertEqual(finite.index[1], pd.Timestamp("2022-02-01T00:00:00Z"))

    def test_paired_bootstrap_is_deterministic_and_uses_paired_timestamps(self):
        index = pd.date_range("2022-01-01T00:00:00Z", periods=24 * 40, freq="h")
        elapsed = np.r_[0.0, np.full(len(index) - 1, 3600.0)]
        strategy = pd.DataFrame({
            "elapsed_seconds": elapsed,
            "net_return": np.r_[-0.001, np.full(len(index) - 1, 0.0002)],
        }, index=index)
        benchmark = pd.DataFrame({
            "elapsed_seconds": elapsed,
            "net_return": np.r_[-0.001, np.full(len(index) - 1, 0.0001)],
        }, index=index)
        first = momentum.paired_excess_cagr_bootstrap(
            strategy, benchmark, 3.0, replications=100, seed=7
        )
        second = momentum.paired_excess_cagr_bootstrap(
            strategy, benchmark, 3.0, replications=100, seed=7
        )
        self.assertEqual(first, second)
        self.assertGreater(first["excess_CAGR_CI_low"], 0.0)

    def test_bootstrap_rejects_misaligned_timestamps(self):
        index = pd.date_range("2022-01-01T00:00:00Z", periods=100, freq="h")
        elapsed = np.r_[0.0, np.full(99, 3600.0)]
        left = pd.DataFrame({"elapsed_seconds": elapsed, "net_return": 0.0}, index=index)
        right = left.copy()
        right.index = right.index + pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "identical timestamps"):
            momentum.paired_excess_cagr_bootstrap(left, right, 1.0, 100, 1)

    def test_decision_requires_all_preregistered_gates(self):
        variants = []
        for cost in momentum.COST_BPS_PER_LEG:
            for variant in momentum.VARIANTS:
                is_strategy = variant == "ETH_BTC_momentum_200d"
                variants.append({
                    "cost_bps_per_leg": cost,
                    "variant": variant,
                    "total_return": 0.25 if is_strategy else 0.10,
                    "CAGR": 0.10 if is_strategy else 0.05,
                    "Sharpe": 1.5 if is_strategy else 1.0,
                    "max_drawdown": -0.05 if is_strategy else -0.10,
                })
        metrics = pd.DataFrame(variants)
        bootstrap = pd.DataFrame({
            "block_days": [3.0, 7.0, 14.0],
            "excess_CAGR_CI_low": [0.01, 0.02, 0.005],
        })
        self.assertEqual(momentum.evaluate_decision(metrics, bootstrap)["status"], "GO")
        metrics.loc[
            (metrics["cost_bps_per_leg"] == 20.0)
            & (metrics["variant"] == "ETH_BTC_momentum_200d"),
            "total_return",
        ] = -0.01
        self.assertEqual(momentum.evaluate_decision(metrics, bootstrap)["status"], "NO-GO")

    def test_control_workflow_allowlists_spot_momentum_as_default_branch_only(self):
        workflow = Path(".github/workflows/eth-btc-research.yml").read_text()
        self.assertIn('"/qfr-run-eth-btc-spot-momentum"', workflow)
        self.assertIn('COMMAND="spot-momentum"', workflow)
        self.assertIn("needs.authorize.outputs.command == 'spot-momentum'", workflow)
        self.assertIn("python research/spot_momentum.py", workflow)
        self.assertIn("persist-credentials: false", workflow)

    def test_data_preparation_is_spot_only(self):
        with patch.object(momentum, "download_klines") as download, patch.object(
            momentum, "reconcile_spot_gaps"
        ), patch.object(
            momentum, "validate_spot_event_time_evidence",
            return_value={"accepted": True, "blockers": []},
        ):
            result = momentum.prepare_spot_data(
                "2020-01-01", "2026-10-31", Path("data")
            )
        self.assertTrue(result["accepted"])
        self.assertEqual(download.call_count, 2)
        self.assertTrue(all(call.args[0] == "spot" for call in download.call_args_list))


if __name__ == "__main__":
    unittest.main()
