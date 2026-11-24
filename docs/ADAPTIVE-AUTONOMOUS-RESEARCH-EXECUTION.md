# Adaptive Autonomous Research Execution Standard

**Status: repository-wide operating standard for every current and future agent.**

## Mission

Maximize the rate at which the repository produces **trustworthy, reproducible quantitative research learning** by continuously removing engineering, tooling, data-access, compute, orchestration, and handoff bottlenecks.

An agent's responsibility is not merely to execute the initially proposed method. It is to reach the research objective through the best secure and evidence-preserving route available, adapt when an assumption fails, and improve the system so the next research cycle is more autonomous and reliable.

**Do not confuse the requested outcome with the first implementation idea.** A blocked route is a reason to diagnose and adapt—not a reason to stop, repeat the same attempt, or make the human perform routine agent work.


## Mandatory project-entry sequence: feedback and environment before hypothesis

Every new project must follow the [Evidence-First Project Lifecycle](RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md) and [Asset-Universe Discovery and Scope Policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md). Do not begin with a preselected model and then attempt to obtain, invent, splice or repair data/infrastructure to fit it. The factory has no global asset whitelist: do not inherit ETHUSDT/BTCUSDT or any other prior project's symbols, fixed top-N count, venue or market-cap tier as a constraint on future research.

Before new hypothesis design: review the previous task's research/performance and technical-delivery feedback; record an evidence-backed repository-admin calibration decision; inventory actual data/source access, permissions, history, point-in-time coverage, semantics, quality controls, economic inputs, compute/API limits, storage, provenance and autonomous execution; classify every dimension with evidence; permit hypotheses only against VERIFIED required dimensions; and assign difficulty/timebox only after feasibility and scope are established.

Use `research/project_readiness.py` and the [project-intake template](../templates/PROJECT-INTAKE-TEMPLATE.json). Passing tests does not prove data availability or empirical performance. Complete the [retrospective/admin-calibration standard](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md) before creating a successor task.

## General mindset and higher-order optimization priority

This standard is governed by the [General Antifragile Autonomous Operating Mindset](GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md). It applies across every safe repository activity, not only the ETH/BTC research pipeline.

**Mandatory priority order (governed by the General Antifragile Autonomous Operating Mindset):**
0. Hard invariants — security, legality, privacy, authorization, financial safety, scientific validity, data integrity, provenance, reproducibility and causal correctness. These are veto conditions.
1. Higher-order meta-process optimization — eliminate recurring failures and routine human intervention; improve autonomous orchestration, acquisition, observability, recovery, reproducibility and hygiene.
2. Resolve existing work and highest-value bottlenecks — inspect active runs, incidents, artifacts and dependencies first; do not duplicate work; progress independent workstreams.
3. Original research implementation and recovery — preserve the frozen hypothesis while changing materially failing implementation details.
4. Independent providers and replacement data architectures — use bounded evidence-led pilots and the fallback hierarchy below.
5. Hypothesis/model replacement — only after reasonable distinct alternatives are exhausted; create a separately preregistered experiment.
6. Local optimization and cosmetic polish — last.

The general mindset is authoritative. This document implements it; project tasks may add stricter gates but cannot reorder priorities or contradict hard invariants. Process improvements require a causal rationale, measurable verification, bounded cost, reversibility where practical and a stop condition.


### Mandatory quantitative-model timebox

Before starting a new model's substantive implementation or inspecting empirical model results, apply [the Model Implementation Timebox and Research Conclusion Deadline Policy](MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md). Record the difficulty tier and rationale, UTC start, cycle cap, implementation deadline, final conclusion deadline, milestones and deadline outcome rule in that model's preregistration and the active queue. Do not begin an untimeboxed model.

The limit is the earlier of the tier's cycle cap or calendar deadline. It includes ordinary debugging, data retrieval, CI/runner delays, empirical execution and reporting; agents must adapt routes rather than reset the clock. Keep hard acceptance and safety gates intact. Deadline expiry without valid empirical evidence means **INCONCLUSIVE/INFEASIBLE**, never an invented NO-GO. No automatic extension or rollover is allowed. A materially changed experiment requires a distinct identity and a new preregistration/timebox.

