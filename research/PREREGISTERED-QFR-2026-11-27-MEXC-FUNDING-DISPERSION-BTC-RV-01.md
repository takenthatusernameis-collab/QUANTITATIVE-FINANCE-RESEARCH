# Preregistered Research — MEXC Intraday Funding Dispersion and BTC Realized Volatility

- **Hypothesis ID:** `QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01`
- **Registered:** `2026-11-27T23:39:43Z`
- **Initial status:** PREREGISTERED; source feasibility pending.
- **Difficulty:** MEDIUM
- **Difficulty rationale:** One public MEXC funding-history endpoint with bounded pagination, one public hourly contract-kline endpoint segmented below its documented 2,000-point cap, one fixed dispersion statistic, and existing standardized OLS/paired-loss helpers. Timestamp alignment, source-hash freezing, deterministic tests and one dedicated workflow are required. No credentials, paid data, Binance/Bybit dependency or custom trading simulator is required.
- **Timebox start:** `2026-11-27T23:39:43Z`
- **Maximum substantive cycles:** 4
- **Implementation deadline:** `2026-12-01T23:39:43Z`
- **Final research-conclusion deadline:** `2026-12-02T23:39:43Z`
- **Expiry rule:** Cycle 1 is source feasibility only. If MEXC contract metadata, funding cadence/history, hourly-kline schema/coverage or minimum complete event counts fail, close INCONCLUSIVE/INFEASIBLE without model fitting or venue substitution. If Cycle 1 passes, Cycle 2 may implement only the frozen model and tests; Cycle 3 may run one real-data backtest; Cycle 4 is an independent audit. The earlier of four substantive cycles or five calendar days governs. Expiry is never a performance NO-GO. No extension, clock reset, same-ID feature/target/lag changes, parameter search or repeated identical failed request.

## 1. Falsifiable question

Does the **within-day dispersion** of the three exact eight-hour MEXC BTC_USDT perpetual funding settlements add chronological out-of-sample information about the next 24-hour realized variance of the same MEXC perpetual contract, beyond recent realized variance, absolute return and the day's mean funding level?

The proposed mechanism is **intraday instability in the price of leveraged exposure**. A large spread among the 00:00, 08:00 and 16:00 UTC funding settlements may indicate rapidly changing leverage demand even when the daily mean funding rate is ordinary. That instability may precede greater realized price variation. This is a predictive claim, not proof of trader intent, liquidation causality or a tradable edge.

## 2. Novelty boundary and literature

This is materially different from the repository's completed MEXC funding-level screen: that study used the daily sum of funding to forecast next-session Spot downside loss. This study uses the **population standard deviation of three intraday settlements**, controls for their mean, forecasts **same-venue next-24-hour realized variance**, and uses hourly perpetual-contract closes. It is not a lookback, threshold or multiplier variation of the earlier study.

Relevant literature already studies extreme funding levels and subsequent Bitcoin returns, and separately models funding memory and liquidation-tail risk. A 2026 study also emphasizes point-in-time data availability and archive integrity in perpetual-futures research. The bounded contribution here is the exact within-day funding-dispersion statistic, mean-funding control, same-contract hourly target and frozen MEXC sample—not a first-in-literature claim.

