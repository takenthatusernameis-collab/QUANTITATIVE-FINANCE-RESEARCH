# Model Implementation Timebox and Research Conclusion Deadline Policy

**Status: MANDATORY — active from 2026-11-23 for every new quantitative model in this repository.**

This policy prevents technically open-ended model development. Every proposed model receives a precommitted, difficulty-proportionate implementation-and-conclusion budget before substantive implementation or model-result inspection begins. The deadline controls how long the repository spends reaching a trustworthy decision; it never authorizes weaker data, code, statistical, security or financial-safety standards.

## 0. Mandatory project-feasibility precondition

A model timebox may be assigned only after the [Evidence-First Project Lifecycle](RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md) has been completed. Assess actual data/source access, permissions, history, point-in-time population, market semantics, quality, execution economics, compute/runtime, storage/retention, provenance and workflow capabilities before writing the hypothesis. Design the hypothesis to fit VERIFIED evidence; do not reverse this order.

The [Project Retrospective and Admin-Agent Calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md) must also be completed using both predecessor feedback axes. If the predecessor did not measure strategy performance, record that explicitly and use its research/evidence outcome.

Only after both gates pass should the agent rate difficulty and freeze implementation and final-conclusion deadlines. Use `research/project_readiness.py`; missing, unverified or sample-only required data blocks hypothesis implementation.

## 1. Activation trigger and scope

The deferred activation trigger has been met: the previously active Binance Spot ETH/BTC mean-reversion study reached its documented **NO-GO** conclusion on 2026-11-22. The timebox policy therefore applies to the subsequent, separately preregistered **ETH/BTC Spot Relative-Momentum Rotation** and every later distinct quantitative model.

The original Binance USDⓈ-M funding-aware study remains **INCONCLUSIVE** because its funding acceptance gate is unresolved. It is a separate research workstream and does not postpone activation of this policy for Spot or other independently scoped models. Its data restrictions and acceptance criteria remain unchanged.

This policy applies to new quantitative hypotheses, strategies, model replacements and materially changed specifications. Routine maintenance of a frozen, already-concluded experiment does not reopen its research clock. A material change to hypothesis, market construction, venue/provider, timeframe, sample, signal or cost assumptions creates a separately identified experiment and requires its own preregistration and timebox.

## 2. Mandatory preregistration fields

After the environment and predecessor-feedback gates pass, and before substantive model implementation or inspection of empirical model results, the active task or preregistration must record, in UTC:

1. **Model/experiment identity** and frozen research question.
2. **Expected implementation difficulty:** LOW, MEDIUM or HIGH.
3. **Difficulty rationale:** data readiness, model novelty, integration burden, validation/statistical burden and compute/execution needs.
4. **Implementation start timestamp** and the selected budget tier.
5. **Maximum substantive agent cycles** and exact hard implementation deadline.
6. **Exact final research-conclusion deadline**, covering implementation, valid execution, analysis and the decision report.
7. **Milestones, acceptance gates and stop conditions.**
8. **Deadline outcome rule:** GO/NO-GO only when valid empirical evidence exists; otherwise INCONCLUSIVE/INFEASIBLE with the precise unresolved blocker.

A preregistration without these fields is not ready for implementation. Agents must not silently omit the timebox, defer assigning it until after implementation starts, or replace an exact deadline with a status date such as "pending since".

## 3. Default difficulty tiers

Use the smallest tier that realistically covers the work. Score difficulty before examining performance results; do not inflate it to obtain more time.

| Difficulty | Typical characteristics | Maximum substantive agent cycles | Maximum elapsed calendar time |
|---|---|---:|---:|
| LOW | Accepted data and reusable pipeline; simple frozen model; limited integration and validation | 2 | 2 days |
| MEDIUM | Accepted or readily available data; moderate pipeline integration, execution accounting, benchmarks or statistical validation | 4 | 5 days |
| HIGH | Material new data construction, complex model implementation, substantial independent validation or demanding compute | 8 | 10 days |

The applicable limit is the **earlier** of the cycle cap or calendar deadline. A substantive agent cycle is a distinct work segment that produces a durable implementation, test, data-quality finding, empirical run or decision artifact. Individual tool calls, cosmetic edits and identical retries are not separate cycles.

