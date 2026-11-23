#!/usr/bin/env python3
"""Prospective-only Binance Spot ETH/BTC hourly holdout capture.

Every run re-requests the prospective capture window from 2026-11-01 through
the latest fully closed UTC hour. This bounded hourly series makes missed-run
recovery and revision detection deterministic without relying on an evictable
Actions cache. Raw snapshots are published as append-only
GitHub Release assets; Actions artifacts contain manifests only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_URL = "https://data-api.binance.vision/api/v3/klines"
API_ROOT = "https://api.github.com"
RELEASE_TAG = "spot-holdout-2026"
AUTHORIZED_REPOSITORY = "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"
SYMBOLS = ("ETHUSDT", "BTCUSDT")
INTERVAL = "1h"
HOUR_MS = 3_600_000
CAPTURE_START_MS = 1_793_491_200_000  # 2026-11-01T00:00:00Z
MAX_LIMIT = 1000
MAX_ATTEMPTS = 4
RETRYABLE = {429, 500, 502, 503, 504}
SCHEMA_VERSION = 1
COLUMNS = (
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote", "ignore",
)


def iso_utc(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def latest_closed_hour_open_ms(now_ms: int) -> int:
    """Return the open timestamp of the latest bar whose close time has passed."""
    return (int(now_ms) // HOUR_MS) * HOUR_MS - HOUR_MS


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Snapshot timestamp must include a UTC offset")
    return int(parsed.timestamp() * 1000)


def row_sha256(row: list[str]) -> str:
    return sha256_bytes(json.dumps(row, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def normalize_row(row: Any) -> list[str]:
    if not isinstance(row, (list, tuple)) or len(row) != len(COLUMNS):
        raise ValueError(f"Expected exactly {len(COLUMNS)} Binance kline fields")
    return [str(value) for value in row]


def validate_rows(
    rows: list[Any],
    symbol: str,
    start_ms: int,
    end_open_ms: int,
    now_ms: int,
) -> dict[str, Any]:
    """Validate one symbol's source rows and report every missing expected hour."""
    normalized = [normalize_row(row) for row in rows]
    open_times: list[int] = []
    for row in normalized:
        try:
            open_ms = int(row[0])
            close_ms = int(row[6])
            prices = [float(row[i]) for i in (1, 2, 3, 4)]
            volumes = [float(row[i]) for i in (5, 7, 9, 10)]
            trade_count = int(row[8])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{symbol}: invalid numeric kline field") from exc

        if open_ms % HOUR_MS != 0:
            raise ValueError(f"{symbol}: non-hour-aligned UTC open time {open_ms}")
        if open_ms < start_ms or open_ms > end_open_ms:
            raise ValueError(f"{symbol}: kline open time outside requested bounds: {open_ms}")
        if close_ms != open_ms + HOUR_MS - 1:
            raise ValueError(f"{symbol}: invalid hourly close time for {open_ms}")
        if close_ms >= now_ms:
            raise ValueError(f"{symbol}: unclosed/future kline rejected: {open_ms}")
        if not all(math.isfinite(value) and value > 0 for value in prices):
            raise ValueError(f"{symbol}: invalid OHLC price for {open_ms}")
        if prices[1] < max(prices[0], prices[2], prices[3]):
            raise ValueError(f"{symbol}: high is below an OHLC value for {open_ms}")
        if prices[2] > min(prices[0], prices[1], prices[3]):
            raise ValueError(f"{symbol}: low is above an OHLC value for {open_ms}")
        if not all(math.isfinite(value) and value >= 0 for value in volumes):
            raise ValueError(f"{symbol}: invalid volume field for {open_ms}")
        if trade_count < 0:
            raise ValueError(f"{symbol}: negative trade count for {open_ms}")
        open_times.append(open_ms)

    if len(open_times) != len(set(open_times)):
        raise ValueError(f"{symbol}: duplicate source timestamps")
    if open_times != sorted(open_times):
        raise ValueError(f"{symbol}: source timestamps are not sorted")

    expected = list(range(start_ms, end_open_ms + 1, HOUR_MS))
    observed = set(open_times)
    missing = [timestamp for timestamp in expected if timestamp not in observed]
    return {
        "symbol": symbol,
        "requested_start_utc": iso_utc(start_ms),
        "requested_end_open_utc": iso_utc(end_open_ms),
        "observed_start_utc": iso_utc(open_times[0]) if open_times else None,
        "observed_end_open_utc": iso_utc(open_times[-1]) if open_times else None,
        "expected_rows": len(expected),
        "observed_rows": len(normalized),
        "missing_hour_count": len(missing),
        "missing_hour_utc": [iso_utc(value) for value in missing],
        "duplicate_timestamps": 0,
        "sorted": True,
        "closed_bars_only": True,
        "complete": bool(normalized) and not missing,
    }


