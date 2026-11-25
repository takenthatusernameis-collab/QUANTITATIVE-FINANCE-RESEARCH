# Active Repository Queue

**Updated:** 2026-11-25 01:20 UTC  
**Canonical queue:** this file remains the single active-work index; it may contain one primary critical-path task plus independently admitted parallel workstreams.  
**Currently executing workstreams:** 0.  
**Primary active workstream:** none; no successor strategy or workstream is admitted pending materially new evidence and a fresh readiness review.  
**Additional admitted parallel workstreams:** none.

## Closed workstream record — Binance Spot dynamic-universe audit

- **workstream_id:** `BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24`
- **status / priority:** CLOSED / INCONCLUSIVE; P2 environment-enabling audit, terminal at cycle 4/4 on 2026-11-24
- **objective:** verify whether the complete current Binance Spot catalogue and official public archive/index surfaces can support a dynamically discovered historical universe, including product inception, delisted-symbol and point-in-time membership limitations; no strategy selection or backtest.
- **dependencies:** `post-holdout-environment-review` (completed 2026-11-24).
- **independence rationale:** the predecessor portfolio/environment review is complete; no other workstream is active; this audit uses only public read-only market metadata/archive inputs and does not consume or inspect a confirmatory holdout.
- **write_scope:** `tasks/ACTIVE-QUEUE.md`, `tasks/BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md`, `research/binance_spot_universe_audit.py`, `research/test_binance_spot_universe_audit.py`, `reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md`, `REPOSITORY-OVERVIEW.md` (navigation-only status pointer).
- **exclusive_resource_keys:** `binance-public-api-50-request-budget`, `binance-vision-12-archive-object-250mb-budget`, `main-branch-integration`.
- **confirmatory_holdout_ids:** none.
- **difficulty_assessment:** data novelty 2 (full current catalogue and archive-index discovery are new); methodology 2 (historical/delisted membership must be distinguished from current catalogue); integration 2 (bounded manifest/parser/test work); statistical validation 1 (no strategy statistics); compute/operations 1 (strict request/object/byte caps). Total 8 / MEDIUM.
- **started_at_utc:** `2026-11-24T12:28:44Z`
- **expires_at_utc:** `2026-11-29T12:28:44Z` (five-day MEDIUM ceiling; earlier than absolute deadline 2026-12-02T17:30:00Z).
- **max_cycles / cycles_used:** 4 / 4; closed at 2026-11-24 14:53 UTC when the cycle cap was reached, before the frozen expiry. No extension or clock reset.
- **terminal disposition:** INCONCLUSIVE. Current catalogue VERIFIED for its snapshot; direct archive and sampled lifecycle evidence SAMPLE_ONLY; complete point-in-time membership and universe-wide archive coverage UNKNOWN. See the final audit report below.
- **next action:** none. Reconsider only if materially new authoritative evidence or a separately authorized documented source route becomes available. Do not repeat failed archive probes or use undocumented endpoints.


## Final dynamic-universe audit disposition — 2026-11-24

**Workstream:** BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24  
**Disposition:** **CLOSED / INCONCLUSIVE** at cycle 4/4 (2026-11-24 14:53 UTC); no extension.

