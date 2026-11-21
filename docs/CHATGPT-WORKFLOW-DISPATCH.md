# Adaptive ChatGPT-to-GitHub Actions Dispatch

**Current status:** Autonomous ChatGPT dispatch is **NOT ENABLED / NOT END-TO-END VERIFIED**. The objective is to remove this bottleneck through an adaptive, secure implementation—not to make a human UI dispatch the normal operating process.

This guide is subordinate to and implements the repository-wide [Adaptive Autonomous Research Execution Standard](ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md).

## Objective

A ChatGPT-connected agent must be able to start the required on-demand research workflow, verify that the intended run actually began, inspect its logs, retrieve its artifacts, and continue the research task without routine human UI intervention.

Do not assume that one particular GitHub event or connector action must be used. Inspect the actual capabilities available in the current session, select the strongest viable route, and change route when evidence shows that the current one is unsupported.

## Step 1 — Diagnose the actual integration

At the start of an implementation attempt:

1. Inspect the current connected GitHub tool catalog and read the exact schemas for issue comments, pull-request comments, workflow dispatch, repository dispatch, issue creation, run enumeration, job logs, and artifacts.
2. Inspect existing workflows and current run status. Record each relevant workflow's trigger, permissions, inputs, current branch/ref, and concurrency behavior.
3. Use a harmless test to establish the exact GitHub actor/login used by the connected ChatGPT integration. Never infer the actor from an app display name.
4. Distinguish ordinary-issue commenting from PR-conversation commenting. A tool that accepts a `pr_number` is not proof that it can comment on an ordinary issue.
5. Verify required permission scopes and whether the connected action can actually perform the needed write operation.

**Observed integration limitation during the 2026-11-21 inspection:** the available `add_comment_to_issue` action was described as creating a top-level PR Conversation comment and accepted `pr_number`; the connected tool catalog exposed no direct workflow-dispatch POST action and no clearly supported ordinary-issue-comment creation action. Revalidate this in each future session because connected capabilities can change.

## Step 2 — Select an autonomous dispatch route

Evaluate the following routes in order of actual viability, not as a fixed hierarchy. A later route may be superior when it is the only route the connected integration can securely invoke.

### Route A: direct workflow dispatch

Use the GitHub REST endpoint `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` when an authorized connected action or integration exposes it with repository **Actions: write** permission.

Use typed, validated workflow inputs. Verify the run's workflow path, event, actor, ref, commit, inputs, logs, and artifacts. A tool's read-only support for Actions does not imply dispatch permission.

### Route B: ordinary-issue comment bridge

Use a dedicated ordinary control issue if the connected ChatGPT integration can create comments on ordinary issues.

- The workflow subscribes to `issue_comment` with activity type `created`.
- The job requires the exact control issue number, an ordinary issue (no `pull_request` field), exact verified actor login, and full exact command-body equality.
- Each on-demand workflow receives a distinct command.
- Use fixed, reviewed inputs or allowlisted parameter profiles; do not parse free-form comment text into shell commands.

