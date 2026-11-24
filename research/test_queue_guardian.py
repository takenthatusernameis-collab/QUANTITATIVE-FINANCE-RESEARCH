import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from queue_guardian import (
    GitHubAPI,
    build_execution_context,
    build_run_inventory,
    QUEUE_TIMEOUT_SECONDS,
    STATUS_MARKER,
    format_status_comment,
    group_for,
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


class WorkflowControlTests(unittest.TestCase):
    def test_live_control_comment_is_exactly_gated_and_preserves_dry_run(self):
        workflow_path = (
            Path(__file__).resolve().parents[1]
            / ".github" / "workflows" / "queue-guardian.yml"
        )
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn("github.event.issue.number == 2", workflow)
        self.assertIn("github.event.comment.user.login == 'takenthatusernameis-collab'", workflow)
        self.assertIn("github.event.comment.body == '/qfr-queue-guardian-dry-run'", workflow)
        self.assertIn("github.event.comment.body == '/qfr-queue-guardian-live'", workflow)
        self.assertIn(
            "DRY_RUN: ${{ github.event_name != 'schedule' && "
            "github.event_name != 'workflow_run' && github.event.comment.body != '/qfr-queue-guardian-live' }}",
            workflow,
        )


    def test_research_completion_event_is_scoped_and_live(self):
        workflow_path = (
            Path(__file__).resolve().parents[1]
            / ".github" / "workflows" / "queue-guardian.yml"
        )
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn("workflow_run:", workflow)
        self.assertIn("ETH-BTC networked empirical research", workflow)
        self.assertIn("workflow_id == 425839329", workflow)
        self.assertIn("workflow_run.event == 'issue_comment'", workflow)
        self.assertIn("workflow_run.head_branch == github.event.repository.default_branch", workflow)
        self.assertIn("workflow_run.head_repository.full_name == github.repository", workflow)
        self.assertIn("workflow_run.actor.login == 'takenthatusernameis-collab'", workflow)
        self.assertIn("github.event_name != 'workflow_run' &&", workflow)

    def test_binance_spot_universe_completion_event_is_scoped_and_observable(self):
        workflow_path = (
            Path(__file__).resolve().parents[1]
            / ".github" / "workflows" / "queue-guardian.yml"
        )
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("Binance Spot dynamic-universe feasibility audit", workflow)
        self.assertIn(
            "github.event.workflow_run.name == 'Binance Spot dynamic-universe feasibility audit'",
            workflow,
        )
        self.assertIn("github.event.workflow_run.event == 'issue_comment'", workflow)
        self.assertIn("github.event.workflow_run.display_title == 'Authorized Binance Spot universe audit'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == github.event.repository.default_branch", workflow)
        self.assertIn("github.event.workflow_run.actor.login == 'takenthatusernameis-collab'", workflow)

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
        self.assertEqual(group_for(item), "eth-btc-research-main")
        self.assertEqual(queue_decision(item, [item], NOW)["action"], "cancel_overdue")

    def test_cache_warm_workflow_has_isolated_queue_group_and_is_observable(self):
        queued = make_run(
            24, "eth-btc-cache-warm", "queued",
            NOW - timedelta(minutes=16),
        )
        active = make_run(
            23, "eth-btc-cache-warm", "in_progress",
            NOW - timedelta(hours=1),
        )
        self.assertEqual(group_for(queued), "binance-archive-cache-warm")
        self.assertEqual(
            queue_decision(queued, [queued], NOW)["action"],
            "cancel_overdue",
        )
        self.assertEqual(
            queue_decision(queued, [active, queued], NOW)["action"],
            "preserve_same_group_wait",
        )
        inventory = build_run_inventory([queued])
        self.assertEqual(
            inventory[0]["workflow_name"],
            "Trusted Binance archive cache warmer",
        )

    def test_binance_spot_universe_audit_has_isolated_queue_group_and_is_observable(self):
        queued = make_run(
            25, "binance-spot-universe-audit", "queued",
            NOW - timedelta(minutes=16),
        )
        active = make_run(
            26, "binance-spot-universe-audit", "in_progress",
            NOW - timedelta(hours=1),
        )
        for item in (queued, active):
            item["display_title"] = "Authorized Binance Spot universe audit"
            item["head_branch"] = "main"
            item["head_repository"] = {
                "full_name": "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"
            }
            item["actor"] = {"login": "takenthatusernameis-collab"}
        self.assertEqual(group_for(queued), "binance-spot-universe-audit-main")
        self.assertEqual(queue_decision(queued, [queued], NOW)["action"], "cancel_overdue")
        self.assertEqual(
            queue_decision(queued, [active, queued], NOW)["action"],
            "preserve_same_group_wait",
        )
        inventory = build_run_inventory([queued])
        self.assertEqual(
            inventory[0]["workflow_name"],
            "Binance Spot dynamic-universe feasibility audit",
        )
        self.assertEqual(
            inventory[0]["display_title"],
            "Authorized Binance Spot universe audit",
        )

    def test_unauthorized_spot_audit_run_gets_its_own_queue_group(self):
        item = make_run(
            27, "binance-spot-universe-audit", "queued",
            NOW - timedelta(minutes=16),
        )
        item["display_title"] = "Ignored Binance Spot audit comment 999"
        item["event"] = "issue_comment"
        self.assertEqual(
            group_for(item),
            "binance-spot-universe-audit-ignored-27",
        )
        self.assertEqual(
            queue_decision(item, [item], NOW)["action"],
            "cancel_overdue",
        )

    def test_timestamp_must_include_timezone(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-11-22T10:00:00")


class FakeAPI:
    def __init__(self, runs, cancel_state=None, cancel_error=None):
        self.runs = list(runs)
        self.cancel_state = cancel_state or {"status": "completed", "conclusion": "cancelled"}
        self.cancel_error = cancel_error
        self.cancelled = []
        self.issues = []

    def list_all_runs(self):
        return list(self.runs)

    def get_run(self, run_id):
        return next(item for item in self.runs if item["id"] == run_id)

    def cancel_run(self, run_id):
        self.cancelled.append(run_id)
        if self.cancel_error:
            raise self.cancel_error
        self.get_run(run_id).update(self.cancel_state)

    def find_incident_issue(self, run_id):
        marker = f"<!-- qfr-queue-run:{run_id} -->"
        return next((issue for issue in self.issues if marker in issue["body"]), None)

    def create_issue(self, title, body):
        issue = {"number": 123, "html_url": "https://github.com/example/repo/issues/123",
                 "title": title, "body": body}
        self.issues.append(issue)
        return issue


class StatusCommentTests(unittest.TestCase):
    def test_execution_context_and_status_comment_distinguish_dry_run_from_live(self):
        dry = build_execution_context(True, {
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_WORKFLOW": "QFR Actions queue guardian",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "abcdef0123456789",
        })
        live = build_execution_context(False, {
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_RUN_ID": "12346",
            "GITHUB_SHA": "fedcba9876543210",
        })

        self.assertEqual(dry["mode"], "DRY_RUN")
        self.assertTrue(dry["dry_run"])
        self.assertEqual(dry["run_id"], "12345")
        self.assertEqual(live["mode"], "LIVE_ENFORCEMENT")
        self.assertFalse(live["dry_run"])
        self.assertEqual(live["event_name"], "schedule")

        body = format_status_comment({
            "run_inventory": [],
            "run_inventory_total": 0,
            "execution_context": dry,
        })
        self.assertIn("event: issue_comment", body)
        self.assertIn("mode: **DRY_RUN**", body)
        self.assertIn("commit: abcdef01", body)

    def test_status_comment_upsert_is_idempotent_and_only_updates_bot_comment(self):
        api = GitHubAPI("example/repo", "token")
        comments = [{
            "id": 1,
            "body": STATUS_MARKER + "\nuser-authored marker",
            "user": {"login": "someone-else"},
        }]

        def fake_request(method, path, body=None):
            if method == "GET":
                return 200, list(comments)
            if method == "POST":
                comment = {
                    "id": max(item["id"] for item in comments) + 1,
                    "body": body["body"],
                    "user": {"login": "github-actions[bot]"},
                }
                comments.append(comment)
                return 201, comment
            if method == "PATCH":
                comment_id = int(path.rsplit("/", 1)[1])
                comment = next(item for item in comments if item["id"] == comment_id)
                comment["body"] = body["body"]
                return 200, comment
            raise AssertionError(f"Unexpected request: {method} {path}")

        api.request = fake_request
        first_body = STATUS_MARKER + "\n## QFR workflow status\nPASS"
        created = api.upsert_status_comment(first_body)
        unchanged = api.upsert_status_comment(first_body)
        updated = api.upsert_status_comment(first_body + "\nUpdated")

        self.assertEqual(created["state"], "created")
        self.assertEqual(unchanged["state"], "unchanged")
        self.assertEqual(updated["state"], "updated")
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]["user"]["login"], "someone-else")
        self.assertEqual(comments[1]["body"], first_body + "\nUpdated")


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


    def test_cancellation_api_error_still_creates_orphan_issue(self):
        item = make_run(24, "research-tests", "queued", NOW - timedelta(minutes=25))
        api = FakeAPI([item], cancel_error=RuntimeError("HTTP 403 cancellation forbidden"))
        report = process_queue(api, NOW)
        self.assertEqual(report["actions"][0]["result"],
                         "CANCELLATION_BLOCKED_OR_UNCONFIRMED")
        self.assertIn("CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION",
                      api.issues[0]["body"])
        self.assertIn("HTTP 403", api.issues[0]["body"])

    def test_existing_incident_prevents_repeat_cancellation_attempt(self):
        item = make_run(25, "research-tests", "queued", NOW - timedelta(minutes=25))
        api = FakeAPI([item], cancel_state={"status": "queued", "conclusion": None})
        # First pass records the blocked cancellation incident.
        process_queue(api, NOW)
        self.assertEqual(api.cancelled, [25])
        # An unchanged orphaned run is not cancelled repeatedly on later scans.
        report = process_queue(api, NOW + timedelta(minutes=5))
        self.assertEqual(api.cancelled, [25])
        self.assertEqual(report["actions"][0]["result"],
                         "EXISTING_INCIDENT_NO_REPEAT_CANCELLATION")

    def test_report_exposes_research_run_inventory_and_status_comment(self):
        test_run = make_run(31, "research-tests", "in_progress", NOW - timedelta(minutes=2))
        research_run = make_run(30, "eth-btc-research", "completed", NOW - timedelta(minutes=4))
        research_run["conclusion"] = "failure"
        unrelated = make_run(29, "unmapped-workflow", "completed", NOW - timedelta(minutes=5))
        api = FakeAPI([research_run, unrelated, test_run])

        report = process_queue(api, NOW, dry_run=True)
        body = format_status_comment(report)

        self.assertTrue(report["run_enumeration_complete"])
        self.assertEqual(report["enumerated_runs"], 3)
        self.assertEqual(report["run_inventory_total"], 2)
        self.assertEqual([item["run_id"] for item in report["run_inventory"]], [31, 30])
        self.assertIn("Active runs", body)
        self.assertIn("[31]", body)
        self.assertIn("Research pipeline tests", body)
        self.assertIn("failure", body)

    def test_dry_run_never_cancels_or_creates_issue(self):
        item = make_run(23, "research-tests", "queued", NOW - timedelta(minutes=25))
        api = FakeAPI([item])
        report = process_queue(api, NOW, dry_run=True)
        self.assertEqual(api.cancelled, [])
        self.assertEqual(report["actions"][0]["result"], "DRY_RUN_WOULD_CANCEL")
        self.assertEqual(api.issues, [])


if __name__ == "__main__":
    unittest.main()