The deferred activation condition was met by the prior Spot mean-reversion NO-GO on 2026-11-22. The current Spot Momentum assignment is MEDIUM: four substantive cycles maximum, implementation by **2026-11-26 18:00 UTC**, and a final research conclusion by **2026-11-28 18:00 UTC**. The separate unresolved USDⓈ-M funding study does not suspend this policy.

### Parallel workstream execution

Independent work should proceed concurrently where it increases decision throughput and passes the dependency, duplicate-dispatch, write-scope, exclusive-resource, confirmatory-holdout and real-capacity checks. One primary critical-path task may coexist with additional independent active workstreams; a single-active-task queue must not become an artificial serialization bottleneck. Do not start a successor whose explicit predecessor gate remains open.

Every workstream owns its own difficulty-based cycle cap and UTC expiry. Its clock starts at substantive execution, not while queued, and does not reset on handoff, ordinary CI delay or a change of agent. Expiry closes only that workstream; unrelated admitted work continues. The earlier of its own cycle cap or expiry timestamp controls, and expiry without valid empirical evidence is INCONCLUSIVE/INFEASIBLE, never an automatic NO-GO.

Apply [Parallel Research Workstreams and Per-Workstream Expiry Policy](PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md). Before concurrent activation, use evaluate_parallel_workstream_admission and assess_workstream_timebox in research/workstream_policy.py. The validator is a guardrail, not a replacement for evidence-first intake, authorization, resource-capacity assessment or scientific review.

Before any substantive action, brainstorm a compact adaptive antifragile plan from the live context: current tasks, run/incident state, recent failures, available tools and permissions, costs, independent work and long-term impact. Generate at least three materially different approaches for a significant blocker where applicable; rank them and define success criteria. Record the plan in the existing task handoff, not a new per-session document.

Then perform the mandatory conservative repository cleanup in [Repository Hygiene and Context Compaction](REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md), before the primary meta-improvement or research task. Keep one canonical active task pointer. Remove disposable scratch/build clutter and stale active instructions, but preserve historical evidence, source data needed for reproducibility, checksums, manifests, run logs, incident records and research conclusions. Never delete active work or force a clean tree at the expense of provenance.

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

### Provider and architecture failover hierarchy

The initial ETH/BTC execution sequence is:
1. Resolve existing Binance official archive, public market-data host, parser and aggregate-trade evidence first as P3 existing-work recovery. Respect HTTP 451 and any other access restriction; never route around it.
2. **MEXC independent-provider pilot (first P4 candidate):** test synchronized ETH/USDT and BTC/USDT hourly histories, plus suitable USD-quoted pairs if available. Establish endpoint/product identity, inception/retention, pagination and bounded full-history feasibility before scaling.
3. **Bitget independent-provider pilot (second P4 candidate):** independently test synchronized ETH/USDT and BTC/USDT hourly histories and suitable USD pairs, with separate provenance and acceptance.
4. Pilot Coinbase Exchange synchronized ETH-USD/BTC-USD candles and Kraken ETH/USD/BTC/USD OHLCVT as further independent alternatives.
5. Keep discovering and screening lawful, independently verifiable venues and historical-data vendors. Candidates are not limited to this list; examples include OKX, Bybit, Gate.io, KuCoin and specialist historical-data providers. Verify current product availability and permitted access rather than assuming it.
6. Test raw-trade reconstruction or independently verifiable aggregate-trade datasets when candle sources omit or corrupt observations.
7. Compare independent sources on common historical windows to quantify discrepancies; comparison is a quality diagnostic, not permission to splice venues.

MEXC and Bitget have first and second **pilot-order priority**, not automatic acceptance. Rank bounded pilots by expected information gain, probability of success, data quality, historical coverage, full-history feasibility, reproducibility and cost. Evidence-based scoring may reorder execution; authorization and scientific acceptance are hard filters, not score components that can be traded off.

