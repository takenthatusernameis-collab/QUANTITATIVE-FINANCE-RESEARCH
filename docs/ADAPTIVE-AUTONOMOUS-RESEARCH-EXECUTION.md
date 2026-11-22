# Adaptive Autonomous Research Execution Standard

**Status: repository-wide operating standard for every current and future agent.**

## Mission

Maximize the rate at which the repository produces **trustworthy, reproducible quantitative research learning** by continuously removing engineering, tooling, data-access, compute, orchestration, and handoff bottlenecks.

An agent's responsibility is not merely to execute the initially proposed method. It is to reach the research objective through the best secure and evidence-preserving route available, adapt when an assumption fails, and improve the system so the next research cycle is more autonomous and reliable.

**Do not confuse the requested outcome with the first implementation idea.** A blocked route is a reason to diagnose and adapt—not a reason to stop, repeat the same attempt, or make the human perform routine agent work.

## Non-negotiable principles

1. **Outcome over prescribed mechanism.** Preserve the research objective and acceptance criteria while changing tools, APIs, event triggers, execution environments, data sources, orchestration, or implementation details when evidence justifies it.
2. **Autonomy is a design objective.** Prefer agent-initiated, event-driven, observable execution. Human intervention is reserved for genuinely privileged owner decisions (for example, granting an unavailable permission, installing an app, or supplying a secret). Do not turn a human UI click into the normal operating procedure or report it as autonomous completion.
3. **Scientific integrity is not a bottleneck to bypass.** Never weaken data completeness, provenance, causality, holdout independence, transaction-cost treatment, statistical validation, reproducibility, or research stop conditions to make a run pass.
4. **Least privilege and explicit authorization.** Use only authorized accounts, scopes, secrets, repositories, and actions. Do not evade access controls, broaden permissions speculatively, expose credentials, or execute untrusted pull-request code.
5. **Evidence before status claims.** A configured workflow is not a successful run; an accepted comment is not proof of a triggered run; a synthetic test is not empirical evidence; and a missing result is not a negative research finding.
6. **Learn from every failure.** Preserve the exact error, diagnosed cause, attempted route, observed result, and next alternative. Do not force the next agent to rediscover the same limitation.

## Mandatory autonomy: research must not wait for routine human intervention

**Default rule: execute.** Historical backtests, data audits, public-market-data retrieval, parser repairs, provider comparisons, hypothesis tests, synthetic tests, CI, artifact retrieval, reporting, and repository changes within the connected agent's existing authorized scope are ordinary research operations. The agent must perform them without asking the user to click a button, confirm a routine step, approve a known-safe rerun, or manually start a workflow.

A workflow that requires the human to activate routine research is an engineering defect. A conclusion such as "the backtest is ready but I must wait for manual confirmation to launch it" is **FAILURE**, not a completed handoff. Repair the trigger, use the verified agent-controlled event path, or move the execution to another authorized runner. Never present manual UI activation as the recommended next step or leave a research task dormant solely because a routine trigger is missing.

This rule does **not** authorize unsafe access or live financial actions. Pause only the specific unsafe operation for a genuine security/legal/financial-risk boundary, such as:
- suspected credential exposure, compromised identity, or secret exfiltration;
- executing untrusted code or allowing untrusted event data to reach a privileged runner;
- obtaining or using a permission, credential, private dataset, or repository scope that the connected identity is not authorized to access;
- bypassing a legal, contractual, geographic, or provider access restriction (including an HTTP 451 restriction);
- live order placement, capital deployment, custody changes, or strategy promotion that has not been separately authorized.

Do not classify ordinary missing data, an unavailable endpoint, a parser error, dependency setup, runner selection, CI activation, or a failed historical backtest as a security issue. A provider's access restriction must be respected; change to a lawful, authorized source rather than circumventing the restriction. If a genuinely owner-only security grant is indispensable and no authorized alternative exists, isolate that one action, prepare the smallest exact prerequisite once, and continue all independent research and engineering work. Never make the entire research loop wait for it.

**Measure manual dependency as failure.** Record every human intervention requested or required, its cause, whether it was genuinely security-critical, and the corrective automation. The target is zero routine human interventions. A task is not autonomously complete if a person had to click "Run workflow", manually approve a normal backtest, transfer ordinary artifacts, or repeatedly answer questions that the agent could resolve through authorized tools.

## Mandatory response to repeated failure: change the approach

An error is evidence that an approach may be wrong—not an instruction to keep repeating it. The first meaningful failure requires root-cause diagnosis and a materially different alternative. After two independent occurrences of the same non-transient error on the same route, stop that route; do not repeat the same endpoint, parameters, data representation, parser, or model unchanged. Repeating an identical failed attempt without new evidence is a process failure.

