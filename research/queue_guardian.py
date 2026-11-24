from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

QUEUE_TIMEOUT_SECONDS = 900
WORKFLOW_GROUPS = {
    ".github/workflows/eth-btc-research.yml": "eth-btc-research-main",
    ".github/workflows/research-tests.yml": "research-tests-main",
    ".github/workflows/eth-btc-cache-warm.yml": "binance-archive-cache-warm",
    ".github/workflows/binance-spot-universe-audit.yml": "binance-spot-universe-audit-main",
}
OBSERVABILITY_WORKFLOWS = {
    ".github/workflows/eth-btc-research.yml": "ETH/BTC research",
    ".github/workflows/research-tests.yml": "Research pipeline tests",
    ".github/workflows/eth-btc-cache-warm.yml": "Trusted Binance archive cache warmer",
    ".github/workflows/binance-spot-universe-audit.yml": "Binance Spot dynamic-universe feasibility audit",
}
STATUS_ISSUE_NUMBER = 2
STATUS_MARKER = "<!-- qfr-queue-status -->"
QUEUE_STATUSES = {"queued", "pending"}


def parse_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def workflow_path(run: dict[str, Any]) -> str:
    return str(run.get("path") or "").split("@", 1)[0]


def group_for(run: dict[str, Any]) -> str | None:
    path = workflow_path(run)
    if path == ".github/workflows/binance-spot-universe-audit.yml":
        actor = run.get("actor") or {}
        head_repository = run.get("head_repository") or {}
        authorized = (
            run.get("display_title") == "Authorized Binance Spot universe audit"
            and run.get("event") == "issue_comment"
            and actor.get("login") == "takenthatusernameis-collab"
            and run.get("head_branch") == "main"
            and head_repository.get("full_name")
            == "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"
        )
        if authorized:
            return "binance-spot-universe-audit-main"
        return f"binance-spot-universe-audit-ignored-{run.get('id', 'unknown')}"
    return WORKFLOW_GROUPS.get(path)


