# Bounded Model Implementation and Research Timebox

**Policy status: DORMANT — activation is deferred until the current ETH/BTC strategy reaches a documented terminal conclusion.**

**Scope after activation:** every new quantitative model or strategy candidate entering implementation in this repository. This policy is prospective; it does not retroactively timebox the current ETH/BTC study or implementation work already underway when activation occurs.

## 1. Purpose

Prevent open-ended model exploration, repeated implementation churn and premature empirical testing. A candidate receives a difficulty-adjusted, predetermined implementation budget. Its specification and implementation must pass objective technical acceptance criteria before empirical strategy research begins.

The objective is not to force a model to pass, produce a profitable result or relax scientific standards. A model that cannot be implemented within its allotted budget must be recorded as incomplete, simplified or abandoned—not sent into research merely to generate a result.

This timebox governs **model implementation only**. It does not impose an arbitrary deadline on scientifically justified empirical research, and it does not weaken the repository's data-quality, provenance, preregistration, statistical or financial-safety requirements.

## 2. Activation gate — ETH/BTC conclusion first

This policy remains dormant until **both** conditions below are satisfied:

1. The current ETH/BTC strategy has a durable final report stating a terminal disposition: **GO, NO-GO, INCONCLUSIVE or INFEASIBLE**, with the evidence, limitations, unresolved uncertainties and rationale recorded.
2. The canonical [Active Task Queue](../tasks/ACTIVE-QUEUE.md) explicitly marks that original ETH/BTC experiment as concluded/closed, and no active task remains to continue empirical work on that same experiment. Any remaining avenue must either be completed, explicitly rejected as infeasible, or clearly separated as a new experiment.

A partial result does not activate the policy. In particular, a Spot-only NO-GO does not conclude a combined or perpetual study while its own research gates remain unresolved. A temporary access or data blocker is not automatically a terminal conclusion; an INCONCLUSIVE/INFEASIBLE disposition must explain why remaining feasible routes have been exhausted, rejected or formally taken out of scope.

Once the gate is met, the next agent must change this document's status to **ACTIVE**, record the activation date and link the final ETH/BTC report and queue entry, and apply the policy to all model implementations started after that point. Do not activate it early or apply it retroactively.

## 3. Pre-implementation commitment

Before implementation begins, create or update one durable model brief/preregistration containing:

- a unique experiment/model ID and concise research objective;
- the model's frozen intended behavior, inputs, outputs, trading/portfolio semantics and material assumptions;
- the expected implementation difficulty tier and a short evidence-based rationale;
- the implementation start timestamp and fixed deadline in UTC;
- the mandatory technical acceptance checklist and named validation commands;
- explicit scope boundaries, dependencies, risks and the fallback decision if the deadline is missed.

The difficulty tier and deadline must be selected **before substantive model implementation**. Classify by the hardest material feature in scope, not by the easiest component. Do not increase the tier simply because implementation is going poorly, and do not lower it to obtain a more generous or convenient classification.

The clock starts when the committed model brief authorizes implementation. It is continuous elapsed calendar time, not accumulated agent runtime. Idle periods, agent handoffs, ordinary CI/runner failures, retries, refactoring, library exploration and provider/endpoint changes do not reset or pause it. Continue safe independent work while any single dependency is blocked.

## 4. Difficulty tiers and fixed implementation budgets

| Tier | Expected implementation difficulty | Initial implementation budget |
|---|---|---:|
| **1 — Simple** | One clearly specified signal/model; one market or instrument; established data schema and backtest harness; standard features and no material custom infrastructure. | **2 calendar days** |
| **2 — Moderate** | Several combined signals/features, modest feature engineering, ordinary risk/position-sizing or exit logic, or a small number of instruments using existing data and execution interfaces. | **4 calendar days** |
| **3 — Complex** | Multi-asset or multi-market logic, multiple timeframes, regime/state-dependent behavior, event-time or asynchronous inputs, custom portfolio construction, or material simulator/execution integration. | **7 calendar days** |
| **4 — Exceptional** | A genuinely novel statistical/ML architecture, multiple interacting model stages, a bespoke data representation or simulation engine, or several substantial integrations with distinct market semantics. | **10 calendar days** |

Use the lowest tier whose definition fully covers the candidate; where a material feature crosses tiers, use the higher tier and explain why. Tier 4 is exceptional, not a default label for any unfamiliar or difficult task. If scope is too broad to estimate, split it into independently specified deliverables before starting the clock rather than granting an unlimited exploratory phase.

### One limited extension

At most **one** extension may be granted, for no more than **25% of the original budget rounded up to the next whole calendar day**. It must be recorded before the original deadline and is allowed only when:

- the core model specification and architecture are implemented;
- all critical causality, leakage, correctness and synthetic-smoke checks pass;
- at least 80% of the remaining non-critical acceptance checklist is complete; and
- the outstanding work is a short, named, testable punch list—not a request for more open-ended exploration.