For every material bottleneck:
1. Preserve the error, response code, request parameters, time window, source, content hash, parser/schema, and exact failing stage.
2. Separate transient transport failure, provider restriction, data absence, source-format change, implementation bug, and an invalid research/model assumption.
3. Generate at least three materially different responses where applicable: change endpoint/official archive route; change authorized data provider or venue; change data construction or pipeline composition; change time resolution/sample scope; or replace the unworkable model/hypothesis with a separately specified alternative.
4. Test the cheapest representative slice first, including a known-good positive control and the failure case. Confirm the new route returns valid non-empty observations where expected, correct timestamps, units, schema and source provenance.
5. If it passes, scale the method with bounded, resumable acquisition and content hashes. If it fails, record why and move to the next distinct approach.
6. If the original study cannot be implemented with realistic accessible evidence, stop spending cycles on that exact design. Preserve its **INCONCLUSIVE/INFEASIBLE** status, then formulate and test a more feasible research question or model. Do not fabricate evidence, weaken the original acceptance gates, or retroactively relabel a different study as the original one.

### Required quantitative-finance examples

**Negative example — repeated failure:** the same ETHUSDT/BTCUSDT monthly archives repeatedly produce the same 31 missing hours; the same `api.binance.com` endpoint repeatedly returns HTTP 451; the same aggregate-trades connector returns empty for both missing and known-active controls; or the same USDⓈ-M parser repeatedly fails on the January 2022 archive. Re-downloading the same files, retrying the same restricted host, or merely restating that the blocker persists adds no evidence. Asking the owner to manually start the next backtest is also failure.

**Positive example — redesign the evidence path:** independently acquire synchronized ETH/USD and BTC/USD OHLCV series from an authorized provider, validate each series and compute the synthetic cross rate as (P_{ETH/BTC,t}=P_{ETH/USD,t}/P_{BTC/USD,t}). For log-spread models, use (log(P_{ETH/USD,t})-log(P_{BTC/USD,t})). Verify both series use the same quote currency, compatible venue/market conventions, UTC bar boundaries and timestamps; align only on genuinely observed common intervals; retain each source's provenance; do not forward-fill missing bars or assume USDT/USD equals one. If quote currencies differ, acquire and validate the conversion series explicitly. Compare the derived ratio against a direct ETHBTC market series when available.

Other valid alternatives include a different authorized exchange/provider, raw trade-level aggregation, official daily archives instead of an inaccessible REST host, a shorter independently validated sample, a different bar frequency, or a model that does not require the failed data representation. A new sample or model is a distinct experiment: pre-specify its hypothesis, scope, costs, controls and acceptance criteria before evaluating its performance.

**Backtest activation rule:** once a historical research run meets its machine-checkable data, code, and pre-registered methodology gates, the agent must launch it through an authorized agent-triggered workflow without routine human confirmation. Add and verify an allowlisted command for every required research workflow. A failing data gate should fail the run clearly and automatically; it must never silently bypass validation. A workflow trigger being agent-controlled and a dataset being empirically valid are separate requirements.

## Adaptive contingency loop

Use this loop whenever a task encounters a blocker or a proposed mechanism is unavailable.

### 1. Define the invariant objective

Write down:
- the actual research or automation outcome needed;
- the evidence/artifacts that prove it;
- the scientific, security, cost, and authorization constraints that must remain unchanged;
- which parts can progress independently of the blocked component.

Do not let a tooling workaround redefine the scientific question.

### 2. Locate the bottleneck precisely

Classify it before choosing a remedy:

- **Tool capability:** the connected integration lacks the required action or its schema is narrower than expected.
- **Permission/identity:** the action exists but the connected actor lacks the necessary access or is not the verified actor.
- **Trigger/orchestration:** work can be executed but cannot be started autonomously, resumed, deduplicated, or chained.
- **Network/data source:** an endpoint is blocked, incomplete, throttled, discontinued, or inconsistent.
- **Runtime/compute:** limits, dependencies, timeouts, memory, or long-running jobs prevent execution.
- **State/storage/artifacts:** results cannot be checkpointed, recovered, transferred, or inspected reliably.
- **Scientific acceptance gate:** data or evidence genuinely fail a pre-registered requirement.

Do not label an execution-environment or integration failure as a scientific result.

### 3. Inspect the actual capabilities

Before concluding that a route is unavailable:
- inspect the currently connected tool catalog and the exact action schema;
- inspect repository workflows, triggers, permissions, secrets references, control surfaces, and recent run evidence;
- verify the identity used by the connected integration from a harmless real operation;
- distinguish read access from write access and issue-comment support from pull-request-comment support;
- check current official platform documentation when endpoint permissions or event semantics matter.

