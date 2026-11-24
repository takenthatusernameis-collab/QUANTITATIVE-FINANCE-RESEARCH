# Documentation and Operating-Contract Index

This directory is the navigation layer for the quantitative-finance research factory. Read governing documents in order; use task-specific files for the current experiment and reports/archive snapshots for historical evidence.

## Authority order

1. Hard invariants: explicit authorization, security, legality, privacy, scientific validity, data integrity, provenance, independent holdouts and no-live-trading boundaries.
2. [General Antifragile Autonomous Operating Mindset](GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md): highest-level principles and priority hierarchy.
3. [Evidence-First Project Lifecycle](RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md): mandatory predecessor feedback, environment inventory, hypothesis eligibility, project ranking and timebox assignment.
4. [Asset-Universe Discovery and Scope Policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md): factory-wide open asset discovery and project-specific universe justification.
5. [Project Retrospective and Admin-Agent Calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md): required research/performance and technical-delivery feedback before the next project.
6. [Adaptive Autonomous Research Execution](ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md): operational failover, dispatch, recovery, queue and handoff rules.
7. [Parallel Research Workstreams and Per-Workstream Expiry Policy](PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md): safe concurrency, independent clocks, resource isolation and admission checks.
8. [Model Implementation Timebox Policy](MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md): difficulty-based cycle limits, hard deadlines and terminal outcomes.
9. [Repository Hygiene and Context Compaction](REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md): safe cleanup and evidence preservation.
10. [ChatGPT-to-GitHub Dispatch](CHATGPT-WORKFLOW-DISPATCH.md): exact connected-actor bridge, event validation and autonomous run verification.
11. [External Scheduler and Dispatch Reliability](EXTERNAL-SCHEDULER-AND-DISPATCH-RELIABILITY.md): independent scheduling, authenticated dispatch, idempotency, delivery verification and watchdog requirements.

Lower-level documents may impose stricter controls but may not weaken higher-level rules.

## Start-here paths

| Need | Canonical entry |
|---|---|
| Start an agent cycle | [Repository README](../README.md), then [active queue](../tasks/ACTIVE-QUEUE.md) |
| Choose a new research project | [Evidence-first lifecycle](RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md) |
| Discover eligible assets/instruments | [Asset-universe discovery policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md) |
| Record prior-task learning | [Retrospective and calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md) |
| Create a model timebox | [Timebox policy](MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md) |
| Admit independent parallel work | [Parallel workstream policy](PARALLEL-RESEARCH-WORKSTREAM-AND-EXPIRY-POLICY.md) and [deterministic checks](../research/workstream_policy.py) |
| Inspect the ETH/BTC pipeline | [Research pipeline README](../research/README.md) |
| Validate the current Spot capture | [First scheduled holdout validation](../tasks/PROSPECTIVE-HOLDOUT-FIRST-SCHEDULED-RUN-VALIDATION.md) |
| Plan the next project after capture validation | [Post-holdout environment and portfolio review](../tasks/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW.md) |
| Reuse a project-intake record | [Project intake template](../templates/PROJECT-INTAKE-TEMPLATE.json) |

## Repository architecture

- `research/`: deterministic policy functions, data adapters, model implementations and tests.
- `tasks/`: bounded project specifications and one canonical queue index; the queue may track multiple independent active workstreams, each with its own expiry.
- `reports/`: dated, evidence-backed results, audits, retrospectives and handoffs.
- `templates/`: reusable project and review structures; templates are not evidence.
- `archive/`: snapshots of superseded instructions and original prompts.
- `.github/workflows/`: test, capture, research, cache and queue-guardian automation.

## Documentation quality contract

Every operational document should state purpose, authority/status, intended reader, prerequisites, inputs/evidence, procedure, outputs, acceptance criteria, stop conditions, recovery path and canonical successor. Keep one authoritative location per rule. Current status belongs in the active queue, reusable rules in `docs/`, project requirements in `tasks/`, and historical evidence in `reports/` or `archive/`.

Prefer short navigable entry points and linked runbooks over duplicated policy blocks or append-only transcripts. Make substantive claims traceable to a commit, run, artifact, source or explicit unresolved assumption. Update links/tests when moving documents.

## Software-factory practices

Adopt reproducible research and secure supply-chain practices without unnecessary services: immutable action references, least-privilege workflow permissions, automated dependency-update proposals, deterministic tests, explicit schemas, fail-closed gates, source lineage/content hashes, code/environment metadata, separation of research/engineering/operational outcomes, independent holdouts, bounded resumable work, and evidence-based retrospectives.

References: [Turing Way](https://book.the-turing-way.org/), [FAIR software](https://fair-software.eu/), [MLflow dataset tracking](https://mlflow.org/docs/latest/ml/dataset/), [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions), and [OpenSSF Scorecard](https://scorecard.dev/).
