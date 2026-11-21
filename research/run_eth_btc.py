#!/usr/bin/env python3
"""Reproducible ETH/BTC relative-value research pipeline.

Downloads Binance monthly 1h spot and USD-M perpetual klines, plus perpetual
funding history; performs pre-specified walk-forward tests; writes CSV outputs
and plots. No live trading or order placement is implemented.

Important: default fees/slippage/spread are scenario assumptions, not a claim
about any account's actual exchange tier. Supply actual costs before relying on
net results. Spot short-leg results are theoretical unless borrow is feasible
and borrow costs are supplied separately.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import io
import json
import math
import time
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller, coint, kpss, zivot_andrews
from statsmodels.tsa.vector_ar.vecm import coint_johansen

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote", "ignore",
]
SYMBOLS = ("ETHUSDT", "BTCUSDT")


def month_starts(start: str, end: str) -> Iterable[pd.Timestamp]:
    s = pd.Timestamp(start).replace(day=1)
    e = pd.Timestamp(end).replace(day=1)
    for p in pd.date_range(s, e, freq="MS"):
        yield p


def last_completed_month_end() -> str:
    now = pd.Timestamp.now(tz="UTC")
    first = now.normalize().replace(day=1)
    return (first - pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _download_archive(url: str, cache_file: Path, session: requests.Session) -> tuple[bytes, bool]:
    if cache_file.exists():
        payload = cache_file.read_bytes()
    else:
        response = session.get(url, timeout=90)
        if response.status_code == 404:
            raise FileNotFoundError(url)
        response.raise_for_status()
        payload = response.content
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(payload)

    # Binance publishes SHA-256 sidecars for archive integrity. If a sidecar is
    # unavailable, retain the file but record that it was not checksum-verified.
    verified = False
    try:
        check = session.get(url + ".CHECKSUM", timeout=30)
        if check.ok:
            expected = check.text.strip().split()[0].lower()
            actual = hashlib.sha256(payload).hexdigest().lower()
            if expected != actual:
                raise ValueError(f"SHA-256 mismatch for {url}")
            verified = True
    except requests.RequestException:
        pass
    return payload, verified


def download_klines(market: str, symbol: str, start: str, end: str, data_dir: Path) -> Path:
    """Download monthly Binance 1h kline archives and consolidate to CSV."""
    session = requests.Session()
    base = "spot" if market == "spot" else "futures/um"
    frames = []
    archive_manifest = []
    for month in month_starts(start, end):
        tag = month.strftime("%Y-%m")
        filename = f"{symbol}-1h-{tag}.zip"
        url = f"https://data.binance.vision/data/{base}/monthly/klines/{symbol}/1h/{filename}"
        cache = data_dir / "cache" / market / symbol / filename
        try:
            payload, checksum_verified = _download_archive(url, cache, session)
        except FileNotFoundError:
            print(f"WARN missing archive: {url}")
            continue
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV in {url}")
            raw = pd.read_csv(archive.open(csv_names[0]), header=None)
        if raw.empty:
            continue
        raw = raw.iloc[:, :len(COLUMNS)]
        raw.columns = COLUMNS[:raw.shape[1]]
        raw["open_time"] = pd.to_numeric(raw["open_time"], errors="coerce")
        unit = "us" if raw["open_time"].median() > 10**14 else "ms"
        raw["timestamp"] = pd.to_datetime(raw["open_time"], unit=unit, utc=True)
        archive_manifest.append({"month": tag, "url": url, "archive_sha256": hashlib.sha256(payload).hexdigest(),
                                 "checksum_verified": checksum_verified, "rows": int(len(raw)), "timestamp_unit": unit})
        for col in ("open", "high", "low", "close", "volume", "quote_volume"):
            if col in raw:
                raw[col] = pd.to_numeric(raw[col], errors="coerce")
        frames.append(raw[["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]])
        time.sleep(0.03)
    if not frames:
        raise RuntimeError(f"No {market} data downloaded for {symbol}; check date range and symbol history")
    out = pd.concat(frames, ignore_index=True).drop_duplicates("timestamp").sort_values("timestamp")
    out_path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    manifest_path = data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
    manifest_path.write_text(json.dumps({"market": market, "symbol": symbol, "archives": archive_manifest,
                                         "consolidated_csv_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest()}, indent=2))
    return out_path


def download_funding(symbol: str, start: str, end: str, data_dir: Path) -> Path:
    """Paginate Binance USD-M funding history (max 1,000 events per request)."""
    session = requests.Session()
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    end_ms = int(end_ts.timestamp() * 1000) - 1
    rows = []
    while start_ms <= end_ms:
        response = session.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000},
            timeout=45,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected funding API response for {symbol}: {batch}")
        rows.extend(batch)
        last = int(batch[-1]["fundingTime"])
        if len(batch) < 1000 or last < start_ms:
            break
        start_ms = last + 1
        time.sleep(0.05)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError(f"No funding history returned for {symbol}")
    frame["timestamp"] = pd.to_datetime(frame["fundingTime"], unit="ms", utc=True)
    frame["fundingRate"] = pd.to_numeric(frame["fundingRate"], errors="coerce")
    out = data_dir / "raw" / f"um_{symbol}_funding.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    clean = frame[["timestamp", "fundingRate"]].drop_duplicates("timestamp").sort_values("timestamp")
    clean.to_csv(out, index=False)
    (data_dir / "raw" / f"um_{symbol}_funding_manifest.json").write_text(json.dumps({
        "symbol": symbol, "endpoint": "https://fapi.binance.com/fapi/v1/fundingRate",
        "rows": int(len(clean)), "start": str(clean["timestamp"].min()), "end": str(clean["timestamp"].max()),
        "csv_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }, indent=2))
    return out


def load_pair(market: str, data_dir: Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    parts = []
    for symbol, prefix in (("ETHUSDT", "eth"), ("BTCUSDT", "btc")):
        path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run the downloader first")
        x = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp").sort_index()
        parts.append(x[["open", "high", "low", "close", "volume"]].rename(columns=lambda c: f"{prefix}_{c}"))
    out = pd.concat(parts, axis=1, join="inner").dropna().sort_index()
    if start is not None:
        out = out.loc[out.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        out = out.loc[out.index < end_exclusive]
    if out.empty:
        raise RuntimeError(f"No synchronized ETH/BTC {market} observations")
    return out


def load_funding(symbol: str, index: pd.DatetimeIndex, data_dir: Path) -> pd.Series:
    path = data_dir / "raw" / f"um_{symbol}_funding.csv"
    if not path.exists():
        return pd.Series(0.0, index=index)
    f = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")["fundingRate"]
    return f.reindex(index).fillna(0.0)


def add_features(df: pd.DataFrame, lookback: int) -> dict[str, pd.Series]:
    y = np.log(df["eth_close"])
    x = np.log(df["btc_close"])
    # Fixed 1:1 log-price spread.
    fixed_spread = y - x
    fixed_mu = fixed_spread.shift(1).rolling(lookback, min_periods=lookback).mean()
    fixed_sd = fixed_spread.shift(1).rolling(lookback, min_periods=lookback).std()
    fixed_z = (fixed_spread - fixed_mu) / fixed_sd.replace(0, np.nan)

    # Expanding-in-time rolling OLS, shifted one bar. Rebalance beta only at
    # 00:00 UTC using information available through the prior hour.
    yp, xp = y.shift(1), x.shift(1)
    cov = yp.rolling(lookback, min_periods=lookback).cov(xp)
    var = xp.rolling(lookback, min_periods=lookback).var()
    beta_hourly = cov / var.replace(0, np.nan)
    alpha_hourly = yp.rolling(lookback, min_periods=lookback).mean() - beta_hourly * xp.rolling(lookback, min_periods=lookback).mean()
    midnight = df.index.hour == 0
    beta = beta_hourly.where(midnight).ffill().where(lambda s: (s > 0) & (s < 5))
    alpha = alpha_hourly.where(midnight).ffill()
    dynamic_spread = y - alpha - beta * x
    dyn_mu = dynamic_spread.shift(1).rolling(lookback, min_periods=lookback).mean()
    dyn_sd = dynamic_spread.shift(1).rolling(lookback, min_periods=lookback).std()
    dynamic_z = (dynamic_spread - dyn_mu) / dyn_sd.replace(0, np.nan)
    return {
        "fixed_spread": fixed_spread, "fixed_z": fixed_z,
        "dynamic_spread": dynamic_spread, "dynamic_z": dynamic_z,
        "beta": beta, "alpha": alpha,
    }


def make_position(z: pd.Series, beta: pd.Series, start: pd.Timestamp, end: pd.Timestamp,
                  entry: float, exit_z: float, stop: float, max_hold: int) -> pd.Series:
    pos = pd.Series(0.0, index=z.index)
    state, age = 0.0, 0
    mask = (z.index >= start) & (z.index < end)
    locs = np.flatnonzero(mask)
    for i in locs:
        value = z.iat[i]
        if not np.isfinite(value) or not np.isfinite(beta.iat[i]):
            state, age = 0.0, 0
        elif state == 0:
            if value <= -entry:
                state, age = 1.0, 0
            elif value >= entry:
                state, age = -1.0, 0
        else:
            age += 1
            if abs(value) <= exit_z or abs(value) >= stop or age >= max_hold:
                state, age = 0.0, 0
        pos.iat[i] = state
    # Liquidate at the end of each OOS fold; exit costs are included in-fold.
    if len(locs):
        pos.iat[locs[-1]] = 0.0
    return pos


def backtest(df: pd.DataFrame, position: pd.Series, beta: pd.Series,
             fee_bps: float, slippage_bps: float, spread_bps: float,
             cost_multiplier: float, funding_eth: pd.Series | None = None,
             funding_btc: pd.Series | None = None, borrow_bps_per_day: float = 0.0,
             periods_per_day: int = 24) -> pd.DataFrame:
    b = beta.fillna(1.0).clip(lower=0.01, upper=5.0)
    gross = 1.0 + b
    w_eth = position / gross
    w_btc = -position * b / gross
    prev_eth = w_eth.shift(1).fillna(0.0)
    prev_btc = w_btc.shift(1).fillna(0.0)
    # Signal is generated from the prior completed bar close; open-to-open PnL
    # therefore starts only after the next-bar-open execution.
    r_eth = df["eth_open"].pct_change().fillna(0.0)
    r_btc = df["btc_open"].pct_change().fillna(0.0)
    gross_pnl = prev_eth * r_eth + prev_btc * r_btc
    turnover = (w_eth - prev_eth).abs() + (w_btc - prev_btc).abs()
    one_way_cost = (fee_bps + slippage_bps + spread_bps) / 10000.0
    costs = turnover * one_way_cost * cost_multiplier
    fe = funding_eth if funding_eth is not None else pd.Series(0.0, index=df.index)
    fb = funding_btc if funding_btc is not None else pd.Series(0.0, index=df.index)
    funding_pnl = -(prev_eth * fe + prev_btc * fb)
    short_notional = (-prev_eth).clip(lower=0.0) + (-prev_btc).clip(lower=0.0)
    borrow_cost = short_notional * borrow_bps_per_day / 10000.0 / periods_per_day
    return pd.DataFrame({
        "gross_return": gross_pnl,
        "cost": costs,
        "funding_pnl": funding_pnl,
        "borrow_cost": borrow_cost,
        "net_return": gross_pnl - costs + funding_pnl - borrow_cost,
        "turnover": turnover,
        "position": position,
        "w_eth": w_eth,
        "w_btc": w_btc,
    }, index=df.index)


def block_bootstrap_sharpe_ci(r: pd.Series, periods_per_year: int, reps: int = 150) -> tuple[float, float]:
    """Approximate 95% CI using a moving-block bootstrap (7-day blocks)."""
    values = r.dropna().to_numpy(dtype=float)
    if len(values) < 100:
        return np.nan, np.nan
    block = 168 if periods_per_year == 8760 else 7
    rng = np.random.default_rng(20261121)
    estimates = []
    n = len(values)
    blocks_needed = int(math.ceil(n / block))
    starts_max = max(1, n - block + 1)
    for _ in range(reps):
        starts = rng.integers(0, starts_max, size=blocks_needed)
        sample = np.concatenate([values[i:i+block] for i in starts])[:n]
        sd = sample.std(ddof=1)
        if sd > 0:
            estimates.append(sample.mean() / sd * math.sqrt(periods_per_year))
    if not estimates:
        return np.nan, np.nan
    return tuple(np.quantile(estimates, [0.025, 0.975]).astype(float))


def metrics(bt: pd.DataFrame, periods_per_year: int) -> dict:
    r = bt["net_return"].replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < 2:
        return {k: np.nan for k in ("CAGR", "volatility", "Sharpe", "Sortino", "max_drawdown", "Calmar", "turnover_per_year", "avg_gross_exposure", "time_in_market", "trade_count", "win_rate", "profit_factor", "avg_holding_period", "tail_1pct")}
    equity = (1.0 + r).cumprod()
    years = len(r) / periods_per_year
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 and years > 0 else np.nan
    vol = float(r.std(ddof=1) * math.sqrt(periods_per_year))
    sharpe = float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year)) if r.std(ddof=1) > 0 else np.nan
    sharpe_ci_low, sharpe_ci_high = block_bootstrap_sharpe_ci(r, periods_per_year)
    downside = r[r < 0].std(ddof=1)
    sortino = float(r.mean() / downside * math.sqrt(periods_per_year)) if pd.notna(downside) and downside > 0 else np.nan
    dd = equity / equity.cummax() - 1.0
    mdd = float(dd.min())
    held = bt.loc[r.index, "position"].shift(1).fillna(0.0)
    entries = (held.ne(0) & held.shift(1).fillna(0).eq(0))
    trade_id = entries.cumsum()
    active = held.ne(0)
    trade_returns = (1.0 + r[active]).groupby(trade_id[active]).prod() - 1.0
    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else (np.inf if len(wins) else np.nan)
    holding = active.groupby(trade_id[active]).sum()
    return {
        "CAGR": cagr,
        "volatility": vol,
        "Sharpe": sharpe,
        "Sharpe_CI_low": sharpe_ci_low,
        "Sharpe_CI_high": sharpe_ci_high,
        "Sortino": sortino,
        "max_drawdown": mdd,
        "Calmar": cagr / abs(mdd) if mdd < 0 and pd.notna(cagr) else np.nan,
        "turnover_per_year": float(bt.loc[r.index, "turnover"].sum() / years),
        "avg_gross_exposure": float((bt.loc[r.index, "w_eth"].abs() + bt.loc[r.index, "w_btc"].abs()).mean()),
        "time_in_market": float(active.mean()),
        "trade_count": int(len(trade_returns)),
        "win_rate": float((trade_returns > 0).mean()) if len(trade_returns) else np.nan,
        "profit_factor": pf,
        "avg_holding_period": float(holding.mean()) if len(holding) else np.nan,
        "tail_1pct": float(r.quantile(0.01)),
    }


def diagnostics(train: pd.DataFrame, features: dict[str, pd.Series], label: str) -> dict:
    y = np.log(train["eth_close"]).dropna()
    x = np.log(train["btc_close"]).reindex(y.index)
    out = {"variant": label, "train_start": str(train.index.min()), "train_end": str(train.index.max()), "n": int(len(train))}
    try:
        stat, pvalue, _ = coint(y, x)
        out.update({"engle_granger_stat": float(stat), "engle_granger_p": float(pvalue)})
    except Exception as exc:
        out["engle_granger_error"] = str(exc)
    beta = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
    residual = y - (y.mean() - beta * x.mean()) - beta * x
    try:
        out["residual_adf_p"] = float(adfuller(residual.dropna(), autolag="AIC")[1])
    except Exception as exc:
        out["residual_adf_error"] = str(exc)
    try:
        out["residual_kpss_p"] = float(kpss(residual.dropna(), regression="c", nlags="auto")[1])
    except Exception as exc:
        out["residual_kpss_error"] = str(exc)
    try:
        joh = coint_johansen(pd.concat([y, x], axis=1).dropna(), det_order=0, k_ar_diff=1)
        out["johansen_trace_r0"] = float(joh.lr1[0])
        out["johansen_crit95_r0"] = float(joh.cvt[0, 1])
    except Exception as exc:
        out["johansen_error"] = str(exc)
    lagged = residual.shift(1).dropna()
    delta = residual.diff().dropna().reindex(lagged.index)
    if len(lagged) > 10:
        slope = float(np.polyfit(lagged, delta, 1)[0])
        out["ar1_slope"] = slope
        out["half_life_bars"] = float(-math.log(2) / slope) if slope < 0 else np.inf
    else:
        out["half_life_bars"] = np.nan
    try:
        out["zivot_andrews_p"] = float(zivot_andrews(residual.dropna(), maxlag=12, regression="c", autolag="AIC")[1])
    except Exception as exc:
        out["zivot_andrews_error"] = str(exc)
    rolling_p = []
    for end in pd.date_range(train.index.min() + pd.Timedelta(days=180), train.index.max(), freq="90D"):
        sub = train.loc[(train.index > end - pd.Timedelta(days=180)) & (train.index <= end)]
        if len(sub) >= 120:
            try:
                rolling_p.append(float(coint(np.log(sub["eth_close"]), np.log(sub["btc_close"]))[1]))
            except Exception:
                pass
    out["rolling_180d_coint_windows"] = len(rolling_p)
    out["rolling_180d_coint_share_p_lt_0_05"] = float(np.mean(np.array(rolling_p) < 0.05)) if rolling_p else np.nan
    return out


def regime_labels(df: pd.DataFrame, train: pd.DataFrame, periods_per_day: int) -> pd.Series:
    rel = df["eth_close"].pct_change() - df["btc_close"].pct_change()
    rv = rel.rolling(30 * periods_per_day, min_periods=30 * periods_per_day).std().shift(1)
    tr = train.index
    q1, q2 = rv.reindex(tr).quantile([1/3, 2/3]).values
    return pd.Series(np.where(rv <= q1, "low", np.where(rv <= q2, "mid", "high")), index=df.index).where(rv.notna())


def walk_forward(df: pd.DataFrame, market: str, interval: str, out_dir: Path,
                 fee_bps: float, slippage_bps: float, spread_bps: float,
                 funding_eth: pd.Series | None = None, funding_btc: pd.Series | None = None,
                 borrow_bps_per_day: float = 0.0) -> None:
    hourly = interval == "1h"
    ppd = 24 if hourly else 1
    ppy = 8760 if hourly else 365
    lookback = 30 * ppd
    train_days, test_days = 730, 90
    max_hold = 7 * ppd
    feats = add_features(df, lookback)
    fold_rows, regime_rows, diag_rows, cost_rows, oos_rows = [], [], [], [], []
    first_test = df.index.min() + pd.Timedelta(days=train_days)
    for fold_no, test_start in enumerate(pd.date_range(first_test, df.index.max(), freq=f"{test_days}D"), 1):
        test_end = min(test_start + pd.Timedelta(days=test_days), df.index.max() + pd.Timedelta(hours=1 if hourly else 24))
        train_start = test_start - pd.Timedelta(days=train_days)
        train = df.loc[(df.index >= train_start) & (df.index < test_start)]
        test_mask = (df.index >= test_start) & (df.index < test_end)
        if len(train) < int(train_days * ppd * 0.95) or not test_mask.any():
            continue
        regimes = regime_labels(df, train, ppd)
        for variant, zkey, bkey in (("fixed_1x1", "fixed_z", None), ("rolling_hedge", "dynamic_z", "beta")):
            beta = pd.Series(1.0, index=df.index) if bkey is None else feats[bkey]
            signal_pos = make_position(feats[zkey], beta, test_start, test_end, 2.0, 0.5, 4.0, max_hold)
            # Signal at bar close t is executed at bar t+1 open. Close the
            # position at the final OOS open so the exit cost is in the fold.
            pos = signal_pos.shift(1).fillna(0.0)
            test_locs = np.flatnonzero(test_mask)
            if len(test_locs):
                pos.iat[test_locs[-1]] = 0.0
            diag_rows.append({"market": market, "interval": interval, "fold": fold_no, **diagnostics(train, feats, variant)})
            for mult in (1.0, 1.5, 2.0):
                bt = backtest(df, pos, beta, fee_bps, slippage_bps, spread_bps, mult, funding_eth, funding_btc, borrow_bps_per_day, ppd)
                sample = bt.loc[test_mask].copy()
                row = {"market": market, "interval": interval, "fold": fold_no, "test_start": str(test_start), "test_end": str(test_end), "variant": variant, "cost_multiplier": mult, **metrics(sample, ppy)}
                fold_rows.append(row)
                cost_rows.append({k: row[k] for k in ("market", "interval", "fold", "variant", "cost_multiplier", "CAGR", "Sharpe", "Sortino", "max_drawdown", "Calmar", "turnover_per_year")})
                labels = regimes.loc[test_mask]
                for regime in ("low", "mid", "high"):
                    idx = labels.index[labels == regime]
                    if len(idx):
                        sub = sample.loc[idx]
                        regime_rows.append({"market": market, "interval": interval, "fold": fold_no, "variant": variant, "cost_multiplier": mult, "regime": regime, "n": len(sub), **metrics(sub, ppy)})
                if mult == 1.0:
                    for t in sample.index:
                        oos_rows.append({"timestamp": t, "market": market, "interval": interval, "fold": fold_no, "variant": variant, "net_return": sample.at[t, "net_return"], "gross_return": sample.at[t, "gross_return"], "cost": sample.at[t, "cost"], "funding_pnl": sample.at[t, "funding_pnl"], "borrow_cost": sample.at[t, "borrow_cost"], "position": sample.at[t, "position"], "beta": beta.at[t] if pd.notna(beta.at[t]) else np.nan, "regime": regimes.at[t]})
        # Same-capital, 1x benchmarks on the same test window. Apply entry
        # and exit costs; on USD-M data also deduct observed funding cash flows.
        r_e = df["eth_open"].pct_change().fillna(0.0).loc[test_mask]
        r_b = df["btc_open"].pct_change().fillna(0.0).loc[test_mask]
        fe = funding_eth.loc[test_mask] if funding_eth is not None else pd.Series(0.0, index=r_e.index)
        fb = funding_btc.loc[test_mask] if funding_btc is not None else pd.Series(0.0, index=r_e.index)
        bench_cost = (fee_bps + slippage_bps + spread_bps) / 10000.0
        bench_defs = [
            ("BTC_buy_hold", r_b - fb, 1.0, 0.0),
            ("ETH_buy_hold", r_e - fe, 0.0, 1.0),
            ("50_50_ETH_BTC", 0.5*r_e + 0.5*r_b - 0.5*(fe + fb), 0.5, 0.5),
            ("long_ETH_short_BTC", 0.5*r_e - 0.5*r_b - 0.5*fe + 0.5*fb, 0.5, -0.5),
            ("no_trade", r_e*0.0, 0.0, 0.0),
        ]
        for name, returns, w_eth_bench, w_btc_bench in bench_defs:
            returns = returns.copy()
            entry_turnover = abs(w_eth_bench) + abs(w_btc_bench)
            if len(returns) and entry_turnover:
                # The benchmark enters at the first test open; do not credit
                # the pre-entry open-to-open return on that first timestamp.
                returns.iloc[0] = -bench_cost * entry_turnover
            if name == "long_ETH_short_BTC" and market == "spot" and borrow_bps_per_day:
                returns.iloc[1:] -= 0.5 * borrow_bps_per_day / 10000.0 / ppd
            bench = pd.DataFrame({
                "net_return": returns,
                "turnover": 0.0,
                "position": 1.0 if entry_turnover else 0.0,
                "w_eth": w_eth_bench,
                "w_btc": w_btc_bench,
            })
            if len(bench) and entry_turnover:
                returns.iloc[-1] -= bench_cost * entry_turnover
                bench["net_return"] = returns
                bench.iloc[0, bench.columns.get_loc("turnover")] += entry_turnover
                bench.iloc[-1, bench.columns.get_loc("turnover")] += entry_turnover
                bench.iloc[-1, bench.columns.get_loc("position")] = 0.0
                bench.iloc[-1, bench.columns.get_loc("w_eth")] = 0.0
                bench.iloc[-1, bench.columns.get_loc("w_btc")] = 0.0
            fold_rows.append({"market": market, "interval": interval, "fold": fold_no, "test_start": str(test_start), "test_end": str(test_end), "variant": name, "cost_multiplier": 1.0, **metrics(bench, ppy)})

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(out_dir / f"{market}_{interval}_oos_summary.csv", index=False)
    regime_df = pd.DataFrame(regime_rows)
    cost_df = pd.DataFrame(cost_rows)
    regime_df.to_csv(out_dir / f"{market}_{interval}_regime_summary.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(out_dir / f"{market}_{interval}_diagnostics.csv", index=False)
    cost_df.to_csv(out_dir / f"{market}_{interval}_cost_sensitivity.csv", index=False)
    if not regime_df.empty:
        base = regime_df[regime_df["cost_multiplier"] == 1.0]
        if not base.empty:
            pivot = base.pivot_table(index="regime", columns="variant", values="Sharpe", aggfunc="mean")
            plt.figure(figsize=(9, 4)); pivot.plot(kind="bar", ax=plt.gca())
            plt.title("Mean out-of-sample Sharpe by volatility regime"); plt.tight_layout()
            plt.savefig(out_dir / f"{market}_{interval}_volatility_regimes.png", dpi=150); plt.close()
    if not cost_df.empty:
        strat = cost_df[cost_df["variant"].isin(["fixed_1x1", "rolling_hedge"])]
        if not strat.empty:
            pivot = strat.pivot_table(index="cost_multiplier", columns="variant", values="CAGR", aggfunc="mean")
            plt.figure(figsize=(8, 4)); pivot.plot(marker="o", ax=plt.gca())
            plt.title("Mean out-of-sample CAGR versus transaction-cost multiplier"); plt.tight_layout()
            plt.savefig(out_dir / f"{market}_{interval}_cost_sensitivity.png", dpi=150); plt.close()
    oos = pd.DataFrame(oos_rows)
    if not oos.empty:
        oos.to_csv(out_dir / f"{market}_{interval}_oos_returns.csv", index=False)
        make_plots(df, feats, oos, out_dir, market, interval)
        stress_rows = []
        for variant in ("fixed_1x1", "rolling_hedge"):
            candidates = oos[(oos["variant"] == variant) & (oos["position"] != 0)].sort_values("timestamp")
            if candidates.empty:
                continue
            last = candidates.iloc[-1]
            beta_last = float(last["beta"]) if pd.notna(last["beta"]) else 1.0
            pos_last = float(last["position"])
            we = pos_last / (1.0 + abs(beta_last))
            wb = -pos_last * beta_last / (1.0 + abs(beta_last))
            scenarios = {
                "ETH -20%, BTC -10%": (-0.20, -0.10, 0.0),
                "ETH -35%, BTC -15%": (-0.35, -0.15, 0.0),
                "ETH +20%, BTC -10%": (0.20, -0.10, 0.0),
                "ETH -10%, BTC +10%": (-0.10, 0.10, 0.0),
                "ETH -5%, BTC -5%": (-0.05, -0.05, 0.0),
                "three funding events at +10bp each": (0.0, 0.0, 3 * 0.001),
            }
            for scenario, (re, rb, common_funding) in scenarios.items():
                pnl = we * re + wb * rb - (we + wb) * common_funding
                stress_rows.append({"market": market, "interval": interval, "variant": variant,
                                    "reference_timestamp": str(last["timestamp"]), "position": pos_last,
                                    "beta": beta_last, "scenario": scenario, "one_shot_pnl_on_nav": pnl,
                                    "assumption": "Illustrative instantaneous shock; not a forecast"})
        if stress_rows:
            pd.DataFrame(stress_rows).to_csv(out_dir / f"{market}_{interval}_stress_scenarios.csv", index=False)


def make_plots(df: pd.DataFrame, feats: dict, oos: pd.DataFrame, out_dir: Path, market: str, interval: str) -> None:
    plt.figure(figsize=(11, 5))
    (df["eth_close"] / df["eth_close"].iloc[0]).plot(label="ETH normalized")
    (df["btc_close"] / df["btc_close"].iloc[0]).plot(label="BTC normalized")
    plt.legend(); plt.title(f"ETH and BTC normalized prices — {market} {interval}"); plt.tight_layout()
    plt.savefig(out_dir / f"{market}_{interval}_prices.png", dpi=150); plt.close()

    plt.figure(figsize=(11, 4))
    feats["fixed_z"].plot(label="Fixed 1:1 spread z-score", alpha=0.8)
    feats["dynamic_z"].plot(label="Rolling-hedge spread z-score", alpha=0.8)
    plt.axhline(2, linestyle="--"); plt.axhline(-2, linestyle="--"); plt.axhline(0, linewidth=0.7)
    plt.legend(); plt.title("Spread z-scores (rolling estimates use past data only)"); plt.tight_layout()
    plt.savefig(out_dir / f"{market}_{interval}_spread_zscore.png", dpi=150); plt.close()

    plt.figure(figsize=(11, 4)); feats["beta"].plot(); plt.title("Daily-updated rolling hedge ratio"); plt.tight_layout()
    plt.savefig(out_dir / f"{market}_{interval}_hedge_ratio.png", dpi=150); plt.close()

    pivot = oos.pivot_table(index="timestamp", columns="variant", values="net_return", aggfunc="first").fillna(0.0)
    equity = (1.0 + pivot).cumprod()
    plt.figure(figsize=(11, 5)); equity.plot(ax=plt.gca()); plt.title("Out-of-sample equity (1x cost case)"); plt.tight_layout()
    plt.savefig(out_dir / f"{market}_{interval}_oos_equity.png", dpi=150); plt.close()
    dd = equity / equity.cummax() - 1.0
    plt.figure(figsize=(11, 4)); dd.plot(ax=plt.gca()); plt.title("Out-of-sample drawdowns"); plt.tight_layout()
    plt.savefig(out_dir / f"{market}_{interval}_drawdowns.png", dpi=150); plt.close()


def self_test() -> None:
    rng = np.random.default_rng(7)
    idx = pd.date_range("2022-01-01", periods=24*100, freq="h", tz="UTC")
    btc = 20000 * np.exp(np.cumsum(rng.normal(0, 0.002, len(idx))))
    rel = np.zeros(len(idx))
    noise = rng.normal(0, 0.004, len(idx))
    for i in range(1, len(idx)):
        rel[i] = 0.97 * rel[i-1] + noise[i]
    eth = btc * np.exp(np.log(0.07) + rel)
    frame = pd.DataFrame({"eth_open": eth, "btc_open": btc, "eth_close": eth, "btc_close": btc}, index=idx)
    f = add_features(frame, 24*10)
    p = make_position(f["fixed_z"], pd.Series(1.0, index=idx), idx[24*30], idx[-1], 2, 0.5, 4, 24*7)
    bt = backtest(frame, p, pd.Series(1.0, index=idx), 10, 2, 1, 1.0)
    assert np.isfinite(bt["net_return"]).all()
    assert set(p.dropna().unique()).issubset({-1.0, 0.0, 1.0})
    print("SELF-TEST PASS: feature generation, position state machine, costs and PnL are finite.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default=last_completed_month_end())
    parser.add_argument("--market", choices=("spot", "um", "both"), default="both")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/generated"))
    parser.add_argument("--spot-fee-bps", type=float, default=10.0)
    parser.add_argument("--um-fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--spread-bps", type=float, default=1.0)
    parser.add_argument("--spot-borrow-bps-per-day", type=float, default=0.0, help="Optional short-borrow charge for theoretical spot backtests")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    markets = ("spot", "um") if args.market == "both" else (args.market,)
    for market in markets:
        for symbol in SYMBOLS:
            download_klines(market, symbol, args.start, args.end, args.data_dir)
        pair = load_pair(market, args.data_dir, args.start, args.end)
        if market == "um":
            for symbol in SYMBOLS:
                download_funding(symbol, args.start, args.end, args.data_dir)
            f_eth = load_funding("ETHUSDT", pair.index, args.data_dir)
            f_btc = load_funding("BTCUSDT", pair.index, args.data_dir)
            fee = args.um_fee_bps
        else:
            f_eth = f_btc = None
            fee = args.spot_fee_bps
        quality = {
            "market": market, "rows": int(len(pair)), "start": str(pair.index.min()), "end": str(pair.index.max()),
            "expected_frequency": "1h", "gap_count": int((pair.index.to_series().diff().dropna() != pd.Timedelta(hours=1)).sum()),
            "max_gap": str(pair.index.to_series().diff().max()),
            "symbols": {},
        }
        for symbol in SYMBOLS:
            manifest_file = args.data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
            quality["symbols"][symbol] = json.loads(manifest_file.read_text()) if manifest_file.exists() else {"manifest_missing": True}
        if market == "um":
            quality["funding"] = {}
            for symbol in SYMBOLS:
                funding_manifest = args.data_dir / "raw" / f"um_{symbol}_funding_manifest.json"
                quality["funding"][symbol] = json.loads(funding_manifest.read_text()) if funding_manifest.exists() else {"manifest_missing": True}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / f"{market}_data_quality.json").write_text(json.dumps(quality, indent=2))
        borrow = args.spot_borrow_bps_per_day if market == "spot" else 0.0
        walk_forward(pair, market, "1h", args.output_dir, fee, args.slippage_bps, args.spread_bps, f_eth, f_btc, borrow)
        daily = pair[["eth_open", "btc_open", "eth_close", "btc_close"]].resample("1D").agg({"eth_open": "first", "btc_open": "first", "eth_close": "last", "btc_close": "last"}).dropna()
        walk_forward(daily, market, "1d", args.output_dir, fee, args.slippage_bps, args.spread_bps, None, None, borrow)
    manifest = {
        "start": args.start, "end": args.end, "markets": markets,
        "spot_fee_bps_per_leg_per_side": args.spot_fee_bps,
        "um_fee_bps_per_leg_per_side": args.um_fee_bps,
        "slippage_bps_per_leg_per_side": args.slippage_bps,
        "spread_bps_per_leg_per_side": args.spread_bps,
        "spot_borrow_bps_per_day": args.spot_borrow_bps_per_day,
        "entry_z": 2.0, "exit_z": 0.5, "stop_z": 4.0,
        "hourly_lookback_bars": 720, "daily_lookback_bars": 30,
        "train_days": 730, "test_days": 90, "max_hold_days": 7,
        "annualization": {"1h": 8760, "1d": 365},
        "note": "Default trading costs are scenario assumptions; verify actual account fees and borrow costs.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Research outputs written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