For every provider, define before scaling: (a) one known-active positive control; (b) a meaningful negative/missing-data control; (c) product inception and requested coverage; (d) UTC timestamps, units, schema, OHLCV invariants and duplicates; (e) source URL/parameters, checksums or immutable content hashes and manifest; (f) full-history transfer/storage feasibility; (g) explicit acceptance and rejection rules; and (h) the next independent fallback. A successful download or HTTP 200 is never sufficient for acceptance.

When direct ETH/BTC is unavailable, test materially different constructions in separate experiment identities. Preferred example: ETHBTC = ETHUSD / BTCUSD using synchronized same-venue prices and consistent bar conventions. If quote currencies differ, obtain and validate the required USDT/USD or USDC/USD conversion rather than assuming parity. Other architecture alternatives include raw-trade aggregation, alternative archive formats, event-time/irregular-time data and a separately justified observation frequency. Preserve elapsed time and missing observations; never forward-fill or infer zero returns. Do not combine venue datasets without an explicit, tested reconciliation methodology.

After two distinct providers fail on the original construction, advance to a different data architecture instead of trying endless provider variants. If the architecture search is exhausted and the original hypothesis is infeasible, formally classify it INCONCLUSIVE/INFEASIBLE and use a new preregistered hypothesis/model with independent acceptance criteria and provenance. A timeframe, market construction or model change that alters the inference creates a distinct experiment.

### Separate funding-data hierarchy

Spot price validation and perpetual funding acceptance are independent. Evaluate Binance Vision final-rate archives, Tardis and other credible settlement sources separately. Record final settled rates, predicted/pre-event estimates, next-event timestamps, effective funding intervals, contract incarnation/retention and the completeness of the payable settlement population as separate fields. Never substitute pre-event estimates for final settlements. A spot-only experiment may proceed under its own gates but cannot establish perpetual-strategy profitability.

### Machine-enforced decision rules

Use research/adaptive_decision.py as the tested policy implementation:
- provider candidates are scored on expected information gain, success probability, data quality, coverage, reproducibility and cost, but unauthorized candidates are excluded;
- provider evidence fails closed when any required provenance, coverage, controls, schema, timestamp, OHLCV, duplicate or checksum gate is missing/false; funding additionally requires final-settlement semantics, complete settlement population and contract-incarnation coverage;
- transient failures may receive bounded retry; restricted routes stop immediately; the second identical non-transient failure stops that route; two distinct provider failures escalate to a different architecture;
- independent workstreams continue when their dependencies do not intersect the blocked inputs;
- experiment identities encode the hypothesis, provider, venue, market construction, quote currency, timeframe, sample, strategy, cost model and source version;
- spot and perpetual claims are separated; duplicate active dispatches are reused, not duplicated;
- hypothesis replacement requires exhausted alternatives, formal original INCONCLUSIVE/INFEASIBLE status, a different identity, frozen preregistration, independent acceptance criteria and its own provenance;
- the six-input empirical gate rejects missing, unknown, incomplete or unmanifested inputs and incomplete Spot reconciliation.

When the relevant evidence is not machine-readable, record the missing evidence as unresolved; do not infer acceptance. Unit tests exercise policy logic, not live provider quality or empirical market performance.

**Backtest activation rule:** once a historical research run meets its machine-checkable data, code, and pre-registered methodology gates, the agent must launch it through an authorized agent-triggered workflow without routine human confirmation. Add and verify an allowlisted command for every required research workflow. A failing data gate should fail the run clearly and automatically; it must never silently bypass validation. A workflow trigger being agent-controlled and a dataset being empirically valid are separate requirements.

**ETH/BTC market-scoped command allowlist on control PR #2:**

