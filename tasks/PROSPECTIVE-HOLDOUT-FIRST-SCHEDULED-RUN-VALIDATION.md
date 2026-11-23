# Prospective Spot Holdout — First Scheduled Run and Recovery Validation

**Status:** PENDING — next bounded task  
**Priority:** P1 research-enabling infrastructure  
**Task budget:** 1 substantive cycle; hard deadline **2026-11-25 17:30 UTC**. No automatic extension.

## Context

The initial prospective Binance Spot capture is implemented and has one successful owner-authorized end-to-end run. See [capture report](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-CAPTURE-2026-11-23.md), [workflow run 45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), and [release snapshot](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026).

The daily schedule is `23 4 * * *` UTC. The first scheduled run is expected after **2026-11-24 04:23 UTC**. At that time, if the run starts after 04:00 UTC, the latest closed hourly open should be 2026-11-24 03:00 UTC, giving 556 expected hourly rows per symbol from 2026-11-01 00:00 UTC. Verify actual run timestamps rather than assuming the schedule fired.

## Objective

Verify that the scheduled capture appends a new, complete snapshot, validates and reconciles the previous snapshot, preserves provenance and retention, and leaves the queue guardian healthy. Resolve any concrete durability/provenance defect within the same bounded cycle. This is a data-infrastructure task only.

## Required steps

1. Inspect the latest main commit, active queue, open PR #2 comments, workflow runs, queue guardian report and current release assets before any dispatch. Do not duplicate a successful capture or overlap an active run.
2. Find the first run triggered by `schedule` after 2026-11-24 04:23 UTC. Confirm the authorization and capture jobs completed, the capture used `main`, and the 20-minute timeout was respected.
3. Verify the new release asset and manifest: exact ETHUSDT/BTCUSDT identity, 1h interval, UTC bounds, latest fully closed bar, expected/observed counts, no duplicates, ordering, missing hours, overlap corrections and source errors. A missing hour must remain unresolved and fail closed; never synthesize or forward-fill.
4. Confirm the new snapshot's `previous_snapshot` points to the preceding asset and that the previous ZIP digest and both CSV hashes were verified before merge. Check that both snapshots remain in the same release and no prior asset was overwritten.
5. Inspect the durable ZIP manifest and the 30-day Actions manifest artifact. The first implementation writes the ZIP before attaching post-upload storage metadata, so the embedded `storage` field is null while the Actions manifest has the asset ID/digest. Decide whether a durable JSON sidecar should be published; if implementing one, use a unique append-only name, include the ZIP asset ID/URL/digest and per-file hashes, add deterministic idempotency/collision tests, and validate it without exposing raw data in Actions artifacts or Git.
6. Review the release's `immutable` metadata and retention behavior. The first release reported `immutable=false`; describe retention as no automatic artifact TTL, not write-once protection. Do not claim protection from deliberate deletion. Do not change repository or release permissions.
7. Verify the queue guardian's `workflow_run` handoff after the scheduled capture: no orphaned/duplicate runs, no enforcement action without a policy violation, no errors. Confirm no queued, requested or in-progress workflow runs remain.
8. Review the configured `workflow_dispatch` fallback. If an authorized direct dispatch can be exercised through an available owner-authorized path, validate it once; otherwise record that the event itself remains untested and do not impersonate the owner or weaken the exact-actor gate.
9. Run the relevant deterministic tests and full CI if code changes are made. Commit one atomic Git Data handoff to `main`; update the report, README and canonical queue in the same commit.
10. Do not run any strategy backtest, optimize the closed Spot Momentum model, inspect signals/performance, access unaccepted funding, purchase data, add credentials, use other venues or authorize live trading.

## Acceptance criteria

- [ ] First scheduled event is found and its result is independently inspected.
- [ ] New snapshot reconciles the previous release asset and preserves every prior observation unless a source correction is explicitly recorded.
- [ ] Both symbols have exact identity, closed hourly bars, UTC ordering and complete or explicitly rejected coverage.
- [ ] Release assets are append-only by workflow policy; no prior snapshot is overwritten or deleted.
- [ ] Durable manifest/provenance is complete, or a concrete limitation and safe remedy are recorded.
- [ ] Retention claims distinguish no automatic TTL from protection against manual deletion.
- [ ] Queue guardian handoff is successful and no orphaned/duplicate active run remains.
- [ ] CI passes if implementation changes are made; no raw market data is committed.
- [ ] No empirical strategy evaluation, funding research or live trading occurs.

## Stop conditions

- If the scheduled event has not fired, do not create duplicate runs merely to make the dashboard look healthy. Diagnose the event/branch configuration and preserve the exact evidence.
- If either symbol has missing, revised or malformed rows, publish only an explicitly incomplete snapshot and preserve the gap/correction evidence. Never promote incomplete data to a holdout.
- If durable retention depends on an unavailable owner-only setting, keep the existing release snapshot, mark the limitation precisely and continue independent safe validation.
- Do not extend the one-cycle deadline. The next model remains unselected until a separate preregistration and independent holdout are available.
