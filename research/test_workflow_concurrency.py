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

if __name__ == "__main__":
    unittest.main()
