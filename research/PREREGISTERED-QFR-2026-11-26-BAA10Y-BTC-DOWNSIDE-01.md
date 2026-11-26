# Preregistration — BAA10Y corporate-credit spread widening and Bitcoin downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01
- **Registered:** 2026-11-26T10:05:47Z, before implementation and empirical-result inspection.
- **Status:** FEASIBILITY_CHECKED
- **Expected difficulty:** MEDIUM.
- **Difficulty rationale:** public daily spread and BTC Spot sources are discoverable; existing repository code provides a checksummed BTC archive path and reusable walk-forward/bootstrap primitives. Moderate work remains for strict publication-time alignment, a new feature/event constructor, regression tests, workflow integration and evidence persistence.
- **Timebox start:** 2026-11-26T10:05:47Z.
- **Maximum substantive cycles:** 4 total.
- **Hard implementation deadline:** 2026-11-29T10:05:47Z.
- **Hard final research-conclusion deadline:** 2026-12-01T10:05:47Z.
- **Expiry rule:** if source acceptance or implementation is incomplete at the implementation deadline, close as INCONCLUSIVE/INFEASIBLE with the exact blocker. If valid empirical evidence is not complete by the final deadline, close as INCONCLUSIVE/INFEASIBLE. Expiry is never a performance NO-GO. No automatic extension, clock reset, gate weakening or repeated identical route. A materially changed feature, lag, target, market or source requires a new hypothesis ID and preregistration.

## Research question and falsifiable claim

Does a strictly lagged five-business-observation widening in the Moody's Baa corporate-bond yield minus 10-year U.S. Treasury yield add chronological out-of-sample information about next-five-session Bitcoin downside semivariance beyond Bitcoin's own recent downside semivariance and total realized variance?

The proposed transmission mechanism is corporate-credit repricing: widening Baa-versus-Treasury yields may reflect deteriorating credit-risk compensation, liquidity conditions and reduced risk-bearing capacity. If this credit-market repricing contains incremental cross-asset information, it may precede higher BTC left-tail variance. The test is predictive, not causal.

## Novelty and literature boundary

This is not a claim that credit spreads and cryptocurrency returns have never been studied. Lee and Ryu (2026), *State-Dependent Relationship Between Cryptocurrency Returns and Credit Spreads*, report asymmetric and state-dependent relationships for crypto returns, but their reported BTC return relationship is statistically insignificant across quantiles after controlling for the S&P 500. Their study uses option-adjusted credit spreads and daily return regressions. This experiment asks a different question: whether a strictly lagged BAA10Y yield-spread change forecasts next-five-session BTC downside semivariance after controlling for BTC's own recent downside semivariance and realized variance. It uses a different public yield-spread proxy and a frozen weekly walk-forward design. No first-in-literature claim is made.

- Lee, G. and Ryu, D. (2026), *European Financial Management*, 32(1), 261–287. DOI: https://doi.org/10.1111/eufm.70010.
- Almeida, C., Grith, M., Miftachov, R. and Wang, Z. (2024; revised 2025), *Risk Premia in the Bitcoin Market*. https://arxiv.org/abs/2410.15195. This work studies Bitcoin option-implied and realized-return premia, not the BAA10Y predictor specified here.

## Data feasibility and provenance

### BAA10Y corporate-yield spread

- FRED series: https://fred.stlouisfed.org/series/BAA10Y
- FRED table: https://fred.stlouisfed.org/data/BAA10Y
- Source: Federal Reserve Bank of St. Louis, Interest Rate Spreads release.
- Frequency: daily, business days; units: percent, not seasonally adjusted.
- Series definition: Moody's Seasoned Baa Corporate Bond yield minus the 10-Year Treasury Constant Maturity yield.
- Public CSV route: https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAA10Y&cosd=1986-01-02.
- The FRED table page showed published history beginning 1986-01-02 and daily observations through 2026-11-20 at feasibility screening. The exact current response, row count and end date must be revalidated in the admitted run.
- FRED series notes include a Moody's proprietary-information notice. Do not commit or redistribute raw BAA10Y observations. Persist only the source-response SHA-256, coverage metadata, aggregate forecast metrics and event counts. If the terms do not permit this limited analytical use, fail closed and close INCONCLUSIVE/INFEASIBLE.
- Use the current FRED vintage. Historical ALFRED point-in-time vintages are not reconstructed.

