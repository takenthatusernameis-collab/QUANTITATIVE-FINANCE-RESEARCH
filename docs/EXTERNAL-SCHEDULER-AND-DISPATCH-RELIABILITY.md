# External Scheduler and Dispatch Reliability

**Status:** Mandatory repository-wide operating policy for time-sensitive, deadline-bound and freshness-sensitive automation.

## 1. Non-negotiable rule

**GitHub Actions `schedule` is best-effort only. It must never be the primary clock, sole trigger, deadline guarantee, recovery plan or evidence of successful delivery.**

GitHub's official documentation explicitly warns that scheduled events may be delayed during high-load periods and that some queued jobs may be dropped. A workflow file being present on `main`, a valid cron expression, a recent push or a successful manual run does not establish that a future schedule event will be delivered.

Treat GitHub cron as an opportunistic canary at most. Never tell a user to wait for the next GitHub cron tick as the recovery plan for a missed time-sensitive operation.

## 2. Required architecture

For every time-sensitive research capture, market-data refresh, reconciliation, watchdog or deadline-bound operation:

1. **Independent scheduler:** use a scheduler outside GitHub Actions, operated in a separate scheduling/control domain. Suitable provider classes include managed cloud schedulers or independently operated worker/cron services. Select a concrete provider only after its access, reliability, security and cost are verified.
2. **Authenticated dispatch:** have the scheduler actively call the protected GitHub `workflow_dispatch` API. Prefer a dedicated GitHub App installation token restricted to this repository and `Actions: write`. A narrowly scoped fine-grained token is a fallback only when explicitly authorized. Never embed a long-lived credential in code, workflow inputs, issue comments or logs.
3. **Exact identity gate:** verify the real `github.actor` produced by the chosen credential before changing the workflow allowlist. Do not accept arbitrary actors, assume an App's bot name, or weaken existing owner/control-PR authorization.
4. **Deterministic slot identity:** every expected operation must carry a stable slot identity and idempotency key (for example, workstream + UTC capture date + interval). Retries of the same slot must reconcile to one logical operation, not append duplicate snapshots.
5. **Durable dispatch ledger:** record expected slot, scheduled target, dispatch attempts, API responses, workflow run ID, actor, ref/SHA, start/completion timestamps and final disposition outside the ephemeral scheduler invocation.
6. **Run observation:** an HTTP acceptance response alone is not completion. Query GitHub Actions until the exact run is observed; verify workflow ID/path, event, actor, default-branch ref, slot key, start time, jobs, outcome and artifacts.
7. **Bounded recovery:** retry transient dispatch failures with bounded backoff. Before every retry, search for an already-created run using the slot key and time window. Never launch another capture merely because the first response was ambiguous.
8. **Independent watchdog:** a second monitor, not driven by the same GitHub cron or scheduler instance, must detect missing, queued-too-long, failed or incomplete runs and raise a durable incident/alert. The watchdog must not silently fabricate data or weaken acceptance gates.

## 3. GitHub cron coexistence

- A GitHub `schedule` trigger may be retained only as a non-authoritative canary/opportunistic fallback.
- Before enabling both external dispatch and cron for a side-effecting capture, either remove/disable the cron trigger or prove deterministic per-slot idempotency across both event sources.
- Never count a `schedule` event as the only proof that the independent scheduler is installed or healthy.
- `workflow_run` events are useful event-driven handoffs after an actual workflow completes, but are not a substitute for the independent clock/watchdog.

## 4. First-agent wake-up fallback — mandatory when automation is absent or late

An independent scheduler is the preferred timing mechanism, but its absence must not turn a research task into an indefinite wait. **The first authorized agent that wakes after a task's explicit due time is the last line of defense and must directly resume the due operation when its expected output/run is missing.**

For every time-gated task, record in the task file: `not_before_utc` or `due_at_utc`, a stable slot/task idempotency key, expected output, acceptance criteria, authorized execution route, lease/serialization mechanism, bounded retry rule, task expiry and the direct-agent fallback.

