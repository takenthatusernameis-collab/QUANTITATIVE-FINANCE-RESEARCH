# ChatGPT-Initiated GitHub Actions Dispatch

**Status: recommended bridge documented; not yet enabled or end-to-end tested.**

## Decision

## Repository-wide rule for newly created workflows

The indirect activation pattern is a **repository-wide default for every newly created workflow that a ChatGPT-connected agent is expected to start on demand**—not just the ETH/BTC empirical workflow and not just workflows created after network-permission failures.

This includes workflows created for network access, dependency/runtime limitations, data collection, diagnostics, validation, report generation, artifact processing, or other explicitly delegated tasks.

For each such workflow:

1. Keep `workflow_dispatch` with well-defined inputs as the owner/manual fallback.
2. Also subscribe to `issue_comment` with activity type `created`, unless a direct ChatGPT-to-GitHub workflow-dispatch action with the necessary Actions: write permission has been verified end-to-end. Even when direct dispatch is available, retaining the issue-comment route is a useful fallback where practical.
3. Assign that workflow one unique, documented command (for example, `/run-network-diagnostic` or `/run-data-validation`). Do not reuse one command across workflows.
4. Route commands through the repository's dedicated ordinary control issue. Use the same control issue and exact approved account, but give each workflow its own command and strict job-level gate.
5. Make the job run only for either the explicit `workflow_dispatch` event or an `issue_comment: created` event matching **all** of: the exact control issue number, non-PR issue, exact allowlisted author login, and the entire exact command body.
6. Give issue-comment invocations fixed, reviewed defaults or strictly allowlisted parameter profiles. Never turn arbitrary comment text into shell input or workflow code.
7. Record the workflow path, command, purpose, required permissions, expected artifacts, and manual fallback in the workflow file's comments or its task/documentation entry.

This requirement applies to **on-demand agent-executed workflows**. Ordinary CI workflows that are intentionally started by `push`, `pull_request`, or other native events do not need an issue-comment command unless ChatGPT must also be able to start them independently. Do not add issue-comment triggers indiscriminately to every CI workflow.

Do not leave a newly created agent-invoked workflow manual-only merely because it was created for a one-off network or environment workaround. Implement its gated indirect trigger in the same change whenever feasible. If activation cannot be completed (for example, the control issue or approved account identity is not yet verified), document the exact missing prerequisite, keep the workflow's manual fallback, and mark indirect activation **NOT ENABLED**—never imply it is callable by ChatGPT yet.

### Reusable workflow trigger shape

A new agent-invoked workflow should generally have both event declarations:

```yaml
on:
  workflow_dispatch:
    # Declare typed, validated manual inputs for maintainers.
  issue_comment:
    types: [created]
```

Its job-level condition must use that workflow's own unique command. Adapt this illustrative gate with the actual control issue number, approved login, and unique command before enabling it:

```yaml
jobs:
  task:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (
        github.event_name == 'issue_comment' &&
        github.event.action == 'created' &&
        github.event.issue.number == <CONTROL_ISSUE_NUMBER> &&
        github.event.issue.pull_request == null &&
        github.event.comment.user.login == '<APPROVED_GITHUB_LOGIN>' &&
        github.event.comment.body == '/run-unique-workflow-command'
      )
```

A trigger declaration alone is not a security gate. Validate all conditions at the job (or a mandatory first gate job that every privileged job depends on) so an unrelated issue comment cannot run the task.

There are two ways to remove the owner-side **Actions → Run workflow** click:

1. **Preferred when available: direct workflow dispatch.** The GitHub REST endpoint `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` starts a workflow configured with `workflow_dispatch`. The caller needs repository **Actions: write** permission. The currently connected ChatGPT/GitHub toolset can inspect and comment on repository threads, but it does not expose this workflow-dispatch POST action.
2. **Available indirect bridge: a dedicated issue-comment command.** ChatGPT can post a comment to a dedicated control issue through the GitHub issue-comment API (provided the connection has **Issues: write** permission and the action supports ordinary issues). GitHub emits `issue_comment` with activity type `created`; a workflow that subscribes to that event can run the research job. This does not call the `workflow_dispatch` API; it uses a separate event trigger.

