import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import wikipedia_attention_btc_downside as model


class WikipediaAttentionBtcDownsideTests(unittest.TestCase):
    def make_market(self, days=2600):
        start = model.BTC_START_DATE
        prices = {
            start + dt.timedelta(days=index):
                30000.0 * math.exp(
                    0.00012 * index
                    + 0.035 * math.sin(index / 11.0)
                    + 0.012 * math.sin(index / 2.9)
                )
            for index in range(days)
        }
        pageviews = {}
        for index in range(days):
            day = model.PAGEVIEW_START_DATE + dt.timedelta(days=index)
            pageviews[day] = 1200 + int(250 * math.sin(index / 13.0)) + (index % 17) * 9
        return pageviews, prices

    def test_zero_view_calendar_reconstructs_one_omitted_day(self):
        start = dt.date(2020, 1, 1)
        values = {start: 10, start + dt.timedelta(days=2): 20}
        with patch.object(model.source, "MIN_NONZERO_ROWS", 1):
            completed, coverage, missing = model.complete_pageview_calendar(
                values, start, start + dt.timedelta(days=2)
            )
        self.assertEqual(completed[start + dt.timedelta(days=1)], 0)
        self.assertEqual(missing, [start + dt.timedelta(days=1)])
        self.assertEqual(coverage["documented_zero_view_days_reconstructed"], 1)

    def test_zero_view_calendar_rejects_multiple_consecutive_omissions(self):
        start = dt.date(2020, 1, 1)
        values = {start: 10, start + dt.timedelta(days=3): 20}
        with patch.object(model.source, "MIN_NONZERO_ROWS", 1):
            with self.assertRaisesRegex(ValueError, "consecutive"):
                model.complete_pageview_calendar(values, start, start + dt.timedelta(days=3))

    def test_signal_uses_exact_d_minus_2_and_d_minus_9_pageview_dates(self):
        pageviews, prices = self.make_market()
        events, meta = model.build_events(pageviews, prices)
        self.assertGreater(len(events), 150)
        first = events[0]
        self.assertEqual(first["pageview_recent_date"], first["signal_date"] - dt.timedelta(days=2))
        self.assertEqual(first["pageview_prior_date"], first["signal_date"] - dt.timedelta(days=9))
        expected = (
            math.log1p(pageviews[first["signal_date"] - dt.timedelta(days=2)])
            - math.log1p(pageviews[first["signal_date"] - dt.timedelta(days=9)])
        )
        self.assertAlmostEqual(first["wikipedia_attention_7d_log_change"], expected)
        self.assertEqual(meta["event_step_calendar_days"], model.EVENT_STEP_DAYS)

    def test_signal_target_and_five_session_semivariance_are_correct(self):
        pageviews, prices = self.make_market()
        events, _ = model.build_events(pageviews, prices)
        first = events[0]
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        dates = sorted(prices)
        index = dates.index(first["signal_date"])
        future_returns = [
            math.log(prices[dates[j]] / prices[dates[j - 1]])
            for j in range(index + 1, index + 6)
        ]
        expected = statistics_fmean([min(value, 0.0) ** 2 for value in future_returns]) * 10000.0
        self.assertAlmostEqual(first["target_semivariance_pct2"], expected)

    def test_missing_required_pageview_date_is_skipped_not_filled(self):
        pageviews, prices = self.make_market()
        first_signal = model.BTC_START_DATE + dt.timedelta(days=20)
        del pageviews[first_signal - dt.timedelta(days=2)]
        events, meta = model.build_events(pageviews, prices)
        self.assertGreater(meta["skipped"]["missing_pageview_feature_date"], 0)
        self.assertNotEqual(events[0]["signal_date"], first_signal)

    def test_baseline_contains_frozen_risk_and_momentum_features(self):
        pageviews, prices = self.make_market()
        events, _ = model.build_events(pageviews, prices)
        first = events[0]
        for feature in (
            "pre_downside5_log",
            "pre_downside20_log",
            "pre_rv20_log",
            "pre_return5",
            "pre_return20",
        ):
            self.assertIn(feature, first)
            self.assertTrue(math.isfinite(first[feature]))

    def test_target_windows_never_overlap(self):
        pageviews, prices = self.make_market()
        events, _ = model.build_events(pageviews, prices)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_walk_forward_requires_104_prior_fully_matured_events(self):
        events = []
        start = dt.date(2017, 9, 6)
        for index in range(106):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.3 + 0.04 * math.sin(index / 3.0),
                "pre_downside5_log": 0.1 + 0.03 * math.sin(index / 4.0),
                "pre_downside20_log": 0.2 + 0.04 * math.cos(index / 7.0),
                "pre_rv20_log": 0.3 + 0.02 * math.sin(index / 9.0),
                "pre_return5": 0.01 * math.sin(index / 5.0),
                "pre_return20": 0.02 * math.cos(index / 11.0),
                "wikipedia_attention_7d_log_change": 0.2 * math.cos(index / 5.0),
                "target_semivariance_pct2": 1.0 + 0.2 * math.sin(index / 3.0),
            })
        predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0]["train_n"], 104)
        self.assertEqual(predictions[0]["record_date"], predictions[0]["signal_date"])

    def test_bootstrap_is_deterministic_and_uses_four_event_blocks(self):
        rows = []
        start = dt.date(2022, 1, 1)
        for index in range(60):
            target = 0.3 + 0.1 * math.sin(index / 4.0)
            rows.append({
                "record_date": start + dt.timedelta(days=6 * index),
                "target_bp": target,
                "baseline_prediction_bp": target + 0.04 * math.cos(index / 3.0),
                "augmented_prediction_bp": target + 0.03 * math.sin(index / 5.0),
            })
        first = model.bootstrap_paired_loss(rows)
        second = model.bootstrap_paired_loss(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["reps"], 2000)
        self.assertEqual(first["block_size_events"], 4)

    def test_decision_requires_frozen_minimum_sample_counts(self):
        validation = {
            "n": 59,
            "baseline": {"rmse_bp": 1.0},
            "augmented": {"rmse_bp": 0.9},
            "rmse_improvement_pct": 10.0,
        }
        test = {
            "n": 100,
            "baseline": {"rmse_bp": 1.0},
            "augmented": {"rmse_bp": 0.9},
            "rmse_improvement_pct": 10.0,
        }
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.1}
        status, _ = model.decide(validation, test, paired)
        self.assertEqual(status, "INCONCLUSIVE")

    def test_decision_rule_promising_and_rejected_branches(self):
        validation = {
            "n": 60,
            "baseline": {"rmse_bp": 1.0},
            "augmented": {"rmse_bp": 0.9},
            "rmse_improvement_pct": 10.0,
        }
        test = {
            "n": 100,
            "baseline": {"rmse_bp": 1.0},
            "augmented": {"rmse_bp": 0.95},
            "rmse_improvement_pct": 5.0,
        }
        status, _ = model.decide(validation, test, {"ci_95_low": 0.01, "ci_95_high": 0.1})
        self.assertEqual(status, "BACKTESTED")
        validation["rmse_improvement_pct"] = -5.0
        test["rmse_improvement_pct"] = -2.0
        status, _ = model.decide(validation, test, {"ci_95_low": -0.1, "ci_95_high": -0.01})
        self.assertEqual(status, "REJECTED")

    def test_document_updates_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.md"
            prereg = root / "prereg.md"
            registry.write_text(
                "# Hypothesis Registry\n\n"
                "| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n",
                encoding="utf-8",
            )
            prereg.write_text(
                "# Preregistration\n\n"
                "- **Status:** FEASIBILITY_CHECKED\n",
                encoding="utf-8",
            )
            result = {
                "status": "INCONCLUSIVE",
                "disposition": "INCONCLUSIVE — synthetic test disposition",
                "completed_backtest": True,
                "data_scope": "synthetic deterministic fixture",
                "summary_metrics": {"validation_n": 60, "test_n": 100},
                "paired_squared_loss_bootstrap": {"status": "COMPUTED"},
            }
            with patch.object(model, "REGISTRY_PATH", registry), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, "reports/session.md", "reports/manifest.json")
                model.update_documents(result, "reports/session.md", "reports/manifest.json")
            registry_text = registry.read_text(encoding="utf-8")
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertEqual(registry_text.count(f"| {model.HYPOTHESIS_ID} |"), 1)
            self.assertEqual(prereg_text.count("## Empirical disposition"), 1)


def statistics_fmean(values):
    return sum(values) / len(values)


if __name__ == "__main__":
    unittest.main()
