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
}
QUEUE_STATUSES = {"queued", "pending"}


def parse_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def workflow_path(run: dict[str, Any]) -> str:
    return str(run.get("path") or "").split("@", 1)[0]


def group_for(run: dict[str, Any]) -> str | None:
    return WORKFLOW_GROUPS.get(workflow_path(run))


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


def process_queue(api: GitHubAPI, now: datetime, dry_run: bool = False) -> dict[str, Any]:
    runs = api.list_all_runs()
    report: dict[str, Any] = {"checked_at": now.astimezone(timezone.utc).isoformat(),
                              "enumerated_runs": len(runs), "actions": [], "errors": []}
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
        report = process_queue(api, datetime.now(timezone.utc),
                               dry_run=os.environ.get("DRY_RUN", "false").lower() == "true")
        write_report(report)
    except Exception as exc:
        print(f"Queue guardian failed closed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