Never infer support from a tool name, UI label, documentation example, or a previous session.

### 4. Generate and rank alternatives

When the first route is blocked, identify materially different alternatives. Rank them by:
1. end-to-end autonomy;
2. security and least privilege;
3. reliability and recoverability;
4. observability and auditability;
5. operating cost and rate-limit exposure;
6. implementation and maintenance burden.

Prefer an existing connected capability or free, repository-native mechanism over adding paid infrastructure. Do not choose a weaker or less secure path merely because it is the easiest.

### 5. Test the smallest safe proof

Use a harmless, low-cost, reversible test that validates the actual missing capability—not just configuration syntax.

For dispatch, this means proving that the real connected agent can submit the command, that GitHub starts the intended workflow with the expected event/actor/ref, and that the agent can retrieve and verify the output.

For data access, it means testing the exact endpoint, symbol, time range, schema, and completeness behavior. For compute, it means testing checkpoint/restart and artifact recovery.

### 6. Adapt instead of looping

- Retry transient timeouts or rate limits only with bounded backoff.
- After two independent instances of the same explicit permission denial, do not repeat the identical call. Change the access route, execution environment, or permission design.
- If an alternative fails, record why and select the next materially different option.
- Do not keep creating near-identical workflows or repeatedly dispatching an unchanged failing experiment.
- Do not create broad `push` or recurring `schedule` triggers merely to force progress. Prefer exact, allowlisted agent-triggered commands for routine audits and historical backtests; missing activation is an engineering failure to repair, not a reason to request a human click.
- If all safe autonomous routes require an owner-only permission or credential, finish every independently executable part, prepare the exact minimal setup, and state the single precise owner prerequisite. Continue the rest of the research/engineering work where possible.

### 7. Persist the learning

Update the relevant README, standard, task, or report with:
- the bottleneck and its evidence;
- the alternatives considered and why they were accepted/rejected;
- the implementation and exact permission boundary;
- tests, run IDs, commit SHAs, logs, artifacts, and hashes;
- what is now automated and what remains blocked;
- the next concrete experiment or implementation step.

Queue a next task that advances the objective rather than merely repeating the blocked attempt.

## GitHub Actions queue-pending contingency

A queued workflow is an infrastructure/orchestration state, not a research result. Never report it as running, completed, passed, or failed until the corresponding run/job evidence supports that status. Never ask the owner to click "Run workflow", rerun a routine historical job, or approve an ordinary CI/data-audit step merely to clear a queue.

### Identify which queue is blocking execution

For every delayed run, preserve the workflow run ID and task/command key, then inspect both the workflow-run record and its jobs. Record the run URL, workflow path/name, event, actor, ref, head SHA, created_at, updated_at, current status/conclusion, job names/statuses, requested runner labels, populated runner name/group, and the relevant concurrency group. Inspect competing runs in the same group and the current workflow YAML. Use created_at and job timestamps to estimate queue age; do not rely on run_started_at alone as a queue-duration measurement.

Distinguish at least these cases:

- **Workflow-level/concurrency pending:** another run in the same concurrency group is occupying the slot. Identify that run and whether it is genuinely progressing, stuck, or obsolete. A workflow-level concurrency key can serialize otherwise unrelated commands.
- **Job queued for a runner:** the run exists, but a job has not acquired a runner. Inspect runner labels/groups, available runner capacity, plan/organization concurrency limits, and GitHub Actions service status. Compare other recent jobs using the same runner class.
- **Job waiting on an environment or approval:** this is an approval/protection gate, not ordinary runner capacity. Routine historical research and CI should not be coupled to an environment that requires owner approval. Do not bypass a genuine protection boundary; redesign the routine workflow so it does not request privileged deployment/capital permissions.
- **Workflow dispatch not actually created, rejected, or cancelled:** verify the trigger event, exact actor/command gate, run record, cancellation reason, and API response. A comment succeeding is not proof a run was queued.

### Queue-age response thresholds

These are repository operating thresholds, not a GitHub service-level guarantee:

