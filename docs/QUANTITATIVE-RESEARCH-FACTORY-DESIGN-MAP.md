# Quantitative Research Factory — Production Design Map

**Status:** Canonical factory architecture and agent-cycle entry map.  
**Audience:** Every coordinator, research agent, engineering agent, reviewer and future automation worker.  
**Authority:** This map explains how the factory's work moves from an investment question to independently reviewable research evidence and then into a learning loop. It does not override the hard invariants or detailed policies linked below.

## Start here: the operating instruction

At every wake-up, behave as the coordinator of an evidence-producing research factory—not as a code generator waiting for a cron tick and not as an agent whose goal is to create another task or commit.

1. **Reconstruct reality.** Read this map, inspect the live default branch, recent commits, the canonical active queue, open issues/PRs, workflow executions, artifacts, incidents, credentials/permissions actually available, and the current task's last handoff. Treat repository prose as a pointer; verify live state.
2. **Clean before doing new work.** Perform the safe repository-hygiene preflight before substantive implementation: identify stale instructions, duplicate task pointers, disposable scratch/build output and confusing generated clutter. Preserve source data, manifests, checksums, logs, frozen preregistrations, decisions and all reproducibility evidence. Do not delete or rewrite active or historical evidence to make the tree look clean.
3. **Close the highest-value open loop.** Resume the existing critical-path task, recover or reconcile existing runs and artifacts, and resolve the most consequential blocker before inventing new work. Check for an already active or completed operation before dispatching anything.
4. **Plan adaptively.** State the current objective, evidence, uncertainty, constraints and stop conditions. For a material blocker, generate at least three materially different routes where useful, compare expected information gain, feasibility, cost, risk and reversibility, then select the strongest route. A route change must preserve the objective and scientific acceptance criteria; a changed research question requires a new experiment identity.
5. **Run the production line below.** Complete the stage gates; do not pass an unresolved data, scientific, security or operational defect downstream. Continue independent work only when dependency, holdout, write-scope, exclusive-resource and capacity checks pass.
6. **Verify and hand off.** Separate engineering, data, empirical and operational outcomes. Commit a small, coherent, validated change and an evidence-backed task handoff when repository changes are warranted. Do not manufacture a successor task or a documentation-only commit when the existing queue is already accurate and no substantive change occurred.

**A wake-up is complete only when it has made a verified contribution to the current objective, durably recorded a genuine blocker and its recovery route, or explicitly established that no safe/high-value action is available.** A passing unit test, a new task file, a commit count or a positive backtest is not a substitute for that standard.

**Missed-time rule:** when a time-sensitive slot or expected run is absent, mark operations `DEGRADED`, inspect the independent scheduler ledger, dispatch/API responses and watchdog evidence, and execute bounded idempotent recovery through the authorized external route. Never tell a user or the next agent to wait for another GitHub cron tick; never create a duplicate side effect to compensate for an ambiguous trigger.

## 1. Factory objective and governing design principles

The factory maximizes the rate at which it produces **trustworthy, reproducible, decision-useful quantitative-finance learning**. It does not maximize the number of backtests, commits, agents, workflows, positive results or lines of code. A valid negative or inconclusive result is useful when it retires uncertainty honestly.

The production system follows these principles:

- **Evidence before hypotheses:** establish the authorized information and execution environment before selecting a model. Unknown or inaccessible inputs do not become verified because a model needs them.
- **Quality at the source:** detect and stop on abnormal data, code, execution or research evidence before it contaminates later stages. Never hide defects with forward-fills, fabricated observations or weakened acceptance gates.
- **Small, reversible batches:** prefer focused changes that can be tested, reviewed, isolated and recovered independently. Integrate shared branches serially with expected-head protection.
- **Explicit flow and ownership:** every active workstream has an identity, accountable role, input/output contract, dependencies, write scope, exclusive resources, budget and expiry.
- **Independent verification:** the author of a confirmatory result must not be its only validator. Preserve blind holdouts and independent source evidence.
- **Autonomy with authorization:** remove routine human intervention, but never bypass explicit permission, least privilege, privacy, legal restrictions or financial-safety boundaries.
- **Adaptation without moving goalposts:** replace a failing provider, endpoint, pipeline or implementation when evidence justifies it; freeze the research question and acceptance criteria unless a new experiment is formally created.
- **Compounding improvement, bounded by evidence:** fix recurring causes and measure whether the fix improves throughput, reliability or research quality. Avoid endless process redesign and speculative infrastructure.

