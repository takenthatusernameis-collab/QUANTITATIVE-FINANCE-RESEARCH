"""Preregistered ETH/BTC Spot relative-momentum rotation.

This module is deliberately Spot-only. It never reads funding data, uses leverage,
shorts either asset, merges venues, or places orders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from event_time import (
    SECONDS_PER_DAY,
    SECONDS_PER_YEAR,
    elapsed_seconds,
    event_time_metrics,
    validate_event_time_frame,
)
from run_eth_btc import (
    SYMBOLS,
    download_klines,
    load_pair,
    reconcile_spot_gaps,
    validate_spot_event_time_evidence,
)

EXPERIMENT_ID = "ETH-BTC-SPOT-MOMENTUM"
START_DATE = "2020-01-01"
END_DATE = "2026-10-31"
OOS_START = pd.Timestamp("2022-01-01T00:00:00Z")
OOS_END_EXCLUSIVE = pd.Timestamp("2026-11-01T00:00:00Z")
SMA_DAYS = 200
MAX_DAILY_CLOSE_STALENESS_HOURS = 1.0
COST_BPS_PER_LEG = (5.0, 10.0, 15.0, 20.0, 25.0, 50.0)
BASELINE_COST_BPS = 10.0
BOOTSTRAP_BLOCK_DAYS = (3.0, 7.0, 14.0)
BOOTSTRAP_PRIMARY_BLOCK_DAYS = 7.0
BOOTSTRAP_REPLICATIONS = 1000
BOOTSTRAP_SEED = 20261123
VARIANTS = (
    "ETH_BTC_momentum_200d",
    "BTC_buy_hold",
    "ETH_buy_hold",
    "50_50_ETH_BTC_buy_hold",
    "50_50_ETH_BTC_monthly_rebalanced",
)


class ResearchGateError(RuntimeError):
    """Raised when Spot provenance or experiment inputs are not accepted."""


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def spot_source_hashes(data_dir: Path) -> dict[str, str]:
    paths = {}
    for symbol in SYMBOLS:
        for suffix in ("1h.csv", "archive_manifest.json", "gap_reconciliation.json"):
            if suffix == "1h.csv":
                path = data_dir / "raw" / f"spot_{symbol}_1h.csv"
            elif suffix == "archive_manifest.json":
                path = data_dir / "raw" / f"spot_{symbol}_archive_manifest.json"
            else:
                path = data_dir / "raw" / f"spot_{symbol}_gap_reconciliation.json"
            if not path.is_file():
                raise ResearchGateError(f"Required Spot provenance file is missing: {path}")
            paths[str(path)] = sha256_file(path)
    return paths


def prepare_spot_data(start: str, end: str, data_dir: Path) -> dict:
    """Download only Binance Spot prices and independently reconcile observed gaps."""
    for symbol in SYMBOLS:
        download_klines(
            "spot", symbol, start, end, data_dir,
            allow_confirmed_no_trade_gaps=True,
        )
    for symbol in SYMBOLS:
        reconcile_spot_gaps(symbol, start, end, data_dir)
    evidence = validate_spot_event_time_evidence(data_dir, start, end)
    if not evidence.get("accepted", False):
        raise ResearchGateError(
            "Spot price observations failed the provenance/no-trade acceptance gate: "
            + "; ".join(evidence.get("blockers", []))
        )
    return evidence


def build_daily_signals(
    frame: pd.DataFrame,
    max_close_staleness_hours: float = MAX_DAILY_CLOSE_STALENESS_HOURS,
) -> pd.DataFrame:
    """Build the frozen 200-observation daily ratio SMA without filling missing data.

    A UTC day's close is its last observed hourly close, provided that close is
    no more than the configured staleness allowance before midnight. A stale or
    absent daily close produces no new signal; the previous target is retained.
    """
    validate_event_time_frame(frame)
    if not np.isfinite(max_close_staleness_hours) or max_close_staleness_hours < 0:
        raise ValueError("Daily-close staleness allowance must be finite and non-negative")

    normalized_days = frame.index.normalize()
    last_positions = (
        pd.Series(np.arange(len(frame)), index=normalized_days)
        .groupby(level=0)
        .last()
        .to_numpy(dtype=int)
    )
    last_bar_times = frame.index[last_positions]
    daily = frame.iloc[last_positions][["eth_close", "btc_close"]].copy()
    daily.index = last_bar_times.normalize()
    daily.index.name = "utc_date"
    daily["source_bar_timestamp"] = last_bar_times
    day_end = daily.index + pd.Timedelta(days=1)
    close_time = last_bar_times + pd.Timedelta(hours=1)
    daily["close_staleness_hours"] = (
        (day_end - close_time).total_seconds() / 3600.0
    )
    daily["ratio"] = daily["eth_close"].astype(float) / daily["btc_close"].astype(float)
    eligible = (
        daily["close_staleness_hours"].ge(0)
        & daily["close_staleness_hours"].le(max_close_staleness_hours)
    )
    daily.loc[~eligible, "ratio"] = np.nan
    valid_ratio = daily.loc[daily["ratio"].notna(), "ratio"]
    daily["sma_200"] = valid_ratio.rolling(
        window=SMA_DAYS, min_periods=SMA_DAYS
    ).mean().reindex(daily.index)
    valid = daily["ratio"].notna() & daily["sma_200"].notna()
    daily["signal"] = pd.Series(pd.NA, index=daily.index, dtype="object")
    daily.loc[valid & (daily["ratio"] > daily["sma_200"]), "signal"] = "ETH"
    daily.loc[valid & (daily["ratio"] <= daily["sma_200"]), "signal"] = "BTC"
    daily["signal_known_at"] = daily.index + pd.Timedelta(days=1)

    execution_times = []
    delays = []
    for known_at in daily["signal_known_at"]:
        location = int(frame.index.searchsorted(known_at, side="left"))
        if location >= len(frame.index):
            execution_times.append(pd.NaT)
            delays.append(np.nan)
        else:
            execution_at = frame.index[location]
            execution_times.append(execution_at)
            delays.append((execution_at - known_at).total_seconds() / 60.0)
    daily["execution_timestamp"] = pd.to_datetime(execution_times, utc=True)
    daily["execution_delay_minutes"] = delays
    daily["signal_date"] = daily.index
    return daily.reset_index()


def build_target_schedule(
    frame: pd.DataFrame,
    oos_start: pd.Timestamp = OOS_START,
    oos_end_exclusive: pd.Timestamp = OOS_END_EXCLUSIVE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map daily close signals to the first observed open at/after next UTC midnight."""
    validate_event_time_frame(frame)
    if oos_start.tzinfo is None or oos_end_exclusive.tzinfo is None:
        raise ValueError("OOS boundaries must be timezone-aware")
    oos_start = oos_start.tz_convert("UTC")
    oos_end_exclusive = oos_end_exclusive.tz_convert("UTC")
    if oos_start >= oos_end_exclusive:
        raise ValueError("OOS start must precede OOS end")

    index = frame.index[(frame.index >= oos_start) & (frame.index < oos_end_exclusive)]
    if len(index) < 2:
        raise ResearchGateError("Fewer than two observed hourly opens exist in the OOS window")

    signals = build_daily_signals(frame)
    valid_signals = signals.loc[
        signals["signal"].notna() & signals["execution_timestamp"].notna()
    ].sort_values("signal_date")
    execution_map: dict[pd.Timestamp, tuple[str, pd.Timestamp]] = {}
    for row in valid_signals.itertuples(index=False):
        execution_at = pd.Timestamp(row.execution_timestamp)
        if oos_start <= execution_at < oos_end_exclusive and execution_at in index:
            execution_map[execution_at] = (
                str(row.signal), pd.Timestamp(row.signal_date)
            )

    target_assets = []
    source_dates = []
    current_asset = None
    current_signal_date = None
    for timestamp in index:
        if timestamp in execution_map:
            current_asset, current_signal_date = execution_map[timestamp]
        if current_asset is None or current_signal_date is None:
            raise ResearchGateError(
                f"No valid pre-OOS momentum signal was executable by {timestamp}"
            )
        target_assets.append(current_asset)
        source_dates.append(current_signal_date)

    targets = pd.DataFrame(index=index)
    targets["target_asset"] = target_assets
    targets["signal_date"] = source_dates
    targets["w_eth"] = (targets["target_asset"] == "ETH").astype(float)
    targets["w_btc"] = (targets["target_asset"] == "BTC").astype(float)
    return targets, signals


