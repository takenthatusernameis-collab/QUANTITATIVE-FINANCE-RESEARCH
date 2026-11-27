from __future__ import annotations

import datetime as dt
import math
import unittest
from unittest.mock import patch

import btc_blockspace_fee_rate_btc_downside as model


def synthetic_series(days: int = 1094):
    start = dt.date(2023, 11, 28)
    fee_daily = {}
    prices = {}
    price = 37_000.0
    for offset in range(days + 1):
        day = start + dt.timedelta(days=offset)
        fee_daily[day] = float(2 + (offset % 43) * 1.75 + (offset % 7) ** 2 / 3)
        if offset < days:
            shock = 0.006 * math.sin(offset / 7.0) + 0.003 * math.cos(offset / 19.0) - 0.001
            price *= math.exp(shock)
            prices[day] = price
    return fee_daily, prices


class BitcoinBlockspaceFeeRateModelTests(unittest.TestCase):
    def test_feature_uses_exact_t_minus_1_and_t_minus_8_fee_dates(self):
        fee_daily, prices = synthetic_series(days=120)
        events, _ = model.build_events(fee_daily, prices)
        event = events[0]
        signal = event["signal_date"]
        self.assertEqual(event["fee_lag_1_date"], signal - dt.timedelta(days=1))
        self.assertEqual(event["fee_lag_8_date"], signal - dt.timedelta(days=8))
        expected = math.log1p(fee_daily[signal - dt.timedelta(days=1)]) - math.log1p(
            fee_daily[signal - dt.timedelta(days=8)]
        )
        self.assertAlmostEqual(event["blockspace_fee_pressure_7d"], expected, places=14)

    def test_target_uses_next_five_returns_and_excludes_signal_day(self):
        fee_daily, prices = synthetic_series(days=120)
        events, _ = model.build_events(fee_daily, prices)
        event = events[0]
        signal = event["signal_date"]
        self.assertEqual(event["target_start_date"], signal + dt.timedelta(days=1))
        self.assertEqual(event["target_end_date"], signal + dt.timedelta(days=5))
        dates = sorted(prices)
        index = dates.index(signal)
        future = [math.log(prices[dates[k]] / prices[dates[k - 1]]) for k in range(index + 1, index + 6)]
        expected = sum(min(value, 0.0) ** 2 for value in future) / 5 * 10_000
        self.assertAlmostEqual(event["target_semivariance_pct2"], expected, places=14)

    def test_events_are_six_days_apart_and_targets_do_not_overlap(self):
        fee_daily, prices = synthetic_series()
        events, meta = model.build_events(fee_daily, prices)
        self.assertGreater(len(events), 150)
        self.assertFalse(meta["target_windows_overlap"])
        for left, right in zip(events, events[1:]):
            self.assertEqual((right["signal_date"] - left["signal_date"]).days, 6)
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_build_events_rejects_price_gap(self):
        fee_daily, prices = synthetic_series(days=100)
        del prices[dt.date(2024, 1, 5)]
        with self.assertRaisesRegex(ValueError, "contiguous"):
            model.build_events(fee_daily, prices)

    def test_missing_fee_lag_is_not_filled(self):
        fee_daily, prices = synthetic_series(days=120)
        signal = sorted(prices)[20]
        fee_daily.pop(signal - dt.timedelta(days=1))
        events, meta = model.build_events(fee_daily, prices)
        self.assertGreater(meta["skipped"]["missing_fee_lag"], 0)
        self.assertTrue(all(row["fee_lag_1_date"] in fee_daily for row in events))

    def test_walk_forward_uses_65_fully_matured_prior_events(self):
        fee_daily, prices = synthetic_series()
        events, _ = model.build_events(fee_daily, prices)
        predictions = model.walk_forward(events)
        self.assertTrue(predictions)
        for row in predictions:
            self.assertEqual(row["train_n"], 65)
            self.assertLess(row["train_last_signal_date"], row["signal_date"])
            self.assertLess(row["train_last_target_end_date"], row["signal_date"])

    def test_walk_forward_has_preregistered_validation_and_test_sample_sizes(self):
        fee_daily, prices = synthetic_series()
        events, _ = model.build_events(fee_daily, prices)
        predictions = model.walk_forward(events)
        validation = [r for r in predictions if model.VALIDATION_START <= r["signal_date"] < model.TEST_START]
        test = [r for r in predictions if r["signal_date"] >= model.TEST_START]
        self.assertGreaterEqual(len(validation), model.MIN_VALIDATION_FORECASTS)
        self.assertGreaterEqual(len(test), model.MIN_TEST_FORECASTS)

    def test_decision_requires_both_one_percent_gains_and_positive_ci(self):
        val = {"n": 30, "rmse_improvement_pct": 1.0}
        test = {"n": 70, "rmse_improvement_pct": 1.5}
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.5}
        self.assertEqual(model.decide(val, test, paired)[0], "GO")
        test["rmse_improvement_pct"] = 0.99
        self.assertEqual(model.decide(val, test, paired)[0], "INCONCLUSIVE")
        test["rmse_improvement_pct"] = 1.5
        paired["ci_95_low"] = 0.0
        self.assertEqual(model.decide(val, test, paired)[0], "INCONCLUSIVE")

    def test_rejection_requires_no_improvement_in_both_periods_and_negative_ci(self):
        val = {"n": 30, "rmse_improvement_pct": 0.0}
        test = {"n": 70, "rmse_improvement_pct": -0.5}
        paired = {"ci_95_low": -2.0, "ci_95_high": -0.1}
        self.assertEqual(model.decide(val, test, paired)[0], "REJECTED")
        paired["ci_95_high"] = 0.0
        self.assertEqual(model.decide(val, test, paired)[0], "INCONCLUSIVE")

    def test_decision_is_inconclusive_below_frozen_sample_minimums(self):
        val = {"n": 24, "rmse_improvement_pct": 5.0}
        test = {"n": 100, "rmse_improvement_pct": 5.0}
        paired = {"ci_95_low": 1.0, "ci_95_high": 2.0}
        self.assertEqual(model.decide(val, test, paired)[0], "INCONCLUSIVE")
        val["n"] = 25
        test["n"] = 59
        self.assertEqual(model.decide(val, test, paired)[0], "INCONCLUSIVE")

    def test_bootstrap_is_reproducible_and_positive_means_augmented_better(self):
        rows = []
        for i in range(60):
            target = 1.0 + (i % 5) * 0.1
            rows.append({
                "target_bp": target,
                "baseline_prediction_bp": target + 2.0,
                "augmented_prediction_bp": target + 0.5,
            })
        first = model.paired_loss_bootstrap(rows)
        second = model.paired_loss_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertGreater(first["mean_baseline_minus_augmented_squared_loss"], 0)
        self.assertEqual(first["reps"], 2000)
        self.assertEqual(first["block_size_events"], 5)

    def test_source_fetch_uses_one_mempool_request_and_only_preaccepted_price_archives(self):
        start = model.MODEL_START
        end = dt.date(2026, 11, 25)
        fee_daily = {
            start + dt.timedelta(days=i): 5.0 + i % 13
            for i in range((dt.date(2026, 11, 26) - start).days + 1)
        }
        prices = {
            start + dt.timedelta(days=i): 30_000.0 + i * 10
            for i in range((end - start).days + 1)
        }
        row = {
            "url": "https://example.test/accepted.zip",
            "archive_sha256": "a" * 64,
            "checksum_sha256": "b" * 64,
            "checksum_verified": True,
            "timestamp_unit": "milliseconds",
        }
        accepted = {
            "requested_end": end.isoformat(),
            "archive_manifest_sha256": model.ACCEPTED_PRICE_ARCHIVE_MANIFEST_SHA256,
            "archives": [row],
        }
        spec = {"url": row["url"], "tag": "accepted", "kind": "monthly"}
        fee_body = b"frozen-fee-response"
        coverage = {
            "first_utc_date": start.isoformat(),
            "last_utc_date": dt.date(2026, 11, 26).isoformat(),
            "unique_utc_dates": len(fee_daily),
        }
        with (
            patch.object(model, "load_accepted_price_evidence", return_value=accepted),
            patch.object(model.fee_source, "fetch_fee_rate_payload", return_value=(fee_body, 200, model.fee_source.ENDPOINT, {})) as fee_fetch,
            patch.object(model.fee_source, "parse_fee_rate_payload", return_value=({}, {"row_count": 2})),
            patch.object(model.fee_source, "validate_coverage", return_value=(fee_daily, coverage)),
            patch.object(model.btc, "build_archive_specs", return_value=[spec]),
            patch.object(model.btc, "download_binance_archive", return_value=(prices, row)),
        ):
            _, returned_prices, sources = model.fetch_sources()
        fee_fetch.assert_called_once_with()
        self.assertEqual(len(returned_prices), len(prices))
        self.assertEqual(sources["BTCUSDT"]["archive_count"], 1)
        self.assertEqual(sources["fee_rate"]["api_requests"], 1)
        self.assertEqual(sources["fee_rate"]["retry_count"], 0)

    def test_source_fetch_fails_closed_when_archive_hash_differs(self):
        start = model.MODEL_START
        end = dt.date(2026, 11, 25)
        fee_daily = {
            start + dt.timedelta(days=i): 5.0
            for i in range((dt.date(2026, 11, 26) - start).days + 1)
        }
        prices = {
            start + dt.timedelta(days=i): 30_000.0 + i
            for i in range((end - start).days + 1)
        }
        accepted_row = {
            "url": "https://example.test/a.zip",
            "archive_sha256": "a" * 64,
            "checksum_sha256": "b" * 64,
        }
        changed_row = {**accepted_row, "archive_sha256": "c" * 64, "checksum_verified": True}
        accepted = {
            "requested_end": end.isoformat(),
            "archive_manifest_sha256": model.ACCEPTED_PRICE_ARCHIVE_MANIFEST_SHA256,
            "archives": [accepted_row],
        }
        with (
            patch.object(model, "load_accepted_price_evidence", return_value=accepted),
            patch.object(model.fee_source, "fetch_fee_rate_payload", return_value=(b"x", 200, model.fee_source.ENDPOINT, {})),
            patch.object(model.fee_source, "parse_fee_rate_payload", return_value=({}, {})),
            patch.object(model.fee_source, "validate_coverage", return_value=(fee_daily, {"first_utc_date": start.isoformat(), "last_utc_date": "2026-11-26", "unique_utc_dates": len(fee_daily)})),
            patch.object(model.btc, "build_archive_specs", return_value=[{"url": accepted_row["url"], "tag": "x", "kind": "monthly"}]),
            patch.object(model.btc, "download_binance_archive", return_value=(prices, changed_row)),
        ):
            with self.assertRaisesRegex(model.SourceInfeasibleError, "differs from previously accepted"):
                model.fetch_sources()


if __name__ == "__main__":
    unittest.main()