The extension and its revised UTC deadline must be written into the same model brief with the evidence supporting it. No second extension, rolling extension or deadline reset is allowed.

## 5. What counts as successful implementation

Implementation is complete only when **every mandatory acceptance criterion** below passes. A percentage-complete estimate, plausible chart, successful import or code that merely runs is not sufficient.

1. **Frozen specification:** inputs, features, transformations, parameter meanings, signal timing, outputs, position sizing, portfolio/risk constraints, state transitions and relevant execution assumptions are documented. Material ambiguity is resolved before empirical evaluation.
2. **Deterministic implementation:** the model is committed, versioned and reproducible from a documented command/configuration. Dependencies and material configuration are pinned or recorded.
3. **Correctness and edge-case tests:** deterministic unit, integration and regression tests cover expected outputs, boundaries, invalid/missing values, timestamp/timezone handling, units, state transitions and relevant failure modes.
4. **Causality and leakage safeguards:** tests demonstrate that features and decisions use only information available at the decision time; no future data, target leakage or train/test contamination is introduced by the implementation.
5. **Economic mechanics:** where applicable, the implementation has explicit, testable interfaces for fees, spread, slippage, funding, borrow, liquidity constraints, leverage and position/risk limits. Unknown cost inputs must fail closed or remain explicit research prerequisites; they must not be silently assumed away.
6. **Synthetic end-to-end validation:** a small deterministic fixture with known expected behavior traverses the model's supported execution path and produces the expected signals/positions/outputs. This validates engineering behavior, not profitability.
7. **Reproducible handoff:** the model brief links the implementation commit, test commands, passing results, known limitations and exact research-entry prerequisites.

No empirical returns, strategy rankings or profitability claims are required or permitted as proof of implementation completion. Synthetic fixtures and engineering tests must not be presented as empirical evidence.

## 6. Research-entry gate

Empirical research may begin only when **both** the model implementation and its research inputs are accepted:

- The model passes every mandatory criterion in Section 5 and is frozen at a specific commit.
- The research preregistration identifies the accepted data sources and coverage, hypothesis, baselines, benchmark, costs, evaluation protocol, validation/OOS boundaries, metrics, statistical methods and research stop conditions.
- Applicable repository data-quality, provenance, market-separation and authorization gates pass. A technically complete model does not make an unaccepted dataset acceptable.

Before this gate passes, agents may implement code, run deterministic unit/integration tests and synthetic fixtures, and perform independent data-source quality work. They must not run strategy backtests, optimize parameters against historical outcomes, calculate or compare empirical performance, inspect OOS results to steer the model, or make economic conclusions for that candidate.

When the gate passes, record **IMPLEMENTATION_READY** with the frozen commit and acceptance evidence, then begin the separately preregistered empirical phase. Research results may be positive, negative, null or inconclusive; the implementation timebox must never bias their interpretation.

## 7. Missed deadline, scope changes and stop decisions

If mandatory acceptance is not achieved by the original deadline or the single approved extension:

- mark the candidate **IMPLEMENTATION_TIMEOUT** or **IMPLEMENTATION_INCOMPLETE**;
- stop unproductive work on that implementation path and do not begin empirical research;
- preserve the code, test evidence, failed approaches, exact blockers, time spent and lessons in the existing canonical handoff;
- choose a clear disposition: simplify the model, replace the implementation approach, defer it for a named external prerequisite, or abandon it;
- keep the original experiment identity and deadline in the audit trail.

A materially different model or hypothesis may be proposed as a **new experiment** with a new brief and its own tier/budget, after the previous candidate is explicitly closed. Cosmetic edits, renaming, changing branches, restarting workflows, switching libraries, repeating the same provider attempt or splitting the same unfinished work across agents do not create a new candidate and cannot reset its clock.

Apply the repository's existing repeated-failure rule: diagnose the first meaningful failure, test materially different alternatives, and stop repeating the same non-transient failed route after two independent occurrences. Do not spend the entire budget on unbounded provider/tool discovery when a simpler model or implementation route can meet the frozen objective.

## 8. Governance and reporting

Every candidate governed by this policy must expose, in its model brief or canonical task handoff:

- experiment/model ID and difficulty tier;
- implementation start, original deadline, and any approved extension;
- acceptance checklist status and links to test evidence;
- current state: **IMPLEMENTING**, **IMPLEMENTATION_READY**, **IMPLEMENTATION_INCOMPLETE** or **IMPLEMENTATION_TIMEOUT**;
- next decision and explicit research-entry status.

The agent must report deadline risk before expiry, not after silently exceeding it. The canonical task queue remains the single source of truth for active work; do not create duplicate progress trackers.

**Hard boundary:** this policy authorizes neither live orders nor capital deployment, strategy promotion, custody changes or automatic trading. Those remain separately controlled and require explicit authorization under the repository's existing safety rules.
