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
BOOTSTRAP_REPS = 150  # Exploratory CI; quantile precision is limited at this count.


def month_starts(start: str, end: str) -> Iterable[pd.Timestamp]:
    s = pd.Timestamp(start).replace(day=1)
    e = pd.Timestamp(end).replace(day=1)
    for p in pd.date_range(s, e, freq="MS"):
        yield p


def last_completed_month_end() -> str:
    now = pd.Timestamp.now(tz="UTC")
    first = now.normalize().replace(day=1)
    return (first - pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def request_with_retry(session: requests.Session, url: str, timeout: int = 60,
                      max_attempts: int = 4, **kwargs) -> requests.Response:
    """GET with bounded retries for transient network, 429 and 5xx failures."""
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(max_attempts):
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            if response.status_code in retryable_statuses:
                if attempt == max_attempts - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else float(2 ** attempt)
                except (TypeError, ValueError):
                    delay = float(2 ** attempt)
                time.sleep(min(max(delay, 0.0), 30.0))
                continue
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in retryable_statuses or attempt == max_attempts - 1:
                raise
            time.sleep(min(float(2 ** attempt), 30.0))
        except requests.RequestException:
            if attempt == max_attempts - 1:
                raise
            time.sleep(min(float(2 ** attempt), 30.0))
    raise RuntimeError(f"Request failed after {max_attempts} attempts: {url}")


def hourly_quality(index: pd.DatetimeIndex, start: str, end: str) -> dict:
    """Measure hourly completeness before any ETH/BTC inner join."""
    start_ts = pd.Timestamp(start, tz="UTC")
    end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    observed_all = pd.DatetimeIndex(index)
    in_sample = observed_all[(observed_all >= start_ts) & (observed_all < end_exclusive)]
    duplicate_count = int(in_sample.duplicated().sum())
    observed = in_sample.drop_duplicates().sort_values()
    expected = pd.date_range(start_ts, end_exclusive - pd.Timedelta(hours=1), freq="h")
    missing = expected.difference(observed)
    gaps = observed.to_series().diff().dropna()
    max_gap = gaps.max() if len(gaps) else pd.NaT
    return {
        "requested_start": str(start_ts),
        "requested_end_inclusive": str(end_exclusive - pd.Timedelta(hours=1)),
        "observed_start": str(observed.min()) if len(observed) else None,
        "observed_end": str(observed.max()) if len(observed) else None,
        "rows": int(len(in_sample)),
        "unique_rows": int(len(observed)),
        "duplicate_timestamps": duplicate_count,
        "expected_hourly_bars": int(len(expected)),
        "missing_hourly_bars": int(len(missing)),
        "missing_hour_samples": [str(x) for x in missing[:20]],
        "max_gap": str(max_gap) if pd.notna(max_gap) else None,
        "longest_gap_hours": float(max_gap.total_seconds() / 3600) if pd.notna(max_gap) else None,
        "complete": bool(len(missing) == 0 and duplicate_count == 0 and len(observed) == len(expected)),
    }


def _download_archive(url: str, cache_file: Path, session: requests.Session) -> tuple[bytes, bool, str | None]:
    if cache_file.exists():
        payload = cache_file.read_bytes()
    else:
        try:
            response = request_with_retry(session, url, timeout=90)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise FileNotFoundError(url) from exc
            raise
        payload = response.content
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(payload)

    verified = False
    checksum_error = None
    try:
        check = request_with_retry(session, url + ".CHECKSUM", timeout=30)
        tokens = check.text.strip().split()
        if not tokens:
            raise ValueError(f"Empty checksum sidecar for {url}")
        expected = tokens[0].lower()
        actual = hashlib.sha256(payload).hexdigest().lower()
        if expected != actual:
            raise ValueError(f"SHA-256 mismatch for {url}: expected {expected}, got {actual}")
        verified = True
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            checksum_error = "checksum sidecar not published (HTTP 404)"
        else:
            raise
    except requests.RequestException as exc:
        checksum_error = f"checksum sidecar unavailable after retries: {exc}"
    return payload, verified, checksum_error


def download_klines(market: str, symbol: str, start: str, end: str, data_dir: Path) -> Path:
    """Download monthly Binance 1h archives; never silently accept missing months."""
    session = requests.Session()
    base = "spot" if market == "spot" else "futures/um"
    frames = []
    archive_manifest = []
    missing_months = []
    for month in month_starts(start, end):
        tag = month.strftime("%Y-%m")
        filename = f"{symbol}-1h-{tag}.zip"
        url = f"https://data.binance.vision/data/{base}/monthly/klines/{symbol}/1h/{filename}"
        cache = data_dir / "cache" / market / symbol / filename
        try:
            payload, checksum_verified, checksum_error = _download_archive(url, cache, session)
        except FileNotFoundError:
            archive_manifest.append({"month": tag, "url": url, "status": "missing_http_404"})
            missing_months.append(tag)
            continue
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV in {url}")
            raw = pd.read_csv(archive.open(csv_names[0]), header=None)
        if raw.empty:
            archive_manifest.append({"month": tag, "url": url, "status": "empty_archive"})
            missing_months.append(tag)
            continue
        if raw.shape[1] < 6:
            raise ValueError(f"Unexpected kline CSV schema in {url}: {raw.shape[1]} columns")
        raw = raw.iloc[:, :len(COLUMNS)]
        raw.columns = COLUMNS[:raw.shape[1]]
        raw["open_time"] = pd.to_numeric(raw["open_time"], errors="coerce")
        if raw["open_time"].isna().any():
            raise ValueError(f"Invalid open_time values in {url}")
        unit = "us" if raw["open_time"].median() > 10**14 else "ms"
        raw["timestamp"] = pd.to_datetime(raw["open_time"], unit=unit, utc=True)
        archive_manifest.append({
            "month": tag, "url": url, "status": "downloaded",
            "archive_sha256": hashlib.sha256(payload).hexdigest(),
            "checksum_verified": checksum_verified, "checksum_error": checksum_error,
            "rows": int(len(raw)), "timestamp_unit": unit,
        })
        for col in ("open", "high", "low", "close", "volume", "quote_volume"):
            if col in raw:
                raw[col] = pd.to_numeric(raw[col], errors="coerce")
        frames.append(raw[["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]])
        time.sleep(0.03)

    if not frames:
        manifest = {
            "market": market, "symbol": symbol, "requested_start": start,
            "requested_end_inclusive": end, "archives": archive_manifest,
            "missing_archive_months": missing_months, "data_quality": None,
        }
        out_path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
        manifest_path = data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        raise RuntimeError(f"No {market} data downloaded for {symbol}; see {manifest_path}")

    combined = pd.concat(frames, ignore_index=True).sort_values("timestamp")
    quality = hourly_quality(pd.DatetimeIndex(combined["timestamp"]), start, end)
    duplicate_count = quality["duplicate_timestamps"]
    out = combined.drop_duplicates("timestamp", keep="first").sort_values("timestamp")
    out_path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    manifest_path = data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
    manifest = {
        "market": market, "symbol": symbol, "requested_start": start,
        "requested_end_inclusive": end, "archives": archive_manifest,
        "missing_archive_months": missing_months,
        "data_quality": quality,
        "consolidated_csv_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if missing_months or duplicate_count or not quality["complete"]:
        raise RuntimeError(
            f"Incomplete {market} {symbol} data: missing archives={missing_months}, "
            f"duplicates={duplicate_count}, missing hours={quality['missing_hourly_bars']}; "
            f"inspect {manifest_path}"
        )
    return out_path


def funding_quality(timestamps: pd.DatetimeIndex, start_ts: pd.Timestamp,
                    end_exclusive: pd.Timestamp) -> dict:
    stamps = pd.DatetimeIndex(timestamps).sort_values()
    duplicate_count = int(stamps.duplicated().sum())
    unique = stamps.drop_duplicates()
    gaps = unique.to_series().diff().dropna()
    median_gap = gaps.median() if len(gaps) else pd.NaT
    max_gap = gaps.max() if len(gaps) else pd.NaT
    # Do not let a missing-event outlier inflate the estimated normal cadence.
    # Binance funding intervals can vary, but a >24h gap is already a material
    # coverage warning unless shorter observed intervals establish a wider
    # legitimate cadence. Estimate cadence only from intervals <=24h.
    normal_gaps = gaps[gaps <= pd.Timedelta(hours=24)]
    cadence_reference_gap = normal_gaps.median() if len(normal_gaps) else pd.NaT
    max_allowed = (
        max(pd.Timedelta(hours=24), cadence_reference_gap * 3)
        if pd.notna(cadence_reference_gap)
        else pd.Timedelta(hours=24)
    )
    start_ok = bool(len(unique) and unique.min() <= start_ts + pd.Timedelta(hours=24))
    end_ok = bool(len(unique) and unique.max() >= end_exclusive - pd.Timedelta(hours=24))
    max_gap_ok = bool(pd.isna(max_gap) or max_gap <= max_allowed)
    return {
        "rows": int(len(stamps)),
        "duplicate_timestamps": duplicate_count,
        "start": str(unique.min()) if len(unique) else None,
        "end": str(unique.max()) if len(unique) else None,
        "median_event_gap_hours": float(median_gap.total_seconds() / 3600) if pd.notna(median_gap) else None,
        "cadence_reference_gap_hours": float(cadence_reference_gap.total_seconds() / 3600) if pd.notna(cadence_reference_gap) else None,
        "max_event_gap_hours": float(max_gap.total_seconds() / 3600) if pd.notna(max_gap) else None,
        "max_allowed_gap_hours": float(max_allowed.total_seconds() / 3600),
        "start_coverage_ok": start_ok,
        "end_coverage_ok": end_ok,
        "max_gap_ok": max_gap_ok,
        "complete": bool(len(unique) > 0 and duplicate_count == 0 and start_ok and end_ok and max_gap_ok),
    }


def download_funding(symbol: str, start: str, end: str, data_dir: Path) -> Path:
    """Paginate funding events and fail on duplicate, incomplete or gapped history."""
    session = requests.Session()
    start_ts = pd.Timestamp(start, tz="UTC")
    end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    cursor_ms = int(start_ts.timestamp() * 1000)
    end_ms = int(end_exclusive.timestamp() * 1000) - 1
    rows = []
    page_count = 0
    last_seen = None
    while cursor_ms <= end_ms:
        response = request_with_retry(
            session, "https://fapi.binance.com/fapi/v1/fundingRate", timeout=45,
            params={"symbol": symbol, "startTime": cursor_ms, "endTime": end_ms, "limit": 1000},
        )
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected funding API response for {symbol}: {batch}")
        if not batch:
            break
        times = [int(item["fundingTime"]) for item in batch]
        if times != sorted(times) or len(times) != len(set(times)):
            raise RuntimeError(f"Funding page is not strictly chronological for {symbol}")
        if times[0] < cursor_ms or (last_seen is not None and times[0] <= last_seen):
            raise RuntimeError(f"Funding pagination repeated or regressed for {symbol}")
        if times[-1] > end_ms:
            raise RuntimeError(f"Funding API returned an event outside requested bounds for {symbol}")
        rows.extend(batch)
        page_count += 1
        last_seen = times[-1]
        if len(batch) < 1000 or last_seen >= end_ms:
            break
        cursor_ms = last_seen + 1
        time.sleep(0.05)

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError(f"No funding history returned for {symbol}")
    frame["timestamp"] = pd.to_datetime(frame["fundingTime"], unit="ms", utc=True)
    frame["fundingRate"] = pd.to_numeric(frame["fundingRate"], errors="coerce")
    if frame["fundingRate"].isna().any() or not np.isfinite(frame["fundingRate"]).all():
        raise RuntimeError(f"Invalid funding rates returned for {symbol}")
    clean = frame[["timestamp", "fundingRate"]].sort_values("timestamp")
    quality = funding_quality(pd.DatetimeIndex(clean["timestamp"]), start_ts, end_exclusive)
    out = data_dir / "raw" / f"um_{symbol}_funding.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out, index=False)
    manifest = {
        "symbol": symbol, "endpoint": "https://fapi.binance.com/fapi/v1/fundingRate",
        "requested_start": str(start_ts), "requested_end_exclusive": str(end_exclusive),
        "pages": page_count, "data_quality": quality,
        "csv_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    manifest_path = data_dir / "raw" / f"um_{symbol}_funding_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if not quality["complete"]:
        raise RuntimeError(f"Incomplete funding history for {symbol}; inspect {manifest_path}")
    return out


def align_funding_events(events: pd.Series, index: pd.DatetimeIndex, symbol: str = "unknown") -> tuple[pd.Series, dict]:
    """Map each settlement to the first hourly open at/after its event timestamp."""
    if events.empty:
        raise RuntimeError(f"Missing funding events for {symbol}")
    events = events.sort_index()
    if events.index.has_duplicates:
        raise RuntimeError(f"Duplicate funding timestamps for {symbol}")
    if events.isna().any() or not np.isfinite(events.to_numpy(dtype=float)).all():
        raise RuntimeError(f"Invalid funding rates for {symbol}")
    index = pd.DatetimeIndex(index).sort_values()
    if index.empty or index.has_duplicates:
        raise RuntimeError("Price index must be non-empty, unique and sorted")
    quality = funding_quality(
        pd.DatetimeIndex(events.index), index[0], index[-1] + pd.Timedelta(hours=1)
    )
    if not quality["complete"]:
        raise RuntimeError(f"Incomplete funding coverage for {symbol}: {quality}")
    target_positions = index.searchsorted(events.index, side="left")
    if (target_positions >= len(index)).any():
        raise RuntimeError(f"Funding event for {symbol} falls after the final price bar")
    lags = index[target_positions] - events.index
    if (lags > pd.Timedelta(hours=1)).any():
        raise RuntimeError(f"Funding event for {symbol} cannot be aligned within one hour")
    aligned = pd.Series(0.0, index=index)
    np.add.at(aligned.values, target_positions, events.to_numpy(dtype=float))
    quality["off_grid_events"] = int((lags != pd.Timedelta(0)).sum())
    quality["max_alignment_lag_minutes"] = float(lags.max().total_seconds() / 60) if len(lags) else 0.0
    return aligned, quality


def load_pair(market: str, data_dir: Path, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    parts = []
    for symbol, prefix in (("ETHUSDT", "eth"), ("BTCUSDT", "btc")):
        path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run the downloader first")
        x = pd.read_csv(path, parse_dates=["timestamp"])
        x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True)
        if x["timestamp"].duplicated().any():
            raise RuntimeError(f"Duplicate timestamps remain in {path}")
        x = x.set_index("timestamp").sort_index()
        parts.append(x[["open", "high", "low", "close", "volume"]].rename(columns=lambda c: f"{prefix}_{c}"))
    out = pd.concat(parts, axis=1, join="inner").dropna().sort_index()
    if start is not None:
        out = out.loc[out.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        out = out.loc[out.index < end_exclusive]
    if out.empty:
        raise RuntimeError(f"No synchronized ETH/BTC {market} observations")
    expected = pd.date_range(
        pd.Timestamp(start, tz="UTC") if start is not None else out.index.min(),
        (pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(hours=1))
        if end is not None else out.index.max(),
        freq="h",
    )
    missing = expected.difference(out.index)
    if len(missing):
        raise RuntimeError(
            f"Synchronized ETH/BTC {market} series has {len(missing)} missing hourly bars; "
            f"first missing timestamps: {[str(x) for x in missing[:10]]}"
        )
    return out


def load_funding(symbol: str, index: pd.DatetimeIndex, data_dir: Path) -> tuple[pd.Series, dict]:
    path = data_dir / "raw" / f"um_{symbol}_funding.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing funding history for {symbol}: {path}")
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    if frame.empty or not {"timestamp", "fundingRate"}.issubset(frame.columns):
        raise RuntimeError(f"Invalid or empty funding file for {symbol}: {path}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["fundingRate"] = pd.to_numeric(frame["fundingRate"], errors="coerce")
    events = frame.set_index("timestamp")["fundingRate"].sort_index()
    return align_funding_events(events, index, symbol)


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


def shift_signal_to_next_open(signal_position: pd.Series) -> pd.Series:
    """Convert a completed-close signal into exposure established at the next open."""
    return signal_position.shift(1).fillna(0.0)


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
        "held_w_eth": prev_eth,
        "held_w_btc": prev_btc,
    }, index=df.index)


def block_bootstrap_sharpe_ci(r: pd.Series, periods_per_year: int, reps: int = BOOTSTRAP_REPS) -> tuple[float, float]:
    """Exploratory percentile 95% CI; 150 replications have limited quantile precision.""""
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


def downside_deviation(returns: pd.Series, minimum_acceptable_return: float = 0.0) -> float:
    """Root-mean-square downside relative to the MAR, using all observations."""
    values = returns.dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return np.nan
    downside = np.minimum(values - minimum_acceptable_return, 0.0)
    return float(np.sqrt(np.mean(np.square(downside))))



def metrics(bt: pd.DataFrame, periods_per_year: int) -> dict:
    r = bt["net_return"].replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < 2:
        empty = {k: np.nan for k in ("CAGR", "volatility", "Sharpe", "Sortino", "max_drawdown", "Calmar", "turnover_per_year", "avg_gross_exposure", "time_in_market", "trade_count", "win_rate", "profit_factor", "avg_holding_period", "tail_1pct")}
        empty["Sharpe_CI_replications"] = BOOTSTRAP_REPS
        empty["Sharpe_CI_interpretation"] = "exploratory; limited percentile precision"
        return empty
    equity = (1.0 + r).cumprod()
    years = len(r) / periods_per_year
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 and years > 0 else np.nan
    vol = float(r.std(ddof=1) * math.sqrt(periods_per_year))
    sharpe = float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year)) if r.std(ddof=1) > 0 else np.nan
    sharpe_ci_low, sharpe_ci_high = block_bootstrap_sharpe_ci(r, periods_per_year)
    downside = downside_deviation(r, minimum_acceptable_return=0.0)
    sortino = float(r.mean() / downside * math.sqrt(periods_per_year)) if pd.notna(downside) and downside > 0 else np.nan
    equity_with_initial = np.concatenate(([1.0], equity.to_numpy(dtype=float)))
    running_peak = np.maximum.accumulate(equity_with_initial)
    dd = equity_with_initial / running_peak - 1.0
    mdd = float(dd.min())
    executed_position = bt.loc[r.index, "position"].fillna(0.0)
    held = executed_position.shift(1).fillna(0.0)
    entries = executed_position.ne(0) & held.eq(0)
    trade_id = entries.cumsum()
    active = held.ne(0)
    # Include the entry-cost bar and exit-cost bar in each trade's net PnL.
    trade_active = executed_position.ne(0) | held.ne(0)
    trade_returns = (1.0 + r[trade_active]).groupby(trade_id[trade_active]).prod() - 1.0
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
        "Sharpe_CI_replications": BOOTSTRAP_REPS,
        "Sharpe_CI_interpretation": "exploratory; limited percentile precision",
        "Sortino": sortino,
        "max_drawdown": mdd,
        "Calmar": cagr / abs(mdd) if mdd < 0 and pd.notna(cagr) else np.nan,
        "turnover_per_year": float(bt.loc[r.index, "turnover"].sum() / years),
        "avg_gross_exposure": float((bt.loc[r.index, "held_w_eth"].abs() + bt.loc[r.index, "held_w_btc"].abs()).mean()),
        "time_in_market": float(active.mean()),
        "trade_count": int(len(trade_returns)),
        "win_rate": float((trade_returns > 0).mean()) if len(trade_returns) else np.nan,
        "profit_factor": pf,
        "avg_holding_period": float(holding.mean()) if len(holding) else np.nan,
        "tail_1pct": float(r.quantile(0.01)),
    }


def diagnostics(train: pd.DataFrame) -> dict:
    """Shared static log-price relationship diagnostics for each training fold."""
    y = np.log(train["eth_close"]).dropna()
    x = np.log(train["btc_close"]).reindex(y.index)
    out = {
        "diagnostic_scope": "shared_static_ols_relationship",
        "train_start": str(train.index.min()),
        "train_end": str(train.index.max()),
        "n": int(len(train)),
    }
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
        gamma = float(np.polyfit(lagged, delta, 1)[0])
        phi = 1.0 + gamma
        out["ar1_gamma"] = gamma
        out["ar1_phi"] = phi
        out["half_life_ou_approx_bars"] = float(-math.log(2) / gamma) if gamma < 0 else np.nan
        out["half_life_exact_ar1_bars"] = (
            float(-math.log(2) / math.log(phi)) if 0 < phi < 1 else np.nan
        )
        out["half_life_exact_valid"] = bool(0 < phi < 1)
    else:
        out.update({
            "ar1_gamma": np.nan, "ar1_phi": np.nan,
            "half_life_ou_approx_bars": np.nan,
            "half_life_exact_ar1_bars": np.nan, "half_life_exact_valid": False,
        })
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


def benchmark_backtest(df: pd.DataFrame, sample_index: pd.DatetimeIndex,
                      initial_weights: tuple[float, float], rebalanced: bool,
                      fee_bps: float, slippage_bps: float, spread_bps: float,
                      funding_eth: pd.Series | None = None,
                      funding_btc: pd.Series | None = None,
                      borrow_bps_per_day: float = 0.0,
                      periods_per_day: int = 24) -> pd.DataFrame:
    """Backtest a benchmark with explicit entry, drift/rebalance and exit turnover."""
    sample_index = pd.DatetimeIndex(sample_index)
    if sample_index.empty:
        return pd.DataFrame(index=sample_index)
    one_way_cost = (fee_bps + slippage_bps + spread_bps) / 10000.0
    r_eth_all = df["eth_open"].pct_change().fillna(0.0)
    r_btc_all = df["btc_open"].pct_change().fillna(0.0)
    fe_all = funding_eth if funding_eth is not None else pd.Series(0.0, index=df.index)
    fb_all = funding_btc if funding_btc is not None else pd.Series(0.0, index=df.index)
    prev_eth = prev_btc = 0.0
    rows = []
    for i, timestamp in enumerate(sample_index):
        gross = funding_pnl = borrow_cost = 0.0
        is_last = i == len(sample_index) - 1
        if i == 0:
            drift_eth = drift_btc = 0.0
            if is_last:
                target_eth = target_btc = 0.0
                turnover = 2.0 * (abs(initial_weights[0]) + abs(initial_weights[1]))
            else:
                target_eth, target_btc = initial_weights
                turnover = abs(target_eth) + abs(target_btc)
        else:
            re = float(r_eth_all.loc[timestamp])
            rb = float(r_btc_all.loc[timestamp])
            gross = prev_eth * re + prev_btc * rb
            fe = float(fe_all.loc[timestamp]) if timestamp in fe_all.index else 0.0
            fb = float(fb_all.loc[timestamp]) if timestamp in fb_all.index else 0.0
            funding_pnl = -(prev_eth * fe + prev_btc * fb)
            short_notional = max(-prev_eth, 0.0) + max(-prev_btc, 0.0)
            borrow_cost = short_notional * borrow_bps_per_day / 10000.0 / periods_per_day
            pretrade_nav = 1.0 + gross + funding_pnl - borrow_cost
            if pretrade_nav <= 0:
                raise RuntimeError("Benchmark NAV became non-positive; benchmark is not margin-realistic")
            drift_eth = prev_eth * (1.0 + re) / pretrade_nav
            drift_btc = prev_btc * (1.0 + rb) / pretrade_nav
            if is_last:
                target_eth = target_btc = 0.0
                turnover = abs(drift_eth) + abs(drift_btc)
            elif rebalanced:
                target_eth, target_btc = initial_weights
                turnover = abs(target_eth - drift_eth) + abs(target_btc - drift_btc)
            else:
                target_eth, target_btc = drift_eth, drift_btc
                turnover = 0.0
        cost = turnover * one_way_cost
        net = gross + funding_pnl - borrow_cost - cost
        rows.append({
            "gross_return": gross, "cost": cost, "funding_pnl": funding_pnl,
            "borrow_cost": borrow_cost, "net_return": net, "turnover": turnover,
            "position": 1.0 if (target_eth != 0.0 or target_btc != 0.0) else 0.0,
            "w_eth": target_eth, "w_btc": target_btc,
        })
        prev_eth, prev_btc = target_eth, target_btc
    return pd.DataFrame(rows, index=sample_index)


def stress_scenarios_for_market(market: str) -> dict[str, tuple[float, float, float, str]]:
    """Return price shocks for both markets and a funding shock only for USDⓈ-M."""
    scenarios = {
        "ETH -20%, BTC -10%": (-0.20, -0.10, 0.0, "Illustrative instantaneous price shock; not a forecast."),
        "ETH -35%, BTC -15%": (-0.35, -0.15, 0.0, "Illustrative instantaneous price shock; not a forecast."),
        "ETH +20%, BTC -10%": (0.20, -0.10, 0.0, "Illustrative instantaneous price shock; not a forecast."),
        "ETH -10%, BTC +10%": (-0.10, 0.10, 0.0, "Illustrative instantaneous price shock; not a forecast."),
        "ETH -5%, BTC -5%": (-0.05, -0.05, 0.0, "Illustrative instantaneous price shock; not a forecast."),
    }
    if market == "um":
        scenarios["UM funding: +10bp per leg for 3 settlements"] = (
            0.0, 0.0, 3 * 0.001,
            "Assumes +0.10% (10 bp) funding per settlement on both ETHUSDT and BTCUSDT USDⓈ-M legs for three events (0.30% per leg total); rates are hypothetical, not observed.",
        )
    return scenarios



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
        diag_rows.append({"market": market, "interval": interval, "fold": fold_no, **diagnostics(train)})
        for variant, zkey, bkey in (("fixed_1x1", "fixed_z", None), ("rolling_hedge", "dynamic_z", "beta")):
            beta = pd.Series(1.0, index=df.index) if bkey is None else feats[bkey]
            signal_pos = make_position(feats[zkey], beta, test_start, test_end, 2.0, 0.5, 4.0, max_hold)
            # A close signal at t becomes a position at the next bar's open.
            pos = shift_signal_to_next_open(signal_pos)
            test_locs = np.flatnonzero(test_mask)
            if len(test_locs):
                pos.iat[test_locs[-1]] = 0.0
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

        test_index = df.index[test_mask]
        benchmark_defs = [
            ("BTC_buy_hold", (0.0, 1.0), False),
            ("ETH_buy_hold", (1.0, 0.0), False),
            ("50_50_ETH_BTC_buy_hold", (0.5, 0.5), False),
            ("50_50_ETH_BTC_rebalanced", (0.5, 0.5), True),
            ("long_ETH_short_BTC_buy_hold", (0.5, -0.5), False),
            ("no_trade", (0.0, 0.0), False),
        ]
        for name, weights, rebalance in benchmark_defs:
            bench = benchmark_backtest(
                df, test_index, weights, rebalance, fee_bps, slippage_bps,
                spread_bps, funding_eth, funding_btc,
                borrow_bps_per_day if name == "long_ETH_short_BTC_buy_hold" and market == "spot" else 0.0,
                ppd,
            )
            fold_rows.append({
                "market": market, "interval": interval, "fold": fold_no,
                "test_start": str(test_start), "test_end": str(test_end),
                "variant": name, "cost_multiplier": 1.0, **metrics(bench, ppy),
            })

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
            for scenario, (re, rb, common_funding, assumption) in in stress_scenarios_for_market(market).items():
                pnl = we * re + wb * rb - (we + wb) * common_funding
                stress_rows.append({"market": market, "interval": interval, "variant": variant,
                                    "reference_timestamp": str(last["timestamp"]), "position": pos_last,
                                    "beta": beta_last, "scenario": scenario, "one_shot_pnl_on_nav": pnl,
                                    "assumption": assumption})
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
            f_eth, f_eth_quality = load_funding("ETHUSDT", pair.index, args.data_dir)
            f_btc, f_btc_quality = load_funding("BTCUSDT", pair.index, args.data_dir)
            fee = args.um_fee_bps
        else:
            f_eth = f_btc = None
            f_eth_quality = f_btc_quality = None
            fee = args.spot_fee_bps
        pair_gaps = pair.index.to_series().diff().dropna()
        pair_expected = pd.date_range(
            pd.Timestamp(args.start, tz="UTC"),
            pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(hours=1),
            freq="h",
        )
        quality = {
            "market": market,
            "synchronized_pair": {
                "rows": int(len(pair)),
                "start": str(pair.index.min()),
                "end": str(pair.index.max()),
                "expected_hourly_bars": int(len(pair_expected)),
                "missing_hourly_bars": int(len(pair_expected.difference(pair.index))),
                "max_gap": str(pair_gaps.max()) if len(pair_gaps) else None,
                "longest_gap_hours": float(pair_gaps.max().total_seconds() / 3600) if len(pair_gaps) else None,
            },
            "symbols": {},
        }
        for symbol in SYMBOLS:
            manifest_file = args.data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
            quality["symbols"][symbol] = json.loads(manifest_file.read_text()) if manifest_file.exists() else {"manifest_missing": True}
        if market == "um":
            quality["funding"] = {
                "ETHUSDT": f_eth_quality,
                "BTCUSDT": f_btc_quality,
            }
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
        "risk_free_rate_annual": 0.0,
        "note": "Default trading costs are scenario assumptions; verify actual account fees and borrow costs.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Research outputs written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
