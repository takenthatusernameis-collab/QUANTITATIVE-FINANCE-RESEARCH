import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import persist_btc_mining_difficulty_evidence as persistence


class BitcoinMiningDifficultyPersistenceTests(unittest.TestCase):
    def test_persist_updates_only_target_registry_row_and_readme_block(self):
        with tempfile.TemporaryDirectory(dir=persistence.ROOT) as temp:
            root = Path(temp)
            prereg = root / "prereg.md"
            registry = root / "registry.md"
            readme = root / "README.md"
            report = root / "reports" / "sessions" / "report.md"
            manifest_path = root / "reports" / "generated" / "manifest.json"
            report.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            report.write_text("verified report\n", encoding="utf-8")
            prereg.write_text("# Prereg\n\n- **Status:** PREREGISTERED\n", encoding="utf-8")
            registry.write_text(
                "# Registry\n\n| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| OTHER | REJECTED | Keep me | Existing | Rejected | old |\n",
                encoding="utf-8",
            )
            readme.write_text(
                "# README\n\n<!-- QFR:BTC-MINING-DIFFICULTY:START -->\nold\n"
                "<!-- QFR:BTC-MINING-DIFFICULTY:END -->\n\nKeep this tail.\n",
                encoding="utf-8",
            )
            manifest = {
                "hypothesis_id": persistence.HYPOTHESIS_ID,
                "status": "COMPLETE",
                "decision": "PROMISING",
                "decision_reason": "Frozen rule passed.",
                "run_id": "12345",
                "source_commit_sha": "abc123",
                "preregistration_sha256": hashlib.sha256(prereg.read_bytes()).hexdigest(),
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "validation": {"n": 60, "rmse_improvement_pct": 1.0},
                "test": {"n": 110, "rmse_improvement_pct": 0.5},
                "paired_test_loss_bootstrap": {"ci_95_low": 0.01, "ci_95_high": 0.03},
                "sources": {},
                "sample": {"price_start": "2017-08-17", "price_end": "2026-11-25"},
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(persistence, "PREREG_PATH", prereg), patch.object(
                persistence, "REGISTRY_PATH", registry
            ), patch.object(persistence, "README_PATH", readme), patch.dict(
                os.environ, {"GITHUB_SHA": "abc123"}
            ):
                persistence.persist(manifest_path, report)
            registry_text = registry.read_text(encoding="utf-8")
            self.assertIn("| OTHER | REJECTED | Keep me", registry_text)
            self.assertIn(f"| {persistence.HYPOTHESIS_ID} | BACKTESTED |", registry_text)
            prereg_text = prereg.read_text(encoding="utf-8")
            self.assertIn("Status:** BACKTESTED; decision=PROMISING", prereg_text)
            self.assertIn("## 8. Execution result", prereg_text)
            readme_text = readme.read_text(encoding="utf-8")
            self.assertIn("decision **PROMISING**", readme_text)
            self.assertIn("Keep this tail.", readme_text)
            self.assertEqual(readme_text.count(persistence.README_START), 1)

    def test_persist_rejects_source_commit_mismatch(self):
        with tempfile.TemporaryDirectory(dir=persistence.ROOT) as temp:
            root = Path(temp)
            prereg = root / "prereg.md"
            registry = root / "registry.md"
            readme = root / "README.md"
            report = root / "report.md"
            manifest_path = root / "manifest.json"
            prereg.write_text("- **Status:** PREREGISTERED\n", encoding="utf-8")
            registry.write_text("# Registry\n", encoding="utf-8")
            readme.write_text("# README\n", encoding="utf-8")
            report.write_text("report\n", encoding="utf-8")
            manifest_path.write_text(json.dumps({
                "hypothesis_id": persistence.HYPOTHESIS_ID,
                "source_commit_sha": "old",
            }), encoding="utf-8")
            with patch.object(persistence, "PREREG_PATH", prereg), patch.object(
                persistence, "REGISTRY_PATH", registry
            ), patch.object(persistence, "README_PATH", readme), patch.dict(
                os.environ, {"GITHUB_SHA": "new"}
            ):
                with self.assertRaisesRegex(ValueError, "source_commit_sha"):
                    persistence.persist(manifest_path, report)


if __name__ == "__main__":
    unittest.main()
