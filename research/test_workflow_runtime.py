from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
EXPECTED_NODE24_ACTIONS = {
    "actions/checkout": "v7.0.1",
    "actions/setup-python": "v7.1.0",
    "actions/cache": "v6.1.0",
    "actions/upload-artifact": "v7.0.2",
}


class GitHubActionRuntimeTests(unittest.TestCase):
    def test_workflows_use_verified_node24_action_releases(self):
        observed = {}
        for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith("uses:"):
                    continue
                reference = stripped.split("uses:", 1)[1].strip()
                if "@" not in reference:
                    continue
                action, version = reference.rsplit("@", 1)
                if action in EXPECTED_NODE24_ACTIONS:
                    observed.setdefault(action, set()).add(version)

        self.assertEqual(
            observed,
            {name: {version} for name, version in EXPECTED_NODE24_ACTIONS.items()},
        )

    def test_bitget_public_download_probe_is_exactly_allowlisted(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-probe-bitget-funding-download"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn("command == 'bitget-probe'", workflow)
        self.assertIn("python research/bitget_funding_download_probe.py", workflow)
        self.assertIn("anonymous", workflow.lower())
        self.assertIn("playwright", workflow.lower())
        self.assertIn("/qfr-probe-okx-funding-download", workflow)
        self.assertIn("command == 'okx-probe'", workflow)
        probe_job = workflow.split("  bitget-funding-download-probe:", 1)[1]
        self.assertIn("TARGET_URL:", probe_job)
        self.assertIn("funding_rate", probe_job)
        self.assertIn("historical-data", probe_job)
        self.assertIn("playwright==1.65.0", workflow)
        self.assertNotIn("playwright==1.56.0", workflow)
        probe = (ROOT / "research" / "bitget_funding_download_probe.py").read_text(encoding="utf-8")
        self.assertIn("download_click_skipped_reason", probe)
        self.assertIn("is_geographically_restricted", probe)
        self.assertIn("blocked_geographic_restriction", probe)
        self.assertIn("download_button_clicked", probe)
        self.assertNotIn("candidates[0][\"locator\"].click", probe)

    def test_okx_funding_button_probe_is_exactly_allowlisted(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-probe-okx-funding-button"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="okx-button-probe"', workflow)
        self.assertIn("command == 'okx-button-probe'", workflow)
        self.assertIn("okx-funding-button-probe:", workflow)
        self.assertIn("python research/okx_funding_button_probe.py", workflow)
        self.assertIn("cancel direct downloads immediately", workflow.lower())

    def test_deprecated_node20_action_refs_are_absent(self):
        for workflow in WORKFLOW_DIR.glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            for old in (
                "actions/checkout@v4",
                "actions/setup-python@v5",
                "actions/cache@v4",
                "actions/upload-artifact@v4",
            ):
                self.assertNotIn(old, text, str(workflow))


if __name__ == "__main__":
    unittest.main()
