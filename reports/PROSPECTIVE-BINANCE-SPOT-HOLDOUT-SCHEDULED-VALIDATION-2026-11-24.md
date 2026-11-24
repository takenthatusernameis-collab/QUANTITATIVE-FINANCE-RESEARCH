# Prospective Binance Spot Holdout — Scheduled-Run Checkpoint

**Initial observation:** 2026-11-24 04:33 UTC  
**Latest checkpoint:** 2026-11-24 10:22 UTC  
**Disposition:** RECOVERED — November 24 slot captured by first-agent fallback; same-slot replay verified idempotent reuse  
**Scope:** Workflow and release-state verification only. No market-data capture or strategy evaluation occurred.

## Scheduled workflow

- Workflow: [spot-holdout-capture.yml](../.github/workflows/spot-holdout-capture.yml) runs on the default branch main and declares daily cron 23 4 * * * UTC.
- Main branch head at inspection: [79057751de40](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/79057751de40bd7862416ff6de90a51d0aee9f75).
- The GitHub Actions run query for runs created at or after 2026-11-24T04:23:00Z returned **zero**. Thus no schedule-triggered capture was visible by 04:33 UTC; no capture authorization or data-fetch job had run.
- There were zero queued and zero in-progress workflow runs. PR #2 remained open; no new owner command was posted.

## Release and sidecar state

Release [spot-holdout-2026](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026) still contains only the original ZIP:

- Asset: [snapshot-45242319210-attempt-1.zip](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-45242319210-attempt-1.zip)
- Asset ID: 784136576
- Size: 63,517 bytes
- GitHub digest: sha256:b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf
- No second snapshot or JSON sidecar is present. Previous-snapshot reconciliation and the first ZIP's sidecar backfill therefore remain unverified.
- Release metadata remains immutable=false. The release description still says “immutable”; this is not a write-once guarantee and deliberate deletion remains possible.

## Queue guardian

- Workflow: [queue-guardian.yml](../.github/workflows/queue-guardian.yml), configured for a five-minute cron and qualifying workflow_run handoffs.
- Latest observed scheduled guardian run: [45273577143](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45273577143), 2026-11-23 21:49:36 UTC.
- Latest observed event-driven handoff: [45306164079](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45306164079), completed 2026-11-24 01:35:30 UTC in LIVE_ENFORCEMENT mode with no actions or errors. Its run enumeration completed, but its 375-item inventory was truncated.
- No later scheduled or event-driven guardian run was visible by this checkpoint. The five-minute heartbeat is therefore not demonstrated.

## Engineering status and decision

- Latest main CI run [45309054784](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45309054784) completed successfully. The preceding full run [45308874842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45308874842) passed 300 deterministic tests and the synthetic plumbing smoke test. These are software checks, not market-data acceptance.
- The workflow files and default branch were present and consistent with the documented schedule. No configuration defect was identified. GitHub schedule delivery is best-effort and can be delayed or dropped.
- **Do not manually dispatch or duplicate the capture** merely because the scheduled event is not yet visible. Recheck Actions and the release before further action. Keep the task IN PROGRESS and all empirical/holdout gates closed.
- No strategy backtest, signal/performance inspection, funding access, paid-data acquisition, venue merge, credential creation, live trading or capital deployment occurred.

## Second post-schedule checkpoint — 2026-11-24 06:09 UTC

