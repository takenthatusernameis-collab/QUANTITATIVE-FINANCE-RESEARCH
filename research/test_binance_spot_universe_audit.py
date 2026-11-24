import calendar
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binance_spot_universe_audit as audit


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected extra HTTP request")
        return self.responses.pop(0)


def response(status_code, content=b"", headers=None, url="https://example.test/resource"):
    item = requests.Response()
    item.status_code = status_code
    item.url = url
    item._content = content
    item.raw = io.BytesIO(content)
    item.headers.update(headers or {})
    item.encoding = "utf-8"
    return item


def kline_zip(month, unit):
    year, number = (int(part) for part in month.split("-"))
    days = calendar.monthrange(year, number)[1]
    start = datetime(year, number, 1, tzinfo=timezone.utc).timestamp()
    scale = 1_000_000 if unit == "us" else 1_000
    step = 3_600_000_000 if unit == "us" else 3_600_000
    rows = []
    for index in range(days * 24):
        open_time = int(start * scale) + index * step
        close_time = open_time + step - 1
        rows.append([
            str(open_time), "100", "101", "99", "100.5", "10",
            str(close_time), "1000", "5", "4", "400", "0",
        ])
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerows(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive_file:
        archive_file.writestr(f"BTCUSDT-1h-{month}.csv", text.getvalue())
    return buffer.getvalue(), rows


class BinanceSpotUniverseAuditTests(unittest.TestCase):
    def catalogue_fixture(self):
        return {
            "timezone": "UTC",
            "serverTime": 1795523166064,
            "rateLimits": [],
            "symbols": [
                {
                    "symbol": "BTCUSDT", "status": "TRADING",
                    "baseAsset": "BTC", "quoteAsset": "USDT",
                    "isSpotTradingAllowed": True, "permissions": ["SPOT"],
                    "permissionSets": [["SPOT"]], "filters": [{"filterType": "PRICE_FILTER"}],
                },
                {
                    "symbol": "ETHUSDT", "status": "TRADING",
                    "baseAsset": "ETH", "quoteAsset": "USDT",
                    "isSpotTradingAllowed": True, "permissions": ["SPOT"],
                    "permissionSets": [["SPOT"]], "filters": [],
                },
                {
                    "symbol": "AAAUSDT", "status": "TRADING",
                    "baseAsset": "AAA", "quoteAsset": "USDT",
                    "isSpotTradingAllowed": True, "permissions": ["SPOT"],
                    "permissionSets": [["SPOT"]], "filters": [],
                },
                {
                    "symbol": "ZZZBTC", "status": "BREAK",
                    "baseAsset": "ZZZ", "quoteAsset": "BTC",
                    "isSpotTradingAllowed": False, "permissions": [],
                    "permissionSets": [], "filters": [],
                },
            ],
        }

    def test_normalize_exchange_info_preserves_every_required_catalogue_dimension(self):
        payload = json.dumps(self.catalogue_fixture()).encode()
        records, errors, summary = audit.normalize_exchange_info(payload)
        self.assertEqual(errors, [])
        self.assertEqual(summary["symbol_count_reported"], 4)
        self.assertEqual(summary["symbol_count_normalized"], 4)
        self.assertEqual(summary["status_counts"], {"BREAK": 1, "TRADING": 3})
        self.assertEqual(summary["quote_asset_counts"], {"BTC": 1, "USDT": 3})
        zzz = next(item for item in records if item["symbol"] == "ZZZBTC")
        self.assertFalse(zzz["isSpotTradingAllowed"])
        self.assertEqual(zzz["quoteAsset"], "BTC")

    def test_catalogue_parse_errors_are_explicit_and_not_silently_dropped(self):
        payload = json.dumps({
            "symbols": [
                {"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT"},
                {"symbol": "BROKEN"},
            ]
        }).encode()
        records, errors, summary = audit.normalize_exchange_info(payload)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(summary["parse_error_count"], 1)

    def test_sample_selection_is_deterministic_and_includes_a_nonseed_stratum(self):
        records, _, _ = audit.normalize_exchange_info(
            json.dumps(self.catalogue_fixture()).encode()
        )
        first_symbols, first_meta = audit.select_sample(records)
        second_symbols, second_meta = audit.select_sample(records)
        self.assertEqual(first_symbols, ["BTCUSDT", "ETHUSDT", "ZZZBTC"])
        self.assertEqual(first_symbols, second_symbols)
        self.assertEqual(first_meta, second_meta)
        self.assertTrue(first_meta["sample_is_non_exhaustive"])
        self.assertEqual(first_meta["selected_quote_status_stratum"], {
            "quoteAsset": "BTC", "status": "BREAK"
        })

    def test_s3_listing_parser_reads_common_prefixes_and_pagination_token(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
          <IsTruncated>true</IsTruncated>
          <NextContinuationToken>next-page-token</NextContinuationToken>
          <KeyCount>1</KeyCount>
          <CommonPrefixes><Prefix>data/spot/monthly/klines/BTCUSDT/</Prefix></CommonPrefixes>
        </ListBucketResult>"""
        parsed = audit.parse_s3_listing(xml)
        self.assertTrue(parsed["is_truncated"])
        self.assertEqual(parsed["next_continuation_token"], "next-page-token")
        self.assertEqual(parsed["common_prefixes"], ["data/spot/monthly/klines/BTCUSDT/"])

    def test_s3_listing_parser_rejects_non_s3_index_html(self):
        with self.assertRaises(ValueError):
            audit.parse_s3_listing(b"<html><body>Index unavailable</body></html>")

    def test_monthly_parser_accepts_complete_millisecond_archive(self):
        payload, rows = kline_zip("2020-01", "ms")
        parsed = audit.parse_monthly_kline_zip(payload, "2020-01")
        self.assertEqual(parsed["rows"], len(rows))
        self.assertEqual(parsed["timestamp_unit"], "ms")
        self.assertEqual(parsed["expected_timestamp_unit"], "ms")
        self.assertTrue(parsed["complete_month"])
        self.assertEqual(parsed["missing_hours"], 0)

    def test_monthly_parser_accepts_complete_microsecond_archive(self):
        payload, rows = kline_zip("2026-10", "us")
        parsed = audit.parse_monthly_kline_zip(payload, "2026-10")
        self.assertEqual(parsed["rows"], len(rows))
        self.assertEqual(parsed["timestamp_unit"], "us")
        self.assertEqual(parsed["expected_timestamp_unit"], "us")
        self.assertTrue(parsed["complete_month"])

    def test_monthly_parser_detects_missing_hour_without_synthesizing_it(self):
        payload, rows = kline_zip("2020-01", "ms")
        rows.pop(17)
        text = io.StringIO()
        writer = csv.writer(text, lineterminator="\n")
        writer.writerows(rows)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive_file:
            archive_file.writestr("BTCUSDT-1h-2020-01.csv", text.getvalue())
        parsed = audit.parse_monthly_kline_zip(buffer.getvalue(), "2020-01")
        self.assertFalse(parsed["complete_month"])
        self.assertEqual(parsed["missing_hours"], 1)
        self.assertEqual(parsed["rows"], 743)

    def test_monthly_parser_rejects_wrong_column_count(self):
        text = "1640995200000,100,101\n"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive_file:
            archive_file.writestr("bad.csv", text)
        with self.assertRaisesRegex(ValueError, "expected 12"):
            audit.parse_monthly_kline_zip(buffer.getvalue(), "2020-01")

    def test_checksum_parser_extracts_sha256_and_rejects_invalid_sidecar(self):
        digest = hashlib.sha256(b"archive").hexdigest()
        self.assertEqual(audit.parse_checksum(f"{digest}  file.zip\n".encode()), digest)
        with self.assertRaises(ValueError):
            audit.parse_checksum(b"not-a-checksum")

    def test_request_client_retries_429_once_after_retry_after(self):
        session = FakeSession([
            response(429, b"rate limited", {"Retry-After": "0"}),
            response(200, b'{"ok":true}'),
        ])
        client = audit.RequestClient(session=session)
        with patch.object(audit.time, "sleep") as sleep:
            result, payload = client.get("https://example.test/api")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(payload, b'{"ok":true}')
        self.assertEqual(client.metadata_requests, 2)
        self.assertEqual(client.http_requests, 2)
        sleep.assert_called_once_with(0.0)

    def test_request_client_stops_immediately_on_restricted_status(self):
        session = FakeSession([response(403, b"forbidden")])
        client = audit.RequestClient(session=session)
        with self.assertRaises(audit.RestrictedRoute):
            client.get("https://example.test/api")
        self.assertEqual(client.metadata_requests, 1)
        self.assertEqual(client.http_requests, 1)
        self.assertEqual(len(session.calls), 1)

    def test_request_client_enforces_unique_archive_object_budget(self):
        session = FakeSession([response(404) for _ in range(audit.MAX_ARCHIVE_OBJECTS)])
        client = audit.RequestClient(session=session)
        for index in range(audit.MAX_ARCHIVE_OBJECTS):
            client.get(f"https://example.test/archive-{index}.zip", kind="object")
        with self.assertRaises(audit.BudgetExceeded):
            client.get("https://example.test/archive-over-budget.zip", kind="object")
        self.assertEqual(client.archive_objects, audit.MAX_ARCHIVE_OBJECTS)

    def test_negative_control_symbol_is_not_in_seed_catalogue(self):
        self.assertNotIn(audit.NEGATIVE_CONTROL_SYMBOL, audit.SEED_SYMBOLS)

    def test_workflow_is_exact_actor_gated_read_only_and_default_branch_only(self):
        workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "binance-spot-universe-audit.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", workflow)
        self.assertIn("types: [created]", workflow)
        self.assertIn("github.event.issue.number == 2", workflow)
        self.assertIn("github.event.issue.pull_request != null", workflow)
        self.assertIn("github.event.issue.state == 'open'", workflow)
        self.assertIn("github.event.comment.user.login == 'takenthatusernameis-collab'", workflow)
        self.assertIn("github.event.comment.body == '/qfr-audit-binance-spot-universe'", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request_target:", workflow)
        self.assertNotIn("actions: write", workflow)
        self.assertNotIn("checkout@", workflow.split("Run bounded public-data audit")[1].split("Upload compact")[0])

if __name__ == "__main__":
    unittest.main()
