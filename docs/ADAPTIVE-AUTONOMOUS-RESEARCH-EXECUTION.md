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
- Do not create broad `push` or recurring `schedule` triggers merely to force progress.
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