- `/qfr-run-eth-btc-empirical` — combined Spot + USD-M perpetual experiment; requires all six inputs and both market-specific gates.
- `/qfr-run-eth-btc-spot-empirical` — independent Spot-only experiment; does not require perpetual funding, but requires both Spot price manifests, complete hourly data or independently reconciled no-trade gaps, and an accepted event-time/elapsed-time policy whenever gaps remain.
- `/qfr-run-eth-btc-um-empirical` — independent USD-M perpetual experiment; requires both USD-M price histories and both accepted final-settlement funding histories, but does not require Spot completeness.

The preflight receives the same market scope as the selected empirical command. The audit still records all six inputs so independent evidence is retained; the scoped research gate decides only whether the requested experiment is eligible. An accepted Spot gap classification alone is not enough to run the current hourly Spot engine: the event-time/elapsed-time PnL, signal, execution and annualization policy must also be implemented and accepted. The current gate deliberately keeps that condition false. Scope separation is not a reduction of scientific standards: Spot results cannot establish perpetual profitability, and the original combined experiment remains gated on all six inputs.


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

### 7. Persist the learning and calibrate the next project

Record both scientific/research outcome and technical-delivery outcome. Use the [Project Retrospective and Admin-Agent Calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md) standard. The next project must cite both evidence sets and state at least one repository-admin decision to change, retain or retire, with an expected effect and validation metric.



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
| 5–15 minutes | Inspect run/job state and exact concurrency group; identify any earlier active same-group predecessor. Recheck after a bounded 2–5 minute interval. |
| More than 15 minutes | **Cancel the run immediately** if it is still run-level `queued`/`pending` and no earlier run in the exact same concurrency group is `in_progress`. Preserve its task as `RETRY_REQUIRED`; do not immediately duplicate it. Keep it only while that verified predecessor is active. |

| More than 30 minutes | Treat as a prolonged infrastructure blocker. Make one evidence-based recovery decision: allow a demonstrably progressing same-group run to finish; repair a repository-controlled concurrency/configuration mistake; or use an already-authorized, available alternative runner/execution route. Do not repeatedly dispatch the same command. |
| More than 60 minutes | Mark the run **INFRASTRUCTURE-BLOCKED / QUEUED**, preserve the run ID and diagnostics in the task handoff, and advance all independent work. Revisit the same run before considering a replacement. A new run requires a safe deduplication/fencing plan. |

Poll at bounded intervals (typically 2–5 minutes during diagnosis, then 5–10 minutes for a sustained external capacity delay). If the current agent session cannot remain active, persist the run ID, last-observed status/time, evidence, and exact next status check for the next scheduled agent cycle. Do not imply that a background poller exists unless one is actually configured.

### Deterministic 15-minute queued-run cancellation

**Default: cancel a workflow run once it has remained in GitHub Actions `queued` or `pending` state for more than 15 minutes. The sole exception is a positively verified wait for an earlier run to finish in the exact same concurrency group.** This is a deterministic queue policy, not a discretionary suggestion.

Apply the rule on every queue scan:

1. Consider only non-terminal workflow runs whose run-level status is `queued` or `pending`. Use the run's `created_at` as the age clock and re-fetch it immediately before cancellation. Do not apply this workflow-run rule to an individual job with status `queued` inside a workflow run that is already `in_progress`; that may be normal job dependency scheduling.
2. Determine the workflow's effective concurrency group from the workflow file/ref that governs the run. The exception is true only when an **earlier-created run** in that exact same group is currently `in_progress` and therefore occupies the concurrency slot. A run from another workflow, a different group, a merely queued/pending run, or a guessed dependency does not qualify.
3. If that exact active same-group predecessor exists, preserve the queued run regardless of its age. Record `WAITING_ON_SAME_GROUP_RUN`, its predecessor run ID, and recheck when the predecessor completes. This is the only age-based cancellation exemption. Do not reset its original creation timestamp.
4. If no qualifying predecessor exists and the queued/pending run is older than 15 minutes, cancel it immediately through an authorized GitHub Actions cancellation API/action. Do not wait for the 30- or 60-minute thresholds. This includes runner-capacity waits, missing/offline runner labels, and unexplained queued/pending states.
5. Re-fetch the run after requesting cancellation and verify the terminal `completed` / `cancelled` state. Record the run ID, age, reason `QUEUE_TIMEOUT_OVER_15M_NO_ACTIVE_SAME_GROUP_PREDECESSOR`, cancellation request/result, timestamp, and any API error. If it already started or completed during the race, do not claim it was cancelled; inspect its actual state and outputs.
6. A cancelled run is **not completed work**. Keep its task/CI requirement open as `RETRY_REQUIRED` or `CI_RETRY_REQUIRED`, preserving the exact command, inputs, SHA and artifacts. Do not immediately enqueue an identical replacement into the same unavailable capacity. Retry once only after there is positive evidence that runner capacity has recovered or through a materially different already-authorized execution route.
7. Never cancel `in_progress` runs, environment/protection `waiting` runs, or runs merely because an individual dependent job has not started. Those are outside this specific 15-minute runner-queue rule and follow their respective execution/protection policies.

