"""Elapsed-time accounting for synchronized, irregularly observed UTC observations.

No missing candle is manufactured. Signals and executions occur only at observed
timestamps; returns, funding, borrow and annualization use actual elapsed time.
The production pipeline separately requires provenance-complete no-trade evidence.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

SECONDS_PER_DAY = 86_400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
EVENT_TIME_POLICY_VERSION = "observed-utc-elapsed-v2"


def _validate_datetime_index(index: pd.Index, *, require_hourly: bool = False) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("Observations must use a DatetimeIndex")
    if index.tz is None or str(index.tz) != "UTC":
        raise ValueError("Timestamps must be timezone-aware UTC")
    if index.hasnans:
        raise ValueError("Timestamps cannot be missing")
    if index.has_duplicates:
        raise ValueError("Duplicate observation timestamps are not allowed")
    if not index.is_monotonic_increasing:
        raise ValueError("Observation timestamps must be strictly increasing")
    if require_hourly and not index.equals(index.floor("h")):
        raise ValueError("Hourly observations must be aligned to UTC hour boundaries")


def validate_event_time_frame(frame: pd.DataFrame) -> None:
    """Validate observed pair prices without requiring a complete hourly grid."""
    _validate_datetime_index(frame.index, require_hourly=True)
    required = ("eth_open", "btc_open", "eth_close", "btc_close")
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing event-time price columns: {missing}")
    for column in required:
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f"{column} must contain finite, strictly positive prices")


def elapsed_seconds(index: pd.DatetimeIndex) -> pd.Series:
    """Elapsed wall-clock seconds since the previous observed bar; first is zero."""
    _validate_datetime_index(index, require_hourly=True)
    elapsed = index.to_series().diff().dt.total_seconds().fillna(0.0)
    if (elapsed.iloc[1:] <= 0).any():
        raise ValueError("Elapsed intervals must be strictly positive")
    return elapsed.astype(float)


def add_event_time_features(
    frame: pd.DataFrame,
    lookback_days: int = 30,
    min_observation_fraction: float = 0.95,
    observations_per_day: int = 24,
) -> dict[str, pd.Series]:
    """Create causal, calendar-time rolling spread features on observed bars only."""
    validate_event_time_frame(frame)
    if lookback_days < 1:
        raise ValueError("lookback_days must be positive")
    if not 0 < min_observation_fraction <= 1:
        raise ValueError("min_observation_fraction must be in (0, 1]")
    if observations_per_day < 1:
        raise ValueError("observations_per_day must be positive")
    min_observations = max(
        2, math.ceil(lookback_days * observations_per_day * min_observation_fraction)
    )
    window = f"{lookback_days}D"

    y = np.log(frame["eth_close"].astype(float))
    x = np.log(frame["btc_close"].astype(float))
    fixed_spread = y - x
    fixed_history = fixed_spread.shift(1).rolling(window, min_periods=min_observations)
    fixed_mu = fixed_history.mean()
    fixed_sd = fixed_history.std()
    fixed_z = (fixed_spread - fixed_mu) / fixed_sd.replace(0, np.nan)

    # Estimate only from observations strictly before the current close.
    yp, xp = y.shift(1), x.shift(1)
    y_history = yp.rolling(window, min_periods=min_observations)
    x_history = xp.rolling(window, min_periods=min_observations)
    beta_raw = y_history.cov(xp) / x_history.var().replace(0, np.nan)

    utc_day = pd.Series(frame.index.normalize(), index=frame.index)
    first_observation_of_day = utc_day.ne(utc_day.shift(1))
    beta_candidate = beta_raw.where(first_observation_of_day)
    valid_beta = beta_candidate.gt(0) & beta_candidate.lt(5)
    beta = beta_candidate.where(valid_beta).ffill()
    alpha_candidate = (
        y_history.mean() - beta_raw * x_history.mean()
    ).where(first_observation_of_day & valid_beta)
    alpha = alpha_candidate.ffill()

    dynamic_spread = y - alpha - beta * x
    dynamic_history = dynamic_spread.shift(1).rolling(window, min_periods=min_observations)
    dynamic_mu = dynamic_history.mean()
    dynamic_sd = dynamic_history.std()
    dynamic_z = (dynamic_spread - dynamic_mu) / dynamic_sd.replace(0, np.nan)
    return {
        "fixed_spread": fixed_spread,
        "fixed_z": fixed_z,
        "dynamic_spread": dynamic_spread,
        "dynamic_z": dynamic_z,
        "beta": beta,
        "alpha": alpha,
    }


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Fold boundaries must be timezone-aware")
    return timestamp.tz_convert("UTC")


def make_event_time_positions(
    z: pd.Series,
    beta: pd.Series,
    start: Any,
    end: Any,
    entry: float = 2.0,
    exit_z: float = 0.5,
    stop: float = 4.0,
    max_hold: pd.Timedelta = pd.Timedelta(days=7),
) -> tuple[pd.Series, list[dict[str, Any]]]:
    """Turn close signals into next-observed-open positions and actual hold records.

    A max-hold breach is detected at an observed close and executed at the next
    observed open. Therefore actual hold duration can exceed the threshold by
    the time until the next tradable observation; that delay is recorded rather
    than hidden or converted into a fictitious fill.
    """
    _validate_datetime_index(z.index, require_hourly=True)
    if not z.index.equals(beta.index):
        raise ValueError("z-score and hedge-ratio indexes must match exactly")
    start_ts, end_ts = _utc_timestamp(start), _utc_timestamp(end)
    if start_ts >= end_ts:
        raise ValueError("Fold start must precede fold end")
    if not (entry > exit_z >= 0 and stop > entry):
        raise ValueError("Require entry > exit_z >= 0 and stop > entry")
    max_hold = pd.Timedelta(max_hold)
    if max_hold <= pd.Timedelta(0):
        raise ValueError("max_hold must be positive")

    positions = pd.Series(0.0, index=z.index, dtype=float)
    locations = np.flatnonzero((z.index >= start_ts) & (z.index < end_ts))
    trades: list[dict[str, Any]] = []
    state = 0.0
    held_since: pd.Timestamp | None = None
    active_trade: dict[str, Any] | None = None
    pending_target: float | None = None
    pending_reason: str | None = None

    def close_trade(timestamp: pd.Timestamp, reason: str) -> None:
        nonlocal active_trade, held_since
        if active_trade is not None and held_since is not None:
            seconds = (timestamp - held_since).total_seconds()
            trades.append({
                "direction": active_trade["direction"],
                "entry_time": held_since.isoformat(),
                "exit_time": timestamp.isoformat(),
                "hold_seconds": seconds,
                "hold_days": seconds / SECONDS_PER_DAY,
                "exit_reason": reason,
            })
        active_trade = None
        held_since = None

    for ordinal, location in enumerate(locations):
        timestamp = z.index[location]
        is_last = ordinal == len(locations) - 1

        if is_last:
            # An already-pending exit may execute at this observed open. A
            # pending entry is discarded so a fold cannot open at its boundary.
            if pending_target == 0.0 and state != 0.0:
                close_trade(timestamp, pending_reason or "signal_exit")
                state = 0.0
            if state != 0.0:
                close_trade(timestamp, "fold_end")
                state = 0.0
            positions.iat[location] = 0.0
            break

        changed_at_open = False
        if pending_target is not None:
            target = float(pending_target)
            if target != state:
                if state != 0.0:
                    close_trade(timestamp, pending_reason or "position_change")
                if target != 0.0:
                    held_since = timestamp
                    active_trade = {"direction": target}
                state = target
                changed_at_open = True
            pending_target = None
            pending_reason = None

        positions.iat[location] = state
        if changed_at_open:
            continue

        z_value = float(z.iat[location]) if pd.notna(z.iat[location]) else np.nan
        beta_value = float(beta.iat[location]) if pd.notna(beta.iat[location]) else np.nan
        if not np.isfinite(z_value) or not np.isfinite(beta_value) or beta_value <= 0:
            if state != 0.0:
                pending_target, pending_reason = 0.0, "invalid_signal"
            continue

        if state == 0.0:
            if z_value <= -entry:
                pending_target, pending_reason = 1.0, "entry"
            elif z_value >= entry:
                pending_target, pending_reason = -1.0, "entry"
        else:
            assert held_since is not None
            if abs(z_value) <= exit_z:
                pending_target, pending_reason = 0.0, "mean_reversion_exit"
            elif abs(z_value) >= stop:
                pending_target, pending_reason = 0.0, "stop"
            elif timestamp - held_since >= max_hold:
                pending_target, pending_reason = 0.0, "max_hold"

    return positions, trades


def _funding_rates_at_observations(
    events: pd.Series | None,
    index: pd.DatetimeIndex,
) -> pd.Series:
    aligned = pd.Series(0.0, index=index, dtype=float)
    if events is None or events.empty:
        return aligned
    if not isinstance(events.index, pd.DatetimeIndex):
        raise TypeError("Funding events must use a DatetimeIndex")
    if events.index.tz is None or str(events.index.tz) != "UTC":
        raise ValueError("Funding event timestamps must be timezone-aware UTC")
    if events.index.has_duplicates or not events.index.is_monotonic_increasing:
        raise ValueError("Funding events must be unique and sorted")
    rates = pd.to_numeric(events, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(rates).all():
        raise ValueError("Funding rates must be finite")
    event_ns = events.index.asi8
    observation_ns = index.asi8
    if (event_ns < observation_ns[0]).any():
        raise ValueError("Funding history begins before the observed backtest window")
    target = np.searchsorted(observation_ns, event_ns, side="left")
    if (target >= len(index)).any():
        raise ValueError("Funding event occurs after the last observed timestamp")
    values = np.zeros(len(index), dtype=float)
    np.add.at(values, target, rates)
    return pd.Series(values, index=index)


def event_time_backtest(
    frame: pd.DataFrame,
    position: pd.Series,
    beta: pd.Series,
    fee_bps: float,
    slippage_bps: float,
    spread_bps: float,
    cost_multiplier: float,
    funding_eth: pd.Series | None = None,
    funding_btc: pd.Series | None = None,
    borrow_bps_per_day: float = 0.0,
) -> pd.DataFrame:
    """Account for PnL, costs, funding and borrow over actual observed intervals."""
    validate_event_time_frame(frame)
    index = frame.index
    if not position.index.equals(index) or not beta.index.equals(index):
        raise ValueError("Position and beta indexes must match the observed price index")
    parameters = (fee_bps, slippage_bps, spread_bps, cost_multiplier, borrow_bps_per_day)
    if not all(np.isfinite(value) and value >= 0 for value in parameters):
        raise ValueError("Cost and borrow parameters must be finite and non-negative")
    positions = pd.to_numeric(position, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(positions).all() or not set(np.unique(positions)).issubset({-1.0, 0.0, 1.0}):
        raise ValueError("Positions must be finite values in {-1, 0, 1}")
    if len(positions) and positions[0] != 0.0:
        raise ValueError("The first observed position must be flat; prior holdings are unknown")

    hedge = pd.to_numeric(beta, errors="coerce").astype(float)
    invalid_active_hedge = (position != 0.0) & (~np.isfinite(hedge) | (hedge <= 0))
    if invalid_active_hedge.any():
        raise ValueError("Active positions require a finite positive hedge ratio")
    hedge = hedge.where(np.isfinite(hedge) & (hedge > 0), 1.0).clip(0.01, 5.0)

    gross = 1.0 + hedge
    w_eth = position.astype(float) / gross
    w_btc = -position.astype(float) * hedge / gross
    previous_eth = w_eth.shift(1).fillna(0.0)
    previous_btc = w_btc.shift(1).fillna(0.0)

    eth_return = frame["eth_open"].astype(float).div(frame["eth_open"].shift(1)).sub(1.0).fillna(0.0)
    btc_return = frame["btc_open"].astype(float).div(frame["btc_open"].shift(1)).sub(1.0).fillna(0.0)
    gross_return = previous_eth * eth_return + previous_btc * btc_return
    turnover = (w_eth - previous_eth).abs() + (w_btc - previous_btc).abs()
    one_way_cost = (fee_bps + slippage_bps + spread_bps) / 10_000.0
    costs = turnover * one_way_cost * cost_multiplier

    eth_funding = _funding_rates_at_observations(funding_eth, index)
    btc_funding = _funding_rates_at_observations(funding_btc, index)
    funding_pnl = -(previous_eth * eth_funding + previous_btc * btc_funding)
    short_notional = (-previous_eth).clip(lower=0.0) + (-previous_btc).clip(lower=0.0)
    elapsed = elapsed_seconds(index)
    borrow_cost = short_notional * borrow_bps_per_day / 10_000.0 * elapsed / SECONDS_PER_DAY
    net_return = gross_return - costs + funding_pnl - borrow_cost

    return pd.DataFrame({
        "elapsed_seconds": elapsed,
        "gross_return": gross_return,
        "cost": costs,
        "funding_pnl": funding_pnl,
        "borrow_cost": borrow_cost,
        "net_return": net_return,
        "turnover": turnover,
        "position": position.astype(float),
        "w_eth": w_eth,
        "w_btc": w_btc,
        "held_w_eth": previous_eth,
        "held_w_btc": previous_btc,
    }, index=index)


def event_time_benchmark_backtest(
    frame: pd.DataFrame,
    sample_index: pd.DatetimeIndex,
    initial_weights: tuple[float, float],
    rebalanced: bool,
    fee_bps: float,
    slippage_bps: float,
    spread_bps: float,
    funding_eth: pd.Series | None = None,
    funding_btc: pd.Series | None = None,
    borrow_bps_per_day: float = 0.0,
) -> pd.DataFrame:
    """Backtest a benchmark on observed timestamps with elapsed-time carrying costs."""
    validate_event_time_frame(frame)
    index = pd.DatetimeIndex(sample_index)
    if index.empty:
        return pd.DataFrame(index=index)
    _validate_datetime_index(index, require_hourly=True)
    if index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("Benchmark sample timestamps must be unique and sorted")
    if not index.isin(frame.index).all():
        raise ValueError("Benchmark sample timestamps must be present in the price frame")
    weights = tuple(float(value) for value in initial_weights)
    if len(weights) != 2 or not all(np.isfinite(value) for value in weights):
        raise ValueError("Benchmark weights must be two finite values")
    parameters = (fee_bps, slippage_bps, spread_bps, borrow_bps_per_day)
    if not all(np.isfinite(value) and value >= 0 for value in parameters):
        raise ValueError("Benchmark cost and borrow parameters must be finite and non-negative")

    def events_in_sample(events: pd.Series | None) -> pd.Series | None:
        if events is None or events.empty:
            return None
        if not isinstance(events.index, pd.DatetimeIndex):
            raise TypeError("Funding events must use a DatetimeIndex")
        if events.index.tz is None or str(events.index.tz) != "UTC":
            raise ValueError("Funding event timestamps must be timezone-aware UTC")
        if events.index.has_duplicates or not events.index.is_monotonic_increasing:
            raise ValueError("Funding events must be unique and sorted")
        values = pd.to_numeric(events, errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Funding rates must be finite")
        return events.loc[(events.index >= index[0]) & (events.index <= index[-1])]

    eth_funding = _funding_rates_at_observations(events_in_sample(funding_eth), index)
    btc_funding = _funding_rates_at_observations(events_in_sample(funding_btc), index)
    prices = frame.loc[index]
    eth_returns = prices["eth_open"].astype(float).pct_change().fillna(0.0)
    btc_returns = prices["btc_open"].astype(float).pct_change().fillna(0.0)
    elapsed = elapsed_seconds(index)
    one_way_cost = (fee_bps + slippage_bps + spread_bps) / 10_000.0
    previous_eth = previous_btc = 0.0
    rows = []

    for ordinal, timestamp in enumerate(index):
        gross = funding_pnl = borrow_cost = 0.0
        is_last = ordinal == len(index) - 1
        if ordinal == 0:
            if is_last:
                target_eth = target_btc = 0.0
                turnover = 2.0 * (abs(weights[0]) + abs(weights[1]))
            else:
                target_eth, target_btc = weights
                turnover = abs(target_eth) + abs(target_btc)
        else:
            re = float(eth_returns.loc[timestamp])
            rb = float(btc_returns.loc[timestamp])
            gross = previous_eth * re + previous_btc * rb
            fe = float(eth_funding.loc[timestamp])
            fb = float(btc_funding.loc[timestamp])
            funding_pnl = -(previous_eth * fe + previous_btc * fb)
            short_notional = max(-previous_eth, 0.0) + max(-previous_btc, 0.0)
            borrow_cost = (
                short_notional * borrow_bps_per_day / 10_000.0
                * float(elapsed.loc[timestamp]) / SECONDS_PER_DAY
            )
            pretrade_nav = 1.0 + gross + funding_pnl - borrow_cost
            if pretrade_nav <= 0:
                raise RuntimeError(
                    "Event-time benchmark NAV became non-positive; benchmark is not margin-realistic"
                )
            drift_eth = previous_eth * (1.0 + re) / pretrade_nav
            drift_btc = previous_btc * (1.0 + rb) / pretrade_nav
            if is_last:
                target_eth = target_btc = 0.0
                turnover = abs(drift_eth) + abs(drift_btc)
            elif rebalanced:
                target_eth, target_btc = weights
                turnover = abs(target_eth - drift_eth) + abs(target_btc - drift_btc)
            else:
                target_eth, target_btc = drift_eth, drift_btc
                turnover = 0.0

        cost = turnover * one_way_cost
        net = gross + funding_pnl - borrow_cost - cost
        rows.append({
            "elapsed_seconds": float(elapsed.loc[timestamp]),
            "gross_return": gross,
            "cost": cost,
            "funding_pnl": funding_pnl,
            "borrow_cost": borrow_cost,
            "net_return": net,
            "turnover": turnover,
            "position": 1.0 if target_eth != 0.0 or target_btc != 0.0 else 0.0,
            "w_eth": target_eth,
            "w_btc": target_btc,
            "held_w_eth": previous_eth,
            "held_w_btc": previous_btc,
        })
        previous_eth, previous_btc = target_eth, target_btc

    return pd.DataFrame(rows, index=index)


def event_time_metrics(backtest: pd.DataFrame) -> dict[str, float | int]:
    """Annualize log-return drift and variance by elapsed calendar time.

    Zero-duration entry/exit costs affect compounded return, CAGR, drawdown and
    turnover, but are excluded from elapsed-time volatility estimation.
    """
    required = {"elapsed_seconds", "net_return", "turnover"}
    if not required.issubset(backtest.columns):
        raise ValueError(
            f"Missing event-time metric columns: {sorted(required - set(backtest.columns))}"
        )
    elapsed = pd.to_numeric(backtest["elapsed_seconds"], errors="coerce").to_numpy(dtype=float)
    returns = pd.to_numeric(backtest["net_return"], errors="coerce").to_numpy(dtype=float)
    turnover = pd.to_numeric(backtest["turnover"], errors="coerce").to_numpy(dtype=float)
    if not (
        np.isfinite(elapsed).all()
        and np.isfinite(returns).all()
        and np.isfinite(turnover).all()
    ):
        raise ValueError("Event-time metrics require finite elapsed time, returns and turnover")
    if (elapsed < 0).any():
        raise ValueError("Elapsed durations cannot be negative")
    if (returns <= -1.0).any():
        raise ValueError("Net return at or below -100% is not admissible")

    positive_duration = elapsed > 0
    if not positive_duration.any():
        raise ValueError("At least one positive-duration observed return interval is required")
    dt_years = elapsed[positive_duration] / SECONDS_PER_YEAR
    positive_log_returns = np.log1p(returns[positive_duration])
    all_log_returns = np.log1p(returns)
    total_years = float(dt_years.sum())
    if total_years <= 0:
        raise ValueError("Total elapsed time must be positive")

    annual_log_return = float(all_log_returns.sum() / total_years)
    residuals = positive_log_returns - annual_log_return * dt_years
    variance_rate = float(np.square(residuals).sum() / total_years)
    annualized_volatility = math.sqrt(max(variance_rate, 0.0))
    downside_rate = float(
        np.square(np.minimum(positive_log_returns, 0.0)).sum() / total_years
    )
    downside_volatility = math.sqrt(max(downside_rate, 0.0))

    nav = np.concatenate(([1.0], np.cumprod(1.0 + returns)))
    drawdown = nav / np.maximum.accumulate(nav) - 1.0
    total_return = float(np.expm1(all_log_returns.sum()))
    cagr = float(np.expm1(annual_log_return))
    result: dict[str, float | int] = {
        "observations": int(positive_duration.sum()),
        "elapsed_years": total_years,
        "elapsed_days": float(total_years * 365.25),
        "total_return": total_return,
        "CAGR": cagr,
        "annual_log_return": annual_log_return,
        "annualized_volatility": annualized_volatility,
        "continuous_time_sharpe": (
            float(annual_log_return / annualized_volatility)
            if annualized_volatility > 0 else float("nan")
        ),
        "continuous_time_sortino": (
            float(annual_log_return / downside_volatility)
            if downside_volatility > 0 else float("nan")
        ),
        "max_drawdown": float(drawdown.min()),
        "Calmar": (
            float(cagr / abs(drawdown.min()))
            if drawdown.min() < 0 else float("nan")
        ),
        "turnover_per_year": float(turnover.sum() / total_years),
    }
    if {"held_w_eth", "held_w_btc"}.issubset(backtest.columns):
        eth_weights = pd.to_numeric(backtest["held_w_eth"], errors="coerce").to_numpy(dtype=float)
        btc_weights = pd.to_numeric(backtest["held_w_btc"], errors="coerce").to_numpy(dtype=float)
        gross_exposure = np.abs(eth_weights) + np.abs(btc_weights)
        if np.isfinite(gross_exposure).all():
            duration = elapsed[positive_duration]
            result["avg_gross_exposure"] = float(
                np.sum(gross_exposure[positive_duration] * duration) / duration.sum()
            )
            result["time_in_market"] = float(
                duration[gross_exposure[positive_duration] > 0].sum() / duration.sum()
            )
    return result
