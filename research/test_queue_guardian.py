import unittest
from datetime import datetime, timedelta, timezone

from queue_guardian import (
    QUEUE_TIMEOUT_SECONDS,
    concurrency_group,
    parse_timestamp,
    process_queue,
    queue_decision,
)

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def make_run(run_id, workflow, status, created_at):
    return {
        "id": run_id,
        "name": workflow,
        "path": f".github/workflows/{workflow}.yml@refs/heads/main",
        "status": status,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "head_sha": f"{run_id:040x}",
        "html_url": f"https://github.com/example/repo/actions/runs/{run_id}",
        "event": "push",
        "actor": {"login": "github-actions[bot]"},
    }


class QueueDecisionTests(unittest.TestCase):
    def test_exactly_fifteen_minutes_is_not_over_threshold(self):
        queued = make_run(10, "research-tests", "queued",
                          NOW - timedelta(seconds=QUEUE_TIMEOUT_SECONDS))
        self.assertEqual(queue_decision(queued, [queued], NOW)["action"],
                         "wait_under_threshold")

    def test_queued_without_predecessor_is_cancelled_after_fifteen_minutes(self):
        queued = make_run(11, "research-tests", "queued",
                          NOW - timedelta(minutes=15, seconds=1))
        decision = queue_decision(queued, [queued], NOW)
        self.assertEqual(decision["action"], "cancel_overdue")
        self.assertEqual(decision["reason"],
                         "QUEUE_TIMEOUT_OVER_15M_NO_ACTIVE_SAME_GROUP_PREDECESSOR")

    def test_earlier_active_same_group_predecessor_is_only_exemption(self):
        queued = make_run(12, "eth-btc-research", "pending", NOW - timedelta(hours=2))
        predecessor = make_run(11, "eth-btc-research", "in_progress", NOW - timedelta(hours=3))
        decision = queue_decision(queued, [predecessor, queued], NOW)
        self.assertEqual(decision["action"], "preserve_same_group_wait")
        self.assertEqual(decision["predecessor_run_id"], 11)

    def test_active_different_group_does_not_exempt(self):
        queued = make_run(13, "research-tests", "queued", NOW - timedelta(minutes=16))
        active = make_run(12, "eth-btc-research", "in_progress", NOW - timedelta(hours=1))
        self.assertEqual(queue_decision(queued, [active, queued], NOW)["action"],
                         "cancel_overdue")

    def test_later_created_same_group_active_run_does_not_exempt(self):
        queued = make_run(14, "research-tests", "queued", NOW - timedelta(minutes=16))
        active_later = make_run(15, "research-tests", "in_progress", NOW - timedelta(minutes=5))
        self.assertEqual(queue_decision(queued, [queued, active_later], NOW)["action"],
                         "cancel_overdue")

    def test_queued_or_pending_run_is_not_a_predecessor(self):
        queued = make_run(16, "research-tests", "queued", NOW - timedelta(minutes=16))
        other = make_run(15, "research-tests", "pending", NOW - timedelta(minutes=20))
        self.assertEqual(queue_decision(queued, [other, queued], NOW)["action"],
                         "cancel_overdue")

    def test_running_or_environment_waiting_workflow_is_not_cancelled(self):
        for status in ("in_progress", "waiting", "completed"):
            item = make_run(17, "research-tests", status, NOW - timedelta(hours=4))
            self.assertNotEqual(queue_decision(item, [item], NOW)["action"],
                                "cancel_overdue")

    def test_unmapped_workflow_is_never_cancelled(self):
        item = make_run(18, "unknown-workflow", "queued", NOW - timedelta(hours=1))
        self.assertEqual(queue_decision(item, [item], NOW)["action"],
                         "ignore_unmapped_workflow")

    def test_workflow_path_with_or_without_ref_suffix_is_mapped(self):
        item = make_run(19, "eth-btc-research", "queued", NOW - timedelta(minutes=16))
        item["path"] = ".github/workflows/eth-btc-research.yml"
        self.assertEqual(concurrency_group(item), "eth-btc-research-main")
        self.assertEqual(queue_decision(item, [item], NOW)["action"], "cancel_overdue")

    def test_timestamp_must_include_timezone(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-11-22T10:00:00")


class FakeAPI:
    def __init__(self, runs, cancel_state=None):
        self.runs = list(runs)
        self.cancel_state = cancel_state or {"status": "completed", "conclusion": "cancelled"}
        self.cancelled = []
        self.issues = []

    def list_all_runs(self):
        return list(self.runs)

    def get_run(self, run_id):
        return next(item for item in self.runs if item["id"] == run_id)

    def cancel_run(self, run_id):
        self.cancelled.append(run_id)
        self.get_run(run_id).update(self.cancel_state)

    def find_incident_issue(self, run_id):
        marker = f"<!-- qfr-queue-run:{run_id} -->"
        return next((issue for issue in self.issues if marker in issue["body"]), None)

    def create_issue(self, title, body):
        issue = {"number": 123, "html_url": "https://github.com/example/repo/issues/123",
                 "title": title, "body": body}
        self.issues.append(issue)
        return issue


class QueueProcessingTests(unittest.TestCase):
    def test_cancels_overdue_and_creates_retry_issue(self):
        item = make_run(20, "research-tests", "queued", NOW - timedelta(minutes=20))
        api = FakeAPI([item])
        report = process_queue(api, NOW)
        self.assertEqual(api.cancelled, [20])
        self.assertEqual(report["actions"][0]["result"], "CANCELLED_RETRY_REQUIRED")
        self.assertTrue(report["actions"][0]["issue_created"])
        self.assertIn("QUEUE_CANCELLED / RETRY_REQUIRED", api.issues[0]["body"])

    def test_failed_cancellation_creates_orphan_and_alternative_issue(self):
        item = make_run(21, "eth-btc-research", "pending", NOW - timedelta(minutes=19))
        api = FakeAPI([item], cancel_state={"status": "queued", "conclusion": None})
        report = process_queue(api, NOW)
        self.assertEqual(report["actions"][0]["result"],
                         "CANCELLATION_BLOCKED_OR_UNCONFIRMED")
        self.assertIn("CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION",
                      api.issues[0]["body"])
        self.assertIn("independently isolated alternative attempt", api.issues[0]["body"])

    def test_preserves_active_same_group_predecessor(self):
        item = make_run(22, "eth-btc-research", "pending", NOW - timedelta(minutes=55))
        active = make_run(21, "eth-btc-research", "in_progress", NOW - timedelta(hours=1))
        api = FakeAPI([active, item])
        report = process_queue(api, NOW)
        self.assertEqual(api.cancelled, [])
        self.assertEqual(report["actions"][0]["action"], "preserve_same_group_wait")

    def test_dry_run_never_cancels_or_creates_issue(self):
        item = make_run(23, "research-tests", "queued", NOW - timedelta(minutes=25))
        api = FakeAPI([item])
        report = process_queue(api, NOW, dry_run=True)
        self.assertEqual(api.cancelled, [])
        self.assertEqual(report["actions"][0]["result"], "DRY_RUN_WOULD_CANCEL")
        self.assertEqual(api.issues, [])


if __name__ == "__main__":
    unittest.main()
