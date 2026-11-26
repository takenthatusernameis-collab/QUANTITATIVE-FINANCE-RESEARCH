# Preregistration — STLFSI4 tightening and Bitcoin downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01
- **Registered:** 2026-11-25T23:54:29Z, before this experiment's empirical result inspection.
- **Status:** ACTIVE — same-instrument Binance Vision archive replacement implemented; hosted verification pending. Prior REST attempt 45727248228 failed before empirical evaluation.
- **Difficulty:** MEDIUM.
- **Implementation timebox:** through 2026-11-29T23:54:29Z.
- **Research conclusion deadline:** 2026-12-02T23:54:29Z.
- **Maximum substantive cycles:** one preregistered screen. Any alternate feature, horizon, model family or robustness experiment requires a new hypothesis ID and preregistration.
- **Expiry:** if accepted source freshness, deterministic tests or the frozen screen is incomplete by the conclusion deadline, close INCONCLUSIVE/INFEASIBLE. Do not relax gates, retune or extend this ID.

## Distinct mechanism and falsifiable claim

The St. Louis Fed Financial Stress Index (STLFSI4) combines 18 weekly financial-market variables. A rise in broad financial stress may transmit disproportionately into Bitcoin's downside tail risk, rather than simply increasing symmetric volatility.

**Claim:** a strictly lagged four-week increase in STLFSI4 adds out-of-sample information about next-five-session BTC downside semivariance beyond BTC's own recent downside semivariance and total realized variance.

The single frozen predictor is:

    stlfsi4_4w_change = STLFSI4_t - STLFSI4_(t-4 weekly observations)

A positive value means financial stress increased over the four-week interval. No threshold, sign reversal, alternate lookback, feature substitution or asset substitution is permitted.

This is a forecasting screen, not a causal claim, trading strategy, executable P&L or claim of first discovery.

## Literature and novelty boundary

- Colombage, Jayawardhana and Oatley (2025), “Global Financial Stress and Its Transmission to Cryptocurrency Markets: A Cointegration and Causality Approach,” Journal of Risk and Financial Management 18(10), 532. It finds stress/volatility indices transmit shocks to cryptocurrency markets, but uses OFR-FSI and broad crypto measures rather than this STLFSI4/BTC downside-semivariance forecast: https://doi.org/10.3390/jrfm18100532.
- Yavuz (2026), “Financial stress and cross-asset market spillovers: evidence from a time-varying connectedness framework,” Hitit Journal of Social Sciences 19(2). It includes STLFSI and Bitcoin in a connectedness analysis, finding STLFSI a net risk transmitter and Bitcoin a net transmitter on average; it does not test this one-sided five-session forecast: https://dergipark.org.tr/en/pub/hititsbd/article/1900941.
- Lin et al. (2026), “Residual Structural State and Short-Horizon Downside-Risk Forecasting in Cryptocurrency Markets,” Mathematics 14(9), 1509. It studies Binance-based downside-semivariance forecasting with a structural-state predictor; it motivates the target and forecast evaluation, not the STLFSI4 predictor: https://doi.org/10.3390/math14091509.

The bounded contribution is an incremental, strict-lag, single-Bitcoin forecast test. Existing literature already establishes financial-stress/crypto spillovers and downside-risk forecasting; this experiment must not claim first discovery.

## Data feasibility and sources

### FRED STLFSI4

- Series: https://fred.stlouisfed.org/series/STLFSI4
- Frequency: weekly, ending Friday; observations are subject to revision.
- FRED's release calendar lists the series at 9:00 a.m. US Central Time on Wednesdays, with holiday shifts (for example, the 2026-11-12 release moved to Thursday): https://fred.stlouisfed.org/releases/calendar?rid=187.
- At preregistration, FRED showed observation 2026-11-20, updated 2026-11-25 11:37 a.m. CST.
- Fetch current public CSV from https://fred.stlouisfed.org/graph/fredgraph.csv?id=STLFSI4&cosd=2017-08-17.
- Availability convention: use a week-ending Friday observation only at the close of the UTC daily candle dated Friday + 7 calendar days. This is deliberately later than the normal Wednesday/holiday-shifted Thursday release. The target begins on the following UTC daily candle.
- Require at least 400 observations, weekly-Friday dates, no source gap above 14 days, latest observation no more than 10 calendar days old, no future dates, and valid finite values.

### Binance BTCUSDT spot

