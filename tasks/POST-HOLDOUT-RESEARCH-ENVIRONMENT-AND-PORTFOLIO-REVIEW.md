# Post-Holdout Research Environment and Portfolio Review

**Status:** READY — prerequisite [First Scheduled Holdout Run Validation](PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md) closed on 2026-11-24. Record the actual start time and two-day expiry when substantive review begins; the timebox does not run while READY.  
**Priority:** P2 — research portfolio selection and admin-agent calibration.  
**Project kind:** environment assessment / research-factory improvement; not a strategy backtest.  
**Budget:** LOW difficulty, maximum 2 substantive cycles and 2 elapsed calendar days from activation; absolute completion deadline **2026-11-27 17:30 UTC**. The earlier limit controls.

## Activation and predecessor handoff

The predecessor is RECOVERED: the first-agent fallback captured and validated the 2026-11-24 Binance Spot slot, the same-slot replay proved idempotent ZIP/sidecar reuse, and the queue-guardian handoffs succeeded. The predecessor's research/evidence yield was infrastructure-only; no strategy returns were measured and no strategy is promoted. Its technical-delivery lesson is that GitHub cron failed, while direct first-agent wake-up recovery succeeded. The external scheduler/watchdog remain UNCONFIGURED and must not be conflated with per-slot recovery.

The difficulty assessment remains LOW. On activation, freeze `started_at_utc`, `expires_at_utc` (no later than two calendar days after start and no later than the existing absolute deadline), `max_cycles=2`, `cycles_used=0`, dependencies, write scope and resource reservations in the canonical queue before generating candidate hypotheses.

## Objective

Use the completed holdout-validation task's research/evidence outcome and technical-delivery outcome, together with the recent empirical NO-GO and funding-INCONCLUSIVE findings, to establish the actual evidence and operating environment. Only after that inventory may the agent generate and rank candidate research hypotheses. Do not preselect a model in this task. The research opportunity and asset universe are not restricted to ETHUSDT/BTCUSDT or to the assets currently cached in this repository.

## Required sequence

1. Read the evidence-first lifecycle and project-retrospective/admin-calibration standards.
2. Complete both feedback axes for the preceding holdout-validation task:
   - Research/evidence outcome: capture completeness, integrity, reconciliation, independent-data value and unresolved scientific limitations. State explicitly that this infrastructure task did not measure strategy returns.
   - Technical delivery: scheduled-event reliability, queue-guardian heartbeat, test/CI outcomes, dispatch, runtime, artifact/sidecar hashes, recovery, retention, manual interventions and workflow fragility.
3. Carry forward the Spot mean-reversion and Spot momentum NO-GO evidence and the separate funding-aware INCONCLUSIVE result. Do not tune the closed Spot experiments or present funding evidence as accepted.
4. Inventory actual environment across authorized sources, data access, historical coverage, point-in-time universes, product semantics, costs, API limits, compute, workflow permissions, storage and reproducibility.
5. Classify each source/dimension as VERIFIED, SAMPLE_ONLY, CLAIMED_UNVERIFIED, UNAVAILABLE/RESTRICTED, UNKNOWN or NOT_APPLICABLE with evidence and rationales.
6. Identify research questions the verified information can answer. Generate candidates only after the inventory is complete.
7. Reject candidates depending on unavailable or unverified inputs. Rank only feasible candidates by information gain, decision value, economic rationale, validation feasibility, cost and time.
9. If no model is ready, select a bounded environment-enabling project or report that no new model is currently justified.
10. For any selected hypothesis, create a distinct preregistration, experiment identity, independent holdout, asset-universe policy, difficulty assessment and hard expiration. Do not begin implementation under this portfolio-review task.
11. Commit the retrospective, environment matrix, admin-agent calibration decision and one evidence-backed successor handoff to `main`.

## Admin-agent calibration

Identify at least one evidence-backed decision to change, retain or retire in the repository-admin rubric. State the prior assumption, actual evidence, revised decision, expected effect and validation metric. Examples: feasibility forecasts, data-source priors, task difficulty estimates, queue/dispatch reliability or documentation/handoff quality.

## Acceptance criteria

- [ ] Research/evidence and technical-delivery feedback are recorded with links to runs, commits and artifacts.
- [ ] No trading-performance metrics are invented for the infrastructure task.
- [ ] Environment inventory covers all required dimensions and separates verified evidence from claims/unknowns.
- [ ] Candidate hypotheses are generated only after the inventory is complete.
- [ ] No candidate requiring unverified data is selected.
- [ ] Any successor hypothesis has a difficulty/timebox frozen before implementation.
- [ ] One admin-agent calibration decision has an explicit validation metric.
- [ ] One canonical successor task is committed, or the review justifies why no further project should begin.

## Stop conditions

- Do not start before the current holdout-validation task closes.
- Do not purchase Market History or another paid dataset, create credentials or grant permissions without explicit owner authorization.
- Do not bypass access restrictions, combine venues without an accepted methodology, run strategy backtests, tune concluded models or authorize live trading.
- If the environment cannot support a defensible hypothesis, stop at an environment-enabling project or a documented no-project decision.
