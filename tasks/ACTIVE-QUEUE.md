# Active Repository Queue

**Updated:** 2026-11-24 01:42 UTC  
**Single canonical active task:** [First Scheduled Holdout Run Validation](PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md).  
**Queued successor (not active until current task closes):** [Post-Holdout Research Environment and Portfolio Review](POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md).

## Repository governance upgrade — completed 2026-11-24

The evidence-first lifecycle, dual-axis retrospectives, tested project-readiness gate, documentation index, action SHA pinning, grouped dependency updates and per-ref CI deduplication are committed. See [governance implementation retrospective](../reports/EVIDENCE-FIRST-RESEARCH-GOVERNANCE-IMPLEMENTATION-2026-11-24.md). Latest CI [45306713796](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45306713796) passed 280 deterministic tests and the synthetic plumbing smoke test.

## Current active assignment

**Priority:** P1 — prospective research-data infrastructure.  
**Budget:** one substantive cycle.  
**Hard deadline:** 2026-11-25 17:30 UTC.

The first daily Binance Spot capture is scheduled for **2026-11-24 04:23 UTC**. At the last checkpoint it was still pending. Do not dispatch a duplicate capture just to create an event. Verify the actual schedule-triggered run, new ETHUSDT/BTCUSDT snapshot, previous-snapshot digest and CSV-hash reconciliation, sidecar publication/backfill, release retention limits, and queue-guardian handoff. Follow the full acceptance criteria and stop conditions in the task file.

**Scope restrictions:** no strategy backtest, no tuning of the closed Spot Momentum experiment, no unaccepted funding data, no paid data/key purchase, no venue merge and no live trading.

**Asset-universe boundary:** ETHUSDT/BTCUSDT are the two symbols of this capture-validation task only. They do not define or restrict the factory's future asset universe. Future research discovery must follow [the open asset-universe policy](../docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md).

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

- Capture schedule: daily at 04:23 UTC; the first scheduled event after implementation is the active validation target.
- Queue guardian: configured on a five-minute schedule and on qualifying workflow completions. The last previously observed scheduled heartbeat was 2026-11-23 21:49:36 UTC; inspect actual later runs and do not infer ongoing health from configuration alone.
- Control PR #2 remains an exact-actor, exact-command dispatch surface; it is not a reason to execute or merge PR-head code.
- Main branch protection was not enabled; no repository permissions or settings are changed by this queue.

## Handoff discipline

Keep this file as a concise index, not a chronological transcript. Put reusable policy in `docs/`, project instructions in `tasks/`, dated evidence in `reports/`, and superseded state in `archive/`. Before each successor, record predecessor research/performance feedback, technical-delivery feedback, admin-agent calibration and the next task's difficulty/timebox.

The detailed previous queue history is preserved in [archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md](../archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).
