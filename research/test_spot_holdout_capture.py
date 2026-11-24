from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from spot_holdout_capture import (
    API_URL,
    COLUMNS,
    LEGACY_RELEASE_BODY,
    RELEASE_BODY,
    build_durable_sidecar,
    capture_slot,
    HOUR_MS,
    CAPTURE_START_MS,
    fetch_klines,
    latest_closed_hour_open_ms,
    load_previous_snapshot,
    merge_rows,
    publish_release_asset,
    publish_snapshot_sidecar,
    read_csv_rows,
    rows_to_csv,
    sha256_bytes,
    validate_rows,
    write_snapshot,
)


def make_row(open_ms: int, close: str = "2000", volume: str = "10") -> list[str]:
    return [
        str(open_ms), "1990", "2010", "1980", close, volume,
        str(open_ms + HOUR_MS - 1), "20000", "100", "5", "10000", "0",
    ]


class Response:
    def __init__(self, payload=None, status=200, content=b""):
        self._payload = payload
        self.status_code = status
        self.content = content
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._payload


class SpotHoldoutCaptureTests(unittest.TestCase):
    def test_latest_closed_hour_excludes_current_open_hour(self):
        now = CAPTURE_START_MS + 10 * HOUR_MS + 15 * 60_000
        self.assertEqual(latest_closed_hour_open_ms(now), CAPTURE_START_MS + 9 * HOUR_MS)

    def test_capture_slot_uses_first_daily_utc_due_time_that_has_elapsed(self):
        before = int(datetime(2026, 11, 24, 4, 22, tzinfo=timezone.utc).timestamp() * 1000)
        due = int(datetime(2026, 11, 24, 4, 23, tzinfo=timezone.utc).timestamp() * 1000)
        after = int(datetime(2026, 11, 24, 10, 5, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(capture_slot(before)["date"], "2026-11-23")
        self.assertEqual(capture_slot(due)["date"], "2026-11-24")
        self.assertEqual(capture_slot(after)["id"], "binance-spot-1h:prospective-2026-11:2026-11-24")
        self.assertEqual(capture_slot(after)["due_at_utc"], "2026-11-24T04:23:00Z")

    def test_validate_rows_accepts_sorted_closed_utc_bars(self):
        start = CAPTURE_START_MS
        rows = [make_row(start), make_row(start + HOUR_MS)]
        quality = validate_rows(rows, "ETHUSDT", start, start + HOUR_MS, start + 2 * HOUR_MS)
        self.assertTrue(quality["complete"])
        self.assertEqual(quality["observed_rows"], 2)
        self.assertEqual(quality["missing_hour_count"], 0)

    def test_gap_detection_does_not_fill_missing_hours(self):
        start = CAPTURE_START_MS
        rows = [make_row(start), make_row(start + 2 * HOUR_MS)]
        quality = validate_rows(rows, "BTCUSDT", start, start + 2 * HOUR_MS, start + 3 * HOUR_MS)
        self.assertFalse(quality["complete"])
        self.assertEqual(quality["missing_hour_count"], 1)
        self.assertEqual(quality["missing_hour_utc"], [
            "2026-11-01T01:00:00Z"
        ])

    def test_duplicate_timestamps_fail_closed(self):
        start = CAPTURE_START_MS
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_rows([make_row(start), make_row(start)], "ETHUSDT", start, start, start + HOUR_MS)

    def test_unsorted_timestamps_fail_closed(self):
        start = CAPTURE_START_MS
        with self.assertRaisesRegex(ValueError, "not sorted"):
            validate_rows([make_row(start + HOUR_MS), make_row(start)], "ETHUSDT",
                          start, start + HOUR_MS, start + 2 * HOUR_MS)

    def test_unclosed_bar_is_rejected(self):
        start = CAPTURE_START_MS
        with self.assertRaisesRegex(ValueError, "unclosed"):
            validate_rows([make_row(start)], "ETHUSDT", start, start, start + HOUR_MS - 1)

    def test_invalid_ohlc_is_rejected(self):
        start = CAPTURE_START_MS
        row = make_row(start)
        row[2] = "1970"
        with self.assertRaisesRegex(ValueError, "high"):
            validate_rows([row], "ETHUSDT", start, start, start + HOUR_MS)

    def test_merge_is_sorted_idempotent_and_records_corrections(self):
        start = CAPTURE_START_MS
        old = make_row(start + HOUR_MS, close="2000")
        first = make_row(start, close="1900")
        revised = make_row(start + HOUR_MS, close="2001")
        later = make_row(start + 2 * HOUR_MS)
        merged, corrections = merge_rows([old, first], [revised, later])
        self.assertEqual([int(row[0]) for row in merged],
                         [start, start + HOUR_MS, start + 2 * HOUR_MS])
        self.assertEqual(merged[1], revised)
        self.assertEqual(len(corrections), 1)
        self.assertEqual(merge_rows(merged, [revised, later])[0], merged)

    def test_csv_round_trip_preserves_schema_and_rows(self):
        rows = [make_row(CAPTURE_START_MS), make_row(CAPTURE_START_MS + HOUR_MS)]
        payload = rows_to_csv(rows)
        self.assertEqual(read_csv_rows(payload), rows)
        self.assertEqual(sha256_bytes(payload), sha256_bytes(payload))

    def test_fetch_klines_uses_exact_symbol_and_paginates(self):
        start = CAPTURE_START_MS
        first_page = [make_row(start + i * HOUR_MS) for i in range(1000)]
        second_page = [make_row(start + 1000 * HOUR_MS)]
        session = Mock()
        session.get.side_effect = [Response(first_page), Response(second_page)]
        rows = fetch_klines(session, "ETHUSDT", start, start + 1000 * HOUR_MS)
        self.assertEqual(len(rows), 1001)
        self.assertEqual(session.get.call_count, 2)
        first_call = session.get.call_args_list[0]
        self.assertEqual(first_call.args[0], API_URL)
        self.assertEqual(first_call.kwargs["params"]["symbol"], "ETHUSDT")
        self.assertEqual(first_call.kwargs["params"]["interval"], "1h")

    def test_empty_partial_acquisition_is_returned_for_gap_flagging(self):
        session = Mock()
        session.get.return_value = Response([])
        rows = fetch_klines(session, "BTCUSDT", CAPTURE_START_MS, CAPTURE_START_MS)
        self.assertEqual(rows, [])

    def test_http_451_is_not_retried_or_routed_to_an_alternative_host(self):
        session = Mock()
        session.get.return_value = Response(status=451)
        with self.assertRaises(requests.HTTPError):
            fetch_klines(session, "ETHUSDT", CAPTURE_START_MS, CAPTURE_START_MS)
        self.assertEqual(session.get.call_count, 1)

    def test_previous_snapshot_manifest_and_file_hashes_are_verified(self):
        start = CAPTURE_START_MS
        rows = [make_row(start), make_row(start + HOUR_MS)]
        csv_bytes = rows_to_csv(rows)
        manifest = {
            "schema_version": 1,
            "capture_type": "prospective_binance_spot_hourly",
            "market": "spot",
            "interval": "1h",
            "status": "COMPLETE",
            "data_quality_complete": True,
            "requested_start_utc": "2026-11-01T00:00:00Z",
            "requested_end_open_utc": "2026-11-01T01:00:00Z",
            "files": {
                "spot_ETHUSDT_1h.csv": {"sha256": sha256_bytes(csv_bytes)},
                "spot_BTCUSDT_1h.csv": {"sha256": sha256_bytes(csv_bytes)},
            },
        }
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("spot_ETHUSDT_1h.csv", csv_bytes)
            archive.writestr("spot_BTCUSDT_1h.csv", csv_bytes)
            archive.writestr("manifest.json", json.dumps(manifest))
        payload = stream.getvalue()
        release = {"assets": [{
            "name": "snapshot-old-attempt-1.zip",
            "id": 12,
            "state": "uploaded",
            "created_at": "2026-11-23T00:00:00Z",
            "browser_download_url": "https://example.invalid/snapshot.zip",
            "size": len(payload),
            "digest": "sha256:" + sha256_bytes(payload),
        }]}
        session = Mock()
        session.get.side_effect = [Response(release), Response(content=payload)]
        previous = load_previous_snapshot(
            session, "owner/repo", "spot-holdout-2026", "snapshot-current-attempt-1.zip"
        )
        self.assertEqual(previous["asset_id"], 12)
        self.assertEqual(previous["rows"]["ETHUSDT"], rows)

    def test_release_storage_failure_is_reported(self):
        session = Mock()
        session.get.return_value = Response(status=404)
        session.post.return_value = Response(status=403)
        with self.assertRaises(requests.HTTPError):
            publish_release_asset(
                session, "owner/repo", "token", "tag", "snapshot-1-attempt-1.zip", b"zip"
            )

    def test_release_upload_is_verified_with_exact_content_type(self):
        zip_bytes = b"test-zip-bytes"
        digest = "sha256:" + sha256_bytes(zip_bytes)
        release = {
            "upload_url": "https://uploads.github.com/repos/owner/repo/releases/7/assets{?name,label}",
            "assets": [],
        }
        uploaded = {
            "id": 9, "name": "snapshot-1-attempt-1.manifest.json",
            "browser_download_url": "https://github.com/owner/repo/releases/download/tag/snapshot.manifest.json",
            "created_at": "2026-11-23T00:00:00Z",
            "digest": digest,
        }
        verified = {"assets": [{**uploaded, "size": len(zip_bytes)}], "immutable": False}
        session = Mock()
        session.get.side_effect = [Response(release), Response(verified)]
        session.post.return_value = Response(uploaded, status=201)
        result = publish_release_asset(
            session, "owner/repo", "token", "tag", "snapshot-1-attempt-1.manifest.json",
            zip_bytes, content_type="application/json"
        )
        self.assertEqual(result["asset_id"], 9)
        self.assertEqual(result["asset_digest"], digest)
        self.assertFalse(result["idempotent_reuse"])
        self.assertFalse(result["platform_immutable"])
        self.assertEqual(session.post.call_count, 1)
        self.assertEqual(session.post.call_args.kwargs["headers"]["Content-Type"], "application/json")

    def test_release_asset_collision_is_not_overwritten(self):
        zip_bytes = b"new-bytes"
        session = Mock()
        session.get.return_value = Response({
            "upload_url": "https://uploads.github.com/upload",
            "assets": [{
                "name": "snapshot-1-attempt-1.zip",
                "digest": "sha256:" + "0" * 64,
            }],
        })
        with self.assertRaisesRegex(RuntimeError, "collision"):
            publish_release_asset(
                session, "owner/repo", "token", "tag", "snapshot-1-attempt-1.zip", zip_bytes
            )
        session.post.assert_not_called()

    def test_durable_sidecar_requires_verified_zip_metadata_and_file_hashes(self):
        manifest = {
            "files": {
                "spot_ETHUSDT_1h.csv": {"sha256": "a" * 64},
                "spot_BTCUSDT_1h.csv": {"sha256": "b" * 64},
            },
            "storage": {
                "asset_id": 9,
                "asset_name": "snapshot-9-attempt-1.zip",
                "asset_url": "https://example.invalid/snapshot.zip",
                "asset_digest": "sha256:" + "c" * 64,
                "archive_sha256": "c" * 64,
            },
        }
        payload = build_durable_sidecar(manifest)
        decoded = json.loads(payload.decode("utf-8"))
        self.assertEqual(decoded["storage"]["asset_id"], 9)
        self.assertEqual(decoded["storage"]["asset_url"], "https://example.invalid/snapshot.zip")
        self.assertEqual(decoded["storage"]["asset_digest"], "sha256:" + "c" * 64)
        self.assertEqual(decoded["files"]["spot_ETHUSDT_1h.csv"]["sha256"], "a" * 64)
        with self.assertRaisesRegex(ValueError, "verified ZIP asset"):
            build_durable_sidecar({"files": manifest["files"], "storage": None})
        with self.assertRaisesRegex(ValueError, "per-file SHA-256"):
            build_durable_sidecar({
                "files": {"spot_ETHUSDT_1h.csv": {}},
                "storage": manifest["storage"],
            })

    def test_previous_snapshot_sidecar_is_append_only_and_provenance_complete(self):
        previous = {
            "manifest": {
                "schema_version": 1,
                "files": {
                    "spot_ETHUSDT_1h.csv": {"sha256": "1" * 64},
                    "spot_BTCUSDT_1h.csv": {"sha256": "2" * 64},
                },
            },
            "asset_name": "snapshot-old-attempt-1.zip",
            "asset_id": 12,
            "asset_url": "https://example.invalid/snapshot-old.zip",
            "asset_size_bytes": 123,
            "asset_created_at": "2026-11-23T00:00:00Z",
            "asset_digest": "sha256:" + "b" * 64,
            "archive_sha256": "b" * 64,
            "platform_immutable": False,
        }
        published = {
            "asset_id": 13,
            "asset_name": "snapshot-old-attempt-1.manifest.json",
            "asset_url": "https://example.invalid/snapshot-old.manifest.json",
            "asset_size_bytes": 900,
            "asset_digest": "sha256:" + "c" * 64,
            "idempotent_reuse": False,
        }
        with patch("spot_holdout_capture.publish_release_asset", return_value=published) as publish:
            result = publish_snapshot_sidecar(Mock(), "owner/repo", "token", previous)
        self.assertEqual(result["asset_id"], 13)
        kwargs = publish.call_args.kwargs
        self.assertEqual(kwargs["asset_name"], "snapshot-old-attempt-1.manifest.json")
        self.assertEqual(kwargs["content_type"], "application/json")
        sidecar = json.loads(kwargs["zip_bytes"].decode("utf-8"))
        self.assertEqual(sidecar["storage"]["asset_id"], 12)
        self.assertEqual(sidecar["storage"]["asset_url"], previous["asset_url"])
        self.assertEqual(sidecar["storage"]["asset_digest"], previous["asset_digest"])
        self.assertEqual(sidecar["files"]["spot_BTCUSDT_1h.csv"]["sha256"], "2" * 64)

    def test_write_snapshot_publishes_zip_and_durable_sidecar(self):
        rows = [make_row(CAPTURE_START_MS + i * HOUR_MS) for i in range(5)]
        captured_sidecars = []

        def fake_publish(**kwargs):
            payload = kwargs["zip_bytes"]
            digest = sha256_bytes(payload)
            if kwargs["content_type"] == "application/zip":
                return {
                    "asset_id": 101,
                    "asset_name": kwargs["asset_name"],
                    "asset_url": "https://example.invalid/snapshot.zip",
                    "asset_size_bytes": len(payload),
                    "asset_created_at": "2026-11-01T03:10:00Z",
                    "asset_digest": "sha256:" + digest,
                    "platform_immutable": False,
                    "idempotent_reuse": False,
                }
            captured_sidecars.append(json.loads(payload.decode("utf-8")))
            return {
                "asset_id": 102,
                "asset_name": kwargs["asset_name"],
                "asset_url": "https://example.invalid/snapshot.manifest.json",
                "asset_size_bytes": len(payload),
                "asset_created_at": "2026-11-01T03:10:01Z",
                "asset_digest": "sha256:" + digest,
                "platform_immutable": False,
                "idempotent_reuse": False,
            }

        with tempfile.TemporaryDirectory() as directory:
            with patch("spot_holdout_capture.load_existing_slot_snapshot", return_value=None), \
                 patch("spot_holdout_capture.load_previous_snapshot", return_value=None), \
                 patch("spot_holdout_capture.fetch_klines", return_value=rows), \
                 patch("spot_holdout_capture.publish_release_asset", side_effect=fake_publish) as publish:
                manifest = write_snapshot(
                    Path(directory), "owner/repo", "42", "1", "commit-sha",
                    CAPTURE_START_MS + 5 * HOUR_MS + 10 * 60_000, Mock(), "token",
                )
            self.assertEqual(publish.call_count, 2)
            self.assertEqual(publish.call_args_list[0].kwargs["content_type"], "application/zip")
            self.assertEqual(publish.call_args_list[1].kwargs["content_type"], "application/json")
            sidecar = captured_sidecars[0]
            self.assertEqual(sidecar["storage"]["asset_id"], 101)
            self.assertEqual(
                sidecar["files"]["spot_ETHUSDT_1h.csv"]["sha256"],
                manifest["files"]["spot_ETHUSDT_1h.csv"]["sha256"],
            )
            self.assertEqual(
                sidecar["storage"]["asset_digest"],
                "sha256:" + sidecar["storage"]["archive_sha256"],
            )
            self.assertEqual(manifest["storage"]["sidecar_asset_id"], 102)
            zip_path = Path(directory) / "snapshot-slot-2026-11-01.zip"
            with zipfile.ZipFile(zip_path) as archive:
                embedded = json.loads(archive.read("manifest.json").decode("utf-8"))
            self.assertEqual(embedded["storage"]["sidecar_asset_name"], "snapshot-slot-2026-11-01.manifest.json")
            self.assertEqual(manifest["capture_slot_id"], "binance-spot-1h:prospective-2026-11:2026-11-01")
            self.assertEqual(manifest["capture_slot_due_at_utc"], "2026-11-01T04:23:00Z")
            self.assertFalse(embedded["storage"]["platform_immutable"])


    def test_write_snapshot_reuses_existing_slot_without_duplicate_fetch_or_publication(self):
        existing = {
            "schema_version": 1,
            "capture_type": "prospective_binance_spot_hourly",
            "status": "COMPLETE",
            "data_quality_complete": True,
            "research_evaluation_authorized": False,
            "capture_slot_id": "binance-spot-1h:prospective-2026-11:2026-11-24",
            "capture_slot_date_utc": "2026-11-24",
            "capture_slot_due_at_utc": "2026-11-24T04:23:00Z",
            "files": {},
            "storage": {"asset_id": 77, "sidecar_asset_id": 78},
        }
        now = int(datetime(2026, 11, 24, 10, 5, tzinfo=timezone.utc).timestamp() * 1000)
        with tempfile.TemporaryDirectory() as directory:
            with patch("spot_holdout_capture.load_existing_slot_snapshot", return_value=existing) as find_slot, \
                 patch("spot_holdout_capture.load_previous_snapshot") as previous, \
                 patch("spot_holdout_capture.fetch_klines") as fetch, \
                 patch("spot_holdout_capture.publish_release_asset") as publish:
                result = write_snapshot(
                    Path(directory), "owner/repo", "99", "1", "commit-sha",
                    now, Mock(), "token",
                )
            self.assertTrue(result["idempotent_slot_reuse"])
            self.assertEqual(find_slot.call_args.args[3]["id"], existing["capture_slot_id"])
            previous.assert_not_called()
            fetch.assert_not_called()
            publish.assert_not_called()
            persisted = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(persisted["idempotent_slot_reuse"])

    def test_release_asset_idempotent_reuse_requires_exact_digest_and_size(self):
        payload = b"same-manifest"
        asset = {
            "id": 22,
            "name": "snapshot-22-attempt-1.manifest.json",
            "size": len(payload),
            "created_at": "2026-11-23T00:00:00Z",
            "browser_download_url": "https://example.invalid/sidecar.json",
            "digest": "sha256:" + sha256_bytes(payload),
        }
        session = Mock()
        session.get.return_value = Response({"assets": [asset], "immutable": False})
        result = publish_release_asset(
            session, "owner/repo", "token", "tag",
            "snapshot-22-attempt-1.manifest.json", payload, content_type="application/json",
        )
        self.assertTrue(result["idempotent_reuse"])
        self.assertEqual(result["asset_id"], 22)
        self.assertEqual(result["asset_size_bytes"], len(payload))
        session.post.assert_not_called()

    def test_legacy_release_description_is_corrected_without_changing_immutability(self):
        legacy = {
            "id": 7,
            "body": LEGACY_RELEASE_BODY,
            "upload_url": "https://uploads.github.com/repos/owner/repo/releases/7/assets{?name,label}",
            "assets": [],
            "immutable": False,
        }
        corrected = {**legacy, "body": RELEASE_BODY}
        payload = b"new-sidecar"
        digest = "sha256:" + sha256_bytes(payload)
        uploaded = {
            "id": 8,
            "name": "snapshot-8-attempt-1.manifest.json",
            "browser_download_url": "https://example.invalid/snapshot.manifest.json",
            "created_at": "2026-11-23T00:00:00Z",
            "digest": digest,
        }
        verified = {"assets": [{**uploaded, "size": len(payload)}], "immutable": False}
        session = Mock()
        session.get.side_effect = [Response(legacy), Response(verified)]
        session.patch.return_value = Response(corrected)
        session.post.return_value = Response(uploaded, status=201)
        publish_release_asset(
            session, "owner/repo", "token", "tag",
            "snapshot-8-attempt-1.manifest.json", payload, content_type="application/json",
        )
        session.patch.assert_called_once()
        self.assertIn("/releases/7", session.patch.call_args.args[0])
        self.assertEqual(session.patch.call_args.kwargs["json"]["body"], RELEASE_BODY)

    def test_previous_snapshot_without_github_digest_fails_closed(self):
        session = Mock()
        session.get.return_value = Response({"assets": [{
            "name": "snapshot-old-attempt-1.zip",
            "id": 12,
            "state": "uploaded",
            "created_at": "2026-11-23T00:00:00Z",
            "browser_download_url": "https://example.invalid/snapshot.zip",
            "size": 100,
        }]})
        with self.assertRaisesRegex(ValueError, "no GitHub SHA-256 digest"):
            load_previous_snapshot(
                session, "owner/repo", "spot-holdout-2026", "snapshot-current-attempt-1.zip"
            )
        self.assertEqual(session.get.call_count, 1)

    def test_workflow_is_scheduled_gated_and_manifest_only(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "spot-holdout-capture.yml").read_text(encoding="utf-8")
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("issue_comment:", workflow)
        self.assertIn('"/qfr-capture-spot-holdout"', workflow)
        self.assertIn("takenthatusernameis-collab", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("permissions: {}", workflow)
        capture_job = workflow.split("  capture:", 1)[1]
        self.assertIn("permissions:\n      contents: write", capture_job)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("actions/cache", workflow)
        artifact = workflow.split("      - name: Upload manifest only", 1)[1]
        self.assertIn("manifest.json", artifact)
        self.assertNotIn(".csv", artifact)
        self.assertNotIn(".zip", artifact)
        self.assertNotIn(".manifest.json", artifact)
        guardian = (root / ".github" / "workflows" / "queue-guardian.yml").read_text(encoding="utf-8")
        self.assertIn("Prospective Binance Spot holdout capture", guardian)
        self.assertIn("github.event.workflow_run.name == 'Prospective Binance Spot holdout capture'", guardian)
        self.assertIn('["schedule","workflow_dispatch","issue_comment"]', guardian)


if __name__ == "__main__":
    unittest.main()