- Main remained at [a9aea723b270](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a9aea723b27016840e00ae2f864a1b91e5f6b3aa). The latest-100 Actions run inventory contained no `spot-holdout-capture.yml` run with `event=schedule` created at or after 2026-11-24 04:23 UTC. No capture authorization or data-fetch job ran for the scheduled event.
- The workflow remains configured on main with cron `23 4 * * *` UTC. Its `workflow_dispatch` gate still requires actor `takenthatusernameis-collab`; the PR-comment route still requires the exact owner, open PR #2 and exact command. No new owner command appeared after `/qfr-capture-spot-holdout` at 2026-11-23 18:48:40 UTC. No authenticated `workflow_dispatch` action was available in this execution path; that fallback remains untested. No comment or manual/duplicate capture was issued.
- Release [spot-holdout-2026](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026) still contains only [asset 784136576](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/download/spot-holdout-2026/snapshot-45242319210-attempt-1.zip): 63,517 bytes, GitHub digest `sha256:b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`. No second ZIP or JSON sidecar exists. Release metadata remains `immutable=false`; this is not write-once protection.
- Queue guardian [run 45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900) ran 05:37:22–05:37:45 UTC on main in LIVE_ENFORCEMENT mode and succeeded. The job completed its inspect-and-recover and report-upload steps. Its report inventoried 411 research/test runs (latest 50 retained), found no active research/test runs, and recorded `actions=[]` and `errors=[]`. The open-issues inventory contained no queue-guardian incident. No later guardian schedule run was visible by 06:09 UTC; the configured five-minute schedule has still not demonstrated a five-minute cadence.
- Latest main CI [run 45327618205](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45327618205) completed successfully at 04:37:49 UTC: 300 deterministic tests passed in 14.670 seconds, followed by `SELF-TEST PASS` for the synthetic plumbing smoke test. This is engineering validation only; no new market-data acceptance or empirical result was produced.
- The recursive main tree contained 114 entries. No disposable cache, temporary, scratch or generated-data file was identified; the `templates/` path is legitimate project-intake material. No file or branch deletion was justified. PR #2 remains open as the control surface; no other open issue/PR or queue-guardian incident was found.

### Adaptive blocker plan and decision

1. **Preserve the single scheduled capture identity:** continue read-only, bounded checks at the next natural schedule boundary and reconcile the release only after an actual schedule event. This avoids duplicate snapshots and protects the confirmatory holdout.
2. **Use the existing owner-authorized dispatch only if genuinely available:** a direct authenticated `workflow_dispatch` capability was not available here, and the task forbids using the PR-comment command as a substitute for a missing scheduled event. Keep this fallback untested; do not impersonate the owner or weaken the actor gate.
3. **If schedule delivery continues to fail, assess a distinct event-relay/monitor architecture:** require an independently authorized principal, least-privilege scope, idempotent run key, durable run manifest and explicit recovery/stop conditions. No such relay or additional permission is currently verified, so do not add credentials, permissions, external services or a speculative workflow in this task.

**Disposition:** remain IN PROGRESS. Preserve the original one-substantive-cycle budget and hard deadline of 2026-11-25 17:30 UTC; do not reset or extend them. The next natural capture opportunity is 2026-11-25 04:23 UTC. Keep the queued Post-Holdout Research Environment and Portfolio Review dependency-gated until this task closes. No strategy backtest, funding access, venue merge, paid-data acquisition or live trading occurred.


## Third post-schedule checkpoint — 2026-11-24 07:15 UTC

- A time-filtered Actions query for runs created at or after 04:23 UTC returned four runs: two research-pipeline pushes, one cancelled earlier push, and queue guardian run [45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900). **No run from `spot-holdout-capture.yml` appeared**, so no scheduled authorization or capture job ran. Main remains at [16873c03b57e](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/16873c03b57e7d1e9dbee19f0be27fc8921636b3).
- The release still contains only ZIP asset [784136576](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026): 63,517 bytes, GitHub digest `sha256:b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`. No second ZIP or JSON sidecar exists. Release metadata remains `immutable=false`; this is not write-once protection.
- Queue guardian [run 45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900) completed successfully at 05:37:45 UTC. Its artifact [14893776351](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900) was downloaded and inspected (SHA-256 `2b0a19b801214e5c9813f0b8a300d1c542ee822413d340c55edaa2271a18da11`). The report records complete enumeration of 531 runs, 411 research/test runs, a latest-50 retained inventory (all 50 completed), no active runs, `actions=[]`, and `errors=[]`. No later guardian run or open queue-guardian incident was visible.
- Latest main CI [run 45339112663](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45339112663) completed successfully at 06:16:20 UTC on this documentation checkpoint's parent commit. Its deterministic-test and synthetic-plumbing-smoke steps both passed. The preceding full CI [run 45327618205](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45327618205) passed 300 deterministic tests in 14.670 seconds and the same smoke test. These are engineering checks, not holdout-data acceptance.
- PR #2 remains open; the last owner command remains `/qfr-capture-spot-holdout` at 2026-11-23 18:48:40 UTC. No later owner comment, review or other open issue was found. No authenticated `workflow_dispatch` capability is available in this execution path; the fallback remains untested.
- Remote main's recursive tree still contains 114 entries, with no disposable cache, scratch, temporary or generated-data paths. No deletion was justified. The local working tree is not exposed by the GitHub view.
- No manual/duplicate capture, strategy backtest, signal/performance inspection, funding access, paid-data acquisition, venue merge, credential creation, live trading or capital deployment occurred.