**Concurrency exception ends immediately when the predecessor is no longer `in_progress`.** If the queued run is still `queued`/`pending` and its original age already exceeds 15 minutes after that predecessor ends, it becomes eligible for cancellation on the next scan. Do not invent a fresh 15-minute grace period.

**Enforcement prerequisite:** the agent/watchdog must have an authorized Actions-write cancellation capability. Read-only run inspection is not enforcement. If the connected tool lacks a cancellation action, record `CANCELLATION_ENFORCEMENT_BLOCKED` with the affected run IDs, mark each eligible run `CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION`, and immediately initiate the mandatory isolated alternative attempt described below. Provisioning a least-privilege, agent-controlled cancellation path remains an engineering task, but it must not block alternative research. Never claim cancellation occurred and never substitute a request for the owner to click Cancel.

### Mandatory fallback when a queued run cannot be cancelled

**A failed or unavailable cancellation must not leave the research objective idle.** Once a run is eligible for the 15-minute cancellation rule, attempt the authorized cancellation once and inspect the result. If cancellation cannot be issued, is rejected, times out, or does not reach a terminal state after re-fetching, the agent must do both of the following in the same recovery cycle:

1. **Mark the original run explicitly in the durable task/incident record** with status `CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION`. Record the original run ID and URL, task key, age, concurrency group, last observed state/time, cancellation action/result/error, and the fact that it may still start later. Do not describe it as cancelled, dead, terminated, or harmless. GitHub Actions run records do not provide a general-purpose user-defined label field; the canonical status tag belongs in the repository task/incident ledger and, if an incident issue is used, as an issue label/comment. Never rely on a label alone for state tracking.

2. **Initiate exactly one separate alternative attempt**, without waiting for the original run to be cleared. It must preserve the same high-level research objective but materially change at least one failed mechanism: execution plane/runner, workflow/dispatch path, provider/endpoint, data construction, pipeline architecture, timeframe, model/hypothesis, or decomposition of the work. A new run ID with the same workflow, same runner pool, same inputs and same code is not a different approach. Record its status as `ALTERNATIVE_ATTEMPT_ACTIVE`, its own attempt ID/run ID, parent/orphan run ID, changed mechanism, hypothesis, inputs, acceptance criteria and completion evidence.

#### Independence and orphan-safety requirements

- Give the alternative a distinct stable attempt key and run name. Keep its branch/worktree, working directory, cache key, artifacts, manifests and output paths separate from the orphaned attempt. Never allow the two attempts to overwrite shared mutable state.
- Prefer a genuinely different authorized execution plane or provider/pipeline so the alternative is not waiting on the same failed queue, runner labels, endpoint or orchestration bottleneck. Before dispatch, inspect the actual route and capacity; do not assume a new workflow name creates a different runner pool.
- Keep both attempts read-only with respect to market venues, accounts and capital. Do not introduce orders, live credentials, custody changes or external irreversible side effects.
- Use immutable inputs, checksums, idempotency keys and bounded provider request budgets. If the original run unexpectedly starts later, the two attempts must remain isolated; coordinate shared rate limits and prevent duplicate writes or conflicting publication.
- If complete parallel execution cannot be made safe, immediately execute a genuinely independent, non-mutating slice of the alternative (for example a provider positive-control probe, a separate asset-pair ingestion, a different model specification, deterministic tests or an independent data-quality audit) while keeping the original orphan fenced from shared outputs. Do not wait passively for the original run.
- Do not weaken the original experiment's data, causality, cost, holdout or statistical gates. Treat the alternative as a distinct experiment with its own pre-specified hypothesis and acceptance criteria; never merge its results into the original experiment as if they were the same sample or model.

