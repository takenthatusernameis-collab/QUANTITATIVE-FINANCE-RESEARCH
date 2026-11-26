import datetime as dt
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import mexc_btc_funding_downside as model
import stlfsi4_btc_downside_semivariance as btc


def settlement(day, hour, rate=0.0001, cycle=8):
    stamp = dt.datetime.combine(day, dt.time(hour), tzinfo=dt.timezone.utc)
    return {
        "symbol": "BTC_USDT",
        "fundingRate": rate,
        "settleTime": int(stamp.timestamp() * 1000),
        "collectCycle": cycle,
    }


def page_payload(rows, page=1, total_count=None, total_pages=1):
    return {
        "success": True,
        "code": 0,
        "data": {
            "pageSize": 1000,
            "totalCount": total_count if total_count is not None else len(rows),
            "totalPage": total_pages,
            "currentPage": page,
            "resultList": rows,
        },
    }


class MexcFundingDownsideTests(unittest.TestCase):
    def test_parser_accepts_documented_mexc_envelope_and_millisecond_timestamps(self):
        day = dt.date(2026, 1, 2)
        rows = [settlement(day, hour, rate) for hour, rate in ((0, 0.0001), (8, -0.0002), (16, 0.0003))]
        meta, parsed = model.parse_funding_page(json.dumps(page_payload(rows)).encode(), 1)
        self.assertEqual(meta["current_page"], 1)
        self.assertEqual(meta["total_count"], 3)
        self.assertEqual([row["settle_hour"] for row in parsed], [0, 8, 16])
        self.assertAlmostEqual(sum(row["funding_rate"] for row in parsed), 0.0002)

    def test_parser_rejects_wrong_symbol_and_non_eight_hour_cycle(self):
        day = dt.date(2026, 1, 2)
        wrong_symbol = settlement(day, 0)
        wrong_symbol["symbol"] = "ETH_USDT"
        with self.assertRaisesRegex(ValueError, "unexpected symbol"):
            model.parse_funding_page(json.dumps(page_payload([wrong_symbol])).encode(), 1)
        wrong_cycle = settlement(day, 0, cycle=4)
        with self.assertRaisesRegex(ValueError, "8-hour funding schema"):
            model.parse_funding_page(json.dumps(page_payload([wrong_cycle])).encode(), 1)

    def test_parser_rejects_non_slot_and_seconds_timestamp(self):
        day = dt.date(2026, 1, 2)
        wrong_slot = settlement(day, 12)
        with self.assertRaisesRegex(ValueError, "not aligned"):
            model.parse_funding_page(json.dumps(page_payload([wrong_slot])).encode(), 1)
        seconds = settlement(day, 0)
        seconds["settleTime"] //= 1000
        with self.assertRaisesRegex(ValueError, "millisecond"):
            model.parse_funding_page(json.dumps(page_payload([seconds])).encode(), 1)

    def test_parser_rejects_page_progression_mismatch(self):
        day = dt.date(2026, 1, 2)
        rows = [settlement(day, 0)]
        with self.assertRaisesRegex(ValueError, "page progression mismatch"):
            model.parse_funding_page(json.dumps(page_payload(rows, page=2)).encode(), 1)

    def test_funding_history_retrieves_every_page_and_hashes_each_response(self):
        base_day = dt.date(2025, 1, 1)
        all_rows = []
        start = dt.datetime.combine(base_day, dt.time(0), tzinfo=dt.timezone.utc)
        for index in range(1001):
            stamp = start + dt.timedelta(hours=8 * index)
            all_rows.append({
                "symbol": "BTC_USDT",
                "fundingRate": 0.00001 * math.sin(index / 10),
                "settleTime": int(stamp.timestamp() * 1000),
                "collectCycle": 8,
            })
        payloads = {
            1: json.dumps(page_payload(all_rows[:1000], page=1, total_count=1001, total_pages=2)).encode(),
            2: json.dumps(page_payload(all_rows[1000:], page=2, total_count=1001, total_pages=2)).encode(),
        }

        def fake_fetch(url, timeout=15):
            page = int(parse_qs(urlsplit(url).query)["page_num"][0])
            return payloads[page]

        with patch.object(model.base, "fetch_bytes", side_effect=fake_fetch):
            rows, source = model.fetch_funding_history()
        self.assertEqual(len(rows), 1001)
        self.assertEqual(source["reported_total_pages"], 2)
        self.assertEqual(len(source["retrieved_pages"]), 2)
        self.assertEqual(len(source["page_manifest_sha256"]), 64)

    def test_daily_aggregation_sums_exact_three_settlements(self):
        start, end = dt.date(2026, 1, 1), dt.date(2026, 1, 3)
        rows = []
        for offset in range(3):
            day = start + dt.timedelta(days=offset)
            rows.extend([
                {"settle_date": day, "settle_hour": 0, "funding_rate": 0.0001},
                {"settle_date": day, "settle_hour": 8, "funding_rate": -0.0002},
                {"settle_date": day, "settle_hour": 16, "funding_rate": 0.0003},
            ])
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "MIN_FUNDING_ROWS", 9),
            patch.object(model, "MIN_COMPLETE_DAYS", 3),
        ):
            daily, coverage = model.aggregate_complete_funding_days(rows)
        self.assertEqual(len(daily), 3)
        self.assertAlmostEqual(daily[start], 0.0002)
        self.assertEqual(coverage["complete_utc_days"], 3)
        self.assertEqual(coverage["incomplete_utc_days"], 0)

    def test_daily_aggregation_fails_closed_on_incomplete_settlement_day(self):
        start, end = dt.date(2026, 1, 1), dt.date(2026, 1, 3)
        rows = []
        for offset in range(3):
            day = start + dt.timedelta(days=offset)
            rows.extend([
                {"settle_date": day, "settle_hour": 0, "funding_rate": 0.0001},
                {"settle_date": day, "settle_hour": 8, "funding_rate": -0.0002},
            ])
            if offset != 1:
                rows.append({"settle_date": day, "settle_hour": 16, "funding_rate": 0.0003})
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "MIN_FUNDING_ROWS", 6),
            patch.object(model, "MIN_COMPLETE_DAYS", 2),
        ):
            with self.assertRaisesRegex(ValueError, "funding coverage fails"):
                model.aggregate_complete_funding_days(rows)

    def test_event_uses_day_d_funding_and_only_next_session_return(self):
        start = dt.date(2026, 1, 1)
        returns = [0.01, -0.02, 0.005, -0.01, 0.015, -0.03, 0.02, -0.005, 0.01]
        prices = {start: 100.0}
        for index, value in enumerate(returns, start=1):
            prices[start + dt.timedelta(days=index)] = prices[start + dt.timedelta(days=index - 1)] * math.exp(value)
        d = start + dt.timedelta(days=5)
        funding = {
            d: 0.0006,
            d + dt.timedelta(days=1): 0.1234,
            d + dt.timedelta(days=2): -0.0004,
        }
        events, meta = model.build_events(funding, prices)
        self.assertEqual(len(events), 3)
        first = events[0]
        self.assertEqual(first["signal_date"], d)
        self.assertEqual(first["target_start_date"], d + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], d + dt.timedelta(days=1))
        self.assertAlmostEqual(first["funding_24h_sum"], 0.0006)
        next_return = math.log(prices[d + dt.timedelta(days=1)] / prices[d])
        self.assertAlmostEqual(first["target_downside_loss_pct2"], btc.semi_var_pct2([next_return]))
        self.assertEqual(meta["accepted_events"], 3)

    def test_walk_forward_requires_104_strictly_matured_prior_events(self):
        rows = []
        start = dt.date(2020, 1, 1)
        for index in range(107):
            day = start + dt.timedelta(days=index)
            rows.append({
                "signal_date": day,
                "target_end_date": day + dt.timedelta(days=1),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "target_downside_loss_pct2": math.expm1(0.3 + 0.04 * math.sin(index / 3.0)),
                "pre_downside1_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside5_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv5_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "funding_24h_sum": 0.0001 * math.cos(index / 5.0) + index * 0.000001,
            })
        predictions = model.walk_forward(rows)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)
        self.assertEqual(predictions[0]["signal_date"], start + dt.timedelta(days=105))

    def test_decision_requires_both_periods_and_positive_paired_lower_bound(self):
        paired = {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05}
        self.assertEqual(
            model.decide({"n": 60, "rmse_improvement_pct": 2.0}, {"n": 120, "rmse_improvement_pct": 1.0}, paired)[0],
            "BACKTESTED",
        )
        self.assertEqual(
            model.decide({"n": 60, "rmse_improvement_pct": 2.0}, {"n": 120, "rmse_improvement_pct": -1.0}, paired)[0],
            "INCONCLUSIVE",
        )
        rejected = {"ci_95_low_bp2": -0.2, "ci_95_high_bp2": -0.01}
        self.assertEqual(
            model.decide({"n": 60, "rmse_improvement_pct": -2.0}, {"n": 120, "rmse_improvement_pct": -1.0}, rejected)[0],
            "REJECTED",
        )

    def test_update_documents_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "HYPOTHESIS-REGISTRY.md"
            prereg = root / "PREREG.md"
            registry.write_text(
                "# Registry\n\n| Hypothesis ID | Status | Mechanism | Data | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n\n## Disposition rules\n",
                encoding="utf-8",
            )
            prereg.write_text(
                "# Preregistration\n\n- **Status:** PREREGISTERED\n",
                encoding="utf-8",
            )
            result = {
                "status": "INCONCLUSIVE",
                "disposition": "INCONCLUSIVE — mixed evidence",
                "completed_backtest": True,
                "data_sources": {},
                "summary_metrics": {"validation_n": 60, "test_n": 120},
                "paired_squared_loss_bootstrap": {"ci_95_low_bp2": -0.1, "ci_95_high_bp2": 0.1},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
                model.update_documents(result, "reports/sessions/report.md", "reports/generated/manifest.json")
            registry_text = registry.read_text(encoding="utf-8")
            self.assertEqual(registry_text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("- **Status:** INCONCLUSIVE\n", prereg_text)
            self.assertEqual(prereg_text.count("## Empirical disposition"), 1)


if __name__ == "__main__":
    unittest.main()