The clock starts at the recorded implementation start timestamp. It includes ordinary CI/runner queues, debugging, data acquisition, analysis and reporting; routine execution friction is not a reason to reset it. Agents must use the repository's recovery and alternative-route procedures within the same budget.

## 4. Required execution and deadline behavior

- Freeze the hypothesis, model specification, baselines, costs, statistical method, acceptance criteria and timebox before implementation.
- Deliver a minimally complete, reproducible implementation with deterministic tests and provenance; then run the valid historical experiment as soon as all pre-registered gates pass.
- Keep implementation progress and empirical validity distinct. Passing tests or a synthetic smoke test is not a market-data or strategy result.
- Preserve every hard scientific and security gate. Never forward-fill, fabricate observations, weaken a gate, contaminate a holdout, change frozen criteria after seeing results or run with unauthorized data/credentials.
- Diagnose a material failure and try a materially different route within the existing budget. Do not spend cycles repeating an unchanged failed endpoint, parser, download or workflow.
- Do not automatically extend, reset or roll over a deadline because implementation is difficult, a run is queued, or an agent handoff occurs. If a material scope change is necessary, close the current experiment with its evidence and preregister a distinct experiment with a fresh identity and budget before proceeding.
- At the deadline, publish the strongest defensible conclusion and a concise report. If valid empirical evidence exists, apply the frozen criteria and report **GO** or **NO-GO**. If implementation, data acceptance or execution is still unresolved, report **INCONCLUSIVE** or **INFEASIBLE** and identify the exact blocker. A timebox expiration is **not** evidence of poor strategy performance and must never be mislabeled NO-GO.
- Stop work on the expired experiment after the final handoff. Any further research must be a separately justified experiment, not an unbounded continuation under the old task.

The purpose is not to force a positive result or rush unsafe work. It is to guarantee that each model gets a proportionate, finite opportunity to produce a valid conclusion—and that an unresolved model does not consume unlimited research cycles.

## 5. First assignment — ETH/BTC Spot Relative-Momentum Rotation (CONCLUDED)

This is the first model governed by the activated policy.

- **Experiment:** `ETH-BTC-SPOT-MOMENTUM`
- **Difficulty:** MEDIUM.
- **Rationale:** The hypothesis and signal are simple and frozen (daily ETH/BTC ratio versus a 200-day SMA); accepted Binance Spot observations and an event-time research path already exist. Moderate work remains to integrate the model into the repository, verify causal next-hour execution and elapsed-time accounting, reproduce benchmarks/costs/bootstrap inference, and complete tests/reporting. No new venue or funding source is authorized or required.
- **Start:** 2026-11-23T13:14:44Z, the commit timestamp at which the model-specific timebox was frozen in the preregistration.
- **Maximum budget:** 4 substantive agent cycles total.
- **Implementation deadline:** 2026-11-26 18:00 UTC.
- **Final empirical conclusion deadline:** 2026-11-28 18:00 UTC.
- **Required final deliverable:** committed reproducible implementation, deterministic tests, accepted input/provenance checks, empirical result report with all frozen metrics and benchmarks, and GO/NO-GO/INCONCLUSIVE conclusion.
- **Outcome:** completed on 2026-11-23 after substantive cycle 1 of 4; **NO-GO** under all six preregistered criteria. Report: [ETH-BTC Spot Momentum empirical conclusion](../reports/ETH-BTC-SPOT-MOMENTUM-EMPIRICAL-RESULT-2026-11-23.md). No unused cycles or deadline extension were applied; the model is closed and must not be tuned on the OOS sample.
- **Expired-budget handling:** if the acceptance gates or empirical result are not complete by the final deadline, close this attempt as INCONCLUSIVE/IMPLEMENTATION-INFEASIBLE with the exact blocker. Do not call it NO-GO, weaken the gates or silently extend the deadline.

These dates and limits are frozen for this experiment. The canonical task-level copy is in [the Spot Momentum preregistration](../tasks/ETH-BTC-SPOT-MOMENTUM-PREREGISTRATION.md); the active queue and README must keep pointing agents to this policy and assignment.
