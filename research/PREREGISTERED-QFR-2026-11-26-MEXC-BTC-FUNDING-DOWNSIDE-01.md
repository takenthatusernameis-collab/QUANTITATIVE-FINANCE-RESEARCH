# Preregistration — MEXC BTC perpetual funding pressure and next-session BTC downside risk

- **Hypothesis ID:** QFR-2026-11-26-MEXC-BTC-FUNDING-DOWNSIDE-01
- **Registered:** 2026-11-26T15:15:43Z, before implementation and empirical-result inspection.
- **Initial status:** PREREGISTERED.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** one public paginated MEXC funding-history endpoint, one existing Binance Spot archive pipeline, daily aggregation of three 8-hour settlements, one lagged feature, a new one-session downside target, deterministic cadence/alignment tests, a dedicated workflow and evidence persistence. Existing repository helpers cover archive verification, daily semivariance, standardized OLS, metrics and paired block bootstrap. The source history may be limited to roughly 540 days and must be verified before any model result is interpreted.
- **Timebox start:** 2026-11-26T15:15:43Z.
- **Maximum substantive cycles:** 4 total.
- **Hard implementation deadline:** 2026-11-29T15:15:43Z.
- **Hard final research-conclusion deadline:** 2026-12-01T15:15:43Z.
- **Expiry rule:** the earlier of four substantive cycles or the five-calendar-day limit governs. If the MEXC source cannot meet the frozen history, cadence, freshness or sample gates, close INCONCLUSIVE/INFEASIBLE with the exact source limitation. If implementation, tests or the frozen empirical screen remain incomplete at the applicable deadline, close INCONCLUSIVE/INFEASIBLE. No automatic extension, silent clock reset, relaxed gate, same-ID retuning or duplicate source route.

## Research question and falsifiable claim

Does the prior UTC day's cumulative MEXC BTC_USDT perpetual funding rate add chronological out-of-sample information about the next Binance BTCUSDT Spot daily downside loss beyond Bitcoin's own recent downside semivariance and realized variance?

The mechanism is **perpetual leverage-price pressure**. Persistently positive funding means longs pay shorts and may reflect a premium for leveraged long exposure. If this premium represents crowded long-side risk, unusually positive 24-hour funding may precede greater next-session BTC downside risk as leveraged exposure is reduced. Negative funding may reflect the opposite imbalance. This is a predictive hypothesis, not a claim that funding uniquely identifies trader intent or causes subsequent returns.

## Novelty and literature boundary

This hypothesis uses an exchange-published **perpetual funding settlement cashflow price** as a measure of marginal derivatives leverage demand. It is materially distinct from the CFTC Bitcoin study, which used weekly leveraged-fund gross-short positions/open interest, and from the Deribit study, which used options-implied volatility. It is not a parameter variation of either.

