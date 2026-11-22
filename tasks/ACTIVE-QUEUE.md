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
- **Funding route replacement implemented:** download_funding() no longer calls the HTTP-451 fapi.binance.com endpoint. It now ingests Binance Vision monthly USD-M fundingRate ZIPs, requires verified .CHECKSUM files, validates the three-column calc_time/funding_interval_hours/last_funding_rate schema and UTC month bounds, and writes per-month provenance plus a consolidated CSV. Implementation commits are linked in the same-session replacement section below. Production archive availability/schema and CI remain unverified.
- **Funding remains fail-closed:** the new downloader retains archive data/manifests but marks event_semantics=UNVERIFIED and completeness_status=PROVISIONAL_NOT_ACCEPTED, then raises to prevent empirical use until settlement-population semantics are independently reconciled. Do not assume fixed eight-hour cadence or substitute zero funding.
- **Funding completeness caveat:** Binance's own public-data issue [#517](https://github.com/binance/binance-public-data/issues/517) remained open on 2026-11-22 and asks whether monthly fundingRate archives enumerate every payable settlement and clarifies event/contract semantics. A valid ZIP/checksum and plausible cadence do not by themselves certify the complete settlement population.
- No empirical backtest has been verified. The original Binance ETH/BTC study remains **INCONCLUSIVE**.

### Next executable steps, ordered by information value

1. Resolve comment 7072165218 to its Actions run using the queue-guardian report or an Actions run-list interface; record run ID, event, actor, ref, SHA, status, jobs, artifact IDs and hashes. Do not create a duplicate audit.
2. Inspect that audit's six input manifests, Spot gap reconciliations, logs and artifact inventory. Confirm whether all six manifests were uploaded and whether the aggregate-trade positive controls passed. Separate source/data failures from dispatch/engineering failures.
3. Verify CI for commits 96979f0 and 42138f4; confirm the zero-volume regression passes and that no-control days remain unresolved.
4. Verify the already-implemented monthly fundingRate archive failover in CI, then run a bounded representative ETH/BTC archive probe through the authorized hosted runner. Inspect the actual CSV schema, checksum, event timestamps, duplicates, per-row interval metadata and coverage. Extend to the full requested history only after the representative probe passes; keep completeness unverified while settlement-population semantics remain unresolved.
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


## Same-session replacement invariant — 2026-11-22

A blocker diagnosed as requiring replacement must be acted on in the same agent session. It is not acceptable to leave “replace X” as a future handoff when the agent can implement a safe alternative now. The known HTTP-451 funding REST route was replaced in code commit [9850f2d](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9850f2d2598ffcd1d25c0fefc1ce2b6e0f997977) with Binance Vision monthly fundingRate archive ingestion; UTC month-bound validation was corrected in [e3c883e](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/e3c883edf8c55a9df70b232e39b3905aa3295074); archive schema/checksum/fail-closed regression tests were added in [492ed21](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/492ed2145a86ff61aff5b4e2354ac6e9304c4a8a). The replacement writes provenance-rich manifests and intentionally refuses to certify funding completeness because settlement-population semantics remain unresolved. This is an implemented fail-closed replacement, **not** verified archive availability, complete funding coverage, or an empirical result. The new test CI result is pending verification. Next: verify the tests and run a bounded representative archive probe through the authorized hosted runner; inspect the actual archive schema/checksum and event population before considering funding accepted.


### Funding-route replacement implementation delta — 2026-11-22

- The old `fapi.binance.com/fapi/v1/fundingRate` request has been removed from `research/run_eth_btc.py`. The implementation now iterates the official Binance Vision monthly USD-M `fundingRate` ZIP route, requires a verified `.CHECKSUM`, validates the three-field `calc_time/funding_interval_hours/last_funding_rate` schema, UTC month bounds, finite numeric values and positive interval metadata, and preserves per-month hashes and errors.
- Follow-up implementation commits: [7384c15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/7384c15cbc8b0cf3c4a712132bd5cc119aca541e) maps the archive rate field to the pipeline's `fundingRate` contract; [86dcd42](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/86dcd42cb06e220f11fd7b3197e6c3fea9392f1e) adds a regression assertion for that contract; [261a235](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/261a2351a040d7d0f3f36f0c7c1a1e46d7b8a831) corrects fallback-manifest source provenance. Current implementation contains zero references to the blocked `fapi.binance.com` endpoint.
- Latest research-test run [44973336934](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44973336934) targets commit `261a235` and is **PENDING** at handoff; earlier runs are also queued/in progress. Do not claim tests passed until the latest relevant run completes.
- The downloader deliberately records `event_semantics=UNVERIFIED` and `completeness_status=PROVISIONAL_NOT_ACCEPTED` and raises after retaining the data/manifest. This prevents the empirical strategy from consuming a checksum-valid but semantically unverified settlement population. Archive availability, actual production schema and complete event coverage remain unverified; next execution is a bounded representative ETH/BTC archive probe after CI, then independent reconciliation of settlement semantics. No empirical backtest is authorized by this partial ingestion.


## Latest wake-up cycle — 2026-11-22 03:24 UTC

**Adaptive antifragile plan:** resolve the current queue/run state first; perform conservative remote-tree hygiene; diagnose the latest verified CI failure; fix it in the same session; close the run-status observability gap without weakening queue or research gates; then continue only with a bounded, non-overlapping data probe.

**Queue and handoff review:** open [QFR queue guardian] issue search returned zero incidents. Control PR #2 remains open. Audit comment 7072165218 is resolved to run [44971182002](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44971182002), completed with an expected incomplete-data result; its artifact has been retrieved and inspected. No overlapping audit remains and no empirical run was started.

