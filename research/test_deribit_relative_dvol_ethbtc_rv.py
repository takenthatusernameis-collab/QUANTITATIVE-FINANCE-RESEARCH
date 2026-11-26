from __future__ import annotations

import datetime as dt
import json
import math
import unittest
from unittest.mock import patch

import deribit_relative_dvol_ethbtc_rv as model


class DeribitRelativeDvolTests(unittest.TestCase):
    def _prices(self, count=700):
        start = dt.date(2023, 3, 26)
        btc, eth = {}, {}
        for index in range(count):
            day = start + dt.timedelta(days=index)
            btc[day] = 30000.0 * math.exp(0.0002 * index + 0.018 * math.sin(index / 13.0) + 0.006 * math.cos(index / 5.0))
            eth[day] = 1800.0 * math.exp(0.0003 * index + 0.023 * math.sin(index / 9.0) + 0.008 * math.cos(index / 6.0))
        return btc, eth

    def _dvol(self, count=700):
        start = dt.date(2023, 3, 26)
        btc, eth = {}, {}
        for index in range(count):
            day = start + dt.timedelta(days=index)
            btc[day] = 0.48 + 0.035 * math.sin(index / 17.0) + 0.012 * math.cos(index / 8.0)
            eth[day] = 0.69 + 0.052 * math.sin(index / 19.0) + 0.018 * math.cos(index / 7.0)
        return btc, eth

    def test_parse_fred_accepts_observation_date_and_skips_missing(self):
        body = b"observation_date,CBETHUSD\n2023-03-26,1800\n2023-03-27,.\n2023-03-28,1810\n"
        parsed = model.parse_fred_series(body, "CBETHUSD")
        self.assertEqual(len(parsed), 2)
        self.assertNotIn(dt.date(2023, 3, 27), parsed)

    def test_parse_fred_rejects_duplicate_dates(self):
        body = b"observation_date,CBBTCUSD\n2023-03-26,30000\n2023-03-26,30100\n"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(body, "CBBTCUSD")

    def test_parse_fred_rejects_nonpositive_prices(self):
        body = b"observation_date,CBBTCUSD\n2023-03-26,0\n"
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_fred_series(body, "CBBTCUSD")

    def test_parse_dvol_page_validates_daily_ohlc_and_continuation(self):
        day = dt.date(2023, 3, 26)
        stamp = model.utc_midnight_ms(day)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "data": [[stamp, 0.5, 0.6, 0.4, 0.55]],
                "continuation": stamp,
            },
        }
        rows, continuation = model.parse_dvol_page(
            json.dumps(payload).encode(), "BTC", stamp, stamp + model.DAY_MS - 1
        )
        self.assertEqual(rows[0]["date"], day)
        self.assertEqual(rows[0]["close"], 0.55)
        self.assertEqual(continuation, stamp)

    def test_parse_dvol_rejects_malformed_ohlc(self):
        day = dt.date(2023, 3, 26)
        stamp = model.utc_midnight_ms(day)
        payload = {"jsonrpc": "2.0", "result": {"data": [[stamp, 0.5, 0.4, 0.3, 0.55]], "continuation": None}}
        with self.assertRaisesRegex(ValueError, "OHLC ordering"):
            model.parse_dvol_page(json.dumps(payload).encode(), "ETH", stamp, stamp + model.DAY_MS - 1)

    def test_parse_dvol_rejects_api_error(self):
        payload = {"jsonrpc": "2.0", "error": {"code": 10001, "message": "bad request"}}
        with self.assertRaisesRegex(ValueError, "API error"):
            model.parse_dvol_page(json.dumps(payload).encode(), "BTC", 0, model.DAY_MS)

    def test_dvol_pagination_uses_continuation_and_deduplicates_boundary(self):
        start = dt.date(2023, 3, 26)
        first_ms = model.utc_midnight_ms(start)
        second_ms = model.utc_midnight_ms(start + dt.timedelta(days=1))
        page1 = json.dumps({
            "jsonrpc": "2.0",
            "result": {"data": [[second_ms, 0.5, 0.6, 0.4, 0.55]], "continuation": first_ms},
        }).encode()
        page2 = json.dumps({
            "jsonrpc": "2.0",
            "result": {"data": [[first_ms, 0.51, 0.61, 0.41, 0.56]], "continuation": None},
        }).encode()
        with patch.object(model, "fetch_dvol_page", side_effect=[page1, page2]) as fetch:
            values, metadata = model.fetch_dvol_history("BTC", start, start + dt.timedelta(days=1))
        self.assertEqual(len(values), 2)
        self.assertEqual(metadata["rows"], 2)
        self.assertEqual(fetch.call_count, 2)

    def test_dvol_scale_normalizes_decimal_fraction_and_percentage_points(self):
        start = dt.date(2023, 3, 26)
        fractional = {start: 0.5, start + dt.timedelta(days=1): 0.6}
        normalized, scale, factor = model.normalize_dvol_scale(fractional)
        self.assertEqual(scale, "decimal_fraction")
        self.assertEqual(factor, 100.0)
        self.assertAlmostEqual(normalized[start], 50.0)
        points = {start: 50.0, start + dt.timedelta(days=1): 60.0}
        normalized_points, scale_points, factor_points = model.normalize_dvol_scale(points)
        self.assertEqual(scale_points, "percentage_points")
        self.assertEqual(factor_points, 1.0)
        self.assertEqual(normalized_points, points)

    def test_build_events_uses_strictly_prior_common_dvol_and_nonoverlapping_targets(self):
        btc, eth = self._prices()
        btc_dvol, eth_dvol = self._dvol()
        events, metadata = model.build_events(btc, eth, btc_dvol, eth_dvol)
        self.assertGreater(len(events), 50)
        self.assertEqual(events[0]["signal_date"], dt.date(2023, 4, 25))
        self.assertEqual(events[0]["dvol_observation_date"], dt.date(2023, 4, 24))
        for event in events:
            self.assertLess(event["dvol_observation_date"], event["signal_date"])
            self.assertLess(event["target_start_date"], event["target_end_date"])
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["target_start_date"])
        self.assertEqual(metadata["events"], len(events))
        self.assertEqual(metadata["skipped"]["overlapping_target_window"], 0)

    def test_same_date_dvol_is_never_used(self):
        btc, eth = self._prices()
        btc_dvol, eth_dvol = self._dvol()
        events, _ = model.build_events(btc, eth, btc_dvol, eth_dvol)
        same_date_candidates = [event for event in events if event["signal_date"] in btc_dvol]
        self.assertTrue(same_date_candidates)
        for event in same_date_candidates:
            self.assertLess(event["dvol_observation_date"], event["signal_date"])

    def test_missing_common_price_day_fails_closed(self):
        btc, eth = self._prices(100)
        btc_dvol, eth_dvol = self._dvol(100)
        missing = dt.date(2023, 4, 10)
        del eth[missing]
        with self.assertRaisesRegex(ValueError, "calendar gap"):
            model.build_events(btc, eth, btc_dvol, eth_dvol)

    def test_stale_common_dvol_is_skipped_not_forward_filled(self):
        btc, eth = self._prices(180)
        btc_dvol, eth_dvol = self._dvol(180)
        btc_dvol = {day: value for day, value in btc_dvol.items() if day.day % 3 == 0}
        eth_dvol = {day: value for day, value in eth_dvol.items() if day.day % 3 == 0}
        events, metadata = model.build_events(btc, eth, btc_dvol, eth_dvol)
        self.assertGreater(metadata["skipped"]["stale_common_dvol"], 0)
        self.assertTrue(all((event["signal_date"] - event["dvol_observation_date"]).days <= 2 for event in events))

    def test_walk_forward_requires_52_fully_matured_prior_events(self):
        events = []
        start = dt.date(2024, 1, 1)
        for index in range(model.MODEL_WINDOW + 2):
            signal = start + dt.timedelta(days=7 * index)
            x1 = math.sin(index * 0.37)
            x2 = math.cos(index * 0.19)
            x3 = 1.0 + (index % 11) * 0.03
            x4 = 1.4 + (index % 13) * 0.02
            x5 = math.sin(index * 0.11) + 0.2 * math.cos(index * 0.07)
            target = 0.3 * x1 - 0.2 * x2 + 0.1 * x3 + 0.2 * x4 - 0.4 * x5
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=7),
                "target_log_relative_rv": target,
                "pre_btc_rv7_log": x1,
                "pre_btc_rv30_log": x2,
                "pre_eth_rv7_log": x3,
                "pre_eth_rv30_log": x4,
                "relative_dvol_log_ratio": x5,
            })
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_target_ending_on_current_signal(self):
        events = []
        start = dt.date(2024, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=7),
                "target_log_relative_rv": float(index % 5),
                "pre_btc_rv7_log": math.sin(index * 0.31),
                "pre_btc_rv30_log": math.cos(index * 0.17),
                "pre_eth_rv7_log": 1.0 + (index % 9) * 0.02,
                "pre_eth_rv30_log": 1.2 + (index % 7) * 0.03,
                "relative_dvol_log_ratio": math.sin(index * 0.13),
            })
        current_signal = start + dt.timedelta(days=7 * model.MODEL_WINDOW)
        events.append({
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=7),
            "target_log_relative_rv": 0.2,
            "pre_btc_rv7_log": 0.1,
            "pre_btc_rv30_log": 0.2,
            "pre_eth_rv7_log": 1.1,
            "pre_eth_rv30_log": 1.3,
            "relative_dvol_log_ratio": 0.05,
        })
        self.assertEqual(model.walk_forward_predictions(events), [])

    def test_paired_bootstrap_is_reproducible_and_positive_when_augmented_is_better(self):
        rows = []
        for index in range(60):
            target = float((index % 9) - 4)
            rows.append({
                "target_log_relative_rv": target,
                "baseline_prediction": target + 2.0 + (index % 3) * 0.1,
                "augmented_prediction": target + 0.5 + (index % 2) * 0.1,
            })
        first = model.paired_loss_bootstrap(rows)
        second = model.paired_loss_bootstrap(rows)
        self.assertEqual(first, second)
        self.assertGreater(first["mean_baseline_minus_augmented_squared_loss"], 0)
        self.assertGreater(first["ci95_low"], 0)

    def test_decision_is_inconclusive_when_paired_interval_crosses_zero(self):
        validation = {"n": 50, "baseline": {"rmse_log_relative_rv": 1.0}, "augmented": {"rmse_log_relative_rv": 0.9}}
        test = {"n": 50, "baseline": {"rmse_log_relative_rv": 1.0}, "augmented": {"rmse_log_relative_rv": 0.95}}
        paired = {"ci95_low": -0.1, "ci95_high": 0.2}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_decision_rejects_only_with_consistent_negative_evidence(self):
        validation = {"n": 50, "baseline": {"rmse_log_relative_rv": 1.0}, "augmented": {"rmse_log_relative_rv": 1.1}}
        test = {"n": 50, "baseline": {"rmse_log_relative_rv": 1.0}, "augmented": {"rmse_log_relative_rv": 1.1}}
        paired = {"ci95_low": -0.3, "ci95_high": -0.1}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "REJECTED")


if __name__ == "__main__":
    unittest.main()