GitHub only triggers an `issue_comment` workflow if the workflow file exists on the default branch. The event runs using the last commit on the default branch and sets `GITHUB_REF` to that branch. See the [official event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

### Route C: PR-comment bridge when ordinary-issue comments are unsupported

If the real connected action supports PR conversation comments but cannot create ordinary-issue comments, **do not stop at that limitation**. Evaluate a dedicated control PR as an alternative event surface.

- Create or designate one stable control PR and record its exact number.
- Use the connected PR-comment action to post a harmless test command.
- Subscribe to `issue_comment: created` and gate the run on the exact control PR number, `github.event.issue.pull_request != null`, exact verified actor login, and exact full command body.
- Run only workflow code from the repository's default branch. GitHub's `issue_comment` event uses the last commit on the default branch; explicitly avoid any checkout or execution of the control PR head.
- Never use `pull_request_target` as a shortcut, never checkout PR-supplied refs, and never interpret PR title/body/comment content as code or shell input.
- Test that comments on all other issues and PRs are rejected and that the control PR cannot modify the executed workflow revision.

A PR control surface is a deliberate, narrowly scoped contingency for a connector that only exposes PR comments. It is not permission to execute untrusted PR code. If its security cannot be demonstrated, reject this route and move to Route D.

### Route D: GitHub App or authenticated dispatch relay

If the current connector cannot send the required event, investigate a repository-scoped GitHub App or an already-authorized secure relay.

Possible implementations:
- An installation token invoking workflow dispatch with **Actions: write**.
- An installation token creating a control comment with **Issues: write** or **Pull requests: write**.
- A `repository_dispatch` event with a unique event type and validated payload; GitHub documents **Contents: write** for fine-grained tokens for this endpoint.
- A narrowly scoped API broker or worker that authenticates the caller, accepts only allowlisted workflow identifiers/commands and validated parameter profiles, then calls the GitHub API.

Prefer short-lived GitHub App installation tokens and minimum repository permissions. Store private keys and tokens only in GitHub Actions secrets or an appropriate secret manager. Do not put credentials in commits, logs, issue text, workflow inputs, or this document. Do not ask for a broad token when a narrower app permission is sufficient.

If the app installation, permission grant, or secret creation is an owner-only prerequisite, finish the implementation and tests that do not need that secret, then identify the exact smallest prerequisite once. Continue other independent research work rather than making the entire research cycle depend on the human performing a routine dispatch.

### Route E: bounded polling only as a last resort

Consider a poller only after direct API dispatch, issue/PR comment events, and a secure authenticated relay have been evaluated and shown infeasible.

Any poller must have a justified interval, low API/compute cost, strict identity/command validation, idempotency, deduplication, concurrency controls, rate-limit monitoring, and a clear stop condition. Do not add recurring full-data jobs or continuous polling just to avoid diagnosing the actual blocker.

## Step 3 — Implement the selected route securely

Every agent-invoked on-demand workflow must have a working autonomous activation method. Do not require every workflow to use the same GitHub event: implement the route proven viable by the integration and document its exact command/payload, actor, permissions, workflow path, inputs, expected artifacts, and verification procedure.

For an `issue_comment` route, the workflow trigger generally has this shape:

```yaml
on:
  issue_comment:
    types: [created]
  workflow_dispatch: # optional break-glass owner recovery, not the agent's normal path
```

For an ordinary-issue control surface, the job gate must enforce all of:

```yaml
github.event_name == 'issue_comment' &&
github.event.action == 'created' &&
github.event.issue.number == <CONTROL_ISSUE_NUMBER> &&
github.event.issue.pull_request == null &&
github.event.comment.user.login == '<VERIFIED_ACTOR_LOGIN>' &&
github.event.comment.body == '/exact-unique-command'
```

For a control-PR surface, use the PR's exact number and require `github.event.issue.pull_request != null`; keep all other checks equally strict. The workflow must execute from the default branch and must not checkout or run control-PR code.

For direct dispatch or `repository_dispatch`, validate the workflow ID, ref, event type, payload schema, actor, and every parameter at the workflow boundary. Treat every external input as untrusted. Do not interpolate free-form inputs into shell source.

Set minimal job permissions. Use concurrency groups or another idempotency/locking mechanism so duplicate comments, retries, or parallel agents cannot launch overlapping expensive full-data runs. Keep the event trigger on the default branch and do not introduce broad `push` triggers or arbitrary recurring schedules.

## Step 4 — Prove end-to-end activation

A route is not enabled because a workflow file exists, a control issue/PR exists, an app has been installed, or a comment API returns success.

Use a harmless deterministic test and verify all of the following:

- [ ] The real ChatGPT-connected integration can invoke the selected write action.
- [ ] The exact GitHub actor/login is observed from the resulting comment or event.
- [ ] The control issue/PR or authenticated relay is identified and its exact target is configured.
- [ ] Only the exact authorized target, actor, event, and complete command/payload pass the gate.
- [ ] ChatGPT itself initiates the test; a human-launched UI run does not satisfy this criterion.
- [ ] GitHub records the intended workflow path, event, actor, ref, and commit SHA.
- [ ] Job logs prove the security gate passed and the harmless task completed.
- [ ] ChatGPT retrieves the output/artifact and verifies its expected content/hash.
- [ ] Duplicate/replayed commands do not start duplicate expensive work.
- [ ] Every on-demand workflow the agent is expected to start has a documented, tested autonomous route.

Until these are demonstrated, state exactly which requirement is still unverified and continue with the next viable contingency. Do not overstate activation.

## Operational behavior once enabled

1. Inspect the control surface and enumerate current Actions runs.
2. Check that no conflicting or duplicate expensive run is queued/in progress.
3. Validate the requested workflow, inputs, and research scope against the current pending task.
4. Send the exact approved command or authenticated dispatch payload.
5. Find the new run and verify workflow, event, actor, ref, SHA, and inputs.
6. Inspect jobs, logs, artifacts, manifests, hashes, and research outputs.
7. Record the execution and improve the persistent handoff.

The `workflow_dispatch` event may remain available as a human-owned break-glass recovery control where appropriate. It is not the routine agent procedure, does not satisfy autonomous acceptance, and should not be repeatedly presented as the answer to an unresolved automation blocker.

## Repository-specific state

- Current empirical workflow: `.github/workflows/eth-btc-research.yml`.
- Its current trigger is `workflow_dispatch` only.
- The repository has no verified autonomous ChatGPT dispatch route yet.
- The next agent should first test the connected PR-comment capability, because the currently observed integration exposes a PR-comment action but not a clearly supported ordinary-issue-comment action or direct workflow-dispatch POST.
- If the PR-comment route is viable, implement and prove the tightly gated control-PR path. Otherwise proceed to an authenticated GitHub App/API relay or the next secure alternative. Do not simply tell the human to click Run workflow.
- The research data-quality gate remains independent: an automated trigger must not rerun or bypass the ETH/BTC study until the pending data-gap reconciliation task validates the required inputs.

## Official references

- [Workflow events: issue_comment, workflow_dispatch, repository_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Create an issue comment: Issues or Pull requests write permission](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment)
- [Create a workflow dispatch event: Actions write permission](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [Create a repository dispatch event: Contents write permission](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GITHUB_TOKEN event suppression and dispatch exceptions](https://docs.github.com/en/actions/concepts/security/github_token)


## Verified repository-specific dispatch route — 2026-11-21

**Status: the PR-comment route is now end-to-end verified for a harmless smoke command.** The connected GitHub integration's authenticated login was read directly as `takenthatusernameis-collab`. A dedicated draft control PR is open at [PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2). Do not merge or close this PR; it is the stable control surface.

The default-branch workflow `.github/workflows/eth-btc-research.yml` now accepts `issue_comment: created` and authorizes only when all conditions match:

- PR number is exactly `2`, the comment target is a pull request, and the PR state is open;
- authenticated comment author is exactly `takenthatusernameis-collab`;
- comment body equals the entire allowlisted command, with no extra text:
  - `/qfr-control-smoke` — harmless smoke test;
  - `/qfr-run-eth-btc-data-audit` — audit all four price series and both funding histories, and reconcile missing ETH Spot hours against Binance REST and daily archives.

The workflow uses repository-level `contents: read` permissions only. The issue-comment event executes the workflow from `main`; the research job explicitly checks out `github.event.repository.default_branch`. It never checks out, imports, executes, or trusts the control PR head or its contents. No `pull_request_target` trigger is used. The smoke job performs no checkout and no data access.

### Verification evidence

- Control PR: [#2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2), created as a draft and left open.
- Smoke comment ID: `7071125644`.
- Smoke workflow run: [44963633770](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963633770), run number 3, event `issue_comment`, actor `takenthatusernameis-collab`, ref `main`, commit `96b93aeba313d9a083bb031a949955cb8e606509`, conclusion **success**.
- The authorization logs confirm exact target PR #2, open PR state, exact actor, `issue_comment` created event, and whole-body command equality. The audit job was skipped for the smoke command as intended.
- Audit comment ID: `7071128780`. The corresponding data-audit workflow run is [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383). At the time of this documentation update, authorization, checkout of `main`, dependency installation and the synthetic smoke test have passed; the real data audit is still running. Its result must be recorded before claiming the underlying research task complete.

### Operating procedure

1. Confirm the control PR remains open and the workflow file on `main` still contains the expected PR number and verified actor.
2. Confirm no conflicting full-data/audit run is queued or in progress (workflow concurrency group serializes this workflow).
3. Use the connected PR-comment action to post one exact command to PR #2.
4. Verify the new run's event, actor, `main` ref, SHA, authorization job outputs/logs, research job logs, and uploaded artifact.
5. Never treat a successful trigger or smoke test as a successful data audit or empirical finding. Keep the research status **INCONCLUSIVE** until all input manifests and reconciliation evidence pass the declared acceptance rules.

The manual `workflow_dispatch` route remains a break-glass owner control. The comment route's `/qfr-run-eth-btc-data-audit` command always invokes `--audit-only --reconcile-spot-gaps`; it cannot launch a strategy backtest. Full empirical execution remains a separate manual owner action and is still gated by data completeness.
