# Pending Research Task: Audit, Harden, and Execute ETH/BTC Mean-Reversion Study

**Status:** Ready for execution  
**Priority:** High  
**Type:** Pipeline correction + network-enabled empirical replication  
**Scope:** Research only. Do not deploy capital, place live orders, or commit raw market-data CSVs.

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
