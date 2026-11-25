from __future__ import annotations

import datetime as dt
import json
import math
import unittest

import cftc_sp500_crowding_volatility as model


class CftcSp500CrowdingTests(unittest.TestCase):
    def test_parse_cftc_filters_exact_eminisp_code_and_uses_outright_positions(self):
        payload = [
            {
                "report_date_as_yyyy_mm_dd": "2020-01-07T00:00:00.000",
                "contract_market_name": "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
                "cftc_contract_market_code": "13874A",
                "open_interest_all": "1000",
                "lev_money_positions_long": "600",
                "lev_money_positions_short": "300",
            },
            {
                "report_date_as_yyyy_mm_dd": "2020-01-07T00:00:00.000",
                "contract_market_name": "MICRO E-MINI S&P 500 INDEX - CHICAGO MERCANTILE EXCHANGE",
                "cftc_contract_market_code": "13874U",
                "open_interest_all": "10000",
                "lev_money_positions_long": "9000",
                "lev_money_positions_short": "1000",
            },
        ]
        rows = model.parse_cftc(json.dumps(payload).encode())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cftc_contract_market_code"], "13874A")
        self.assertEqual(rows[0]["lev_money_net"], 300)
        self.assertAlmostEqual(rows[0]["net_pct_oi"], 0.3)

    def test_parse_cftc_rejects_duplicate_report_dates(self):
        base = {
            "report_date_as_yyyy_mm_dd": "2020-01-07",
            "contract_market_name": "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
            "cftc_contract_market_code": "13874A",
            "open_interest_all": "1000",
            "lev_money_positions_long": "600",
            "lev_money_positions_short": "300",
        }
        with self.assertRaisesRegex(ValueError, "Duplicate CFTC report dates"):
            model.parse_cftc(json.dumps([base, base]).encode())

    def test_parse_cftc_fails_closed_on_invalid_open_interest(self):
        row = {
            "report_date_as_yyyy_mm_dd": "2020-01-07",
            "contract_market_name": "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
            "cftc_contract_market_code": "13874A",
            "open_interest_all": "0",
            "lev_money_positions_long": "600",
            "lev_money_positions_short": "300",
        }
        with self.assertRaisesRegex(ValueError, "Invalid open interest"):
            model.parse_cftc(json.dumps([row]).encode())

    def test_crowding_percentile_uses_only_prior_reports(self):
        rows = []
        start = dt.date(2006, 6, 13)
        for index in range(model.CROWDING_LOOKBACK):
            rows.append({
                "report_date": start + dt.timedelta(days=7 * index),
                "abs_net_pct_oi": 0.8,
            })
        rows.append({
            "report_date": start + dt.timedelta(days=7 * model.CROWDING_LOOKBACK),
            "abs_net_pct_oi": 0.1,
        })
        features = model.build_crowding_features(rows)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]["crowding_percentile"], 0.0)
        self.assertFalse(features[0]["high_crowding"])

    def test_known_backlog_is_excluded(self):
        self.assertTrue(model.is_backlog_report(dt.date(2025, 9, 30)))
        self.assertTrue(model.is_backlog_report(dt.date(2026, 1, 20)))
        self.assertFalse(model.is_backlog_report(dt.date(2025, 9, 23)))
        self.assertFalse(model.is_backlog_report(dt.date(2026, 1, 27)))

    def test_realized_volatility_uses_root_sum_squared_returns_in_percent(self):
        actual = model.realized_volatility([0.01, -0.02, 0.0])
        expected = math.sqrt(0.01 ** 2 + 0.02 ** 2) * 100.0
        self.assertAlmostEqual(actual, expected)

    def test_realized_volatility_rejects_missing_return(self):
        with self.assertRaisesRegex(ValueError, "missing or invalid"):
            model.realized_volatility([0.01, None, -0.02])

    def test_signal_uses_first_close_after_fourteen_day_availability_lag(self):
        start = dt.date(2020, 1, 1)
        prices = {}
        day = start
        index = 0
        while day <= dt.date(2020, 5, 31):
            if day.weekday() < 5:
                prices[day] = 100.0 + index * 0.1 + math.sin(index / 5.0)
                index += 1
            day += dt.timedelta(days=1)
        cot = [{
            "report_date": dt.date(2020, 1, 7),
            "crowding_percentile": 0.95,
            "high_crowding": True,
            "abs_net_pct_oi": 0.8,
            "net_pct_oi": -0.8,
        }]
        events, meta = model.build_events(cot, prices)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["availability_date"], dt.date(2020, 1, 21))
        self.assertGreaterEqual(events[0]["signal_date"], dt.date(2020, 1, 21))
        self.assertGreater(events[0]["target_start_date"], events[0]["signal_date"])
        self.assertEqual((events[0]["target_end_date"] - events[0]["target_start_date"]).days, 7)
        self.assertEqual(events[0]["record_date"], events[0]["signal_date"])

    def test_overlapping_five_session_targets_are_excluded(self):
        start = dt.date(2020, 1, 1)
        prices = {}
        day = start
        index = 0
        while day <= dt.date(2020, 5, 31):
            if day.weekday() < 5:
                prices[day] = 100.0 + index * 0.1 + math.sin(index / 5.0)
                index += 1
            day += dt.timedelta(days=1)
        cot = [
            {
                "report_date": dt.date(2020, 1, 7),
                "crowding_percentile": 0.95,
                "high_crowding": True,
                "abs_net_pct_oi": 0.8,
                "net_pct_oi": -0.8,
            },
            {
                "report_date": dt.date(2020, 1, 8),
                "crowding_percentile": 0.10,
                "high_crowding": False,
                "abs_net_pct_oi": 0.1,
                "net_pct_oi": 0.1,
            },
        ]
        events, meta = model.build_events(cot, prices)
        self.assertEqual(len(events), 1)
        self.assertEqual(meta["skipped"]["overlapping_target_window"], 1)

    def test_walk_forward_requires_104_fully_matured_training_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=7 * index)
            events.append({
                "report_date": signal - dt.timedelta(days=14),
                "record_date": signal,
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.1 + index * 0.002,
                "target_rv_pct": 1.0 + index * 0.01,
                "crowding_percentile": (index % 20) / 20.0,
                "high_crowding": index % 10 == 0,
                "pre_rv5_log": 0.1 + (index % 13) * 0.01,
                "pre_rv20_log": 0.2 + (index % 17) * 0.01,
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
                "record_date": signal,
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": current_signal,
                "target_bp": 0.1 + index * 0.002,
                "target_rv_pct": 1.0 + index * 0.01,
                "crowding_percentile": (index % 20) / 20.0,
                "high_crowding": index % 10 == 0,
                "pre_rv5_log": 0.1 + (index % 13) * 0.01,
                "pre_rv20_log": 0.2 + (index % 17) * 0.01,
            })
        current = {
            "report_date": current_signal - dt.timedelta(days=14),
            "record_date": current_signal,
            "signal_date": current_signal,
            "target_start_date": current_signal + dt.timedelta(days=1),
            "target_end_date": current_signal + dt.timedelta(days=5),
            "target_bp": 0.3,
            "target_rv_pct": 1.3,
            "crowding_percentile": 0.95,
            "high_crowding": True,
            "pre_rv5_log": 0.3,
            "pre_rv20_log": 0.4,
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
        paired = {"ci_95_low": 0.1}
        event_study = {"high_minus_other_mean_rv_pct": 0.5, "ci_95_low_rv_pct": 0.1}
        status, _ = model.decide(validation, test, paired, event_study)
        self.assertEqual(status, "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
