# Prospective Binance Spot Holdout Capture — Initial Implementation and Capture

**Date:** 2026-11-23  
**Status:** Initial implementation and one end-to-end capture passed; scheduled/manual-event validation pending.  
**Scope:** Binance Spot ETHUSDT/BTCUSDT hourly data only. No strategy evaluation.

## Repository and CI

- Main commit: [39b1682baf32ad066af3dec4ec3d57e57c7836f9](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/39b1682baf32ad066af3dec4ec3d57e57c7836f9).
- Added `.github/workflows/spot-holdout-capture.yml`, `research/spot_holdout_capture.py` and `research/test_spot_holdout_capture.py`; queue guardian now listens for completion of the capture workflow.
- Full CI: [run 45242120532](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242120532), **258 deterministic tests passed** and the synthetic plumbing smoke test passed.
- Capture workflow reran **17 dedicated tests**, all passing.

## End-to-end capture

- Run: [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), event `issue_comment`, owner actor, exact command `/qfr-capture-spot-holdout` on open draft PR #2.
- Authorization job passed; capture job checked out `main`, ran the dedicated tests, fetched public Binance Spot klines, uploaded the release asset and uploaded a manifest-only Actions artifact.
- Requested interval: **2026-11-01 00:00 UTC to 2026-11-23 17:00 UTC**, inclusive hourly opens.
- ETHUSDT: **546 rows**, zero missing hours, duplicates, overlap corrections or source errors.
- BTCUSDT: **546 rows**, zero missing hours, duplicates, overlap corrections or source errors.
- Both series are sorted, UTC-hour-aligned, closed-bars-only, and marked complete. No bars were synthesized, forward-filled or classified as no-trade.
- The manifest explicitly sets `research_evaluation_authorized=false`.

## Data and storage provenance

| Item | Value |
|---|---|
| Release | [spot-holdout-2026](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026) |
| Snapshot asset | [snapshot-45242319210-attempt-1.zip](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-45242319210-attempt-1.zip) |
| Asset ID | `784136576` |
| ZIP size | 63,517 bytes |
| ZIP SHA-256 | `b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf` |
| ETHUSDT CSV SHA-256 | `81c00f22d2c8f61cbdd9ef1a97e3844a36a12686e865c1948143d87db41fdd81` |
| BTCUSDT CSV SHA-256 | `b5b6ae7d40e823a9dfb3efb821bf25cff5eee8e522e53763143bd0768d570c7c` |
| Manifest-only Actions artifact | [14852546156](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210/artifacts/14852546156), 1,363 bytes |
| Actions artifact expiry | 2026-12-23 18:49 UTC |

The snapshot is stored as a GitHub Release asset rather than an Actions artifact, so it has no 30-day Actions-artifact expiry. The release API reported `immutable=false`; therefore this is **not** write-once storage and can be removed by someone with sufficient repository permissions. Under normal operation there is no automatic 180-day expiry, but deliberate deletion/repository removal is not prevented.

The ZIP is assembled before the upload response exists, so its embedded `manifest.json` has `storage: null`. The separate Actions manifest artifact records the post-upload asset ID, URL and digest, but expires after 30 days; GitHub Release API metadata also records the asset identity and digest. The next task must verify the next snapshot and decide whether to add a durable sidecar manifest. Do not describe the release as platform-immutable.

## Automation and governance

- Schedule: daily at 04:23 UTC.
- Manual fallback: `workflow_dispatch`, restricted to the repository owner on `main`.
- Additional fallback: exact owner-only issue-comment command on open PR #2.
- Capture timeout: 20 minutes.
- The issue-comment path was exercised successfully. A scheduled event and an actual `workflow_dispatch` event have not yet been exercised.
- The same issue comment also triggered the ETH/BTC research workflow, but every research execution job was skipped by its exact-command authorization gate; no model or funding job ran.
- Queue guardian [run 45242393950](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242393950) completed with zero actions and zero errors.
- At handoff: zero queued, requested or in-progress workflow runs; PR #2 remains open/draft; seven branches remain; the complete recursive tree contains 87 tracked files and no committed raw market-data files. Main branch protection is disabled; no settings were changed.

## Scientific and safety boundary

The closed Spot Relative-Momentum Rotation remains **NO-GO**; this capture does not reopen it or provide a new performance sample. The original USDⓈ-M funding-aware study remains **INCONCLUSIVE** because funding inputs are unaccepted. No funding data, paid data, credentials, other venues, backtests, strategy optimization, live trading or capital deployment were used or authorized.

## Next task

[Prospective Spot Holdout — First Scheduled Run and Recovery Validation](../tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md) is the single canonical next task. It must inspect the first daily scheduled capture expected after 2026-11-24 04:23 UTC, validate previous-snapshot reconciliation and queue guardian handoff, and review durable manifest provenance.