Hard invariants are vetoes over every optimization: security, legality, privacy, explicit authorization, least privilege, market/data integrity, provenance, causal and temporal correctness, reproducibility, independent holdouts, statistical honesty and no unauthorized live trading or capital deployment.

## 2. End-to-end production-line map

```mermaid
flowchart TD
    A[Question, opportunity or unresolved incident] --> B[Predecessor learning and live-state reconstruction]
    B --> C[Environment, data and execution capability inventory]
    C --> D{Authorized and evidence-feasible?}
    D -- No --> E[Bounded environment-enabling task or documented stop]
    E --> B
    D -- Yes --> F[Portfolio selection and workstream admission]
    F --> G[Preregister hypothesis, data, costs, tests and timebox]
    G --> H[Acquire, normalize and qualify data]
    H --> I{Data contract accepted?}
    I -- No --> J[Quarantine, diagnose and use a distinct recovery route]
    J --> H
    I -- Yes --> K[Implement reproducible model and deterministic tests]
    K --> L[Independent validation and robustness review]
    L --> M{Evidence supports a conclusion?}
    M -- No --> N[INCONCLUSIVE / INFEASIBLE with exact blocker]
    M -- NO-GO --> O[Close hypothesis; preserve negative evidence]
    M -- GO --> P[Research GO; deployment still requires separate authorization]
    P --> Q[If separately authorized: controlled release and monitoring]
    N --> R[Dual-axis retrospective and admin calibration]
    O --> R
    Q --> R
    E --> R
    R --> B

    subgraph Control plane — operates across every stage
      S[Coordinator, queue, WIP and per-workstream clocks]
      T[Independent scheduler, authenticated dispatch and durable ledger]
      U[Independent watchdog, alerts, leases and idempotent recovery]
      V[Versioned artifacts, provenance, CI and audit trail]
    end
    S -. governs .-> F
    T -. triggers .-> G
    T -. triggers .-> H
    U -. observes .-> T
    U -. observes .-> Q
    V -. records .-> K
    V -. records .-> L
```

The diagram is the logical flow, not a requirement to deploy every stage as a separate service or agent. Existing repository code and policies are the first implementation; new infrastructure is admitted only when a measured bottleneck justifies it.

## 3. Production stages, accountable role hats and release gates

A role is an **accountability hat**, not a mandatory separate agent. A single agent may cover several hats for a small, low-risk task. High-consequence boundaries—protected holdout evaluation, data acceptance, privileged execution and any future deployment—require independent checks or explicit owner authorization. Do not create a multi-agent committee where a deterministic test or an independent artifact review is sufficient.

