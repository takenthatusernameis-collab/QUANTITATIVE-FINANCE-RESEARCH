# Prospective Spot Holdout — Capture and First-Agent Recovery Validation

**Status:** COMPLETE — November 24 slot RECOVERED by first-authorized-agent wake-up; complete snapshot and sidecars verified; second same-slot wake-up proved idempotent reuse. External scheduler/watchdog remain UNCONFIGURED and are not represented as DELIVERY_VERIFIED.
**Latest checkpoint:** [2026-11-24 10:22 UTC final recovery checkpoint](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md).  
**Priority:** P1 research-enabling infrastructure  
**Task budget:** 1 substantive cycle; hard deadline **2026-11-25 17:30 UTC**. No automatic extension.

## Context

The initial prospective Binance Spot capture is implemented and has one successful owner-authorized end-to-end run. See [capture report](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-CAPTURE-2026-11-23.md), [workflow run 45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), and [release snapshot](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026).

The workflow still declares `23 4 * * *` UTC, but GitHub explicitly treats scheduled events as best-effort: they may be delayed or dropped. The first expected event on **2026-11-24 04:23 UTC** did not create a capture run. **Do not rely on this cron, wait for the next tick, or use it as the task's completion criterion.** Preferred trigger: an independently operated authenticated scheduler through a protected GitHub dispatch route. **Mandatory backup:** the first authorized agent that wakes after the due time must inspect the current slot and directly initiate the missing capture through the existing exact-owner PR-comment route or another already-authorized runner; do not park the task because an external scheduler is unconfigured. The operation now carries a stable UTC daily slot idempotency key, so later agents and automation must verify/reuse the same slot rather than append duplicates. Compute the latest closed hourly bar and expected rows from the actual verified execution timestamp; never infer them from the planned schedule.

## Objective

Verify the first due prospective capture using either an independently operated authenticated scheduler or, when that is unavailable, the first authorized agent wake-up after the due time. Reconcile the previous snapshot, publish and validate current ZIP/sidecar assets, prove same-slot idempotent reuse, and verify the queue-guardian completion handoff. This is a data-infrastructure task only. Its ETHUSDT/BTCUSDT symbol scope is deliberately specific to this capture validation and must not be copied into a factory-wide asset whitelist, treated as the default future research universe, or used to restrict candidate discovery after this task closes. See [Asset-Universe Discovery and Scope Policy](../docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md).

## Parallel workstream isolation

- Workstream ID: `spot-holdout-first-scheduled-validation`.
- Status: primary active workstream.
- Write scope and exclusive resources are registered in the [canonical queue](ACTIVE-QUEUE.md).
- Protected data identity: `binance-spot-1h:prospective-2026-11`.
- This task keeps its existing one-cycle budget and 2026-11-25 17:30 UTC deadline. The factory's newly adopted parallel-workstream policy does not reset or retroactively re-rate it.

## Required steps

1. Inspect the latest main commit, active queue, open PR #2 comments, workflow runs, queue guardian report and current release assets before any dispatch. Do not duplicate a successful capture or overlap an active run.
2. After the daily due time, inspect the release for `snapshot-slot-YYYY-MM-DD.zip`, its JSON sidecar, the Actions inventory and active runs. If the slot is absent and no valid capture is active, the first authorized agent wake-up must trigger the existing owner-exact `/qfr-capture-spot-holdout` command on open PR #2 (or use an independently authenticated scheduler if verified). Confirm the event/actor, stable slot ID, `main` ref, authorization job, capture job, actual start time and 20-minute timeout. If the slot already exists, verify and reuse it; do not dispatch again. GitHub cron is opportunistic only.
3. Verify the new release asset and manifest: exact ETHUSDT/BTCUSDT identity, 1h interval, UTC bounds, latest fully closed bar, expected/observed counts, no duplicates, ordering, missing hours, overlap corrections and source errors. A missing hour must remain unresolved and fail closed; never synthesize or forward-fill.
4. Confirm the new snapshot's `previous_snapshot` points to the preceding asset and that the previous ZIP digest and both CSV hashes were verified before merge. Check that both snapshots remain in the same release and no prior asset was overwritten.
5. Verify the implemented durable JSON sidecar. Each capture now publishes a deterministic per-slot `snapshot-slot-YYYY-MM-DD.manifest.json` Release asset containing the ZIP asset ID/URL/size/digest and per-file SHA-256 hashes; the next run also backfills a sidecar for the first ZIP before appending the next snapshot. Deterministic tests cover sidecar validation, idempotent reuse, collision rejection, previous-snapshot backfill and current-snapshot publication. Confirm the sidecar contains metadata only, is not uploaded as an Actions artifact, and its own ID/digest is available from Release API metadata.
6. Review the release's `immutable` metadata and retention behavior. The first release reported `immutable=false`; describe retention as no automatic artifact TTL, not write-once protection. Do not claim protection from deliberate deletion. Do not change repository or release permissions.
7. Verify the queue guardian's `workflow_run` handoff after the scheduled capture: no orphaned/duplicate runs, no enforcement action without a policy violation, no errors. Confirm no queued, requested or in-progress workflow runs remain.
8. Record external scheduler provisioning separately. A dedicated repository-scoped GitHub App and separate watchdog remain the preferred long-term scheduling architecture, but they are not available in this task. Do not weaken actor gates, invent credentials or claim `DELIVERY_VERIFIED`. The November 24 slot is permitted to close as `RECOVERED` because the first-agent fallback was executed through the existing exact-owner route and independently replayed idempotently.
9. Run the relevant deterministic tests and full CI if code changes are made. Commit one atomic Git Data handoff to `main`; update the report, README and canonical queue in the same commit.
10. Do not run any strategy backtest, optimize the closed Spot Momentum model, inspect signals/performance, access unaccepted funding, purchase data, add credentials, use other venues or authorize live trading.

