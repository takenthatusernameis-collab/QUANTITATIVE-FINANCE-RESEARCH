COMMIT TO REPOSITORY THE PENDING TASK

# Quantitative Finance Research Factory

**Start every agent cycle:** read the full [original agent-loop prompt](archive/ORIGINAL-AGENT-LOOP-PROMPT.md), then inspect the live GitHub state and the [canonical active queue](tasks/ACTIVE-QUEUE.md). Execute the prior task, verify the evidence, and commit a concrete successor task. A recommendation without a verified repository commit is not a completed handoff.

## Mission

Continuously improve the probability that each agent cycle produces trustworthy, reproducible, decision-useful quantitative-finance research. Negative and inconclusive findings are valid outcomes. The objective is not to manufacture profitable strategies or keep a model alive after its evidence fails.

## Mandatory project-selection rule

**Evidence and the actual operating environment come before hypothesis design.** First inherit both research/performance and technical-delivery feedback from the preceding task. Then inventory authorized data, coverage, point-in-time history, market semantics, costs, compute, APIs, storage, permissions, provenance and automation. Only then design and rank hypotheses that fit verified evidence.

- [Evidence-First Project Lifecycle](docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Asset-Universe Discovery and Scope Policy](docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md)
- [Documentation and Operating-Contract Index](docs/README.md)

## Current research state

The current assignment is still [First Scheduled Holdout Run Validation](tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md). Recheck Actions and the queue before acting; status here is only a navigation aid.

- Binance Spot mean-reversion: **NO-GO**, concluded November 22, 2026.
- ETH/BTC Spot relative-momentum rotation: **NO-GO**, concluded November 23, 2026; frozen and closed.
- Original USD-M funding-aware study: **INCONCLUSIVE**; funding inputs remain unaccepted.
- Prospective Binance Spot holdout capture: initial owner-authorized capture succeeded; first scheduled capture and sidecar/reconciliation verification are the current task. ETHUSDT/BTCUSDT are capture-specific symbols, not a factory-wide asset restriction.
- No live trading, capital deployment, strategy promotion or paid-data purchase is authorized by these research tasks.

## Governing standards

1. [General Antifragile Autonomous Operating Mindset](docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md)
2. [Evidence-First Project Lifecycle](docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
3. [Project Retrospective and Admin-Agent Calibration](docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
4. [Adaptive Autonomous Research Execution](docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md)
5. [Model Implementation Timebox Policy](docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)
6. [Repository Hygiene and Context Compaction](docs/REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md)
7. [ChatGPT-to-GitHub Dispatch](docs/CHATGPT-WORKFLOW-DISPATCH.md)

Detailed historical context from the former README is preserved in [the November 23 README snapshot](archive/README-HISTORICAL-2026-11-23.md). Historical queue entries are preserved in [the November 23 active-queue snapshot](archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).

## Repository map

| Path | Responsibility |
|---|---|
| `research/` | Data adapters, research logic, machine-checkable gates and deterministic tests |
| `tasks/` | Bounded project specifications; one canonical active queue pointer |
| `reports/` | Dated research results, audits, retrospectives and evidence handoffs |
| `docs/` | Governing policies and operational runbooks |
| `templates/` | Reusable project-intake and retrospective templates |
| `archive/` | Superseded instruction snapshots and original prompts |
| `.github/workflows/` | CI, research dispatch, holdout capture, cache and queue automation |

## Agent cycle contract

1. Inspect live branches, PRs, workflow runs, artifacts, queue incidents and current evidence.
2. Read the active task and predecessor feedback; do not duplicate or overlap work.
3. Assess the actual environment before selecting a new model or hypothesis.
4. Rank only feasible projects; assign evidence-backed difficulty, cycle budget and deadline before implementation.
5. Execute within authorization; preserve frozen criteria, independent holdouts and complete provenance.
6. Report research outcomes separately from tests/engineering results.
7. Calibrate repository-admin decisions from both feedback axes and commit one clear successor task.

The main-branch CI runs deterministic tests and a synthetic plumbing smoke test. These establish software behavior, not market-data acceptance or strategy profitability. See [research pipeline instructions](research/README.md).

## Security and reproducibility

External GitHub Actions are pinned to full commit SHAs with version comments; Dependabot proposes updates for review. Workflow jobs should use least-privilege permissions, exact actor/event/ref gates, bounded concurrency, content hashes and durable run manifests. No credentials, paid data, live exchange actions or protected holdout material may be introduced without the required authorization.