def benchmark_target_schedule(index: pd.DatetimeIndex, variant: str) -> pd.DataFrame:
    """Return sparse target weights; NaN rows mean hold the drifted portfolio."""
    targets = pd.DataFrame(np.nan, index=index, columns=["w_eth", "w_btc"], dtype=float)
    if variant == "BTC_buy_hold":
        targets.iloc[0] = (0.0, 1.0)
    elif variant == "ETH_buy_hold":
        targets.iloc[0] = (1.0, 0.0)
    elif variant == "50_50_ETH_BTC_buy_hold":
        targets.iloc[0] = (0.5, 0.5)
    elif variant == "50_50_ETH_BTC_monthly_rebalanced":
        months = index.tz_convert("UTC").tz_localize(None).to_period("M")
        first_in_month = np.r_[True, months[1:] != months[:-1]]
        targets.loc[index[first_in_month], ["w_eth", "w_btc"]] = (0.5, 0.5)
    else:
        raise ValueError(f"Unknown benchmark: {variant}")
    return targets


def portfolio_backtest(
    frame: pd.DataFrame,
    target_weights: pd.DataFrame,
    cost_bps_per_leg: float,
) -> pd.DataFrame:
    """Long-only, cash-funded portfolio accounting on actual observed open-to-open intervals.

    Turnover is the sum of absolute ETH and BTC weight changes. A full ETH-to-BTC
    rotation therefore pays two one-way legs. Entry and final liquidation each
    pay one leg for a 100% single-asset portfolio.
    """
    validate_event_time_frame(frame)
    index = frame.index
    if not target_weights.index.equals(index):
        raise ValueError("Target schedule index must match the price index exactly")
    if not {"w_eth", "w_btc"}.issubset(target_weights.columns):
        raise ValueError("Target schedule must contain w_eth and w_btc")
    if not np.isfinite(cost_bps_per_leg) or cost_bps_per_leg < 0:
        raise ValueError("Cost per leg must be finite and non-negative")
    if len(index) < 2:
        raise ValueError("At least two observations are required")

    schedule = target_weights[["w_eth", "w_btc"]].astype(float)
    values = schedule.to_numpy(dtype=float)
    one_missing = np.isnan(values).sum(axis=1) == 1
    if one_missing.any():
        raise ValueError("Both target weights must be finite together or both be NaN")
    finite_rows = np.isfinite(values).all(axis=1)
    if (values[finite_rows] < -1e-12).any():
        raise ValueError("Spot momentum portfolios cannot hold short weights")
    if (values[finite_rows].sum(axis=1) > 1.0 + 1e-9).any():
        raise ValueError("Target weights cannot exceed 100% gross long exposure")
    if not finite_rows[0]:
        raise ValueError("The first OOS observation requires an explicit initial target")

    elapsed = elapsed_seconds(index).to_numpy(dtype=float)
    eth_open = frame["eth_open"].astype(float).to_numpy()
    btc_open = frame["btc_open"].astype(float).to_numpy()
    previous_eth = 0.0
    previous_btc = 0.0
    rows = []

    for ordinal, timestamp in enumerate(index):
        gross_return = 0.0
        eth_return = btc_return = 0.0
        if ordinal:
            eth_return = eth_open[ordinal] / eth_open[ordinal - 1] - 1.0
            btc_return = btc_open[ordinal] / btc_open[ordinal - 1] - 1.0
            gross_return = previous_eth * eth_return + previous_btc * btc_return
        pretrade_nav = 1.0 + gross_return
        if pretrade_nav <= 0:
            raise RuntimeError("Portfolio NAV became non-positive")
        drift_eth = previous_eth
        drift_btc = previous_btc
        if ordinal:
            drift_eth = previous_eth * (1.0 + eth_return) / pretrade_nav
            drift_btc = previous_btc * (1.0 + btc_return) / pretrade_nav

        if ordinal == len(index) - 1:
            target_eth = target_btc = 0.0
        elif finite_rows[ordinal]:
            target_eth = float(values[ordinal, 0])
            target_btc = float(values[ordinal, 1])
        else:
            target_eth, target_btc = drift_eth, drift_btc

        turnover = abs(target_eth - drift_eth) + abs(target_btc - drift_btc)
        cost = turnover * cost_bps_per_leg / 10_000.0
        net_return = gross_return - cost
        if net_return <= -1.0:
            raise RuntimeError("Portfolio net return reached -100% or less")
        rows.append({
            "elapsed_seconds": float(elapsed[ordinal]),
            "gross_return": float(gross_return),
            "cost": float(cost),
            "net_return": float(net_return),
            "turnover": float(turnover),
            "w_eth": float(target_eth),
            "w_btc": float(target_btc),
            "held_w_eth": float(previous_eth),
            "held_w_btc": float(previous_btc),
        })
        previous_eth, previous_btc = target_eth, target_btc

    return pd.DataFrame(rows, index=index)


