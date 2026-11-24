# Quantitative Finance Research Factory

**Start every agent cycle:** use the [Quantitative Research Factory — Production Design Map](docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) as the canonical wake-up and production-line architecture, then inspect live GitHub state and the [canonical active queue](tasks/ACTIVE-QUEUE.md). Resume the highest-priority active work, perform safe repository hygiene before substantive changes, and verify the gates for each stage. Update the queue and commit only when there is a real, verified state change; do not manufacture a task or commit to satisfy a ritual. A completed claim requires an inspectable artifact, decision or handoff.

## Mission

Continuously improve the probability that each agent cycle produces trustworthy, reproducible, decision-useful quantitative-finance research. Negative and inconclusive findings are valid outcomes. The objective is not to manufacture profitable strategies or keep a model alive after its evidence fails.

## Mandatory project-selection rule

**Evidence and the actual operating environment come before hypothesis design.** First inherit both research/performance and technical-delivery feedback from the preceding task. Then inventory authorized data, coverage, point-in-time history, market semantics, costs, compute, APIs, storage, permissions, provenance and automation. Only then design and rank hypotheses that fit verified evidence.

- [Evidence-First Project Lifecycle](docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Asset-Universe Discovery and Scope Policy](docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md)
- [Parallel Research Workstreams and Per-Workstream Expiry Policy](docs/PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md)
- [Documentation and Operating-Contract Index](docs/README.md)

## Current research state

The current assignment is still [External Dispatch and Recovery Validation](tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md). Recheck Actions and the queue before acting; status here is only a navigation aid.

- Binance Spot mean-reversion: **NO-GO**, concluded November 22, 2026.
- ETH/BTC Spot relative-momentum rotation: **NO-GO**, concluded November 23, 2026; frozen and closed.
- Original USD-M funding-aware study: **INCONCLUSIVE**; funding inputs remain unaccepted.
- Prospective Binance Spot holdout capture: initial owner-authorized run [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210) succeeded via `issue_comment`; the GitHub Actions `schedule` event due 2026-11-24 04:23 UTC did not create a capture run. The latest-100 Actions inventory (536 total runs) contained eight runs created after 04:23 UTC: seven research-test pushes and one queue-guardian schedule run, with none from `spot-holdout-capture.yml`; separate status queries found zero queued and zero in-progress runs. The latest main CI [45360167229](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45360167229) passed 304 deterministic tests in 14.748 seconds and the synthetic plumbing smoke test on commit `d4a451b`; two preceding CI attempts failed on authorization-assertion regressions and were superseded by this passing correction. Release `spot-holdout-2026` still contains only ZIP asset 784136576 (63,517 bytes; SHA-256 `b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`); no second snapshot or JSON sidecar exists and `immutable=false`. GitHub documents scheduled triggers as best-effort; they are non-authoritative and must never be treated as a timing guarantee. An independent authenticated dispatcher plus idempotency and a separate watchdog is required; it is not yet provisioned or verified. Do not wait for the next GitHub cron tick or create a duplicate capture. See [external scheduler policy](docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md) and [scheduled-run checkpoint](reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md). ETHUSDT/BTCUSDT are capture-specific symbols, not a factory-wide asset restriction.
- No live trading, capital deployment, strategy promotion or paid-data purchase is authorized by these research tasks.

## Governing standards

1. [General Antifragile Autonomous Operating Mindset](docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md)
2. [Evidence-First Project Lifecycle](docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
3. [Project Retrospective and Admin-Agent Calibration](docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
4. [Adaptive Autonomous Research Execution](docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md)
5. [Parallel Research Workstreams and Per-Workstream Expiry Policy](docs/PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md)
6. [Model Implementation Timebox Policy](docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)
7. [Repository Hygiene and Context Compaction](docs/REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md)
8. [ChatGPT-to-GitHub Dispatch](docs/CHATGPT-WORKFLOW-DISPATCH.md)
9. [External Scheduler and Dispatch Reliability](docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md)

Detailed historical context from the former README is preserved in [the November 23 README snapshot](archive/README-HISTORICAL-2026-11-23.md). Historical queue entries are preserved in [the November 23 active-queue snapshot](archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).

## Repository map

| Path | Responsibility |
|---|---|
| `research/` | Data adapters, research logic, machine-checkable gates and deterministic tests |
| `tasks/` | Bounded project specifications and one canonical queue pointer; multiple independent active workstreams may run with separate expiries |
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
7. Calibrate repository-admin decisions from both feedback axes; update the canonical queue only when task state genuinely changes, and do not manufacture successor tasks or commits.

The main-branch CI runs deterministic tests and a synthetic plumbing smoke test. These establish software behavior, not market-data acceptance or strategy profitability. See [research pipeline instructions](research/README.md).

## Security and reproducibility

External GitHub Actions are pinned to full commit SHAs with version comments; Dependabot proposes updates for review. Workflow jobs should use least-privilege permissions, exact actor/event/ref gates, bounded concurrency, content hashes and durable run manifests. No credentials, paid data, live exchange actions or protected holdout material may be introduced without the required authorization.


## Direct-agent recovery rule

Deterministic automation is preferred, but it is never the only path to progress. After a task's declared due time, the first authorized agent wake-up must inspect the durable state and directly resume missing work through the strongest already-authorized route, with the same tests, provenance, acceptance criteria and idempotency controls. Do not wait for GitHub cron or another unreliable trigger. See the [factory design map](docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) and [scheduler reliability policy](docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md).
