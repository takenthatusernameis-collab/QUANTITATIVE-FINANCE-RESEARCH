import datetime as dt
import json
import math
import unittest
from unittest.mock import patch

import eth_validator_queue_source_preflight as model


def unix(day):
    return int(dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc).timestamp())


def queue_component(component_id, name, value=1.0):
    return {
        "id": component_id,
        "name": name,
        "unit": "days",
        "points": [
            {"t": unix(dt.date(2020, 12, 1)), "v": str(value), "finality": "final"},
            {"t": unix(dt.date(2026, 10, 31)), "v": str(value + 1), "finality": "final"},
        ],
    }


def synthetic_series():
    return {
        "metric": {"id": model.METRIC_ID},
        "interval": "24h",
        "state": "current",
        "generatedAt": unix(dt.date(2026, 11, 1)),
        "sourceObservedAt": unix(dt.date(2026, 10, 31)),
        "historyStart": unix(dt.date(2020, 12, 1)),
        "historyEnd": unix(dt.date(2026, 11, 1)),
        "components": [
            queue_component("entry_wait", "Entry Wait"),
            queue_component("exit_wait", "Exit Wait"),
            queue_component("consolidation_wait", "Consolidation Wait"),
        ],
    }


def daily_kline(day, close=2000.0, unit="milliseconds"):
    scale = 1_000_000 if unit == "microseconds" else 1_000
    interval = model.DAILY_INTERVAL_MS * (1_000 if unit == "microseconds" else 1)
    open_time = unix(day) * scale
    return [
        str(open_time), str(close), str(close + 2), str(close - 2), str(close + 1),
        "10", str(open_time + interval - 1), str(close * 10), "100",
        "5", str(close * 5), "0",
    ]