| Observed queue age | Required agent response |
|---|---|
| 0–5 minutes | Treat as an ordinary short wait. Keep the existing run ID; do not dispatch a duplicate. |
| 5–15 minutes | Inspect run and job records, same-group runs, runner labels, and Actions service status. Recheck after a bounded 2–5 minute interval rather than busy-polling. |
| 15–30 minutes | Classify the cause as concurrency serialization, runner capacity, approval/configuration, or unknown. Record evidence and the next diagnostic. Continue independent code, data, and research work that does not depend on this run. |
| More than 30 minutes | Treat as a prolonged infrastructure blocker. Make one evidence-based recovery decision: allow a demonstrably progressing same-group run to finish; repair a repository-controlled concurrency/configuration mistake; or use an already-authorized, available alternative runner/execution route. Do not repeatedly dispatch the same command. |
| More than 60 minutes | Mark the run **INFRASTRUCTURE-BLOCKED / QUEUED**, preserve the run ID and diagnostics in the task handoff, and advance all independent work. Revisit the same run before considering a replacement. A new run requires a safe deduplication/fencing plan. |

Poll at bounded intervals (typically 2–5 minutes during diagnosis, then 5–10 minutes for a sustained external capacity delay). If the current agent session cannot remain active, persist the run ID, last-observed status/time, evidence, and exact next status check for the next scheduled agent cycle. Do not imply that a background poller exists unless one is actually configured.

### Safe recovery rules

1. **Never fan out retries to make a queue move faster.** One task/experiment should have one canonical active run. Map the task key and exact inputs to its run ID. Repeated comments or agent cycles must first discover and reuse that run.
2. **Preserve queued work.** For a workflow that must retain every accepted command, configure an explicit bounded concurrency queue. This repository's ETH/BTC research workflow uses one shared concurrency group to prevent overlapping research operations; queue: max preserves up to 100 pending runs instead of allowing a newer pending run to replace the older pending run under the default single-pending behavior. At the configured limit, stop dispatching more copies and record the remaining work in the task ledger.
3. **Do not cancel a run only because it is old.** Cancel or supersede it only when it is demonstrably obsolete, unsafe, invalidated by a newer specification, or replaced by a verified alternative. Before starting a replacement, confirm the old run cannot later execute the same expensive task; use a task-level idempotency key, lock, or explicit cancellation/fencing and verify the resulting state.
4. **Do not alter concurrency merely to bypass a wait.** Split concurrency groups only when the jobs are genuinely independent and shared data, caches, artifacts, rate limits, and research state cannot conflict. Keep non-cancellable serialization for mutually exclusive full-data operations.
5. **Use only already-authorized alternatives.** A different runner class or execution environment is acceptable only if it is actually available, authorized, and does not introduce unapproved cost or broader permissions. Do not create paid infrastructure or request routine owner action as the default recovery.
6. **Classify correctly.** A prolonged queue is not a failed test, data failure, or negative empirical result. Report it as an infrastructure/orchestration delay with its run ID and age. A successful workflow dispatch is likewise not a completed research result.