#### Progress, retry and closure

- After starting the alternative, verify that its trigger, actor, workflow, runner/route, commit, attempt key and first job actually started. A successful dispatch/comment alone is not execution evidence.
- Recheck the orphan and alternative independently. If the orphan later starts, do not automatically cancel the alternative or combine their results; inspect isolation, resource budgets and progress, then keep the more informative safe path(s).
- Do not create a third attempt merely because the first alternative is also queued. Diagnose that new bottleneck and select a materially different independent slice or route; cap the response at one active alternative per orphan incident unless evidence shows the alternative itself has failed and a new separately justified experiment is required.
- Close the orphan incident only when the original run reaches a verified terminal state, or its risk is explicitly bounded and the independent alternative has produced inspectable evidence. Preserve both run IDs and their lineage in the task report.

### Mandatory 60-minute recovery protocol — active recovery, not passive waiting

Crossing 60 minutes is a **mandatory recovery trigger**, not an automatic cancellation deadline and not proof that GitHub is down. The agent must perform this procedure in the same cycle in which the threshold is detected. If the current session cannot complete it, persist the exact next action and run IDs for the next agent cycle; do not just write “still queued”.

#### 1. Open an execution incident record

For each affected task, record:
- canonical task/experiment key and exact command/inputs;
- run ID and URL, workflow path/name, event, actor, ref, commit SHA and concurrency group;
- first observed and latest observed timestamps, calculated queue age, workflow status/conclusion, and every job's status/conclusion;
- runner labels requested, runner name/group if assigned, and any environment/protection wait;
- the run currently occupying the concurrency slot, if any;
- GitHub Status incident/component state and the exact diagnostic/API errors observed;
- artifacts/checkpoints already produced and whether the run could have performed irreversible work.

Keep **execution status** separate from research status. The research result remains NOT RUN / INCONCLUSIVE until valid empirical work completes; a queue delay is never an empirical failure.

#### 2. Diagnose the exact blocker before changing anything

Inspect the run record, latest-attempt jobs, same-concurrency-group runs, workflow YAML, runner labels and available runner configuration. Compare other recent runs that use the same runner class. Check GitHub Status and the applicable repository/organization Actions usage or concurrency limits when the connected identity can read them.

Choose the best-supported classification:
- **Concurrency-slot wait:** identify the exact run holding the same concurrency group. Inspect whether its job is progressing, has a valid long-running step, or is itself stuck. A pending run behind healthy work is serialized, not runner-starved.
- **Runner-capacity or label wait:** the job exists but has no runner assignment. Verify that its requested labels match a runner that actually exists and is online; inspect account/organization concurrency ceilings and whether other workflows are consuming available slots. Do not assume the account's limit.
- **GitHub service incident:** match the time and affected Actions component to the official status incident. Do not flood the service with replacement runs during an incident.
- **Environment/protection wait:** identify the exact environment or approval gate. Do not bypass a genuine owner/security/deployment boundary. If ordinary CI, historical backtests or data audits were incorrectly coupled to a privileged environment, separate the unprivileged job only after verifying it has no deployment, secret, custody or capital authority.
- **Abnormal/stale workflow state:** examples include a run with no jobs created, an apparently queued/in-progress run whose cancellation does not take effect, a failed-cancel message, or cancellation/force-cancellation API errors such as HTTP 409/500. Check whether the same stale run continues to block its concurrency group.
- **Dispatch/authorization problem:** confirm whether a run was actually created, whether the exact actor/command gate passed, and whether the event was rejected, skipped or cancelled. Do not mistake a created comment for a created or authorized run.