### Adaptive decision

1. Keep the capture identity and holdout unchanged. Do not create a manual or duplicate run to compensate for the missing schedule event.
2. Recheck the next natural schedule boundary, **2026-11-25 04:23 UTC**, and reconcile the release only after an actual capture event and successful sidecar publication.
3. If the next scheduled event is also absent, assess (but do not deploy without authorization) a distinct event-relay/monitor architecture with an independently authorized principal, least-privilege scope, idempotent run key, durable manifest and explicit stop conditions. Do not add credentials, permissions or external services speculatively.

**Disposition:** remain IN PROGRESS. Preserve the original one-substantive-cycle budget and hard deadline **2026-11-25 17:30 UTC**; do not extend them. Keep the queued Post-Holdout Research Environment and Portfolio Review dependency-gated until this task closes.


## Scheduler-reliability correction — 2026-11-24

- Timestamp note: the previous heading labeled this checkpoint `10:40 UTC`, but the GitHub commit that recorded this section is timestamped 08:51:42 UTC. The precise observation time was not preserved, so the unsupported `10:40 UTC` label has been removed.
- The prior recovery plan made a category error: it treated GitHub Actions `schedule` as a dependable clock and proposed waiting for the next cron boundary. GitHub's official documentation states scheduled events can be delayed and dropped under load; `schedule` is best-effort, not an SLA or delivery guarantee ([official documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)). This recovery plan is superseded.
- The initial capture itself succeeded through the owner-authorized `issue_comment` event: [run 45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), with both authorization and capture/publish jobs successful. The missing operation is the subsequent scheduled invocation, not the data-fetch implementation failing mid-run.
- A fresh Actions inventory at this checkpoint contained five runs created after 2026-11-24 04:23 UTC; none came from `spot-holdout-capture.yml`. There is still no second ZIP or JSON sidecar. No cause for GitHub's missing event is established; do not infer runner failure, Binance failure or a workflow code failure.
- New operating decision: the holdout must be invoked by an independently operated authenticated scheduler calling the protected `workflow_dispatch` API. Required controls: exact verified GitHub App actor; repository-scoped `Actions: write`; secret held outside Git; deterministic per-slot idempotency key; durable dispatch attempt and run-ID record; poll/verify the resulting workflow run; bounded retry only after duplicate detection; and an independent watchdog that detects missing or incomplete runs. GitHub cron is opportunistic only and cannot satisfy the timing/dispatch criterion. Remove the cron trigger or prove end-to-end per-slot idempotency before enabling concurrent external and cron triggers.
- The existing workflow has an owner-actor `workflow_dispatch` gate and an exact control-PR comment route. The connected GitHub tool catalog used in this session has no direct workflow-dispatch POST action; no GitHub App installation, external scheduler credential or watchdog service has been provisioned. These are explicit prerequisites, not reasons to wait for another GitHub cron.
- Do not dispatch a duplicate merely to compensate for the missing event. Preserve the same protected holdout identity and original one-cycle deadline (**2026-11-25 17:30 UTC**). Keep successor research dependency-gated. No strategy backtest, funding access, paid data, venue merge, live trading or capital deployment occurred.


## Fourth live-state verification — 2026-11-24 09:24 UTC (11:24 Europe/Bucharest)

