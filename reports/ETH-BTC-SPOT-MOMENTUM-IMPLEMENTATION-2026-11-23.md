# ETH/BTC Spot Relative-Momentum — implementation handoff

**Date:** 2026-11-23 13:45 UTC  
**Status:** IMPLEMENTATION COMMITTED; EMPIRICAL RUN NOT YET DISPATCHED  
**Timebox:** MEDIUM difficulty; substantive cycle 1 of 4; implementation deadline 2026-11-26 18:00 UTC; final conclusion deadline 2026-11-28 18:00 UTC.

## Scope and safety

The frozen 200-day ETH/BTC Spot relative-momentum hypothesis now has a dedicated runner, isolated from the previous mean-reversion model and the unresolved USDⓈ-M funding workstream. The runner is Spot-only and downloads only Binance Spot ETHUSDT/BTCUSDT. It does not read funding data, call paid vendors, use credentials, access another venue, short, leverage or place orders.

## Implemented

- Exact Spot monthly archive download and SHA-256/checksum manifest capture.
- Reuse of the repository's existing no-trade-gap reconciliation and fail-closed Spot event-time acceptance gate.
- Daily UTC ratio and 200-valid-close SMA, with no forward-fill or synthetic prices.
- Signal-known time at next UTC midnight and execution at the first observed hourly open at or after that time.
- Long-only 100% ETH / 100% BTC rotation, with 5/10/15/20/25/50 bps all-in per-leg cost scenarios.
- BTC and ETH buy-and-hold, 50/50 buy-and-hold and 50/50 monthly-rebalanced benchmarks.
- Continuous-time elapsed-UTC CAGR, Sharpe, drawdown, turnover, time allocation and recovery-period metrics.
- Paired 3/7/14-calendar-day moving-block bootstrap for net excess CAGR versus BTC, 1,000 replications per block length, deterministic per-block seeds.
- Deterministic tests for the SMA, stale-close handling, next-observed-open execution, two-leg rotation costs, buy-and-hold drift, monthly rebalancing, paired bootstrap, decision gates and Spot-only data preparation.
- Gated control-workflow command `/qfr-run-eth-btc-spot-momentum`; only default-branch code runs and only reports/manifests are uploaded.

## Validation status

The source and tests are committed together with the workflow wiring and preregistration conventions. Hosted CI must pass before dispatch. No market-data backtest or empirical result has been produced by this implementation handoff. A passing unit test or synthetic test is engineering evidence only.

## Next action

Run the exact command on open control PR #2, then inspect the full Actions run, artifact, accepted input provenance, exact source hashes, benchmark outputs, bootstrap intervals and terminal decision. If the Spot gate fails, record the exact blocker and remain INCONCLUSIVE; do not bypass or weaken the gate. The separate funding-aware study remains INCONCLUSIVE.