At each agent wake:

1. Compare current UTC time with the task's due time. Never execute a time-dependent capture early; continue independent safe work while it is not due.
2. After the due time, inspect the durable ledger, Actions/API state, artifacts and target storage. If the expected output is already complete and verified, reuse it and do not repeat the side effect. If a valid run is active, observe it rather than launching another.
3. If the operation is missing, failed or materially incomplete, the first authorized agent takes ownership using the stable task/slot key and the strongest available durable serialization (workflow concurrency, lease or atomic claim), then performs the same bounded task directly through an already-authorized workflow, runner or API route. Apply the exact same code, acceptance criteria, provenance and safety gates.
4. If an automation process failed, do not wait for another attempt of that same unreliable trigger. Preserve its failure evidence, use direct agent execution or a materially different authorized route, and add regression coverage for the cause.
5. If no available tool/permission can execute the operation, do not impersonate an owner, invent credentials, weaken allowlists or mark the task complete. Record the exact owner-only prerequisite, continue independent safe work and surface the blocker.
6. Before every retry, recheck the slot key and durable state. Agent wake-ups, multiple agents and automation events can race; the side effect must be effectively-once. If no atomic claim/serialization is available, do not launch competing side effects.

This fallback is not a real-time scheduling SLA: a late wake means a late execution and must be reported as such. For cumulative snapshots, one verified catch-up snapshot at the actual execution time may supersede missed intermediate slots only when the full history and provenance contract proves no observations were lost. Never backdate acquisition timestamps or fabricate historical execution.

**General repository rule:** deterministic automation is the first choice for repeatable work, but never the only path to progress. If CI, dispatch, a runner, a bot or another deterministic process is absent or demonstrably unreliable, the first agent that resumes the task should directly perform the smallest safe, independently verifiable unit of the work, using the same requirements and tests. Keep direct execution as a permanent last line of defense for research implementation, data audits, validation, reporting, repository maintenance and recovery. This is not a bypass of authorization or scientific gates.

## 5. Acceptance and incident semantics

The scheduler is **not operational** until an end-to-end test proves: dispatch request → authenticated workflow run → correct run identity/slot → capture/reconciliation → durable artifact publication → independent watchdog observation.

Use explicit statuses:

- `UNCONFIGURED`: no independently operated scheduler/credential.
- `DISPATCH_READY`: credentials, exact actor gate and slot contract configured, but delivery not yet proven.
- `DELIVERY_VERIFIED`: end-to-end dispatch and watchdog test passed.
- `DEGRADED`: missed deadline, missing run, ambiguous dispatch or failed monitor; keep data/strategy gates closed.
- `RECOVERED`: same slot reconciled exactly once and all durable evidence independently verified.

No software unit test, synthetic smoke test, successful manual run, valid cron syntax or repository activity may be promoted to `DELIVERY_VERIFIED`.

## 6. Current Spot holdout application

The first owner-authorized capture (run [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210)) succeeded. The expected GitHub cron event on 2026-11-24 04:23 UTC did not create a capture run. The external scheduler, GitHub App identity/credential and independent watchdog remain unprovisioned or unverified. The workflow's existing exact-actor gate must remain intact until any new external identity is actually observed and reviewed. The capture now uses a stable UTC daily slot identity and deterministic release-asset names; a serialized second wake-up for the same slot verifies and reuses the existing ZIP/sidecar instead of creating another capture.

The state is **UNCONFIGURED / DEGRADED** for external scheduling, not "waiting for the next cron." The holdout remains closed until a snapshot is captured/reconciled and its data acceptance criteria pass. If no external scheduler is available, the first authorized agent wake-up after 04:23 UTC is the required backup executor through the existing owner-exact PR command; the agent must inspect the release and active runs first and must not duplicate a successful or active slot.

## References

- [GitHub Actions schedule event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub REST API: create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