def recovery_periods(backtest: pd.DataFrame, variant: str, cost_bps: float) -> list[dict]:
    """Identify every drawdown episode from a running NAV high to recovery or sample end."""
    returns = backtest["net_return"].to_numpy(dtype=float)
    index = backtest.index
    nav = 1.0
    peak_nav = 1.0
    peak_time = index[0]
    underwater = False
    trough_nav = 1.0
    trough_time = index[0]
    episodes = []

    for timestamp, value in zip(index, returns):
        nav *= 1.0 + float(value)
        if nav >= peak_nav:
            if underwater:
                duration = (timestamp - peak_time).total_seconds() / SECONDS_PER_DAY
                episodes.append({
                    "variant": variant,
                    "cost_bps_per_leg": cost_bps,
                    "peak_time": peak_time.isoformat(),
                    "trough_time": trough_time.isoformat(),
                    "recovery_time": timestamp.isoformat(),
                    "recovery_days": duration,
                    "recovered": True,
                })
            peak_nav = nav
            peak_time = timestamp
            underwater = False
            trough_nav = nav
            trough_time = timestamp
        else:
            if not underwater:
                underwater = True
                trough_nav = nav
                trough_time = timestamp
            elif nav < trough_nav:
                trough_nav = nav
                trough_time = timestamp

    if underwater:
        duration = (index[-1] - peak_time).total_seconds() / SECONDS_PER_DAY
        episodes.append({
            "variant": variant,
            "cost_bps_per_leg": cost_bps,
            "peak_time": peak_time.isoformat(),
            "trough_time": trough_time.isoformat(),
            "recovery_time": None,
            "recovery_days": duration,
            "recovered": False,
        })
    return episodes


