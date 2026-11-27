# ChatGPT-to-GitHub Actions control-PR dispatch bridge

**Status: operational and end-to-end verified on 2026-11-27.**

This bridge removes the need for the connected ChatGPT agent to expose a direct workflow-dispatch action. The agent creates an exact command comment on a dedicated, open draft PR. A workflow on the default branch validates the event and calls GitHub's workflow-dispatch API with the repository's short-lived `GITHUB_TOKEN`.

## Control surface

- Dedicated draft control PR: [#15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/15).
- Keep PR #15 open and in draft. Do not merge it; it is a command surface only.
- Connected comment actor: `takenthatusernameis-collab`.
- Listener: `.github/workflows/chatgpt-control-pr-dispatch.yml` on `main`.
- Probe target: `.github/workflows/dispatch-bridge-probe.yml`.
- Current research target: `.github/workflows/initial-claims-btc-downside.yml`.

The old control PR #2 is superseded and must not be reused.

## Exact allowlisted commands

| Full comment body | Fixed target |
|---|---|
| `/qfr-probe-dispatch-bridge` | `dispatch-bridge-probe.yml` |
| `/qfr-run-initial-claims-btc-downside` | `initial-claims-btc-downside.yml` |

No arbitrary workflow name, ref, shell text, parameter or free-form input is accepted. Adding another target requires an explicit allowlist update, a target workflow with provenance inputs, and regression tests.

## Authorization and security boundary

The listener runs only for `issue_comment: created` and its job requires all of:

- exact control PR number `15`;
- `github.event.issue.pull_request != null`;
- exact verified actor `takenthatusernameis-collab`;
- exact full comment body matching one of the two commands.

The job has only `actions: write` and `pull-requests: write`. It maps each exact command to a hard-coded workflow filename, then calls the workflow-dispatch REST endpoint with `ref: main`. It passes `source_comment_id`, `source_control_pr` and `source_actor` to the target.

The bridge does not checkout code, use `pull_request_target`, inspect the PR head, interpolate comment text into shell source, or execute PR-supplied content. The listener itself is loaded from the default branch. The probe target has no token permissions and performs no checkout or writes. The research target retains its existing atomic-admission and deterministic-test gates.

## Replay protection

A PR-level concurrency group serializes comment processing. After GitHub accepts the target workflow dispatch, the bridge adds a `rocket` reaction to the exact source comment. A redelivery of the same comment checks for the `github-actions[bot]` reaction and exits without dispatching again.

A new comment has a new comment ID and is a new authorization. Before retrying an ambiguous command, inspect the comment reaction, bridge run and target run. Do not post a second research command while the first is queued or in progress.

## Verified operation

- Final admission/dispatch regression CI: [#46067137673](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46067137673), success; 56 tests passed, followed by all configured research regression suites. Earlier CI #46066618302 passed the initial 54-test version.
- First harmless probe target: [#46066554372](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066554372), success. Its bridge run [#46066546997](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066546997) failed after dispatch because the PR-comment reaction endpoint returned HTTP 403. The probe itself had already dispatched successfully.
- Permission repair: added `pull-requests: write` and explicit HTTP response capture for the reaction request.
- Second harmless probe: comment `7227938046`; bridge [#46066680693](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066680693), success; target [#46066689151](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066689151), success; idempotency reaction persisted.
- Real research dispatch: comment `7227943059`; bridge [#46066716510](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066716510), success; target [#46066725930](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066725930), success.
- Target provenance log confirmed source comment `7227943059`, PR `15`, actor `takenthatusernameis-collab`, `GITHUB_REF=refs/heads/main`, and source SHA `a1a0303e760ad89dd76529740199dff6aa720d1c`.

## Normal operating procedure

1. Inspect current Actions runs and ensure the target workflow is not already queued or running.
2. Confirm PR #15 is still open and in draft and the bridge listener is active on `main`.
3. Post only the exact allowlisted command required for the authorized task.
4. Verify the bridge run's event, actor, PR gate, command, target workflow ID, API response and rocket reaction.
5. Verify the target run's `workflow_dispatch` event, `github-actions[bot]` actor, default-branch ref, exact source SHA and provenance inputs.
6. Inspect logs, report, manifest, forecast rows and final research disposition. Persist the evidence and next task.

Direct `workflow_dispatch` may remain as an owner-controlled break-glass mechanism. It is not the normal agent path. If the bridge fails, diagnose and repair the actual cause or implement another materially different authorized mechanism. Do not repeatedly direct the human to the Actions UI.

## Official GitHub semantics

- [`issue_comment` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment): the listener must exist on the default branch; it runs from the default branch and does not execute the control PR head.
- [Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): the bridge uses the workflow-dispatch API with the repository's Actions write permission.
- [GITHUB_TOKEN event behavior](https://docs.github.com/en/actions/concepts/security/github_token): `workflow_dispatch` is an allowed event for triggering another workflow with `GITHUB_TOKEN`.
