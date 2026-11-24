# Active Repository Queue

**Updated:** 2026-11-24  
**Canonical queue:** this file remains the single active-work index; it may contain one primary critical-path task plus independently admitted parallel workstreams.  
**Primary active workstream:** [First Scheduled Holdout Run Validation](PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md).  
**Additional admitted parallel workstreams:** none currently. The new policy enables safe parallel work but does not itself create or dispatch another task.  
**Queued successor (not active until current task closes):** [Post-Holdout Research Environment and Portfolio Review](POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md).

## Repository governance upgrade — completed 2026-11-24

The evidence-first lifecycle, dual-axis retrospectives, tested project-readiness gate, documentation index, action SHA pinning, grouped dependency updates, per-ref CI deduplication and parallel-workstream admission/timebox policy are committed. See [governance implementation retrospective](../reports/EVIDENCE-FIRST-RESEARCH-GOVERNANCE-IMPLEMENTATION-2026-11-24.md) and [parallel-workstream policy](../docs/PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md). Latest main CI [45339112663](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45339112663) passed deterministic tests and the synthetic plumbing smoke test; the preceding full run [45327618205](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45327618205) passed 300 deterministic tests in 14.670 seconds.

## Current active assignment

**Priority:** P1 — prospective research-data infrastructure.  
**Budget:** one substantive cycle.  
**Hard deadline:** 2026-11-25 17:30 UTC.

The first daily Binance Spot capture's GitHub Actions cron was due **2026-11-24 04:23 UTC** but created no capture run. A fresh Actions inventory contains five runs created after that time and none from `spot-holdout-capture.yml`; the only scheduled run in that post-deadline inventory was queue guardian [45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900). GitHub documents `schedule` as best-effort, so this cron is not an operational clock, deadline guarantee or recovery plan. The initial owner-authorized capture [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210) succeeded via `issue_comment`; release `spot-holdout-2026` still contains only ZIP asset 784136576 (63,517 bytes; SHA-256 `b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`), with no second snapshot or JSON sidecar and `immutable=false`. An independent authenticated scheduler/dispatcher, per-slot idempotency and a separate watchdog are mandatory. They are not yet provisioned or verified; no connected direct workflow-dispatch API or scheduler credential is available in this execution path. **Do not wait for the next GitHub cron tick.** Keep the holdout closed until a genuinely external dispatch is observed and fully reconciled. Latest main CI [45347499234](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45347499234) passed on commit `1890e63`. See [external scheduler policy](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md), [scheduled-run checkpoint](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md), and the active task.

**Scope restrictions:** no strategy backtest, no tuning of the closed Spot Momentum experiment, no unaccepted funding data, no paid data/key purchase, no venue merge and no live trading.

**Asset-universe boundary:** ETHUSDT/BTCUSDT are the two symbols of this capture-validation task only. They do not define or restrict the factory's future asset universe. Future research discovery must follow [the open asset-universe policy](../docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md).

### Primary workstream isolation record

| Field | Current value |
|---|---|
| Workstream ID / status | `spot-holdout-first-scheduled-validation` / active |
| Write scope | `tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md`; `tasks/ACTIVE-QUEUE.md`; `README.md`; `reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-CAPTURE-2026-11-23.md`; `reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md`; `.github/workflows/spot-holdout-capture.yml`; `research/spot_holdout_capture.py`; `research/test_spot_holdout_capture.py` |
| Exclusive resources | `github-actions:spot-holdout-capture`; `github-release:spot-holdout-2026`; `binance-spot-capture:1h` |
| Confirmatory holdout ID | `binance-spot-1h:prospective-2026-11` |

This pre-policy assignment retains its original one-substantive-cycle budget and 2026-11-25 17:30 UTC deadline in the task file. Its clock is not reset or retrospectively re-rated. Do not admit another workstream that overlaps these paths, reserves the same exclusive resources, or consumes this confirmatory dataset outside a jointly preregistered evaluation with multiplicity control.

## Research-track status

| Workstream | Status | Rule |
|---|---|---|
| ETH/BTC Spot mean-reversion | NO-GO, closed | Do not reopen or tune on the same OOS sample. |
| ETH/BTC Spot relative momentum | NO-GO, closed | Do not tune on the same OOS sample. |
| USD-M funding-aware study | INCONCLUSIVE | Keep funding inputs provisional/unaccepted; no perp backtest. |
| Prospective Binance Spot capture | Initial capture passed; scheduled validation pending | Data infrastructure only; no strategy evaluation. |

## Successor sequencing

After the active holdout-validation task is closed, execute the queued environment/portfolio review. It must consume both feedback axes from the completed task and the prior empirical conclusions, then establish the verified information and infrastructure envelope. **No successor model is selected in advance.** If no candidate fits verified evidence, queue a bounded environment-enabling project or record that no new model is justified.

All successor work must satisfy:
- [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Model Implementation Timebox Policy](../docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)

## Current automation observations to recheck

- Capture trigger: GitHub cron `23 4 * * *` is best-effort only and is not the primary clock. The 2026-11-24 event did not create a capture run. Do not wait for the next cron boundary. External authenticated dispatch, per-slot idempotency and a separate watchdog are mandatory before this pipeline can be considered autonomously scheduled; these are not yet provisioned or verified. The existing owner-controlled `workflow_dispatch` and exact PR-comment routes remain gated; do not weaken actor checks.
- Queue guardian: configured with a five-minute cron plus qualifying workflow_run handoffs. The latest observed run remains [45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900), scheduled at 05:37:22–05:37:45 UTC in LIVE_ENFORCEMENT mode on main. Its report artifact [14893776351](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900) was independently downloaded and inspected: enumeration completed across 531 runs; 411 research/test runs were counted, with only the latest 50 retained; all 50 retained runs were completed; `actions=[]` and `errors=[]`. No later guardian run or open queue-guardian incident was visible by 07:15 UTC. The five-minute cadence remains unproven: treat it as opportunistic monitoring, not a heartbeat or SLA. Prefer event-driven workflow_run handoffs, with a separate external watchdog for missed events. Both scheduled workflows may be delayed or dropped under GitHub's best-effort schedule delivery: [workflow schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
- Control PR #2 remains an exact-actor, exact-command dispatch surface; it is not a reason to execute or merge PR-head code.
- Main branch protection was not enabled; no repository permissions or settings are changed by this queue.

## Handoff discipline

Keep this file as a concise index, not a chronological transcript. Put reusable policy in `docs/`, project instructions in `tasks/`, dated evidence in `reports/`, and superseded state in `archive/`. Before each successor, record predecessor research/performance feedback, technical-delivery feedback, admin-agent calibration and the next task's difficulty/timebox.

The detailed previous queue history is preserved in [archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md](../archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).


## Trigger reliability correction — 2026-11-24

GitHub Actions `schedule` is best-effort and must not be the primary clock or sole trigger for any time-sensitive, deadline-bound or freshness-sensitive research operation. The failed 04:23 UTC capture expectation was a design error: the expected event never created a run, and the task must not be parked until another cron tick. Follow [External Scheduler and Dispatch Reliability](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md). For this holdout, the external authenticated dispatcher, idempotent slot handling and independent watchdog remain unprovisioned; do not represent the pipeline as autonomously scheduled until all three are verified.
