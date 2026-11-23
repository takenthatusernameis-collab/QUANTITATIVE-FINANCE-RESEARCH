# Preregistered ETH/BTC spot relative-momentum rotation

**Status:** PENDING — 2026-11-23  
**Priority:** P5 hypothesis/model replacement after original funding-data architecture screen  
**Scope:** Separate spot-only experiment. No leverage, shorting, funding data, venue merge or live deployment.

## Hypothesis

A simple long-only regime rotation using the ETH/BTC relative trend can outperform BTC buy-and-hold over a multi-year out-of-sample period after trading costs, with a better risk-adjusted return and no worse maximum drawdown. This is a new hypothesis, not a reinterpretation of the NO-GO spot mean-reversion results.

## Frozen model (no parameter search)

- Data: accepted hourly Binance Spot ETHUSDT and BTCUSDT bars; same venue, same quote currency, UTC.
- Compute daily UTC-close ratio R = ETHUSDT / BTCUSDT.
- Signal: at daily close, if R is above its 200-day simple moving average, target 100% ETH; otherwise target 100% BTC.
- Execute a change only at the next UTC-hour open after the signal is known; no look-ahead.
- No leverage, shorts, stop loss, funding, or additional filters. Rebalance only when the target asset changes.
- Use 2020–2021 for the 200-day warm-up. Evaluate pooled out-of-sample from 2022-01-01 through 2026-10-31, without optimizing parameters.

## Benchmarks

- BTC buy-and-hold
- ETH buy-and-hold
- 50/50 ETH/BTC buy-and-hold
- 50/50 ETH/BTC monthly rebalanced

## Costs and metrics

- Baseline cost: 10 basis points per one-way leg; each ETH↔BTC rotation incurs costs on both legs.
- Cost sensitivity: 5, 10, 15, 20, 25 and 50 bps per leg.
- Report net OOS CAGR, Sharpe, maximum drawdown, Calmar, turnover, total transaction costs, time in ETH/BTC and recovery periods.
- Bootstrap net excess CAGR versus BTC using 3-, 7- and 14-day blocks with 95% confidence intervals; record seed and method.

## GO criteria

GO only if the net pooled OOS strategy:
1. beats BTC buy-and-hold CAGR after baseline costs;
2. has a higher Sharpe than BTC;
3. has maximum drawdown no worse than BTC;
4. has a 95% block-bootstrap lower confidence bound for excess CAGR above zero; and
5. remains profitable and does not reverse its decision under 1.5× (15 bps) and 2× (20 bps) baseline costs.

Otherwise report NO-GO. A GO is research-only, not authorization to trade.

## Execution and stop conditions

- This is one frozen model with no parameter grid, no optimization or post-result rule changes.
- Reuse the accepted spot dataset and existing pipeline; repair only necessary data/implementation issues.
- If data quality fails, diagnose one materially different repair and stop after two distinct failures; no repeated downloads unchanged.
- Produce the report, reproducible code, tests, charts and exact source hashes. Do not use funding data or other venues.
- Keep the original perpetual/funding-aware study INCONCLUSIVE until its own data gate is accepted. Do not imply this spot model is the same experiment.