| Stage | Primary role hat | Required input | Durable output | Exit gate / stop condition |
|---|---|---|---|---|
| 0. Opportunity and incident intake | Portfolio / factory coordinator | Live queue, user objective, incidents, prior findings, expected value of information | Ranked question or existing-task recovery decision | No duplicate task/run; a real unresolved question or bottleneck is identified |
| 1. Predecessor learning | Research lead + delivery/reliability reviewer | Prior research/performance results and technical-delivery evidence | Dual-axis retrospective and one evidence-backed admin calibration | Unknown prior outcomes are labelled unknown; failure causes and carry-forward lessons recorded |
| 2. Environment and opportunity mapping | Data/environment architect | Actual APIs, data rights, history, point-in-time coverage, market semantics, costs, compute, storage, network, permissions and execution routes | Verified capability matrix, limitations and feasible opportunity set | Required inputs/permissions are verified; otherwise create a bounded enabling task or stop |
| 3. Portfolio and flow control | Portfolio coordinator / queue manager | Feasible opportunities, dependencies, risk, resource capacity and workstream isolation | Canonical queue entry, priority, owner hats, WIP admission, timebox and expiry | No dependency inversion, duplicate experiment, holdout collision, overlapping writes or resource overcommit |
| 4. Research design | Quant research lead; independent design reviewer for confirmatory work | Verified environment and evidence-backed opportunity | Frozen preregistration: hypothesis, rationale, universe, timing, sample, features, benchmarks, costs, metrics, trials, controls, holdout, exclusions and stop rules | Experiment identity and acceptance criteria are frozen before result inspection or tuning |
| 5. Data acquisition and curation | Data engineer / data steward | Preregistered data contract and authorized sources | Immutable/raw source evidence, normalized dataset, schema, lineage, checksums and validation report | Product identity, coverage, semantics, timestamp alignment, duplicates, gaps, survivorship and provenance pass explicit checks; otherwise quarantine |
| 6. Model implementation | Quant developer / research engineer | Accepted dataset, preregistration, interface contracts | Versioned code, environment lock, run config, deterministic tests and reproducible execution manifest | Unit, property, boundary and integration tests pass; no look-ahead, future data or silent fallback |
| 7. Independent empirical validation | Independent quant reviewer / red team | Frozen code/config, accepted data, untouched holdout and full trial history | Benchmark-relative result, uncertainty, costs, robustness, leakage and multiple-testing review | Independent acceptance criteria pass; no post-hoc changes to the holdout or success threshold |
| 8. Research decision | Research decision owner / review board hat | Complete empirical and validation evidence | GO, NO-GO, INCONCLUSIVE or INFEASIBLE with rationale and evidence links | Empirical outcome is distinct from engineering and data status; time expiry alone is never NO-GO |
| 9. Release and operations (optional) | Release engineer + SRE / model-risk owner | Research GO plus separate operational, compliance and owner authorization | Versioned release, rollback plan, monitoring, incident response and permission record | No live orders, capital deployment or strategy promotion without separate explicit authorization |
| 10. Retrospective and factory improvement | Meta-process / calibration owner with stage owners | Research yield, delivery quality, incidents, toil, costs and bottleneck evidence | Updated causal diagnosis, tested process improvement or explicit no-change decision | Improvement is bounded, reversible where possible, regression-tested and measured after deployment |

### Role contracts

- **Portfolio / factory coordinator:** owns the canonical queue, priority, dependency graph, WIP limits and resource arbitration. Does not fabricate research evidence or override scientific gates.
- **Research lead / hypothesis designer:** owns the research question, preregistration, experiment identity, acceptance criteria and interpretation. Does not certify its own confirmatory result alone.
- **Data steward / data engineer:** owns source authorization, product identity, acquisition, schema, provenance, gap/duplicate checks, versioning and data acceptance. Cannot silently repair away market events or missing intervals.
- **Quant developer:** owns causal implementation, execution semantics, benchmarks, transaction-cost and funding assumptions, reproducibility and deterministic tests. Changes that alter the inference require a new experiment identity.
- **Independent validator / red team:** challenges leakage, selection bias, benchmark choice, trial accounting, statistical power, sensitivity, execution assumptions and holdout integrity. Has authority to stop the line and request evidence, not to tune against the protected sample.
- **Release / reliability engineer (SRE hat):** owns dispatch, observability, leases, retry behavior, alerting, artifact durability, rollback, security hardening and operational runbooks. A green CI badge is not a successful production run.
- **Meta-process owner:** turns recurring failure and toil into measured, tested improvements; prevents duplicated policies and process bloat. Does not optimize process metrics at the expense of research validity.

## 4. Stage contracts and scientific gates

### 4.1 Intake, predecessor feedback and environment first

Before a new hypothesis is designed, review both feedback axes: (a) research/performance/evidence yield, including an explicit statement when no empirical result was obtained; and (b) technical delivery, including data acceptance, reliability, runtime, failed routes, manual interventions, reproducibility, queueing and handoff quality. Record at least one evidence-backed repository-admin calibration decision and how its effect will be measured.

