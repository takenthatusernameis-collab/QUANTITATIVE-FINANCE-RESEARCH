# Prospective Spot Holdout — External Dispatch and Recovery Validation

**Status:** IN PROGRESS — GitHub cron event due 2026-11-24 04:23 UTC did not create a capture run; use the first authorized agent wake-up after the due time as the direct-execution fallback; stable daily slot idempotency is being added; external scheduler/watchdog remain unprovisioned
**Latest checkpoint:** [2026-11-24 07:15 UTC scheduled-run checkpoint](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md).  
**Priority:** P1 research-enabling infrastructure  
**Task budget:** 1 substantive cycle; hard deadline **2026-11-25 17:30 UTC**. No automatic extension.

## Context

The initial prospective Binance Spot capture is implemented and has one successful owner-authorized end-to-end run. See [capture report](../reports/PROSPECTIVE-BINANCE-SPOT-HOLDOUT-CAPTURE-2026-11-23.md), [workflow run 45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), and [release snapshot](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026).

The workflow still declares `23 4 * * *` UTC, but GitHub explicitly treats scheduled events as best-effort: they may be delayed or dropped. The first expected event on **2026-11-24 04:23 UTC** did not create a capture run. **Do not rely on this cron, wait for the next tick, or use it as the task's completion criterion.** Preferred trigger: an independently operated authenticated scheduler through a protected GitHub dispatch route. **Mandatory backup:** the first authorized agent that wakes after the due time must inspect the current slot and directly initiate the missing capture through the existing exact-owner PR-comment route or another already-authorized runner; do not park the task because an external scheduler is unconfigured. The operation is now keyed to one UTC daily slot, so later agents and automation must verify/reuse the same slot rather than append duplicates. Compute the latest closed hourly bar and expected rows from the actual verified execution timestamp; never infer them from the planned schedule.

## Objective

Verify that an independently scheduled and authenticated dispatch appends a new, complete snapshot, validates and reconciles the previous snapshot, preserves provenance and retention, and leaves the queue guardian healthy. Resolve any concrete durability/provenance defect within the same bounded cycle. This is a data-infrastructure task only. Its ETHUSDT/BTCUSDT symbol scope is deliberately specific to this capture validation and must not be copied into a factory-wide asset whitelist, treated as the default future research universe, or used to restrict candidate discovery after this task closes. See [Asset-Universe Discovery and Scope Policy](../docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md).

## Parallel workstream isolation

- Workstream ID: `spot-holdout-first-scheduled-validation`.
- Status: primary active workstream.
- Write scope and exclusive resources are registered in the [canonical queue](ACTIVE-QUEUE.md).
- Protected data identity: `binance-spot-1h:prospective-2026-11`.
- This task keeps its existing one-cycle budget and 2026-11-25 17:30 UTC deadline. The factory's newly adopted parallel-workstream policy does not reset or retroactively re-rate it.

## Required steps

1. Inspect the latest main commit, active queue, open PR #2 comments, workflow runs, queue guardian report and current release assets before any dispatch. Do not duplicate a successful capture or overlap an active run.
2. After the daily due time, inspect the release for `snapshot-slot-YYYY-MM-DD.zip`, its JSON sidecar, the Actions inventory and active runs. If the slot is absent and no valid capture is active, the first authorized agent wake-up must trigger the existing owner-exact `/qfr-capture-spot-holdout` command on open PR #2 (or use an independently authenticated scheduler if verified). Confirm the resulting event/actor, stable slot ID, `main` ref, authorization job, capture job, actual start time and 20-minute timeout. If the slot already exists, verify and reuse it; do not dispatch again. A GitHub cron run is opportunistic only and cannot satisfy the independent scheduler-reliability criterion.
3. Verify the new release asset and manifest: exact ETHUSDT/BTCUSDT identity, 1h interval, UTC bounds, latest fully closed bar, expected/observed counts, no duplicates, ordering, missing hours, overlap corrections and source errors. A missing hour must remain unresolved and fail closed; never synthesize or forward-fill.
4. Confirm the new snapshot's `previous_snapshot` points to the preceding asset and that the previous ZIP digest and both CSV hashes were verified before merge. Check that both snapshots remain in the same release and no prior asset was overwritten.
5. Verify the implemented durable JSON sidecar. Each capture now publishes a unique `snapshot-<run>-attempt-<n>.manifest.json` Release asset containing the ZIP asset ID/URL/size/digest and per-file SHA-256 hashes; the next run also backfills a sidecar for the first ZIP before appending the next snapshot. Deterministic tests cover sidecar validation, idempotent reuse, collision rejection, previous-snapshot backfill and current-snapshot publication. Confirm the sidecar contains metadata only, is not uploaded as an Actions artifact, and its own ID/digest is available from Release API metadata.
6. Review the release's `immutable` metadata and retention behavior. The first release reported `immutable=false`; describe retention as no automatic artifact TTL, not write-once protection. Do not claim protection from deliberate deletion. Do not change repository or release permissions.
7. Verify the queue guardian's `workflow_run` handoff after the scheduled capture: no orphaned/duplicate runs, no enforcement action without a policy violation, no errors. Confirm no queued, requested or in-progress workflow runs remain.
8. Provision and verify the independent scheduler/dispatcher when an authorized provider/credential is available. Preferred route: a dedicated GitHub App installation token with repository-scoped `Actions: write`, stored only in the external scheduler's secret manager, calling the existing `workflow_dispatch` endpoint. Verify and explicitly allowlist its exact actor before use; do not accept arbitrary actors. A narrowly scoped owner-bound fine-grained token is a fallback only if explicitly authorized. Dispatch must carry the deterministic capture-slot key, and the scheduler must poll Actions until the expected run is observed. **The absence of this external service is not a stop-work condition:** the first agent waking after the due time must use the already-authorized exact PR-comment route and observe the real run. If neither that route nor another authorized execution surface is available, record the precise owner-only prerequisite and continue independent safe work; never wait for GitHub cron.
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
## Acceptance criteria

