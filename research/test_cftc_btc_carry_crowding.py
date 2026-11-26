from __future__ import annotations
import datetime as dt, json, math, unittest
import cftc_btc_carry_crowding as model


class CftcBitcoinCarryCrowdingTests(unittest.TestCase):
    def _row(self, day=dt.date(2020, 1, 7), short=600, oi=1000, code="133741", name="BITCOIN"):
        return {"report_date_as_yyyy_mm_dd": day.isoformat() + "T00:00:00.000",
                "contract_market_name": name, "cftc_contract_market_code": code,
                "open_interest_all": str(oi), "lev_money_positions_short": str(short)}

    def test_parser_selects_exact_cme_bitcoin_code_and_gross_short_share(self):
        rows = model.parse_cftc(json.dumps([self._row(), self._row(code="13874A", name="E-MINI S&P 500")]).encode())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gross_short_pct_oi"], 0.6)

    def test_parser_rejects_duplicate_dates(self):
        row = self._row()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_cftc(json.dumps([row, row]).encode())

    def test_parser_rejects_non_tuesday(self):
        with self.assertRaisesRegex(ValueError, "non-Tuesday"):
            model.parse_cftc(json.dumps([self._row(day=dt.date(2020, 1, 8))]).encode())

    def test_parser_allows_documented_non_tuesday_shutdown_catch_up_report(self):
        rows = model.parse_cftc(json.dumps([self._row(day=dt.date(2025, 11, 10))]).encode())
        self.assertEqual(rows[0]["report_date"], dt.date(2025, 11, 10))

    def test_parser_rejects_zero_open_interest(self):
        with self.assertRaisesRegex(ValueError, "open interest"):
            model.parse_cftc(json.dumps([self._row(oi=0)]).encode())

    def test_parser_rejects_short_above_open_interest(self):
        with self.assertRaisesRegex(ValueError, "gross short"):
            model.parse_cftc(json.dumps([self._row(short=1001)]).encode())

    def test_shutdown_backlog_dates_are_excluded(self):
        self.assertTrue(model.is_backlog_report(dt.date(2025, 9, 30)))
        self.assertTrue(model.is_backlog_report(dt.date(2026, 1, 20)))
        self.assertFalse(model.is_backlog_report(dt.date(2025, 9, 23)))
        self.assertFalse(model.is_backlog_report(dt.date(2026, 1, 27)))

    def test_percentile_uses_prior_52_observations_only(self):
        start = dt.date(2018, 4, 10)
        rows = [{"report_date": start + dt.timedelta(days=7*i), "gross_short_pct_oi": 0.2 + i/1000}
                for i in range(model.CROWDING_LOOKBACK)]
        rows.append({"report_date": start + dt.timedelta(days=7*model.CROWDING_LOOKBACK), "gross_short_pct_oi": 0.1})
        features = model.build_crowding_features(rows)
        self.assertTrue(all(x["gross_short_pct_oi_percentile"] is None for x in features[:52]))
        self.assertEqual(features[-1]["gross_short_pct_oi_percentile"], 0.0)

    def test_current_position_is_excluded_from_its_own_history(self):
        start = dt.date(2018, 4, 10)
        rows = [{"report_date": start + dt.timedelta(days=7*i), "gross_short_pct_oi": 0.2}
                for i in range(model.CROWDING_LOOKBACK)]
        rows.append({"report_date": start + dt.timedelta(days=7*model.CROWDING_LOOKBACK), "gross_short_pct_oi": 0.9})
        features = model.build_crowding_features(rows)
        self.assertEqual(features[-1]["gross_short_pct_oi_percentile"], 1.0)
        self.assertTrue(features[-1]["high_crowding"])

    def test_backlog_rows_are_not_added_to_percentile_history(self):
        prior_start = dt.date(2024, 10, 1)
        prior = [{"report_date": prior_start + dt.timedelta(days=7*i), "gross_short_pct_oi": 0.5}
                 for i in range(model.CROWDING_LOOKBACK)]
        backlog_start = dt.date(2025, 9, 30)
        backlog = [{"report_date": backlog_start + dt.timedelta(days=7*i), "gross_short_pct_oi": 0.9}
                   for i in range(17)]
        post = {"report_date": dt.date(2026, 1, 27), "gross_short_pct_oi": 0.6}
        features = model.build_crowding_features(prior + backlog + [post])
        backlog_features = [x for x in features if x["excluded_publication_backlog"]]
        self.assertEqual(len(backlog_features), 17)
        post_feature = features[-1]
        self.assertEqual(post_feature["percentile_history_n"], model.CROWDING_LOOKBACK)
        self.assertEqual(post_feature["percentile_history_start"], prior_start.isoformat())

    def _prices(self, start=dt.date(2019, 10, 1), end=dt.date(2020, 5, 31)):
        out, day, i = {}, start, 0
        while day <= end:
            out[day] = 10000.0 * math.exp(0.0004*i + 0.025*math.sin(i/13.0) + 0.01*math.cos(i/5.0))
            day += dt.timedelta(days=1)
            i += 1
        return out

    def _event_row(self, day, percentile=0.95):
        return {"report_date": day, "gross_short_pct_oi_percentile": percentile,
                "high_crowding": percentile >= model.HIGH_CROWDING_THRESHOLD,
                "excluded_publication_backlog": False, "percentile_history_n": 52,
                "percentile_history_start": (day-dt.timedelta(days=364)).isoformat()}

    def test_signal_respects_14_day_publication_lag_and_five_day_target(self):
        events, meta = model.build_events([self._event_row(dt.date(2020, 1, 7))],
                                          self._prices(), dt.date(2020, 5, 31))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["availability_date"], dt.date(2020, 1, 21))
        self.assertEqual(events[0]["signal_date"], dt.date(2020, 1, 21))
        self.assertEqual(events[0]["target_start_date"], dt.date(2020, 1, 22))
        self.assertEqual(events[0]["target_end_date"], dt.date(2020, 1, 26))

    def test_backlog_event_is_never_used(self):
        prices = self._prices(dt.date(2025, 9, 1), dt.date(2026, 3, 1))
        events, meta = model.build_events([self._event_row(dt.date(2025, 9, 30))], prices, dt.date(2026, 3, 1))
        self.assertEqual(events, [])
        self.assertEqual(meta["skipped"]["known_publication_backlog"], 1)

    def test_weekly_targets_do_not_overlap(self):
        prices = self._prices(dt.date(2019, 12, 1), dt.date(2020, 4, 30))
        rows = [self._event_row(dt.date(2020, 1, d)) for d in (7, 14, 21)]
        events, _ = model.build_events(rows, prices, dt.date(2020, 4, 30))
        self.assertEqual(len(events), 3)
        for a, b in zip(events, events[1:]):
            self.assertLess(a["target_end_date"], b["signal_date"])

    def test_walk_forward_requires_52_fully_matured_training_events(self):
        events, start = [], dt.date(2020, 1, 1)
        for i in range(model.MODEL_WINDOW + 1):
            signal = start + dt.timedelta(days=7*i)
            events.append({"report_date": signal-dt.timedelta(days=14), "signal_date": signal,
                           "target_start_date": signal+dt.timedelta(days=1), "target_end_date": signal+dt.timedelta(days=5),
                           "target_bp": 0.1+i*0.002, "target_semivariance_pct2": 1.0+i*0.01,
                           "gross_short_pct_oi_percentile": (i%20)/20.0, "high_crowding": i%10==0,
                           "pre_downside5_log": 0.1+(i%13)*0.01, "pre_downside20_log": 0.2+(i%17)*0.01,
                           "pre_rv20_log": 0.3+(i%11)*0.01})
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_target_ending_on_current_signal(self):
        events, start = [], dt.date(2020, 1, 1)
        current_signal = start + dt.timedelta(days=7*model.MODEL_WINDOW)
        for i in range(model.MODEL_WINDOW):
            signal = start + dt.timedelta(days=7*i)
            events.append({"report_date": signal-dt.timedelta(days=14), "signal_date": signal,
                           "target_start_date": signal+dt.timedelta(days=1),
                           "target_end_date": current_signal if i == model.MODEL_WINDOW-1 else signal+dt.timedelta(days=5),
                           "target_bp": 0.1+i*0.002, "target_semivariance_pct2": 1.0+i*0.01,
                           "gross_short_pct_oi_percentile": (i%20)/20.0, "high_crowding": i%10==0,
                           "pre_downside5_log": 0.1+(i%13)*0.01, "pre_downside20_log": 0.2+(i%17)*0.01,
                           "pre_rv20_log": 0.3+(i%11)*0.01})
        current = {"report_date": current_signal-dt.timedelta(days=14), "signal_date": current_signal,
                   "target_start_date": current_signal+dt.timedelta(days=1), "target_end_date": current_signal+dt.timedelta(days=5),
                   "target_bp": 0.3, "target_semivariance_pct2": 1.3, "gross_short_pct_oi_percentile": 0.95,
                   "high_crowding": True, "pre_downside5_log": 0.3, "pre_downside20_log": 0.4, "pre_rv20_log": 0.5}
        self.assertEqual(model.walk_forward_predictions(events + [current]), [])

    def test_decision_is_inconclusive_when_paired_interval_crosses_zero(self):
        v = {"n": 100, "baseline": {"rmse_log1p_semivariance": 1.0}, "augmented": {"rmse_log1p_semivariance": 0.9}}
        t = {"n": 100, "baseline": {"rmse_log1p_semivariance": 1.0}, "augmented": {"rmse_log1p_semivariance": 0.9}}
        p = {"ci95_low": -0.1, "ci95_high": 0.2}
        e = {"high_minus_other_mean_semivariance_pct2": 0.5, "ci95_low": -0.1, "ci95_high": 0.8}
        self.assertEqual(model.decide(v, t, p, e)[0], "INCONCLUSIVE")

    def test_decision_rejects_only_with_decisive_negative_evidence(self):
        v = {"n": 100, "baseline": {"rmse_log1p_semivariance": 1.1}, "augmented": {"rmse_log1p_semivariance": 1.2}}
        t = {"n": 100, "baseline": {"rmse_log1p_semivariance": 1.0}, "augmented": {"rmse_log1p_semivariance": 1.1}}
        p = {"ci95_low": -0.5, "ci95_high": -0.1}
        e = {"high_minus_other_mean_semivariance_pct2": -0.2, "ci95_low": -0.4, "ci95_high": -0.1}
        self.assertEqual(model.decide(v, t, p, e)[0], "REJECTED")


if __name__ == "__main__":
    unittest.main()