GitHub documents `issue_comment` as an event for newly created comments on issues and pull requests. The workflow file must already exist on the repository's default branch. The current repository's empirical workflow is `workflow_dispatch`-only, so the bridge is **not active yet**. Do not describe the manual step as removed until the bridge has been implemented and an end-to-end test run has been observed.

## Network-permission escalation: use Actions after repeated denials

This repository should not spend repeated agent turns retrying an operation that the current ChatGPT/tool environment is explicitly forbidden to perform over the network.

- For an ordinary transient timeout or rate limit, use a bounded retry/backoff and inspect whether the failure is transient.
- If the same explicit network-permission denial occurs on **two independent attempts**, stop retrying that same blocked operation and move the network-dependent step to a GitHub Actions hosted runner with the required network access.
- Reuse the existing `.github/workflows/eth-btc-research.yml` for the pre-registered ETH/BTC empirical run. For a different task, use or create a narrowly scoped workflow that checks out the required revision, installs pinned dependencies, performs the actual network-dependent operation, emits diagnostic logs, and uploads useful results/manifests as artifacts.
- Do not create an empty workflow, add a broad push trigger, or schedule repeated full-data jobs as a workaround. Use the direct `workflow_dispatch` API when the connected agent has Actions: write; otherwise use the maintainer-only issue-comment bridge in this document once it has been configured and end-to-end tested. Until then, state the manual dispatch step precisely.
- Record the blocked operation, exact permission error, attempt count, workflow path, run ID, commit SHA, and resulting logs/artifacts. A successful trigger or successful synthetic test is not proof that the required empirical/network operation succeeded.
- Keep credentials in GitHub Actions secrets and avoid printing them. If the hosted runner also receives a network denial, inspect and report that actual failure; do not loop indefinitely or infer a research result.

The purpose of this escalation rule is to distinguish **agent-environment network permissions** from **research/data limitations**. A permission failure is not a market-data result and must not silently terminate otherwise feasible empirical work.

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

## Mandatory acceptance criteria: end-to-end autonomous activation

The implementation is **not complete** until every item below has been demonstrated with a real test. Documentation, workflow YAML, installed permissions, or a successful comment-creation response alone do not satisfy acceptance.

- [ ] **Dedicated control issue created:** one ordinary GitHub issue exists, its number is recorded in the shared workflow configuration/documentation, and it is clearly identified as the command interface. It must not be a pull request.
- [ ] **Actual ChatGPT comment identity established:** create a harmless test comment through the connected ChatGPT GitHub integration and record the exact GitHub actor/login shown by GitHub. Do not guess the identity from the App installation name.
- [ ] **Ordinary-issue commenting capability verified:** prove that the connected ChatGPT action can create a comment on the dedicated ordinary issue, not merely on a pull request. If its exposed action cannot do this, identify and implement a supported alternative; do not claim the bridge is usable.
- [ ] **Harmless test workflow implemented:** create a minimal, low-cost workflow with both manual `workflow_dispatch` fallback and a strictly gated `issue_comment: created` command. It should perform a harmless deterministic action and produce an inspectable output/artifact. Test the exact control-issue, non-PR, approved-author and full-command checks.
- [ ] **ChatGPT successfully triggers the test workflow:** ChatGPT itself posts the exact command through the connected integration; GitHub records the expected `issue_comment` event and starts the intended workflow. A manual Run workflow click does not satisfy this criterion.
- [ ] **Actions logs confirm successful execution:** inspect the resulting run and job logs; verify the event type, workflow path, actor, commit SHA, command gate and successful completion. Record the run URL/ID.
- [ ] **ChatGPT retrieves and verifies the output:** use the connected GitHub integration to inspect the run's artifacts or other output, and confirm that the content matches the test workflow's expected result.
- [ ] **Repository-wide workflow coverage:** apply the same verified activation pattern to every on-demand workflow that ChatGPT is expected to start—existing and future—with a distinct exact command per workflow, while retaining manual `workflow_dispatch` fallback. Native-event CI workflows are exempt unless ChatGPT also needs to start them independently.

**Completion status:** Until all criteria are met, report the activation system as **NOT ENABLED / NOT END-TO-END VERIFIED**. List any failed or unavailable prerequisite explicitly and retain the manual fallback. Do not represent a documented design or partial test as autonomous execution.

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
