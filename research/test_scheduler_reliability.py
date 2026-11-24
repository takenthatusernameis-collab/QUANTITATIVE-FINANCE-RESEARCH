from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "spot-holdout-capture.yml"
TASK = ROOT / "tasks" / "PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md"
POLICY = ROOT / "docs" / "EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md"


class ExternalSchedulerReliabilityTests(unittest.TestCase):
    def test_capture_cron_is_explicitly_non_authoritative(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Best-effort opportunistic trigger only", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("issue_comment:", workflow)

    def test_existing_owner_authorization_is_not_weakened(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ "$ACTOR" != "takenthatusernameis-collab" ]; then', workflow)
        self.assertIn('[ "$COMMENT_USER" != "takenthatusernameis-collab" ] ||', workflow)
        self.assertIn('[ "$ISSUE_NUMBER" != "2" ] ||', workflow)
        self.assertIn('[ "$COMMENT_BODY" != "/qfr-capture-spot-holdout" ]; then', workflow)

    def test_capture_task_requires_external_dispatch_not_next_cron(self):
        task = TASK.read_text(encoding="utf-8").lower()
        self.assertIn("independently operated authenticated scheduler", task)
        self.assertIn("idempotency key", task)
        self.assertIn("independent watchdog", task)
        self.assertIn("do not wait for the next github cron tick", task)
        self.assertIn("first authorized agent wake-up", task)
        self.assertIn("snapshot-slot-2026-11-24.zip", task)

    def test_policy_requires_first_agent_wakeup_fallback_when_automation_is_missing(self):
        policy = POLICY.read_text(encoding="utf-8").lower()
        for phrase in (
            "first authorized agent",
            "after a task's explicit due time",
            "direct-agent fallback",
            "stable task/slot idempotency key",
            "do not wait for another attempt",
        ):
            self.assertIn(phrase, policy)

    def test_task_and_workflow_support_serialized_direct_agent_recovery(self):
        task = TASK.read_text(encoding="utf-8").lower()
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("first authorized agent wake-up", task)
        self.assertIn("snapshot-slot-yyyy-mm-dd.zip", task)
        self.assertIn("group: spot-holdout-capture", workflow)
        self.assertIn("queue: max", workflow)
        self.assertIn("cancel-in-progress: false", workflow)

    def test_policy_requires_observed_run_and_independent_watchdog(self):
        policy = POLICY.read_text(encoding="utf-8").lower()
        for phrase in (
            "best-effort only",
            "independent scheduler",
            "authenticated dispatch",
            "deterministic slot identity",
            "durable dispatch ledger",
            "run observation",
            "independent watchdog",
            "delivery_verified",
        ):
            self.assertIn(phrase, policy)


if __name__ == "__main__":
    unittest.main()