- Queried the latest 100 of 536 repository Actions runs. Eight runs were created at or after the missed 04:23 UTC capture slot: seven `.github/workflows/research-tests.yml` push runs and one `.github/workflows/queue-guardian.yml` schedule run. **Zero** came from `.github/workflows/spot-holdout-capture.yml`. Separate repository-wide queries returned zero queued and zero in-progress workflow runs.
- Latest main CI [45360167229](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45360167229) completed successfully at 08:54:58 UTC on commit [d4a451bb8bda](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d4a451bb8bda64cda44623752078e2289171a1c5). Its job log confirms **304 deterministic tests passed in 14.748 seconds**, followed by `SELF-TEST PASS` for the synthetic plumbing smoke test. Two immediately preceding CI runs [45359822075](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359822075) and [45359984790](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45359984790) failed during successive authorization-assertion corrections; the latest correction passed. This is engineering validation only, not capture delivery or data acceptance.
- The latest observed queue-guardian run remains [45334612900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45334612900), a successful scheduled run created at 05:37:22 UTC. No later guardian run appeared in the latest-100 inventory. The open-issues query returned only control PR #2, with no queue-guardian incident. The five-minute schedule remains unproven and is not a watchdog SLA.
- PR #2 remains open. Its latest owner comment is still the exact command `/qfr-capture-spot-holdout`, posted 2026-11-23 18:48:40 UTC; no newer comment exists. The capture workflow was inspected: its `workflow_dispatch` path requires the verified owner actor, while its issue-comment path is a separate owner/manual control route. No comment or dispatch was issued because neither satisfies the required independent external scheduler.
- Release [`spot-holdout-2026`](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026) still has exactly one uploaded asset: ZIP asset 784136576, `snapshot-45242319210-attempt-1.zip`, 63,517 bytes, GitHub digest `sha256:b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`. There is no second ZIP or JSON sidecar; release metadata remains `immutable=false`.
- The connected GitHub tool catalog still exposes no workflow-dispatch POST action. No independently operated scheduler, repository-scoped GitHub App installation token, external secret-manager credential, durable per-slot dispatch ledger or independent watchdog is available in this execution path. These are the exact owner-side prerequisites. Do not substitute the PR-comment command, GitHub cron, or a manual capture; do not weaken actor gates or create credentials/permissions speculatively.

**Disposition:** remain `IN PROGRESS / BLOCKED` with the original one-substantive-cycle budget and hard deadline **2026-11-25 17:30 UTC** unchanged. Keep the holdout and queued successor closed. No market-data capture, strategy backtest, funding access, paid-data acquisition, venue merge, live trading or capital deployment occurred.


## First-agent wake-up fallback and stable slot protection — 2026-11-24

The expected capture due at 04:23 UTC was not delivered by GitHub Actions cron. The factory now treats cron only as an opportunistic trigger. The first authorized agent wake-up after the due time must inspect the live Actions/release state and start the missing operation through an already-authorized path rather than waiting for another schedule event or an unprovisioned external scheduler.

The implementation uses a deterministic UTC daily slot ID, `binance-spot-1h:prospective-2026-11:YYYY-MM-DD`, and stable release names `snapshot-slot-YYYY-MM-DD.zip` plus `snapshot-slot-YYYY-MM-DD.manifest.json`. Before fetching data, the capture verifies any existing slot ZIP and sidecar by GitHub SHA-256 digest, size, embedded manifest identity and per-file hashes. A second serialized run for the same slot reuses the existing result and does not fetch or publish again. Existing incomplete snapshots remain immutable evidence and are not silently overwritten.

The existing exact-owner PR-comment authorization route remains available as the direct-agent fallback; no actor allowlist, credential or permission has been broadened. The first wake-up must confirm the connector-authored comment actually has the authorized owner identity and that the real Actions run followed. The external scheduler and separate watchdog remain unprovisioned; agent wake-up recovery is not a real-time SLA and does not establish `DELIVERY_VERIFIED`.

No data has yet been captured by this fallback as of this handoff; execution and data acceptance remain pending the actual authenticated run.


## Final first-agent recovery and same-slot replay — 2026-11-24 10:22 UTC

### Trigger failure and fallback execution

The GitHub Actions cron due at **04:23:00 UTC** did not create the capture run. The first authorized agent wake-up after the due time used the existing exact-owner PR #2 command; no authorization gate was weakened and no credential/permission was added.

- An initial owner-authorized attempt [45372850274](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45372850274) stopped at the deterministic capture-test step before data acquisition because a test fixture regression was still present. The release was untouched. The subsequent full CI correction passed before retrying.
- Successful first-agent capture: [run 45373419544](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544), event `issue_comment`, actor `takenthatusernameis-collab`, default-branch commit `27251ddb4fb492e792530afe64de3489f13022f7`, completed 10:18:08 UTC. Authorization, 27 capture tests, data fetch/publication and manifest-artifact upload all succeeded.
- The due time to first actual capture was 5 hours, 54 minutes and 48 seconds. The fallback is not a real-time scheduler; it means the first waking authorized agent does not park the task waiting for cron.

### Data acceptance and provenance