- The complete current 3,751-symbol exchangeInfo snapshot is VERIFIED for its retrieval time and retained hashes.
- Four of five bounded direct monthly archive samples passed; the USDCAED month was explicitly rejected as incomplete. No archive probe was repeated during the final cycle.
- Official New Cryptocurrency Listing and Delisting categories currently render 231 and 45 pages respectively, but both are mixed-product feeds. The read-only page representation did not expose page-number link targets; page 2/oldest-page navigation and historical completeness remain unverified.
- The 18-pair older lifecycle sample is SAMPLE_ONLY (all present in the current catalogue; 15 BREAK, 3 TRADING). It is not a complete event ledger.
- Binance's delisting FAQ provides navigation/notification guidance, not a retention guarantee. The upstream [binance-public-data issue #479](https://github.com/binance/binance-public-data/issues/479) was rechecked at 2026-11-24 19:17 UTC: it remains open with two user comments and no maintainer clarification. This is a lead, not proof that no such internal or undocumented record exists.
- Final classifications: current catalogue VERIFIED; direct archive objects and sampled lifecycle records SAMPLE_ONLY; complete historical membership, point-in-time lifecycle and universe-wide archive completeness UNKNOWN.
- No strategy is ready. No undocumented API was used, no archive sample was repeated, and no backtest or holdout inspection occurred.
- Final report: [Binance Spot Dynamic-Universe and Historical-Coverage Audit](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md). Latest main CI [45404411941](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404411941) succeeded; preceding full CI [45404093861](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404093861) passed 346 deterministic tests and synthetic smoke.


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
- A later GitHub schedule event [45420205895](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45420205895) arrived at 14:59:10 UTC, 10h36m10s after its nominal 04:23 UTC due time. It passed 29 capture tests, returned `idempotent_slot_reuse=true`, reused the same ZIP/sidecar IDs and created no new Release assets. This is a late schedule replay, not an SLA or external scheduler validation.
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
- The evidence-backed successor, [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md), subsequently CLOSED INCONCLUSIVE at cycle 4/4 on 2026-11-24. The current catalogue and sampled archive route are verified only for their tested scope; historical lifecycle and universe-wide archive completeness remain UNKNOWN. No further successor was admitted.
- Full findings: [Post-Holdout Research Environment and Portfolio Review](../reports/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW-2026-11-24.md).

## Research-track status

| Workstream | Status | Rule |
|---|---|---|
| ETH/BTC Spot mean-reversion | NO-GO, closed | Do not reopen or tune on the same OOS sample. |
| ETH/BTC Spot relative momentum | NO-GO, closed | Do not tune on the same OOS sample. |
| USD-M funding-aware study | INCONCLUSIVE | Keep funding inputs provisional/unaccepted; no perp backtest. |
| Prospective Binance Spot capture | COMPLETE / RECOVERED by first-agent fallback | November 24 slot and same-slot replay verified; external scheduler remains UNCONFIGURED. No strategy evaluation. |
| Binance Spot dynamic-universe feasibility audit | CLOSED / INCONCLUSIVE (cycle 4/4) | Current catalogue VERIFIED; direct archive and sampled lifecycle evidence SAMPLE_ONLY; complete point-in-time membership and universe-wide archive completeness UNKNOWN. No strategy start. |



**Historical provider-screening evidence (not an active workstream):** The independent MEXC public funding-history pilot in [the November 22 funding schedule-samples report](../reports/ETH-BTC-FUNDING-SCHEDULE-SAMPLES-2026-11-22.md) paginated 1,620 rows each for BTC_USDT and ETH_USDT (two pages per symbol), from 2025-05-31 16:00 UTC through 2026-11-22 08:00 UTC, with 8-hour-only observed cadence and zero duplicate settlement timestamps. This is an approximately 540-day API window, not the required 2020–2026 history; MEXC does not document historical-retention or contract-incarnation completeness. Its official API documentation exposes page-number pagination (maximum 1,000 rows/page) and row-level collectCycle, but that does not certify the full settlement population ([official API reference](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history)). Keep this provider SAMPLE_ONLY / not accepted for full-history backtesting, and do not repeat the same probe unchanged. Bitget's public download route remains RESTRICTED in the tested browser context. Provider discovery remains non-exhaustive; neither venue is a permanent dependency.

The former [ETH/BTC ingestion task record](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md) is now explicitly marked NOT ACTIVE / NOT ADMITTED. Its historical evidence and unresolved blockers are preserved; the canonical queue remains the only live work pointer.

## Successor sequencing

The post-holdout environment/portfolio review and its evidence-backed dynamic-universe successor audit are both complete. The audit closed INCONCLUSIVE at cycle 4/4: the current catalogue is VERIFIED for its snapshot, while direct archive and sampled lifecycle evidence remain SAMPLE_ONLY and complete point-in-time membership/universe-wide archive coverage remain UNKNOWN. **No successor strategy or active workstream is selected.** Reconsider only if materially new authoritative evidence or a separately authorized source route becomes available.

All successor work must satisfy:
- [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Model Implementation Timebox Policy](../docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md)

## Current automation observations to recheck

