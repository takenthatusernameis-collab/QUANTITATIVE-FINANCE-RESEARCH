# Prospective Binance Spot Holdout Capture

**Status:** PENDING — next bounded task  
**Priority:** P1 research-enabling infrastructure  
**Task budget:** 1 substantive cycle; hard deadline **2026-11-24 17:30 UTC**. No automatic extension.

## Context

The frozen ETH/BTC Spot Relative-Momentum Rotation concluded NO-GO on 2026-11-23. Do not tune, re-filter or reinterpret its 2022-01 through 2026-10 OOS sample. Any new strategy must be separately preregistered and evaluated on an independent/later holdout.

The accepted historical Spot archive ends at **2026-10-31**. A prospective holdout can begin **2026-11-01**, with official public data backfilled to the latest closed hour. No prospective-capture workflow is currently listed in the repository's workflow tree.

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

## Acceptance criteria

- [ ] No duplicate workflow or storage path created without preflight justification.
- [ ] Backfill begins at 2026-11-01 and ends only at a verified latest-closed hourly bar.
- [ ] Public Binance Spot data only; no credentials, trading, funding, other venues or access bypass.
- [ ] Every accepted bar is timestamp/symbol/interval validated; unresolved gaps are explicitly rejected/flagged.
- [ ] Overlap/backfill and deterministic deduplication are implemented and tested.
- [ ] Manifests and hashes are retained; raw market data is outside Git.
- [ ] Storage retention and recovery behavior are verified. If 180-day retention cannot be achieved with authorized resources, mark the task **BLOCKED/INFEASIBLE**, preserve any safe partial capture, and identify the exact owner-only prerequisite instead of pretending the holdout is durable.
- [ ] Scheduled workflow, manual fallback, timeout and fail-closed behavior are validated.
- [ ] CI and one end-to-end capture pass; artifacts contain no raw data unless an approved, explicitly configured storage destination requires it.
- [ ] No empirical strategy evaluation occurs during this task.

## Completion decision

Within the one-cycle deadline, either commit a verified minimal capture system and its evidence, or report **BLOCKED/INFEASIBLE** with the exact storage/permission/retention limitation and a safe partial result. Do not extend the task indefinitely. The next model remains unselected until a new, separate preregistration and timebox are committed.