def build_run_inventory(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory = []
    for run in runs:
        path = workflow_path(run)
        if path not in OBSERVABILITY_WORKFLOWS:
            continue
        actor = run.get("actor") or {}
        inventory.append({
            "run_id": int(run["id"]),
            "workflow_path": path,
            "workflow_name": OBSERVABILITY_WORKFLOWS[path],
            "display_title": run.get("display_title"),
            "event": run.get("event"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "created_at": run["created_at"],
            "updated_at": run.get("updated_at"),
            "head_sha": run.get("head_sha"),
            "actor": actor.get("login"),
            "html_url": run.get("html_url"),
        })
    inventory.sort(key=lambda item: parse_timestamp(item["created_at"]), reverse=True)
    return inventory


def format_status_comment(report: dict[str, Any]) -> str:
    runs = report.get("run_inventory") or []
    active = [
        run for run in runs
        if run.get("status") in {"queued", "pending", "in_progress", "waiting", "requested"}
    ]
    lines = [
        STATUS_MARKER,
        "## QFR workflow status",
        (
            f"Research/test runs captured: {report.get('run_inventory_total', len(runs))}; "
            f"latest {len(runs)} retained in the machine-readable guardian report."
        ),
    ]
    context = report.get("execution_context") or {}
    if context:
        run_id = context.get("run_id") or "unavailable"
        event_name = context.get("event_name") or "unknown"
        mode = context.get("mode") or ("DRY_RUN" if context.get("dry_run") else "LIVE_ENFORCEMENT")
        sha = str(context.get("sha") or "")[:8] or "unavailable"
        lines.extend([
            "",
            "### Guardian execution",
            f"- Run: {run_id}; event: {event_name}; mode: **{mode}**; commit: {sha}",
        ])
    if report.get("run_inventory_truncated"):
        lines.append("The displayed inventory is truncated to the latest retained runs.")
    lines.extend(["", "### Active runs"])
    if active:
        for run in active[:20]:
            url = run.get("html_url") or "#"
            sha = str(run.get("head_sha") or "")[:8]
            lines.append(
                f"- [{run['run_id']}]({url}) — **{run.get('workflow_name')}** "
                f"status={run.get('status')}; event={run.get('event')}; "
                f"actor={run.get('actor')}; commit={sha}"
            )
    else:
        lines.append("- No active research/test workflow runs.")
    for path, label in OBSERVABILITY_WORKFLOWS.items():
        subset = [run for run in runs if run.get("workflow_path") == path]
        lines.extend(["", f"### {label}"])
        if not subset:
            lines.append("- No runs captured.")
            continue
        for run in subset[:4]:
            outcome = str(run.get("status") or "unknown")
            if run.get("conclusion"):
                outcome += f" / {run['conclusion']}"
            url = run.get("html_url") or "#"
            sha = str(run.get("head_sha") or "")[:8]
            lines.append(
                f"- [{run['run_id']}]({url}) — {outcome}; event={run.get('event')}; "
                f"actor={run.get('actor')}; commit={sha}"
            )
    actions = report.get("actions") or []
    if actions:
        lines.extend(["", "### Queue decisions"])
        for action in actions[:10]:
            lines.append(
                f"- Run {action.get('run_id')}: "
                f"{action.get('result', action.get('action'))}"
            )
    errors = report.get("errors") or []
    if errors:
        lines.extend(["", "### Guardian errors"])
        for error in errors[:10]:
            lines.append(f"- Run {error.get('run_id')}: {error.get('error')}")
    return "\n".join(lines)


def age_seconds(run: dict[str, Any], now: datetime) -> float:
    return (now.astimezone(timezone.utc) - parse_timestamp(run["created_at"])).total_seconds()


def active_predecessor(run: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    group = group_for(run)
    if group is None:
        return None
    created = parse_timestamp(run["created_at"])
    candidates = [
        other for other in runs
        if other.get("id") != run.get("id")
        and group_for(other) == group
        and other.get("status") == "in_progress"
        and parse_timestamp(other["created_at"]) < created
    ]
    return min(candidates, key=lambda item: parse_timestamp(item["created_at"])) if candidates else None


def queue_decision(run: dict[str, Any], runs: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    group = group_for(run)
    age = age_seconds(run, now)
    if group is None:
        return {"action": "ignore_unmapped_workflow", "age_seconds": age}
    if run.get("status") not in QUEUE_STATUSES:
        return {"action": "ignore_not_run_level_queued", "age_seconds": age, "group": group}
    if age <= QUEUE_TIMEOUT_SECONDS:
        return {"action": "wait_under_threshold", "age_seconds": age, "group": group}
    predecessor = active_predecessor(run, runs)
    if predecessor:
        return {"action": "preserve_same_group_wait", "age_seconds": age,
                "group": group, "predecessor_run_id": predecessor.get("id")}
    return {"action": "cancel_overdue", "age_seconds": age, "group": group,
            "reason": "QUEUE_TIMEOUT_OVER_15M_NO_ACTIVE_SAME_GROUP_PREDECESSOR"}


class GitHubAPI:
    def __init__(self, repository: str, token: str, api_url: str = "https://api.github.com"):
        self.repository = repository
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        data = json.dumps(body).encode() if body is not None else None
        req = Request(
            self.api_url + path, data=data, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "qfr-queue-guardian",
            },
        )
        try:
            with urlopen(req, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"{method} {path}: transport error: {exc.reason}") from exc

    def list_all_runs(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        page = 1
        total = None
        while True:
            _, payload = self.request(
                "GET", f"/repos/{self.repository}/actions/runs?per_page=100&page={page}"
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
                raise RuntimeError("Invalid workflow-runs response")
            if total is None:
                total = int(payload.get("total_count", 0))
            batch = payload["workflow_runs"]
            result.extend(batch)
            if not batch or len(result) >= total:
                break
            page += 1
        if total is not None and len(result) < total:
            raise RuntimeError(f"Incomplete run enumeration: expected {total}, got {len(result)}")
        return result

    def get_run(self, run_id: int) -> dict[str, Any]:
        _, result = self.request("GET", f"/repos/{self.repository}/actions/runs/{run_id}")
        if not isinstance(result, dict):
            raise RuntimeError(f"Invalid run response for {run_id}")
        return result

    def cancel_run(self, run_id: int) -> None:
        self.request("POST", f"/repos/{self.repository}/actions/runs/{run_id}/cancel")

    def find_incident_issue(self, run_id: int) -> dict[str, Any] | None:
        marker = f"<!-- qfr-queue-run:{run_id} -->"
        page = 1
        while True:
            _, result = self.request(
                "GET", f"/repos/{self.repository}/issues?state=all&per_page=100&page={page}"
            )
            if not isinstance(result, list):
                raise RuntimeError("Invalid issues response")
            for issue in result:
                if "pull_request" not in issue and marker in str(issue.get("body") or ""):
                    return issue
            if len(result) < 100:
                return None
            page += 1

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        _, result = self.request("POST", f"/repos/{self.repository}/issues",
                                 {"title": title, "body": body})
        if not isinstance(result, dict):
            raise RuntimeError("Issue creation returned no issue")
        return result

    def find_status_comment(self) -> dict[str, Any] | None:
        page = 1
        while True:
            _, result = self.request(
                "GET",
                f"/repos/{self.repository}/issues/{STATUS_ISSUE_NUMBER}/comments?per_page=100&page={page}",
            )
            if not isinstance(result, list):
                raise RuntimeError("Invalid control-PR comments response")
            for comment in result:
                author = (comment.get("user") or {}).get("login")
                if author == "github-actions[bot]" and STATUS_MARKER in str(comment.get("body") or ""):
                    return comment
            if len(result) < 100:
                return None
            page += 1

    def upsert_status_comment(self, body: str) -> dict[str, Any]:
        if STATUS_MARKER not in body:
            raise ValueError("Status comment must contain its idempotency marker")
        existing = self.find_status_comment()
        if existing and existing.get("body") == body:
            return {"state": "unchanged", "comment_id": existing.get("id")}
        if existing:
            _, result = self.request(
                "PATCH",
                f"/repos/{self.repository}/issues/comments/{existing['id']}",
                {"body": body},
            )
            if not isinstance(result, dict):
                raise RuntimeError("Status comment update returned no comment")
            return {"state": "updated", "comment_id": result.get("id")}
        _, result = self.request(
            "POST",
            f"/repos/{self.repository}/issues/{STATUS_ISSUE_NUMBER}/comments",
            {"body": body},
        )
        if not isinstance(result, dict):
            raise RuntimeError("Status comment creation returned no comment")
        return {"state": "created", "comment_id": result.get("id")}


def incident_body(run: dict[str, Any], age: float, group: str, state: str,
                  error: str | None = None) -> str:
    run_id = int(run["id"])
    marker = f"<!-- qfr-queue-run:{run_id} -->"
    if state == "CANCELLATION_BLOCKED":
        tag = "CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION"
        next_action = (
            "Cancellation could not be confirmed. Treat this run as potentially able to start later. "
            "Immediately initiate exactly one materially different, independently isolated alternative attempt."
        )
    else:
        tag = "QUEUE_CANCELLED / RETRY_REQUIRED"
        next_action = (
            "The queued run was cancelled. Keep the task open for one controlled retry after verified capacity "
            "recovery or through a materially different authorized execution route. Do not immediately duplicate it."
        )
    snapshot = {
        "run_id": run_id, "run_url": run.get("html_url"), "workflow": run.get("name"),
        "workflow_path": workflow_path(run), "event": run.get("event"),
        "actor": run.get("actor", {}).get("login") if isinstance(run.get("actor"), dict) else None,
        "ref": run.get("head_branch"), "head_sha": run.get("head_sha"),
        "created_at": run.get("created_at"), "last_observed_status": run.get("status"),
        "queue_age_minutes": round(age / 60, 2), "concurrency_group": group,
        "cancellation_error": error,
    }
    return (
        marker + "\n" + "Durable status: " + tag + "\n\n"
        + "Required next action: " + next_action + "\n\n"
        + "Run evidence:\n\n" + json.dumps(snapshot, indent=2) + "\n\n"
        + "Keep any alternative attempt ID, working state, cache, artifacts and output paths separate."
    )


def persist_issue(api: GitHubAPI, run: dict[str, Any], age: float, group: str,
                  state: str, error: str | None = None) -> dict[str, Any]:
    run_id = int(run["id"])
    existing = api.find_incident_issue(run_id)
    if existing:
        return {"issue_number": existing.get("number"), "issue_url": existing.get("html_url"),
                "issue_created": False}
    title_state = "cancellation blocked; alternative required" if state == "CANCELLATION_BLOCKED" else "cancelled; retry required"
    issue = api.create_issue(
        f"[QFR queue guardian] run {run_id}: {title_state}",
        incident_body(run, age, group, state, error),
    )
    return {"issue_number": issue.get("number"), "issue_url": issue.get("html_url"),
            "issue_created": True}


def verify_cancellation(api: GitHubAPI, run_id: int, sleep=time.sleep) -> tuple[bool, dict[str, Any]]:
    latest = api.get_run(run_id)
    for delay in (2, 2, 2):
        if latest.get("status") == "completed":
            return latest.get("conclusion") == "cancelled", latest
        if latest.get("status") == "in_progress":
            return False, latest
        sleep(delay)
        latest = api.get_run(run_id)
    return latest.get("status") == "completed" and latest.get("conclusion") == "cancelled", latest


def build_execution_context(dry_run: bool, env: dict[str, str] | None = None) -> dict[str, Any]:
    source = os.environ if env is None else env
    return {
        "event_name": source.get("GITHUB_EVENT_NAME", "unknown"),
        "run_id": source.get("GITHUB_RUN_ID"),
        "run_attempt": source.get("GITHUB_RUN_ATTEMPT"),
        "workflow": source.get("GITHUB_WORKFLOW"),
        "ref": source.get("GITHUB_REF"),
        "sha": source.get("GITHUB_SHA"),
        "dry_run": bool(dry_run),
        "mode": "DRY_RUN" if dry_run else "LIVE_ENFORCEMENT",
    }


def process_queue(api: GitHubAPI, now: datetime, dry_run: bool = False) -> dict[str, Any]:
    runs = api.list_all_runs()
    inventory = build_run_inventory(runs)
    report: dict[str, Any] = {
        "checked_at": now.astimezone(timezone.utc).isoformat(),
        "enumerated_runs": len(runs),
        "run_enumeration_complete": True,
        "run_inventory_total": len(inventory),
        "run_inventory_truncated": len(inventory) > 50,
        "run_inventory": inventory[:50],
        "actions": [],
        "errors": [],
    }
    ordered = sorted(runs, key=lambda r: parse_timestamp(r["created_at"]))
    for run in ordered:
        decision = queue_decision(run, runs, now)
        if decision["action"] in {"ignore_unmapped_workflow", "ignore_not_run_level_queued",
                                  "wait_under_threshold"}:
            continue
        if decision["action"] == "preserve_same_group_wait":
            report["actions"].append({"run_id": run.get("id"), **decision})
            continue
        run_id = int(run["id"])
        age = float(decision["age_seconds"])
        group = str(decision["group"])
        action: dict[str, Any] = {"run_id": run_id, **decision}
        if dry_run:
            action["result"] = "DRY_RUN_WOULD_CANCEL"
            report["actions"].append(action)
            continue
        try:
            existing_incident = api.find_incident_issue(run_id)
            if existing_incident:
                action["result"] = "EXISTING_INCIDENT_NO_REPEAT_CANCELLATION"
                action["issue_number"] = existing_incident.get("number")
                action["issue_url"] = existing_incident.get("html_url")
                report["actions"].append(action)
                continue
            fresh = api.get_run(run_id)
            fresh_decision = queue_decision(fresh, api.list_all_runs(), now)
            if fresh_decision["action"] == "preserve_same_group_wait":
                action.update(fresh_decision)
                action["result"] = "PRESERVED_NEW_SAME_GROUP_PREDECESSOR"
                report["actions"].append(action)
                continue
            if fresh_decision["action"] != "cancel_overdue":
                action["result"] = "STATE_CHANGED_BEFORE_CANCELLATION"
                action["latest_status"] = fresh.get("status")
                report["actions"].append(action)
                continue
            cancellation_error = None
            try:
                api.cancel_run(run_id)
            except Exception as exc:
                cancellation_error = str(exc)[:1500]

            if cancellation_error is None:
                cancelled, latest = verify_cancellation(api, run_id)
            else:
                # Cancellation failure must still become a durable incident and
                # must trigger the independent-alternative handoff.
                latest = api.get_run(run_id)
                cancelled = False

            action["latest_status"] = latest.get("status")
            action["latest_conclusion"] = latest.get("conclusion")
            if cancelled:
                action["result"] = "CANCELLED_RETRY_REQUIRED"
                incident_state = "CANCELLED"
            elif latest.get("status") == "in_progress":
                action["result"] = "STARTED_DURING_CANCELLATION_RACE"
                report["actions"].append(action)
                continue
            elif latest.get("status") == "completed":
                action["result"] = "COMPLETED_DURING_CANCELLATION_RACE"
                action["latest_conclusion"] = latest.get("conclusion")
                report["actions"].append(action)
                continue
            else:
                action["result"] = "CANCELLATION_BLOCKED_OR_UNCONFIRMED"
                incident_state = "CANCELLATION_BLOCKED"
            action.update(persist_issue(api, fresh, age, group, incident_state,
                                        cancellation_error))
        except Exception as exc:
            action["result"] = "CANCELLATION_OR_RECORDING_ERROR"
            action["error"] = str(exc)[:1500]
            action["durable_issue_recorded"] = False
            report["errors"].append({"run_id": run_id, "error": str(exc)[:1500]})
        report["actions"].append(action)
    return report


def write_report(report: dict[str, Any]) -> None:
    path = os.environ.get("QFR_QUEUE_REPORT", "queue_guardian_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## QFR queue guardian\n\n")
            handle.write(f"Enumerated runs: {report['enumerated_runs']}\n\n")
            for action in report["actions"]:
                handle.write(
                    f"- Run {action.get('run_id')}: {action.get('result', action.get('action'))} "
                    f"(age {action.get('age_seconds', 0) / 60:.1f} min).\n"
                )
            for error in report["errors"]:
                handle.write(f"- Error for run {error['run_id']}: {error['error']}\n")


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        print("GITHUB_REPOSITORY and GITHUB_TOKEN are required", file=sys.stderr)
        return 2
    api = GitHubAPI(repository, token, os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    try:
        dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
        report = process_queue(api, datetime.now(timezone.utc), dry_run=dry_run)
        report["execution_context"] = build_execution_context(dry_run)
        try:
            report["status_comment"] = api.upsert_status_comment(format_status_comment(report))
        except Exception as exc:
            report["status_comment_error"] = str(exc)[:1500]
            print(f"Non-fatal status-comment update failure: {exc}", file=sys.stderr)
        write_report(report)
    except Exception as exc:
        print(f"Queue guardian failed closed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