- **External scheduler:** still UNCONFIGURED / DEGRADED; no independent scheduler, dedicated GitHub App credential or separate watchdog is provisioned. GitHub cron is best-effort only and must never be treated as the primary clock or recovery plan. The November 24 schedule event arrived 10h36m10s late and idempotently reused the recovered slot; this demonstrates delay, not dependable delivery.
- **First-agent recovery:** exercised successfully for the November 24 holdout slot. The direct-agent route checks due time, live Actions state and Release assets, then uses the exact-owner command only if the stable slot is missing and no capture is active. A second authorized wake-up proved exact ZIP/sidecar reuse; do not duplicate.
- **Next holdout slot:** `binance-spot-1h:prospective-2026-11:2026-11-25` is due at 2026-11-25 04:23 UTC. At this checkpoint (01:09 UTC) it remained 3h14m before due; no November 25 capture run or asset was expected, and no early/duplicate dispatch was made. The November 24 ZIP/sidecar remain the latest completed slot. After the due time, the first authorized agent wake-up must inspect live runs and Release assets, then use the exact-owner fallback only if the stable slot is absent and no valid capture is active.
- **Queue guardian:** five-minute cron cadence remains unproven and is not an SLA. Latest scheduled heartbeat [45522121183](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45522121183) completed successfully at 2026-11-25 00:57:39 UTC in `LIVE_ENFORCEMENT` mode on main commit `1b44ff9`. It enumerated all 669/669 workflow runs; 510 relevant runs were counted, with only the latest 50 retained in the report. `actions=[]`, `errors=[]`, and the status comment was updated. The latest 100-run API view had no queued/in-progress/requested/pending runs. The preceding scheduled heartbeat was [45436708676](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45436708676) at 2026-11-24 16:24:15 UTC, an 8h33m24s gap; this single recovery does not remove the `DEGRADED` / not delivery-verified status. Earlier event-driven handoffs remain successful.
- **Research CI:** MEXC code/test commit [f158b1b](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/f158b1bde453d36d60b53be18ae13865bf9049ae) passed [run 45524716098](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45524716098): 348 deterministic tests in 15.559 seconds plus the synthetic pipeline smoke test. The follow-up queue/handoff commit [1867d57](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1867d573841f44351d07550898edab91db1ada98) also passed [run 45524885961](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45524885961): 348 tests plus the synthetic smoke test. Coverage rejects an empty MEXC funding-history population and protects the exact-owner/default-branch/manifest-only dispatch contract. This validates code, not historical funding completeness or a trading edge.
- **Control PR:** PR #2 remains the exact-owner command surface; do not execute or merge PR-head code. Existing exact actor/ref/event gates remain intact.
- **Current active workstream:** none. The Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit closed INCONCLUSIVE at cycle 4/4; see [final report](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md). No strategy successor is currently admitted.
## Handoff discipline

Keep this file as a concise index, not a chronological transcript. Put reusable policy in `docs/`, project instructions in `tasks/`, dated evidence in `reports/`, and superseded state in `archive/`. Before each successor, record predecessor research/performance feedback, technical-delivery feedback, admin-agent calibration and the next task's difficulty/timebox.

The detailed previous queue history is preserved in [archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md](../archive/ACTIVE-QUEUE-HISTORICAL-2026-11-23.md).


## Trigger reliability correction — 2026-11-24

GitHub Actions `schedule` is best-effort and must not be the primary clock or sole trigger for any time-sensitive, deadline-bound or freshness-sensitive research operation. The failed 04:23 UTC capture expectation was a design error: the expected event never created a run, and the task must not be parked until another cron tick. Follow [External Scheduler and Dispatch Reliability](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md). For this holdout, the external authenticated dispatcher, idempotent slot handling and independent watchdog remain unprovisioned; do not represent the pipeline as autonomously scheduled until all three are verified.


## Direct-agent recovery default — 2026-11-24

Time-sensitive work no longer waits indefinitely for a deterministic trigger. When the due time has passed, the first authorized agent wake-up must inspect the durable slot/output state and directly resume the missing task if no verified result or active run exists. For the Spot holdout, the November 24 slot is `binance-spot-1h:prospective-2026-11:2026-11-24`; use the owner-exact PR command only after checking release assets and active Actions runs. Stable slot assets and the workflow concurrency group prevent duplicate captures. General rule: automation first, first-agent direct execution as the last line of defense, with identical authorization and acceptance gates. See [factory design map](../docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md) and [scheduler reliability policy](../docs/EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md).
