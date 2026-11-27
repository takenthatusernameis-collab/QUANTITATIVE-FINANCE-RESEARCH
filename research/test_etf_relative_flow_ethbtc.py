from __future__ import annotations

import datetime as dt
import math
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import etf_relative_flow_ethbtc as model


class ETFRelativeFlowETHBTCTests(unittest.TestCase):
    def synthetic_prices(self, start: dt.date, count: int):
        btc, eth = {}, {}
        btc_close, eth_close = 100.0, 50.0
        for index in range(count):
            day = start + dt.timedelta(days=index)
            btc_return = 0.001 * math.sin(index / 7.0) + 0.0004
            eth_return = 0.0012 * math.cos(index / 9.0) + 0.0005
            btc_close *= math.exp(btc_return)
            eth_close *= math.exp(eth_return)
            btc[day], eth[day] = btc_close, eth_close
        return btc, eth

    def synthetic_panel(self, count: int):
        rows = []
        start = dt.date(2024, 7, 23)
        for index in range(count):
            rows.append({
                "date": start + dt.timedelta(days=index),
                "btc_total_usdm": 20.0 + index * 0.7 + 0.2 * math.sin(index),
                "eth_total_usdm": 8.0 + index * 0.4 + 0.3 * math.cos(index / 2.0),
            })
        return rows

    def test_event_builder_uses_prior_only_zscores_every_second_flow_date_and_next_five_prices(self):
        price_start = dt.date(2024, 7, 1)
        btc, eth = self.synthetic_prices(price_start, 300)
        panel = self.synthetic_panel(70)
        with patch.object(model, "PRICE_START_DATE", price_start), patch.object(\n            model, "PRICE_END_DATE", price_start + dt.timedelta(days=299)\n        ):\n            events, metadata = model.build_events(panel, btc, eth)\n        self.assertEqual(len(events), 5)
        first = events[0]
        self.assertEqual(first["flow_date"], panel[60]["date"])
        self.assertEqual(events[1]["flow_date"], panel[62]["date"])
        self.assertEqual(first["signal_date"], first["flow_date"] + dt.timedelta(days=5))
        self.assertEqual(first["target_start_date"], first["signal_date"] + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], first["signal_date"] + dt.timedelta(days=5))

        btc_history = [row["btc_total_usdm"] for row in panel[:60]]
        eth_history = [row["eth_total_usdm"] for row in panel[:60]]
        z_btc = (panel[60]["btc_total_usdm"] - statistics.fmean(btc_history)) / statistics.pstdev(btc_history)
        z_eth = (panel[60]["eth_total_usdm"] - statistics.fmean(eth_history)) / statistics.pstdev(eth_history)
        self.assertAlmostEqual(first["common_flow_pressure"], (z_btc + z_eth) / 2.0)
        self.assertAlmostEqual(first["relative_flow_pressure"], z_eth - z_btc)

        signal = first["signal_date"]
        expected = 0.0
        for offset in range(1, 6):
            day, previous = signal + dt.timedelta(days=offset), signal + dt.timedelta(days=offset - 1)
            expected += math.log(eth[day] / eth[previous]) - math.log(btc[day] / btc[previous])
        self.assertAlmostEqual(first["target_bp"], expected * 10_000.0)
        self.assertEqual(metadata["accepted_events"], 5)

    def test_event_builder_rejects_noncontinuous_or_nonpositive_price_history(self):
        price_start = dt.date(2024, 7, 1)
        btc, eth = self.synthetic_prices(price_start, 300)
        del btc[price_start + dt.timedelta(days=30)]
        with patch.object(model, "PRICE_START_DATE", price_start), patch.object(\n            model, "PRICE_END_DATE", price_start + dt.timedelta(days=299)\n        ):\n            with self.assertRaisesRegex(ValueError, "price calendar"):\n                model.build_events(self.synthetic_panel(70), btc, eth)\n        btc, eth = self.synthetic_prices(price_start, 300)\n        eth[price_start + dt.timedelta(days=40)] = -1.0\n        with patch.object(model, "PRICE_START_DATE", price_start), patch.object(\n            model, "PRICE_END_DATE", price_start + dt.timedelta(days=299)\n        ):\n            with self.assertRaisesRegex(ValueError, "Non-positive"):\n                model.build_events(self.synthetic_panel(70), btc, eth)\n
    def test_walk_forward_excludes_unmatured_targets_and_uses_65_event_window(self):
        events = []
        start = dt.date(2020, 1, 1)
        for index in range(6):
            signal = start + dt.timedelta(days=6 * index)
            events.append({
                "signal_date": signal,
                "target_end_date": signal + dt.timedelta(days=5),
                "target_bp": float(index),
                **{name: float(index + 1) for name in model.BASE_FEATURES},
                "relative_flow_pressure": float(index) / 10.0,
            })
        calls = []

        def fake_fit(train, current, features):
            calls.append((current["signal_date"], [row["signal_date"] for row in train], tuple(features)))
            return 0.1

        with patch.object(model, "MODEL_WINDOW", 2), patch.object(model.base, "fit_ols_predict", side_effect=fake_fit):
            predictions = model.walk_forward(events)
        self.assertEqual(len(predictions), 4)
        current_signal, training_dates, features = calls[0]
        self.assertEqual(current_signal, start + dt.timedelta(days=12))
        self.assertEqual(training_dates, [start, start + dt.timedelta(days=6)])
        self.assertTrue(all(day + dt.timedelta(days=5) < current_signal for day in training_dates))
        self.assertEqual(features, tuple(model.BASE_FEATURES))

    def test_bootstrap_is_deterministic_and_uses_five_event_blocks(self):
        rows = []
        for index in range(80):
            target = 0.03 * index
            rows.append({
                "signal_date": dt.date(2020, 1, 1) + dt.timedelta(days=index * 2),
                "target_bp": target,
                "baseline_prediction_bp": target + (0.2 if index % 2 else -0.2),
                "augmented_prediction_bp": target + (0.1 if index % 2 else -0.1),
            })
        first = model.bootstrap_paired_loss(rows)
        second = model.bootstrap_paired_loss(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["reps"], 2000)
        self.assertEqual(first["block_size_events"], 5)
        self.assertEqual(first["seed"], 20261127)

    def test_decision_requires_both_periods_and_paired_interval(self):
        validation = {"n": 60, "rmse_improvement_pct": 1.0}
        test = {"n": 70, "rmse_improvement_pct": 0.5}
        self.assertEqual(model.decide(validation, test, {"ci_95_low_bp2": 0.01, "ci_95_high_bp2": 0.05})[0], "PROMISING")
        validation["rmse_improvement_pct"] = -1.0
        test["rmse_improvement_pct"] = -0.5
        self.assertEqual(model.decide(validation, test, {"ci_95_low_bp2": -0.05, "ci_95_high_bp2": -0.01})[0], "REJECTED")
        test["n"] = 59
        self.assertEqual(model.decide(validation, test, {"ci_95_low_bp2": -0.05, "ci_95_high_bp2": -0.01})[0], "INCONCLUSIVE")

    def test_frozen_source_mismatch_fails_before_event_construction(self):
        wrong = {
            "flow_panel": {"sha256": "0" * 64, "rows": 583, "first_date": "2024-07-23",
                           "last_date": "2026-11-16", "cutoff_date": "2026-11-16", "unmatched_dates": []},
            "price_sources": {},
        }
        with patch.object(model, "fetch_frozen_inputs", return_value=([], {}, {}, wrong)), patch.object(
            model, "build_events"
        ) as build:
            with self.assertRaisesRegex(model.FrozenSourceMismatch, "flow-panel SHA-256"):
                model.run_research()
        build.assert_not_called()

    def test_update_documents_is_idempotent_and_preserves_atomic_admission_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "research" / "HYPOTHESIS-REGISTRY.md"
            prereg = root / "research" / "PREREG.md"
            report = root / "reports" / "sessions" / "report.md"
            manifest = root / "reports" / "generated" / "manifest.json"
            registry.parent.mkdir(parents=True)
            report.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            registry.write_text("| header |\n|---|\n", encoding="utf-8")
            prereg.write_text(
                "- **Status:** ADMITTED; source feasibility PASS; empirical backtest pending.\n\n"
                "## 8. Atomic execution admission\nFrozen admission record.\n",
                encoding="utf-8",
            )
            result = {
                "status": "COMPLETE",
                "decision": "INCONCLUSIVE",
                "decision_reason": "mixed evidence",
                "run_id": "123",
                "source_commit_sha": "abc",
                "report_path": report.relative_to(root).as_posix(),
                "manifest_path": manifest.relative_to(root).as_posix(),
                "validation": {"n": 50, "rmse_improvement_pct": -0.1},
                "test": {"n": 70, "rmse_improvement_pct": 0.1},
                "paired_test_loss_bootstrap": {"ci_95_low_bp2": -0.1, "ci_95_high_bp2": 0.1},
            }
            with patch.object(model, "ROOT", root), patch.object(model, "REGISTRY_PATH", registry), patch.object(
                model, "PREREG_PATH", prereg
            ):
                model.update_documents(result, report, manifest)
                first = registry.read_text(encoding="utf-8")
                model.update_documents(result, report, manifest)
                second = registry.read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(first.count(model.HYPOTHESIS_ID), 1)
            saved = prereg.read_text(encoding="utf-8")
            self.assertIn("## 8. Atomic execution admission", saved)
            self.assertEqual(saved.count("## 9. Execution result"), 1)
            self.assertIn("BACKTESTED; decision=INCONCLUSIVE", saved)


if __name__ == "__main__":
    unittest.main()
