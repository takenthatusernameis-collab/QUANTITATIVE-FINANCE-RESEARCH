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
from datetime import datetime, timedelta, timezone
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
RETENTION_POLICY = (
    "GitHub Release asset; no automatic Actions-artifact expiry; not platform-immutable; "
    "may be deleted with the release or repository"
)
LEGACY_RELEASE_BODY = (
    "Append-only, immutable snapshots of public Binance Spot 1h ETHUSDT/BTCUSDT data. "
    "Each ZIP includes per-symbol CSVs and a SHA-256 manifest. No strategy evaluation "
    "or trading is performed by this archive."
)
RELEASE_BODY = (
    "Append-only by workflow policy: public Binance Spot 1h ETHUSDT/BTCUSDT snapshots. "
    "Each ZIP contains per-symbol CSVs; a separate JSON sidecar records the post-upload "
    "ZIP asset ID, URL, digest and per-file hashes. GitHub Release assets have no automatic "
    "Actions-artifact expiry but are not platform-immutable and may be deleted by repository "
    "maintainers. No strategy evaluation or trading is performed by this archive."
)
COLUMNS = (
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote", "ignore",
)


def iso_utc(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def latest_closed_hour_open_ms(now_ms: int) -> int:
    """Return the open timestamp of the latest bar whose close time has passed."""
    return (int(now_ms) // HOUR_MS) * HOUR_MS - HOUR_MS


def capture_slot(now_ms: int) -> dict[str, str]:
    """Identify the latest daily UTC slot whose 04:23 UTC due time has elapsed."""
    now = datetime.fromtimestamp(int(now_ms) / 1000, tz=timezone.utc)
    due = now.replace(hour=4, minute=23, second=0, microsecond=0)
    if now < due:
        due -= timedelta(days=1)
    slot_date = due.date().isoformat()
    return {
        "date": slot_date,
        "id": f"binance-spot-1h:prospective-2026-11:{slot_date}",
        "due_at_utc": due.isoformat().replace("+00:00", "Z"),
    }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


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
    if not asset.get("id") or not asset.get("browser_download_url") or not asset.get("created_at"):
        raise ValueError("Previous release asset metadata is incomplete")
    expected_digest = asset.get("digest")
    if not isinstance(expected_digest, str) or not expected_digest.startswith("sha256:"):
        raise ValueError("Previous release asset has no GitHub SHA-256 digest")
    download = session.get(asset["browser_download_url"], timeout=60)
    download.raise_for_status()
    payload = download.content
    if asset.get("size") is None or len(payload) != asset["size"]:
        raise ValueError("Previous release asset size does not match GitHub metadata")
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
        "asset_id": asset["id"],
        "asset_url": asset["browser_download_url"],
        "asset_size_bytes": asset["size"],
        "asset_created_at": asset["created_at"],
        "asset_digest": expected_digest,
        "archive_sha256": sha256_bytes(payload),
        "platform_immutable": bool(release.get("immutable", False)),
        "manifest": manifest,
        "rows": previous_rows,
    }


def build_durable_sidecar(manifest: dict[str, Any]) -> bytes:
    """Serialize a compact manifest only after ZIP identity and every file hash are known."""
    storage = manifest.get("storage")
    required_storage = ("asset_id", "asset_name", "asset_url", "asset_digest", "archive_sha256")
    if not isinstance(storage, dict) or any(storage.get(key) in (None, "") for key in required_storage):
        raise ValueError("Durable sidecar requires verified ZIP asset ID, URL and digest")
    if not isinstance(storage.get("asset_id"), int) or storage["asset_id"] <= 0:
        raise ValueError("Durable sidecar requires a positive GitHub asset ID")
    if not isinstance(storage.get("asset_url"), str) or not storage["asset_url"].startswith("https://"):
        raise ValueError("Durable sidecar requires an HTTPS ZIP asset URL")
    archive_sha = storage.get("archive_sha256")
    asset_digest = storage.get("asset_digest")
    if not is_sha256_hex(archive_sha) or asset_digest != f"sha256:{archive_sha}":
        raise ValueError("Durable sidecar ZIP digest fields are invalid or inconsistent")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Durable sidecar requires per-file SHA-256 records")
    if any(
        not isinstance(record, dict) or not is_sha256_hex(record.get("sha256"))
        for record in files.values()
    ):
        raise ValueError("Durable sidecar contains a missing or invalid per-file SHA-256 hash")
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def publish_release_asset(
    session: requests.Session,
    repo: str,
    token: str,
    release_tag: str,
    asset_name: str,
    zip_bytes: bytes,
    content_type: str = "application/zip",
) -> dict[str, Any]:
    """Create or reuse a uniquely named release asset with exact size/digest verification."""
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
                "body": RELEASE_BODY,
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
        if release.get("body") == LEGACY_RELEASE_BODY and not release.get("immutable", False):
            patch = session.patch(
                f"{API_ROOT}/repos/{repo}/releases/{release['id']}",
                headers=headers,
                json={"body": RELEASE_BODY},
                timeout=30,
            )
            patch.raise_for_status()
            release = patch.json()

    existing = next(
        (asset for asset in release.get("assets", []) if asset.get("name") == asset_name),
        None,
    )
    expected_sha = sha256_bytes(zip_bytes)
    if existing:
        if (
            existing.get("digest") == f"sha256:{expected_sha}"
            and existing.get("size") == len(zip_bytes)
            and existing.get("id")
            and existing.get("browser_download_url")
            and existing.get("created_at")
        ):
            return {
                "asset_id": existing["id"],
                "asset_name": existing["name"],
                "asset_url": existing["browser_download_url"],
                "asset_size_bytes": existing["size"],
                "asset_created_at": existing["created_at"],
                "asset_digest": existing["digest"],
                "platform_immutable": bool(release.get("immutable", False)),
                "idempotent_reuse": True,
            }
        raise RuntimeError(f"Release asset name collision or incomplete metadata: {asset_name}")

    upload_url = release.get("upload_url", "").split("{", 1)[0]
    if not upload_url:
        raise RuntimeError("GitHub release response did not include upload_url")
    upload = session.post(
        upload_url,
        params={"name": asset_name},
        headers={**headers, "Content-Type": content_type},
        data=zip_bytes,
        timeout=120,
    )
    upload.raise_for_status()
    uploaded = upload.json()

    verify = session.get(release_url, headers=headers, timeout=30)
    verify.raise_for_status()
    verified_release = verify.json()
    verified_asset = next(
        (asset for asset in verified_release.get("assets", []) if asset.get("name") == asset_name),
        None,
    )
    if not verified_asset:
        raise RuntimeError("Uploaded release asset is not visible after upload")
    if verified_asset.get("size") != len(zip_bytes):
        raise RuntimeError("Uploaded release asset size differs from local bytes")
    digest = verified_asset.get("digest")
    if digest != f"sha256:{expected_sha}":
        raise RuntimeError("Uploaded release asset GitHub SHA-256 digest is missing or differs")
    if not verified_asset.get("id") or not verified_asset.get("browser_download_url") or not verified_asset.get("created_at"):
        raise RuntimeError("Uploaded release asset metadata is incomplete")
    return {
        "asset_id": verified_asset["id"] or uploaded.get("id"),
        "asset_name": asset_name,
        "asset_url": verified_asset["browser_download_url"],
        "asset_size_bytes": verified_asset["size"],
        "asset_created_at": verified_asset["created_at"],
        "asset_digest": digest,
        "platform_immutable": bool(verified_release.get("immutable", False)),
        "idempotent_reuse": False,
    }


def publish_snapshot_sidecar(
    session: requests.Session,
    repo: str,
    token: str,
    previous: dict[str, Any],
) -> dict[str, Any]:
    """Backfill a durable metadata sidecar for an already-published ZIP snapshot."""
    sidecar_name = previous["asset_name"].removesuffix(".zip") + ".manifest.json"
    previous_manifest = dict(previous["manifest"])
    previous_manifest["storage"] = {
        "asset_id": previous["asset_id"],
        "asset_name": previous["asset_name"],
        "asset_url": previous["asset_url"],
        "asset_size_bytes": previous["asset_size_bytes"],
        "asset_created_at": previous["asset_created_at"],
        "asset_digest": previous["asset_digest"],
        "archive_sha256": previous["archive_sha256"],
        "verified_at_utc": previous.get("asset_created_at") or previous_manifest.get("acquired_at_utc"),
        "release_tag": RELEASE_TAG,
        "retention_policy": RETENTION_POLICY,
        "minimum_retention_days": 180,
        "platform_immutable": previous.get("platform_immutable", False),
        "sidecar_asset_name": sidecar_name,
    }
    payload = build_durable_sidecar(previous_manifest)
    return publish_release_asset(
        session=session,
        repo=repo,
        token=token,
        release_tag=RELEASE_TAG,
        asset_name=sidecar_name,
        zip_bytes=payload,
        content_type="application/json",
    )


def load_existing_slot_snapshot(
    session: requests.Session,
    repo: str,
    release_tag: str,
    slot: dict[str, str],
    token: str | None = None,
) -> dict[str, Any] | None:
    """Return a fully hash-verified snapshot already published for this UTC slot.

    The workflow concurrency group serializes capture jobs. The stable slot asset
    name then makes a second wake-up/run observe and reuse the first result rather
    than publish a duplicate. An incomplete first result is still returned as
    incomplete; it is not silently overwritten or retried without diagnosis.
    """
    headers = {"Accept": "application/vnd.github+json"}
    release_url = f"{API_ROOT}/repos/{repo}/releases/tags/{release_tag}"
    response = session.get(release_url, headers=headers, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    release = response.json()

    asset_name = f"snapshot-slot-{slot['date']}.zip"
    sidecar_name = f"snapshot-slot-{slot['date']}.manifest.json"
    asset = next(
        (item for item in release.get("assets", []) if item.get("name") == asset_name),
        None,
    )
    if asset is None:
        return None
    if (
        asset.get("state") != "uploaded"
        or not asset.get("id")
        or not asset.get("browser_download_url")
        or not asset.get("created_at")
        or not asset.get("size")
    ):
        raise ValueError("Existing capture-slot ZIP metadata is incomplete")
    digest = asset.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ValueError("Existing capture-slot ZIP has no GitHub SHA-256 digest")

    zip_response = session.get(asset["browser_download_url"], headers={"Accept": "application/octet-stream"}, timeout=120)
    zip_response.raise_for_status()
    zip_payload = zip_response.content
    archive_sha = sha256_bytes(zip_payload)
    if len(zip_payload) != asset["size"] or digest != f"sha256:{archive_sha}":
        raise ValueError("Existing capture-slot ZIP size or digest does not match GitHub metadata")

    with zipfile.ZipFile(io.BytesIO(zip_payload)) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        if (
            manifest.get("schema_version") != SCHEMA_VERSION
            or manifest.get("capture_type") != "prospective_binance_spot_hourly"
            or manifest.get("market") != "spot"
            or manifest.get("interval") != INTERVAL
            or manifest.get("capture_slot_id") != slot["id"]
            or manifest.get("capture_slot_date_utc") != slot["date"]
            or manifest.get("capture_slot_due_at_utc") != slot["due_at_utc"]
            or manifest.get("release_asset_name") != asset_name
            or manifest.get("storage", {}).get("sidecar_asset_name") != sidecar_name
        ):
            raise ValueError("Existing capture-slot ZIP manifest identity does not match its slot")
        for symbol in SYMBOLS:
            filename = f"spot_{symbol}_1h.csv"
            record = manifest.get("files", {}).get(filename)
            if filename not in names or not isinstance(record, dict):
                raise ValueError(f"Existing capture-slot ZIP is missing {filename}")
            payload = archive.read(filename)
            if sha256_bytes(payload) != record.get("sha256"):
                raise ValueError(f"Existing capture-slot CSV checksum mismatch: {filename}")
            read_csv_rows(payload)

    sidecar = next(
        (item for item in release.get("assets", []) if item.get("name") == sidecar_name),
        None,
    )
    if sidecar is None:
        # The ZIP may have been durably published immediately before an interrupted
        # process stopped. Reconstruct the metadata-only sidecar from the verified ZIP
        # and GitHub's independently checked asset metadata; never re-fetch or replace
        # market data merely to repair this second-stage publication.
        if not token:
            raise ValueError("Existing capture-slot sidecar is missing and no authorized token is available for safe recovery")
        recovered_manifest = dict(manifest)
        recovered_manifest["storage"] = {
            "asset_id": asset["id"],
            "asset_name": asset_name,
            "asset_url": asset["browser_download_url"],
            "asset_size_bytes": asset["size"],
            "asset_created_at": asset["created_at"],
            "asset_digest": digest,
            "archive_sha256": archive_sha,
            "verified_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "release_tag": release_tag,
            "retention_policy": RETENTION_POLICY,
            "minimum_retention_days": 180,
            "platform_immutable": bool(release.get("immutable", False)),
            "sidecar_asset_name": sidecar_name,
            "sidecar_reconstructed_from_verified_zip": True,
        }
        recovered_payload = build_durable_sidecar(recovered_manifest)
        recovered = publish_release_asset(
            session=session,
            repo=repo,
            token=token,
            release_tag=release_tag,
            asset_name=sidecar_name,
            zip_bytes=recovered_payload,
            content_type="application/json",
        )
        sidecar = {
            "state": "uploaded",
            "id": recovered["asset_id"],
            "name": recovered["asset_name"],
            "browser_download_url": recovered["asset_url"],
            "size": recovered["asset_size_bytes"],
            "digest": recovered["asset_digest"],
        }
    if (
        sidecar.get("state") != "uploaded"
        or not sidecar.get("id")
        or not sidecar.get("browser_download_url")
        or not sidecar.get("size")
        or not isinstance(sidecar.get("digest"), str)
        or not sidecar["digest"].startswith("sha256:")
    ):
        raise ValueError("Existing capture-slot sidecar has incomplete metadata")
    sidecar_response = session.get(
        sidecar["browser_download_url"],
        headers={"Accept": "application/json"},
        timeout=30,
    )
    sidecar_response.raise_for_status()
    sidecar_payload = sidecar_response.content
    if len(sidecar_payload) != sidecar["size"] or sidecar["digest"] != f"sha256:{sha256_bytes(sidecar_payload)}":
        raise ValueError("Existing capture-slot sidecar size or digest does not match GitHub metadata")
    sidecar_manifest = json.loads(sidecar_payload.decode("utf-8"))
    sidecar_storage = sidecar_manifest.get("storage", {})
    if (
        sidecar_manifest.get("capture_slot_id") != slot["id"]
        or sidecar_manifest.get("files") != manifest.get("files")
        or sidecar_storage.get("asset_id") != asset["id"]
        or sidecar_storage.get("asset_name") != asset_name
        or sidecar_storage.get("asset_digest") != digest
        or sidecar_storage.get("archive_sha256") != archive_sha
        or sidecar_storage.get("sidecar_asset_name") != sidecar_name
    ):
        raise ValueError("Existing capture-slot sidecar does not reconcile to its ZIP and manifest")

    manifest["storage"] = {
        **sidecar_storage,
        "sidecar_asset_id": sidecar["id"],
        "sidecar_asset_name": sidecar_name,
        "sidecar_asset_url": sidecar["browser_download_url"],
        "sidecar_asset_size_bytes": sidecar["size"],
        "sidecar_asset_digest": sidecar["digest"],
        "sidecar_idempotent_reuse": True,
        "platform_immutable": bool(release.get("immutable", False)),
    }
    manifest["idempotent_slot_reuse"] = True
    return manifest


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
    slot = capture_slot(now_ms)
    existing_slot = load_existing_slot_snapshot(session, repo, RELEASE_TAG, slot, token=token)
    if existing_slot is not None:
        existing_slot["idempotent_slot_reuse"] = True
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(existing_slot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return existing_slot

    end_open_ms = latest_closed_hour_open_ms(now_ms)
    if end_open_ms < CAPTURE_START_MS:
        raise ValueError("Current time precedes the prospective capture start")
    asset_name = f"snapshot-slot-{slot['date']}.zip"
    sidecar_name = f"snapshot-slot-{slot['date']}.manifest.json"
    previous = load_previous_snapshot(session, repo, RELEASE_TAG, asset_name)
    previous_sidecar = publish_snapshot_sidecar(session, repo, token, previous) if previous else None

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
        "capture_slot_id": slot["id"],
        "capture_slot_date_utc": slot["date"],
        "capture_slot_due_at_utc": slot["due_at_utc"],
        "capture_trigger_event": os.environ.get("GITHUB_EVENT_NAME", "direct"),
        "run_id": str(run_id),
        "run_attempt": str(run_attempt),
        "commit_sha": commit_sha or None,
        "files": {},
        "storage": {
            "release_tag": RELEASE_TAG,
            "asset_name": asset_name,
            "sidecar_asset_name": sidecar_name,
            "retention_policy": RETENTION_POLICY,
            "minimum_retention_days": 180,
            "platform_immutable": previous.get("platform_immutable", False) if previous else False,
        },
    }
    if previous:
        manifest["previous_snapshot"] = {
            "asset_name": previous["asset_name"],
            "asset_id": previous["asset_id"],
            "asset_url": previous["asset_url"],
            "asset_digest": previous["asset_digest"],
            "asset_created_at": previous["asset_created_at"],
            "archive_sha256": previous["archive_sha256"],
            "sidecar_asset": previous_sidecar,
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
        content_type="application/zip",
    )
    manifest["storage"] = {
        **storage,
        "release_tag": RELEASE_TAG,
        "archive_sha256": sha256_bytes(zip_bytes),
        "verified_at_utc": storage.get("asset_created_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "retention_policy": RETENTION_POLICY,
        "minimum_retention_days": 180,
        "platform_immutable": storage.get("platform_immutable", False),
        "sidecar_asset_name": sidecar_name,
    }
    sidecar_bytes = build_durable_sidecar(manifest)
    sidecar_storage = publish_release_asset(
        session=session,
        repo=repo,
        token=token,
        release_tag=RELEASE_TAG,
        asset_name=sidecar_name,
        zip_bytes=sidecar_bytes,
        content_type="application/json",
    )
    manifest["storage"].update({
        "sidecar_asset_id": sidecar_storage["asset_id"],
        "sidecar_asset_name": sidecar_storage["asset_name"],
        "sidecar_asset_url": sidecar_storage["asset_url"],
        "sidecar_asset_size_bytes": sidecar_storage["asset_size_bytes"],
        "sidecar_asset_digest": sidecar_storage["asset_digest"],
        "sidecar_idempotent_reuse": sidecar_storage["idempotent_reuse"],
    })
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
        "idempotent_slot_reuse": bool(manifest.get("idempotent_slot_reuse", False)),
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