- [ ] An independently scheduled authenticated dispatch is observed with the exact workstream slot/idempotency key, expected actor, workflow ID, default-branch ref and run timestamps.
- [ ] New snapshot reconciles the previous release asset and preserves every prior observation unless a source correction is explicitly recorded.
- [ ] Both symbols have exact identity, closed hourly bars, UTC ordering and complete or explicitly rejected coverage.
- [ ] Release assets are append-only by workflow policy; no prior snapshot is overwritten or deleted.
- [x] Durable sidecar implementation, strict digest/size checks, idempotency/collision tests and the `immutable=false` retention limitation are committed and documented.
- [ ] Live sidecar backfill/publication for the first ZIP and the next ZIP is verified by the scheduled run.
- [ ] Retention claims distinguish no automatic TTL from protection against manual deletion.
- [ ] Queue guardian handoff is successful and no orphaned/duplicate active run remains.
- [x] CI passes after the latest implementation/policy changes: 300 deterministic tests and the synthetic plumbing smoke test succeeded in [run 45308874842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45308874842); no raw market data is committed.
- [ ] No empirical strategy evaluation, funding research or live trading occurs.

## Stop conditions

- GitHub `schedule` events are not a delivery guarantee. Never park the task until another cron tick. If external dispatch is absent, diagnose the external scheduler's delivery log and GitHub API response; retry only with the same idempotency key after checking whether a run was already created. Keep the holdout closed.
- If either symbol has missing, revised or malformed rows, publish only an explicitly incomplete snapshot and preserve the gap/correction evidence. Never promote incomplete data to a holdout.
- If durable retention depends on an unavailable owner-only setting, keep the existing release snapshot, mark the limitation precisely and continue independent safe validation.
- Do not extend the one-cycle deadline. The next model remains unselected until a separate preregistration and independent holdout are available.


## Trigger reliability correction — 2026-11-24

The previous plan incorrectly treated GitHub Actions cron as a dependable clock and made the next natural cron boundary the recovery plan. This is explicitly superseded. GitHub documents `schedule` as best-effort and permits delay/drop under load: [official event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). The 2026-11-24 04:23 UTC capture event did not create a run; the initial successful capture was owner-authorized via `issue_comment` (run [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210)).

The replacement is an independently operated scheduler that actively calls the protected `workflow_dispatch` route, using a dedicated least-privilege GitHub App identity, a deterministic per-slot idempotency key, durable dispatch/run records, bounded retry with duplicate detection, and a watchdog in a separate scheduling/control domain. GitHub cron may remain only as an opportunistic canary or be removed once external dispatch is live; it is never the primary clock or deadline guarantee. Before enabling simultaneous triggers, either disable the cron capture path or prove run-level idempotency across both routes.

**Do not wait for the next GitHub cron tick.** The connected GitHub action catalog currently exposes read operations and repository writes but no direct workflow-dispatch POST; no scheduler provider, GitHub App installation, dispatch credential or external watchdog has been provisioned/verified in this session. The workflow's existing exact-actor gate remains intact. The policy, handoff and regression checks are being committed now; external credential provisioning and end-to-end dispatch delivery remain explicitly unverified. Do not claim the replacement is operational until a real external dispatch is observed and reconciled.


## First-agent wake-up fallback — activated 2026-11-24

The November 24 daily slot became due at **2026-11-24 04:23 UTC**. No schedule-triggered capture run or second release asset existed at the inspected checkpoint. Under the factory's new direct-execution fallback, the first authorized agent wake-up after that due time must perform the capture rather than wait for another cron or for an unprovisioned external scheduler.

- Stable slot: `binance-spot-1h:prospective-2026-11:2026-11-24`.
- Expected durable assets: `snapshot-slot-2026-11-24.zip` and `snapshot-slot-2026-11-24.manifest.json`.
- Before starting: inspect all Actions attempts and release assets; do not run while an authorized capture for this slot is active or after its verified snapshot exists.
- Authorized direct fallback: create the exact `/qfr-capture-spot-holdout` comment on open PR #2 only when the connected GitHub identity is verified as `takenthatusernameis-collab`; the workflow's existing exact-actor gate remains unchanged.
- The capture workflow's concurrency group serializes competing starts. The script must check the stable slot asset and fully verify its ZIP/sidecar digests before any fetch; a second run reuses the existing result. An incomplete snapshot is not overwritten; it is reported for diagnosis and any recovery uses the same prior data plus a separately justified attempt.
- Execution timestamp and latest closed bar are derived from the actual run, never backdated to 04:23 UTC.
- The independent watchdog remains required for a future externally scheduled deployment. Until it is provisioned, the direct-agent wake-up fallback checks the live Actions inventory and release state; it does not pretend to provide a continuous heartbeat.
- After the run, verify the exact event/actor/ref, jobs, ZIP and sidecar metadata, both CSV hashes, prior-snapshot reconciliation and queue-guardian completion. Keep empirical strategy evaluation disabled.

This wake-up fallback restores progress without claiming that an external scheduler is operational. Direct agent execution is a last line of defense, not a replacement for independently monitored scheduling.
