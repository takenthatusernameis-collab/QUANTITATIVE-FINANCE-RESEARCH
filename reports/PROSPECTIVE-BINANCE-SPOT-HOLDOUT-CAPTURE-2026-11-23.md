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

The ZIP is assembled before its own upload response exists, so it cannot contain its own post-upload asset ID/digest without a self-reference. The implementation now embeds a unique sidecar-name pointer in the ZIP and publishes a separate durable JSON sidecar after upload. The sidecar contains the ZIP asset ID, URL, size, GitHub digest, archive SHA-256 and both per-file SHA-256 hashes. The next capture also backfills this sidecar for the first snapshot before it appends the next ZIP. The sidecar's own asset ID/digest is recorded in Release API metadata and the expiring Actions manifest. GitHub reports `immutable=false`; append-only behavior is enforced by workflow collision checks, not platform write-once protection. The first snapshot remains without its sidecar until the next capture succeeds.

## Automation and governance

- Schedule: daily at 04:23 UTC.
- Manual fallback: `workflow_dispatch`, restricted to the repository owner on `main`.
- Additional fallback: exact owner-only issue-comment command on open PR #2.
- Capture timeout: 20 minutes.
- The issue-comment path was exercised successfully. A scheduled event and an actual `workflow_dispatch` event have not yet been exercised.
- The same issue comment also triggered the ETH/BTC research workflow, but every research execution job was skipped by its exact-command authorization gate; no model or funding job ran.
- Queue guardian [run 45242393950](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242393950) completed with zero actions and zero errors.
- At handoff: zero queued, requested or in-progress workflow runs; PR #2 remains open/draft; seven branches remain; the complete recursive tree contains 87 tracked files and no committed raw market-data files. Main branch protection is disabled; no settings were changed.

## Durable sidecar improvement — 2026-11-23

The capture implementation now creates a durable metadata-only JSON sidecar for each ZIP. It records the ZIP asset ID, URL, size, GitHub digest, archive SHA-256 and per-file hashes. The next capture first reconstructs and publishes a sidecar for the previous ZIP, so the initial asset will be backfilled before a second snapshot is appended. Sidecar assets use unique run/attempt names; exact digest/size matches are reused idempotently, while name collisions with different bytes fail closed.

The ZIP embeds the expected sidecar name, but its own post-upload digest remains in the sidecar to avoid a self-referential checksum. The sidecar's own asset ID/digest is held by GitHub Release API metadata and copied into the expiring Actions manifest. The release's immutable=false property is explicitly recorded; no platform write-once guarantee is claimed. The workflow will also correct the old release description's "immutable" wording on the next authorized capture if it still matches the exact legacy text.

The code and deterministic regression tests were committed to `main` in [7f672c49](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/7f672c49e4ef5f4200e19623c6152d73d61f31bf). The first full CI run [45247197778](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45247197778) ran 264 tests and found one orchestration-test argument mismatch: the ZIP upload relied on the default content type while the test expected an explicit argument. The call was corrected to pass `application/zip`; follow-up CI run [45247539131](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45247539131) passed **264 deterministic tests** and the synthetic plumbing smoke test. The next scheduled run must verify live sidecar backfill/publication and the previous ZIP restore. The first snapshot does not yet have a sidecar until that run succeeds.

## Scientific and safety boundary

The closed Spot Relative-Momentum Rotation remains **NO-GO**; this capture does not reopen it or provide a new performance sample. The original USDⓈ-M funding-aware study remains **INCONCLUSIVE** because funding inputs are unaccepted. No funding data, paid data, credentials, other venues, backtests, strategy optimization, live trading or capital deployment were used or authorized.

## Next task

[Prospective Spot Holdout — First Scheduled Run and Recovery Validation](../tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md) is the single canonical next task. It must inspect the first daily scheduled capture expected after 2026-11-24 04:23 UTC, validate previous-snapshot reconciliation and queue guardian handoff, and review durable manifest provenance.