A lack of fresh log lines by itself does not prove a job is stuck: some legitimate data or compute steps are quiet. Use job state, step state, runner assignment, elapsed time, timeout configuration and competing runs together.

#### 3. Select exactly one safe recovery path

Do not fan out multiple retries. Select the first applicable path below and record why:

1. **Healthy run owns the concurrency slot:** keep the canonical pending run in the queue. Inspect the active run's logs and expected stage; allow it to finish when it is making progress. Do not cancel a valid long-running full-data audit simply to move a later run forward. Continue independent tests, code review, provider research, task specification and local deterministic checks.
2. **Obsolete or genuinely stalled slot-holder:** first inspect checkpoints, logs and side effects. Cancel only when the run is no longer useful, is invalidated/unsafe, or blocks a verified replacement. Confirm cancellation reached a terminal state before starting the replacement. For a long job, preserve partial outputs and resume from a deterministic checkpoint rather than repeating all completed work.
3. **Runner label/capacity problem:** fix an incorrect label or runner selection if repository-controlled and safe. Otherwise use one already-existing, authorized alternative runner or execution path. Verify it has the needed network access, dependencies, data permissions and cost profile. Do not provision paid/larger/self-hosted infrastructure or expand permissions without explicit owner authorization.
4. **GitHub service incident:** leave the canonical run intact unless GitHub marks it cancelled/failed. Stop creating duplicates; continue independent work and recheck the incident and the same run at bounded intervals. Once the incident resolves, inspect the original run before deciding whether a single retry is necessary.
5. **Environment gate:** keep the protected operation paused. Move routine non-privileged testing/research into a separate least-privilege job only if this removes an accidental coupling without bypassing the protected action.
6. **Abnormal/stale run that blocks concurrency:** make at most one carefully evidenced self-service cancellation/force-cancellation attempt if cancellation is appropriate and supported. Re-fetch the run and jobs afterwards. If the run remains queued/in progress, no jobs are created, cancellation reports failure, or the API returns a persistent conflict/server error, stop cycling retries and prepare a GitHub Support case with the repository, workflow/run URLs and IDs, concurrency group, UTC timestamps, job state, cancellation attempts and exact HTTP/error request IDs. Use the Support portal only through an already-authorized account; never expose tokens or secrets. Continue all independent work while the platform-side state is unresolved.

Do not split concurrency groups merely to defeat a wait. Separate groups only for tasks proven independent in code, shared state, caches, rate limits, artifacts and data writes. This repository's single ETH/BTC research group intentionally serializes mutually exclusive empirical runs.

#### 4. Time-box the recovery attempt

After taking the selected action:
- Recheck the same canonical run and relevant jobs after 10–15 minutes.
- If it progresses, continue normal bounded monitoring and verify the eventual outputs.
- If it does not progress, do not repeat the same action or submit an identical dispatch. Record the result of the recovery attempt and either switch once to a materially different, already-authorized route or park the run as **INFRASTRUCTURE-BLOCKED / QUEUED** while advancing independent work.
- If the same abnormal condition persists after the one safe recovery attempt, escalate using the documented platform/support route where applicable; do not start an endless retry loop.
- Never use the 60-minute threshold to weaken data gates, reduce validation, shorten the sample, or label incomplete research as complete.

#### 5. Resume and close the incident safely

When the original run starts or completes, inspect that same run first. Verify actor, event, ref, SHA, inputs, jobs, logs, artifacts, manifests, hashes and outputs. If a replacement was created, ensure only one run can still perform the expensive task; cancel/fence redundant work only after checking its state and side effects. Retry only the failed portion when supported and scientifically safe; otherwise create one new run with a recorded reason and idempotency key.

