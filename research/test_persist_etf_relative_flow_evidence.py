from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import etf_relative_flow_ethbtc as model
import persist_etf_relative_flow_evidence as helper


class ETFRelativeFlowEvidencePersistenceTests(unittest.TestCase):
    def test_persistence_verifies_canonical_paths_and_report_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "reports" / "sessions" / "report.md"
            manifest_path = root / "reports" / "generated" / "manifest.json"
            registry = root / "research" / "HYPOTHESIS-REGISTRY.md"
            prereg = root / "research" / "PREREG.md"
            report.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            registry.parent.mkdir(parents=True)
            report.write_text("frozen report", encoding="utf-8")
            registry.write_text("| header |\n|---|\n", encoding="utf-8")
            prereg.write_text("- **Status:** ADMITTED; source feasibility PASS; empirical backtest pending.\n", encoding="utf-8")
            manifest = {
                "report_path": report.relative_to(root).as_posix(),
                "manifest_path": manifest_path.relative_to(root).as_posix(),
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "status": "COMPLETE",
                "decision": "INCONCLUSIVE",
                "run_id": "123",
                "source_commit_sha": "abc",
                "validation": {"n": 50, "rmse_improvement_pct": 0.1},
                "test": {"n": 70, "rmse_improvement_pct": -0.1},
                "paired_test_loss_bootstrap": {"ci_95_low_bp2": -0.1, "ci_95_high_bp2": 0.1},
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(model, "ROOT", root), patch.object(model, "REGISTRY_PATH", registry), patch.object(
                model, "PREREG_PATH", prereg
            ):
                result = helper.persist(manifest_path, report)
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(result["report_sha256"], manifest["report_sha256"])
            self.assertEqual(saved["registry_sha256"], hashlib.sha256(registry.read_bytes()).hexdigest())
            self.assertEqual(saved["prereg_sha256"], hashlib.sha256(prereg.read_bytes()).hexdigest())
            self.assertIn("BACKTESTED", registry.read_text(encoding="utf-8"))

    def test_persistence_rejects_report_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "reports" / "sessions" / "report.md"
            manifest_path = root / "reports" / "generated" / "manifest.json"
            report.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            report.write_text("changed report", encoding="utf-8")
            manifest = {
                "report_path": report.relative_to(root).as_posix(),
                "manifest_path": manifest_path.relative_to(root).as_posix(),
                "report_sha256": "0" * 64,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(model, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    helper.persist(manifest_path, report)


if __name__ == "__main__":
    unittest.main()