Inventory actual authorized data and tools, not hoped-for access: source/product identity, terms and permissions, history and inception, point-in-time availability, constituents/universe, delistings/corporate actions where relevant, market type, timestamps, units, event semantics, missingness, quality, transaction costs, borrow/funding, compute, storage, network, rate limits, provenance and independent execution control. Mark each item `VERIFIED`, `PARTIAL`, `UNKNOWN`, `RESTRICTED` or `FAILED` with evidence. A hypothesis may depend only on verified required inputs or on a separately authorized, timeboxed environment-enabling task.

Asset discovery is open-ended by default. Prior pairs, venues, examples, cached samples and project-specific capture symbols are not a factory-wide whitelist. Fixed universes require a question-specific, preregistered rationale and inclusion/exclusion policy.

### 4.2 Portfolio allocation, WIP and timeboxes

Prioritize expected information gain and research decision value, adjusted for feasibility, cost, risk, urgency, reversibility and opportunity cost. Resolve existing work and incidents before creating another project. Run independent workstreams in parallel only after checking completed dependencies, unique experiment identity, disjoint write paths, exclusive-resource reservations, holdout isolation and measured compute/network/API capacity.

Each active workstream has a stable ID, objective, accountable owner hat, independence rationale, dependencies, write scope, exclusive resource keys, protected data/holdout IDs, start time, difficulty assessment, maximum substantive cycles, exact UTC expiry, current cycle count and terminal rule. Use the tested workstream-policy functions. The earlier of cycle limit or expiry controls; handoffs and CI queues do not reset the clock. A blocked dependent successor remains queued. Do not enforce an arbitrary global agent count or active-task ceiling; enforce real resource limits and prevent critical-path starvation.

### 4.3 Preregistration and experiment identity

Freeze before inspecting confirmatory results: question, mechanism, assets/instruments, venue/market, sampling frequency, feature and signal definitions, event-time rules, execution assumptions, latency/slippage/fees/funding/borrow, benchmark, sample windows, training/validation/test splits, exclusion rules, metrics, uncertainty method, robustness tests, trial count, multiple-testing treatment, acceptance thresholds, stop conditions and allowed revisions.

A materially changed hypothesis, universe, market construction, timeframe or inference target receives a new experiment ID and fresh independent acceptance criteria. Maintain a ledger of every attempted variant; do not report only the best result. The same OOS/holdout sample must not be reused for unconstrained tuning.

### 4.4 Data contract and acceptance

Keep raw source evidence separate from normalized/derived datasets. Record exact source, retrieval time, request parameters, product identifiers, license/authorization basis, timezone, bar conventions, units, schema/version, row counts, expected coverage, checksums/content hashes and transformation code. Validate positive controls (known active products/times) and negative controls (known missing/invalid products/times), pagination, rate limits, partial responses, ordering, duplicates, gaps, outliers, revisions and cross-source agreement as appropriate.

Never forward-fill, interpolate, infer zero returns, silently splice venues, assume stablecoin parity or silently drop unresolved missing intervals. Any multi-venue combination requires an explicit, preregistered and tested reconciliation methodology. Corrections must be explicit, source-backed, versioned and auditable. A successful download, HTTP 200, API acceptance or non-empty file is not data acceptance.

### 4.5 Implementation and reproducibility

Keep code, tests, configuration, environment, data manifests and outputs tied to a specific commit and experiment identity. Use deterministic fixtures, property/invariant tests, positive/negative controls, explicit failure modes and bounded integration smoke tests. Pin external actions and dependencies where the repository policy requires it; use least privilege, untrusted-input validation, safe shell/API handling and secrets managers rather than committed credentials.

Build the smallest representative slice first, then scale with bounded/resumable acquisition and idempotent writes. Preserve exact errors, response codes, parameters, time windows, source hashes and failing stage. After the first meaningful failure, diagnose and propose a materially different route; after two independent occurrences of the same non-transient failure on one route, stop repeating that route unchanged.

