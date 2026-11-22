# Historical Task: Pre-Dispatch ETH/BTC Metric and Reporting Audit

**Status:** Historical implementation audit complete; owner-side/manual dispatch instructions are obsolete. Current empirical follow-up is `tasks/ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md`.
**Priority:** High  
**Type:** Reproducible empirical replication and evidence review  
**Scope:** Backtesting only; no live orders or capital deployment


> **Historical / superseded execution note:** Historical record retained for auditability. No manual workflow activation is part of the current operating procedure. Use the verified agent-controlled command, inspect and deduplicate existing runs, apply deterministic queue cancellation, and start one isolated alternative attempt if cancellation is unavailable or fails.

## Context

This task originally covered the metric/reporting corrections and the first attempt to dispatch the full ETH/BTC study. The metric audit was merged in `305bf5c70a14d8a8167dbbd4a22ec95f775402f7`; the later funding-gap cadence correction was committed in `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`.

At the time this task was drafted, the GitHub integration could not enumerate all workflow runs. That limitation has since changed: on 2026-11-21 the complete Actions run collection returned 16 of 16 runs, all from `.github/workflows/research-tests.yml`, and none from the full-data workflow `.github/workflows/eth-btc-research.yml`. The integration still exposes no `workflow_dispatch` action. Current owner dispatch and post-run review are tracked in:
- `tasks/ETH-BTC-CI-DISPATCH-AND-ARTIFACT-REVIEW.md`
- `tasks/ETH-BTC-POST-DISPATCH-ARTIFACT-REVIEW.md`

## Pre-dispatch metric and reporting audit

The following corrections were implemented in `research/run_eth_btc.py` and covered by deterministic tests:

1. Sortino downside deviation uses the root-mean-square of negative returns over all observations, with a 0% minimum acceptable return.
2. Maximum drawdown includes initial NAV = 1.0 in the peak path.
3. Average gross exposure is aligned with the lagged weights held during each return interval.
4. Funding stress is reported only for USDⓈ-M results and its hypothetical rate assumptions are explicit.
5. The 150-replication Sharpe bootstrap interval is labeled exploratory, with limited quantile precision.

Additional audit corrections cover benchmark buy-and-hold versus rebalanced accounting, exact discrete AR(1) half-life reporting alongside the OU approximation, funding-event completeness/alignment, per-symbol hourly quality checks, shared diagnostic labeling, and bounded retries.

## Verification record — 2026-11-21

- PR #1 was merged as `305bf5c70a14d8a8167dbbd4a22ec95f775402f7`.
- The latest test CI run [44929570103](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44929570103) passed all 17 deterministic tests and the synthetic plumbing smoke test.
- The subsequent funding-gap cadence correction passed its own earlier CI run [44906070305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44906070305).
- These checks validate code and plumbing only; they do not establish market-data validity or strategy performance.

## Remaining empirical gate

The full-data workflow remains manual-only. The repository owner must dispatch it with start `2020-01-01`, end `2026-10-31`, market `both`. The current GitHub integration cannot invoke that dispatch. After a verified run exists, follow `tasks/ETH-BTC-POST-DISPATCH-ARTIFACT-REVIEW.md` to inspect its jobs, logs, artifacts, data-quality manifests and out-of-sample results.

Keep the empirical conclusion **INCONCLUSIVE** until real data and artifacts have been inspected. No live trading or capital deployment.