Update the task ledger/README with the root cause, diagnostics, action taken, run IDs, commit SHA, recovery result, any owner-only prerequisite, and the next concrete step. A queue incident is closed only when execution resumes/completes, a verified alternative takes over, or an external platform/support blocker is explicitly recorded with a next check. Never leave “wait indefinitely” as the task.
### Safe recovery rules

1. **Never fan out retries to make a queue move faster.** One task/experiment should have one canonical active run. Map the task key and exact inputs to its run ID. Repeated comments or agent cycles must first discover and reuse that run.
2. **Preserve queued work.** For a workflow that must retain every accepted command, configure an explicit bounded concurrency queue. This repository's ETH/BTC research workflow uses one shared concurrency group to prevent overlapping research operations; queue: max preserves up to 100 pending runs instead of allowing a newer pending run to replace the older pending run under the default single-pending behavior. At the configured limit, stop dispatching more copies and record the remaining work in the task ledger.
3. **Enforce the 15-minute queue cancellation rule.** Cancel every run-level `queued`/`pending` run older than 15 minutes unless an earlier run in the exact same concurrency group is currently `in_progress`. Never cancel the predecessor or a valid `in_progress` run under this rule. Verify the terminal cancellation state; retain the task as retry-required and do not duplicate it until capacity or an alternative route is verified.
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



### Decision-to-execution invariant: same-session replacement

When evidence supports the conclusion that a component must be replaced, that conclusion immediately becomes the current session's implementation task. Do not defer it to a later cycle or leave it as a recommendation. Implement a materially different, authorized replacement now; add regression tests; execute the relevant bounded validation; inspect logs/artifacts; and update the single canonical queue and handoff before ending the session. If an external fact or owner-only permission prevents final acceptance, still implement all independent safe work and a fail-closed probe/manifest path in the same session, then identify the exact remaining prerequisite. Distinguish replacement implemented, replacement technically validated, and research/data completeness accepted. Never claim a stronger status than the evidence supports.

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


### Propagation across every safe repository workstream

The adaptive/failover philosophy applies uniformly to all work that does not cross a genuine security, legal, authorization or live-financial boundary. The following is the minimum operating behavior; individual tasks may add stricter scientific acceptance gates but may not weaken this autonomy standard.

| Workstream | Required autonomous behavior after a blocker |
|---|---|
| Research hypothesis/model | Preserve the objective; test a different, independently specified hypothesis/model when the original is infeasible; keep experiments distinct. |
| Market-data ingestion | Continue independent symbols/markets; change authorized provider, endpoint, archive granularity or trade-level construction; never fabricate or silently repair observations. |
| Parsing/schema/quality | Capture exact failing fixture and schema; test supported formats with deterministic tests; add regression coverage; do not drop malformed rows to pass. |
| CI/unit/synthetic tests | Read the exact failed assertion/log; repair the root cause; use a materially different available execution path only when runner/orchestration is the blocker; distinguish plumbing from empirical evidence. |
| Backtests/compute | Execute automatically once frozen code/data/methodology gates pass; chunk long jobs with immutable checkpoints and verified resume; retain elapsed-time/cost correctness. |
| Workflow dispatch/runner queues | Inspect existing runs first; do not duplicate; enforce 15-minute cancellation except a verified earlier active same-group predecessor; if cancellation fails, create a durable orphan incident and start one isolated alternative. |
| Artifacts/storage/reporting | Inspect and hash existing artifacts before re-running; use manifests, compact summaries and independent namespaces; preserve failed evidence and exact limitations. |
| Documentation/tasks/handoffs | Retire stale instructions without rewriting historical evidence; maintain one current task and actionable next step; check queue-guardian incidents each cycle. |
| Security/authorization/live actions | Stop only the specific protected action; complete all independent safe work; prepare the minimum prerequisite once; never evade the boundary. |

An alternative route must differ in a causal bottleneck-relevant way. Merely renaming a workflow, changing the run ID, rerunning the same request, or copying the same failing code into a new job is not adaptation. A new attempt must have a distinct identity and isolated working state. If a complete parallel attempt is unsafe, start a non-mutating independent slice rather than idling the whole repository.

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
