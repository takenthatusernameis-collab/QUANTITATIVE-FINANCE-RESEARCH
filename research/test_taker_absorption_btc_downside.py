from __future__ import annotations

import datetime as dt
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import taker_absorption_btc_downside as model


class TakerAbsorptionBitcoinDownsideTests(unittest.TestCase):
    def synthetic_rows(self, start: dt.date, count: int) -> dict:
        rows = {}
        close = 100.0
        for index in range(count):
            day = start + dt.timedelta(days=index)
            daily_return = (0.004 if index % 7 in {0, 1, 2} else -0.006) + (index % 3) * 0.0002
            close *= math.exp(daily_return)
            imbalance = 0.35 if index % 4 == 0 else (-0.3 if index % 4 == 1 else 0.05)
            rows[day] = {
                "close": close,
                "volume": 10.0,
                "taker_imbalance": imbalance,
            }
        return rows

    def test_signed_absorption_encodes_directional_price_flow_mismatch(self):
        self.assertAlmostEqual(model.signed_absorption_proxy(0.4, -0.02), 0.008)
        self.assertAlmostEqual(model.signed_absorption_proxy(-0.4, 0.02), -0.008)
        self.assertEqual(model.signed_absorption_proxy(0.4, 0.02), 0.0)
        self.assertEqual(model.signed_absorption_proxy(-0.4, -0.02), 0.0)

    def test_signed_absorption_rejects_nonfinite_or_out_of_range_inputs(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            model.signed_absorption_proxy(float("nan"), -0.01)
        with self.assertRaisesRegex(ValueError, "within"):
            model.signed_absorption_proxy(1.1, -0.01)

    def test_event_builder_uses_only_next_five_sessions_and_nonoverlapping_origins(self):
        start = dt.date(2020, 1, 1)
        rows = self.synthetic_rows(start, 120)
        with patch.object(model, "START_DATE", start), patch.object(
            model, "END_DATE", start + dt.timedelta(days=119)
        ), patch.object(
            model, "SIGNAL_END_DATE", start + dt.timedelta(days=90)
        ), patch.object(model, "EVENT_STEP_DAYS", 6):
            events, metadata = model.build_events(rows)
        self.assertGreater(len(events), 5)
        first = events[0]
        self.assertEqual(first["signal_date"], start + dt.timedelta(days=20))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))
        self.assertEqual(metadata["accepted_events"], len(events))
        for left, right in zip(events, events[1:]):
            self.assertLess(left["target_end_date"], right["signal_date"])

    def test_event_builder_skips_missing_taker_flow_instead_of_imputing_zero(self):
        start = dt.date(2020, 1, 1)
        rows = self.synthetic_rows(start, 100)
        signal_date = start + dt.timedelta(days=20)
        rows[signal_date]["taker_imbalance"] = None
        with patch.object(model, "START_DATE", start), patch.object(
            model, "END_DATE", start + dt.timedelta(days=99)
        ), patch.object(
            model, "SIGNAL_END_DATE", start + dt.timedelta(days=80)
        ), patch.object(model, "EVENT_STEP_DAYS", 6):
            events, metadata = model.build_events(rows)
        self.assertEqual(metadata["skipped"]["missing_or_zero_volume_flow"], 1)
        self.assertNotIn(signal_date, [event["signal_date"] for event in events])

    def test_event_builder_rejects_missing_calendar_date(self):
        start = dt.date(2020, 1, 1)
        rows = self.synthetic_rows(start, 80)
        del rows[start + dt.timedelta(days=30)]
        with patch.object(model, "START_DATE", start), patch.object(
            model, "END_DATE", start + dt.timedelta(days=79)
        ):
            with self.assertRaisesRegex(ValueError, "calendar mismatch"):
                model.build_events(rows)

    def test_walk_forward_uses_only_prior_fully_matured_events(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(5):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": 0.1 * (index + 1),
                "target_semivariance_pct2": math.expm1(0.1 * (index + 1)),
                "signed_taker_absorption": 0.001 * index,
                **{name: float(index + 1) for name in model.BASE_FEATURES},
            })
        calls = []

        def fake_fit(train, current, features):
            calls.append((current["signal_date"], [row["signal_date"] for row in train], tuple(features)))
            return 0.1

        with patch.object(model, "MODEL_WINDOW", 2), patch.object(
            model.base, "fit_ols_predict", side_effect=fake_fit
        ):
            predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 3)
        current_calls = [call for call in calls if call[0] == start + dt.timedelta(days=12)]
        self.assertEqual(len(current_calls), 2)
        for _, train_dates, _ in current_calls:
            self.assertEqual(train_dates, [start, start + dt.timedelta(days=6)])

    def test_walk_forward_prediction_features_are_frozen(self):
        self.assertEqual(model.AUG_FEATURES, model.BASE_FEATURES + ["signed_taker_absorption"])
        self.assertEqual(len(model.BASE_FEATURES), 5)

    def test_bootstrap_is_deterministic_for_frozen_seed(self):
        rows = []
        for index in range(50):
            target = 0.01 * index
            rows.append({
                "target_bp": target,
                "baseline_prediction_bp": target + (0.1 if index % 2 else -0.1),
                "augmented_prediction_bp": target + (0.05 if index % 2 else -0.05),
            })
        first = model.bootstrap_paired_loss(rows)
        second = model.bootstrap_paired_loss(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["reps"], model.BOOTSTRAP_REPS)
        self.assertEqual(first["block_size_events"], model.BOOTSTRAP_BLOCK)

    def test_decision_promising_requires_both_periods_and_positive_paired_ci(self):
        validation = {"n": 80, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": 1.0}
        test = {"n": 120, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": 0.5}
        paired = {"ci_95_low": 0.01, "ci_95_high": 0.05}
        self.assertEqual(model.decide(validation, test, paired)[0], "PROMISING")

    def test_decision_rejected_requires_both_periods_and_negative_paired_ci(self):
        validation = {"n": 80, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": -1.0}
        test = {"n": 120, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": -0.5}
        paired = {"ci_95_low": -0.05, "ci_95_high": -0.01}
        self.assertEqual(model.decide(validation, test, paired)[0], "REJECTED")

    def test_decision_is_inconclusive_for_mixed_or_insufficient_evidence(self):
        validation = {"n": 80, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": 1.0}
        test = {"n": 120, "baseline": {"rmse_bp": 1.0}, "rmse_improvement_pct": -0.5}
        paired = {"ci_95_low": -0.05, "ci_95_high": 0.05}
        self.assertEqual(model.decide(validation, test, paired)[0], "INCONCLUSIVE")
        test["n"] = 99
        self.assertEqual(model.decide(validation, test, paired)[0], "INCONCLUSIVE")

    def test_source_manifest_hash_mismatch_fails_before_event_construction(self):
        bad_source = {
            "archive_manifest_sha256": "0" * 64,
            "coverage": {"observed_daily_rows": 3388, "missing_dates": [], "zero_volume_days": 0},
        }
        with patch.object(model.source, "fetch_all_archives", return_value=({}, bad_source)):
            with self.assertRaisesRegex(ValueError, "differs from the frozen source-preflight hash"):
                model.run_research()

    def test_render_report_handles_failed_run_without_metric_objects(self):
        result = {
            "status": "FAILED",
            "decision": "INCONCLUSIVE",
            "error": "checksum mismatch",
            "validation": {"n": 0, "baseline": None, "augmented": None},
            "test": {"n": 0, "baseline": None, "augmented": None},
        }
        rendered = model.render_report(result)
        self.assertIn("checksum mismatch", rendered)
        self.assertIn("INCONCLUSIVE", rendered)
        self.assertIn("not available", rendered)

    def test_update_documents_is_idempotent_and_updates_registry_and_prereg(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "HYPOTHESIS-REGISTRY.md"
            prereg = root / "PREREG.md"
            registry.write_text("| header |\n|---|\n", encoding="utf-8")
            prereg.write_text(
                "- **Status:** PREREGISTERED; source feasibility PASS; backtest not yet run.\n",
                encoding="utf-8",
            )
            result = {
                "status": "COMPLETE",
                "decision": "INCONCLUSIVE",
                "decision_reason": "mixed evidence",
                "validation": {"n": 80, "rmse_improvement_pct": -0.1},
                "test": {"n": 120, "rmse_improvement_pct": 0.1},
                "paired_test_loss_bootstrap": {"ci_95_low": -0.1, "ci_95_high": 0.1},
                "source_manifest": {
                    "archive_count": 136,
                    "coverage": {"observed_daily_rows": 3388},
                },
            }
            report = root / "report.md"
            manifest = root / "manifest.json"
            report.write_text("report", encoding="utf-8")
            manifest.write_text("manifest", encoding="utf-8")
            with patch.object(model, "ROOT", root), patch.object(
                model, "REGISTRY_PATH", registry
            ), patch.object(model, "PREREG_PATH", prereg):
                model.update_documents(result, report, manifest)
                first = registry.read_text(encoding="utf-8")
                model.update_documents(result, report, manifest)
                second = registry.read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(first.count(model.HYPOTHESIS_ID), 1)
            self.assertIn("BACKTESTED", first)
            self.assertIn("decision=INCONCLUSIVE", first)
            self.assertIn("EXECUTED", prereg.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
