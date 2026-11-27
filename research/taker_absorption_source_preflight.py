#!/usr/bin/env python3
"""Read-only, checksum-backed feasibility probe for Binance Spot taker-flow absorption data."""
from __future__ import annotations

import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import zipfile
from pathlib import Path

import stlfsi4_btc_downside_semivariance as market

HYPOTHESIS_ID = "QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01"
START_DATE = dt.date(2017, 8, 17)
END_DATE = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
WORKERS = 6
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
OUTPUT_DIR = ROOT / "reports" / "generated" / "taker-absorption-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"


def _finite(row: list[str], index: int, field: str, row_number: int) -> float:
    try:
        value = float(row[index])
    except (IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field} at row {row_number}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Non-finite {field} at row {row_number}")
    return value


def parse_kline_archive(body: bytes) -> tuple[dict[dt.date, dict], str]:
    """Parse the documented 12-column Binance Spot 1d kline CSV schema."""
    values: dict[dt.date, dict] = {}
    units: set[str] = set()
    for row_number, raw_line in enumerate(io.StringIO(body.decode("utf-8-sig")), start=1):
        if not raw_line.strip():
            continue
        row = next(csv.reader([raw_line]))
        first = row[0].strip().lower() if row else ""
        if row_number == 1 and first in {"open_time", "open time"}:
            continue
        if len(row) != 12:
            raise ValueError(f"Expected 12 Binance kline columns at row {row_number}; found {len(row)}")
        try:
            open_time, close_time = int(row[0]), int(row[6])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Binance timestamp at row {row_number}") from exc
        if open_time >= 100_000_000_000_000:
            unit, day_units, scale = "microseconds", 86_400_000_000, 1_000_000
        elif open_time >= 100_000_000_000:
            unit, day_units, scale = "milliseconds", 86_400_000, 1_000
        else:
            raise ValueError(f"Unsupported timestamp magnitude at row {row_number}")
        if open_time % day_units or close_time != open_time + day_units - 1:
            raise ValueError(f"Row {row_number} is not a complete UTC daily candle")
        day = dt.datetime.fromtimestamp(open_time / scale, dt.timezone.utc).date()
        if day in values:
            raise ValueError(f"Duplicate Binance candle date: {day}")

        open_price, high, low, close = (
            _finite(row, 1, "open", row_number),
            _finite(row, 2, "high", row_number),
            _finite(row, 3, "low", row_number),
            _finite(row, 4, "close", row_number),
        )
        volume = _finite(row, 5, "base volume", row_number)
        quote_volume = _finite(row, 7, "quote volume", row_number)
        trade_count = _finite(row, 8, "trade count", row_number)
        taker_buy_base = _finite(row, 9, "taker-buy base volume", row_number)
        taker_buy_quote = _finite(row, 10, "taker-buy quote volume", row_number)
        if min(open_price, high, low, close) <= 0 or low > min(open_price, close) or high < max(open_price, close) or low > high:
            raise ValueError(f"Invalid OHLC relationship at row {row_number}")
        if volume < 0 or quote_volume < 0 or trade_count < 0 or int(trade_count) != trade_count:
            raise ValueError(f"Invalid volume/trade-count field at row {row_number}")
        tolerance = max(1e-12, volume * 1e-10)
        if taker_buy_base < -tolerance or taker_buy_base > volume + tolerance:
            raise ValueError(f"Taker-buy base volume outside total base volume at row {row_number}")
        quote_tolerance = max(1e-8, quote_volume * 1e-10)
        if taker_buy_quote < -quote_tolerance or taker_buy_quote > quote_volume + quote_tolerance:
            raise ValueError(f"Taker-buy quote volume outside total quote volume at row {row_number}")
        if (trade_count == 0 and (volume > 0 or quote_volume > 0)) or (trade_count > 0 and volume == 0):
            raise ValueError(f"Inconsistent volume and trade count at row {row_number}")
        imbalance = None if volume == 0 else 2.0 * taker_buy_base / volume - 1.0
        if imbalance is not None and not -1.000000001 <= imbalance <= 1.000000001:
            raise ValueError(f"Taker imbalance outside [-1,1] at row {row_number}")
        values[day] = {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": quote_volume,
            "trade_count": int(trade_count),
            "taker_buy_base_volume": taker_buy_base,
            "taker_buy_quote_volume": taker_buy_quote,
            "taker_imbalance": imbalance,
        }
        units.add(unit)
    if not values:
        raise ValueError("Binance archive contains no kline observations")
    if len(units) != 1:
        raise ValueError(f"Mixed timestamp units within one archive: {sorted(units)}")
    return dict(sorted(values.items())), next(iter(units))


