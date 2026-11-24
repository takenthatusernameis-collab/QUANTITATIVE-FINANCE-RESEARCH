# Repository Overview and Current Research Status

> This document contains the substantive overview and research-status material moved out of `README.md` on 2026-11-24. The stable scheduled-automation entry point remains [`README.md`](README.md). For the authoritative assembly-line architecture and wake-up procedure, follow the [Quantitative Research Factory — Production Design Map](docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md). This overview is a navigation/context snapshot; verify changing state against the live [active queue](tasks/ACTIVE-QUEUE.md), workflows and artifacts.

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

The current active assignment is [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](tasks/BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md) — an environment-enabling project, MEDIUM difficulty, cycle 2 of 4, started 2026-11-24 12:28:44 UTC and expiring 2026-11-29 12:28:44 UTC. It has verified the full current 3,751-symbol catalogue and a bounded direct-archive sample, but archive-index pagination, complete historical symbol lifecycle and universe-wide archive coverage remain unverified. No strategy is ready and no successor strategy is admitted.

- Binance Spot mean-reversion: **NO-GO**, concluded November 22, 2026.
- ETH/BTC Spot relative-momentum rotation: **NO-GO**, concluded November 23, 2026; frozen and closed.
- Original USD-M funding-aware study: **INCONCLUSIVE**; funding inputs remain unaccepted.
- Prospective Binance Spot holdout capture: the 2026-11-24 04:23 UTC GitHub cron did not fire. The first authorized agent wake-up used the existing exact-owner PR #2 command and recovered the due slot via [capture run 45373419544](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544); the exact actor and authorization gate passed. The resulting [snapshot-slot-2026-11-24.zip](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-slot-2026-11-24.zip) (asset 786684218, 65,817 bytes, SHA-256 `22bd362b7c0db51c7a3302f5b09c1a4a2327a4d9553b8ac7259f2a343c5caade`) and [JSON sidecar](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-slot-2026-11-24.manifest.json) (asset 786684257, 5,211 bytes, SHA-256 `57cb7b1d297c15a33aa80784a0b72e010988e3da99a0e65171174ce02e19d284`) are published. The run reports 562 complete hourly rows each for ETHUSDT and BTCUSDT through the 2026-11-24 09:00 UTC bar, with zero missing hours, duplicates, overlap corrections or source errors. The original ZIP's sidecar was backfilled (asset 786684146); its original ZIP asset 784136576 was preserved. A second same-slot wake-up [run 45373703705](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373703705) returned `idempotent_slot_reuse=true`, reused the exact ZIP/sidecar IDs and created no additional Release assets. The latest main CI [45375425738](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45375425738) passed 324 deterministic tests and the synthetic plumbing smoke test on `842abf6`, including the generalized direct-agent fallback regression; the three post-capture queue-guardian handoffs succeeded. Release metadata remains `immutable=false`. External scheduler and separate watchdog remain **UNCONFIGURED / DEGRADED**; this slot is **RECOVERED** by the first-agent fallback, but external scheduler delivery is not `DELIVERY_VERIFIED`. No strategy evaluation was run. See [scheduler policy](docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md) and [final capture checkpoint](reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md). ETHUSDT/BTCUSDT are capture-specific symbols, not a factory-wide asset restriction.
- The [Post-Holdout Research Environment and Portfolio Review](reports/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW-2026-11-24.md) completed after one LOW-tier cycle. It found no strategy ready from the verified evidence envelope and selected the bounded dynamic-universe/archive feasibility audit as the next environment-enabling task. See the report for the 11-dimension environment matrix, provider dispositions and admin-agent calibration.
- The active [Binance Spot Dynamic-Universe audit checkpoint](reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md) verifies 3,751 current catalogue symbols and four of five sampled monthly archive files. A non-exhaustive cross-check found 105 of 106 sampled 2023–2026 removed pairs in current exchangeInfo as BREAK and one relisted pair as TRADING; this does not establish complete historical membership. Archive-index pagination and universe-wide historical coverage remain UNKNOWN. The next bounded step is an official announcement-history/pagination check; no strategy may start until the required lifecycle and archive dimensions are VERIFIED.
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

## Agent-cycle authority

The complete wake-up sequence, production-line stages, role contracts, inputs/outputs, stage gates, orchestration and handoff requirements are maintained in the [canonical production design map](docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md). This overview intentionally does not maintain a second copy of that operating contract.

## Security and reproducibility

External GitHub Actions are pinned to full commit SHAs with version comments; Dependabot proposes updates for review. Workflow jobs should use least-privilege permissions, exact actor/event/ref gates, bounded concurrency, content hashes and durable run manifests. No credentials, paid data, live exchange actions or protected holdout material may be introduced without the required authorization.


## Direct-agent recovery reference

The authoritative first-authorized-agent fallback, idempotency and scheduler/watchdog requirements are maintained in the [production design map](docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) and [external scheduler reliability policy](docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md). This overview links to those canonical rules rather than duplicating them.