def portfolio_metrics(
    backtest: pd.DataFrame,
    variant: str,
    cost_bps: float,
    target_asset: pd.Series | None = None,
) -> dict:
    stats = event_time_metrics(backtest)
    duration = backtest["elapsed_seconds"].to_numpy(dtype=float)
    total_duration = float(duration.sum())
    if total_duration <= 0:
        raise ValueError("Portfolio metrics require positive elapsed time")
    held_eth = backtest["held_w_eth"].to_numpy(dtype=float)
    held_btc = backtest["held_w_btc"].to_numpy(dtype=float)
    episodes = recovery_periods(backtest, variant, cost_bps)
    recovered_days = [float(item["recovery_days"]) for item in episodes]
    rotations = 0
    if target_asset is not None:
        changes = target_asset.ne(target_asset.shift(1))
        rotations = int(
            (changes & target_asset.notna() & target_asset.shift(1).notna()).sum()
        )
    return {
        "variant": variant,
        "cost_bps_per_leg": float(cost_bps),
        "total_return": float(stats["total_return"]),
        "CAGR": float(stats["CAGR"]),
        "annualized_volatility": float(stats["annualized_volatility"]),
        "Sharpe": float(stats["continuous_time_sharpe"]),
        "max_drawdown": float(stats["max_drawdown"]),
        "Calmar": float(stats["Calmar"]),
        "turnover_per_year": float(stats["turnover_per_year"]),
        "total_turnover": float(backtest["turnover"].sum()),
        "total_transaction_cost": float(backtest["cost"].sum()),
        "time_in_ETH_pct": float(np.sum(held_eth * duration) / total_duration),
        "time_in_BTC_pct": float(np.sum(held_btc * duration) / total_duration),
        "rotation_count": rotations,
        "max_recovery_days": max(recovered_days, default=0.0),
        "recovery_episode_count": len(episodes),
        "unrecovered_episode_count": sum(not item["recovered"] for item in episodes),
        "observations": int(stats["observations"]),
        "elapsed_days": float(stats["elapsed_days"]),
    }