- Public market-data-only endpoint: https://data-api.binance.vision/api/v3/klines; official documentation says this market-data endpoint requires no API key: https://developers.binance.com/en/docs/products/spot/faqs/market_data_only.
- Official REST documentation: https://developers.binance.com/en/docs/products/spot/rest-api.
- Symbol: BTCUSDT, spot, interval 1d, timeZone=0 (UTC), paginated with limit=1000.
- Feasibility probe via the connected Binance market-data interface verified BTCUSDT status TRADING and 3,387 completed daily candles from 2017-08-17 through 2026-11-24 with no missing UTC dates. The 2026-11-25 candle was still incomplete and is excluded.
- Require at least 3,000 completed daily candles, history beginning no later than 2017-08-31, latest completed candle no more than two calendar days old, strictly continuous UTC dates, positive closes and no future dates.
- Record exact endpoint, pagination, row counts, date coverage and SHA-256 page hashes. Do not commit raw market data.

### Execution source replacement addendum — 2026-11-26

The first hosted attempt (run 45727248228) did not reach empirical evaluation: the Binance market-data REST host returned daily rows that failed the strict UTC-day parser, while the primary API host returned HTTP 451. This is an execution/source-route failure, not evidence against the hypothesis. The REST kline retrieval route has therefore been replaced in the same session with Binance's official Spot monthly/daily 1d archive distribution for the **same BTCUSDT spot instrument and UTC daily interval**. The active-symbol check remains on the public market-data exchangeInfo endpoint.

The replacement requires a .CHECKSUM sidecar for every ZIP, SHA-256 equality, exactly one CSV per archive, positive finite closes, complete UTC-day open/close bounds, duplicate-free dates, and a continuous daily series. It supports the documented Spot timestamp-unit transition from milliseconds to microseconds beginning 2025-01-01. Completed calendar months use monthly archives only after the documented first-Monday publication date; current or not-yet-published months use daily archives. The current day and immediately preceding day are not requested, leaving a bounded publication buffer. This changes only the transport/archive route; it does not change the instrument, feature, release lag, target, horizon, model, date splits, training window, bootstrap or decision rule.

Official archive format and checksum documentation: https://github.com/binance/binance-public-data. The first valid backtest remains pending until the replacement route passes hosted source acceptance and the frozen walk-forward run.

## Data-revision limitation

FRED explicitly notes STLFSI4 observations are subject to revision. The screen uses the current FRED vintage, not historical ALFRED vintages. The conservative publication lag prevents using a weekly observation before its scheduled release, but does not eliminate look-ahead from subsequent revisions. Even a positive result remains BACKTESTED only, not INDEPENDENTLY_VALIDATED, until point-in-time vintages or independent reconstruction are available.

## Frozen event, feature and target construction

- Use each weekly-ending-Friday STLFSI4 observation after a fixed seven-calendar-day availability lag.
- Signal is formed at the close of the corresponding Binance UTC daily candle. Use only that close and prior data.
- Predictor: four-week STLFSI4 change, using five consecutive weekly observations; skip irregular/missing four-week windows.
- BTC log return: r_t = log(close_t / close_(t-1)).
- Downside semivariance over a window of n daily returns: 10000 * mean(min(r_t, 0)^2), in percentage-points squared. No annualization.
- Target: next five UTC daily close-to-close returns' downside semivariance, transformed as log1p(target).
- Baseline predictors: log1p of prior-five-session downside semivariance; log1p of prior-twenty-session downside semivariance; log1p of prior-twenty-session total realized variance.
- Augmented predictors: baseline plus the single stlfsi4_4w_change feature.
- No forward-fill, imputation, overlapping targets or incomplete future windows. Every training target must end strictly before the current signal date.

## Model and chronological evaluation

- Baseline and augmented models: rolling ordinary least squares, using the repository's deterministic training-only feature standardization and ridge-stabilized normal equations.
- Rolling training window: 104 prior weekly events whose signal date and target end are strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p downside-semivariance space.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four weekly events, using the repository's fixed bootstrap seed.

## Frozen decision rule

A promising forecast screen requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero. All other outcomes are INCONCLUSIVE. A promising result is BACKTESTED only; the current-vintage revision limitation bars independent validation or strategy promotion.

Do not change the predictor, lag, target, horizon, date splits, training window, bootstrap settings or decision thresholds after seeing results.

## Safety and interpretation

Forecasting only. No live orders, capital deployment, trading P&L, causal claim or deployment authorization. Do not redistribute raw FRED or Binance observations. Preserve source hashes, reports and aggregate metrics.

## Empirical disposition

- **Prior attempt 1:** INCONCLUSIVE — REST source acceptance failed before a valid backtest; no empirical result exists.
- **Replacement:** official Binance Vision Spot archive route implemented for the same BTCUSDT 1d UTC instrument; checksums and continuous coverage are enforced.
- **Current attempt:** pending hosted CI and source acceptance. No result or daily KPI credit is claimed until the new run completes.
