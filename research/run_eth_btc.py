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
import csv
import itertools
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
from adaptive_decision import evaluate_research_scope_gate, evaluate_six_input_gate

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


def hourly_quality(index: pd.DatetimeIndex, start: str, end: str,
                   archive_manifest: list[dict] | None = None) -> dict:
    """Measure hourly completeness and preserve every gap with archive provenance."""
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

    archive_by_month = {
        str(item.get("month")): item
        for item in (archive_manifest or [])
        if item.get("month")
    }
    missing_details = []
    for timestamp in missing:
        month = timestamp.strftime("%Y-%m")
        source = archive_by_month.get(month, {})
        missing_details.append({
            "timestamp": str(timestamp),
            "archive_month": month,
            "archive_url": source.get("url"),
            "archive_sha256": source.get("archive_sha256"),
            "archive_checksum_verified": source.get("checksum_verified"),
            "archive_status": source.get("status"),
        })

    missing_intervals = []
    if len(missing):
        group_start = previous = missing[0]
        groups = []
        for timestamp in missing[1:]:
            if timestamp - previous != pd.Timedelta(hours=1):
                groups.append((group_start, previous))
                group_start = timestamp
            previous = timestamp
        groups.append((group_start, previous))
        for first, last in groups:
            months = sorted({x.strftime("%Y-%m") for x in pd.date_range(first, last, freq="h")})
            sources = []
            for month in months:
                source = archive_by_month.get(month, {})
                sources.append({
                    "month": month,
                    "url": source.get("url"),
                    "archive_sha256": source.get("archive_sha256"),
                    "checksum_verified": source.get("checksum_verified"),
                    "status": source.get("status"),
                })
            missing_intervals.append({
                "start": str(first),
                "end": str(last),
                "hours": int((last - first) / pd.Timedelta(hours=1)) + 1,
                "archive_months": months,
                "archive_sources": sources,
            })

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
        "missing_hour_timestamps": [str(x) for x in missing],
        "missing_hour_details": missing_details,
        "missing_hour_intervals": missing_intervals,
        "max_gap": str(max_gap) if pd.notna(max_gap) else None,
        "longest_gap_hours": float(max_gap.total_seconds() / 3600) if pd.notna(max_gap) else None,
        "complete": bool(len(missing) == 0 and duplicate_count == 0 and len(observed) == len(expected)),
    }


