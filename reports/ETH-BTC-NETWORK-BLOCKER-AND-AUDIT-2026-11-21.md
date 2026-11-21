# ETH/BTC full-data run attempt and pre-run audit

**Date:** 2026-11-21  
**Status:** INCONCLUSIVE — no raw market data could be retrieved  
**Scope:** Research/backtesting only; no trading or capital deployment

## Run attempt

The pending `ETH-BTC-FULL-DATA-EXECUTION.md` task was attempted. This execution environment cannot resolve `data.binance.vision` (DNS failure from `curl`); the web reader also could not open the binary archive. Therefore, no historical candles or funding records were acquired, and no empirical strategy statistics were calculated.

The official Binance Public Data documentation confirms monthly/daily market-data archives and SHA-256 `.CHECKSUM` files:
- https://github.com/binance/binance-public-data
- https://developers.binance.com/en/docs/products/spot/rest-api

This is an environment-access failure, not evidence for or against ETH/BTC mean reversion.

## Workflow workaround added

A manual networked GitHub Actions workflow was committed:

- File: `.github/workflows/eth-btc-research.yml`
- Commit: `4bd671138084681caefc85c9e4e7568a34ccbb8d`
- Trigger: `workflow_dispatch` (manual)
- Inputs: inclusive start/end dates and market choice (spot, USDⓈ-M, or both)
- Runner: GitHub-hosted Ubuntu with Python 3.11; installs dependencies, runs the synthetic smoke test, then executes the full research pipeline.
- Caches downloaded Binance archives and uploads generated reports plus data manifests. It deliberately does **not** upload raw market-data CSVs.

The workflow file is present on `main`, but it has not been dispatched. This repository currently had no existing workflow files and no recorded workflow runs when inspected.

GitHub documents that a manual `workflow_dispatch` trigger creates a Run workflow button when the workflow exists on the default branch. See:
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

## Static code review — fix/validate before relying on results

The following items are concerns to verify or correct; they are not claims that the backtest is definitely wrong in every convention.

1. **Benchmark portfolio definitions and costs:** the 50/50 benchmark's simple weighted-return formula implicitly maintains constant weights each bar, while only entry/exit costs are charged. Specify whether each benchmark is buy-and-hold units or periodically rebalanced weights, and include rebalancing turnover/costs where applicable. Ensure benchmark exposure and capital bases are comparable.
2. **Half-life calculation:** the current code estimates a slope in `Δspread = c + γ·spread(t−1)` and reports `−ln(2)/γ`. This is an OU-style approximation. Validate against the exact discrete AR(1) half-life formula `−ln(2)/ln(φ)` for `0 < φ < 1`, where `φ = 1 + γ`; clearly label or report both.
3. **Funding completeness/alignment:** funding records are reindexed to hourly candle timestamps and missing values are filled with zero. Validate event timestamps, coverage, duplicates and gaps; never let missing funding silently look like zero funding.
4. **Market-data quality:** duplicate timestamps are dropped during consolidation; missing archive months are skipped; the final quality report is built from the synchronized pair only. Report duplicates, missing-hour counts, longest gap and per-symbol coverage before the inner join, and explicitly record skipped archives.
5. **Diagnostics labeling:** fold diagnostics are called once per strategy variant but the tests use the same static residual specification, so identical results are labeled `fixed_1x1` and `rolling_hedge`. Either make variant-specific diagnostics or label shared diagnostics clearly.
6. **Resilience and tests:** archive/API downloads have no retry/backoff. Add bounded retries, validate page/archive completeness, and create deterministic tests for next-open execution, funding settlement timing, entry/exit/rebalance costs, benchmark accounting, and missing-data handling. The existing synthetic self-test is only a plumbing smoke test.

The strategy signal/execution path was inspected: the close-derived signal is shifted to the next open, and open-to-open returns use prior-open holdings. No obvious look-ahead was identified in that alignment, but it needs dedicated unit tests before empirical performance is trusted.

## Conclusion

**INCONCLUSIVE.** No real-data performance can be reported. The next agent should address the audit items, run the manual workflow in GitHub Actions, inspect all outputs/data-quality manifests, and only then issue a supported GO/NO-GO/INCONCLUSIVE conclusion. Do not deploy capital based on the current synthetic tests or static review.