class EthereumValidatorQueueSourcePreflightTests(unittest.TestCase):
    def test_openapi_schema_requires_components_and_exact_point_fields(self):
        payload = {
            "openapi": "3.0.3",
            "info": {"version": "1.0.0"},
            "components": {"schemas": {
                "Series": {"properties": {"components": {"type": "array"}}},
                "Point": {"required": ["t", "v", "finality"]},
            }},
        }
        self.assertEqual(model.validate_openapi(payload)["series_components_schema"], "array")
        payload["components"]["schemas"]["Point"]["required"] = ["t", "v"]
        with self.assertRaisesRegex(model.PreflightError, "t/v/finality"):
            model.validate_openapi(payload)

    def test_catalog_requires_exact_metric_and_daily_access(self):
        metric = {
            "id": model.METRIC_ID,
            "name": "Validator Queue Wait Time",
            "unit": "days",
            "status": "active",
            "intervals": ["24h", "1w"],
            "historyStart": unix(dt.date(2020, 12, 1)),
            "historyEnd": unix(dt.date(2026, 11, 1)),
        }
        result = model.validate_catalog({"asset": "ETH", "metrics": [metric]})
        self.assertEqual(result["id"], model.METRIC_ID)
        metric["intervals"] = ["1w"]
        with self.assertRaisesRegex(model.PreflightError, "daily 24h"):
            model.validate_catalog({"asset": "ETH", "metrics": [metric]})

    def test_series_identifies_entry_exit_and_separate_consolidation(self):
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}
        result = model.validate_queue_series(synthetic_series(), headers)
        self.assertEqual(result["state"], "current")
        self.assertTrue(result["consolidation_component_present"])
        self.assertEqual([x["kind"] for x in result["components"]], ["entry", "exit", "consolidation"])
        self.assertEqual(result["entry_values"][dt.date(2020, 12, 1)], 1.0)
        self.assertEqual(result["exit_values"][dt.date(2026, 10, 31)], 2.0)
        self.assertEqual({item["unit_source"] for item in result["components"]}, {"component"})

    def test_series_rejects_missing_component_license_or_preview(self):
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}
        payload = synthetic_series()
        payload["components"] = [payload["components"][0], payload["components"][2]]
        with self.assertRaisesRegex(model.PreflightError, "entry-wait|exit-wait"):
            model.validate_queue_series(payload, headers)
        with self.assertRaisesRegex(model.PreflightError, "Link header"):
            model.validate_queue_series(synthetic_series(), {})
        headers["x-ckh-preview"] = "Plus; sample=1"
        with self.assertRaisesRegex(model.PreflightError, "fixed plan preview"):
            model.validate_queue_series(synthetic_series(), headers)

    def test_component_parser_preserves_nulls_and_excludes_partial_values(self):
        component = {
            "id": "entry_wait",
            "name": "Entry Wait",
            "unit": "days",
            "points": [
                {"t": unix(dt.date(2020, 12, 1)), "v": "0", "finality": "final"},
                {"t": unix(dt.date(2020, 12, 2)), "v": None, "finality": "final"},
                {"t": unix(dt.date(2020, 12, 3)), "v": "9", "finality": "partial"},
            ],
        }
        parsed = model.parse_component(component)
        self.assertEqual(parsed["values"], {dt.date(2020, 12, 1): 0.0})
        self.assertEqual(parsed["null_count"], 1)
        self.assertEqual(parsed["non_final_count"], 1)

    def test_checksum_parser_requires_matching_filename_and_sha256(self):
        digest = "a" * 64
        self.assertEqual(
            model.parse_archive_checksum(f"{digest}  ETHUSDT-1d-2021-01.zip".encode(),
                                         "ETHUSDT-1d-2021-01.zip"),
            digest,
        )
        with self.assertRaisesRegex(model.PreflightError, "different archive"):
            model.parse_archive_checksum(f"{digest}  other.zip".encode(), "ETHUSDT-1d-2021-01.zip")

    def test_monthly_and_daily_archive_specs_have_expected_population(self):
        monthly = model.build_monthly_archive_specs(model.PRICE_START, model.PRICE_MONTHLY_END)
        daily = model.build_daily_archive_specs(model.PRICE_BUFFER_START, model.PRICE_BUFFER_END)
        self.assertEqual(len(monthly), 71)
        self.assertEqual(monthly[0]["tag"], "2020-12")
        self.assertEqual(monthly[-1]["tag"], "2026-10")
        self.assertEqual(len(daily), 5)
        self.assertEqual(daily[0]["tag"], "2026-11-01")
        self.assertEqual(daily[-1]["tag"], "2026-11-05")

    def test_daily_kline_parser_accepts_milliseconds_and_microseconds(self):
        day = dt.date(2021, 1, 1)
        ms = model.parse_daily_klines((",".join(daily_kline(day, unit="milliseconds")) + "\n").encode())
        us = model.parse_daily_klines((",".join(daily_kline(day, unit="microseconds")) + "\n").encode())
        self.assertEqual(ms[0][day], 2001.0)
        self.assertEqual(ms[1], "milliseconds")
        self.assertEqual(us[1], "microseconds")

    def test_daily_kline_parser_rejects_bad_ohlc_and_duplicates(self):
        day = dt.date(2021, 1, 1)
        bad = daily_kline(day)
        bad[3] = "3000"
        with self.assertRaisesRegex(model.PreflightError, "OHLC relationship"):
            model.parse_daily_klines((",".join(bad) + "\n").encode())
        valid = daily_kline(day)
        with self.assertRaisesRegex(model.PreflightError, "Duplicate"):
            model.parse_daily_klines((",".join(valid) + "\n" + ",".join(valid) + "\n").encode())

    def test_schedule_has_minimum_validation_test_and_warmup_counts(self):
        entry = {}
        exit_ = {}
        day = model.ORIGIN_GRID_START - dt.timedelta(days=2)
        last = model.SAMPLE_END - dt.timedelta(days=3)
        while day <= last:
            entry[day] = 2.0
            exit_[day] = 3.0
            day += dt.timedelta(days=1)
        prices = {}
        day = model.PRICE_START
        while day <= model.PRICE_END:
            prices[day] = 2000.0 + (day - model.PRICE_START).days
            day += dt.timedelta(days=1)
        result = model.evaluate_schedule(entry, exit_, prices)
        self.assertEqual(result["validation"]["scheduled_origins"], 183)
        self.assertEqual(result["test"]["scheduled_origins"], 111)
        self.assertGreaterEqual(result["validation"]["valid_origins_after_source_exclusions"], 100)
        self.assertGreaterEqual(result["test"]["valid_origins_after_source_exclusions"], 100)
        self.assertTrue(result["target_windows_non_overlapping"])
        self.assertGreaterEqual(result["observed_training_count_min"], 60)
        self.assertEqual(result["observed_training_count_max"], 100)
        self.assertGreater(result["test"]["pre_pectra_origins"], 0)
        self.assertGreater(result["test"]["post_pectra_origins"], 0)

    def test_schedule_rejects_insufficient_queue_coverage(self):
        entry = {}
        exit_ = {}
        day = model.ORIGIN_GRID_START - dt.timedelta(days=2)
        last = model.SAMPLE_END - dt.timedelta(days=3)
        while day <= last:
            entry[day] = 2.0
            exit_[day] = 3.0
            day += dt.timedelta(days=1)
        prices = {}
        day = model.PRICE_START
        while day <= model.PRICE_END:
            prices[day] = 2000.0
            day += dt.timedelta(days=1)
        for origin in model.build_origin_schedule():
            entry.pop(origin["date"] - dt.timedelta(days=2), None)
        with self.assertRaisesRegex(model.PreflightError, "valid validation origins"):
            model.evaluate_schedule(entry, exit_, prices)


    def test_catalog_url_candidates_infer_asset_from_metric_before_explicit_asset(self):
        self.assertEqual(
            model.build_catalog_url_candidates(),
            [
                f"{model.CATALOG_URL}?ids={model.METRIC_ID}",
                f"{model.CATALOG_URL}?asset=ETH",
            ],
        )

    def test_catalog_fetch_uses_ids_inference_then_explicit_asset_fallback(self):
        metric = {
            "id": model.METRIC_ID,
            "name": "Validator Queue Wait Time",
            "unit": "days",
            "status": "active",
            "intervals": ["24h", "1w"],
            "historyStart": unix(dt.date(2020, 12, 1)),
            "historyEnd": unix(dt.date(2026, 11, 1)),
        }
        responses = [
            (json.dumps({"asset": "BTC", "metrics": []}).encode("utf-8"), {}),
            (json.dumps({"asset": "ETH", "metrics": [metric]}).encode("utf-8"), {}),
        ]
        model.PARTIAL_EVIDENCE.clear()
        with patch.object(model, "fetch_bytes", side_effect=responses):
            url, raw, catalog = model.fetch_eth_catalog()
        self.assertEqual(url, model.build_catalog_url_candidates()[1])
        self.assertEqual(catalog["id"], model.METRIC_ID)
        self.assertEqual(len(raw) > 0, True)
        attempts = model.PARTIAL_EVIDENCE["cryptokeyhole"]["catalog_attempts"]
        self.assertEqual([item["response_asset"] for item in attempts], ["BTC", "ETH"])
        self.assertFalse(attempts[0]["accepted"])
        self.assertTrue(attempts[1]["accepted"])
        self.assertIn("Unexpected catalog asset", attempts[0]["error"])

    def test_run_preflight_preserves_partial_metadata_when_both_catalog_routes_mismatch(self):
        openapi = {
            "openapi": "3.0.3",
            "info": {"version": "1.0.0"},
            "components": {"schemas": {
                "Series": {"properties": {"components": {"type": "array"}}},
                "Point": {"required": ["t", "v", "finality"]},
            }},
        }

        def fake_fetch(url):
            if url == model.OPENAPI_URL:
                return json.dumps(openapi).encode("utf-8"), {}
            return json.dumps({"asset": "BTC", "metrics": []}).encode("utf-8"), {}

        model.PARTIAL_EVIDENCE.clear()
        with patch.object(model, "fetch_bytes", side_effect=fake_fetch):
            with self.assertRaisesRegex(model.PreflightError, "No valid ETH catalog response"):
                model.run_preflight()
        evidence = model.PARTIAL_EVIDENCE["cryptokeyhole"]
        self.assertIn("openapi_sha256", evidence)
        self.assertEqual(len(evidence["catalog_attempts"]), 2)
        self.assertEqual(
            [item["response_asset"] for item in evidence["catalog_attempts"]],
            ["BTC", "BTC"],
        )
        self.assertTrue(all(not item["accepted"] for item in evidence["catalog_attempts"]))


    def test_series_components_inherit_validated_catalog_unit_when_unit_is_omitted(self):
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}
        payload = synthetic_series()
        for component in payload["components"]:
            component.pop("unit")
        result = model.validate_queue_series(payload, headers, default_unit="days")
        self.assertEqual({item["unit"] for item in result["components"]}, {"days"})
        self.assertEqual({item["unit_source"] for item in result["components"]}, {"catalog_metric"})

    def test_series_rejects_missing_component_unit_without_catalog_fallback(self):
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}
        payload = synthetic_series()
        for component in payload["components"]:
            component.pop("unit")
        with self.assertRaisesRegex(model.PreflightError, "no validated series/catalog unit is available"):
            model.validate_queue_series(payload, headers)

    def test_series_rejects_parent_unit_conflict_with_validated_catalog(self):
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}
        payload = synthetic_series()
        payload["metric"]["unit"] = "hours"
        for component in payload["components"]:
            component.pop("unit")
        with self.assertRaisesRegex(model.PreflightError, "conflicts with validated catalog unit"):
            model.validate_queue_series(payload, headers, default_unit="days")

    def test_run_preflight_records_series_shape_before_component_validation(self):
        openapi = {
            "openapi": "3.0.3",
            "info": {"version": "1.0.0"},
            "components": {"schemas": {
                "Series": {"properties": {"components": {"type": "array"}}},
                "Point": {"required": ["t", "v", "finality"]},
            }},
        }
        metric = {
            "id": model.METRIC_ID,
            "name": "Validator Queue Wait Time",
            "unit": "days",
            "status": "active",
            "intervals": ["24h"],
            "historyStart": unix(dt.date(2020, 12, 1)),
            "historyEnd": unix(dt.date(2026, 11, 1)),
        }
        catalog = {"asset": "ETH", "metrics": [metric]}
        series = synthetic_series()
        series["components"][0]["unit"] = "hours"
        headers = {"link": '<https://creativecommons.org/licenses/by/4.0/>; rel="license"'}

        def fake_fetch(url):
            if url == model.OPENAPI_URL:
                return json.dumps(openapi).encode("utf-8"), {}
            if url.startswith(model.CATALOG_URL):
                return json.dumps(catalog).encode("utf-8"), {}
            if url.startswith(model.SERIES_URL):
                return json.dumps(series).encode("utf-8"), headers
            raise AssertionError(f"Unexpected URL: {url}")

        model.PARTIAL_EVIDENCE.clear()
        with patch.object(model, "fetch_bytes", side_effect=fake_fetch):
            with self.assertRaisesRegex(model.PreflightError, "not expressed in days"):
                model.run_preflight()
        shape = model.PARTIAL_EVIDENCE["cryptokeyhole"]["series_shape"]
        self.assertEqual(shape["metric_id"], model.METRIC_ID)
        self.assertEqual(shape["components"][0]["unit"], "hours")
        self.assertGreater(shape["components"][0]["point_count"], 0)


if __name__ == "__main__":
    unittest.main()