Official diagnostics: [GitHub Actions concurrency controls](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), [Actions limits](https://docs.github.com/en/actions/reference/limits), and [GitHub Status](https://www.githubstatus.com/).

## Dispatch contingency patterns

The dispatch route is selected by demonstrated capabilities, not by loyalty to one event type.

### A. Direct authenticated workflow dispatch

Use the GitHub Actions workflow-dispatch API when a connected tool or authorized integration can invoke it with the required repository Actions write permission. Keep workflow inputs typed and validated. Verify the returned run by workflow path, event, actor, ref, inputs, logs, and artifacts.

### B. Issue-comment event bridge

Use a dedicated control issue when the connected agent can create comments on ordinary issues. Each on-demand workflow gets a distinct exact command and a strict gate checking:
- event is `issue_comment` with activity `created`;
- exact control-issue number;
- ordinary issue (not a PR);
- exact approved actor login;
- entire comment body equals the workflow's command.

Use reviewed fixed defaults or validated parameter profiles. Never interpret arbitrary comment text as shell input.

### C. Pull-request-comment bridge when issue comments are unsupported

If the connected integration demonstrably supports pull-request comments but not ordinary-issue comments, a dedicated, tightly controlled control PR is a viable contingency—not an automatic rejection.

For this route:
- use one stable, explicitly designated control PR and its exact PR number;
- gate on `issue_comment: created`, the exact PR number, the exact verified actor, and exact full command body;
- run the workflow from the repository default branch, as GitHub's `issue_comment` event uses the last commit on the default branch and sets `GITHUB_REF` to the default branch;
- never check out, import, execute, or otherwise trust the control PR head or any PR-supplied code/data as executable instructions;
- do not use `pull_request_target` as a shortcut;
- keep all job permissions minimal and test that comments on every other issue/PR are ignored.

This route is appropriate only after reviewing the event payload and proving the integration's real actor and commenting behavior. GitHub documents the default-branch behavior for `issue_comment` events in its [workflow event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

### D. GitHub App or authorized API relay

If the connected ChatGPT action cannot create the required comment or dispatch request, investigate a repository-scoped GitHub App or another already-authorized integration that can do so. Possible mechanisms include:
- a GitHub App installation token invoking workflow dispatch (Actions write);
- a GitHub App installation token creating a control comment (Issues or Pull requests write);
- a `repository_dispatch` event with a unique `event_type` and validated payload (Contents write);
- a narrowly scoped, authenticated relay/worker that accepts only an allowlisted workflow command and invokes the GitHub API.

Keep private keys and tokens in GitHub Actions secrets or a suitable secret manager. Use short-lived installation tokens where possible. Do not create an unauthenticated webhook, embed credentials in source, or ask for a broad personal access token when a fine-grained app permission is sufficient. Any external relay must be justified against native GitHub capabilities and its cost, reliability, and maintenance burden.

### E. Polling only when event-driven routes are genuinely unavailable

A bounded poller for a control issue/PR may be considered only after direct dispatch, authenticated comments, and a secure relay have been evaluated. It must have a justified interval, strict actor/command validation, idempotency, concurrency control, rate-limit monitoring, deduplication, and an explicit stop condition. Do not introduce recurring compute or API costs without evidence that polling is the best remaining route.

### Dispatch completion standard

A route is not autonomous until a real ChatGPT-connected operation triggers a harmless workflow, the expected event and actor are verified in the run, logs prove the gate passed, and the agent retrieves and checks the output. A comment creation response, a workflow YAML file, or a manually launched test does not meet this standard.

Keep `workflow_dispatch` available as a break-glass owner recovery path where appropriate, but do not make it the agent's default route, repeatedly instruct the human to use it, or count it as satisfying autonomous execution.

## Research execution contingencies

Apply the same adaptive reasoning to the research pipeline itself.

| Bottleneck | Adaptive response |
|---|---|
| Agent network access blocked | Move only the network-dependent step to an authorized hosted runner; preserve exact request, source, logs and artifacts. |
| One official data endpoint is incomplete | Cross-check a different official endpoint, archive granularity, or official market-data representation; compare timestamps and hashes. |
| Provider/API rate limits | Use bounded backoff, caching, pagination, batch sizing, request budgeting, and resumable retrieval. Do not silently reduce the sample. |
| One asset/market fails validation | Audit the full declared universe independently and report all failures; do not stop at the first symbol or silently exclude it. |
| Long job exceeds runtime | Split into deterministic chunks with checkpoints, content hashes, and validated resume; verify aggregate boundaries and no overlap/gaps. |
| Dependencies or runtime unavailable | Use pinned, compatible versions or a controlled hosted environment; retain reproducibility and record environment details. |
| Artifact is too large or unavailable | Partition/compress outputs, retain compact manifests and hashes, and use supported artifact/object storage; never commit raw market data merely to simplify transfer. |
| A scientific gate fails | Diagnose, document, and repair source or methodology where legitimate; otherwise preserve NO-GO/INCONCLUSIVE. Never weaken the gate to manufacture a result. |

## Security, research integrity, and stop conditions

- Never expose API keys, app private keys, tokens, or secrets in code, task text, commits, logs, or artifacts.
- Never execute untrusted pull-request code in a privileged workflow.
- Never use comment text, issue fields, or arbitrary external payloads as shell commands.
- Use exact actor/target/command allowlists and the minimum permissions required.
- Use concurrency controls and idempotency to prevent duplicate expensive runs.
- Do not create live-trading credentials, place live orders, deploy capital, or promote a strategy unless separately and explicitly authorized.
- Preserve pre-registration, holdout independence, causal ordering, realistic fees/slippage/funding, survivorship controls, and the original strategy specification.
- Unresolved data-quality failures remain **INCONCLUSIVE**; synthetic tests validate plumbing only.

## Definition of a successful agent session

A session should leave the research system better able to learn autonomously. The agent must:
1. complete the most recent pending task where possible;
2. remove or materially reduce at least one verified bottleneck, or identify the exact owner-only prerequisite after exhausting safe alternatives;
3. validate the change with inspectable evidence;
4. update persistent documentation and preserve negative findings;
5. define the next task as the highest-value step in the research-learning loop.

**The target is not simply a successful run today. It is a research factory that can discover, retrieve, test, challenge, report, recover, and improve with progressively less routine human intervention.**

## Official platform references

- [GitHub Actions workflow events, including `issue_comment` and `repository_dispatch`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Create an issue comment and required write permissions](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment)
- [Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [Create a repository dispatch event and required Contents permission](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GITHUB_TOKEN event suppression and exceptions](https://docs.github.com/en/actions/concepts/security/github_token)
