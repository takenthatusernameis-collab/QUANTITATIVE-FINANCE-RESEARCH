# Preregistration — news-based US economic policy uncertainty and Bitcoin downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-EPU-BTC-DOWNSIDE-SEMIVARIANCE-01
- **Registered:** 2026-11-26T14:43:43Z, before implementation and empirical-result inspection.
- **Status:** PREREGISTERED
- **Difficulty:** LOW.
- **Difficulty rationale:** one public daily FRED series, one existing BTCUSDT Spot archive pipeline, one lagged feature, one instrument, one established walk-forward model and no new infrastructure. The source schema, price retrieval, semivariance functions and OLS/bootstrap helpers already exist in the repository.
- **Timebox start:** 2026-11-26T14:43:43Z.
- **Maximum substantive cycles:** 2 total.
- **Hard implementation deadline:** 2026-11-27T14:43:43Z.
- **Hard final research-conclusion deadline:** 2026-11-28T14:43:43Z.
- **Expiry rule:** the earlier of two substantive cycles or the two-calendar-day maximum governs. The first cycle is this frozen implementation and one real-data screen; at most one materially justified repair/validation cycle remains. If the implementation, source acceptance or valid empirical conclusion is unresolved at its applicable deadline, close INCONCLUSIVE/INFEASIBLE. No automatic extension, silent clock reset, relaxed acceptance gate or same-ID retuning.

## Research question and falsifiable claim

Does a strictly lagged five-calendar-day increase in the US news-based Economic Policy Uncertainty Index add chronological out-of-sample information about next-five-session Bitcoin downside semivariance beyond Bitcoin's own recent downside semivariance and total realized variance?

The mechanism is **news-based policy uncertainty and delayed risk-bearing**. A rise in newspaper-based uncertainty about economic policy may increase uncertainty about regulation, fiscal decisions, trade, monetary policy and the distribution of future cash flows. Bitcoin may respond through changes in risk appetite and leverage even when the uncertainty originates outside crypto. The frozen test asks whether the index adds predictive information; it does not identify a causal policy shock or assume that every EPU increase is bearish.

## Novelty and literature boundary

This is materially distinct from the repository's prior Bitcoin predictors based on credit spreads, Federal Reserve balance-sheet quantity, composite financial stress, CFTC futures positioning and option-implied volatility. The new information source is a daily newspaper-based policy-uncertainty index, not a market price, trader-position report, monetary aggregate or financial-conditions composite.

- FRED identifies USEPUINDXD as the daily, seven-day, not-seasonally-adjusted Economic Policy Uncertainty Index for the United States. Its notes identify Baker, Bloom and Davis and state that the daily index is based on US newspapers: https://fred.stlouisfed.org/series/USEPUINDXD.
- Baker, Bloom and Davis, “Measuring Economic Policy Uncertainty” (2016), Quarterly Journal of Economics, provides the underlying EPU research framework: https://www.policyuncertainty.com/media/BakerBloomDavis.pdf.
- No first-in-literature claim is made. The bounded contribution is a lagged daily EPU-to-BTC downside-semivariance forecast screen with a frozen chronological test.

## Data feasibility, source and coverage gates

### US Economic Policy Uncertainty Index — USEPUINDXD

- Official series: https://fred.stlouisfed.org/series/USEPUINDXD.
- Public table: https://fred.stlouisfed.org/data/USEPUINDXD.
- Public CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=USEPUINDXD&cosd=2017-08-12&coed=2026-11-24.
- Source: Baker, Scott R.; Bloom, Nick; Davis, Steven J.
- Frequency: daily, 7-day; units: index; not seasonally adjusted.
- FRED's current table reported observations through 2026-11-24 and a last update on 2026-11-25. Freeze the sample end at 2026-11-24; do not extend the sample after seeing results.
- Require at least 3,000 positive finite observations, first date no later than 2017-08-14, last date within two calendar days of the frozen sample end, no future dates and no gap greater than two calendar days. Missing values are skipped and never filled or interpolated.
- Use the current FRED vintage. Preserve the raw response SHA-256 and exact retrieval URL. Historical ALFRED vintages are not reconstructed.