## Implementation progress — 2026-11-23

- Added a durable, append-only JSON Release sidecar for each ZIP. The sidecar records the ZIP asset ID, URL, size, GitHub SHA-256 digest, archive SHA-256, release immutability state and per-file SHA-256 hashes.
- Added automatic backfill of the previous ZIP's sidecar before the next snapshot is published. The first snapshot's sidecar is therefore expected to be created during the first scheduled run.
- The ZIP now embeds the unique sidecar asset name before it is published. The ZIP's own post-upload ID/digest is stored in the sidecar, avoiding a self-referential ZIP checksum.
- Release-asset reuse requires exact GitHub digest, size and identity metadata. Previous snapshot restore now fails closed if the GitHub digest or asset size is missing/mismatched.
- The capture workflow conditionally corrects the legacy release description only when it exactly matches the old "immutable" wording and the release API says the release is not immutable. No permissions or protection settings are changed.
- Added deterministic tests for sidecar structure, previous-snapshot backfill, current-snapshot publication, idempotent reuse, collision rejection, digest requirements and release-description correction. The first full CI run [45247197778](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45247197778) found one test-harness argument mismatch; the ZIP upload now passes `application/zip` explicitly. Follow-up CI run [45247539131](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45247539131) passed **264 deterministic tests** and the synthetic plumbing smoke test.

## Pre-schedule checkpoint — 2026-11-24 01:58 UTC

