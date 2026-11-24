# Project Retrospective and Repository-Admin Agent Calibration

**Status: MANDATORY after every substantive task and before selection of the next project.**

## Purpose

Every completed project must improve both (1) the repository's quantitative-finance research decisions and (2) the technical judgment of repository-admin/orchestration agents that select, prioritize, scope, dispatch and review work.

The next project must explicitly use both kinds of feedback from the previous task. A narrative summary without evidence, a CI report without research learning, or a performance report without engineering review is incomplete.

This calibrates agent instructions, decision rubrics, prioritization rules and automation. It does not claim to fine-tune or change the underlying AI model's weights.

## A. Research and performance feedback

When an empirical model or strategy was evaluated, record the frozen specification and actual evidence: hypothesis/experiment identity; accepted data scope and holdout; primary/secondary metrics versus frozen benchmarks; net returns/CAGR, Sharpe or other risk-adjusted metrics, maximum drawdown, turnover and exposure where relevant; fees, spread, slippage, funding, borrow and liquidity; confidence intervals, bootstrap/inference, sample size and trade concentration; regime/subperiod robustness; sensitivity and alternative explanations; and the GO/NO-GO/INCONCLUSIVE decision with its frozen criteria.

Do not optimize the next model to one prior metric or to a positive result. A NO-GO is useful evidence about the tested hypothesis and scope, not proof that every related idea is invalid. A wide confidence interval is uncertainty, not evidence of equivalence. Timebox expiry or data-access failure is not a performance NO-GO.

When the preceding task did not produce an empirical strategy result (for example, a capture, parser, provider pilot or infrastructure task), state that explicitly. Use its research/evidence-performance feedback instead: accepted versus rejected inputs, coverage gained, uncertainties resolved, controls passed/failed, source feasibility learned and whether the result changed the opportunity set. Never invent trading metrics for an infrastructure task.

## B. Technical-delivery feedback

Always review delivery independently of empirical performance: forecast versus actual difficulty/cycles/time; scope and rework; test/CI failures and flaky tests; provider/API reliability, access restrictions, rate limits, pagination, schema drift and completeness; throughput, cache/storage, runtime, memory, retries and checkpoint recovery; dispatch success, event/actor/ref correctness, queue time, duplicate/orphan runs and guardian behavior; artifact completeness, retention, hashes, provenance and retrieval; manual interventions and owner-only dependencies; dependency/security status, workflow permissions and branch/PR hygiene; documentation discoverability, stale instructions and handoff accuracy; and operating cost/maintenance.

Classify root causes as research design, data/source, implementation, environment/permission, compute, orchestration, storage/provenance, validation or documentation. Do not label a provider denial as a model failure or passing tests as research success.

## Required retrospective record

| Field | Required content |
|---|---|
| Previous task identity | Canonical task path, project/experiment ID and final commit |
| Research/performance feedback | Result, metrics or explicit not-measured reason; evidence refs |
| Technical-delivery feedback | Delivery evidence, metrics and failures; evidence refs |
| Forecast errors | What was misestimated about access, coverage, time, cost, permissions or complexity |
| Root causes | Evidence-backed causal explanation |
| Admin-agent calibration | Decisions to change, retain or retire in selection, sizing, dispatch or review |
| Expected effect | Future failure, wasted cycle or poor decision to reduce |
| Validation | Test, metric or next-cycle observation to verify calibration |
| Carry-forward | Constraints, accepted evidence, rejected routes and unresolved items |

At minimum retain one research/performance entry, one technical-delivery entry and one explicit repository-admin calibration decision. "No change" is acceptable only with evidence and a reason.

## How repository-admin agents must calibrate

After each task, revisit:

1. **Opportunity selection:** Was the project based on verified data and infrastructure before the hypothesis was chosen?
2. **Feasibility forecasting:** Were access, product inception, full-history/point-in-time coverage, compute, storage, permissions and economics estimated accurately?
3. **Priority allocation:** Did the task address the highest-value bottleneck or polish a low-impact subsystem?
4. **Difficulty/timebox:** Did the rating reflect actual novelty, method, integration, validation and compute burden?
5. **Research judgment:** Were negative/null/inconclusive outcomes interpreted correctly and holdouts protected?
6. **Technical judgment:** Were repeated failures stopped, alternatives materially different and recovery paths verified?
7. **Autonomy:** Which manual steps, queue stalls or artifact transfers remained?
8. **Documentation:** Could a new agent locate the governing rule, current task, evidence and stop conditions quickly?

Translate feedback into a small number of testable decisions: revise a provider feasibility prior after a verified coverage failure; adjust task duration after repeated measured overruns; downgrade a workflow reliability estimate after missed/orphaned events; prefer verified point-in-time data over an incomplete cheap source; add a contract test after a parser regression; or simplify a document after stale instructions caused a wrong handoff.

Do not alter weights or priorities merely to explain away one result. Require a causal explanation, supporting evidence and observable validation. Preserve the previous decision and the reason it changed.

## Calibration metrics

| Metric | Meaning |
|---|---|
| Verified-feasibility forecast error | Predicted versus observed access, coverage and quality |
| Timebox calibration | Planned versus actual cycles and elapsed time by tier |
| Evidence yield | Decision-relevant uncertainties resolved per cycle |
| Research conclusion quality | Correct GO/NO-GO/INCONCLUSIVE use and frozen-criteria compliance |
| Provider-route efficiency | Distinct routes tested, repeated failures avoided and accepted inputs |
| CI/recovery reliability | Test success, flaky rate, checkpoint recovery and orphaned runs |
| Autonomous completion rate | Tasks completed without routine human intervention |
| Handoff integrity | Successor task, evidence, commits and prerequisites are discoverable |
| Cost per decision | Runner/API/storage/service cost for a defensible conclusion |

Every KPI needs a definition, denominator, source and interpretation. Never improve a metric by weakening gates, omitting failures or shrinking the denominator.

## Next-project transition gate

- [ ] Research/performance feedback is recorded, including why performance was not measured when applicable.
- [ ] Technical-delivery feedback is recorded with inspectable evidence.
- [ ] At least one admin-agent calibration decision is recorded with expected effect and validation metric.
- [ ] The next project starts with an actual environment inventory.
- [ ] A new hypothesis depends only on verified environment dimensions.
- [ ] Rejected ideas and feasibility blockers are preserved.
- [ ] Difficulty, cycle budget, hard deadline and conclusion rules are frozen before implementation.
- [ ] A unique project identity, acceptance criteria and one canonical queue pointer are committed.

The first task after agent initialization must use a bootstrap retrospective from the latest available reports and CI/workflow evidence. No task may skip either feedback axis because an earlier report used a different template.
