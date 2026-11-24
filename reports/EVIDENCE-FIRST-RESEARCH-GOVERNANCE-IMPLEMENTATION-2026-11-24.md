# Evidence-First Research Governance Upgrade — 2026-11-24

**Project ID:** QFR-GOV-2026-11-24-EVIDENCE-FIRST  
**Project kind:** meta-process and research-factory improvement  
**Final main commit:** [9780ad6](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9780ad676bee13503519a2cc1cfcbd45b9995740)  
**Validation:** [CI run 45306713796](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45306713796) — **280 deterministic tests passed; synthetic plumbing smoke test passed**.

## 1. Scope and conclusion

The task implemented the repository's mandatory evidence-first project-selection standard, two-axis retrospective, deterministic project-intake gates, documentation navigation and a queued post-holdout research-portfolio review.

No strategy was selected, no market data was retrieved, no backtest was run, no holdout was inspected for signals or performance, no paid data/credentials were acquired, and no live trading/deployment was performed.

**Research-performance result for this governance project: NOT MEASURED.** This was a meta-process improvement, not an empirical strategy evaluation. Existing research conclusions remain unchanged:
- Binance Spot ETH/BTC mean-reversion: **NO-GO**, 2026-11-22.
- ETH/BTC Spot relative-momentum rotation: **NO-GO**, 2026-11-23; frozen and closed.
- USD-M funding-aware research: **INCONCLUSIVE**; funding data remain unaccepted.

Relevant reports: [Spot mean-reversion result](ETH-BTC-SPOT-EMPIRICAL-RESULT-2026-11-22.md), [Spot momentum result](ETH-BTC-SPOT-MOMENTUM-EMPIRICAL-RESULT-2026-11-23.md), and [funding architecture decision](ETH-BTC-FUNDING-DATA-ARCHITECTURE-PIVOT-2026-11-23.md).

## 2. Predecessor research/evidence feedback

The immediately preceding repository assignment remains the first scheduled Binance Spot holdout-capture validation. Its initial owner-triggered capture succeeded, collecting **546 closed hourly observations per symbol** for ETHUSDT and BTCUSDT with no reported missing hours, duplicates, corrections or source errors. This infrastructure result did not measure investment performance.

Evidence: [initial capture run 45242319210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45242319210), [durable release snapshot](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/releases/tag/spot-holdout-2026), and [first scheduled-run validation task](../tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md).

The capture's scientific value is prospective data preservation for a later independent experiment. Until the first scheduled event, second snapshot, previous-snapshot reconciliation and sidecar backfill are independently verified, this dataset is not promoted as a completed validated holdout.

## 3. Predecessor technical-delivery feedback

Observed technical facts used in this upgrade:

| Area | Evidence | Admin-agent implication |
|---|---|---|
| Capture workflow | Issue-comment-triggered run passed; scheduled and manual-dispatch events were still unobserved at handoff | Distinguish configuration and smoke tests from proven event delivery |
| Data provenance | Release asset exists with SHA-256; release metadata reported `immutable=false` | Describe retention accurately; do not claim write-once durability |
| Queue guardian | Five-minute schedule was configured, but recent schedule heartbeats were sparse; workflow-completion handoffs were observed | Measure actual heartbeat reliability, not just cron configuration |
| Test/CI quality | Static workflow tests encoded old action-tag references and failed after actions were pinned to full SHAs | Keep tests aligned with security controls and test exact behavior, not obsolete syntax |
| Documentation | README had 337 lines and active queue was 70,736 bytes; status, reusable policy and historical transcript were mixed | Separate navigation, governing policy, active task and historical evidence |
| Automation maintenance | Adding ungrouped Dependabot updates opened five simultaneous Python dependency PRs | Group version updates, cap concurrency and delay risky releases |

The first governance CI attempts exposed three stale action-tag assertions; after updating them to assert the reviewed commit SHAs, a multiline-regex omission caused one more failure. Both defects were corrected. The final run passed **280 tests in 14.956 seconds** and the synthetic plumbing smoke test. These are software/engineering results, not market-data or strategy evidence.