def paired_excess_cagr_bootstrap(
    strategy: pd.DataFrame,
    benchmark: pd.DataFrame,
    block_days: float,
    replications: int = BOOTSTRAP_REPLICATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Paired moving-block bootstrap of strategy-minus-BTC net CAGR.

    Blocks are contiguous in observed UTC time, sampled with probability
    proportional to the first interval's elapsed duration. Strategy and BTC
    always use identical sampled blocks. The zero-duration initial entry cost
    is compounded into the first positive-duration interval before resampling.
    """
    if not strategy.index.equals(benchmark.index):
        raise ValueError("Paired bootstrap inputs must have identical timestamps")
    if block_days <= 0 or replications < 100:
        raise ValueError("Block length must be positive and replications at least 100")

    elapsed = strategy["elapsed_seconds"].to_numpy(dtype=float).copy()
    strategy_returns = strategy["net_return"].to_numpy(dtype=float).copy()
    benchmark_returns = benchmark["net_return"].to_numpy(dtype=float).copy()
    if not (
        np.isfinite(elapsed).all()
        and np.isfinite(strategy_returns).all()
        and np.isfinite(benchmark_returns).all()
    ):
        raise ValueError("Bootstrap inputs must be finite")
    if (strategy_returns <= -1.0).any() or (benchmark_returns <= -1.0).any():
        raise ValueError("Bootstrap returns must exceed -100%")
    if len(elapsed) < 3 or elapsed[0] != 0.0 or (elapsed[1:] <= 0).any():
        raise ValueError("Expected one zero-duration initial row followed by positive intervals")

    strategy_returns[1] = (
        (1.0 + strategy_returns[0]) * (1.0 + strategy_returns[1]) - 1.0
    )
    benchmark_returns[1] = (
        (1.0 + benchmark_returns[0]) * (1.0 + benchmark_returns[1]) - 1.0
    )
    elapsed = elapsed[1:]
    strategy_returns = strategy_returns[1:]
    benchmark_returns = benchmark_returns[1:]

    block_seconds = float(block_days) * SECONDS_PER_DAY
    cumulative = np.concatenate(([0.0], np.cumsum(elapsed)))
    row_starts = np.arange(len(elapsed))
    block_ends = np.searchsorted(
        cumulative, cumulative[:-1] + block_seconds, side="left"
    )
    valid_starts = np.flatnonzero(
        (block_ends > row_starts) & (block_ends <= len(elapsed))
    )
    if not len(valid_starts):
        raise ValueError("No complete calendar-time bootstrap block fits the OOS sample")
    probabilities = elapsed[valid_starts] / elapsed[valid_starts].sum()
    target_seconds = float(elapsed.sum())
    rng = np.random.default_rng(seed)
    strategy_log = np.log1p(strategy_returns)
    benchmark_log = np.log1p(benchmark_returns)
    excess_cagrs = np.empty(replications, dtype=float)
    max_blocks = int(math.ceil(target_seconds / block_seconds)) + 2

    for replication in range(replications):
        sampled_strategy_log = 0.0
        sampled_benchmark_log = 0.0
        sampled_seconds = 0.0
        blocks_used = 0
        while sampled_seconds < target_seconds and blocks_used < max_blocks:
            start = int(rng.choice(valid_starts, p=probabilities))
            end = int(block_ends[start])
            if end <= start:
                raise RuntimeError("Bootstrap sampler produced an empty block")
            sampled_strategy_log += float(strategy_log[start:end].sum())
            sampled_benchmark_log += float(benchmark_log[start:end].sum())
            sampled_seconds += float(elapsed[start:end].sum())
            blocks_used += 1
        if sampled_seconds < target_seconds:
            raise RuntimeError("Bootstrap sampler did not cover the target OOS duration")
        years = sampled_seconds / SECONDS_PER_YEAR
        strategy_cagr = math.expm1(sampled_strategy_log / years)
        benchmark_cagr = math.expm1(sampled_benchmark_log / years)
        excess_cagrs[replication] = strategy_cagr - benchmark_cagr

    return {
        "block_days": float(block_days),
        "replications": int(replications),
        "seed": int(seed),
        "confidence_level": 0.95,
        "excess_CAGR_mean": float(np.mean(excess_cagrs)),
        "excess_CAGR_median": float(np.median(excess_cagrs)),
        "excess_CAGR_CI_low": float(np.quantile(excess_cagrs, 0.025)),
        "excess_CAGR_CI_high": float(np.quantile(excess_cagrs, 0.975)),
        "method": "paired moving-block bootstrap; contiguous observed UTC intervals; elapsed-duration-weighted block starts",
    }


def evaluate_decision(
    metrics_frame: pd.DataFrame,
    bootstrap_frame: pd.DataFrame,
) -> dict:
    indexed = metrics_frame.set_index(["cost_bps_per_leg", "variant"])
    strategy_name = "ETH_BTC_momentum_200d"
    btc_name = "BTC_buy_hold"
    baseline_strategy = indexed.loc[(BASELINE_COST_BPS, strategy_name)]
    baseline_btc = indexed.loc[(BASELINE_COST_BPS, btc_name)]
    bootstrap_positive = bool(
        len(bootstrap_frame) == len(BOOTSTRAP_BLOCK_DAYS)
        and (bootstrap_frame["excess_CAGR_CI_low"] > 0.0).all()
    )
    criteria = {
        "baseline_net_CAGR_exceeds_BTC": bool(
            baseline_strategy["CAGR"] > baseline_btc["CAGR"]
        ),
        "baseline_Sharpe_exceeds_BTC": bool(
            baseline_strategy["Sharpe"] > baseline_btc["Sharpe"]
        ),
        "baseline_max_drawdown_no_worse_than_BTC": bool(
            baseline_strategy["max_drawdown"] >= baseline_btc["max_drawdown"]
        ),
        "95pct_bootstrap_lower_bound_positive_for_3_7_14_day_blocks": bootstrap_positive,
    }
    stress_results = {}
    for cost in (15.0, 20.0):
        strategy = indexed.loc[(cost, strategy_name)]
        btc = indexed.loc[(cost, btc_name)]
        stress_pass = bool(
            strategy["total_return"] > 0.0
            and strategy["CAGR"] > btc["CAGR"]
            and strategy["Sharpe"] > btc["Sharpe"]
            and strategy["max_drawdown"] >= btc["max_drawdown"]
        )
        stress_results[str(int(cost))] = {
            "pass": stress_pass,
            "strategy_total_return": float(strategy["total_return"]),
            "strategy_CAGR": float(strategy["CAGR"]),
            "BTC_CAGR": float(btc["CAGR"]),
            "strategy_Sharpe": float(strategy["Sharpe"]),
            "BTC_Sharpe": float(btc["Sharpe"]),
            "strategy_max_drawdown": float(strategy["max_drawdown"]),
            "BTC_max_drawdown": float(btc["max_drawdown"]),
        }
        criteria[f"{int(cost)}bps_cost_case_profitable_and_decision_preserved"] = stress_pass

    failed = [name for name, passed in criteria.items() if not passed]
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": "GO" if not failed else "NO-GO",
        "research_only": True,
        "criteria": criteria,
        "failed_criteria": failed,
        "stress_cases": stress_results,
        "interpretation": (
            "GO is research-only and does not authorize trading."
            if not failed
            else "The frozen strategy failed one or more preregistered promotion criteria; do not tune on this OOS sample."
        ),
    }


def _format_pct(value: float) -> str:
    return "n/a" if not np.isfinite(value) else f"{value * 100:.2f}%"


def _format_num(value: float, digits: int = 3) -> str:
    return "n/a" if not np.isfinite(value) else f"{value:.{digits}f}"


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(
    output_dir: Path,
    metrics_frame: pd.DataFrame,
    bootstrap_frame: pd.DataFrame,
    decision: dict,
    signals: pd.DataFrame,
    hashes: dict[str, str],
    oos_index: pd.DatetimeIndex,
) -> None:
    strategy_rows = metrics_frame[
        metrics_frame["variant"] == "ETH_BTC_momentum_200d"
    ].sort_values("cost_bps_per_leg")
    metric_table = _markdown_table(
        ["Cost bps/leg", "Net total return", "Net CAGR", "Sharpe", "Max drawdown", "Turnover/year", "Time ETH", "Time BTC"],
        [[
            f"{row.cost_bps_per_leg:.0f}",
            _format_pct(row.total_return),
            _format_pct(row.CAGR),
            _format_num(row.Sharpe),
            _format_pct(row.max_drawdown),
            _format_num(row.turnover_per_year, 2),
            _format_pct(row.time_in_ETH_pct),
            _format_pct(row.time_in_BTC_pct),
        ] for row in strategy_rows.itertuples(index=False)],
    )
    benchmark_rows = metrics_frame[
        (metrics_frame["cost_bps_per_leg"] == BASELINE_COST_BPS)
        & metrics_frame["variant"].isin(VARIANTS)
    ]
    benchmark_table = _markdown_table(
        ["Variant", "Net total return", "Net CAGR", "Sharpe", "Max drawdown", "Turnover/year"],
        [[
            row.variant,
            _format_pct(row.total_return),
            _format_pct(row.CAGR),
            _format_num(row.Sharpe),
            _format_pct(row.max_drawdown),
            _format_num(row.turnover_per_year, 2),
        ] for row in benchmark_rows.itertuples(index=False)],
    )
    bootstrap_table = _markdown_table(
        ["Block days", "95% lower excess CAGR", "95% upper excess CAGR", "Replications"],
        [[
            f"{row.block_days:.0f}",
            _format_pct(row.excess_CAGR_CI_low),
            _format_pct(row.excess_CAGR_CI_high),
            str(int(row.replications)),
        ] for row in bootstrap_frame.itertuples(index=False)],
    )
    valid = signals[signals["signal"].notna()]
    delays = valid["execution_delay_minutes"].dropna()
    lines = [
        f"# {EXPERIMENT_ID} — empirical result",
        "",
        f"**Decision: {decision['status']}**",
        "",
        f"- OOS window: {oos_index.min().isoformat()} through {oos_index.max().isoformat()} observed opens.",
        f"- OOS observations: {len(oos_index):,}; elapsed calendar days: {(oos_index[-1] - oos_index[0]).total_seconds() / SECONDS_PER_DAY:,.2f}.",
        f"- Valid daily signals: {len(valid):,}; ETH signals: {int((valid['signal'] == 'ETH').sum()):,}; BTC signals: {int((valid['signal'] == 'BTC').sum()):,}.",
        f"- Mean signal-to-execution delay: {_format_num(float(delays.mean()), 2)} minutes; maximum: {_format_num(float(delays.max()), 2)} minutes.",
        f"- Stale/missing daily closes skipped: {int(signals['ratio'].isna().sum()):,}.",
        "",
        "## Frozen implementation conventions",
        "",
        "- Daily ratio is ETHUSDT close divided by BTCUSDT close. The 200-day SMA uses the current completed daily close and the prior 199 valid daily closes.",
        "- A UTC day's close is its last observed hourly close only when it is no more than one hour stale at midnight. No price is forward-filled or synthesized; a stale day generates no new signal.",
        "- A signal is known at the next UTC midnight and executes at the first observed hourly open at or after that time. A missing 00:00 bar therefore delays execution to the next observed open.",
        "- The portfolio is 100% long ETH when the ratio is above its SMA and 100% long BTC otherwise. No leverage, shorts, funding or venue mixing.",
        "- Costs are all-in bps per one-way leg. ETH-to-BTC rotation pays both the ETH sale and BTC purchase legs.",
        "",
        "## Baseline-cost benchmarks (10 bps per leg)",
        "",
        benchmark_table,
        "",
        "## Strategy cost sensitivity",
        "",
        metric_table,
        "",
        "## Paired block-bootstrap excess CAGR versus BTC",
        "",
        bootstrap_table,
        "",
        "Bootstrap uses paired strategy/BTC returns, identical contiguous UTC-time blocks, block starts weighted by the first interval's elapsed duration, 1,000 replications per block length, 95% percentile intervals and per-block seeds equal to base seed 20261123 plus the block length. The initial zero-duration entry cost is compounded into the first positive-duration return before resampling.",
        "",
        "## GO criteria",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}"
        for name, passed in decision["criteria"].items()
    )
    lines.extend([
        "",
        f"**Failed criteria:** {', '.join(decision['failed_criteria']) if decision['failed_criteria'] else 'none'}.",
        "",
        decision["interpretation"],
        "",
        "## Data provenance",
        "",
        "- Venue/market: Binance Spot only; exact instruments ETHUSDT and BTCUSDT.",
        f"- Requested source window: {START_DATE} through {END_DATE}.",
        f"- Accepted source files: {len(hashes)}; SHA-256 values are in spot_momentum_run_manifest.json.",
        "",
        _markdown_table(
            ["File", "SHA-256"],
            [[path, digest] for path, digest in hashes.items()],
        ),
        "",
        "## Limitations and safety",
        "",
        "- Results use hourly open-to-open returns and actual observed elapsed time. Missing hours remain missing; accepted no-trade intervals are not filled.",
        "- The modeled 5–50 bps costs are scenarios, not measured historical fills or account-specific fee schedules.",
        "- OHLCV opens are not historical order-book executions; market impact, partial fills, outages and tax are not modeled.",
        "- The study is Spot-only and does not resolve the separate Binance USDⓈ-M funding-aware study, which remains INCONCLUSIVE.",
        "- A GO is research-only. No live orders, capital deployment or strategy promotion are authorized.",
        "",
    ])
    (output_dir / "spot_momentum_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_research(
    data_dir: Path = Path("data"),
    output_dir: Path = Path("reports/generated/spot-momentum"),
    start: str = START_DATE,
    end: str = END_DATE,
    skip_download: bool = False,
) -> dict:
    if start != START_DATE or end != END_DATE:
        raise ValueError(
            f"This frozen experiment requires exactly {START_DATE} through {END_DATE}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        if skip_download:
            evidence = validate_spot_event_time_evidence(data_dir, start, end)
            if not evidence.get("accepted", False):
                raise ResearchGateError("; ".join(evidence.get("blockers", [])))
        else:
            evidence = prepare_spot_data(start, end, data_dir)

        pair = load_pair("spot", data_dir, start, end, allow_irregular=True)
        if pair.index.min() > OOS_START - pd.Timedelta(days=730):
            raise ResearchGateError("Spot data do not include the full 2020–2021 warm-up")
        if pair.index.max() < OOS_END_EXCLUSIVE - pd.Timedelta(days=1):
            raise ResearchGateError("Spot data do not reach the final preregistered OOS date")
        hashes = spot_source_hashes(data_dir)
        target_schedule, signals = build_target_schedule(pair)
        oos_index = target_schedule.index
        if oos_index.min() < OOS_START or oos_index.max() >= OOS_END_EXCLUSIVE:
            raise ResearchGateError("OOS index escaped the frozen evaluation window")

        schedules = {"ETH_BTC_momentum_200d": target_schedule[["w_eth", "w_btc"]]}
        for variant in VARIANTS[1:]:
            schedules[variant] = benchmark_target_schedule(oos_index, variant)

        all_metrics = []
        baseline_backtests = {}
        baseline_recoveries = []
        equity = pd.DataFrame(index=oos_index)
        for cost in COST_BPS_PER_LEG:
            for variant, schedule in schedules.items():
                backtest = portfolio_backtest(pair.loc[oos_index], schedule, cost)
                target_asset = (
                    target_schedule["target_asset"]
                    if variant == "ETH_BTC_momentum_200d" else None
                )
                all_metrics.append(
                    portfolio_metrics(backtest, variant, cost, target_asset)
                )
                if cost == BASELINE_COST_BPS:
                    baseline_backtests[variant] = backtest
                    baseline_recoveries.extend(recovery_periods(backtest, variant, cost))
                    nav = (1.0 + backtest["net_return"]).cumprod()
                    equity[f"{variant}_NAV"] = nav
                    equity[f"{variant}_drawdown"] = (
                        nav / np.maximum.accumulate(np.r_[1.0, nav.to_numpy()])[1:] - 1.0
                    )

        metrics_frame = pd.DataFrame(all_metrics)
        strategy_base = baseline_backtests["ETH_BTC_momentum_200d"]
        btc_base = baseline_backtests["BTC_buy_hold"]
        bootstrap_rows = [
            paired_excess_cagr_bootstrap(
                strategy_base,
                btc_base,
                block_days,
                replications=BOOTSTRAP_REPLICATIONS,
                seed=BOOTSTRAP_SEED + int(block_days),
            )
            for block_days in BOOTSTRAP_BLOCK_DAYS
        ]
        bootstrap_frame = pd.DataFrame(bootstrap_rows)
        decision = evaluate_decision(metrics_frame, bootstrap_frame)

        signals.to_csv(output_dir / "spot_momentum_signal_audit.csv", index=False)
        metrics_frame.to_csv(output_dir / "spot_momentum_metrics.csv", index=False)
        bootstrap_frame.to_csv(output_dir / "spot_momentum_bootstrap.csv", index=False)
        equity.to_csv(output_dir / "spot_momentum_equity_curve.csv", index_label="timestamp")
        pd.DataFrame(baseline_recoveries).to_csv(
            output_dir / "spot_momentum_recovery_periods.csv", index=False
        )
        returns_output = pd.DataFrame(index=oos_index)
        returns_output["target_asset"] = target_schedule["target_asset"]
        returns_output["signal_date"] = target_schedule["signal_date"]
        for variant, backtest in baseline_backtests.items():
            returns_output[f"{variant}_net_return"] = backtest["net_return"]
            returns_output[f"{variant}_gross_return"] = backtest["gross_return"]
            returns_output[f"{variant}_cost"] = backtest["cost"]
        returns_output.to_csv(
            output_dir / "spot_momentum_oos_returns.csv", index_label="timestamp"
        )

        plt.figure(figsize=(11, 5))
        for variant in ("ETH_BTC_momentum_200d", "BTC_buy_hold", "ETH_buy_hold"):
            plt.plot(equity.index, equity[f"{variant}_NAV"], label=variant)
        plt.title("ETH/BTC 200-day relative-momentum rotation — net NAV")
        plt.xlabel("UTC time")
        plt.ylabel("NAV")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "spot_momentum_equity_curve.png", dpi=150)
        plt.close()

        plt.figure(figsize=(9, 5))
        for variant in ("ETH_BTC_momentum_200d", "BTC_buy_hold"):
            subset = metrics_frame[
                metrics_frame["variant"] == variant
            ].sort_values("cost_bps_per_leg")
            plt.plot(
                subset["cost_bps_per_leg"], subset["CAGR"],
                marker="o", label=variant,
            )
        plt.title("Net CAGR sensitivity to one-way cost per leg")
        plt.xlabel("Cost (bps per leg)")
        plt.ylabel("CAGR")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "spot_momentum_cost_sensitivity.png", dpi=150)
        plt.close()

        run_manifest = {
            "experiment_id": EXPERIMENT_ID,
            "status": "COMPLETE",
            "decision": decision["status"],
            "requested_start": start,
            "requested_end_inclusive": end,
            "oos_start": OOS_START.isoformat(),
            "oos_end_exclusive": OOS_END_EXCLUSIVE.isoformat(),
            "market": "Binance Spot only",
            "symbols": list(SYMBOLS),
            "data_acceptance": evidence,
            "source_file_sha256": hashes,
            "hourly_observations": int(len(pair)),
            "hourly_first_timestamp": pair.index.min().isoformat(),
            "hourly_last_timestamp": pair.index.max().isoformat(),
            "oos_observations": int(len(oos_index)),
            "oos_first_timestamp": oos_index.min().isoformat(),
            "oos_last_timestamp": oos_index.max().isoformat(),
            "daily_signal": {
                "ratio": "ETHUSDT daily UTC close / BTCUSDT daily UTC close",
                "moving_average": "200 valid daily observations, current completed close included",
                "stale_close_policy": "last observed hourly close must be no more than one hour stale at UTC midnight; otherwise no new signal",
                "signal_execution": "first observed hourly open at or after the next UTC midnight",
                "position": "100% ETH if ratio > SMA200, otherwise 100% BTC",
            },
            "cost_bps_per_one_way_leg": list(COST_BPS_PER_LEG),
            "baseline_cost_bps_per_leg": BASELINE_COST_BPS,
            "bootstrap": {
                "method": "paired moving-block bootstrap over contiguous observed UTC intervals",
                "block_days": list(BOOTSTRAP_BLOCK_DAYS),
                "primary_block_days": BOOTSTRAP_PRIMARY_BLOCK_DAYS,
                "replications_per_block": BOOTSTRAP_REPLICATIONS,
                "confidence_level": 0.95,
                "seeds": {
                    str(int(block)): BOOTSTRAP_SEED + int(block)
                    for block in BOOTSTRAP_BLOCK_DAYS
                },
                "paired_benchmark": "BTC_buy_hold",
                "initial_entry_cost": "compounded into first positive-duration interval",
            },
            "decision_criteria": decision,
            "safety": {
                "funding_data_used": False,
                "leverage_used": False,
                "shorts_used": False,
                "other_venues_used": False,
                "live_trading": False,
            },
        }
        (output_dir / "spot_momentum_run_manifest.json").write_text(
            json.dumps(run_manifest, indent=2, default=_json_default),
            encoding="utf-8",
        )
        (output_dir / "spot_momentum_decision.json").write_text(
            json.dumps(decision, indent=2, default=_json_default),
            encoding="utf-8",
        )
        write_report(
            output_dir, metrics_frame, bootstrap_frame, decision,
            signals, hashes, oos_index,
        )
        return run_manifest
    except Exception as exc:
        failure = {
            "experiment_id": EXPERIMENT_ID,
            "status": "INCONCLUSIVE",
            "requested_start": start,
            "requested_end_inclusive": end,
            "error": f"{type(exc).__name__}: {exc}",
            "funding_data_used": False,
            "live_trading": False,
        }
        (output_dir / "spot_momentum_preflight_failure.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("reports/generated/spot-momentum"),
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Use only already-present Spot data; provenance validation remains mandatory",
    )
    args = parser.parse_args()
    result = run_research(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        start=args.start,
        end=args.end,
        skip_download=args.skip_download,
    )
    print(json.dumps(result, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
