# Pending Research Task: Validate Metric Audit, Dispatch Networked ETH/BTC Study, and Review Artifacts

**Status:** Pending CI validation and owner-side manual Actions dispatch  
**Priority:** High  
**Type:** Reproducible empirical replication and evidence review  
**Scope:** Backtesting only; no live orders or capital deployment


## Context

The metric/reporting corrections and six deterministic tests are on branch `agent/eth-btc-metric-audit-20261121`. The pull request should be checked for passing `Research pipeline tests` before merge. The manual-only workflow `.github/workflows/eth-btc-research.yml` remains unchanged. The available GitHub integration cannot enumerate all Actions runs or dispatch `workflow_dispatch`; an empty commit-associated workflow-run response is not proof of no run.


## Required actions

1. Inspect the pull request and verify CI has passed the complete test job, including all deterministic tests and synthetic smoke test. If CI cannot be verified through the integration, record it as **UNVERIFIED** and leave the PR unmerged.
2. Check **Actions → ETH-BTC networked empirical research** for a full-data run after the audit corrections. If none exists, the repository owner must manually dispatch with start `2020-01-01`, end `2026-10-31`, market `both`. Do not add push or scheduled triggers to bypass the manual gate.
3. When a verified run ID is available, inspect all jobs, steps, logs and artifacts. Download and inspect generated reports, CSV summaries, charts, data-quality JSON, archive/checksum manifests, funding manifests and run manifest.
4. Validate per-symbol hourly continuity, row counts, sample bounds, duplicate timestamps, skipped months, timestamp units, archive checksums, funding coverage and alignment. Keep raw market-data CSVs out of Git.
5. Review out-of-sample folds/regimes, cost sensitivity, benchmark accounting, funding attribution, turnover, drawdowns, bootstrap uncertainty and stress scenarios. Distinguish statistical cointegration from durable net trading edge.
6. Update the report and README with a reproducible evidence-based **GO / NO-GO / INCONCLUSIVE** conclusion. Disclose account-specific fees, borrow feasibility, historical execution costs and margin/liquidation gaps. Until real data and artifacts are inspected, keep the conclusion **INCONCLUSIVE**.


## Acceptance criteria

CI validation is passed and the metric audit is merged; the full networked workflow has run successfully; artifacts and data-quality evidence have been inspected; and a reproducible conclusion is recorded. If owner dispatch or artifact access remains blocked, document the exact remaining step and keep the empirical conclusion **INCONCLUSIVE**.