- [Extreme Perpetual Futures Funding and Subsequent Bitcoin Returns: Intraday Evidence from Binance](https://scispace.com/papers/extreme-perpetual-futures-funding-and-subsequent-bitcoin-jvfbu2voc5a6)
- [Delayed Marks, Funding Memory, and Forecasting Liquidation-Tail Risk in Crypto Perpetual Futures](https://scispace.com/papers/delayed-marks-funding-memory-and-forecasting-liquidation-dv1c3r2ytuwj)
- [Point-in-Time Audit Before Alpha: Public-Archive Availability and a Negative Matched-Budget Study on BTC Perpetual Futures](https://scispace.com/papers/point-in-time-audit-before-alpha-public-archive-availability-l3zm5oizo910)

## 3. Frozen source order and feasibility gates

Use MEXC public market-data endpoints only. No private endpoints, API keys, order placement or account data.

### MEXC API host order

1. Primary REST base: `https://api.mexc.com`. MEXC's official changelog says the Futures API base domain changed to this host on 2026-01-19.
2. Compatibility diagnostic only: `https://contract.mexc.com`, the previously used Futures host. Try it only after a route-level 404/410, DNS failure or connection failure on the primary host. Never use another hostname to evade HTTP 401, 403, 429 or 451.
3. Do not substitute Binance, Bybit, another exchange, a wrapper or a third-party vendor under this hypothesis ID.

Official documentation:
- [MEXC Get Contract Information](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info).
- [MEXC Get Funding Rate History](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history): `GET /api/v1/contract/funding_rate/history`, `page_size` up to 1,000, fields `fundingRate`, millisecond `settleTime`, `collectCycle`, rate limit 20 requests per 2 seconds.
- [MEXC Get Candlestick Data](https://www.mexc.io/api-docs/futures/market-endpoints/get-candlestick-data): `GET /api/v1/contract/kline/{symbol}`, `Min60`, Unix-second `start`/`end`, maximum 2,000 points per request.
- [MEXC Futures API changelog](https://www.mexc.io/api-docs/futures/update-log).

### Contract and funding history

- Exact instrument: `BTC_USDT`, perpetual (`futureType=1`), `quoteCoin=USDT`, `settleCoin=USDT`, `state=0`.
- Contract detail: `GET /api/v1/contract/detail/country?symbol=BTC_USDT`.
- Funding history: `GET /api/v1/contract/funding_rate/history?symbol=BTC_USDT&page_num={page}&page_size=1000`.
- Retrieve every page in `totalPage`, hard maximum 10. Require `success=true`, `code=0`, stable pagination metadata, exact page progression and no duplicate settlement timestamps.
- Sample window: 2025-06-15 through 2026-11-26 inclusive.
- Each record must have finite funding rate, exact symbol, `collectCycle=8`, positive Unix-millisecond settlement time, and exact 00:00, 08:00 or 16:00 UTC alignment.
- Require at least 1,200 settlements, at least 400 complete UTC dates with exactly those three settlements, no more than 5% incomplete candidate dates, and a latest complete date no earlier than 2026-11-24. Missing settlements are never filled or treated as zero.

### Hourly contract prices

- Use the same MEXC `BTC_USDT` perpetual, `interval=Min60`, documented `time` and `close` arrays.
- Request non-overlapping segments of at most 1,800 hours, below the 2,000-point cap.
- Required hourly range: 2025-06-07 00:00 UTC through 2026-11-27 17:00 UTC, end exclusive.
- Require hour-aligned Unix-second timestamps, positive finite closes, unique bars, at least 99.5% coverage, no run of more than two consecutive missing hours, and a final completed bar at least through 2026-11-27 16:00 UTC.
- No forward fill, interpolation, venue mixing or silent gap repair.

### Event feasibility

- A candidate event exists only when that UTC date has all three exact funding settlements and all required hourly bars.
- Signal timestamp: 17:00 UTC on date d, after the 16:00 funding settlement and the completed 16:00–17:00 hourly candle. The one-hour settlement-to-signal embargo is frozen.
- Require at least 400 complete event windows, 120 pre-validation events for rolling warm-up, 30 validation events and 100 test events. If these gates fail, close INCONCLUSIVE/INFEASIBLE before model implementation.
- Source preflight may validate schema, coverage, cadence, timestamp alignment and event availability only. It must not calculate correlations, fit a model, inspect forecast errors or run a backtest.

Do not commit raw observations. Persist request URLs, retrieval time, response hashes, canonical in-window source hashes, coverage, pagination, missingness and validation outcomes only.

## 4. Frozen feature, signal and target

For each complete UTC date d:

- Funding observations: exact MEXC settlements at 00:00, 08:00 and 16:00 UTC.
- Baseline funding-level control: `funding_mean_bps = mean(r00, r08, r16) × 10,000`.
- Sole augmented feature: `funding_dispersion_bps = pstdev(r00, r08, r16) × 10,000`, population standard deviation. Do not substitute sample standard deviation, range, absolute changes, sign flips, alternate lags or other statistics.
- Signal: 17:00 UTC after the completed hourly candle and one-hour embargo after the last funding settlement.
- Baseline price features: `log1p(previous_24h_RV_bps2)`, `log1p(previous_168h_RV_bps2)`, and absolute previous-24h log return in basis points.
- Baseline model: those three price features plus `funding_mean_bps`.
- Augmented model: baseline plus exactly one feature, `funding_dispersion_bps`.
- Target window: 24 complete hourly log returns from 17:00 UTC on date d through 17:00 UTC on date d+1. Target: `log1p(sum(hourly_log_return²) × 10^8)`, or log1p of 24-hour realized variance in bp². This is not downside semivariance or trading P&L.
- Events occur once per UTC day. Target windows are adjacent but non-overlapping; a prior target must be fully matured strictly before a training signal.

## 5. Frozen walk-forward model and inference

- Training: latest 120 prior events whose signal timestamp and 24-hour target end are both strictly earlier than the current signal.
- Validation: 2025-11-01 through 2025-12-31.
- Test: 2026-01-01 onward.
- Estimator: repository standardized OLS helper with fixed 1e-8 coefficient ridge stabilization. No feature selection, hyperparameter search, regime slicing or parameter tuning.
- Compare baseline and augmented RMSE on the same chronological forecasts.
- Paired test squared-loss moving-block bootstrap: 2,000 replications, block size 7 daily events, seed 20261127. Positive baseline-minus-augmented loss favors augmentation.
- Minimum model sample: 30 validation forecasts, 100 test forecasts and a computable paired-loss interval.

## 6. Frozen decision rule

- **PROMISING (forecast screen only):** validation and test RMSE both improve, and the paired test-loss 95% confidence interval lower bound is strictly positive.
- **REJECTED:** validation and test RMSE both worsen, and the paired test-loss 95% confidence interval upper bound is strictly negative.
- **INCONCLUSIVE:** every other valid outcome, including mixed signs, an interval crossing zero or insufficient inference.
- Source/schema/coverage failure or timebox expiry before a valid empirical run is **INCONCLUSIVE/INFEASIBLE**, not a performance NO-GO.
- Even PROMISING is not independent validation, a causal finding, a tradable strategy, profitability evidence or permission to deploy. Do not report CAGR, Sharpe, Sortino, Calmar, drawdown or live-trading claims for this forecast-only experiment.

## 7. Cycle accounting

1. Cycle 1 — source feasibility only: contract detail, complete funding pagination, segmented hourly candles, canonical hashes and complete event counts. No model.
2. Cycle 2 — implement only after Cycle 1 passes; deterministic tests for API parsing, timestamp alignment, no-lookahead, 24-hour target construction, 120-event maturity, decision rule and bootstrap.
3. Cycle 3 — one frozen real-data walk-forward backtest; persist report, manifest and forecast rows; no same-ID rerun or tuning.
4. Cycle 4 — independent reconstruction from persisted forecast rows, metric/bootstrap verification, provenance audit and final closure.

Every cycle leaves a durable report or decision artifact. Identical retries, cosmetic edits and tool calls are not substantive cycles.

## 8. Security and interpretation boundaries

- Public endpoints only; no API key, account endpoint, private position, order, capital deployment or live trading.
- Do not evade regional or endpoint restrictions. HTTP 401/403/451 is not permission to change providers or route around access controls.
- MEXC historical API records do not provide a complete historical publication-time audit. The one-hour lag is conservative but does not prove exact historical API availability; this remains a limitation.
- Funding dispersion is not direct observation of trader identities, net leverage, open interest or liquidations. Funding can also reflect basis arbitrage, hedging, inventory and contract-specific mechanics.
- One contract and one venue do not establish cross-market generality. This is a forecast screen, not causal inference or executable strategy evaluation.
- Account for repository-wide multiple testing and selection bias. Any promising result requires an independent confirmation study.
