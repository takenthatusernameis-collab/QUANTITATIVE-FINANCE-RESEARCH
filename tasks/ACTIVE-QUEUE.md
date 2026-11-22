# Active Repository Queue

**Canonical active-task pointer.** Updated 2026-11-22. All wake-up agents must read this file after the general mindset and hygiene preflight, then inspect linked run/incident state before creating new work.

## Current operating priority

**Higher-order meta-process optimization is the first engineering priority after hard safety/scientific invariants.** Keep the queue guardian, autonomous dispatch, artifact persistence and repository hygiene reliable. The objective is to remove recurring manual interventions and avoid repeated failures across future cycles, not to create documentation churn.

## Active task

### P0 — Complete adaptive ETH/BTC ingestion and no-trade validation

Canonical task: [ETH-BTC ingestion and no-trade validation](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

Last fully verified audit: [44969155096](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44969155096), completed with data-audit failure (not a dispatch failure and not an empirical result). Artifact ID 14732529254, ZIP SHA-256 dbf237352b0067ff043d36b04c90a843a233b7430cbe80ceddef97814c5718a3.

A newer audit command was posted to control PR #2 as comment 7072165218 after commit 8fa50dd900dd5f4337fe615c0df188d74b5bc1db. Its workflow run ID/status is **UNVERIFIED**: the connected GitHub interface can fetch jobs/artifacts for a known run ID but does not expose a general workflow-run listing; fetch_commit_workflow_runs is PR-triggered-only and returned no rows for this default-branch commit. Do not dispatch another full audit until the command's run is resolved through a machine-checkable Actions/queue-guardian report.

### Current implementation and evidence

- Commit [8fa50dd](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8fa50dd900dd5f4337fe615c0df188d74b5bc1db) adds explicit kline header/alias handling, millisecond/microsecond timestamp parsing, strict numeric validation, parse-error manifests, Spot aggregate-trade probes, per-day positive-control probes, and fail-closed manifests for all six price/funding inputs.
- The code and deterministic tests are committed, but no CI result or post-commit audit artifact has yet been independently verified. Synthetic tests are engineering evidence only.
- Spot ETHUSDT and BTCUSDT previously each had 31 synchronized missing hours and zero duplicates. Monthly and daily kline archives omitted those hours. The new aggregate-trade route must be verified with known-active positive controls before any empty result can support a no-trade classification.
- **Positive-control fix committed:** commit [96979f0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/96979f0bf27bdb38e58151e4987760bfffecf6be) filters daily/monthly control candidates to finite volume greater than zero and records the chosen source and volume. Commit [42138f4](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/42138f490aab8274c575748d9a12ab6c81c6e8ef) adds a regression test where the nearest candle has zero volume. The research-tests workflow should trigger on both research-path pushes, but CI results remain **UNVERIFIED** because the connected interface cannot enumerate push runs.
- The USDⓈ-M kline parser now supports recognized header/no-header schemas and both timestamp scales, but the exact January 2022 production archives still need a successful runner verification. Do not silently drop malformed rows.
- **Funding remains blocked:** download_funding() still calls https://fapi.binance.com/fapi/v1/fundingRate, the same route that returned HTTP 451 for both ETH and BTC. The latest audit code still invokes that function. Do not repeat the known-blocked route unchanged or bypass the provider restriction.
- **Distinct funding alternative to test:** Binance Vision monthly USD-M archive pattern is https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-YYYY-MM.zip; secondary technical sources report columns calc_time, funding_interval_hours, last_funding_rate. Treat this as a candidate route, not yet verified in this repository. Inspect an actual archive and its .CHECKSUM before implementing production ingestion.
- **Funding completeness caveat:** Binance's own public-data issue [#517](https://github.com/binance/binance-public-data/issues/517) remained open on 2026-11-22 and asks whether monthly fundingRate archives enumerate every payable settlement and clarifies event/contract semantics. A valid ZIP/checksum and plausible cadence do not by themselves certify the complete settlement population. Preserve an explicit provisional/unknown completeness status until archive rows, interval metadata, coverage and event semantics are reconciled; never assume a fixed eight-hour cadence or substitute zero funding.
- No empirical backtest has been verified. The original Binance ETH/BTC study remains **INCONCLUSIVE**.

### Next executable steps, ordered by information value

1. Resolve comment 7072165218 to its Actions run using the queue-guardian report or an Actions run-list interface; record run ID, event, actor, ref, SHA, status, jobs, artifact IDs and hashes. Do not create a duplicate audit.
2. Inspect that audit's six input manifests, Spot gap reconciliations, logs and artifact inventory. Confirm whether all six manifests were uploaded and whether the aggregate-trade positive controls passed. Separate source/data failures from dispatch/engineering failures.
3. Verify CI for commits 96979f0 and 42138f4; confirm the zero-volume regression passes and that no-control days remain unresolved.
4. Probe the official monthly fundingRate archive route with one representative ETH and BTC month, inspect the real CSV schema and checksum, then implement bounded/resumable archive ingestion only after that probe. Validate every requested month, event timestamps, duplicates, per-row interval metadata and coverage. Keep completeness unverified if the official settlement-population semantics remain unresolved.
5. Keep all six manifests artifact-ready, including explicit failure records and source hashes; no raw market CSV uploads.
6. In parallel, evaluate a separately specified synchronized ETH/USD and BTC/USD dataset from an authorized independent provider. Keep it as a distinct experiment with its own data/methodology gates.
7. Run historical empirical work only after the selected experiment's complete input, missing-observation, funding and methodology gates pass. No live trading, capital deployment or strategy promotion.

## Meta-process and automation work

- [Queue guardian](../.github/workflows/queue-guardian.yml): scheduled every five minutes. Verify a **scheduled** run performs live enforcement; the completed PR-comment dry-run only validates inspection/plumbing.
- [Queue guardian implementation](../research/queue_guardian.py) and [tests](../research/test_queue_guardian.py). Last verified CI run [44968997867](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44968997867) passed 37 deterministic tests and the synthetic smoke test.
- Preserve the 15-minute cancellation rule and earlier active same-concurrency-group predecessor exception. If cancellation fails, record the orphan and launch one independent alternative attempt; deduplicate issue/run lineage.
- No open repository issues were returned by the current open-issue search, so no open queue-guardian incident needed recovery. PR #2 remains open as the control surface.
- The connected GitHub action set does not currently expose a general workflow-run list. The queue guardian's own API enumeration remains the available machine-side route; do not infer that an empty PR-filtered run result means no push/issue-comment run exists.
- Continue verifying scheduled watchdog enforcement separately from the already-passed manual dry-run.

## Cleanup and handoff rules

- Keep this file as the one canonical active queue; update it in place.
- Mark completed/superseded task plans; preserve historical reports and data provenance.
- Keep logs, raw CSVs, plots, and large outputs in retained artifacts/storage, not Git. Keep compact manifests, hashes and decision summaries.
- At every cycle: brainstorm session plan → conservative hygiene cleanup → inspect queue incidents/active runs → remove the highest-leverage manual dependency → execute current tasks → verify, measure and hand off.
- Never create a duplicate run while an existing canonical attempt is active. Never treat a successful trigger or synthetic test as empirical evidence.

## Latest wake-up cycle — 2026-11-22 (post-ingestion implementation review)

**Adaptive antifragile plan:** (1) inspect queue-guardian incidents and the canonical task; (2) review the newest implementation and test changes; (3) run the conservative hygiene preflight; (4) identify the remaining high-leverage data/automation bottlenecks; (5) avoid duplicate expensive work and leave a machine-checkable handoff.

**Queue/run review:** zero open repository issues were returned, so no open queue-guardian incident needed recovery. PR #2 is still open. Its latest comment is the exact audit command /qfr-run-eth-btc-data-audit (comment ID 7072165218). The associated run ID/status could not be resolved through the connected interface; mark it **UNVERIFIED** rather than assuming it is absent or completed. No second audit was dispatched.

**Hygiene result:** the preceding full tracked-tree inspection found 37 tracked objects and no tracked Python/test caches, raw market data, generated reports or scratch files. The newest commit changes the research implementation/tests rather than adding generated artifacts; .gitignore continues to exclude local data and disposable caches. No deletion or archival change was justified. A remote GitHub view cannot establish local untracked working-tree state, so that remains unverified.

**Implementation review:** commit 8fa50dd adds the parser, trade-level reconciliation and six-manifest persistence improvements. The latest research-tests workflow is configured to trigger on changes under research/**, but its post-commit result is not exposed by the current run-list interface. Positive-volume controls are now enforced and regression-tested in commits 96979f0 and 42138f4; their CI result remains unverified. The remaining data bottleneck is the unchanged HTTP-451 funding REST route, which must be replaced by a probed archive/provider route while keeping completeness claims conservative.

**Meta-process decision:** no new dispatch bridge or queue policy was justified this cycle. The highest-value improvement is to close the run-status observability gap and verify the already-triggered audit, while preventing a duplicate full-data run. Continue independent code/data work; do not wait for manual activation.


## Follow-up implementation — 2026-11-22

**Code fix:** aggregate-trade positive controls now require a finite positive-volume candle. The selected timestamp, source (daily or monthly archive), and volume are persisted in the control manifest. This prevents a zero-volume row from being treated as a known-active positive control. Commit 96979f0 contains the implementation; commit 42138f4 updates the three reconciliation fixtures and adds a deterministic regression test in which the nearest candle has zero volume and a later positive-volume candle must be selected.

**Verification:** the research-tests workflow is configured for push events under research/**, so the commits should trigger CI automatically. No post-commit workflow result is independently available through the connected interface; record it as **UNVERIFIED**, not PASS. The latest full audit command (PR #2 comment 7072165218) has not been resolved to a run ID, and no duplicate audit was launched.

**Remaining priority:** replace the still-unchanged fapi.binance.com funding request with a separately probed monthly archive/provider route; validate the real schema and checksums, and keep settlement-population completeness provisional until its semantics are established.
