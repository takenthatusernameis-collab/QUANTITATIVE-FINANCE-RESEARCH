# Prospective Binance Spot Holdout Capture

**Status:** IMPLEMENTED — initial end-to-end capture passed; scheduled/manual-event validation transferred to successor  
**Priority:** P1 research-enabling infrastructure  
**Task budget:** 1 implementation cycle consumed; no extension. Operational follow-up is a separate bounded task.

## Context

The frozen ETH/BTC Spot Relative-Momentum Rotation concluded NO-GO on 2026-11-23. Do not tune, re-filter or reinterpret its 2022-01 through 2026-10 OOS sample. Any new strategy must be separately preregistered and evaluated on an independent/later holdout.

The accepted historical Spot archive ends at **2026-10-31**. A prospective holdout begins **2026-11-01**. The initial capture implementation is committed at [39b1682](https://github.com/${repo}/commit/39b1682baf32ad066af3dec4ec3d57e57c7836f9), and the first end-to-end run [45242319210](https://github.com/${repo}/actions/runs/45242319210) completed with 546 closed hourly bars per symbol and no gaps. Scheduled and actual workflow-dispatch event validation remain outstanding.

## Objective

Within one bounded cycle, investigate and, if safely feasible, implement the smallest reliable **prospective-only** capture system for Binance Spot hourly bars for `ETHUSDT` and `BTCUSDT`. It must preserve future independent holdout data without committing raw market data or requiring credentials.

This is a data/infrastructure task—not a model task. **Do not run backtests, optimize strategies, inspect signal/performance results, or select model parameters.**

## Required steps

1. **Preflight:** inspect current main, active queue, workflows, data/cache layout, existing downloader/reconciliation functions and open runs. Confirm no existing capture pipeline is being duplicated.
2. **Storage feasibility:** verify actual GitHub Actions artifact retention limits/settings, cache eviction behavior and any already-authorized durable storage. Select a storage approach that can preserve the intended holdout. Cache alone is not guaranteed durable. Do not introduce credentials, new external accounts, paid services or owner-only storage permissions.
3. **Backfill and capture:** acquire official Binance Spot hourly bars from 2026-11-01 through the latest fully closed hour, then continue scheduled capture with a bounded overlap/backfill window to tolerate delayed runs and revisions. Use public official endpoints/archives only. Keep ETHUSDT and BTCUSDT separate and correctly labeled.
4. **Integrity and acceptance:** timestamps must be UTC, unique, sorted, hourly aligned; only completed bars may be accepted. Check exact symbol, interval, requested/observed bounds, duplicate/invalid rows, overlapping corrections and gaps. Do not synthesize, interpolate, forward-fill or automatically classify gaps as no-trade. Unresolved gaps must fail closed and be separately reconciled with authoritative evidence.
5. **Provenance:** each capture must produce a compact manifest with endpoint/archive URLs, acquisition timestamp, requested bounds, observed bounds, row counts, gap/duplicate validation, per-file SHA-256 and storage/artifact identifiers. Preserve enough evidence to merge later capture segments reproducibly.
6. **Automation:** use a trusted scheduled workflow plus `workflow_dispatch` fallback. Select a conservative schedule and explicit timeout. Low-trust issue-comment workflows must not write caches. Monitor schedule reliability and fail loudly if a capture is missed or incomplete.
7. **Tests:** add deterministic tests for UTC normalization, closed-hour selection, overlap deduplication, append/merge ordering, gap detection, duplicate detection, checksums, partial/failed acquisition and storage failure. Run CI and one bounded end-to-end capture.
8. **Report and handoff:** document the chosen retention/storage design, verified limits, exact capture run and artifact links, current coverage, gaps, test results, and whether the holdout can be preserved for at least **180 days**. Do not claim durability beyond verified retention.

## Execution result — 2026-11-23

**Implementation and initial end-to-end capture: PASS.** The workflow, capture module, tests and queue-guardian integration were committed atomically in [39b1682](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/39b1682baf32ad066af3dec4ec3d57e57c7836f9).

- Full CI [45242120532](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242120532): 258 deterministic tests and synthetic plumbing smoke passed.
- Capture [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210): authorization passed for the owner-only exact command; all 17 dedicated tests passed; the capture and release upload succeeded.
- Coverage: 2026-11-01 00:00 UTC through 2026-11-23 17:00 UTC, 546 rows each for ETHUSDT/BTCUSDT; zero gaps, duplicates, corrections or source errors; closed bars only.
- Durable snapshot: [release asset](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-45242319210-attempt-1.zip), ID `784136576`, 63,517 bytes, SHA-256 `b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`. Release assets have no Actions-artifact expiry, but the release is not platform-immutable and can be deleted.
- Manifest artifact: [14852546156](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210/artifacts/14852546156), 1,363 bytes, 30-day retention through 2026-12-23 18:49 UTC. The ZIP's embedded manifest predates the post-upload storage metadata; the GitHub Release API supplies the asset ID/digest.
- The exact issue-comment route is end-to-end validated. A GitHub `schedule` event was later observed on 2026-11-24 at 14:59:10 UTC, 10h36m10s after its nominal 04:23 UTC due time; it returned `idempotent_slot_reuse=true` and reused the already published slot without creating duplicate Release assets. The actual `workflow_dispatch` event remains unexercised.
- No backtest, model selection, funding access, credentials, paid purchase, raw-data Git commit or live trading occurred.

## Acceptance criteria

- [x] No duplicate workflow or storage path created without preflight justification.
- [x] Backfill begins at 2026-11-01 and ends only at a verified latest-closed hourly bar.
- [x] Public Binance Spot data only; no credentials, trading, funding, other venues or access bypass.
- [x] Every accepted bar is timestamp/symbol/interval validated; the initial capture had no unresolved gaps.
- [x] Overlap/backfill and deterministic deduplication are implemented and tested.
- [x] Manifests and hashes are retained; raw market data is outside Git.
- [x] A GitHub Release asset with no automatic Actions-artifact expiry is used; it can still be deliberately deleted because the release is not immutable. Recovery behavior is implemented and unit-tested.
- [x] A GitHub schedule event was exercised late on 2026-11-24; it verified/reused the existing slot and created no duplicate Release assets.
- [ ] An actual `workflow_dispatch` event remains unexercised; no claim of manual-dispatch validation is made. The exact owner-only issue-comment route and scheduled event are validated.
- [x] CI and one end-to-end capture pass; the Actions artifact contains only the manifest, while the durable release asset contains the required public market-data snapshot.
- [x] No empirical strategy evaluation occurred during this task.

## Completion decision

The implementation and initial end-to-end capture passed within the consumed cycle. Do not extend this task. The first scheduled-run/recovery follow-up is documented separately. The late schedule event does not validate `workflow_dispatch` or an independent external scheduler. The next model remains unselected until a new, separate preregistration and timebox are committed.
