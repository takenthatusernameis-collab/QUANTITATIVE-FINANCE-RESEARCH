from __future__ import annotations

import datetime as dt
import json
import math
import unittest

import ust_10y_basis_crowding_sp500_volatility as model


class Ust10yBasisCrowdingTests(unittest.TestCase):
    @staticmethod
    def cftc_row(report_date="2020-01-07T00:00:00.000", code="043602", name="UST 10Y NOTE - CHICAGO BOARD OF TRADE"):
        return {
            "report_date_as_yyyy_mm_dd": report_date,
            "contract_market_name": name,
            "cftc_contract_market_code": code,
            "open_interest_all": "1000",
            "lev_money_positions_long": "300",
            "lev_money_positions_short": "600",
        }

    @staticmethod
    def market_data(start=dt.date(2019, 10, 1), end=dt.date(2020, 5, 31)):
        prices = {}
        vix = {}
        day = start
        index = 0
        while day <= end:
            if day.weekday() < 5:
                prices[day] = 100.0 + index * 0.1 + math.sin(index / 5.0)
                vix[day] = 18.0 + 2.0 * math.sin(index / 13.0)
                index += 1
            day += dt.timedelta(days=1)
        return prices, vix

    def test_parse_cftc_uses_exact_10y_code_and_signed_net_short_share(self):
        payload = [
            self.cftc_row(),
            self.cftc_row(code="043607", name="ULTRA UST 10Y - CHICAGO BOARD OF TRADE"),
        ]
        rows = model.parse_cftc(json.dumps(payload).encode())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cftc_contract_market_code"], "043602")
        self.assertEqual(rows[0]["net_short"], 300)
        self.assertAlmostEqual(rows[0]["net_short_pct_oi"], 0.3)

    def test_parse_cftc_accepts_historical_10_year_label(self):
        row = self.cftc_row(name="10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE")
        rows = model.parse_cftc(json.dumps([row]).encode())
        self.assertEqual(len(rows), 1)

    def test_parse_cftc_rejects_unexpected_market_name_for_exact_code(self):
        row = self.cftc_row(name="5-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE")
        with self.assertRaisesRegex(ValueError, "Unexpected market name"):
            model.parse_cftc(json.dumps([row]).encode())

    def test_parse_cftc_rejects_duplicate_report_dates(self):
        row = self.cftc_row()
        with self.assertRaisesRegex(ValueError, "Duplicate CFTC report dates"):
            model.parse_cftc(json.dumps([row, row]).encode())

    def test_parse_cftc_fails_closed_on_invalid_open_interest(self):
        row = self.cftc_row()
        row["open_interest_all"] = "0"
        with self.assertRaisesRegex(ValueError, "Invalid open interest"):
            model.parse_cftc(json.dumps([row]).encode())

    def test_crowding_percentile_uses_only_prior_signed_net_short_reports(self):
        start = dt.date(2006, 6, 13)
        rows = [
            {"report_date": start + dt.timedelta(days=7 * i), "net_short_pct_oi": 0.1}
            for i in range(model.CROWDING_LOOKBACK)
        ]
        rows.append({
            "report_date": start + dt.timedelta(days=7 * model.CROWDING_LOOKBACK),
            "net_short_pct_oi": 0.2,
        })
        features = model.build_crowding_features(rows)
        self.assertIsNone(features[0]["net_short_percentile"])
        self.assertEqual(features[-1]["net_short_percentile"], 1.0)
        self.assertTrue(features[-1]["high_crowding"])

    def test_net_long_observation_is_not_reclassified_as_absolute_crowding(self):
        start = dt.date(2006, 6, 13)
        rows = [
            {"report_date": start + dt.timedelta(days=7 * i), "net_short_pct_oi": 0.1}
            for i in range(model.CROWDING_LOOKBACK)
        ]
        rows.append({
            "report_date": start + dt.timedelta(days=7 * model.CROWDING_LOOKBACK),
            "net_short_pct_oi": -0.2,
        })
        features = model.build_crowding_features(rows)
        self.assertEqual(features[-1]["net_short_percentile"], 0.0)
        self.assertFalse(features[-1]["high_crowding"])

    def test_known_backlog_is_excluded_from_feature_history(self):
        start = dt.date(2006, 6, 13)
        rows = [
            {"report_date": start + dt.timedelta(days=7 * i), "net_short_pct_oi": 0.1}
            for i in range(model.CROWDING_LOOKBACK)
        ]
        rows.append({
            "report_date": model.BACKLOG_START,
            "net_short_pct_oi": 0.99,
        })
        rows.append({
            "report_date": model.BACKLOG_END + dt.timedelta(days=7),
            "net_short_pct_oi": 0.2,
        })
        features = model.build_crowding_features(rows)
        self.assertIsNone(features[-2]["net_short_percentile"])
        self.assertEqual(features[-1]["net_short_percentile"], 1.0)
        self.assertTrue(features[-1]["high_crowding"])

    def test_backlog_boundary_is_fixed(self):
        self.assertTrue(model.is_backlog_report(dt.date(2025, 9, 30)))
        self.assertTrue(model.is_backlog_report(dt.date(2026, 1, 20)))
        self.assertFalse(model.is_backlog_report(dt.date(2025, 9, 23)))
        self.assertFalse(model.is_backlog_report(dt.date(2026, 1, 27)))

    def test_parse_fred_series_uses_named_series_and_unique_dates(self):
        body = (
            "observation_date,SP500\n"
            "2020-01-02,3000\n"
            "2020-01-03,3010\n"
        ).encode()
        values = model.parse_fred_series(body, "SP500")
        self.assertEqual(len(values), 2)
        self.assertEqual(values[dt.date(2020, 1, 2)], 3000.0)

    def test_realized_volatility_uses_root_sum_squared_returns_in_percent(self):
        actual = model.realized_volatility([0.01, -0.02, 0.0])
        expected = math.sqrt(0.01 ** 2 + 0.02 ** 2) * 100.0
        self.assertAlmostEqual(actual, expected)

    def test_realized_volatility_rejects_missing_return(self):
        with self.assertRaisesRegex(ValueError, "missing or invalid"):
            model.realized_volatility([0.01, None, -0.02])

    def test_signal_uses_first_close_after_fourteen_day_lag_and_same_date_vix(self):
        prices, vix = self.market_data()
        cot = [{
            "report_date": dt.date(2020, 1, 7),
            "net_short_pct_oi": 0.3,
            "net_short_percentile": 0.95,
            "high_crowding": True,
        }]
        events, meta = model.build_events(cot, prices, vix)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["availability_date"], dt.date(2020, 1, 21))
        self.assertGreaterEqual(events[0]["signal_date"], dt.date(2020, 1, 21))
        self.assertGreater(events[0]["target_start_date"], events[0]["signal_date"])
        self.assertEqual((events[0]["target_end_date"] - events[0]["target_start_date"]).days, 6)
        self.assertIn("log_vix", events[0])
        self.assertEqual(events[0]["record_date"] if "record_date" in events[0] else events[0]["signal_date"], events[0]["signal_date"])

    def test_missing_signal_date_vix_is_not_filled_or_forward_filled(self):
        prices, vix = self.market_data()
        vix.pop(dt.date(2020, 1, 21), None)
        cot = [{
            "report_date": dt.date(2020, 1, 7),
            "net_short_pct_oi": 0.3,
            "net_short_percentile": 0.95,
            "high_crowding": True,
        }]
        events, meta = model.build_events(cot, prices, vix)
        self.assertEqual(events, [])
        self.assertEqual(meta["skipped"]["missing_vix_on_signal_date"], 1)

    def test_overlapping_five_session_targets_are_excluded(self):
        prices, vix = self.market_data()
        cot = [
            {
                "report_date": dt.date(2020, 1, 7),
                "net_short_pct_oi": 0.3,
                "net_short_percentile": 0.95,
                "high_crowding": True,
            },
            {
                "report_date": dt.date(2020, 1, 8),
                "net_short_pct_oi": 0.1,
                "net_short_percentile": 0.1,
                "high_crowding": False,
            },
        ]
        events, meta = model.build_events(cot, prices, vix)
        self.assertEqual(len(events), 1)
        self.assertEqual(meta["skipped"]["overlapping_target_window"], 1)

    def test_walk_forward_requires_104_fully_matured_training_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "report_date": signal - dt.timedelta(days=14),
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.1 + index * 0.002,
                "target_rv_pct": 1.0 + index * 0.01,
                "net_short_pct_oi": 0.1 + (index % 7) * 0.01,
                "net_short_percentile": (index % 20) / 20.0,
                "high_crowding": index % 10 == 0,
                "pre_rv5_log": 0.1 + (index % 13) * 0.01,
                "pre_rv20_log": 0.2 + (index % 17) * 0.01,
                "log_vix": 2.5 + (index % 11) * 0.01,
            })
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_training_target_ending_on_current_signal(self):
        events = []
        start = dt.date(2020, 1, 1)
        current_signal = start + dt.timedelta(days=7 * model.MODEL_WINDOW)
        for index in range(model.MODEL_WINDOW):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "report_date": signal - dt.timedelta(days=14),
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": current_signal,
                "target_bp": 0.1 + index * 0.002,
                "target_rv_pct": 1.0 + index * 0.01,
                "net_short_pct_oi": 0.1 + (index % 7) * 0.01,
                "net_short_percentile": (index % 20) / 20.0,
                "high_crowding": index % 10 == 0,
                "pre_rv5_log": 0.1 + (index % 13) * 0.01,
                "pre_rv20_log": 0.2 + (index % 17) * 0.01,
                "log_vix": 2.5 + (index % 11) * 0.01,
            })
        current = {
            "report_date": current_signal - dt.timedelta(days=14),
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=5),
            "target_bp": 0.3,
            "target_rv_pct": 1.3,
            "net_short_pct_oi": 0.4,
            "net_short_percentile": 0.95,
            "high_crowding": True,
            "pre_rv5_log": 0.3,
            "pre_rv20_log": 0.4,
            "log_vix": 2.8,
        }
        self.assertEqual(model.walk_forward_predictions(events + [current]), [])

    def test_decision_does_not_promote_without_minimum_sample(self):
        validation = {
            "n": 29,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.5},
        }
        test = {
            "n": 29,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.5},
        }
        paired = {"ci_95_low": 0.1, "ci_95_high": 0.2}
        event_study = {"high_minus_other_mean_rv_pct": 0.5, "ci_95_low_rv_pct": 0.1, "ci_95_high_rv_pct": 0.8}
        status, _ = model.decide(validation, test, paired, event_study)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_decision_remains_inconclusive_when_event_study_interval_crosses_zero(self):
        validation = {
            "n": 50,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.9},
        }
        test = {
            "n": 60,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.9},
        }
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.2}
        event_study = {"high_minus_other_mean_rv_pct": 0.5, "ci_95_low_rv_pct": -0.1, "ci_95_high_rv_pct": 0.8}
        status, _ = model.decide(validation, test, paired, event_study)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_decision_requires_all_frozen_promotion_conditions(self):
        validation = {
            "n": 50,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.9},
        }
        test = {
            "n": 60,
            "baseline": {"rmse_log1p_rv": 1.0},
            "augmented": {"rmse_log1p_rv": 0.9},
        }
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.2}
        event_study = {"high_minus_other_mean_rv_pct": 0.5, "ci_95_low_rv_pct": 0.1, "ci_95_high_rv_pct": 0.8}
        status, _ = model.decide(validation, test, paired, event_study)
        self.assertEqual(status, "BACKTESTED")


    def test_source_coverage_rejects_stale_cftc_reports(self):
        today = dt.date(2026, 11, 25)
        latest_cftc = today - dt.timedelta(days=30)
        cot_rows = [
            {"report_date": latest_cftc - dt.timedelta(days=7 * (1059 - index))}
            for index in range(1060)
        ]
        start = dt.date(2016, 11, 25)
        end = dt.date(2026, 11, 24)
        span = (end - start).days
        prices = {}
        vix = {}
        for index in range(1500):
            day = start + dt.timedelta(days=round(span * index / 1499))
            prices[day] = 100.0 + index
            vix[day] = 15.0 + index / 100.0
        with self.assertRaisesRegex(ValueError, "CFTC latest report is stale"):
            model.validate_source_coverage(cot_rows, prices, vix, today)


if __name__ == "__main__":
    unittest.main()
