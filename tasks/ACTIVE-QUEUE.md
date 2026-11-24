# Active Repository Queue

**Updated:** 2026-11-24 10:35 UTC  
**Canonical queue:** this file remains the single active-work index; it may contain one primary critical-path task plus independently admitted parallel workstreams.  
**Currently executing workstreams:** [Post-Holdout Research Environment and Portfolio Review](POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md) — ACTIVE; LOW; started 2026-11-24T10:27:16Z; expires 2026-11-26T10:27:16Z; maximum 2 cycles; cycles_used=0.  
**Next ready workstream:** none.  
**Additional admitted parallel workstreams:** none currently.

## Repository governance upgrade — completed 2026-11-24

The evidence-first lifecycle, dual-axis retrospectives, tested project-readiness gate, documentation index, action SHA pinning, grouped dependency updates, per-ref CI deduplication and parallel-workstream admission/timebox policy are committed. See [governance implementation retrospective](../reports/EVIDENCE-FIRST-RESEARCH-GOVERNANCE-IMPLEMENTATION-2026-11-24.md) and [parallel-workstream policy](../docs/PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md). Latest main CI [45375425738](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45375425738) passed 324 deterministic tests in 15.423 seconds and the synthetic plumbing smoke test on commit `842abf6`, including the direct-agent recovery regression; the two preceding CI attempts [45359822075](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359822075) and [45359984790](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359984790) failed on successive authorization-assertion regressions and were superseded by the passing correction. Earlier full run [45327618205](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45327618205) passed 300 deterministic tests in 14.670 seconds.

## Most recent completed critical-path assignment

**Workstream:** `spot-holdout-first-scheduled-validation`  
**Disposition:** COMPLETE / November 24 slot `RECOVERED` by the first authorized agent wake-up after the due time.  
**Original budget/deadline:** one substantive cycle; 2026-11-25 17:30 UTC. Closed early without resetting or extending the budget.

- GitHub cron due 2026-11-24 04:23 UTC did not create a run. The first authorized agent wake-up at 10:17:48 UTC inspected Actions/release state and used the existing exact-owner PR #2 command. [Capture run 45373419544](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544) passed authorization and capture.
- Stable slot `binance-spot-1h:prospective-2026-11:2026-11-24` is COMPLETE: 562 hourly rows per symbol, from 2026-11-01 00:00 UTC through the 2026-11-24 09:00 UTC bar; zero missing hours, duplicate timestamps, overlap corrections or source errors.
- Current ZIP asset 786684218 (65,817 bytes; SHA-256 `22bd362b7c0db51c7a3302f5b09c1a4a2327a4d9553b8ac7259f2a343c5caade`) and current JSON sidecar asset 786684257 (5,211 bytes; SHA-256 `57cb7b1d297c15a33aa80784a0b72e010988e3da99a0e65171174ce02e19d284`) were published. The original ZIP 784136576 was preserved and its sidecar was backfilled as asset 786684146.
- Same-slot replay [45373703705](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373703705) independently verified and reused the exact ZIP/sidecar (`idempotent_slot_reuse=true`); Release asset count remained four, with no duplicate snapshot.
- Main CI [45373689039](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373689039) passed 320 deterministic tests and the synthetic plumbing smoke test. Queue-guardian event-driven handoffs [45373479882](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373479882), [45373736534](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373736534) and [45373756502](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373756502) succeeded.
- No strategy backtest, empirical strategy evaluation, funding research, paid-data acquisition, venue merge, live trading or capital deployment occurred.

**Residual operating limitation:** the external scheduler, GitHub App dispatch credential and independent watchdog remain `UNCONFIGURED / DEGRADED`. This slot is `RECOVERED` by the agent fallback; this does not promote the external scheduler to `DELIVERY_VERIFIED`. GitHub cron remains non-authoritative.

## Current active workstream — Post-Holdout Research Environment and Portfolio Review

