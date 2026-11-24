# Active Repository Queue

**Updated:** 2026-11-24 13:31 UTC  
**Canonical queue:** this file remains the single active-work index; it may contain one primary critical-path task plus independently admitted parallel workstreams.  
**Currently executing workstreams:** 1.  
**Primary active workstream:** [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md) — ACTIVE; MEDIUM; cycle 3/4; expires 2026-11-29 12:28:44 UTC.  
**Additional admitted parallel workstreams:** none.

## Active workstream record — Binance Spot dynamic-universe audit

- **workstream_id:** `BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24`
- **status / priority:** active / P2 primary environment-enabling critical path
- **objective:** verify whether the complete current Binance Spot catalogue and official public archive/index surfaces can support a dynamically discovered historical universe, including product inception, delisted-symbol and point-in-time membership limitations; no strategy selection or backtest.
- **dependencies:** `post-holdout-environment-review` (completed 2026-11-24).
- **independence rationale:** the predecessor portfolio/environment review is complete; no other workstream is active; this audit uses only public read-only market metadata/archive inputs and does not consume or inspect a confirmatory holdout.
- **write_scope:** `tasks/ACTIVE-QUEUE.md`, `tasks/BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md`, `research/binance_spot_universe_audit.py`, `research/test_binance_spot_universe_audit.py`, `reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md`, `REPOSITORY-OVERVIEW.md` (navigation-only status pointer).
- **exclusive_resource_keys:** `binance-public-api-50-request-budget`, `binance-vision-12-archive-object-250mb-budget`, `main-branch-integration`.
- **confirmatory_holdout_ids:** none.
- **difficulty_assessment:** data novelty 2 (full current catalogue and archive-index discovery are new); methodology 2 (historical/delisted membership must be distinguished from current catalogue); integration 2 (bounded manifest/parser/test work); statistical validation 1 (no strategy statistics); compute/operations 1 (strict request/object/byte caps). Total 8 / MEDIUM.
- **started_at_utc:** `2026-11-24T12:28:44Z`
- **expires_at_utc:** `2026-11-29T12:28:44Z` (five-day MEDIUM ceiling; earlier than absolute deadline 2026-12-02T17:30:00Z).
- **max_cycles / cycles_used:** 4 / 3 (third substantive wake-up checkpoint, 2026-11-24 13:21 UTC). The activation record was committed before the first substantive action; the earlier of four substantive cycles or expiry controls.
- **next action:** final independent evidence review in cycle 4; if no supported visible route reaches older category pages and no official completeness guarantee exists, close INCONCLUSIVE/INFEASIBLE. Do not use undocumented endpoints or repeat archive probes.


## Latest dynamic-universe audit checkpoint — 2026-11-24

The [dated checkpoint report](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md) now includes the third wake-up (13:21 UTC).

- Current exchangeInfo: 3,751/3,751 symbols normalized, zero parse errors; 1,376 TRADING, 2,375 BREAK, 50 quote assets. Raw response SHA-256 `1547b62532d008d7e2ca92a64d3f60be23d32552a675a96b82f67f515d2b5d53`; normalized catalogue SHA-256 `86cfc7b96303d1b8c3397469ca4524328109425fb89b24c75e7ca7d572ceda47`.
- Direct archive sample remains unchanged: four accepted of five monthly files; one USDCAED month explicitly rejected as incomplete. Five metadata/API requests, 11 archive objects, 155,377 downloaded bytes. No repeat was performed.
- Official announcement category pages visibly expose 231 New Cryptocurrency Listing pages and 45 Delisting pages, but both are mixed-product categories. Page 2/oldest-page navigation and completeness were not verified; no official retention guarantee was found.
- Older event cross-check: 18 unique pairs from four 2022 notices plus the ACM/TRY removal/reopening sequence; all 18 appear in the current catalogue (15 BREAK, 3 TRADING). This remains SAMPLE_ONLY, not a complete lifecycle ledger.
- Undocumented public BAPI list endpoints were inadvertently opened during route discovery; its output is excluded from evidence and further use is prohibited. The pre-listing archive URL attempt was inaccessible with no HTTP status/bytes and is not an accepted negative control.
- Current catalogue VERIFIED for the snapshot; direct archive and sampled lifecycle records SAMPLE_ONLY; complete historical membership, announcement-history completeness and universe-wide archive coverage UNKNOWN. No strategy start.
- Latest main CI [45404093861](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404093861) passed 346 deterministic tests in 15.485 seconds and the synthetic smoke test on commit `1459356eeb93c017920d6ab016249493b4ccb67b`. This is engineering evidence only.

## Repository governance upgrade — completed 2026-11-24

The evidence-first lifecycle, dual-axis retrospectives, tested project-readiness gate, documentation index, action SHA pinning, grouped dependency updates, per-ref CI deduplication and parallel-workstream admission/timebox policy are committed. See [governance implementation retrospective](../reports/EVIDENCE-FIRST-RESEARCH-GOVERNANCE-IMPLEMENTATION-2026-11-24.md) and [parallel-workstream policy](../docs/PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md). Latest main CI [45397358320](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45397358320) passed 346 deterministic tests in 15.555 seconds and the synthetic smoke test on commit `c67b6d`; earlier CI attempts [45359822075](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359822075) and [45359984790](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359984790) failed on successive authorization-assertion regressions and were superseded by the passing correction. Earlier full run [45327618205](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45327618205) passed 300 deterministic tests in 14.670 seconds.

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

## Most recent completed portfolio-review assignment — 2026-11-24

**Workstream:** `post-holdout-environment-review`  
**Disposition:** COMPLETE after **1 of 2** maximum substantive cycles; closed early without resetting or rolling over the unused cycle.  
**Frozen LOW-tier clock:** 2026-11-24T10:27:16Z to 2026-11-26T10:27:16Z.