### 4.6 Independent quantitative validation

Respect time ordering. Use walk-forward or rolling-origin evaluation where appropriate; never use random shuffling when it leaks future information. Use purging/embargo where overlapping labels or horizons require it. Keep benchmarks, transaction costs, slippage, liquidity/capacity and execution timing realistic. Report gross and net returns, drawdowns, turnover, exposure, tail/risk metrics, uncertainty and relevant regime/asset breakdowns.

Account for all trials and selection. Apply methods appropriate to the experiment—e.g. Probability of Backtest Overfitting (PBO), Deflated Sharpe Ratio (DSR), multiple-testing controls, bootstrap/stationarity diagnostics and sensitivity analyses—rather than treating a conventional holdout as sufficient in every setting. No single metric is universal; document assumptions and limitations. Independent validators inspect the code/config, split logic, execution model and full trial history, not just the headline return.

### 4.7 Four orthogonal outcome axes

Never collapse these into one green/red status:

| Axis | Example states | What it establishes |
|---|---|---|
| Engineering | PASS / FAIL / INCOMPLETE | Code and tests behave as specified |
| Data | ACCEPTED / REJECTED / PARTIAL / UNVERIFIED | Inputs meet the declared data contract |
| Empirical research | GO / NO-GO / INCONCLUSIVE / INFEASIBLE | Frozen hypothesis has a defensible research conclusion |
| Operations | DELIVERY_VERIFIED / DEGRADED / UNCONFIGURED / RECOVERED | The real trigger-to-artifact-to-watchdog operating path works |

An engineering PASS does not accept data, validate a strategy or prove scheduler delivery. A strategy NO-GO requires valid empirical evidence against frozen criteria. Missing inputs, infeasible execution or a timebox expiry produce INCONCLUSIVE/INFEASIBLE, not NO-GO. A research GO is not permission to trade or deploy capital.

## 5. Orchestration and reliability control plane

### 5.1 Event-driven execution is not the same as reliable time scheduling

**Never use GitHub Actions `schedule`/cron as the primary clock, sole trigger, deadline guarantee, recovery plan or heartbeat.** GitHub documents it as best-effort; runs can be delayed or dropped. A valid cron expression, workflow on `main`, successful manual execution, recent push or green CI is not proof that the next scheduled operation will be delivered. GitHub cron may be retained only as an opportunistic canary when its side effects are idempotent and it cannot race an external dispatcher.

For every time-sensitive, freshness-sensitive or deadline-bound operation, require this control-plane chain:

1. An **independent external scheduler** in a separate scheduling/control domain evaluates the expected slot/deadline.
2. It acquires a durable lease and computes a deterministic slot identity/idempotency key (e.g. workstream + UTC date + interval + data contract version).
3. It dispatches through an authenticated, least-privilege route. For GitHub, prefer a dedicated repository-scoped GitHub App installation token with only the required Actions permission; store it only in the external secret manager. Verify the actual resulting `github.actor` before changing allowlists. Never assume a bot identity, broaden an actor allowlist speculatively, or weaken an existing actor/ref/event gate to force delivery. Never commit, print or place long-lived secrets in repository files, workflow inputs or logs; keep them only in an authorized external secret manager.
4. A durable dispatch ledger records expected slot, due time, credential/actor identity (never secret), attempt number, API response, run ID, workflow ID/path, ref/SHA, dispatch/start/completion time, artifacts and final disposition.
5. The dispatcher observes the exact GitHub run and verifies event, actor, default-branch ref, slot key, workflow identity, jobs, outcome and outputs. An HTTP 2xx or accepted dispatch is not completion.
6. Retries use bounded backoff and first search for an already-created run with the same key. The delivery mechanism may be at-least-once; the side effect must be effectively-once through durable idempotent reconciliation. Ambiguous acceptance must never produce a blind duplicate capture.
7. A **separate independent watchdog** in a different failure domain observes expected slots, queue age, heartbeat/freshness, run completion and artifact publication. It raises durable incidents/alerts for missing, stuck, failed or partial work. It must not depend on the same GitHub cron or the same scheduler process it is monitoring.
8. Recovery reconciles the same slot and evidence exactly once; it never fabricates market data, bypasses permissions or weakens scientific acceptance.