- **ID/status:** `post-holdout-environment-review` / ACTIVE.
- **Difficulty/timebox:** LOW; 2026-11-24T10:27:16Z to 2026-11-26T10:27:16Z; maximum 2 substantive cycles, cycles_used=0. Absolute deadline: 2026-11-27 17:30 UTC; the earlier expiry controls.
- **Dependency:** first scheduled holdout validation closed as RECOVERED; evidence is in [the final November 24 checkpoint](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md).
- **Write scope:** task, canonical queue, README, parallel-workstream status pointer, review report and one evidence-justified successor task if needed.
- **Exclusive resources / confirmatory holdouts:** none; read-only evidence review, no protected data access or strategy evaluation.
- **Objective:** complete both predecessor feedback axes, build a verified environment matrix, make one measurable admin-agent calibration decision, then select one feasible successor or record a no-project decision. Do not implement a model under this review.


## Research-track status

| Workstream | Status | Rule |
|---|---|---|
| ETH/BTC Spot mean-reversion | NO-GO, closed | Do not reopen or tune on the same OOS sample. |
| ETH/BTC Spot relative momentum | NO-GO, closed | Do not tune on the same OOS sample. |
| USD-M funding-aware study | INCONCLUSIVE | Keep funding inputs provisional/unaccepted; no perp backtest. |
| Prospective Binance Spot capture | COMPLETE / RECOVERED by first-agent fallback | November 24 slot and same-slot replay verified; external scheduler remains UNCONFIGURED. No strategy evaluation. |

## Successor sequencing

After the active holdout-validation task is closed, execute the queued environment/portfolio review. It must consume both feedback axes from the completed task and the prior empirical conclusions, then establish the verified information and infrastructure envelope. **No successor model is selected in advance.** If no candidate fits verified evidence, queue a bounded environment-enabling project or record that no new model is justified.

All successor work must satisfy:
- [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Model Implementation Timebox Policy](../docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)

## Current automation observations to recheck

- **External scheduler:** still UNCONFIGURED / DEGRADED; no independent scheduler, dedicated GitHub App credential or separate watchdog is provisioned. GitHub cron is best-effort only and must never be treated as the primary clock or recovery plan.
- **First-agent recovery:** exercised successfully for the November 24 holdout slot. The direct-agent route checks due time, live Actions state and Release assets, then uses the exact-owner command only if the stable slot is missing and no capture is active. A second authorized wake-up proved exact ZIP/sidecar reuse; do not duplicate.
- **Queue guardian:** five-minute cron cadence remains unproven and is not an SLA. Event-driven capture handoffs [45373479882](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373479882), [45373736534](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373736534) and [45373756502](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373756502) completed successfully.
- **Research CI:** latest full CI [45373689039](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373689039) passed 320 deterministic tests and the synthetic plumbing smoke test on `0316062`.
- **Control PR:** PR #2 remains the exact-owner command surface; do not execute or merge PR-head code. Existing exact actor/ref/event gates remain intact.
- **Next ready workstream:** Post-Holdout Research Environment and Portfolio Review. Start its clock only when substantive work begins; first inspect predecessor feedback and this completed capture evidence.
## Handoff discipline

Keep this file as a concise index, not a chronological transcript. Put reusable policy in `docs/`, project instructions in `tasks/`, dated evidence in `reports/`, and superseded state in `archive/`. Before each successor, record predecessor research/performance feedback, technical-delivery feedback, admin-agent calibration and the next task's difficulty/timebox.

The detailed previous queue history is preserved in [archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md](../archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).


## Trigger reliability correction — 2026-11-24

GitHub Actions `schedule` is best-effort and must not be the primary clock or sole trigger for any time-sensitive, deadline-bound or freshness-sensitive research operation. The failed 04:23 UTC capture expectation was a design error: the expected event never created a run, and the task must not be parked until another cron tick. Follow [External Scheduler and Dispatch Reliability](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md). For this holdout, the external authenticated dispatcher, idempotent slot handling and independent watchdog remain unprovisioned; do not represent the pipeline as autonomously scheduled until all three are verified.


## Direct-agent recovery default — 2026-11-24

Time-sensitive work no longer waits indefinitely for a deterministic trigger. When the due time has passed, the first authorized agent wake-up must inspect the durable slot/output state and directly resume the missing task if no verified result or active run exists. For the Spot holdout, the November 24 slot is `binance-spot-1h:prospective-2026-11:2026-11-24`; use the owner-exact PR command only after checking release assets and active Actions runs. Stable slot assets and the workflow concurrency group prevent duplicate captures. General rule: automation first, first-agent direct execution as the last line of defense, with identical authorization and acceptance gates. See [factory design map](../docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) and [scheduler reliability policy](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md).