- Both predecessor feedback axes were completed. The holdout capture was an infrastructure/data-preservation result, not a strategy return measurement.
- The environment matrix covers all 11 required dimensions and distinguishes pair-specific VERIFIED evidence from broader SAMPLE_ONLY/UNKNOWN scope.
- No strategy was selected. The prior Spot mean-reversion and Spot Momentum NO-GO results remain closed; USD-M funding remains INCONCLUSIVE.
- Two admin-agent calibrations were recorded: scheduled-delivery reliability must be proven end-to-end; source dimensions are VERIFIED only for the exact tested scope and execution environment.
- The evidence-backed successor, [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md), is now ACTIVE / MEDIUM / cycle 2 of 4, with frozen expiry 2026-11-29 12:28:44 UTC. The current catalogue and sampled archive route are verified only for their tested scope; historical lifecycle and universe-wide archive completeness remain UNKNOWN.
- Full findings: [Post-Holdout Research Environment and Portfolio Review](../reports/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW-2026-11-24.md).

## Research-track status

| Workstream | Status | Rule |
|---|---|---|
| ETH/BTC Spot mean-reversion | NO-GO, closed | Do not reopen or tune on the same OOS sample. |
| ETH/BTC Spot relative momentum | NO-GO, closed | Do not tune on the same OOS sample. |
| USD-M funding-aware study | INCONCLUSIVE | Keep funding inputs provisional/unaccepted; no perp backtest. |
| Prospective Binance Spot capture | COMPLETE / RECOVERED by first-agent fallback | November 24 slot and same-slot replay verified; external scheduler remains UNCONFIGURED. No strategy evaluation. |
| Binance Spot dynamic-universe feasibility audit | ACTIVE / checkpoint 3 of 4 | Current catalogue VERIFIED; direct archive objects, visible announcement pagination and sampled older lifecycle records SAMPLE_ONLY; complete point-in-time membership and universe-wide archive completeness UNKNOWN. No strategy start. |

## Successor sequencing

The post-holdout environment/portfolio review is complete and its evidence-backed successor audit is ACTIVE at cycle 3/4. The [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md) has completed its current-catalogue, bounded direct-archive and first official-announcement/event-sample checks. The visible categories expose 231 and 45 pages but mix product types; older-page navigation and complete retention remain unverified. An 18-pair 2022/ACM-TRY event sample is present in the current catalogue (15 BREAK, 3 TRADING), but this is not a complete lifecycle ledger. **No successor strategy is selected.** Use the final cycle for an independent review, then close INCONCLUSIVE/INFEASIBLE if point-in-time membership or archive completeness remains unverified.

All successor work must satisfy:
- [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Model Implementation Timebox Policy](../docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)

## Current automation observations to recheck

- **External scheduler:** still UNCONFIGURED / DEGRADED; no independent scheduler, dedicated GitHub App credential or separate watchdog is provisioned. GitHub cron is best-effort only and must never be treated as the primary clock or recovery plan.
- **First-agent recovery:** exercised successfully for the November 24 holdout slot. The direct-agent route checks due time, live Actions state and Release assets, then uses the exact-owner command only if the stable slot is missing and no capture is active. A second authorized wake-up proved exact ZIP/sidecar reuse; do not duplicate.
- **Queue guardian:** five-minute cron cadence remains unproven and is not an SLA. Event-driven capture handoffs [45373479882](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373479882), [45373736534](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373736534) and [45373756502](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373756502) completed successfully.
- **Research CI:** latest main CI [45404093861](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404093861) passed 346 deterministic tests in 15.485 seconds and the synthetic pipeline smoke test on commit `1459356eeb93c017920d6ab016249493b4ccb67b`. This validates code, not archive completeness or a trading edge.
- **Control PR:** PR #2 remains the exact-owner command surface; do not execute or merge PR-head code. Existing exact actor/ref/event gates remain intact.
- **Current active workstream:** Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit — MEDIUM, cycle 3/4, expires 2026-11-29 12:28:44 UTC. See [checkpoint report](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md). No strategy successor is currently admitted.
## Handoff discipline

Keep this file as a concise index, not a chronological transcript. Put reusable policy in `docs/`, project instructions in `tasks/`, dated evidence in `reports/`, and superseded state in `archive/`. Before each successor, record predecessor research/performance feedback, technical-delivery feedback, admin-agent calibration and the next task's difficulty/timebox.

The detailed previous queue history is preserved in [archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md](../archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).


## Trigger reliability correction — 2026-11-24

GitHub Actions `schedule` is best-effort and must not be the primary clock or sole trigger for any time-sensitive, deadline-bound or freshness-sensitive research operation. The failed 04:23 UTC capture expectation was a design error: the expected event never created a run, and the task must not be parked until another cron tick. Follow [External Scheduler and Dispatch Reliability](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md). For this holdout, the external authenticated dispatcher, idempotent slot handling and independent watchdog remain unprovisioned; do not represent the pipeline as autonomously scheduled until all three are verified.


## Direct-agent recovery default — 2026-11-24

Time-sensitive work no longer waits indefinitely for a deterministic trigger. When the due time has passed, the first authorized agent wake-up must inspect the durable slot/output state and directly resume the missing task if no verified result or active run exists. For the Spot holdout, the November 24 slot is `binance-spot-1h:prospective-2026-11:2026-11-24`; use the owner-exact PR command only after checking release assets and active Actions runs. Stable slot assets and the workflow concurrency group prevent duplicate captures. General rule: automation first, first-agent direct execution as the last line of defense, with identical authorization and acceptance gates. See [factory design map](../docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) and [scheduler reliability policy](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md).