- The first scheduled capture at 04:23 UTC had not yet become due. No schedule-triggered capture run or second release asset existed at this checkpoint. No manual or duplicate capture was dispatched.
- The current release still contains only the initial ZIP [asset 784136576](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026), with `immutable=false`; the first durable sidecar backfill therefore remains pending the next successful capture.
- Queue guardian event-driven handoff [45306164079](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45306164079) completed successfully at 01:35:30 UTC in LIVE_ENFORCEMENT mode. Its report recorded no actions and no errors; run enumeration completed, while the 375-item inventory was explicitly truncated. The most recent scheduled guardian run remains [45273577143](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45273577143) at 2026-11-23 21:49:36 UTC. Thus event-driven operation has one successful recent check, but the configured five-minute cron has not demonstrated a five-minute cadence. GitHub documents schedule delivery as best-effort and subject to delay/drop under high load: [schedule event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
- Three unrelated Dependabot issue-comment events on closed PR #8 triggered the capture workflow; the exact authorization gate rejected the bot/target/command and the capture job was skipped. No market data was fetched by those runs.
- A separate workstream-policy boundary fixture initially failed because the test treated an exact two-day LOW-tier ceiling as invalid. The implementation correctly allows the exact ceiling and rejects only an expiry beyond it. The fixture now uses two days plus one second, with a new exact-boundary acceptance test. Full CI [45308874842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45308874842) passed **300 deterministic tests** and the synthetic plumbing smoke test on `ca112f1`. This was a test-fixture correction, not a relaxation or implementation defect.
- The recursive remote Git tree contained 113 entries and no disposable cache, scratch, temporary, or generated-data candidates. Local untracked state is not observable through the remote GitHub view; no remote cleanup deletion was justified.
- No strategy backtest, signal/performance inspection, funding research, paid-data acquisition, venue merge, credential creation, live trading or capital deployment occurred.

The next checkpoint must inspect the actual schedule-triggered capture and its queue-guardian completion handoff. Do not dispatch a duplicate to compensate for an event that has not yet become due or is merely delayed.


## Post-schedule checkpoint — 2026-11-24 04:33 UTC

- The scheduled capture workflow remains present on the default branch main and declares cron 23 4 * * * UTC. Main was at [79057751](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/79057751de40bd7862416ff6de90a51d0aee9f75). A fresh Actions query for runs created at or after 04:23 UTC returned **zero**; no schedule-triggered capture had appeared by this checkpoint. The authorization/capture jobs therefore have no new run to inspect.
- No queued or in-progress Actions runs were present. PR #2 remains open and the last owner command remains the prior /qfr-capture-spot-holdout; no newer command was issued.
- Release [spot-holdout-2026](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026) still contains only ZIP asset [784136576](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-45242319210-attempt-1.zip), size 63,517 bytes, GitHub digest sha256:b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf. No JSON sidecar or second ZIP is present. Release metadata remains immutable=false; its description still uses the word immutable, so do not treat it as write-once storage.
- The queue guardian still declares a five-minute schedule, but its latest observed scheduled run remains [45273577143](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45273577143) at 2026-11-23 21:49:36 UTC. Its latest qualifying event-driven run is [45306164079](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45306164079), completed at 01:35:30 UTC with no actions or errors; its 375-run inventory was truncated. No later scheduled or event-driven run was visible by this checkpoint.
- The capture schedule and queue-guardian schedule are configured on the default branch; no configuration defect was identified in the inspected workflow files. GitHub schedule delivery is best-effort and may be delayed or dropped. **Do not manually dispatch or duplicate the capture** merely because the scheduled event is not yet visible. Recheck the run inventory and release before taking any further action.
- Latest main CI run [45309054784](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45309054784) completed successfully on this main commit. The preceding full run [45308874842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45308874842) passed 300 deterministic tests and the synthetic plumbing smoke test. This is engineering validation only; no new holdout data or strategy evidence was produced.
- No backtest, strategy/performance inspection, funding access, paid-data acquisition, venue merge, credential creation, live trading or capital deployment occurred.
## Acceptance criteria — final disposition 2026-11-24

- [x] The missing due slot was recovered by the first authorized agent wake-up after 04:23 UTC, through the existing exact-owner PR #2 command. Capture run [45373419544](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544) passed the actor gate and capture job.
- [x] Stable slot `binance-spot-1h:prospective-2026-11:2026-11-24` produced exactly one ZIP and one JSON sidecar, with deterministic names and verified GitHub digests.
- [x] ETHUSDT and BTCUSDT each have 562 closed, ordered hourly observations from 2026-11-01 00:00 UTC through 2026-11-24 09:00 UTC; zero missing hours, duplicate timestamps, overlap corrections or source errors.
- [x] The new manifest links the previous ZIP asset 784136576 and its verified digest; the previous snapshot's sidecar was backfilled as asset 786684146.
- [x] Current ZIP asset 786684218 (65,817 bytes; SHA-256 `22bd362b7c0db51c7a3302f5b09c1a4a2327a4d9553b8ac7259f2a343c5caade`) and sidecar asset 786684257 (5,211 bytes; SHA-256 `57cb7b1d297c15a33aa80784a0b72e010988e3da99a0e65171174ce02e19d284`) are present in Release `spot-holdout-2026`.
- [x] A second same-slot owner-authorized wake-up [45373703705](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373703705) returned `idempotent_slot_reuse=true`, verified/reused the same asset IDs and did not create additional release assets.
- [x] Release immutability and retention are described accurately: `immutable=false`; Release assets have no automatic Actions-artifact TTL but can still be deliberately deleted.
- [x] Queue-guardian event-driven handoffs [45373479882](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373479882), [45373736534](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373736534) and [45373756502](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373756502) succeeded.
- [x] Main CI [45373689039](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373689039) passed 320 deterministic tests and the synthetic plumbing smoke test; capture workflow tests passed in both capture runs.
- [x] No strategy backtest, empirical strategy evaluation, funding research, paid-data acquisition, venue merge, live trading or capital deployment occurred.

## Residual factory-wide reliability gap — not a blocker to this recovered slot

The independent external scheduler, dedicated GitHub App dispatch credential and watchdog in a separate failure domain remain `UNCONFIGURED / DEGRADED`. Do not claim `DELIVERY_VERIFIED`. The per-slot recovery state is `RECOVERED` because the first-agent fallback succeeded and a second wake-up proved idempotent reuse. These states are deliberately separate. Future time-sensitive work must continue to use the first-authorized-agent fallback when no reliable scheduler is provisioned; an unresolved external scheduler gap must not stall independent safe research.

## Stop conditions and handoff

- Never use GitHub Actions cron as the primary clock, deadline guarantee or recovery plan.
- Before any same-slot retry, inspect Actions, release assets and active runs; reuse a complete verified result, observe a valid active run, or proceed with bounded recovery only if the slot is missing/incomplete.
- Never overwrite an incomplete or conflicting snapshot, forward-fill missing market observations, backdate acquisition time, weaken authorization gates or bypass external-data restrictions.
- The external scheduler/watchdog gap remains a separate meta-process improvement; provision only when an authorized provider/identity is available. The next ready workstream is the [Post-Holdout Research Environment and Portfolio Review](POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md).
