import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_eth_btc as research


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def response(status_code, content=b"ok"):
    item = requests.Response()
    item.status_code = status_code
    item.url = "https://example.test/resource"
    item._content = content
    item.encoding = "utf-8"
    return item


class ResearchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
        self.frame = pd.DataFrame({
            "eth_open": [100.0, 110.0, 121.0, 121.0],
            "btc_open": [100.0, 100.0, 100.0, 100.0],
            "eth_close": [100.0, 110.0, 121.0, 121.0],
            "btc_close": [100.0, 100.0, 100.0, 100.0],
        }, index=self.index)


    def metric_frame(self, returns, positions=None, w_eth=None, w_btc=None):
        n = len(returns)
        index = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
        positions = np.zeros(n) if positions is None else np.asarray(positions, dtype=float)
        w_eth = positions / 2.0 if w_eth is None else np.asarray(w_eth, dtype=float)
        w_btc = -positions / 2.0 if w_btc is None else np.asarray(w_btc, dtype=float)
        held_eth = pd.Series(w_eth, index=index).shift(1).fillna(0.0)
        held_btc = pd.Series(w_btc, index=index).shift(1).fillna(0.0)
        return pd.DataFrame({
            "net_return": returns, "position": positions, "turnover": np.zeros(n),
            "w_eth": w_eth, "w_btc": w_btc,
            "held_w_eth": held_eth, "held_w_btc": held_btc,
        }, index=index)

    def test_bounded_retry_recovers_from_transient_503(self):
        session = FakeSession([response(503), response(200)])
        with patch.object(research.time, "sleep"):
            result = research.request_with_retry(session, "https://example.test/resource")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(session.calls, 2)

    def test_hourly_quality_reports_missing_bar_and_gap(self):
        observed = self.index.delete(2)
        result = research.hourly_quality(observed, "2024-01-01", "2024-01-01")
        self.assertEqual(result["missing_hourly_bars"], 21)
        self.assertEqual(result["longest_gap_hours"], 2.0)
        self.assertFalse(result["complete"])

    def test_close_signal_executes_next_open_and_pnl_starts_after_that_open(self):
        close_signal = pd.Series([1.0, 0.0, 0.0, 0.0], index=self.index)
        executed = research.shift_signal_to_next_open(close_signal)
        self.assertEqual(executed.tolist(), [0.0, 1.0, 0.0, 0.0])
        bt = research.backtest(
            self.frame, executed, pd.Series(1.0, index=self.index),
            0.0, 0.0, 0.0, 1.0,
        )
        self.assertAlmostEqual(bt.loc[self.index[1], "gross_return"], 0.0)
        self.assertAlmostEqual(bt.loc[self.index[2], "gross_return"], 0.05)

    def test_entry_and_exit_turnover_costs_are_charged_on_both_legs(self):
        position = pd.Series([0.0, 1.0, 1.0, 0.0], index=self.index)
        bt = research.backtest(
            self.frame, position, pd.Series(1.0, index=self.index),
            10.0, 2.0, 1.0, 1.0,
        )
        self.assertAlmostEqual(bt["turnover"].sum(), 2.0)
        self.assertAlmostEqual(bt["cost"].sum(), 0.0026)

    def test_funding_event_is_aligned_to_next_bar_when_off_grid(self):
        events = pd.Series(
            [0.001, 0.002],
            index=[self.index[0] + pd.Timedelta(minutes=30), self.index[3]],
        )
        aligned, quality = research.align_funding_events(events, self.index, "TEST")
        self.assertAlmostEqual(aligned.loc[self.index[1]], 0.001)
        self.assertAlmostEqual(aligned.loc[self.index[3]], 0.002)
        self.assertEqual(quality["off_grid_events"], 1)
        self.assertEqual(quality["max_alignment_lag_minutes"], 30.0)

    def test_funding_settlement_uses_position_held_before_settlement(self):
        position = pd.Series([1.0, 1.0, 1.0, 0.0], index=self.index)
        funding_eth = pd.Series([0.0, 0.001, 0.0, 0.0], index=self.index)
        funding_btc = pd.Series(0.0, index=self.index)
        bt = research.backtest(
            self.frame, position, pd.Series(1.0, index=self.index),
            0.0, 0.0, 0.0, 1.0, funding_eth, funding_btc,
        )
        self.assertAlmostEqual(bt.loc[self.index[1], "funding_pnl"], -0.0005)

    def test_funding_gap_is_not_mistaken_for_zero_funding(self):
        stamps = pd.DatetimeIndex([
            self.index[0],
            self.index[0] + pd.Timedelta(hours=8),
            self.index[0] + pd.Timedelta(hours=40),
        ])
        quality = research.funding_quality(
            stamps, self.index[0], self.index[0] + pd.Timedelta(hours=48)
        )
        self.assertFalse(quality["max_gap_ok"])
        self.assertFalse(quality["complete"])

    def test_missing_funding_file_fails_instead_of_returning_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                research.load_funding("ETHUSDT", self.index, Path(directory))

    def test_buy_hold_and_rebalanced_benchmarks_include_real_turnover(self):
        moving = self.frame.copy()
        moving["eth_open"] = [100.0, 120.0, 120.0, 120.0]
        moving["btc_open"] = [100.0, 100.0, 100.0, 110.0]
        buy_hold = research.benchmark_backtest(
            moving, self.index, (0.5, 0.5), False, 10.0, 0.0, 0.0
        )
        rebalanced = research.benchmark_backtest(
            moving, self.index, (0.5, 0.5), True, 10.0, 0.0, 0.0
        )
        self.assertGreater(rebalanced["turnover"].sum(), buy_hold["turnover"].sum())
        self.assertAlmostEqual(buy_hold.iloc[0]["cost"], 0.001)
        self.assertEqual(buy_hold.iloc[-1]["position"], 0.0)
        self.assertEqual(rebalanced.iloc[-1]["position"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[0]["held_w_eth"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[0]["held_w_btc"], 0.0)
        self.assertAlmostEqual(buy_hold.iloc[1]["held_w_eth"], 0.5)
        self.assertAlmostEqual(buy_hold.iloc[1]["held_w_btc"], 0.5)

    def test_flat_buy_hold_charges_one_entry_and_one_exit(self):
        flat = self.frame.copy()
        flat[["eth_open", "btc_open"]] = 100.0
        bt = research.benchmark_backtest(
            flat, self.index, (0.5, 0.5), False, 10.0, 0.0, 0.0
        )
        self.assertAlmostEqual(bt["turnover"].sum(), 2.0)
        self.assertAlmostEqual(bt["cost"].sum(), 0.002)

    def test_half_life_reports_exact_discrete_ar1_formula(self):
        rng = np.random.default_rng(123)
        n = 1200
        log_btc = np.cumsum(rng.normal(0.0, 0.002, n))
        spread = np.zeros(n)
        noise = rng.normal(0.0, 0.003, n)
        for i in range(1, n):
            spread[i] = 0.85 * spread[i - 1] + noise[i]
        idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
        frame = pd.DataFrame({
            "eth_close": np.exp(log_btc + spread),
            "btc_close": np.exp(log_btc),
        }, index=idx)
        result = research.diagnostics(frame)
        phi = result["ar1_phi"]
        if 0.0 < phi < 1.0:
            expected = -np.log(2.0) / np.log(phi)
            self.assertAlmostEqual(result["half_life_exact_ar1_bars"], expected)
            self.assertTrue(result["half_life_exact_valid"])
        self.assertEqual(result["diagnostic_scope"], "shared_static_ols_relationship")


    def test_sortino_downside_deviation_uses_all_observations_mixed(self):
        returns = pd.Series([0.10, -0.10, -0.10])
        expected = np.sqrt((0.0 + 0.01 + 0.01) / 3.0)
        self.assertAlmostEqual(research.downside_deviation(returns), expected)
        bt = self.metric_frame(returns)
        result = research.metrics(bt, 1)
        self.assertAlmostEqual(result["Sortino"], returns.mean() / expected)

    def test_sortino_downside_deviation_all_negative(self):
        returns = pd.Series([-0.10, -0.20])
        expected = np.sqrt((0.01 + 0.04) / 2.0)
        self.assertAlmostEqual(research.downside_deviation(returns), expected)

    def test_max_drawdown_includes_initial_nav(self):
        result = research.metrics(self.metric_frame([-0.10, 0.05]), 1)
        self.assertAlmostEqual(result["max_drawdown"], -0.10)

    def test_average_gross_exposure_aligns_with_returns(self):
        bt = self.metric_frame(
            [0.0, 0.0, 0.0], positions=[1.0, 1.0, 2.0],
            w_eth=[0.5, 0.5, 1.0], w_btc=[-0.5, -0.5, -1.0],
        )
        result = research.metrics(bt, 1)
        self.assertAlmostEqual(result["avg_gross_exposure"], 2.0 / 3.0)

    def test_funding_stress_is_um_only_and_rates_are_explicit(self):
        spot = research.stress_scenarios_for_market("spot")
        um = research.stress_scenarios_for_market("um")
        self.assertFalse(any("funding" in name.lower() for name in spot))
        funding_name = "UM funding: +10bp per leg for 3 settlements"
        self.assertIn(funding_name, um)
        self.assertIn("hypothetical, not observed", um[funding_name][3])
        self.assertAlmostEqual(um[funding_name][2], 0.003)

    def test_sharpe_interval_is_explicitly_exploratory_at_150_reps(self):
        result = research.metrics(self.metric_frame([0.01, -0.01, 0.0]), 1)
        self.assertEqual(result["Sharpe_CI_replications"], 150)
        self.assertIn("exploratory", result["Sharpe_CI_interpretation"])


if __name__ == "__main__":
    unittest.main()
