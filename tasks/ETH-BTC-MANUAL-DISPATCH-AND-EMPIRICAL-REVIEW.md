# Pending Research Task: Dispatch and Review the Full ETH/BTC Empirical Study

**Status:** Pending manual workflow dispatch  
**Priority:** High  
**Type:** Network-enabled empirical replication and results review  
**Scope:** Research/backtesting only. Do not deploy capital or place live orders.

## Context

The research code audit and deterministic CI validation are complete. Commit `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1` fixes the funding-gap completeness defect. GitHub Actions run [44906070305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44906070305) passed all 11 unit tests and the synthetic plumbing smoke test.

The full-data workflow exists at [eth-btc-research.yml](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/blob/main/.github/workflows/eth-btc-research.yml), but it is manual-only. The current GitHub integration can inspect runs, jobs, logs and artifacts but cannot invoke the `workflow_dispatch` API.

## Required execution

1. Inspect GitHub Actions for a run of **ETH-BTC networked empirical research** created after commit `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`.
2. If no run exists, do not modify the workflow merely to create an automatic push or scheduled trigger. Record that a repository owner must manually open **Actions → ETH-BTC networked empirical research → Run workflow** and dispatch:
   - start: `2020-01-01`
   - end: `2026-10-31`
   - market: `both`
   Keep the workflow one-off/manual.
3. If a run exists, inspect its status, every job/step, logs and artifacts. Do not call it complete while it is queued, in progress, failed, or missing expected artifacts.
4. On success, download and inspect the generated report, CSV summaries, charts, data-quality JSON, archive/checksum manifests, funding manifests and run manifest. Verify sample bounds, row counts, per-symbol hourly continuity, duplicates, skipped months, timestamp units, checksum status and funding gaps.
5. Review the out-of-sample fold and volatility-regime results, cost sensitivities, benchmark accounting, funding contributions, turnover, drawdowns, bootstrap uncertainty and stress scenarios. Confirm the report distinguishes statistical cointegration from a durable net trading edge.
6. Keep raw market-data CSVs out of Git. Record artifact names, hashes and reproducibility details. Update the research report and task status.
7. Use **GO / NO-GO / INCONCLUSIVE** only when supported by the evidence. If account-specific fees, historical execution costs, borrow feasibility, or margin/liquidation modeling remain unavailable, disclose them and do not overstate tradability. No live trading.

## Acceptance criteria

The task is complete only after the full workflow has run successfully on real data, artifacts have been inspected, and a reproducible evidence-based conclusion has been recorded. If manual dispatch has not occurred, report the exact manual step and leave the empirical conclusion **INCONCLUSIVE**.
