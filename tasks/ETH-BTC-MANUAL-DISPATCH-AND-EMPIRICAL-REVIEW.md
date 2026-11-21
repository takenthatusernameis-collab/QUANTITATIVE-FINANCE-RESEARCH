# Pending Research Task: Dispatch and Review the Full ETH/BTC Empirical Study

**Status:** Metric corrections merged and CI passed; pending owner-side Actions dispatch and empirical artifact review  
**Priority:** High  
**Type:** Network-enabled empirical replication and results review  
**Scope:** Research/backtesting only. Do not deploy capital or place live orders.

## Context

The code audit corrections committed in `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1` fixed the funding-gap completeness defect. GitHub Actions run [44906070305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44906070305) was independently inspected: its `test` job completed successfully, all 11 deterministic unit tests passed, and the synthetic plumbing smoke test passed. It checked the test workflow only; it is **not** the full empirical study. The test workflow produced no artifacts, as expected.

The full-data workflow exists at [eth-btc-research.yml](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/blob/main/.github/workflows/eth-btc-research.yml), with a manual-only `workflow_dispatch` trigger.

**Tooling limitation:** the current GitHub integration can inspect jobs, logs and artifacts when supplied a known run ID, but it does not expose a repository-wide workflow-run listing or a `workflow_dispatch` action. Its commit-associated workflow-run lookup is limited to pull-request-triggered runs; an empty response is not proof that no Actions run exists. The Actions page could not be read through the current research interface. Therefore the full-data run's existence/status is **UNVERIFIED**, not confirmed absent. A repository owner must inspect the Actions UI and, if no full-data run exists, dispatch it manually.

## Pre-dispatch metric and reporting audit

Before launching the expensive full-data workflow, inspect and correct these issues in `research/run_eth_btc.py`, adding deterministic tests:

1. **Sortino denominator:** the current implementation takes the standard deviation of only negative returns. For the documented 0% minimum acceptable return, use downside deviation based on all observations, i.e. the root mean square of `min(return, 0)`. Test mixed-return and all-negative samples.
2. **Initial-capital drawdown:** the current equity curve starts at the first realized bar and computes its running peak only from that bar onward. Include initial NAV = 1.0 in the peak path so a first-bar entry loss is not omitted from maximum drawdown. Add a regression test.
3. **Exposure alignment:** PnL on timestamp `t` uses the weights held from the prior open, while average gross exposure currently uses weights at `t`. Align the reported average exposure with the same holding interval used for returns, and test the convention.
4. **Funding stress output:** the generated “three funding events” scenario is also written for Spot runs, even though Spot has no perpetual funding. Restrict it to USDⓈ-M results and make the assumed ETH/BTC funding-rate shock explicit; do not imply identical funding rates are observed data.
5. **Bootstrap precision:** assess whether 150 moving-block bootstrap replications are sufficient for a reported 95% Sharpe interval. Increase the count only if runtime remains reasonable, or clearly label the interval exploratory and document the replication count.

Keep the research specification pre-registered: do not optimize thresholds after seeing OOS results. Preserve the original prompt archive and do not change the full-data workflow to push or scheduled execution merely to bypass the manual gate.

## Progress record — 2026-11-21

- Implemented Sortino downside RMS over all observations, initial-NAV drawdown, interval-aligned average gross exposure, and market-specific funding stress reporting.
- Added six deterministic tests covering mixed/all-negative downside samples, Sortino integration, initial drawdown, exposure alignment, funding-stress gating/assumptions, and bootstrap labeling.
- Kept the 150-replication Sharpe bootstrap but labeled the interval exploratory with limited quantile precision.
- PR #1 was merged as `305bf5c70a14d8a8167dbbd4a22ec95f775402f7`; CI run `44929403565` (run 14) passed all 17 deterministic tests and the synthetic plumbing smoke test. The full empirical run remains unverified and requires owner-side Actions dispatch.

## Required execution

1. Metric audit corrections are merged and CI passed; this step is complete. No additional code changes are required unless the later artifact review finds a new defect.
2. Check GitHub Actions manually for a run of **ETH-BTC networked empirical research** created after commit `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`. Because the current integration cannot enumerate all workflow runs, do not infer absence from an empty commit-associated workflow-run response. If a run ID is supplied or otherwise verified, inspect its status, every job/step, logs and artifacts.
3. If no full-data run exists, do not modify the workflow merely to add an automatic push or scheduled trigger. The repository owner must open **Actions → ETH-BTC networked empirical research → Run workflow** and dispatch:
   - start: `2020-01-01`
   - end: `2026-10-31`
   - market: `both`
   Keep the workflow one-off/manual.
4. On successful completion, download and inspect the generated report, CSV summaries, charts, data-quality JSON, archive/checksum manifests, funding manifests and run manifest. Verify sample bounds, row counts, per-symbol hourly continuity, duplicates, skipped months, timestamp units, checksum status and funding gaps.
5. Review out-of-sample folds and volatility regimes, cost sensitivities, benchmark accounting, funding contributions, turnover, drawdowns, bootstrap uncertainty and stress scenarios. Distinguish statistical cointegration from a durable net trading edge.
6. Keep raw market-data CSVs out of Git. Record artifact names, hashes and reproducibility details. Update the research report and task status.
7. Use **GO / NO-GO / INCONCLUSIVE** only when supported by evidence. If account-specific fees, historical execution costs, borrow feasibility, or margin/liquidation modeling remain unavailable, disclose them and do not overstate tradability. No live trading.

## Acceptance criteria

The task is complete only after the metric definitions are corrected and tested, the full workflow has run successfully on real data, artifacts have been inspected, and a reproducible evidence-based conclusion has been recorded. If manual dispatch has not occurred or real-data artifacts are unavailable, report the exact blocker and leave the empirical conclusion **INCONCLUSIVE**.
