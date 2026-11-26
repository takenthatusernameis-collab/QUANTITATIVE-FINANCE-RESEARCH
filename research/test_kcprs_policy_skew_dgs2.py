from __future__ import annotations

import datetime as dt
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kcprs_policy_skew_dgs2 as model


class KcprsPolicySkewTests(unittest.TestCase):
    def business_dates(self, start: dt.date, count: int) -> list[dt.date]:
        dates = []
        day = start
        while len(dates) < count:
            if day.weekday() < 5:
                dates.append(day)
            day += dt.timedelta(days=1)
        return dates

    def make_market(self, count=900):
        dates = self.business_dates(dt.date(1989, 4, 3), count)
        dgs2 = {
            day: 4.0 + 0.0005 * i + 0.25 * math.sin(i / 31.0) + 0.03 * math.cos(i / 7.0)
            for i, day in enumerate(dates)
        }
        dgs10 = {
            day: dgs2[day] + 0.6 + 0.2 * math.sin(i / 53.0)
            for i, day in enumerate(dates)
        }
        kcprs = {
            day: 0.2 * math.sin(i / 37.0) + 0.1 * math.cos(i / 11.0)
            for i, day in enumerate(dates)
        }
        return dates, kcprs, dgs2, dgs10

    def test_parse_fred_accepts_negative_skew_and_missing_values(self):
        body = (
            "observation_date,KCPRS\n"
            "2026-11-20,-0.365\n"
            "2026-11-23,.\n"
            "2026-11-24,0.125\n"
        ).encode()
        parsed = model.parse_fred_series(body, "KCPRS")
        self.assertEqual(len(parsed), 2)
        self.assertAlmostEqual(parsed[dt.date(2026, 11, 20)], -0.365)

    def test_parse_fred_rejects_duplicate_dates_and_nonpositive_yields(self):
        duplicate = (
            "observation_date,DGS2\n"
            "2026-11-20,3.9\n"
            "2026-11-20,4.0\n"
        ).encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            model.parse_fred_series(duplicate, "DGS2", positive_required=True)
        nonpositive = "observation_date,DGS2\n2026-11-20,0\n".encode()
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            model.parse_fred_series(nonpositive, "DGS2", positive_required=True)

    def test_source_coverage_accepts_long_fresh_synchronized_series(self):
        dates = self.business_dates(dt.date(1989, 4, 3), 9500)
        series = {
            "KCPRS": {day: 0.1 * math.sin(i / 20.0) for i, day in enumerate(dates)},
            "DGS2": {day: 4.0 + 0.0001 * i for i, day in enumerate(dates)},
            "DGS10": {day: 4.5 + 0.0001 * i for i, day in enumerate(dates)},
        }
        coverage = model.validate_source_coverage(series, dates[-1] + dt.timedelta(days=1))
        self.assertEqual(coverage["KCPRS"]["first_date"], dates[0].isoformat())
        self.assertEqual(coverage["common_all_series_dates"], len(dates))

    def test_source_coverage_rejects_stale_kcprs(self):
        dates = self.business_dates(dt.date(1989, 4, 3), 9823)
        today = dt.date(2026, 11, 26)
        cutoff = dt.date(2026, 11, 10)
        series = {
            "KCPRS": {day: 0.1 for day in dates if day <= cutoff},
            "DGS2": {day: 4.0 for day in dates},
            "DGS10": {day: 4.5 for day in dates},
        }
        with self.assertRaisesRegex(ValueError, "stale"):
            model.validate_source_coverage(series, today)

    def test_signal_uses_latest_strictly_prior_kcprs_level(self):
        dates, kcprs, dgs2, dgs10 = self.make_market()
        events, meta = model.build_events(kcprs, dgs2, dgs10)
        self.assertGreater(len(events), 20)
        first = events[0]
        signal_index = dates.index(first["signal_date"])
        self.assertEqual(first["kcprs_observation_date"], dates[signal_index - 1])
        self.assertLess(first["kcprs_observation_date"], first["signal_date"])
        self.assertAlmostEqual(first["kcprs_level_pp"], kcprs[dates[signal_index - 1]])
        self.assertEqual(meta["event_spacing_sessions"], 22)

    def test_same_day_kcprs_is_never_used(self):
        dates, kcprs, dgs2, dgs10 = self.make_market()
        events, _ = model.build_events(kcprs, dgs2, dgs10)
        self.assertTrue(events)
        for event in events:
            self.assertLess(event["kcprs_observation_date"], event["signal_date"])

    def test_stale_kcprs_is_not_forward_filled(self):
        dates, kcprs, dgs2, dgs10 = self.make_market()
        for day in dates[55:64]:
            kcprs.pop(day, None)
        events, meta = model.build_events(kcprs, dgs2, dgs10)
        self.assertGreater(meta["skipped"]["stale_prior_kcprs_observation"], 0)
        self.assertNotEqual(events[0]["signal_date"], dates[63])

    def test_target_windows_are_nonoverlapping_and_mature_before_next_signal(self):
        dates, kcprs, dgs2, dgs10 = self.make_market()
        events, _ = model.build_events(kcprs, dgs2, dgs10)
        for previous, current in zip(events, events[1:]):
            self.assertLess(previous["target_end_date"], current["signal_date"])
            self.assertEqual(
                dates.index(current["signal_date"]) - dates.index(previous["signal_date"]),
                model.EVENT_STEP_SESSIONS,
            )

    def make_events(self, count):
        events = []
        start = dt.date(2000, 1, 3)
        for index in range(count):
            signal = start + dt.timedelta(days=22 * index)
            events.append({
                "signal_date": signal,
                "kcprs_observation_date": signal - dt.timedelta(days=1),
                "target_start_date": signal + dt.timedelta(days=1),
                "target_end_date": signal + dt.timedelta(days=21),
                "source_regime": "EURODOLLAR_OPTIONS",
                "target_bp": 0.1 * math.sin(index / 4.0) + 0.002 * index,
                "dgs2_level_pct": 3.0 + 0.01 * math.sin(index / 8.0),
                "dgs2_change_21d_bp": 2.0 * math.sin(index / 5.0),
                "dgs2_change_63d_bp": 3.0 * math.cos(index / 9.0),
                "curve_10y2y_bp": 40.0 + 5.0 * math.sin(index / 7.0),
                "kcprs_level_pp": 0.3 * math.sin(index / 6.0),
            })
        return events

    def test_walk_forward_requires_52_fully_matured_events(self):
        events = self.make_events(model.MODEL_WINDOW + 1)
        predictions = model.walk_forward_predictions(events)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["train_n"], model.MODEL_WINDOW)

    def test_decision_does_not_promote_without_minimum_sample(self):
        validation = {
            "n": 29,
            "baseline": {"rmse_bp": 2.0},
            "augmented": {"rmse_bp": 1.0},
        }
        test = {
            "n": 29,
            "baseline": {"rmse_bp": 2.0},
            "augmented": {"rmse_bp": 1.0},
        }
        status, _ = model.decide(validation, test, {"ci_95_low_bp2": 0.1})
        self.assertEqual(status, "INCONCLUSIVE")

    def test_preregistration_updater_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prereg.md"
            path.write_text("# Preregistration\n\n- **Status:** PREREGISTERED — pending.\n", encoding="utf-8")
            result = {
                "status": "INCONCLUSIVE",
                "disposition": "INCONCLUSIVE — mixed evidence.",
                "completed_backtest": True,
                "data_scope": "synthetic scope",
                "summary_metrics": {
                    "validation_n": 40,
                    "test_n": 40,
                    "validation_improvement_pct": -1.0,
                    "test_improvement_pct": 0.5,
                },
            }
            with patch.object(model, "PREREG_PATH", path):
                model.update_preregistration(result, "reports/sessions/2026-11-26/report.md")
                model.update_preregistration(result, "reports/sessions/2026-11-26/report.md")
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("## Empirical disposition"), 1)
            self.assertIn("- **Status:** INCONCLUSIVE — mixed evidence.", content)
            self.assertIn("- **Final status:** INCONCLUSIVE — mixed evidence.", content)
            self.assertIn("../reports/sessions/2026-11-26/report.md", content)

    def test_registry_upsert_replaces_existing_hypothesis_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.md"
            path.write_text(
                "# Registry\n\n"
                "| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |\n"
                "|---|---|---|---|---|---|\n"
                f"| {model.HYPOTHESIS_ID} | PREREGISTERED | old | old | pending | old |\n",
                encoding="utf-8",
            )
            with patch.object(model, "REGISTRY_PATH", path):
                model.upsert_registry(
                    "INCONCLUSIVE", "INCONCLUSIVE — test", "test scope",
                    "reports/sessions/2026-11-26/report.md",
                )
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count(model.HYPOTHESIS_ID), 1)
            self.assertIn("| INCONCLUSIVE |", content)
            self.assertIn("../reports/sessions/2026-11-26/report.md", content)

    def test_workflow_has_immutable_checkout_and_atomic_admission(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github" / "workflows" / "kcprs-policy-skew-dgs2.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("ref: $" + "{{ github.sha }}", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("contains(github.event.head_commit.message, '[QFR-ADMIT]')", workflow)


if __name__ == "__main__":
    unittest.main()
