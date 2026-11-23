from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "eth-btc-research.yml"


class WorkflowConcurrencyPolicyTests(unittest.TestCase):
    def test_untrusted_issue_comments_do_not_block_the_authorized_research_queue(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        match = re.search(r"(?m)^  group: (\$\{\{.*\}\})$", workflow)
        self.assertIsNotNone(match, "workflow-level concurrency group must be explicit")
        expression = match.group(1)

        for required in (
            "github.event_name == 'issue_comment'",
            "github.event.action != 'created'",
            "github.event.issue.number != 2",
            "github.event.issue.pull_request == null",
            "github.event.issue.state != 'open'",
            "github.event.comment.user.login != 'takenthatusernameis-collab'",
            "!contains(fromJSON(",
            "format('eth-btc-research-ignored-{0}', github.event.comment.id)",
            "|| 'eth-btc-research-main'",
        ):
            self.assertIn(required, expression)

        authorization_block = workflow.split('case "$COMMENT_BODY" in', 1)[1].split("esac", 1)[0]
        authorization_commands = set(
            re.findall(r'^\s*"(/qfr-[^"]+)"\)', authorization_block, re.MULTILINE)
        )
        concurrency_commands = set(re.findall(r'"(/qfr-[^"]+)"', expression))
        self.assertEqual(concurrency_commands, authorization_commands)
        self.assertNotIn("/qfr-queue-guardian-live", concurrency_commands)
        self.assertIn("  queue: max", workflow)
        self.assertIn("  cancel-in-progress: false", workflow)



    def test_tardis_schedule_change_samples_are_exactly_dated(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        for sample_date in ("2025-06-01", "2025-10-01", "2026-02-01"):
            command = f"/qfr-probe-tardis-funding-{sample_date}"
            block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
            self.assertIn('COMMAND="tardis-probe"', block)
            self.assertIn(f'START="{sample_date}"', block)
            self.assertIn(f'END="{sample_date}"', block)
            self.assertIn('MARKET="both"', block)
            self.assertIn('RECONCILE="false"', block)


    def test_mexc_probe_is_allowlisted_and_bounded(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        block = workflow.split('"/qfr-probe-mexc-funding-history")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="mexc-probe"', block)
        self.assertIn('START="2020-01-01"', block)
        self.assertIn('END="2026-10-31"', block)
        self.assertIn("MEXC_SYMBOLS: BTC_USDT,ETH_USDT", workflow)
        self.assertIn("PAGE_SIZE: '1000'", workflow)
        self.assertIn("MAX_PAGES: '200'", workflow)
        self.assertIn("MAX_RECORDS: '200000'", workflow)
        self.assertIn("Upload MEXC manifests (never raw pages)", workflow)

    def test_kraken_residual_anomaly_audit_is_allowlisted_exact_and_manifest_only(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-residual-anomalies"
        block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="kraken-anomaly-audit"', block)
        self.assertIn('START="2018-01-01"', block)
        self.assertIn('END="2026-11-23"', block)
        self.assertIn('RECONCILE="false"', block)
        self.assertIn(command, workflow.split("case \"$COMMENT_BODY\" in", 1)[0])
        self.assertIn("needs.authorize.outputs.command == 'kraken-anomaly-audit'", workflow)
        self.assertIn("MODE=anomaly-audit", workflow)
        self.assertIn('kraken_funding_export_probe.py --mode "$MODE"', workflow)
        self.assertIn("target_symbols=set(TARGETED_SYMBOLS)", (ROOT / "research" / "kraken_funding_export_probe.py").read_text(encoding="utf-8"))
        artifact_block = workflow.split("name: Upload compact evidence only (never raw ZIP or CSV)", 1)[1].split("\n\n", 1)[0]
        self.assertIn("/manifest.json", artifact_block)
        self.assertIn("/*.png", artifact_block)
        self.assertNotIn("*.zip", artifact_block.lower())
        self.assertNotIn("*.csv", artifact_block.lower())

    def test_kraken_api_rate_cap_census_is_allowlisted_exact_and_manifest_only(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-rate-cap-census"
        block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="kraken-api-cap-audit"', block)
        self.assertIn('START="2018-01-01"', block)
        self.assertIn('END="2026-11-23"', block)
        self.assertIn('RECONCILE="false"', block)
        self.assertIn(command, workflow.split("case \"$COMMENT_BODY\" in", 1)[0])
        self.assertIn("needs.authorize.outputs.command == 'kraken-api-cap-audit'", workflow)
        artifact_block = workflow.split("name: Upload manifest only (never raw API rows)", 1)[1].split("\n\n", 1)[0]
        self.assertIn("/manifest.json", artifact_block)
        self.assertNotIn("*.zip", artifact_block.lower())
        self.assertNotIn("*.csv", artifact_block.lower())

    def test_kraken_tardis_timestamp_probe_is_allowlisted_and_bounded(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-tardis-timestamp-mapping"
        block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="kraken-tardis-timestamp-audit"', block)
        self.assertIn('START="2026-10-01"', block)
        self.assertIn('END="2026-10-01"', block)
        self.assertIn('MARKET="both"', block)
        self.assertIn('RECONCILE="false"', block)
        self.assertIn(command, workflow.split('case "$COMMENT_BODY" in', 1)[0])
        self.assertIn("needs.authorize.outputs.command == 'kraken-tardis-timestamp-audit'", workflow)
        job = workflow.split("  kraken-tardis-timestamp-probe:", 1)[1].split("\n\n  kraken-pi-price-validation:", 1)[0]
        self.assertIn("python research/kraken_tardis_timestamp_probe.py", job)
        self.assertIn("/manifest.json", job)
        self.assertNotIn(r"\${{", job)
        self.assertIn("if: ${{ needs.authorize.outputs.authorized", job)
        self.assertNotIn("*.csv", job.lower())
        self.assertNotIn("*.gz", job.lower())
        probe = (ROOT / "research" / "kraken_tardis_timestamp_probe.py").read_text(encoding="utf-8")
        self.assertIn("PI_XBTUSD", probe)
        self.assertIn("PI_ETHUSD", probe)
        self.assertIn("settlement_population_complete", probe)

    def test_kraken_tardis_gap_probe_is_allowlisted_and_bounded(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-tardis-gap-events"
        block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="kraken-tardis-gap-audit"', block)
        self.assertIn('START="2025-12-04"', block)
        self.assertIn('END="2026-10-30"', block)
        self.assertIn('MARKET="both"', block)
        self.assertIn('RECONCILE="false"', block)
        self.assertIn(command, workflow.split('case "$COMMENT_BODY" in', 1)[0])
        self.assertIn("needs.authorize.outputs.command == 'kraken-tardis-gap-audit'", workflow)
        job = workflow.split("  kraken-tardis-gap-event-probe:", 1)[1].split("\n\n  kraken-pi-price-validation:", 1)[0]
        self.assertIn("python research/kraken_tardis_gap_probe.py", job)
        self.assertIn("/manifest.json", job)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", job)
        self.assertNotIn("*.csv", job.lower())
        self.assertNotIn("*.gz", job.lower())

    def test_kraken_pi_price_validation_is_allowlisted_and_bounded(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        command = "/qfr-audit-kraken-pi-price-validation"
        block = workflow.split(f'"{command}")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="kraken-pi-price-validation"', block)
        self.assertIn('START="2026-08-20"', block)
        self.assertIn('END="2026-10-30"', block)
        self.assertIn('MARKET="both"', block)
        self.assertIn('RECONCILE="false"', block)
        self.assertIn(command, workflow.split('case "$COMMENT_BODY" in', 1)[0])
        self.assertIn("needs.authorize.outputs.command == 'kraken-pi-price-validation'", workflow)
        self.assertIn("python research/kraken_pi_price_validation.py", workflow)
        job = workflow.split("  kraken-pi-price-validation:", 1)[1].split("\n\n  okx-funding-button-probe:", 1)[0]
        self.assertIn("/manifest.json", job)
        self.assertIn("retention-days: 30", job)
        self.assertNotIn("*.zip", job.lower())
        self.assertNotIn("*.csv", job.lower())


    def test_bybit_probe_is_allowlisted_and_bounded(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        block = workflow.split('"/qfr-probe-bybit-funding-history")', 1)[1].split(";;", 1)[0]
        self.assertIn('COMMAND="bybit-probe"', block)
        self.assertIn('START="2020-01-01"', block)
        self.assertIn('END="2026-11-22"', block)
        self.assertIn("BYBIT_SYMBOLS: BTCUSDT,ETHUSDT", workflow)
        self.assertIn("LIMIT: '200'", workflow)
        self.assertIn("Upload Bybit sample manifests (never raw responses)", workflow)
        self.assertIn("bybit-funding-probe-${{ github.run_id }}/*.json", workflow)

if __name__ == "__main__":
    unittest.main()
