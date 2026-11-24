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

## 4. Acceptance and incident semantics

The scheduler is **not operational** until an end-to-end test proves: dispatch request → authenticated workflow run → correct run identity/slot → capture/reconciliation → durable artifact publication → independent watchdog observation.

Use explicit statuses:

- `UNCONFIGURED`: no independently operated scheduler/credential.
- `DISPATCH_READY`: credentials, exact actor gate and slot contract configured, but delivery not yet proven.
- `DELIVERY_VERIFIED`: end-to-end dispatch and watchdog test passed.
- `DEGRADED`: missed deadline, missing run, ambiguous dispatch or failed monitor; keep data/strategy gates closed.
- `RECOVERED`: same slot reconciled exactly once and all durable evidence independently verified.

No software unit test, synthetic smoke test, successful manual run, valid cron syntax or repository activity may be promoted to `DELIVERY_VERIFIED`.

## 5. Current Spot holdout application

The first owner-authorized capture (run [45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210)) succeeded. The expected GitHub cron event on 2026-11-24 04:23 UTC did not create a capture run. The external scheduler, GitHub App identity/credential, per-slot idempotency and independent watchdog remain unprovisioned or unverified. The workflow's existing exact-actor gate must remain intact until the external identity is actually observed and reviewed.

Therefore the current state is **UNCONFIGURED / DEGRADED**, not "waiting for the next cron." The holdout remains closed until an authenticated external dispatch is observed and all snapshot/sidecar reconciliation criteria pass.

## References

- [GitHub Actions schedule event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub REST API: create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
