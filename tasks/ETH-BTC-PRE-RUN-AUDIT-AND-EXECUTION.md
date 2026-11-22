# Pending Research Task: Audit, Harden, and Execute ETH/BTC Mean-Reversion Study

**Status:** Historical code audit and CI correction record; manual-dispatch instructions are obsolete; current work is `tasks/ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md`.
**Priority:** High  
**Type:** Pipeline correction + network-enabled empirical replication  
**Scope:** Research only. Do not deploy capital, place live orders, or commit raw market-data CSVs.


> **Historical / superseded execution note:** Historical audit record. Do not restart the old plan or ask the owner to activate a workflow. The agent must use the current authorized dispatch path, inspect all run states and artifacts, and switch to a materially different safe approach after a meaningful blocker.

## Context

The full-data execution task was attempted on 2026-11-21, but the current execution runtime cannot resolve `data.binance.vision`. A manual GitHub Actions workflow is now available at `.github/workflows/eth-btc-research.yml` and has not yet been run. The previous attempt and code-review concerns are documented in `reports/ETH-BTC-NETWORK-BLOCKER-AND-AUDIT-2026-11-21.md`.

## Objectives

1. Review and fix or explicitly justify the code-audit concerns before trusting results:
   - Benchmark accounting: distinguish buy-and-hold units from rebalanced weights; apply appropriate turnover costs to rebalancing.
   - Half-life: compare the OU approximation `−ln(2)/γ` with the exact discrete AR(1) half-life `−ln(2)/ln(φ)`, `φ=1+γ`; validate conditions and label the estimator clearly.
   - Funding: validate settlement timestamps, duplicate events, expected coverage and gaps. Do not silently convert incomplete funding data into zero funding.
   - Data quality: report each symbol's duplicate timestamps, missing hourly bars, longest gap, date coverage, archive/checksum coverage and skipped months before pair synchronization. Record the synchronized pair's quality separately.
   - Diagnostics: do not label duplicated shared static cointegration tests as variant-specific. Clearly separate common relationship diagnostics from strategy-specific diagnostics.
   - Download resilience: implement reasonable bounded retry/backoff and fail clearly on incomplete data or unexpected API responses.
2. Add deterministic tests for signal-close/next-open execution, PnL alignment, funding settlement timing, turnover/entry/exit/rebalance costs, benchmark calculations, gap detection, and missing funding.
3. Run the synthetic smoke test and full study through the network-enabled manual GitHub Actions workflow. Use `2020-01-01` through `2026-10-31` and `market=both` unless data/listing availability justifies a documented adjustment.
4. Verify checksums where available, timestamp units, sample bounds, hourly continuity and funding coverage. Inspect all OOS fold, volatility-regime, cost-sensitivity, diagnostic, stress and daily robustness outputs.
5. Replace default costs with sourced venue/account-specific inputs where verifiable; otherwise retain conservative scenarios and disclose uncertainty. Spot short-leg borrow remains theoretical unless borrow feasibility and costs are evidenced.
6. Produce a final reproducible report with a supported **GO / NO-GO / INCONCLUSIVE** conclusion, charts and machine-readable outputs. If the workflow cannot be triggered or a required data/cost input is unavailable, state the blocker precisely and classify the conclusion as **INCONCLUSIVE**.

## Execution constraints

- The workflow is manual-only (`workflow_dispatch`); do not add a daily full-data schedule.
- Raw price/funding CSVs stay out of Git. Keep hashes/manifests and report artifacts.
- Do not treat synthetic tests, statistical cointegration alone, or gross performance as proof of a tradable net edge.
- Do not start any live trading or capital deployment.

## Deliverables

- Corrected research code and dependencies.
- Deterministic tests.
- Verified market-data/funding quality manifests.
- Reproducible walk-forward fold/regime/cost/benchmark/stress outputs and charts.
- Final report with methodology, assumptions, limitations and conclusion.
- Execution record explaining workflow result and remaining blockers.

## Acceptance criteria

Task is complete only when code/test corrections are documented, the full empirical workflow has actually run successfully on real data, the output is reproducible, all performance is genuinely out of sample and net of stated costs, and the final conclusion is supported by diagnostics and sensitivity analysis. If any criterion cannot be met, leave the conclusion INCONCLUSIVE and record what remains.


## Automation execution update — 2026-11-21

- Confirmed the manual workflow `.github/workflows/eth-btc-research.yml` exists on the default branch and includes a hosted runner, Python setup, dependencies, a synthetic smoke-test command, a full-data research command, and artifact upload.
- The current GitHub connector exposes repository/file and commit operations but no workflow-dispatch action. The web interface/API for Actions runs is inaccessible through the current research tools, so I could not launch or verify the workflow run or retrieve its artifacts.
- Static review reconfirmed unresolved audit items: missing funding files and missing funding timestamps are silently treated as zero; monthly archives may be skipped without a completeness failure; downloads have no bounded retry/backoff; shared diagnostics are repeated under strategy labels; and the 50/50 benchmark is implicitly rebalanced each bar without charging rebalancing turnover. These must be corrected or explicitly modeled before interpreting results.
- **No empirical market-data results were produced.** This is a tooling/dispatch blocker, not a strategy result. The next actionable step is to manually dispatch the workflow from GitHub Actions after the code-audit corrections, then inspect logs and artifacts.


## Follow-up execution update — 2026-11-21

- Reviewed the latest CI run. The first run exposed one genuine defect in `funding_quality`: a 32-hour funding gap was allowed because the missing-event outlier inflated the median cadence estimate (8h and 32h gaps produced a 20h median and a 60h threshold).
- Corrected the cadence estimator to use observed intervals no longer than 24 hours as its reference, preventing long gaps from inflating the threshold. The manifest now records `cadence_reference_gap_hours`.
- Commit: `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`.
- Verification: GitHub Actions run [44906070305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44906070305) completed successfully on 2026-11-21. All 11 deterministic unit tests passed, followed by the synthetic plumbing smoke test. This verifies code/test plumbing only; it is not empirical market evidence.
- The previously identified code-audit items are now represented in the implementation: explicit buy-and-hold versus rebalanced benchmark accounting and turnover; exact discrete AR(1) half-life alongside the OU approximation; strict missing/duplicate funding validation and event alignment; per-symbol archive quality, missing-month failure and checksum manifests; explicitly shared static relationship diagnostics; and bounded transient-request retries.
- The full-data workflow remains manual-only. The available GitHub integration can inspect workflow runs and logs but cannot invoke `workflow_dispatch`. No empirical ETH/BTC results have been generated. The next task is to dispatch the existing workflow manually and review its artifacts.