## 4. Technical changes delivered

1. Added [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md), requiring environment/data/permission/compute/storage assessment before hypothesis design.
2. Added [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md), mandating research/performance and technical feedback, plus an evidence-backed calibration decision and validation metric before each successor.
3. Added [research/project_readiness.py](../research/project_readiness.py) and deterministic tests to require complete environment classifications, verified evidence for every required hypothesis dimension, prior-task feedback and justified difficulty ratings.
4. Added a project-intake template and a documentation authority/navigation index.
5. Shortened the README to a start-here hub and the active queue to a compact current-state pointer; preserved the superseded README and queue verbatim in `archive/`.
6. Pinned external GitHub Actions to full commit SHAs, retaining readable version comments and exact-SHA regression tests.
7. Grouped Dependabot version proposals by ecosystem, limited each ecosystem to one open update PR and added cooldowns. The five initial ungrouped Python update PRs (#6–#10) were closed; no dependency upgrades were merged.
8. Changed research-test concurrency to isolate each PR/ref and cancel superseded checks rather than globally serializing unrelated main and PR test runs.

The documentation approach follows useful reproducibility and supply-chain patterns from [The Turing Way](https://book.the-turing-way.org/), [FAIR software](https://fair-software.eu/), [MLflow dataset/experiment tracking](https://mlflow.org/docs/latest/ml/dataset/), [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions), and [OpenSSF Scorecard](https://scorecard.dev/). No new paid service or runtime dependency was introduced for the readiness policy.

## 5. Repository-admin agent calibration

**Decision: CHANGE the default project-selection sequence from model-first to evidence-first.**

- Previous failure pattern: a compelling model or data source could become the implicit objective, after which agents spent cycles trying to repair access, completeness, semantics, retention or infrastructure around it.
- Evidence: Spot model NO-GOs, funding-source infeasibility/incompleteness, unobserved scheduled capture behavior, non-immutable release storage and queue/CI maintenance friction.
- New rule: review predecessor feedback; inventory the actual authorized environment; classify each dimension; design hypotheses only against verified required inputs; rank feasible candidates; then assess difficulty and freeze expiry before implementation.
- Additional calibration: every successor must record one explicit admin-agent decision to change, retain or retire, with expected effect and a measurable validation signal. This changes the repository's decision policy/templates/tests; it does not change the underlying AI model weights.

## 6. Difficulty and timebox calibration

**Bootstrap exception:** this governance project created the mandatory timebox standard while the project was already under way. Its scope is retrospectively characterized as HIGH because it changed multiple governing documents, machine-checkable policy, tests, workflows and handoff structure; however, it did **not** have a prospectively frozen difficulty score and deadline. Do not treat this project as evidence of successful prospective timebox calibration. This gap is explicitly carried forward as a lesson: every successor must score difficulty and freeze expiry before implementation.

The standard now scores five dimensions (data novelty, methodology, integration, statistical validation, compute/operations), each 1–3:
- LOW: 5–7 total; at most 2 substantive cycles / 2 elapsed days.
- MEDIUM: 8–11; at most 4 cycles / 5 days.
- HIGH: 12–15; at most 8 cycles / 10 days.

The earlier of cycle cap or elapsed deadline controls; a timebox cannot weaken evidence gates.

## 7. Successor and validation metric

The current active assignment remains [First Scheduled Holdout Run Validation](../tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md). Only after it closes should the queued [Post-Holdout Research Environment and Portfolio Review](../tasks/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md) activate. No next strategy is preselected.

Primary calibration measures:
- percentage of required hypothesis inputs marked VERIFIED with evidence before model implementation;
- forecast-versus-observed feasibility and timebox error by tier;
- decision-relevant evidence yield per substantive cycle;
- CI/queue/dispatch reliability and stale-run rate;
- number of routine manual interventions; and
- whether each task handoff contains both feedback axes and an admin-calibration decision.

The queued successor must report these where measurable, must not invent metrics where not measured, and must preserve the current no-backtest/no-paid-data/no-live-trading boundaries.
