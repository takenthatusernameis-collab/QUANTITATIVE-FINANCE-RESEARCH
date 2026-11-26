from __future__ import annotations
import datetime as dt
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import cftc_btc_noncommercial_crowding as model


class CftcBtcNoncommercialTests(unittest.TestCase):
    def make_market(self, weeks=180, extra_days=45):
        first = dt.date(2017, 8, 17)
        last = first + dt.timedelta(days=7 * weeks + extra_days)
        prices, day, index = {}, first, 0
        while day <= last:
            prices[day] = 10000.0 * math.exp(
                0.00015 * index + 0.025 * math.sin(index / 8.0) + 0.009 * math.sin(index / 2.9)
            )
            day += dt.timedelta(days=1)
            index += 1
        return prices

    def cot_row(self, day, long=600, short=300, oi=1000, code="133741",
                market="BITCOIN - CHICAGO MERCANTILE EXCHANGE"):
        return {
            "report_date_as_yyyy_mm_dd": f"{day.isoformat()}T00:00:00.000",
            "market_and_exchange_names": market,
            "cftc_contract_market_code": code,
            "open_interest_all": str(oi),
            "noncomm_positions_long_all": str(long),
            "noncomm_positions_short_all": str(short),
        }

    def test_url_uses_legacy_futures_only_exact_code_and_frozen_cutoff(self):
        parsed = urlparse(model.build_cftc_url())
        self.assertIn("/resource/6dca-aqww.json", parsed.path)
        params = parse_qs(parsed.query)
        self.assertIn("cftc_contract_market_code='133741'", params["$where"][0])
        self.assertIn("2026-11-17", params["$where"][0])
        self.assertIn("noncomm_positions_long_all", params["$select"][0])
        self.assertEqual(params["$limit"], ["50000"])

    def test_parser_filters_exact_contract_and_computes_signed_net_share(self):
        day = dt.date(2020, 1, 7)
        payload = [
            self.cot_row(day, long=600, short=300, oi=1000),
            self.cot_row(day, long=9000, short=1000, oi=10000, code="133742", market="OTHER CME MARKET"),
        ]
        rows = model.parse_cftc(json.dumps(payload).encode())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["noncomm_net"], 300)
        self.assertAlmostEqual(rows[0]["cftc_noncomm_net_long_share"], 0.3)

    def test_parser_rejects_wrong_market_and_non_tuesday_report(self):
        day = dt.date(2020, 1, 7)
        with self.assertRaisesRegex(ValueError, "Unexpected CFTC market name"):
            model.parse_cftc(json.dumps([self.cot_row(day, market="ETHEREUM - CME")]).encode())
        with self.assertRaisesRegex(ValueError, "non-Tuesday"):
            model.parse_cftc(json.dumps([self.cot_row(dt.date(2020, 1, 6))]).encode())

    def test_parser_rejects_invalid_open_interest_and_duplicate_dates(self):
        day = dt.date(2020, 1, 7)
        with self.assertRaisesRegex(ValueError, "Invalid CFTC open interest"):
            model.parse_cftc(json.dumps([self.cot_row(day, oi=0)]).encode())
        valid = self.cot_row(day)
        with self.assertRaisesRegex(ValueError, "Duplicate CFTC Bitcoin report dates"):
            model.parse_cftc(json.dumps([valid, valid]).encode())

    def test_parser_rejects_net_position_exceeding_open_interest(self):
        with self.assertRaisesRegex(ValueError, "exceeds open interest"):
            model.parse_cftc(json.dumps([self.cot_row(dt.date(2020, 1, 7), long=1500, short=0, oi=1000)]).encode())

    def test_known_cftc_publication_backlog_is_excluded(self):
        self.assertTrue(model.BACKLOG_START <= dt.date(2025, 9, 30) <= model.BACKLOG_END)
        self.assertTrue(model.BACKLOG_START <= dt.date(2026, 1, 20) <= model.BACKLOG_END)
        self.assertFalse(model.BACKLOG_START <= dt.date(2025, 9, 23) <= model.BACKLOG_END)
        self.assertFalse(model.BACKLOG_START <= dt.date(2026, 1, 27) <= model.BACKLOG_END)

    def test_event_signal_uses_fourteen_day_buffer_and_future_target(self):
        prices = self.make_market()
        report = dt.date(2020, 1, 7)
        events, meta = model.build_events([{"report_date": report, "cftc_noncomm_net_long_share": 0.3}], prices)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["signal_date"], report + dt.timedelta(days=14))
        self.assertEqual(event["availability_date"], event["signal_date"])
        self.assertGreater(event["target_start_date"], event["signal_date"])
        self.assertEqual((event["target_end_date"] - event["target_start_date"]).days, 4)
        self.assertAlmostEqual(event["cftc_noncomm_net_long_share"], 0.3)
        self.assertEqual(meta["publication_lag_calendar_days"], 14)

    def test_backlog_rows_never_enter_event_sample(self):
        prices = self.make_market(weeks=260)
        events, meta = model.build_events(
            [{"report_date": dt.date(2025, 10, 7), "cftc_noncomm_net_long_share": 0.4}], prices
        )
        self.assertEqual(events, [])
        self.assertEqual(meta["skipped"]["known_publication_backlog"], 1)

    def test_weekly_five_session_targets_do_not_overlap(self):
        prices = self.make_market(weeks=200)
        cot = [{"report_date": dt.date(2020, 1, 7) + dt.timedelta(days=7*i),
                "cftc_noncomm_net_long_share": 0.1*i} for i in range(4)]
        events, _ = model.build_events(cot, prices)
        self.assertEqual(len(events), 4)
        for left, right in zip(events, events[1:]):
            self.assertEqual((right["signal_date"] - left["signal_date"]).days, 7)
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_coverage_fails_closed_on_irregular_or_stale_cftc_rows(self):
        today = dt.date(2026, 11, 26)
        cot = [{"report_date": today - dt.timedelta(days=7*(450-i)), "x": i} for i in range(450)]
        cot[-1]["report_date"] = dt.date(2026, 11, 17)
        cot[0]["report_date"] = dt.date(2018, 4, 3)
        # Construct an exact weekly sequence ending on the frozen last Tuesday.
        start = dt.date(2026, 11, 17) - dt.timedelta(days=7*449)
        cot = [{"report_date": start + dt.timedelta(days=7*i)} for i in range(450)]
        prices, day = {}, dt.date(2017, 8, 17)
        while day <= dt.date(2026, 11, 24):
            prices[day] = 100.0
            day += dt.timedelta(days=1)
        coverage = model.validate_coverage(cot, prices, today)
        self.assertEqual(coverage["CFTC"]["last_report_date"], "2026-11-17")
        bad = [dict(x) for x in cot]
        bad[-1]["report_date"] = dt.date(2026, 10, 1)
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_coverage(bad, prices, today)

    def test_walk_forward_requires_104_fully_matured_prior_events(self):
        events, start = [], dt.date(2020, 1, 7)
        for i in range(model.MODEL_WINDOW + 2):
            signal = start + dt.timedelta(days=7*i)
            events.append({
                "report_date": signal - dt.timedelta(days=14), "signal_date": signal,
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.2 + 0.03*math.sin(i/4),
                "pre_downside5_log": 0.1 + 0.02*math.sin(i/3),
                "pre_downside20_log": 0.2 + 0.03*math.cos(i/6),
                "pre_rv20_log": 0.3 + 0.01*math.sin(i/8),
                "cftc_noncomm_net_long_share": 0.25*math.sin(i/9),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_walk_forward_excludes_training_target_ending_on_current_signal(self):
        events, start = [], dt.date(2020, 1, 7)
        current_signal = start + dt.timedelta(days=7*model.MODEL_WINDOW)
        for i in range(model.MODEL_WINDOW):
            signal = start + dt.timedelta(days=7*i)
            events.append({
                "report_date": signal-dt.timedelta(days=14), "signal_date": signal,
                "target_end_date": current_signal, "target_bp": 0.1+i*0.001,
                "pre_downside5_log": 0.1+(i%7)*0.01, "pre_downside20_log": 0.2+(i%9)*0.01,
                "pre_rv20_log": 0.3+(i%11)*0.01, "cftc_noncomm_net_long_share": 0.2*math.sin(i),
            })
        current = {
            "report_date": current_signal-dt.timedelta(days=14), "signal_date": current_signal,
            "target_end_date": current_signal+dt.timedelta(days=5), "target_bp": 0.3,
            "pre_downside5_log": 0.2, "pre_downside20_log": 0.3, "pre_rv20_log": 0.4,
            "cftc_noncomm_net_long_share": 0.1,
        }
        self.assertEqual(model.walk_forward(events+[current]), [])

    def test_decision_requires_both_periods_and_paired_interval(self):
        val, test = {"n": 60, "rmse_improvement_pct": 2.0}, {"n": 100, "rmse_improvement_pct": 1.0}
        self.assertEqual(model.decide(val, test, {"ci_95_low": 0.01, "ci_95_high": 0.05})[0], "BACKTESTED")
        self.assertEqual(model.decide(val, {"n": 100, "rmse_improvement_pct": -1.0},
                                      {"ci_95_low": 0.01, "ci_95_high": 0.05})[0], "INCONCLUSIVE")
        self.assertEqual(model.decide({"n": 60, "rmse_improvement_pct": -2.0},
                                      {"n": 100, "rmse_improvement_pct": -1.0},
                                      {"ci_95_low": -0.2, "ci_95_high": -0.01})[0], "REJECTED")

    def test_registry_and_prereg_persistence_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, prereg = root/"HYPOTHESIS-REGISTRY.md", root/"PREREG.md"
            registry.write_text("# Registry\n\n| ID | Status | Mechanism | Data | Disposition | Evidence |\n|---|---|---|---|---|---|\n| EXISTING | REJECTED | Keep | Existing | Preserve | old.md |\n", encoding="utf-8")
            prereg.write_text("# Prereg\n\n- **Status:** FEASIBILITY_CHECKED\n\n## Research question\n", encoding="utf-8")
            result = {"status": "INCONCLUSIVE", "disposition": "INCONCLUSIVE — mixed evidence",
                      "completed_backtest": True, "data_scope": "synthetic scope",
                      "summary_metrics": {"validation_n": 40, "test_n": 80}}
            with patch.object(model, "REGISTRY", registry), patch.object(model, "PREREG", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            text = registry.read_text(encoding="utf-8")
            self.assertIn("| EXISTING | REJECTED |", text)
            self.assertEqual(text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            p = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE. INCONCLUSIVE — mixed evidence.", p)
            self.assertEqual(p.count("## Empirical disposition"), 1)


if __name__ == "__main__":
    unittest.main()
