# ChatGPT-Initiated GitHub Actions Dispatch

**Status: recommended bridge documented; not yet enabled or end-to-end tested.**

## Decision

There are two ways to remove the owner-side **Actions → Run workflow** click:

1. **Preferred when available: direct workflow dispatch.** The GitHub REST endpoint `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` starts a workflow configured with `workflow_dispatch`. The caller needs repository **Actions: write** permission. The currently connected ChatGPT/GitHub toolset can inspect and comment on repository threads, but it does not expose this workflow-dispatch POST action.
2. **Available indirect bridge: a dedicated issue-comment command.** ChatGPT can post a comment to a dedicated control issue through the GitHub issue-comment API (provided the connection has **Issues: write** permission and the action supports ordinary issues). GitHub emits `issue_comment` with activity type `created`; a workflow that subscribes to that event can run the research job. This does not call the `workflow_dispatch` API; it uses a separate event trigger.

GitHub documents `issue_comment` as an event for newly created comments on issues and pull requests. The workflow file must already exist on the repository's default branch. The current repository's empirical workflow is `workflow_dispatch`-only, so the bridge is **not active yet**. Do not describe the manual step as removed until the bridge has been implemented and an end-to-end test run has been observed.

## Recommended implementation

Keep `.github/workflows/eth-btc-research.yml` as the single empirical workflow and retain its existing `workflow_dispatch` trigger as a manual fallback. Add this event:

```yaml
on:
  workflow_dispatch:
    # Keep the existing inputs unchanged.
  issue_comment:
    types: [created]
```

Create one dedicated, ordinary issue for workflow control. Pin it and document the exact command, for example:

```text
/run-eth-btc-research
```

Record the resulting issue number and the one approved GitHub login in the workflow's job-level gate. Do not use a pull request as the control surface. The research job should execute only when **all** of these conditions hold:

- The event is `workflow_dispatch`, or it is `issue_comment` with activity `created`.
- For a comment event, the issue number exactly matches the dedicated control issue.
- The comment is on an ordinary issue, not a pull request (`github.event.issue.pull_request == null`).
- The comment author's login exactly matches the configured maintainer/approved ChatGPT-connected GitHub identity.
- The entire comment body exactly equals `/run-eth-btc-research` (no substring matches, edited comments, or arbitrary command text).

Example job condition (replace both placeholders with verified values before enabling):

```yaml
jobs:
  empirical-research:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (
        github.event_name == 'issue_comment' &&
        github.event.action == 'created' &&
        github.event.issue.number == <CONTROL_ISSUE_NUMBER> &&
        github.event.issue.pull_request == null &&
        github.event.comment.user.login == '<APPROVED_GITHUB_LOGIN>' &&
        github.event.comment.body == '/run-eth-btc-research'
      )
```

For the comment path, use fixed, reviewed research parameters rather than parsing user-supplied shell text. For the current pre-registered run these are:

- Start: `2020-01-01`
- End: `2026-10-31`
- Market: `both`

Preserve the current `workflow_dispatch` inputs so a maintainer can still select a different validated range or market through GitHub's UI. Set event-aware defaults for the comment route; do not assume `inputs.*` is populated for an `issue_comment` event.

## Security and reliability requirements

- Use an exact allowlisted login and exact control-issue number. Do not authorize all commenters, all collaborators, or all bots by broad association checks alone.
- Verify the identity shown on a test comment made by the actual ChatGPT-connected GitHub account. If the connector comments as an app/bot, add only that exact verified identity after confirming it is controlled by the repository owner.
- Accept only `created` events. Do not trigger on `edited` or `deleted`.
- Reject pull-request comments. Never check out or execute code from a pull-request head in this workflow.
- Keep `permissions: contents: read`; the research job does not need write access to the repository. The comment API caller needs Issues: write (or Pull requests: write for a PR comment endpoint).
- Do not interpolate comment content into a shell command, workflow expression that becomes a shell fragment, or a dynamic `run:` script.
- Check the Actions run list before posting the command. Do not submit another expensive full-data run while one is queued or in progress.
- Keep the manual `workflow_dispatch` path as a recovery option.
- Verify that a comment created through the actual ChatGPT GitHub connection produces a run with event `issue_comment`, the intended workflow path, the expected actor, commit SHA and parameters. A successful comment-creation API response alone is not proof the workflow ran.
- If the comment is created by a workflow using the repository's `GITHUB_TOKEN`, GitHub suppresses most resulting workflow events to prevent recursion (except `workflow_dispatch` and `repository_dispatch`). In that case the comment bridge will not dispatch a run; use a GitHub App user/installation token or PAT not derived from the Actions job's `GITHUB_TOKEN`, or use the direct workflow-dispatch API.
- Do not add a `push` or recurring `schedule` trigger as a workaround. A push trigger can run on unrelated documentation/code changes and may be suppressed when the push is made with `GITHUB_TOKEN`.

## ChatGPT operating procedure once enabled

1. Inspect the dedicated control issue and current Actions runs.
2. Confirm no full empirical run is queued or in progress and confirm the exact defaults still match the pre-registered research plan.
3. Post exactly `/run-eth-btc-research` as a new comment on the dedicated control issue using the connected GitHub issue-comment action.
4. Enumerate Actions runs and verify a new run whose workflow is `.github/workflows/eth-btc-research.yml` and event is `issue_comment`.
5. Record the new run ID and inspect the job, logs and artifacts under the existing post-dispatch artifact-review task. If no run appears, report **UNVERIFIED/BLOCKED** and retain the manual fallback; do not claim success.

## Official GitHub references

- [Events that trigger workflows — `issue_comment`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Create an issue comment — required repository permissions](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment)
- [Create a workflow dispatch event — required Actions permission](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [GITHUB_TOKEN event suppression](https://docs.github.com/en/actions/concepts/security/github_token)