### Bitcoin Spot — BTCUSDT

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC.
- Source: official Binance Vision monthly/daily Spot kline archives and per-archive SHA-256 sidecars: https://github.com/binance/binance-public-data.
- Active-market check: public exchangeInfo endpoint, https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT.
- Frozen sample: 2017-08-17 through 2026-11-24 inclusive.
- Require at least 3,000 completed daily candles, exact frozen first/last dates, positive finite closes and every UTC calendar date present. Exclude the incomplete current candle.
- Verify every archive against its official checksum sidecar; reject duplicate dates, incomplete daily candles, mixed timestamp units within an archive and any missing UTC date.
- Do not commit raw market observations.

## Frozen feature, signal and target

- EPU feature: ln(USEPUINDXD[d] / USEPUINDXD[d-5]), where both are exact daily observations five calendar days apart. Positive values indicate a rise in the index over the preceding five calendar days. No interpolation, smoothing, percentile selection or threshold optimization.
- Availability rule: use the EPU observation dated d only at the close of the Binance BTCUSDT UTC daily candle dated d+2. The two-calendar-day buffer is intended to allow the daily newspaper index to become available; exact historical intraday publication timestamps are not reconstructed.
- Event schedule: one signal every six calendar days, anchored at 2017-09-04 EPU date, so five-session target windows do not overlap.
- Baseline predictors: log1p of prior-five-observation BTC downside semivariance; log1p of prior-twenty-observation downside semivariance; log1p of prior-twenty-observation total realized variance.
- Augmented model: baseline predictors plus the EPU five-day log change.
- Target: log1p of next-five-UTC-session BTC downside semivariance, measured as the mean squared negative daily log return multiplied by 10,000 (percentage-points squared; not annualized).
- All feature windows end at the signal close. The target begins with the next UTC daily return. Any incomplete return window or missing EPU feature endpoint causes that event to be skipped, never filled.

## Walk-forward model and evaluation

- Baseline and augmented models use the repository's standardized, ridge-stabilized OLS predictor; all scaling and fitting use training observations only.
- Rolling training window: 104 prior events whose signals and target end dates are strictly earlier than the current signal.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum acceptance sample: at least 30 forecasts in both validation and test.
- Primary metric: RMSE in log1p downside-semivariance space; MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four events, fixed seed 20261127.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired test squared-loss 95% upper confidence bound is below zero.
- INCONCLUSIVE: every other outcome, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale sources or incomplete data.
- A promising result remains a forecast-only BACKTESTED screen. It is not independent validation or a trading strategy.

## Limitations and safety

- USEPUINDXD is a newspaper-based composite, not a direct policy shock, policy-rate surprise, investor-positioning measure or market-implied risk price. It can respond to broad political and economic news.
- The current FRED vintage is used. Historical point-in-time ALFRED revisions and historical intraday release timestamps are not reconstructed; the two-day lag does not remove all vintage/revision look-ahead risk.
- The daily 7-day EPU series is aligned to UTC BTC daily closes by calendar date. No missing observations are filled.
- BTCUSDT is one venue's Spot series, not a consolidated executable price or derivatives P&L series.
- This is forecast research only. No causal inference, transaction-cost-adjusted strategy, profitability, live order, capital deployment or strategy-promotion claim is authorized.
- Do not assign CAGR, Sharpe, Sortino, Calmar, turnover or drawdown to this forecast-only result.

## Implementation acceptance

- Deterministic parser tests cover FRED schema, missing values, duplicates and invalid non-positive observations.
- Event tests prove the two-day availability lag, exact five-calendar-day EPU change, next-five-session target, six-day event spacing and non-overlapping target windows.
- Walk-forward tests prove the 104-event fully matured training requirement.
- Decision-rule and idempotent registry/preregistration update tests pass.
- The complete workflow compiles, runs the model-specific suite and repository workflow-admission regression suite before retrieving empirical sources.
- The triggering commit SHA, FRED response hash, Binance archive checksums, report and manifest are retained.