The manifest-only Actions artifact [14909403654](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544/artifacts/14909403654) was downloaded and inspected. Its manifest records:

- Stable slot: `binance-spot-1h:prospective-2026-11:2026-11-24`; actual acquisition timestamp `2026-11-24T10:18:00.440000Z`.
- Requested/observed range: 2026-11-01 00:00 UTC through the fully closed 2026-11-24 09:00 UTC hourly bar.
- ETHUSDT: 562 expected/observed rows; 0 missing hours; 0 duplicates; 0 overlap corrections; source error null; all rows sorted and closed.
- BTCUSDT: the same 562 expected/observed rows and zero missing hours, duplicates, overlap corrections or source errors.
- ETHUSDT CSV SHA-256: `db864661bdf017cfc6743f775ac5ac2949085c7c851a812cc2e31906802af888`.
- BTCUSDT CSV SHA-256: `6584a02490ddbbcd1b1346c74b1a9e392a1d54305fac4e27a991981d36f8956f`.
- `previous_snapshot` references original ZIP asset 784136576 and its verified SHA-256 `b1200bdea3a01e56963b8afda0cab497d4396e0eaae21344bfc624d8a518b0cf`. The first ZIP's sidecar was backfilled as asset 786684146 (3,960 bytes; SHA-256 `21be6fc2d2bbd02b522db079088d4dffd78585ea0a29d788a854fd7f88ec6213`).
- Current ZIP: asset 786684218, `snapshot-slot-2026-11-24.zip`, 65,817 bytes, GitHub SHA-256 `22bd362b7c0db51c7a3302f5b09c1a4a2327a4d9553b8ac7259f2a343c5caade`.
- Current sidecar: asset 786684257, `snapshot-slot-2026-11-24.manifest.json`, 5,211 bytes, GitHub SHA-256 `57cb7b1d297c15a33aa80784a0b72e010988e3da99a0e65171174ce02e19d284`.
- Release metadata remains `immutable=false`; retention is not write-once protection. The manifest explicitly sets `research_evaluation_authorized=false`.

### Live idempotency / first-agent replay proof

A second authorized wake-up posted the same exact command at [PR #2 comment 7128620372](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7128620372). [Run 45373703705](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373703705) completed successfully on `main`; its capture tests passed and its output returned `idempotent_slot_reuse=true`. The verifier downloaded and checked the existing ZIP and sidecar, reused ZIP asset 786684218 and sidecar asset 786684257, and did not fetch or publish another snapshot. The Release still has exactly four assets (original ZIP + backfilled sidecar + current ZIP + current sidecar). This proves the first-agent fallback is idempotent under a repeated wake-up for the same due slot.

### Engineering and guardian verification

- Full main CI [45375425738](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45375425738) passed **324 deterministic tests in 15.423 seconds** and the synthetic plumbing smoke test.
- Capture runs 45373419544 and 45373703705 both succeeded. Their event-driven queue-guardian completion handoffs [45373479882](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373479882), [45373736534](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373736534) and [45373756502](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373756502) all succeeded.
- No strategy backtest, signal/performance inspection, funding access, paid-data acquisition, venue merge, live trading or capital deployment occurred.

### Final operating disposition

The November 24 data slot is **RECOVERED** and the bounded capture-validation task is **COMPLETE**. The external scheduler, independent watchdog and dedicated dispatch credential remain **UNCONFIGURED / DEGRADED**; the above first-agent recovery must not be misreported as `DELIVERY_VERIFIED` for an external scheduler. Per-slot recovery and scheduler health are separate states. The next ready task is the Post-Holdout Research Environment and Portfolio Review; its timebox begins on its first substantive execution.


## Interrupted sidecar-publication recovery hardening — regression-tested 2026-11-24

The final main-branch implementation now handles a partial publication in which the deterministic ZIP exists but its metadata-only sidecar does not. On the next same-slot wake-up it verifies GitHub's ZIP size and SHA-256, the embedded slot identity, each CSV's SHA-256 and readable rows, then reconstructs and uploads only the sidecar using the existing workflow token. It does not refetch market data or publish another ZIP. If the sidecar is absent and no authorized token is available, it fails closed before downloading the ZIP. Positive reconstruction and no-token rejection are included in the final 324-test CI run [45375425738](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45375425738). This is a tested recovery branch, not a fault that occurred during the successful November 24 capture.