**Hygiene preflight:** the complete remote tree contains 37 tracked paths and is not truncated. No tracked Python caches, scratch files, raw market data or generated research outputs were present. .gitignore excludes disposable caches, local data and generated outputs. Five branches are visible; their commit ancestry could not be verified through the connected branch-fetch route, so none was deleted. Remote inspection cannot establish local untracked working-tree state.

**CI diagnosis and same-session correction:** run [44973336934](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44973336934), on commit 261a235, completed with one failure among 46 tests. The sole failing test supplied a synthetic CSV string containing literal backslash-n sequences, so pandas saw a malformed one-line/one-column input and the function correctly raised the archive-ingestion failure before reaching the intended event-semantics assertion. This was a fixture defect, not evidence that the production archive path works or fails. Corrected the fixture to construct real newline-delimited CSV text in commit [ec74947](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ec74947522422356b1b9a5ff04c7ca228df5e15b). Post-fix CI is verified: run [44980449997](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44980449997) passed 46 tests plus the synthetic smoke test; run [44980801176](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44980801176) passed 48 tests, including the new status-comment tests, plus the synthetic smoke test. The later permission/workflow commits have a new test run queued and remain to be verified.

**Meta-process improvement:** the queue guardian now retains a bounded recent run inventory for the two research workflows and upserts one bot-owned, idempotent status comment on control PR #2. It records run IDs, event, actor, status/conclusion, timestamps, commit SHA and URL; it never overwrites user-authored marker comments. The status-comment update is non-fatal and its failure is persisted in the guardian report. Implementation commit [d746d0a](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d746d0abc596a8a2908c6efed0e75676099e37c1); deterministic tests commit [d61f09c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d61f09c6c960778b44825bc462d9073a2025c3ee). The workflow already has issues:write; the new comment path updates only the marker-bearing github-actions[bot] comment and is idempotent.

**Dispatch verification:** harmless dry-run command 7073565371 triggered queue guardian run [44980838848](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44980838848), which completed successfully. Its artifact 14737717163 enumerated 73 repository runs completely and found no queue actions or errors; 68 research/test runs were counted, with the latest 50 retained. The status-comment POST failed with HTTP 403, Resource not accessible by integration. Added the narrowly scoped pull-requests:write permission in [3aa0b08](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/3aa0b0802269c1211c7156c3feedbde3a88ddcce); a new CI run is queued and the permission retry remains pending.

### Next executable actions

1. Verify CI for commits 3aa0b08, 0630670 and 8bdf5f0. Run 44981394352 was queued at the last check; inspect its exact state and predecessor before any retry. Do not duplicate the workflow test run.
2. Re-run the harmless queue-guardian dry-run after the permission commit. Confirm the bot-owned status comment is created/updated and its inventory resolves the current test runs and prior audit run. If the POST still fails, inspect the exact artifact error and choose a different least-privilege status surface rather than retrying blindly.
3. Once workflow CI is green and the permission path is verified, post the allowlisted command /qfr-probe-eth-btc-funding-2024-01. Inspect actual January 2024 funding archive availability, .CHECKSUM verification, three-column schema, timestamp range, interval metadata, row counts, duplicates and per-symbol manifests. Expect the empirical gate to remain closed while event semantics are unverified.
4. Address the 31 missing Spot bars per symbol with a materially different, positive-control-validated source/construction. Do not classify any missing hour as no-trade until a known-active positive control passes.
5. Continue the ETH/BTC ingestion task only after each independent source gate passes. Do not run the full empirical backtest or infer strategy performance while funding semantics or Spot gap classifications remain unresolved.

**Research conclusion:** original Binance ETH/BTC study remains **INCONCLUSIVE**. No new market-performance metrics were produced in this cycle.


**Funding-semantics cross-check:** public Binance issue [#517](https://github.com/binance/binance-public-data/issues/517) remains open, last updated 2026-11-19, with four public comments and no Binance-team clarification visible in the current thread. The monthly archive route must remain provisional and fail-closed.


**Resolved full-audit evidence:** run 44971182002 (commit 8fa50dd; comment 7072165218) completed with audit status INCOMPLETE and exit code 2, not an infrastructure failure. Artifact [14733503636](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44971182002/artifacts/14733503636) is a 48,040-byte ZIP with SHA-256 fa27161253ba556e96e4d5444cfdded4e9eacebadefec9ce05acc53763281b4f; it contains nine files, including the summary and all six input manifests. The summary SHA-256 is e8d0a1cd62b3d4489cb9c4d4f20c3a091c9e8bb479f98d44553169fee7407799. All 82 monthly archives for each of the four price series passed checksums with zero parse errors. USD-M ETH and BTC each have 59,904/59,904 hourly bars, zero gaps and zero duplicates. Spot ETH and BTC each have 59,873/59,904 bars and 31 missing hours; all 31 gaps per symbol remain classified aggregate_trade_positive_control_failed_unresolved. Both old funding REST requests returned HTTP 451. All six manifests were persisted; no raw CSVs were uploaded. The empirical/preflight steps were skipped after the incomplete audit.

**Latest workflow changes:** commit 3aa0b08 adds pull-requests:write only for the queue guardian's single bot-owned status comment; 0630670 adds a fixed January 2024 audit-only probe command; 8bdf5f0 makes research-tests run when the research workflow changes. The check for 3aa0b08 was queued at last inspection; no probe was dispatched while this CI run was unresolved.
