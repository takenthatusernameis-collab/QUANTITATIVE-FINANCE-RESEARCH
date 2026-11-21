# Pending Research Task: Complete ETH/BTC Mean-Reversion Study with Verified Data

**Status:** Ready for execution  
**Priority:** High  
**Type:** Empirical replication and completion  
**Scope:** Research and backtesting only; do not deploy capital or place live orders.

## Objective

Complete the ETH/BTC market-neutral mean-reversion study left INCONCLUSIVE in `reports/ETH-BTC-MEAN-REVERSION-2026-11-21.md` because the prior execution environment could not retrieve raw market data.

## Required work

1. Run `research/run_eth_btc.py` in an environment with working outbound access to Binance Public Data and the USDⓈ-M funding-rate API. Start with `--start 2020-01-01 --end 2026-10-31 --market both` unless verified listing/data availability requires a documented adjustment.
2. Verify archive SHA-256 checksums where available. Record exact sample start/end, row counts, duplicate timestamps, missing-hour counts, maximum gaps, timestamp units, and the data hashes in a committed manifest. Do not commit large raw market-data files.
3. Inspect the code and outputs for implementation defects before interpreting results. In particular verify next-bar-open execution alignment, funding-event alignment, daily beta update timing, fold liquidation costs, benchmark entry/exit costs, and no look-ahead.
4. Replace illustrative fee, slippage, spread and spot-borrow assumptions with sourced, venue-specific inputs where possible. If historical bid/ask or borrow data cannot be obtained, keep those costs as explicit conservative scenarios and retain the limitation in the report.
5. Review Engle–Granger, ADF, KPSS, Johansen, Zivot–Andrews, rolling cointegration stability and half-life diagnostics by training fold. Distinguish statistical cointegration from a tradable net edge.
6. Review hourly out-of-sample results by fold and volatility regime for both fixed 1:1 and rolling hedge-ratio strategies. Compare with all supplied benchmarks and 1.0x / 1.5x / 2.0x costs. Inspect bootstrap Sharpe intervals, drawdowns, tail losses, turnover, funding and exposure.
7. Inspect stress scenarios and explicitly discuss margin/liquidation, prolonged non-convergence, volatility/funding shocks, exchange outages and execution gaps. Do not claim liquidation realism unless a margin model is implemented and validated.
8. Produce a final report with a supported **GO / NO-GO / INCONCLUSIVE** conclusion, machine-readable outputs, and all requested charts. If any key data or cost input remains unavailable, classify the result as **INCONCLUSIVE**.

## Deliverables

- Updated research code and dependency file if corrections are needed.
- Verified data manifest and quality report (no raw market data required in Git).
- Hourly OOS fold, regime, diagnostics, cost-sensitivity and stress outputs.
- Daily robustness outputs, clearly labeled price-only unless funding and daily execution costs are fully represented.
- Final report with reproducibility instructions, assumptions, limitations and conclusion.

## Acceptance criteria

The task is complete only when the empirical results are reproducible, all performance is genuinely out of sample and net of stated costs, the raw-data provenance is verifiable, and the conclusion is supported by diagnostics and sensitivity tests. No live orders or capital deployment are permitted.
