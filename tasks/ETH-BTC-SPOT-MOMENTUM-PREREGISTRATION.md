# Preregistered ETH/BTC spot relative-momentum rotation

**Status:** PENDING — 2026-11-23  
**Priority:** P5 hypothesis/model replacement after original funding-data architecture screen  
**Scope:** Separate spot-only experiment. No leverage, shorting, funding data, venue merge or live deployment.

## Mandatory timebox — frozen before implementation

- **Policy activation:** the preceding Binance Spot ETH/BTC mean-reversion study reached NO-GO on 2026-11-22. This new, separately preregistered model is the first model subject to the activated deadline policy. The unresolved USDⓈ-M funding-aware study is separate and does not defer this requirement.
- **Expected implementation difficulty:** MEDIUM.
- **Rationale:** the model is a single frozen 200-day relative-momentum rule and accepted Spot data/event-time infrastructure already exist; moderate integration, next-hour execution/elapsed-time verification, benchmark/cost/bootstrap validation, tests and reporting remain.
- **Timebox start:** 2026-11-23T13:14:44Z (UTC; preregistration commit timestamp).
- **Maximum budget:** 4 substantive agent cycles total, including implementation, valid empirical execution, analysis and final reporting.
- **Hard implementation deadline:** 2026-11-26 18:00 UTC.
- **Hard final conclusion deadline:** 2026-11-28 18:00 UTC.
- **Deadline rule:** if all data/code/methodology gates pass, report GO or NO-GO using the frozen criteria. If a valid empirical conclusion is not available by the final deadline, close as INCONCLUSIVE/INFEASIBLE with the exact blocker. Expiry is not a performance NO-GO. Do not weaken gates, reset the clock or extend the deadline automatically.
- **Completion evidence:** repository-committed implementation, deterministic tests, accepted source/provenance checks, reproducible empirical outputs, complete report and terminal decision. An uncommitted local prototype or synthetic test alone does not satisfy completion.

See [the governing timebox policy](../docs/MODEL-IMPLEMENTATION-TIMEBOX-POLICY.md). These dates and limits are frozen.

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

## Frozen implementation conventions

The following operational details are fixed before any empirical result is inspected:

- A UTC day's close is the last observed hourly close in that day, but it is eligible only if its close timestamp is no more than one hour before the UTC midnight boundary. A stale or absent daily close generates no new signal; the existing target is retained. No price is forward-filled or synthesized.
- The 200-day SMA is the arithmetic mean of the current completed daily ratio and the preceding 199 valid daily closes. A signal is known at the next UTC midnight.
- Execution occurs at the first observed hourly open at or after the signal-known timestamp. If the exact 00:00 bar is absent, execution is delayed to the next observed open and the delay is recorded.
- The OOS interval is the observed hourly-open sample from 2022-01-01 00:00 UTC inclusive through 2026-11-01 00:00 UTC exclusive. The final observed OOS open is liquidated to cash at that open.
- Transaction-cost inputs are all-in bps per one-way leg. Initial entry and final exit each incur one leg; a full ETH-to-BTC rotation incurs two legs. Benchmarks use the same cost convention.
- Sharpe is computed using the repository's continuous-time elapsed-UTC estimator because the accepted hourly Spot index can contain provenance-confirmed no-trade gaps.
- Paired moving-block bootstrap resamples strategy and BTC returns with identical contiguous observed-time blocks. Block starts are weighted by the elapsed duration of their first interval. Use 1,000 replications for each 3-, 7- and 14-calendar-day block, 95% percentile intervals, base seed 20261123 and per-block seed = base seed + block length. Compound the zero-duration initial entry cost into the first positive-duration interval before resampling.
- The bootstrap gate is conservative: the 95% lower confidence bound for excess CAGR must be above zero for all three preregistered block lengths. The 15 and 20 bps stress cases must remain profitable and preserve the point-estimate decision versus BTC (CAGR, Sharpe and drawdown criteria).

## Execution and stop conditions

- This is one frozen model with no parameter grid, no optimization or post-result rule changes.
- Reuse the accepted spot dataset and existing pipeline; repair only necessary data/implementation issues.
- If data quality fails, diagnose one materially different repair and stop after two distinct failures; no repeated downloads unchanged.
- Produce the report, reproducible code, tests, charts and exact source hashes. Do not use funding data or other venues.
- Keep the original perpetual/funding-aware study INCONCLUSIVE until its own data gate is accepted. Do not imply this spot model is the same experiment.