def parse_kline_archive(payload: bytes, url: str) -> pd.DataFrame:
    """Parse a Binance Vision kline ZIP with explicit header and timestamp schemas."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one kline CSV in {url}; found {len(csv_names)}")
        raw = pd.read_csv(
            archive.open(csv_names[0]), header=None, dtype=str, keep_default_na=False
        )
    if raw.empty:
        result = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
        result.attrs["timestamp_unit"] = None
        result.attrs["header_detected"] = False
        return result
    if raw.shape[1] < 8 or raw.shape[1] > len(COLUMNS):
        raise ValueError(f"Unexpected kline CSV schema in {url}: {raw.shape[1]} columns")

    width = raw.shape[1]
    aliases = {
        "count": "trade_count",
        "number_of_trades": "trade_count",
        "quote_asset_volume": "quote_volume",
        "taker_buy_volume": "taker_buy_base",
        "taker_buy_base_volume": "taker_buy_base",
        "taker_buy_base_asset_volume": "taker_buy_base",
        "taker_buy_quote_volume": "taker_buy_quote",
        "taker_buy_quote_asset_volume": "taker_buy_quote",
    }
    first_row = [
        aliases.get(str(value).strip().lower().replace(" ", "_"),
                    str(value).strip().lower().replace(" ", "_"))
        for value in raw.iloc[0].tolist()
    ]
    expected_header = COLUMNS[:width]
    header_detected = first_row[0] in {"open_time", "open time"}
    if header_detected:
        if first_row != expected_header:
            raise ValueError(
                f"Unsupported kline header schema in {url}: "
                f"observed={first_row}; expected={expected_header}"
            )
        raw = raw.iloc[1:].reset_index(drop=True)

    if raw.empty:
        result = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
        result.attrs["timestamp_unit"] = None
        result.attrs["header_detected"] = header_detected
        return result

    raw.columns = COLUMNS[:width]
    raw["open_time"] = pd.to_numeric(raw["open_time"], errors="coerce")
    invalid_open = raw["open_time"].isna() | ~np.isfinite(raw["open_time"].to_numpy(dtype=float))
    if invalid_open.any():
        samples = raw.loc[invalid_open, "open_time"].head(3).tolist()
        raise ValueError(
            f"Invalid open_time values in {url}; rows={int(invalid_open.sum())}; samples={samples}"
        )

    median_open = float(raw["open_time"].median())
    if median_open < 10**11:
        raise ValueError(f"Unsupported kline timestamp scale in {url}: median={median_open}")
    unit = "us" if median_open > 10**14 else "ms"
    raw["timestamp"] = pd.to_datetime(raw["open_time"], unit=unit, utc=True)

    numeric_columns = ("open", "high", "low", "close", "volume", "quote_volume")
    for column in numeric_columns:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
        values = raw[column].to_numpy(dtype=float)
        invalid = raw[column].isna() | ~np.isfinite(values)
        if invalid.any():
            samples = raw.loc[invalid, column].head(3).tolist()
            raise ValueError(
                f"Invalid {column} values in {url}; rows={int(invalid.sum())}; samples={samples}"
            )

    result = raw[["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]].copy()
    result.attrs["timestamp_unit"] = unit
    result.attrs["header_detected"] = header_detected
    return result


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
    parse_errors = []
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
        try:
            raw = parse_kline_archive(payload, url)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            parse_errors.append({"month": tag, "url": url, "error": error})
            archive_manifest.append({
                "month": tag, "url": url, "status": "parse_failed",
                "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "checksum_verified": checksum_verified,
                "checksum_error": checksum_error,
                "error": error,
            })
            time.sleep(0.03)
            continue
        if raw.empty:
            archive_manifest.append({"month": tag, "url": url, "status": "empty_archive"})
            missing_months.append(tag)
            continue
        unit = raw.attrs.get("timestamp_unit")
        archive_manifest.append({
            "month": tag, "url": url, "status": "downloaded",
            "archive_sha256": hashlib.sha256(payload).hexdigest(),
            "checksum_verified": checksum_verified, "checksum_error": checksum_error,
            "rows": int(len(raw)), "timestamp_unit": unit,
            "header_detected": bool(raw.attrs.get("header_detected", False)),
        })
        frames.append(raw[["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]])
        time.sleep(0.03)

    if not frames:
        manifest = {
            "market": market, "symbol": symbol, "requested_start": start,
            "requested_end_inclusive": end, "archives": archive_manifest,
            "missing_archive_months": missing_months, "parse_errors": parse_errors,
            "data_quality": None, "status": "failed",
        }
        out_path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
        manifest_path = data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        raise RuntimeError(
            f"No {market} data downloaded for {symbol}; parse_errors={len(parse_errors)}; "
            f"see {manifest_path}"
        )

    combined = pd.concat(frames, ignore_index=True).sort_values("timestamp")
    quality = hourly_quality(pd.DatetimeIndex(combined["timestamp"]), start, end, archive_manifest)
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
        "parse_errors": parse_errors,
        "data_quality": quality,
        "consolidated_csv_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "status": "complete" if not missing_months and not parse_errors and not duplicate_count and quality["complete"] else "incomplete",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if missing_months or parse_errors or duplicate_count or not quality["complete"]:
        raise RuntimeError(
            f"Incomplete {market} {symbol} data: missing archives={missing_months}, "
            f"parse errors={len(parse_errors)}, duplicates={duplicate_count}, "
            f"missing hours={quality['missing_hourly_bars']}; inspect {manifest_path}"
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
    """Ingest monthly Binance Vision funding archives; never call the blocked REST route.

    Archive ingestion is deliberately provisional until Binance's settlement-population
    semantics are independently established. The data and manifest are retained for
    inspection, but this function fails closed so the empirical backtest cannot treat
    an unverified archive population as complete.
    """
    session = requests.Session()
    start_ts = pd.Timestamp(start, tz="UTC")
    end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    frames = []
    archive_manifest = []
    failures = []

    for month in month_starts(start, end):
        tag = month.strftime("%Y-%m")
        filename = f"{symbol}-fundingRate-{tag}.zip"
        url = (
            "https://data.binance.vision/data/futures/um/monthly/fundingRate/"
            f"{symbol}/{filename}"
        )
        cache = data_dir / "cache" / "um" / "fundingRate" / symbol / filename
        try:
            payload, checksum_verified, checksum_error = _download_archive(url, cache, session)
            if not checksum_verified:
                raise RuntimeError(f"Funding archive checksum not verified: {checksum_error}")
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(csv_names) != 1:
                    raise ValueError(
                        f"Expected exactly one funding CSV in {url}; found {len(csv_names)}"
                    )
                raw = pd.read_csv(
                    archive.open(csv_names[0]), header=None, dtype=str, keep_default_na=False
                )
            if raw.empty or raw.shape[1] != 3:
                raise ValueError(
                    f"Unexpected funding archive schema in {url}: "
                    f"rows={len(raw)}, columns={raw.shape[1]}"
                )

            expected = ["calc_time", "funding_interval_hours", "last_funding_rate"]
            first = [str(value).strip().lower() for value in raw.iloc[0].tolist()]
            header_detected = first == expected
            if header_detected:
                raw = raw.iloc[1:].reset_index(drop=True)
            raw.columns = expected
            for column in expected:
                raw[column] = pd.to_numeric(raw[column], errors="coerce")
                values = raw[column].to_numpy(dtype=float)
                invalid = raw[column].isna() | ~np.isfinite(values)
                if invalid.any():
                    raise ValueError(
                        f"Invalid {column} values in {url}: {int(invalid.sum())} rows"
                    )
            if (raw["funding_interval_hours"] <= 0).any():
                raise ValueError(f"Non-positive funding interval in {url}")
            raw["timestamp"] = pd.to_datetime(raw["calc_time"], unit="ms", utc=True)
            month_start = month.tz_localize("UTC")
            next_month = month_start + pd.offsets.MonthBegin(1)
            if ((raw["timestamp"] < month_start) | (raw["timestamp"] >= next_month)).any():
                raise ValueError(f"Funding timestamps outside archive month in {url}")
            frames.append(raw[["timestamp", "funding_interval_hours", "last_funding_rate"]])
            archive_manifest.append({
                "month": tag, "url": url, "status": "downloaded_checksum_verified",
                "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "checksum_verified": True, "rows": int(len(raw)),
                "header_detected": header_detected,
                "schema": expected,
                "interval_hours_observed": sorted(
                    set(raw["funding_interval_hours"].astype(float).tolist())
                ),
            })
        except Exception as exc:
            failures.append({"month": tag, "url": url, "error": f"{type(exc).__name__}: {exc}"})
            archive_manifest.append({
                "month": tag, "url": url, "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            })

    out = data_dir / "raw" / f"um_{symbol}_funding.csv"
    manifest_path = data_dir / "raw" / f"um_{symbol}_funding_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if frames:
        combined = pd.concat(frames, ignore_index=True).sort_values("timestamp")
        in_sample = combined[
            (combined["timestamp"] >= start_ts) & (combined["timestamp"] < end_exclusive)
        ].copy()
        duplicate_count = int(in_sample["timestamp"].duplicated().sum())
        output_frame = in_sample.rename(columns={"last_funding_rate": "fundingRate"})
        output_frame.to_csv(out, index=False)
        stamps = pd.DatetimeIndex(in_sample["timestamp"])
        quality = funding_quality(stamps, start_ts, end_exclusive) if len(stamps) else None
        csv_sha256 = hashlib.sha256(out.read_bytes()).hexdigest()
    else:
        in_sample = pd.DataFrame(columns=["timestamp", "funding_interval_hours", "last_funding_rate"])
        duplicate_count = 0
        quality = None
        csv_sha256 = None

    manifest = {
        "symbol": symbol,
        "source": "Binance Vision monthly USD-M fundingRate archives",
        "requested_start": str(start_ts),
        "requested_end_exclusive": str(end_exclusive),
        "archives": archive_manifest,
        "failed_months": failures,
        "rows": int(len(in_sample)),
        "duplicate_timestamps": duplicate_count,
        "data_quality": quality,
        "csv_sha256": csv_sha256,
        "event_semantics": "UNVERIFIED",
        "completeness_status": "PROVISIONAL_NOT_ACCEPTED",
        "status": "failed" if failures or not frames or duplicate_count else "provisional",
        "reason": (
            "Binance public-data issue #517 leaves settlement-population and event semantics "
            "unresolved; archive presence/checksum/cadence cannot establish complete payable events."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if failures or not frames or duplicate_count:
        raise RuntimeError(
            f"Funding archive ingestion failed for {symbol}: failed_months={len(failures)}, "
            f"duplicate_timestamps={duplicate_count}; inspect {manifest_path}"
        )
    raise RuntimeError(
        f"Funding archive data retained but not accepted for {symbol}: event semantics and "
        f"settlement-population completeness remain unverified; inspect {manifest_path}"
    )


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
    """Exploratory percentile 95% CI; 150 replications have limited quantile precision."""
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
            "held_w_eth": prev_eth, "held_w_btc": prev_btc,
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
            for scenario, (re, rb, common_funding, assumption) in stress_scenarios_for_market(market).items():
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



def query_aggregate_trades(session: requests.Session, symbol: str,
                          timestamp: pd.Timestamp) -> dict:
    """Probe one UTC hour for any aggregate trade; limit=1 is sufficient for presence."""
    ts = pd.Timestamp(timestamp)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    start_ms = int(ts.timestamp() * 1000)
    end_ms = start_ms + 60 * 60 * 1000 - 1
    endpoint = "https://data-api.binance.vision/api/v3/aggTrades"
    params = {
        "symbol": symbol,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 1,
    }
    response = request_with_retry(session, endpoint, timeout=45, params=params)
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected aggregate-trades API response for {symbol}: {payload}")
    sample = None
    timestamp_unit = "ms"
    for item in payload:
        if not isinstance(item, dict) or not {"a", "p", "q", "T"}.issubset(item):
            raise RuntimeError(f"Unexpected aggregate-trade schema for {symbol}: {item}")
        raw_time = int(item["T"])
        item_unit = "us" if raw_time > 10**14 else "ms"
        trade_ms = raw_time // 1000 if item_unit == "us" else raw_time
        if trade_ms < start_ms or trade_ms > end_ms:
            raise RuntimeError(
                f"Aggregate trade timestamp outside requested hour for {symbol}: {item['T']}"
            )
        timestamp_unit = item_unit
        if sample is None:
            sample = {
                "aggregate_trade_id": int(item["a"]),
                "timestamp": str(pd.to_datetime(raw_time, unit=item_unit, utc=True)),
                "price": str(item["p"]),
                "quantity": str(item["q"]),
            }
    body = getattr(response, "content", b"")
    if isinstance(body, str):
        body = body.encode("utf-8")
    return {
        "endpoint": endpoint,
        "request": params,
        "http_status": int(response.status_code),
        "request_succeeded": True,
        "rows_returned": len(payload),
        "trade_found": bool(payload),
        "timestamp_unit": timestamp_unit,
        "sample_trade": sample,
        "response_sha256": hashlib.sha256(body).hexdigest(),
    }


def inspect_aggtrades_archive(payload: bytes, day: str,
                              gap_timestamps: list[pd.Timestamp],
                              control_timestamp: pd.Timestamp | None = None) -> dict:
    """Stream a checksum-verified daily aggTrades ZIP into per-hour evidence counts."""
    day_start = pd.Timestamp(day, tz="UTC")
    day_end = day_start + pd.Timedelta(days=1)

    def utc_hour(value):
        ts = pd.Timestamp(value)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return ts.floor("h")

    gap_hours = {str(utc_hour(value)): utc_hour(value) for value in gap_timestamps}
    control_hour = utc_hour(control_timestamp) if control_timestamp is not None else None
    gap_counts = {key: 0 for key in gap_hours}
    gap_samples = {}
    control_count = 0
    control_sample = None
    row_count = 0
    duplicate_ids = 0
    out_of_order_ids = 0
    out_of_order_timestamps = 0
    previous_id = None
    previous_timestamp = None
    timestamp_unit = None
    first_timestamp = None
    last_timestamp = None
    member_name = None
    header_detected = False

    expected_header = [
        "aggtradeid", "price", "quantity", "firsttradeid",
        "lasttradeid", "timestamp", "isbuyermaker", "isbestmatch",
    ]

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one aggTrades CSV for {day}; found {len(csv_names)}")
        member_name = csv_names[0]
        with archive.open(member_name) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8", newline=""))
            first_row = next(reader, None)
            if first_row is None:
                raise ValueError(f"Empty aggTrades CSV for {day}")
            normalized_header = [
                value.strip().lstrip("\ufeff").lower().replace("_", "").replace(" ", "")
                for value in first_row
            ]
            if normalized_header == expected_header:
                header_detected = True
                rows = reader
            elif len(first_row) == 8 and first_row[0].strip().isdigit():
                rows = itertools.chain([first_row], reader)
            else:
                raise ValueError(
                    f"Unsupported aggTrades schema for {day}: first row={first_row}"
                )

            for line_number, row in enumerate(rows, start=2 if header_detected else 1):
                if not row:
                    continue
                if len(row) != 8:
                    raise ValueError(
                        f"Expected 8 aggTrades fields for {day} at CSV line {line_number}; "
                        f"found {len(row)}"
                    )
                try:
                    trade_id = int(row[0])
                    price = float(row[1])
                    quantity = float(row[2])
                    first_trade_id = int(row[3])
                    last_trade_id = int(row[4])
                    raw_timestamp = int(row[5])
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid aggTrades numeric field for {day} at CSV line {line_number}"
                    ) from exc
                if (
                    not math.isfinite(price) or price <= 0
                    or not math.isfinite(quantity) or quantity <= 0
                    or first_trade_id < 0 or last_trade_id < first_trade_id
                    or trade_id < 0
                ):
                    raise ValueError(
                        f"Invalid aggTrades values for {day} at CSV line {line_number}"
                    )

                unit = "us" if raw_timestamp > 10**14 else "ms"
                if timestamp_unit is None:
                    timestamp_unit = unit
                elif timestamp_unit != unit:
                    raise ValueError(f"Mixed aggTrades timestamp units in {day}")
                trade_timestamp = pd.to_datetime(raw_timestamp, unit=unit, utc=True)
                if not day_start <= trade_timestamp < day_end:
                    raise ValueError(
                        f"aggTrades timestamp outside requested UTC day for {day}: "
                        f"{trade_timestamp}"
                    )
                if previous_id is not None:
                    if trade_id == previous_id:
                        duplicate_ids += 1
                    elif trade_id < previous_id:
                        out_of_order_ids += 1
                if previous_timestamp is not None and trade_timestamp < previous_timestamp:
                    out_of_order_timestamps += 1
                previous_id = trade_id
                previous_timestamp = trade_timestamp
                row_count += 1
                first_timestamp = trade_timestamp if first_timestamp is None else first_timestamp
                last_timestamp = trade_timestamp

                hour_key = str(trade_timestamp.floor("h"))
                if hour_key in gap_counts:
                    gap_counts[hour_key] += 1
                    if hour_key not in gap_samples:
                        gap_samples[hour_key] = {
                            "aggregate_trade_id": trade_id,
                            "timestamp_utc": str(trade_timestamp),
                            "price": price,
                            "quantity": quantity,
                        }
                if control_hour is not None and control_hour <= trade_timestamp < control_hour + pd.Timedelta(hours=1):
                    control_count += 1
                    if control_sample is None:
                        control_sample = {
                            "aggregate_trade_id": trade_id,
                            "timestamp_utc": str(trade_timestamp),
                            "price": price,
                            "quantity": quantity,
                        }

    anomaly_count = duplicate_ids + out_of_order_ids + out_of_order_timestamps
    status = "PARSED" if row_count > 0 and anomaly_count == 0 else (
        "PARSED_WITH_ANOMALIES" if row_count > 0 else "EMPTY_ARCHIVE"
    )
    return {
        "status": status,
        "archive_member": member_name,
        "header_detected": header_detected,
        "timestamp_unit": timestamp_unit,
        "rows": row_count,
        "first_timestamp_utc": str(first_timestamp) if first_timestamp is not None else None,
        "last_timestamp_utc": str(last_timestamp) if last_timestamp is not None else None,
        "duplicate_aggregate_trade_ids": duplicate_ids,
        "out_of_order_aggregate_trade_ids": out_of_order_ids,
        "out_of_order_timestamps": out_of_order_timestamps,
        "gap_trade_counts": gap_counts,
        "gap_trade_samples": gap_samples,
        "positive_control_timestamp": str(control_hour) if control_hour is not None else None,
        "positive_control_trade_count": control_count if control_hour is not None else None,
        "positive_control_sample": control_sample,
    }


def classify_gap_reconciliation(api_found: bool, daily_archive_found: bool,
                                values_match: bool | None = None,
                                api_request_succeeded: bool = True,
                                agg_trades_found: bool | None = None,
                                agg_trades_request_succeeded: bool | None = None,
                                positive_control_passed: bool = False) -> str:
    """Classify price-bar and trade-level evidence without inferring zero activity."""
    if api_found and daily_archive_found:
        return "confirmed_monthly_archive_omission" if values_match else "official_source_value_mismatch"
    if api_found or daily_archive_found:
        return "single_official_representation_only"
    if agg_trades_request_succeeded is True:
        if agg_trades_found:
            return "aggregate_trades_present_kline_missing"
        if positive_control_passed:
            return "confirmed_no_trade_interval"
        return "aggregate_trade_positive_control_failed_unresolved"
    if agg_trades_request_succeeded is False:
        return "aggregate_trade_request_failed_unresolved"
    if not api_request_succeeded:
        return "api_request_failed_daily_archive_absent_unresolved"
    return "both_kline_sources_empty_trade_status_unverified"


def reconcile_spot_gaps(symbol: str, start: str, end: str, data_dir: Path) -> dict:
    """Cross-check missing Spot hours against REST, daily klines and aggregate trades.

    Aggregate-trade empty responses are interpreted only after a same-day known-active
    kline positive control succeeds. This function records evidence; it never inserts bars.
    """
    csv_path = data_dir / "raw" / f"spot_{symbol}_1h.csv"
    manifest_path = data_dir / "raw" / f"spot_{symbol}_archive_manifest.json"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing consolidated Spot CSV required for reconciliation: {csv_path}")
    source_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    frame = pd.read_csv(
        csv_path, usecols=lambda column: column in {"timestamp", "volume"}
    )
    if "volume" not in frame.columns:
        frame["volume"] = np.nan
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    quality = hourly_quality(
        pd.DatetimeIndex(frame["timestamp"]), start, end, source_manifest.get("archives", [])
    )
    missing = pd.to_datetime(quality["missing_hour_timestamps"], utc=True)
    result = {
        "market": "spot",
        "symbol": symbol,
        "requested_start": start,
        "requested_end_inclusive": end,
        "rest_endpoint": "https://data-api.binance.vision/api/v3/klines",
        "rest_host_type": "official_public_market_data_only_host",
        "daily_archive_base": "https://data.binance.vision/data/spot/daily/klines",
        "aggregate_trade_endpoint": "https://data-api.binance.vision/api/v3/aggTrades",
        "aggregate_trade_probe_limit": 1,
        "source_csv": str(csv_path),
        "source_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "monthly_archive_quality": quality,
        "daily_archives": {},
        "aggregate_trade_positive_controls": {},
        "daily_aggtrades_archives": {},
        "gaps": [],
        "classification_counts": {},
        "reconciliation_complete": True,
    }
    if not len(missing):
        result["gap_count"] = 0
        out_path = data_dir / "raw" / f"spot_{symbol}_gap_reconciliation.json"
        out_path.write_text(json.dumps(result, indent=2))
        result["manifest_path"] = str(out_path)
        return result

    session = requests.Session()
    daily_frames: dict[str, pd.DataFrame] = {}
    daily_info: dict[str, dict] = {}
    gaps_by_day: dict[str, list[pd.Timestamp]] = {}
    for timestamp in missing:
        gaps_by_day.setdefault(timestamp.strftime("%Y-%m-%d"), []).append(timestamp)

    for day in sorted(gaps_by_day):
        filename = f"{symbol}-1h-{day}.zip"
        url = f"https://data.binance.vision/data/spot/daily/klines/{symbol}/1h/{filename}"
        cache = data_dir / "cache" / "spot_daily" / symbol / filename
        try:
            payload, verified, checksum_error = _download_archive(url, cache, session)
            daily_frames[day] = parse_kline_archive(payload, url)
            daily_info[day] = {
                "url": url,
                "status": "downloaded",
                "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "checksum_verified": verified,
                "checksum_error": checksum_error,
                "rows": int(len(daily_frames[day])),
                "timestamp_unit": daily_frames[day].attrs.get("timestamp_unit"),
            }
        except FileNotFoundError:
            daily_frames[day] = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
            daily_info[day] = {"url": url, "status": "missing_http_404"}
        except Exception as exc:
            daily_frames[day] = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
            daily_info[day] = {"url": url, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
        time.sleep(0.03)

    result["daily_archives"] = daily_info

    for timestamp in missing:
        hour_start_ms = int(timestamp.timestamp() * 1000)
        hour_end_ms = hour_start_ms + 60 * 60 * 1000 - 1
        params = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": hour_start_ms,
            "endTime": hour_end_ms,
            "limit": 10,
        }
        gap_day = timestamp.strftime("%Y-%m-%d")
        api_request_succeeded = False
        entry = {
            "timestamp": str(timestamp),
            "gap_day": gap_day,
            "archive_month": timestamp.strftime("%Y-%m"),
            "daily_archive": daily_info.get(gap_day, {}),
            "api_request": params,
            "api_status": None,
            "api_rows_returned": 0,
            "api_candle_found": False,
            "daily_candle_found": False,
            "values_match": None,
        }
        try:
            response = request_with_retry(
                session, result["rest_endpoint"], timeout=45, params=params
            )
            payload = response.json()
            if not isinstance(payload, list):
                raise RuntimeError(f"Unexpected klines API response: {payload}")
            entry["api_status"] = response.status_code
            api_request_succeeded = True
            entry["api_request_succeeded"] = True
            entry["api_rows_returned"] = len(payload)
            api_rows = [row for row in payload if int(row[0]) == hour_start_ms]
            if api_rows:
                row = api_rows[0]
                entry["api_candle_found"] = True
                entry["api_candle"] = {
                    "open": float(row[1]), "high": float(row[2]),
                    "low": float(row[3]), "close": float(row[4]),
                    "volume": float(row[5]),
                    "quote_volume": float(row[7]) if len(row) > 7 else None,
                }
                entry["api_candle_sha256"] = hashlib.sha256(
                    json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                ).hexdigest()
        except Exception as exc:
            entry["api_error"] = f"{type(exc).__name__}: {exc}"

        daily_frame = daily_frames.get(gap_day)
        if daily_frame is not None and not daily_frame.empty:
            matches = daily_frame.loc[daily_frame["timestamp"] == timestamp]
            if not matches.empty:
                row = matches.iloc[0]
                entry["daily_candle_found"] = True
                entry["daily_candle"] = {
                    column: float(row[column])
                    for column in ("open", "high", "low", "close", "volume")
                }
                entry["daily_candle_sha256"] = hashlib.sha256(
                    json.dumps(entry["daily_candle"], sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()

        if entry["api_candle_found"] and entry["daily_candle_found"]:
            fields = ("open", "high", "low", "close", "volume")
            entry["values_match"] = all(
                math.isclose(
                    entry["api_candle"][field], entry["daily_candle"][field],
                    rel_tol=1e-12, abs_tol=1e-12,
                )
                for field in fields
            )
        entry["api_request_succeeded"] = api_request_succeeded
        entry["classification"] = classify_gap_reconciliation(
            entry["api_candle_found"], entry["daily_candle_found"], entry["values_match"],
            api_request_succeeded=api_request_succeeded,
        )
        result["gaps"].append(entry)
        time.sleep(0.03)

    unresolved_by_day: dict[str, list[dict]] = {}
    for entry in result["gaps"]:
        if not entry["api_candle_found"] and not entry["daily_candle_found"]:
            unresolved_by_day.setdefault(entry["gap_day"], []).append(entry)

    observed_by_day: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    active_monthly = frame.loc[
        np.isfinite(frame["volume"].to_numpy(dtype=float)) & (frame["volume"] > 0)
    ]
    for row in active_monthly.itertuples(index=False):
        observed_by_day.setdefault(row.timestamp.strftime("%Y-%m-%d"), []).append(
            (pd.Timestamp(row.timestamp), float(row.volume))
        )

    for day, day_gaps in unresolved_by_day.items():
        daily_frame = daily_frames.get(day)
        daily_candidates: list[tuple[pd.Timestamp, float]] = []
        if daily_frame is not None and not daily_frame.empty and "volume" in daily_frame:
            daily_volume = pd.to_numeric(daily_frame["volume"], errors="coerce")
            active_daily = daily_frame.loc[
                np.isfinite(daily_volume.to_numpy(dtype=float)) & (daily_volume > 0)
            ]
            daily_candidates = [
                (pd.Timestamp(row.timestamp), float(row.volume))
                for row in active_daily.itertuples(index=False)
            ]
        candidates = daily_candidates or observed_by_day.get(day, [])
        candidate_source = (
            "daily_archive" if daily_candidates
            else ("monthly_archive" if candidates else None)
        )
        control_info = {
            "status": "unavailable",
            "known_active_kline_control_available": bool(candidates),
            "positive_control_passed": False,
        }
        if candidates:
            first_gap = day_gaps[0]["timestamp"]
            control_ts, control_volume = min(
                candidates,
                key=lambda candidate: abs(
                    (candidate[0] - pd.Timestamp(first_gap)).total_seconds()
                ),
            )
            control_info["control_timestamp"] = str(control_ts)
            control_info["control_volume"] = control_volume
            control_info["candidate_source"] = candidate_source
            try:
                control_probe = query_aggregate_trades(session, symbol, control_ts)
                control_info.update(control_probe)
                control_info["positive_control_passed"] = bool(control_probe["trade_found"])
                control_info["status"] = "passed" if control_info["positive_control_passed"] else "empty_response"
            except Exception as exc:
                control_info["status"] = "request_failed"
                control_info["error"] = f"{type(exc).__name__}: {exc}"
        result["aggregate_trade_positive_controls"][day] = control_info

        for entry in day_gaps:
            try:
                trade_probe = query_aggregate_trades(
                    session, symbol, pd.Timestamp(entry["timestamp"])
                )
                entry["aggregate_trade_probe"] = trade_probe
                entry["agg_trades_request_succeeded"] = True
                entry["agg_trades_found"] = bool(trade_probe["trade_found"])
            except Exception as exc:
                entry["agg_trades_request_succeeded"] = False
                entry["agg_trades_found"] = None
                entry["agg_trades_error"] = f"{type(exc).__name__}: {exc}"
            entry["positive_control_passed"] = bool(control_info["positive_control_passed"])
            entry["classification"] = classify_gap_reconciliation(
                entry["api_candle_found"], entry["daily_candle_found"], entry["values_match"],
                api_request_succeeded=entry["api_request_succeeded"],
                agg_trades_found=entry["agg_trades_found"],
                agg_trades_request_succeeded=entry["agg_trades_request_succeeded"],
                positive_control_passed=entry["positive_control_passed"],
            )
            time.sleep(0.03)

        # The REST aggregate-trades route has previously failed its same-day
        # positive control. Fall back to the official daily archive rather than
        # repeating an unchanged empty REST probe or inferring no trading.
        needs_archive = (
            not control_info.get("positive_control_passed", False)
            or any(not entry.get("agg_trades_request_succeeded", False) for entry in day_gaps)
        )
        if needs_archive:
            archive_filename = f"{symbol}-aggTrades-{day}.zip"
            archive_url = (
                "https://data.binance.vision/data/spot/daily/aggTrades/"
                f"{symbol}/{archive_filename}"
            )
            archive_cache = (
                data_dir / "cache" / "spot_daily_aggtrades" / symbol / archive_filename
            )
            try:
                archive_payload, checksum_verified, checksum_error = _download_archive(
                    archive_url, archive_cache, session
                )
                archive_probe = inspect_aggtrades_archive(
                    archive_payload,
                    day,
                    [pd.Timestamp(entry["timestamp"]) for entry in day_gaps],
                    pd.Timestamp(control_info["control_timestamp"])
                    if control_info.get("control_timestamp") else None,
                )
                archive_record = {
                    **archive_probe,
                    "url": archive_url,
                    "archive_sha256": hashlib.sha256(archive_payload).hexdigest(),
                    "checksum_verified": checksum_verified,
                    "checksum_error": checksum_error,
                }
                if not checksum_verified:
                    archive_record["status"] = "CHECKSUM_UNVERIFIED"
                result["daily_aggtrades_archives"][day] = archive_record
                archive_valid = checksum_verified and archive_probe["status"] == "PARSED"
                archive_control_passed = (
                    archive_valid
                    and archive_probe["positive_control_trade_count"] is not None
                    and archive_probe["positive_control_trade_count"] > 0
                )
                control_info["archive_url"] = archive_url
                control_info["archive_checksum_verified"] = checksum_verified
                control_info["archive_positive_control_passed"] = bool(archive_control_passed)
                control_info["archive_positive_control_trade_count"] = (
                    archive_probe["positive_control_trade_count"]
                )

                for entry in day_gaps:
                    gap_key = str(pd.Timestamp(entry["timestamp"]))
                    trade_count = archive_probe["gap_trade_counts"].get(gap_key, 0)
                    entry["aggregate_trade_archive"] = {
                        "url": archive_url,
                        "archive_sha256": archive_record["archive_sha256"],
                        "checksum_verified": checksum_verified,
                        "trade_count": trade_count,
                        "positive_control_passed": bool(archive_control_passed),
                        "sample_trade": archive_probe["gap_trade_samples"].get(gap_key),
                    }
                    if archive_valid and trade_count > 0:
                        if entry.get("agg_trades_found") is False:
                            entry["aggregate_trade_rest_archive_disagreement"] = (
                                "REST probe returned no trade; checksum-verified daily archive contains trades"
                            )
                        entry["agg_trades_request_succeeded"] = True
                        entry["agg_trades_found"] = True
                        entry["positive_control_passed"] = bool(archive_control_passed)
                        entry["classification"] = "aggregate_trades_present_kline_missing"
                    elif archive_control_passed:
                        if entry.get("agg_trades_found") is True:
                            entry["aggregate_trade_source_disagreement"] = (
                                "REST probe found trades; checksum-verified daily archive has none"
                            )
                            entry["classification"] = "aggregate_trade_source_disagreement_unresolved"
                        else:
                            entry["agg_trades_request_succeeded"] = True
                            entry["agg_trades_found"] = False
                            entry["positive_control_passed"] = True
                            entry["classification"] = "confirmed_no_trade_interval"
                    elif entry["classification"] not in {
                        "aggregate_trades_present_kline_missing",
                        "confirmed_no_trade_interval",
                    }:
                        entry["classification"] = "aggregate_trade_archive_positive_control_failed_unresolved"
            except FileNotFoundError as exc:
                result["daily_aggtrades_archives"][day] = {
                    "url": archive_url, "status": "missing_http_404",
                    "error": f"{type(exc).__name__}: {exc}",
                }
                for entry in day_gaps:
                    entry["aggregate_trade_archive_error"] = f"{type(exc).__name__}: {exc}"
                    if entry["classification"] not in {"aggregate_trades_present_kline_missing"}:
                        entry["classification"] = "aggregate_trade_archive_request_failed_unresolved"
            except Exception as exc:
                result["daily_aggtrades_archives"][day] = {
                    "url": archive_url, "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
                for entry in day_gaps:
                    entry["aggregate_trade_archive_error"] = f"{type(exc).__name__}: {exc}"
                    if entry["classification"] not in {"aggregate_trades_present_kline_missing"}:
                        entry["classification"] = "aggregate_trade_archive_request_failed_unresolved"

    for entry in result["gaps"]:
        label = entry["classification"]
        result["classification_counts"][label] = result["classification_counts"].get(label, 0) + 1
    resolved_labels = {
        "confirmed_monthly_archive_omission",
        "aggregate_trades_present_kline_missing",
        "confirmed_no_trade_interval",
    }
    result["reconciliation_complete"] = (
        len(result["gaps"]) == len(missing)
        and all(entry["classification"] in resolved_labels for entry in result["gaps"])
    )
    result["gap_count"] = len(result["gaps"])
    out_path = data_dir / "raw" / f"spot_{symbol}_gap_reconciliation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    result["manifest_path"] = str(out_path)
    return result

def audit_all_inputs(start: str, end: str, data_dir: Path, output_dir: Path,
                     reconcile_gaps: bool = False, market_scope: str = "both") -> dict:
    """Audit all six inputs and always persist one artifact-ready manifest per input."""
    summary = {
        "start": start,
        "end": end,
        "price_series": {},
        "funding_series": {},
        "gap_reconciliation": None,
        "complete": False,
    }
    expected_manifest_paths = []

    for market in ("spot", "um"):
        for symbol in SYMBOLS:
            key = f"{market}_{symbol}"
            csv_path = data_dir / "raw" / f"{market}_{symbol}_1h.csv"
            manifest_path = data_dir / "raw" / f"{market}_{symbol}_archive_manifest.json"
            source_base = "spot" if market == "spot" else "futures/um"
            source = (
                f"https://data.binance.vision/data/{source_base}/monthly/klines/"
                f"{symbol}/1h/"
            )
            record = {
                "market": market,
                "symbol": symbol,
                "status": "not_run",
                "csv_path": str(csv_path),
                "manifest_path": str(manifest_path),
                "source": source,
            }
            try:
                download_klines(market, symbol, start, end, data_dir)
                record["status"] = "complete"
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = f"{type(exc).__name__}: {exc}"

            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                except Exception as exc:
                    manifest = {
                        "manifest_read_error": f"{type(exc).__name__}: {exc}",
                        "archives": [],
                    }
            else:
                manifest = {
                    "market": market,
                    "symbol": symbol,
                    "requested_start": start,
                    "requested_end_inclusive": end,
                    "source": source,
                    "archives": [],
                    "missing_archive_months": [],
                    "data_quality": None,
                }

            quality = manifest.get("data_quality")
            if record["status"] == "complete" and not (
                isinstance(quality, dict) and quality.get("complete", False)
            ):
                record["status"] = "failed"
                record["error"] = (
                    "Downloader returned without a complete data-quality manifest"
                )
            elif record["status"] == "failed" and isinstance(quality, dict):
                if not quality.get("complete", False):
                    record["status"] = "incomplete"

            manifest["market"] = market
            manifest["symbol"] = symbol
            manifest["requested_start"] = start
            manifest["requested_end_inclusive"] = end
            manifest["source"] = source
            manifest["status"] = record["status"]
            manifest["audit_status"] = record["status"]
            if record.get("error"):
                manifest["audit_error"] = record["error"]
            manifest_path.write_text(json.dumps(manifest, indent=2))

            record["data_quality"] = manifest.get("data_quality")
            record["missing_archive_months"] = manifest.get("missing_archive_months", [])
            record["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            record["manifest_status"] = manifest.get("status", record["status"])
            summary["price_series"][key] = record
            expected_manifest_paths.append(manifest_path)

    for symbol in SYMBOLS:
        key = f"um_{symbol}_funding"
        csv_path = data_dir / "raw" / f"um_{symbol}_funding.csv"
        manifest_path = data_dir / "raw" / f"um_{symbol}_funding_manifest.json"
        source = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-YYYY-MM.zip"
        record = {
            "symbol": symbol,
            "status": "not_run",
            "csv_path": str(csv_path),
            "manifest_path": str(manifest_path),
            "source": source,
        }
        try:
            download_funding(symbol, start, end, data_dir)
            record["status"] = "complete"
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except Exception as exc:
                manifest = {"manifest_read_error": f"{type(exc).__name__}: {exc}"}
        else:
            start_ts = pd.Timestamp(start, tz="UTC")
            end_exclusive = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
            manifest = {
                "market": "um",
                "symbol": symbol,
                "endpoint": source,
                "requested_start": str(start_ts),
                "requested_end_exclusive": str(end_exclusive),
                "pages": 0,
                "rows_received": 0,
                "data_quality": None,
            }

        quality = manifest.get("data_quality")
        if record["status"] == "complete" and not (
            isinstance(quality, dict) and quality.get("complete", False)
        ):
            record["status"] = "failed"
            record["error"] = (
                "Funding downloader returned without a complete data-quality manifest"
            )
        elif record["status"] == "failed" and isinstance(quality, dict):
            if not quality.get("complete", False):
                record["status"] = "incomplete"

        manifest["market"] = "um"
        manifest["symbol"] = symbol
        manifest["endpoint"] = source
        manifest["requested_start"] = str(pd.Timestamp(start, tz="UTC"))
        manifest["requested_end_exclusive"] = str(
            pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        )
        manifest["status"] = record["status"]
        manifest["audit_status"] = record["status"]
        if record.get("error"):
            manifest["audit_error"] = record["error"]
        manifest_path.write_text(json.dumps(manifest, indent=2))

        record["data_quality"] = manifest.get("data_quality")
        record["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        record["manifest_status"] = manifest.get("status", record["status"])
        summary["funding_series"][key] = record
        expected_manifest_paths.append(manifest_path)

    if reconcile_gaps:
        summary["gap_reconciliation"] = {}
        for symbol in SYMBOLS:
            try:
                summary["gap_reconciliation"][symbol] = reconcile_spot_gaps(
                    symbol, start, end, data_dir
                )
            except Exception as exc:
                summary["gap_reconciliation"][symbol] = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "reconciliation_complete": False,
                }

    manifest_paths = [str(path) for path in expected_manifest_paths if path.exists()]
    all_six_manifests_present = len(manifest_paths) == 6
    summary["input_manifest_count"] = len(manifest_paths)
    summary["input_manifest_paths"] = manifest_paths
    summary["all_six_manifests_present"] = all_six_manifests_present

    price_ok = all(record["status"] == "complete" for record in summary["price_series"].values())
    funding_ok = all(record["status"] == "complete" for record in summary["funding_series"].values())
    reconciliation_ok = (
        not reconcile_gaps
        or (
            bool(summary["gap_reconciliation"])
            and all(
                item.get("reconciliation_complete", False)
                for item in summary["gap_reconciliation"].values()
            )
        )
    )
    input_states = {
        key: record.get("status") == "complete"
        for key, record in summary["price_series"].items()
    }
    input_states.update({
        f"funding_{record['symbol']}": record.get("status") == "complete"
        for record in summary["funding_series"].values()
    })
    manifest_states = {
        key: Path(record["manifest_path"]).is_file()
        for key, record in summary["price_series"].items()
    }
    manifest_states.update({
        f"funding_{record['symbol']}": Path(record["manifest_path"]).is_file()
        for record in summary["funding_series"].values()
    })
    six_input_audit = evaluate_six_input_gate(
        input_states,
        manifests_present=all_six_manifests_present,
        spot_gap_reconciliation_complete=(
            reconciliation_ok if reconcile_gaps else None
        ),
    )
    research_scope_gate = evaluate_research_scope_gate(
        input_states,
        manifest_states,
        market_scope=market_scope,
        spot_gap_reconciliation_complete=(
            reconciliation_ok if reconcile_gaps else None
        ),
        # Confirmed no-trade intervals still require a separately implemented
        # event-time/elapsed-time PnL and execution policy before Spot acceptance.
        spot_time_policy_accepted=False,
    )
    summary["six_input_audit_gate"] = six_input_audit
    summary["research_scope_gate"] = research_scope_gate
    summary["empirical_gate"] = research_scope_gate
    summary["complete"] = bool(research_scope_gate["allowed"])
    summary["status"] = "COMPLETE" if summary["complete"] else "INCOMPLETE"
    summary["price_series_complete"] = price_ok
    summary["funding_series_complete"] = funding_ok
    summary["reconciliation_complete"] = reconciliation_ok
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "data_audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    return summary

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
    parser.add_argument("--audit-only", action="store_true", help="Audit all four price series and both funding histories; do not run strategy backtests")
    parser.add_argument("--reconcile-spot-gaps", action="store_true", help="During --audit-only, cross-check missing ETH Spot hours against Binance REST and daily archives")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if args.reconcile_spot_gaps and not args.audit_only:
        parser.error("--reconcile-spot-gaps requires --audit-only")
    if args.audit_only:
        summary = audit_all_inputs(
            args.start, args.end, args.data_dir, args.output_dir,
            reconcile_gaps=args.reconcile_spot_gaps,
            market_scope=args.market,
        )
        print(json.dumps(summary, indent=2))
        if not summary["complete"]:
            raise SystemExit(2)
        return
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