`workflow_run` is useful for a completion handoff after a real workflow has run; it is not an independent clock. A control-PR/issue-comment route is an event-driven command surface, not a general deadline scheduler. If no independent scheduler, credential or permission is available, mark the operation `UNCONFIGURED`/`DEGRADED`, identify the exact owner-only prerequisite, continue independent safe work, and do not represent the process as autonomously scheduled.

### 5.2 Operational state machine

- `UNCONFIGURED`: no independent scheduler/dispatcher or required authority exists.
- `DISPATCH_READY`: scheduler, credential, actor gate, slot contract, durable ledger and watchdog are configured but end-to-end delivery is not proven.
- `DELIVERY_VERIFIED`: an end-to-end test proves expected slot → authenticated dispatch → observed correct run → completed work → durable output → independent watchdog observation.
- `DEGRADED`: a deadline was missed, dispatch is ambiguous, run is stuck/failed/partial, output is missing or monitor is unhealthy. Keep dependent data and strategy gates closed.
- `RECOVERED`: the original slot is safely reconciled through idempotent recovery and all required evidence is independently verified.

Unit tests, synthetic smoke tests, a manual owner run, workflow configuration and successful repository pushes cannot promote the operating state to `DELIVERY_VERIFIED`.

### 5.3 Queue, concurrency and recovery

Use the canonical active queue as the portfolio board. Make ownership, blockers, due times, priorities, dependencies, evidence locations and resource reservations visible. Prefer event-driven handoffs and durable job/slot state over polling-only loops. Keep queue guardian or automation as a policy-enforcement tool, not an assumed clock. Avoid cancellation races, unsafe concurrency, orphaned runs and ambiguous retries. Before dispatch, inspect queued/in-progress/completed attempts and artifacts. For shared mutable resources, use explicit leases/locks and idempotency; for Git writes, use expected-head updates.

Every event that can change durable state must be auditable: who/what initiated it, why it was authorized, which inputs and versions were used, what changed, and what output was produced. Alert on missing expected output, not merely on an exception inside a process that may never have started.

## 6. Failure, stop-the-line and adaptation protocol

Apply a research-factory form of **jidoka**: stop the affected line at the first material abnormality; do not let a defective input, unauthorized action or invalid result flow into the next stage. Isolate the failed workstream or component while allowing independent safe work to continue.

For every material failure:

1. Capture evidence: stage, timestamp, run/slot/experiment ID, actor, commit, inputs, request parameters, status/exception, logs, artifact IDs/hashes and impact.
2. Classify root cause: trigger/scheduler delivery, authorization, infrastructure, transient transport, provider restriction, missing data, schema/semantics, implementation, statistical design, model assumption, resource contention or handoff.
3. State what the evidence rules out and what remains unknown. Do not label an unstarted workflow a capture-job failure.
4. Produce at least three genuinely distinct options when the issue is material: repair current component, use a different authorized route/provider/architecture, or explicitly stop/replace the experiment. Compare feasibility, information gain, security, cost, timebox and reversibility.
5. Pilot the cheapest discriminating test with positive and negative controls; add regression tests for the root cause. Preserve the failed path as evidence.
6. Implement the safest materially different fix within authority. If an external permission or secret is unavailable, complete all independent work and state the exact owner prerequisite rather than bypassing it.
7. Measure the result after deployment. Keep, revise or roll back based on evidence; update the canonical runbook/test and predecessor feedback.

After two independent occurrences of the same non-transient error on the same route, stop retrying that route unchanged. A changed provider, data construction, trigger, runtime or hypothesis must be materially different, not merely renamed. A research failure, data-access failure and operational-delivery failure must remain distinct in reports and statuses.

## 7. Recursive compounding and factory scorecard