def fetch_klines(
    session: requests.Session,
    symbol: str,
    start_ms: int,
    end_open_ms: int,
) -> list[list[str]]:
    """Fetch the full bounded history with strict pagination and no host fallback."""
    rows: list[list[str]] = []
    cursor = start_ms
    end_close_ms = end_open_ms + HOUR_MS - 1
    while cursor <= end_open_ms:
        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "startTime": cursor,
            "endTime": end_close_ms,
            "limit": MAX_LIMIT,
        }
        payload = request_json(session, API_URL, params=params, timeout=30)
        if not isinstance(payload, list):
            raise ValueError(f"{symbol}: Binance response is not a kline list")
        if not payload:
            break
        if len(payload) > MAX_LIMIT:
            raise ValueError(f"{symbol}: Binance exceeded the requested page limit")
        batch = [normalize_row(row) for row in payload]
        times = [int(row[0]) for row in batch]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError(f"{symbol}: unordered or duplicate page")
        if times[0] < cursor or times[-1] > end_open_ms:
            raise ValueError(f"{symbol}: response escaped requested bounds")
        rows.extend(batch)
        next_cursor = times[-1] + HOUR_MS
        if next_cursor <= cursor:
            raise ValueError(f"{symbol}: pagination made no progress")
        cursor = next_cursor
        if len(batch) < MAX_LIMIT:
            break
    return rows