### Availability and publication embargo

- Signal origins are Wednesday UTC BTC daily-candle closes, exactly seven calendar days apart.
- For a signal dated t, the latest eligible BAA10Y observation must be dated on or before t minus five calendar days.
- The selected observation must be no more than four calendar days older than that cutoff. If it is older, skip the event; never forward-fill beyond the bound.
- The five-calendar-day embargo is conservative relative to the observed next-business-day FRED update pattern, but exact historical publication timestamps and revisions are not reconstructed. The manifest must record the cutoff date, selected observation date, and age for each accepted event in aggregate/event metadata without storing raw BAA10Y values.

### Bitcoin Spot

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC.
- Source: official Binance Vision monthly/daily Spot kline archives with per-archive .CHECKSUM sidecars: https://github.com/binance/binance-public-data.
- Active-market check: public market-data exchangeInfo endpoint, https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT.
- Prior repository runs verified BTCUSDT daily history from 2017-08-17 through 2026-11-24; this experiment must revalidate all archives and coverage.
- Require at least 3,000 completed daily candles, history beginning no later than 2017-08-19, latest completed candle no more than two calendar days old, no missing UTC date, positive finite closes, and no future date.
- Verify every archive SHA-256 against its official sidecar; reject duplicate dates, missing dates, incomplete days, mixed timestamp units within an archive and unverified checksums. Exclude the incomplete current candle.
- Do not commit raw BTC observations.

## Frozen feature, signal and target

- Predictor: five-business-observation change in BAA10Y, defined as 100 times the latest eligible BAA10Y value minus its value five prior valid business observations earlier. Since BAA10Y is in percent, the resulting feature is in basis points. Positive values indicate widening.
- The selected observation date and its five-observation lookback date must both be no later than the five-calendar-day cutoff. Do not interpolate, forward-fill, or use an observation published after the signal.
- BTC log return: ln(close[t] / close[t-1]).
- Downside semivariance over n daily returns: 10,000 times the mean of min(return, 0) squared, in percentage-points squared, not annualized.
- Baseline features: log1p of prior-five-session BTC downside semivariance; log1p of prior-twenty-session downside semivariance; log1p of prior-twenty-session total realized variance.
- Augmented model: baseline plus only the five-observation BAA10Y change in basis points.
- Target: log1p of next-five-UTC-session BTC downside semivariance.
- Signal origins are every Wednesday. Five-session target windows must be fully matured before the next Wednesday signal. No overlapping targets or incomplete future windows are accepted.

## Walk-forward model and evaluation

- Baseline and augmented models: ridge-stabilized ordinary least squares; feature standardization is estimated on training data only.
- Rolling training window: 104 prior weekly events. Every training event's signal and target end must both be strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum: at least 30 forecasts in each period; otherwise INCONCLUSIVE.
- Primary metric: RMSE in log1p downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four consecutive weekly events, fixed seed 20261126.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- INCONCLUSIVE: all other outcomes, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale sources, source-use restrictions or incomplete data.
- A promising forecast remains BACKTESTED only. Current-vintage revisions, source-use restrictions and lack of independent reconstruction prevent independent validation or strategy promotion.
- No result-dependent retuning, alternate horizons, extra predictors, threshold search or repeat run under this hypothesis ID is authorized.

## Limitations and safety

- BAA10Y is a yield differential, not a pure option-adjusted default-risk spread. It includes effects from Treasury yields, duration, liquidity, rating composition and credit-risk compensation.
- The FRED series carries a Moody's proprietary-information notice. Raw values must not be stored in repository artifacts or redistributed. Only aggregate outputs and cryptographic hashes are retained.
- Current FRED vintage can contain revisions that were not available at historical forecast origins.
- The five-day embargo is conservative but does not reconstruct every historical release timestamp.
- BTCUSDT is one venue's Spot series; checksummed archives do not establish consolidated-market representativeness.
- Forecasting only. No live orders, capital deployment, trading P&L, causal claim or deployment authorization.
- Do not assign CAGR, Sharpe, Sortino, Calmar or drawdown to a forecast-only result.

## Empirical disposition

Pending the first admitted real-data run. A failed source or implementation attempt is INCONCLUSIVE/INFEASIBLE, not a performance NO-GO.