def download_archive(spec: dict) -> tuple[dict[dt.date, dict], dict]:
    payload = market.base.fetch_bytes(spec["url"], timeout=30)
    checksum_body = market.base.fetch_bytes(spec["url"] + ".CHECKSUM", timeout=15)
    expected_sha = market.parse_checksum(checksum_body, spec["filename"])
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(
            f"Binance Vision checksum mismatch for {spec['filename']}: "
            f"expected={expected_sha}, actual={actual_sha}"
        )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {spec['filename']}; found {len(csv_names)}")
        csv_body = archive.read(csv_names[0])
    rows, timestamp_unit = parse_kline_archive(csv_body)
    if spec["kind"] == "daily" and set(rows) != {dt.date.fromisoformat(spec["expected_date"])}:
        raise ValueError(f"Daily archive {spec['filename']} does not contain its exact expected date")
    if spec["kind"] == "monthly":
        year, month = map(int, spec["tag"].split("-"))
        if any(day.year != year or day.month != month for day in rows):
            raise ValueError(f"Monthly archive {spec['filename']} contains out-of-month rows")
    return rows, {
        "kind": spec["kind"],
        "period": spec["tag"],
        "url": spec["url"],
        "checksum_url": spec["url"] + ".CHECKSUM",
        "archive_sha256": actual_sha,
        "checksum_sha256": hashlib.sha256(checksum_body).hexdigest(),
        "checksum_verified": True,
        "rows": len(rows),
        "timestamp_unit": timestamp_unit,
        "first_date": min(rows).isoformat(),
        "last_date": max(rows).isoformat(),
    }


def validate_coverage(\n    rows: dict[dt.date, dict], start: dt.date, end: dt.date, min_nonzero_rows: int = 3000\n) -> dict:
    expected_days = (end - start).days + 1
    expected = {start + dt.timedelta(days=i) for i in range(expected_days)}
    observed = set(rows)
    missing = sorted(expected - observed)
    outside = sorted(observed - expected)
    if missing or outside:
        raise ValueError(
            f"Daily kline coverage mismatch: missing={len(missing)} first_missing="
            f"{missing[0] if missing else None}; outside={len(outside)}"
        )
    zero_volume = sum(row["volume"] == 0 for row in rows.values())
    nonzero = [row["taker_imbalance"] for row in rows.values() if row["taker_imbalance"] is not None]
    if len(nonzero) < min_nonzero_rows:
        raise ValueError(f"Insufficient nonzero-volume taker-flow observations: {len(nonzero)} < {min_nonzero_rows}")
    return {
        "expected_daily_rows": expected_days,
        "observed_daily_rows": len(rows),
        "first_date": min(rows).isoformat(),
        "last_date": max(rows).isoformat(),
        "missing_dates": [],
        "zero_volume_days": zero_volume,
        "nonzero_volume_days": len(nonzero),
        "taker_imbalance_min": min(nonzero),
        "taker_imbalance_median": sorted(nonzero)[len(nonzero) // 2],
        "taker_imbalance_max": max(nonzero),
    }


def fetch_all_archives(start: dt.date = START_DATE, end: dt.date = END_DATE) -> tuple[dict, dict]:
    specs = market.build_archive_specs(start, end, dt.datetime.now(dt.timezone.utc).date())
    rows: dict[dt.date, dict] = {}
    manifests: list[dict] = []
    failures: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        future_map = {pool.submit(download_archive, spec): spec for spec in specs}
        for future in concurrent.futures.as_completed(future_map):
            spec = future_map[future]
            try:
                part, record = future.result()
                part = {day: value for day, value in part.items() if start <= day <= end}
                overlap = set(rows).intersection(part)
                if overlap:
                    raise ValueError(f"Duplicate dates across archives: {sorted(overlap)[:3]}")
                rows.update(part)
                manifests.append(record)
            except Exception as exc:
                failures.append({
                    "period": spec["tag"],
                    "url": spec["url"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    manifests.sort(key=lambda item: item["period"])
    if failures:
        raise RuntimeError(
            f"{len(failures)} Binance archives failed; first failures: {failures[:5]}"
        )
    coverage = validate_coverage(rows, start, end)
    manifest_payload = json.dumps(manifests, sort_keys=True, separators=(",", ":")).encode()
    return rows, {
        "source": "Binance Vision official Spot monthly/daily 1d klines",
        "symbol": "BTCUSDT",
        "interval": "1d UTC",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "archive_count": len(manifests),
        "archive_manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "archives": manifests,
        "coverage": coverage,
        "raw_observations_saved": False,
    }


def run_preflight() -> dict:
    rows, source = fetch_all_archives()
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS",
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": source,
        "feature_definition": (
            "taker_imbalance = 2*taker_buy_base_volume/base_volume - 1; "
            "signed_absorption = max(imbalance,0)*max(-return,0) - "
            "max(-imbalance,0)*max(return,0)"
        ),
        "feature_observations": sum(row["taker_imbalance"] is not None for row in rows.values()),
        "backtest_run": False,
        "raw_observations_saved": False,
    }


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "FAIL",
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "backtest_run": False,
            "raw_observations_saved": False,
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "preflight.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("# Taker-absorption source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: `{HYPOTHESIS_ID}`\n")
            handle.write("- Backtest executed: **No**\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