The improvement loop is **observe → identify the binding constraint → design competing interventions → implement one bounded change → test → release → measure → retain or roll back → codify learning**. Prefer improvements that remove a recurring manual step, eliminate a class of defects, shorten a verified bottleneck or increase independently validated research yield. Do not promote a policy to factory-wide status from one anecdote unless it addresses a clear hard invariant; otherwise pilot it and measure recurrence.

Track a small, interpretable scorecard by workstream and over time:

| Dimension | Example measures | Anti-gaming rule |
|---|---|---|
| Research value | Evidence-backed GO/NO-GO/INCONCLUSIVE decisions; accepted data products; uncertainty retired; independent replication | Positive returns and raw backtest count are not productivity measures |
| Flow | Lead/cycle time by stage; queue age; blocked time and cause; WIP; handoff latency; time from question to defensible decision | Do not improve averages by abandoning hard tasks or hiding blocked time |
| Delivery stability | Failed change rate, rework rate, recovery time and deployment/change lead time | Pair throughput with instability; smaller batches and fast rollback beat release-count targets |
| Scheduler/operations | Expected-slot delivery rate, dispatch-to-run latency, missing-run detection time, artifact completeness, duplicate side effects, recovery time, monitor availability | Measure the end-to-end chain; workflow YAML and cron ticks alone are not reliability |
| Scientific integrity | Provenance completeness, data-contract defect escape, leakage/holdout incidents, trial accounting, independent reproduction rate | Never reward a high pass rate by relaxing acceptance criteria |
| Autonomy/toil | Routine human interventions, repeated manual steps, toil hours, self-service recovery rate | Human intervention is acceptable for genuinely privileged owner decisions, not routine orchestration |
| Resource efficiency | Compute/API/storage cost per validated decision, cache hit rate, provider utilization, rework cost | Optimize cost subject to quality and coverage, never by dropping necessary controls |

Use DORA's delivery-throughput and stability measures as a software-engineering lens, not as a proxy for investment research performance. Use SRE-style service indicators/objectives and alerting for the scheduling, dispatch, artifact and monitoring chain. Track repetitive operational toil and automate it when safe. For research reproducibility, make data, code, environment and run provenance easy to inspect and reproduce.

Do not set arbitrary universal numeric targets before establishing baselines and service criticality. Define service-level indicators from actual expected-slot contracts, acceptable lateness, data freshness and impact. Review metrics for unintended incentives; do not optimize any single metric in isolation. Improvement work itself needs an owner, workstream ID, expected measurable benefit, cost ceiling, test, expiry and rollback/stop rule.

## 8. Handoff and completion contract

Every substantive workstream handoff must make the next safe action unambiguous. Record:

- stable workstream/experiment/slot IDs and current stage;
- current status on each of the four outcome axes;
- objective, frozen acceptance criteria and actual scope;
- commits, branch/ref, environment and exact commands/run IDs;
- data sources, versions, request windows, manifests, checksums and artifact links;
- tests and their precise scope (unit, integration, synthetic, data acceptance, empirical validation, operational delivery);
- outcomes, failures, rejected routes, uncertainty and unresolved dependencies;
- changes to permissions/credentials (normally none), resource reservations and holdout boundaries;
- difficulty, cycle count, start/expiry/deadline and stop condition;
- next action, owner hat, prerequisites, recovery path and what must not be repeated.

Keep one canonical queue pointer. Put reusable operating rules in `docs/`, bounded requirements in `tasks/`, evidence and dated checkpoints in `reports/`, implementation/tests in `research/`, and superseded snapshots in `archive/`. Do not duplicate the same policy in several locations; link to the authority. A clean handoff does not require a new task if the queued work is unchanged. A recommendation without inspectable evidence is not a completed deliverable.

## 9. Repository implementation map