def request_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> Any:
    """Retry only transient transport/rate/server errors; never bypass 4xx restrictions."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = session.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code in RETRYABLE and attempt < MAX_ATTEMPTS - 1:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2 ** attempt
                except (TypeError, ValueError):
                    delay = 2 ** attempt
                time.sleep(min(max(delay, 0), 10))
                continue
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in RETRYABLE or attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(min(2 ** attempt, 10))
        except requests.RequestException:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"Request failed after {MAX_ATTEMPTS} attempts: {url}")


def merge_rows(previous_rows: list[list[str]], incoming_rows: list[list[str]]) -> tuple[list[list[str]], list[dict[str, str]]]:
    """Merge by UTC open time; incoming official observations win and corrections are recorded."""
    merged = {int(row[0]): list(row) for row in previous_rows}
    corrections: list[dict[str, str]] = []
    for raw in incoming_rows:
        row = normalize_row(raw)
        timestamp = int(row[0])
        old = merged.get(timestamp)
        if old is not None and old != row:
            corrections.append({
                "timestamp_utc": iso_utc(timestamp),
                "previous_row_sha256": row_sha256(old),
                "replacement_row_sha256": row_sha256(row),
            })
        merged[timestamp] = row
    return [merged[key] for key in sorted(merged)], corrections


def rows_to_csv(rows: list[list[str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def read_csv_rows(payload: bytes) -> list[list[str]]:
    stream = io.StringIO(payload.decode("utf-8"), newline="")
    reader = csv.DictReader(stream)
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError("Previous snapshot has an unexpected CSV schema")
    return [[str(record[column]) for column in COLUMNS] for record in reader]


def load_previous_snapshot(
    session: requests.Session,
    repo: str,
    release_tag: str,
    current_asset_name: str,
) -> dict[str, Any] | None:
    """Load and hash-check the newest prior immutable release snapshot."""
    url = f"{API_ROOT}/repos/{repo}/releases/tags/{release_tag}"
    response = session.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    release = response.json()
    candidates = [
        asset for asset in release.get("assets", [])
        if asset.get("name", "").startswith("snapshot-")
        and asset.get("name", "").endswith(".zip")
        and asset.get("name") != current_asset_name
        and asset.get("state") == "uploaded"
    ]
    if not candidates:
        return None
    asset = max(candidates, key=lambda item: (item.get("created_at", ""), item.get("id", 0)))
    download = session.get(asset["browser_download_url"], timeout=60)
    download.raise_for_status()
    payload = download.content
    expected_digest = asset.get("digest")
    if expected_digest and expected_digest.startswith("sha256:"):
        if sha256_bytes(payload) != expected_digest.split(":", 1)[1]:
            raise ValueError("Previous release asset digest does not match GitHub metadata")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Previous snapshot manifest schema is unsupported")
        if (
            manifest.get("capture_type") != "prospective_binance_spot_hourly"
            or manifest.get("market") != "spot"
            or manifest.get("interval") != INTERVAL
        ):
            raise ValueError("Previous release asset is not a compatible Spot holdout snapshot")
        previous_start = parse_utc_ms(manifest["requested_start_utc"])
        previous_end = parse_utc_ms(manifest["requested_end_open_utc"])
        if previous_start != CAPTURE_START_MS:
            raise ValueError("Previous snapshot has a different prospective start")
        if manifest.get("status") == "COMPLETE" and manifest.get("data_quality_complete") is not True:
            raise ValueError("Previous COMPLETE snapshot is not marked accepted")
        if manifest.get("status") != "COMPLETE" and manifest.get("data_quality_complete") is True:
            raise ValueError("Previous incomplete snapshot is incorrectly marked accepted")
        previous_now = int(datetime.now(timezone.utc).timestamp() * 1000)
        previous_rows: dict[str, list[list[str]]] = {}
        for symbol in SYMBOLS:
            filename = f"spot_{symbol}_1h.csv"
            csv_bytes = archive.read(filename)
            record = manifest.get("files", {}).get(filename, {})
            if sha256_bytes(csv_bytes) != record.get("sha256"):
                raise ValueError(f"Previous snapshot checksum mismatch: {filename}")
            rows = read_csv_rows(csv_bytes)
            quality = validate_rows(
                rows, symbol, previous_start, previous_end, previous_now
            )
            if manifest.get("status") == "COMPLETE" and not quality["complete"]:
                raise ValueError(f"Previous snapshot claims COMPLETE but fails validation: {filename}")
            previous_rows[symbol] = rows
    return {
        "asset_name": asset["name"],
        "asset_id": asset.get("id"),
        "asset_created_at": asset.get("created_at"),
        "asset_digest": expected_digest,
        "archive_sha256": sha256_bytes(payload),
        "manifest": manifest,
        "rows": previous_rows,
    }


def publish_release_asset(
    session: requests.Session,
    repo: str,
    token: str,
    release_tag: str,
    asset_name: str,
    zip_bytes: bytes,
) -> dict[str, Any]:
    """Create the durable release if needed, append one immutable snapshot and verify it."""
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for release-asset storage")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    release_url = f"{API_ROOT}/repos/{repo}/releases/tags/{release_tag}"
    response = session.get(release_url, headers=headers, timeout=30)
    if response.status_code == 404:
        create = session.post(
            f"{API_ROOT}/repos/{repo}/releases",
            headers=headers,
            json={
                "tag_name": release_tag,
                "target_commitish": "main",
                "name": "Prospective Binance Spot ETH/BTC holdout — 2026",
                "body": (
                    "Append-only, immutable snapshots of public Binance Spot 1h ETHUSDT/BTCUSDT data. "
                    "Each ZIP includes per-symbol CSVs and a SHA-256 manifest. No strategy evaluation "
                    "or trading is performed by this archive."
                ),
                "draft": False,
                "prerelease": False,
            },
            timeout=30,
        )
        create.raise_for_status()
        release = create.json()
    else:
        response.raise_for_status()
        release = response.json()

    existing = next(
        (asset for asset in release.get("assets", []) if asset.get("name") == asset_name),
        None,
    )
    expected_sha = sha256_bytes(zip_bytes)
    if existing:
        if existing.get("digest") == f"sha256:{expected_sha}":
            return {
                "asset_id": existing.get("id"),
                "asset_name": existing.get("name"),
                "asset_url": existing.get("browser_download_url"),
                "asset_digest": existing.get("digest"),
                "idempotent_reuse": True,
            }
        raise RuntimeError(f"Release asset name collision with different bytes: {asset_name}")

    upload_url = release.get("upload_url", "").split("{", 1)[0]
    if not upload_url:
        raise RuntimeError("GitHub release response did not include upload_url")
    upload = session.post(
        upload_url,
        params={"name": asset_name},
        headers={**headers, "Content-Type": "application/zip"},
        data=zip_bytes,
        timeout=120,
    )
    upload.raise_for_status()
    uploaded = upload.json()

    verify = session.get(release_url, headers=headers, timeout=30)
    verify.raise_for_status()
    verified_asset = next(
        (asset for asset in verify.json().get("assets", []) if asset.get("name") == asset_name),
        None,
    )
    if not verified_asset:
        raise RuntimeError("Uploaded release asset is not visible after upload")
    if verified_asset.get("size") != len(zip_bytes):
        raise RuntimeError("Uploaded release asset size differs from local ZIP")
    digest = verified_asset.get("digest")
    if digest and digest != f"sha256:{expected_sha}":
        raise RuntimeError("Uploaded release asset digest differs from local ZIP")
    return {
        "asset_id": verified_asset.get("id", uploaded.get("id")),
        "asset_name": asset_name,
        "asset_url": verified_asset.get("browser_download_url"),
        "asset_digest": digest or f"sha256:{expected_sha}",
        "idempotent_reuse": False,
    }


def write_snapshot(
    output_dir: Path,
    repo: str,
    run_id: str,
    run_attempt: str,
    commit_sha: str,
    now_ms: int,
    session: requests.Session,
    token: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    end_open_ms = latest_closed_hour_open_ms(now_ms)
    if end_open_ms < CAPTURE_START_MS:
        raise ValueError("Current time precedes the prospective capture start")
    asset_name = f"snapshot-{run_id}-attempt-{run_attempt}.zip"
    previous = load_previous_snapshot(session, repo, RELEASE_TAG, asset_name)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "capture_type": "prospective_binance_spot_hourly",
        "status": "INCOMPLETE",
        "data_quality_complete": False,
        "research_evaluation_authorized": False,
        "market": "spot",
        "interval": INTERVAL,
        "symbols": {},
        "source": "Binance public Spot REST klines",
        "source_url": API_URL,
        "acquired_at_utc": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "requested_start_utc": iso_utc(CAPTURE_START_MS),
        "requested_end_open_utc": iso_utc(end_open_ms),
        "latest_closed_hour_open_utc": iso_utc(end_open_ms),
        "overlap_policy": "full bounded-window re-fetch from 2026-11-01; compare all prior timestamps and prefer current official observations",
        "minimum_storage_retention_days": 180,
        "capture_policy": "re-fetch the full prospective window from 2026-11-01 on every run; no automatic truncation",
        "previous_snapshot": None,
        "release_tag": RELEASE_TAG,
        "release_asset_name": asset_name,
        "run_id": str(run_id),
        "run_attempt": str(run_attempt),
        "commit_sha": commit_sha or None,
        "files": {},
        "storage": None,
    }
    if previous:
        manifest["previous_snapshot"] = {
            "asset_name": previous["asset_name"],
            "asset_id": previous["asset_id"],
            "asset_created_at": previous["asset_created_at"],
            "archive_sha256": previous["archive_sha256"],
        }

    all_complete = True
    csv_payloads: dict[str, bytes] = {}
    for symbol in SYMBOLS:
        error = None
        incoming: list[list[str]] = []
        try:
            incoming = fetch_klines(session, symbol, CAPTURE_START_MS, end_open_ms)
            quality = validate_rows(incoming, symbol, CAPTURE_START_MS, end_open_ms, now_ms)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            incoming = []
            expected_count = ((end_open_ms - CAPTURE_START_MS) // HOUR_MS) + 1
            quality = {
                "symbol": symbol,
                "requested_start_utc": iso_utc(CAPTURE_START_MS),
                "requested_end_open_utc": iso_utc(end_open_ms),
                "observed_start_utc": None,
                "observed_end_open_utc": None,
                "expected_rows": expected_count,
                "observed_rows": 0,
                "missing_hour_count": expected_count,
                "missing_hour_utc": [
                    iso_utc(CAPTURE_START_MS + i * HOUR_MS)
                    for i in range(expected_count)
                ],
                "duplicate_timestamps": None,
                "sorted": False,
                "closed_bars_only": False,
                "complete": False,
            }
        previous_rows = previous["rows"].get(symbol, []) if previous else []
        merged, corrections = merge_rows(previous_rows, incoming)
        incoming_times = {int(row[0]) for row in incoming}
        prior_only = sorted({int(row[0]) for row in previous_rows} - incoming_times)
        quality["source_error"] = error
        quality["overlap_correction_count"] = len(corrections)
        quality["overlap_corrections"] = corrections
        quality["prior_rows_missing_from_current_source"] = [iso_utc(value) for value in prior_only]
        quality["merged_rows"] = len(merged)
        quality["merged_missing_hour_count"] = max(0, quality["expected_rows"] - len(merged))
        quality["complete"] = bool(
            quality["complete"] and not error and not prior_only and quality["merged_missing_hour_count"] == 0
        )
        all_complete = all_complete and quality["complete"]

        filename = f"spot_{symbol}_1h.csv"
        payload = rows_to_csv(merged)
        csv_payloads[filename] = payload
        manifest["files"][filename] = {
            "sha256": sha256_bytes(payload),
            "rows": len(merged),
            "symbol": symbol,
            "interval": INTERVAL,
            "source_url": API_URL,
        }
        manifest["symbols"][symbol] = quality

    manifest["status"] = "COMPLETE" if all_complete else "INCOMPLETE"
    manifest["data_quality_complete"] = bool(all_complete)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    zip_path = output_dir / asset_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for filename, payload in csv_payloads.items():
            archive.writestr(filename, payload)
        archive.writestr("manifest.json", manifest_path.read_bytes())
    zip_bytes = zip_path.read_bytes()

    storage = publish_release_asset(
        session=session,
        repo=repo,
        token=token,
        release_tag=RELEASE_TAG,
        asset_name=asset_name,
        zip_bytes=zip_bytes,
    )
    manifest["storage"] = {
        **storage,
        "release_tag": RELEASE_TAG,
        "archive_sha256": sha256_bytes(zip_bytes),
        "verified_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "retention_policy": "GitHub Release asset; no Actions-artifact expiry; retained until explicitly deleted with the release or repository",
        "minimum_retention_days": 180,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", AUTHORIZED_REPOSITORY))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()

    if args.repo != AUTHORIZED_REPOSITORY:
        raise SystemExit(f"Repository is not allowlisted: {args.repo}")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for durable release-asset storage")

    session = requests.Session()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        manifest = write_snapshot(
            output_dir=Path(args.output_dir),
            repo=args.repo,
            run_id=str(args.run_id),
            run_attempt=str(args.run_attempt),
            commit_sha=args.commit_sha,
            now_ms=now_ms,
            session=session,
            token=token,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1
    print(json.dumps({
        "status": manifest["status"],
        "data_quality_complete": manifest["data_quality_complete"],
        "research_evaluation_authorized": manifest["research_evaluation_authorized"],
        "requested_start_utc": manifest["requested_start_utc"],
        "requested_end_open_utc": manifest["requested_end_open_utc"],
        "symbols": {
            symbol: {
                "rows": record["merged_rows"],
                "missing_hours": record["missing_hour_count"],
                "corrections": record["overlap_correction_count"],
                "source_error": record["source_error"],
                "complete": record["complete"],
            }
            for symbol, record in manifest["symbols"].items()
        },
        "storage": manifest["storage"],
    }, indent=2))
    return 0 if manifest["data_quality_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
