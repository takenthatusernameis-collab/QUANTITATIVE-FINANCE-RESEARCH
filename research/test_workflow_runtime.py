from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
EXPECTED_NODE24_ACTIONS = {
    "actions/checkout": "v7.0.1",
    "actions/setup-python": "v7.1.0",
    "actions/cache": "v6.1.0",
    "actions/cache/restore": "v6.1.0",
    "actions/cache/save": "v6.1.0",
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

    def test_kraken_funding_export_probe_is_exactly_allowlisted_and_ephemeral(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-probe-kraken-funding-export"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="kraken-export-probe"', workflow)
        self.assertIn("command == 'kraken-export-probe'", workflow)
        self.assertIn("kraken-funding-export-probe:", workflow)
        self.assertIn("python research/kraken_funding_export_probe.py", workflow)
        self.assertIn("never raw ZIP or CSV", workflow)
        probe = (ROOT / "research" / "kraken_funding_export_probe.py").read_text(encoding="utf-8")
        self.assertIn("raw_download_uploaded", probe)
        self.assertIn("raw_download_committed", probe)
        self.assertIn("historical-funding-rates", probe)
        self.assertIn("relativefundingrate", probe.lower())
        self.assertIn("TemporaryDirectory", probe)

    def test_kraken_api_rate_cap_census_is_separate_and_archive_free(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-rate-cap-census"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn('COMMAND="kraken-api-cap-audit"', workflow)
        self.assertIn("kraken-api-cap-audit:", workflow)
        self.assertIn("--mode api-cap-audit", workflow)
        job = workflow.split("  kraken-api-cap-audit:", 1)[1].split("\n\n  okx-funding-button-probe:", 1)[0]
        self.assertNotIn("playwright", job.lower())
        self.assertNotIn("zip", job.lower())
        self.assertIn("Install HTTP client only", job)
        self.assertIn("/manifest.json", job)
        probe = (ROOT / "research" / "kraken_funding_export_probe.py").read_text(encoding="utf-8")
        self.assertIn('"api-cap-audit"', probe)
        self.assertIn("def run_api_cap_audit", probe)
        self.assertIn("rows_unassessed", probe)
        self.assertIn("exceeds_documented_cap_rows", probe)

    def test_kraken_tardis_timestamp_probe_is_bounded_and_manifest_only(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-tardis-timestamp-mapping"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="kraken-tardis-timestamp-audit"', workflow)
        self.assertIn("command == 'kraken-tardis-timestamp-audit'", workflow)
        self.assertIn("kraken-tardis-timestamp-probe:", workflow)
        job = workflow.split("  kraken-tardis-timestamp-probe:", 1)[1].split("\n\n  kraken-pi-price-validation:", 1)[0]
        self.assertIn("python research/kraken_tardis_timestamp_probe.py", job)
        self.assertIn("2026-10-01", job)
        self.assertIn("/manifest.json", job)
        self.assertIn("retention-days: 30", job)
        self.assertNotIn("*.csv", job.lower())
        self.assertNotIn("*.gz", job.lower())
        probe = (ROOT / "research" / "kraken_tardis_timestamp_probe.py").read_text(encoding="utf-8")
        for required in ("funding_timestamp", "relativeFundingRate", "settlement_population_complete",
                         "raw_data_uploaded", "historical_archive_downloaded", "MAX_AGE_SECONDS"):
            self.assertIn(required, probe)

    def test_kraken_pi_price_validation_job_is_bounded_and_manifest_only(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-pi-price-validation"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="kraken-pi-price-validation"', workflow)
        self.assertIn("command == 'kraken-pi-price-validation'", workflow)
        self.assertIn("kraken-pi-price-validation:", workflow)
        job = workflow.split("  kraken-pi-price-validation:", 1)[1].split("\n  okx-funding-button-probe:", 1)[0]
        self.assertIn("python research/kraken_pi_price_validation.py", job)
        self.assertIn("granularity", (ROOT / "research" / "kraken_pi_price_validation.py").read_text(encoding="utf-8"))
        self.assertIn("/manifest.json", job)
        self.assertIn("retention-days: 30", job)
        self.assertNotIn("playwright", job.lower())
        self.assertNotIn("*.zip", job.lower())
        self.assertNotIn("*.csv", job.lower())
        probe = (ROOT / "research" / "kraken_pi_price_validation.py").read_text(encoding="utf-8")
        self.assertIn("raw_response_retained", probe)
        self.assertIn("raw_candle_arrays_uploaded", probe)
        self.assertIn("pre_start_extra_count", probe)
        self.assertIn("no missing hour is filled", probe)


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

    def test_okx_field_info_probe_is_exactly_allowlisted(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-probe-okx-funding-field-info"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="okx-field-info-probe"', workflow)
        self.assertIn("command == 'okx-field-info-probe'", workflow)
        self.assertIn("--inspect-field-info", workflow)
        self.assertIn("okx-funding-field-info-probe-", workflow)

    def test_okx_symbol_options_probe_is_exactly_allowlisted(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        command = "/qfr-probe-okx-funding-symbols"
        self.assertIn(f'"{command}"', workflow)
        self.assertIn(f'"{command}")', workflow)
        self.assertIn('COMMAND="okx-symbol-options-probe"', workflow)
        self.assertIn("command == 'okx-symbol-options-probe'", workflow)
        self.assertIn("--inspect-symbol-options", workflow)
        self.assertIn("okx-funding-symbol-options-probe-", workflow)

    def test_research_cache_does_not_override_low_trust_read_only_default(self):
        workflow = (WORKFLOW_DIR / "eth-btc-research.yml").read_text(encoding="utf-8")
        match = re.search(
            r"(?ms)^  empirical-research:\n(?P<job>.*?)(?=^  [a-z0-9_-]+:\n|\Z)",
            workflow,
        )
        self.assertIsNotNone(match, "empirical-research job must be present")
        job = match.group("job")
        cache_match = re.search(
            r"(?ms)^      - name: Cache Binance archives\n(?P<step>.*?)(?=^      - name:|\Z)",
            job,
        )
        self.assertIsNotNone(cache_match, "archive cache step must be present")
        cache_step = cache_match.group("step")
        self.assertIn("actions/cache@v6.1.0", cache_step)
        self.assertIn("path: data/cache/", cache_step)
        self.assertIn("key: binance-archives-run-${{ github.run_id }}-${{ github.run_attempt }}", cache_step)
        self.assertIn("restore-keys:", cache_step)
        self.assertIn("binance-archives-warm-", cache_step)
        self.assertIn("binance-archives-run-", cache_step)
        self.assertIn("restore-keys:", cache_step)
        self.assertIn("issue_comment is low-trust", cache_step)
        self.assertIn("Do not override with cache-mode: write", cache_step)
        # Protect this research workflow from an accidental cache-write bypass.
        self.assertNotRegex(
            workflow,
            r"(?m)^\s*cache-mode:\s*(?:write|write-only)\s*$",
        )


    def test_trusted_cache_warm_workflow_is_bounded_and_manifest_only(self):
        warm = (WORKFLOW_DIR / "eth-btc-cache-warm.yml").read_text(encoding="utf-8")
        self.assertIn("schedule:", warm)
        self.assertIn("workflow_dispatch:", warm)
        self.assertIn("push:", warm)
        self.assertIn("branches: [main]", warm)
        self.assertIn("if: ${{ github.ref == 'refs/heads/main' }}", warm)
        self.assertIn("ref: main", warm)
        self.assertIn("group: binance-archive-cache-warm", warm)
        self.assertNotIn("issue_comment:", warm)
        self.assertNotIn("workflow_run:", warm)
        self.assertIn("actions/cache/restore@v6.1.0", warm)
        self.assertIn("actions/cache/save@v6.1.0", warm)
        self.assertIn("key: binance-archives-warm-${{ github.run_id }}-${{ github.run_attempt }}", warm)
        self.assertIn("--start 2024-01-01", warm)
        self.assertIn("--end 2024-01-31", warm)
        self.assertIn("--market both", warm)
        self.assertIn("--audit-only", warm)
        self.assertNotIn("--reconcile-spot-gaps", warm)
        self.assertIn("checksum_verified", warm)
        self.assertIn("steps.validate.outcome == 'success'", warm)
        self.assertIn("data/raw/spot_ETHUSDT_archive_manifest.json", warm)
        self.assertIn("data/raw/um_BTCUSDT_funding_manifest.json", warm)
        guardian = (WORKFLOW_DIR / "queue-guardian.yml").read_text(encoding="utf-8")
        self.assertIn("Trusted Binance archive cache warmer", guardian)
        self.assertIn("github.event.workflow_run.name == 'Trusted Binance archive cache warmer'", guardian)
        artifact = warm.split("      - name: Upload manifests and diagnostics only", 1)[1]
        self.assertNotIn("data/cache/", artifact)
        self.assertNotIn(".csv", artifact)
        self.assertNotIn(".zip", artifact)
        self.assertNotIn("cache-mode:", warm)

    def test_deprecated_node20_action_refs_are_absent(self):
        for workflow in WORKFLOW_DIR.glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            for old in (
                "actions/checkout@v4",
                "actions/setup-python@v5",
                "actions/cache@v4",
                "actions/cache/restore@v4",
                "actions/cache/save@v4",
                "actions/upload-artifact@v4",
            ):
                self.assertNotIn(old, text, str(workflow))


if __name__ == "__main__":
    unittest.main()