| Factory capability | Current repository home | Governing contract / notes |
|---|---|---|
| Cycle entry and architecture | `README.md`, this document | This map is the canonical wake-up and production-line view |
| Portfolio / WIP state | `tasks/ACTIVE-QUEUE.md` | One canonical index; independently admitted workstreams each have their own expiry |
| Preregistration and bounded work | `tasks/` | Use stable experiment IDs, frozen criteria, cycle/timebox and explicit stop conditions |
| Research decision logic | `research/adaptive_decision.py`, `research/project_readiness.py` | Tested evidence gates and feasible-project classification |
| Parallel workstream admission | `research/workstream_policy.py` | Tested dependency, isolation, resource and expiry checks |
| Data and model implementations | `research/` | Keep source semantics, lineage and reproducibility explicit |
| Deterministic and regression tests | `research/test_*.py` | Tests establish code behavior, not data acceptance or strategy profitability |
| Workflow/dispatch surfaces | `.github/workflows/` | Least privilege, exact actor/ref/event gates; GitHub cron is never authoritative |
| Queue guardian | `.github/workflows/queue-guardian.yml`, `research/queue_guardian.py` | Enforcement/inspection and event handoff; not a guaranteed scheduler |
| External scheduler policy | `docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md` | Independent dispatcher, durable ledger, slot idempotency and separate watchdog are mandatory for time-sensitive operations |
| Detailed operating standards | `docs/` | The policies below remain the detailed source of truth |
| Evidence, incidents and retrospectives | `reports/` | Dated, inspectable, hash-linked outputs; no raw data in Git unless policy permits |
| Historical context | `archive/` | Preserve prior prompts and superseded state; never treat archived text as current instruction |

## 10. Governing documents and evidence base

Read the linked operating contracts for detail; this map is the navigation and assembly-line layer, not a substitute for their acceptance rules:

1. [General Antifragile Autonomous Operating Mindset](GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md)
2. [Evidence-First Project Lifecycle](RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
3. [Asset-Universe Discovery and Scope Policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md)
4. [Project Retrospective and Admin-Agent Calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
5. [Adaptive Autonomous Research Execution](ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md)
6. [Parallel Research Workstreams and Per-Workstream Expiry Policy](PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md)
7. [Model Implementation Timebox Policy](MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)
8. [Repository Hygiene and Context Compaction](REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md)
9. [ChatGPT-to-GitHub Dispatch](CHATGPT-WORKFLOW-DISPATCH.md)
10. [External Scheduler and Dispatch Reliability](EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md)

The following expert sources support individual design practices; they do **not** prove that one fixed multi-agent architecture is universally optimal:

- [Toyota Production System](https://global.toyota/en/company/vision-and-philosophy/production-system/): jidoka (stop when abnormalities are detected), just-in-time flow and continuous kaizen.
- [DORA software delivery performance metrics](https://dora.dev/guides/dora-metrics/): measure throughput and instability together; its current five measures are change lead time, deployment frequency, failed-deployment recovery time, change fail rate and deployment rework rate.
- [Google SRE Workbook — Eliminating Toil](https://sre.google/workbook/eliminating-toil/) and [Monitoring](https://sre.google/workbook/monitoring/): measure repetitive operational work; use timely metrics and alerting to detect failures and expose root causes.
- [The Turing Way](https://book.the-turing-way.org/): reproducible, ethical and collaborative data science, including project design and provenance practices.
- [GitHub Actions schedule event behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) and [workflow dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): distinguish best-effort event scheduling from authenticated, observable dispatch.
- [Bailey et al., Probability of Backtest Overfitting](https://doi.org/10.21314/JCF.2016.322) and [Bailey & López de Prado, Deflated Sharpe Ratio](https://doi.org/10.3905/jpm.2014.40.5.094): account for selection bias and multiple trials when evaluating investment simulations.
- [Forecasting: Principles and Practice — Time Series Cross-Validation](https://otexts.robjhyndman.com/fpp3/toolbox.html): preserve temporal order using rolling forecast origins where appropriate.

The practical implication is a **modular, evidence-gated, low-toil production line with stop-the-line quality, independent verification, explicit flow ownership and a measured kaizen loop**. It is not a requirement to create a large hierarchy, spawn agents for every role or install a new platform before the need is demonstrated.