- Official MEXC endpoint documentation: [Get Funding Rate History](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history). The endpoint is `GET /api/v1/contract/funding_rate/history`, accepts `symbol`, `page_num` and `page_size`, and documents a maximum page size of 1,000 plus `fundingRate`, `settleTime` and `collectCycle`.
- Official MEXC endpoint documentation: [Get Candlestick Data](https://www.mexc.io/api-docs/futures/market-endpoints/get-candlestick-data). The contract kline endpoint supports `Day1`, Unix-second `start`/`end` and at most 2,000 points per request.
- Binance official public market-data archive: https://github.com/binance/binance-public-data.
- No first-in-literature claim is made. The bounded contribution is a one-day, cross-venue funding-to-Spot-downside forecast screen with strict settlement-time alignment.

## Data feasibility, source and coverage gates

### MEXC BTC_USDT perpetual funding history

- Endpoint: `https://contract.mexc.com/api/v1/contract/funding_rate/history?symbol=BTC_USDT&page_num={page}&page_size=1000`.
- Retrieve every page indicated by the API's `totalPage`, with a hard maximum of 10 pages; verify `success=true`, `code=0`, symbol `BTC_USDT`, matching page metadata, stable `totalCount`, and exact page progression.
- Require at least 1,200 distinct settlement observations, at least 400 accepted UTC dates with exactly three settlements, and a sample reaching at least 2025-06-15 through 2026-11-23. If the official endpoint exposes materially less history than this frozen minimum, close INCONCLUSIVE/INFEASIBLE rather than shortening the sample or changing the split.
- Each accepted record must have finite `fundingRate`, positive integer `settleTime` in Unix milliseconds, `collectCycle=8`, exact `symbol=BTC_USDT`, and a settlement time aligned to 00:00, 08:00 or 16:00 UTC. Reject duplicate settlement timestamps, future timestamps and records outside the frozen sample.
- The accepted event day must contain exactly the three expected settlements (00:00, 08:00 and 16:00 UTC). Missing or extra settlements are not filled. Days with incomplete funding history are skipped and counted.
- Require at least 400 accepted complete funding days, no more than 5% incomplete candidate days in the frozen common source window, and no missing run of more than three consecutive UTC days among accepted daily funding groups. Do not silently interpret an API page cap as complete lifetime history.
- Preserve exact request URLs, retrieval timestamp, page counts, API-reported total count, accepted row count, coverage, response SHA-256 per page and a deterministic aggregate manifest hash. Do not commit raw funding observations.

### Binance BTCUSDT Spot daily reference

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC; use the repository's existing official Vision archive and SHA-256 sidecar verifier.
- Frozen sample: 2025-06-15 through 2026-11-23 inclusive. Retrieve official monthly/daily archives and verify every archive against its official checksum sidecar.
- Require at least 500 completed daily candles, exact frozen last date, positive finite closes, unique UTC dates and no missing UTC date in the accepted window. Exclude any incomplete current candle.
- Do not commit raw market observations.

## Frozen feature, signal and target

- Funding observation: each MEXC funding settlement is assigned to its exact UTC calendar date using `settleTime`.
- Daily funding feature: sum the three funding rates settled at 00:00, 08:00 and 16:00 UTC on date d. This is the cumulative simple funding rate for the three settlements; do not compound, rescale or annualize it.
- Signal timing: use the daily funding sum for date d only at the close of the Binance Spot UTC daily candle dated d. Binance's candle close occurs at the end of that UTC date, after the 16:00 UTC settlement. The feature must not include any settlement dated d+1.
- Target: next one-session BTCUSDT downside semivariance, defined as `max(-r[d+1], 0)^2 * 10,000`, where r is the next Binance daily close-to-close log return. This is one-observation downside loss in percentage-points squared; it is not annualized and is not a trading P&L.
- Baseline predictors: log1p of prior-one-session downside loss, log1p of prior-five-session downside semivariance, and log1p of prior-five-session total realized variance.
- Augmented model: baseline predictors plus the daily cumulative funding-rate sum. No additional feature, threshold, interaction, regime split or parameter search is permitted under this hypothesis ID.
- Event schedule: one event per accepted complete funding day with a matching Binance Spot close and a complete next-session target. One-session targets do not overlap.
- Missing or stale funding dates, missing daily closes, invalid returns or incomplete target windows are skipped and counted; no forward-fill, interpolation or calendar bridging.

## Walk-forward model and evaluation

- Baseline and augmented models use the repository's standardized, ridge-stabilized OLS predictor; all scaling and fitting use training observations only.
- Rolling training window: 104 prior daily events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2025-10-01 through 2026-02-28.
- Test: signal dates 2026-03-01 onward through the frozen sample end.
- Minimum acceptance sample: at least 60 forecasts in validation and 120 in test. If the source depth or frozen split cannot yield these samples, close INCONCLUSIVE/INFEASIBLE; do not move the split or shorten the training window after inspecting results.
- Primary metric: RMSE in log1p one-session downside-loss space; MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length seven daily events, fixed seed 20261126.

## Frozen decision rule

- **BACKTESTED / PROMISING FORECAST SCREEN:** at least 60 validation and 120 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound is strictly above zero.
- **REJECTED:** augmented RMSE fails to improve in both periods and the paired test squared-loss 95% upper confidence bound is strictly below zero.
- **INCONCLUSIVE:** every other outcome, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale sources, cadence changes, source-history caps or incomplete data.
- A promising result remains a forecast-only screen. It is not independent validation or a trading strategy.

## Implementation acceptance

- Deterministic parser tests cover the MEXC response envelope, pagination metadata, symbol, timestamp units, finite rates, exact 8-hour cadence, expected UTC settlement slots, duplicates, incomplete days and source-history limits.
- Event tests prove that the date-d funding feature is available at the date-d Binance daily close, excludes date d+1 settlements, uses only next-session returns for the target, and skips incomplete windows without filling.
- Walk-forward tests prove the 104-event fully matured training requirement.
- Decision-rule, source-hash, report/manifest and idempotent registry/preregistration update tests pass.
- The complete workflow compiles, runs the model-specific suite and repository workflow-admission regression suite before retrieving empirical sources.
- The triggering commit SHA, API page hashes, Binance archive checksums, report and manifest are retained.

## Limitations and safety

- MEXC funding history is one venue's perpetual market, not a consolidated global funding index. The endpoint's currently available historical depth may be limited and is a key feasibility gate.
- Positive funding is not a direct measure of net directional long exposure; arbitrage, hedging, market-maker inventory, contract basis and participant composition can affect it.
- Binance Spot closes are a single venue's reference price, not MEXC index/fair price or executable perpetual P&L. Cross-venue basis and close-time differences remain limitations.
- A one-session downside-loss forecast is not a causal result, a position-sizing rule or a strategy.
- No transaction-cost-adjusted performance, funding-capture P&L, leverage return, profitability, live order, capital deployment or strategy-promotion claim is authorized.
- Do not assign CAGR, Sharpe, Sortino, Calmar, turnover or drawdown to this forecast-only result.

## Empirical disposition

- **Status:** PREREGISTERED
- **No empirical result has been inspected under this hypothesis ID.**
