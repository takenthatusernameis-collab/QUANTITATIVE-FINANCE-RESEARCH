# Preregistration — Federal Reserve balance-sheet contraction and Bitcoin downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-FED-BALANCE-SHEET-BTC-DOWNSIDE-01
- **Registered:** 2026-11-26T06:08:39Z, before this experiment's empirical result inspection.
- **Status:** INCONCLUSIVE
- **Difficulty:** MEDIUM.
- **Implementation timebox:** through 2026-11-29T23:59:59Z.
- **Maximum substantive cycles:** one frozen real-data screen. Any alternate feature, lag, horizon, asset, model or split requires a new hypothesis ID and preregistration.
- **Expiry:** if source acceptance or the frozen screen is incomplete by the timebox, close INCONCLUSIVE/INFEASIBLE. Do not relax gates or repeat the same screen under this ID.

## Research question and distinct mechanism

Does a strictly lagged four-week contraction in Federal Reserve total assets add chronological out-of-sample information about next-five-session Bitcoin downside semivariance beyond Bitcoin's own recent downside semivariance and total realized variance?

The economic mechanism is central-bank balance-sheet quantity and liquidity supply: sustained contraction in the Fed's aggregate assets may tighten dollar funding and risk-bearing capacity, potentially increasing the left-tail risk of a high-beta, continuously traded crypto asset. This is a predictive hypothesis, not a causal claim.

The predictor is not labelled pure quantitative tightening or net liquidity. WALCL is total Federal Reserve assets; it includes securities and other assets, and its changes can reflect valuation, facilities and balance-sheet composition as well as policy. The study tests whether this aggregate public balance-sheet measure contains incremental information, not whether QT causes BTC losses.

This is materially distinct from the repository's STLFSI4 financial-stress screen: STLFSI4 is a composite of 18 financial-market variables, while WALCL is a balance-sheet stock measure published in the Federal Reserve's H.4.1 release. The target and forecast framework are retained for comparability, but the information source and proposed transmission mechanism differ.

## Literature and novelty boundary

- Kyriazis, Ofeidis, Palaiokrassas and Tassiulas (2023), “Monetary Policy, Digital Assets, and DeFi Activity,” studies unexpected U.S. monetary-policy changes and digital-asset returns, and reports volatility effects around FOMC statement releases. It does not test weekly Fed total-assets changes as an incremental predictor of BTC downside semivariance: https://arxiv.org/abs/2302.10252.
- Buthelezi (2024), “Cryptocurrency Responses to U.S. Monetary Policy Shocks: A Data-Driven Exploration of Price and Volatility Patterns,” studies monthly policy-rate changes and cryptocurrency volatility, not the weekly balance-sheet-stock feature specified here: https://doi.org/10.1177/05694345241269036.

The bounded contribution is a strict-lag, single-asset, weekly balance-sheet-stock forecast screen with a frozen chronological test. It does not claim first discovery of monetary-policy/crypto transmission or of balance-sheet effects.

## Data feasibility and provenance

### Federal Reserve total assets — WALCL

- Series: https://fred.stlouisfed.org/series/WALCL
- Public table data: https://fred.stlouisfed.org/data/WALCL
- Source: Board of Governors of the Federal Reserve System, H.4.1 Factors Affecting Reserve Balances, Table 5.
- Frequency: weekly, as of Wednesday.
- Units: millions of U.S. dollars, not seasonally adjusted.
- Public CSV route: https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL&cosd=2017-08-16.
- The H.4.1 release is normally published each Thursday around 4:30 p.m. Eastern; publication may shift to the next business day for a federal holiday: https://www.federalreserve.gov/releases/h41/.
- Availability rule: use a Wednesday observation only at the close of the UTC BTC daily candle dated seven calendar days later. This deliberately exceeds the normal release lag and leaves a buffer for ordinary holiday shifts.
- Require at least 400 valid weekly observations, Wednesday observation dates, no gap above 14 calendar days, no future date, latest observation no more than 10 calendar days old, and strictly positive finite values.
- Use the current FRED vintage and preserve the raw-response SHA-256 only. Historical ALFRED point-in-time vintages are not reconstructed.

### Bitcoin spot — BTCUSDT

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC.
- Source route: official Binance Vision monthly/daily Spot kline archives with per-archive .CHECKSUM sidecars: https://github.com/binance/binance-public-data.
- Active market check: public market-data exchangeInfo endpoint, https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT.
- The repository's prior source pilot verified checksum-validated BTCUSDT 1d UTC archives from 2017-08-17 through 2026-11-24. This experiment revalidates the complete current sample rather than assuming the earlier result is permanent.
- Require at least 3,000 completed daily candles, history beginning no later than 2017-08-19, latest completed candle no more than two calendar days old, no missing UTC date, positive finite closes, and no future date.
- Verify each archive SHA-256 against its official sidecar; reject duplicates, incomplete days, mixed timestamp units within an archive and missing calendar dates. Exclude the incomplete current candle.
- Do not commit raw source observations.

## Frozen feature, signal and target

- Signal: close of the Binance BTCUSDT UTC daily candle dated seven calendar days after a WALCL Wednesday observation.
- Predictor: four-week total-assets contraction proxy, defined as negative 100 times ln(WALCL[t] / WALCL[t-4]), where t and t-4 are five consecutive weekly Wednesday observations. Positive values mean total assets contracted over four weeks; negative values mean expansion.
- Skip any five-observation window that is not exactly weekly. Do not forward-fill, interpolate or fabricate missing balance-sheet values.
- BTC log return: ln(close[t] / close[t-1]).
- Downside semivariance over n daily returns: 10000 times the mean of min(return, 0) squared, in percentage-points squared, not annualized.
- Baseline features: log1p of prior-five-session BTC downside semivariance; log1p of prior-twenty-session downside semivariance; log1p of prior-twenty-session total realized variance.
- Augmented model: baseline plus only the four-week WALCL contraction proxy.
- Target: log1p of next-five-UTC-session BTC downside semivariance.
- Weekly signal origins are seven days apart; five-session target windows must be fully matured before the next signal. No overlapping targets or incomplete future windows are accepted.

## Walk-forward model and evaluation

- Baseline and augmented models: ridge-stabilized ordinary least squares, with feature standardization estimated on training data only.
- Rolling training window: 104 prior weekly events. Every training event's signal and target end must both be strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum: at least 30 forecasts in each period; otherwise INCONCLUSIVE.
- Primary metric: RMSE in log1p downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four consecutive weekly events, fixed seed 20261126.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- INCONCLUSIVE: all other outcomes, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale sources or incomplete data.
- A promising forecast remains BACKTESTED only. Current-vintage FRED revisions and lack of independent reconstruction prevent independent validation or strategy promotion.
- No result-dependent retuning, alternate horizons, extra predictors, threshold search or repeat run under this hypothesis ID is authorized.

## Limitations and safety

- WALCL is not bank reserves, monetary base or a comprehensive net-liquidity measure. Total-asset changes may reflect valuation, facilities, portfolio composition and non-policy factors.
- The fixed seven-day lag reduces release-timing risk but does not reconstruct historical publication timestamps or historical revisions.
- Current FRED vintages can contain revisions that were not available at historical forecast origins.
- BTCUSDT is a single venue's spot series; checksummed archives establish file integrity, not consolidated-market representativeness.
- Forecasting only. No live orders, capital deployment, trading P&L, causal claim or deployment authorization.
- Do not assign CAGR, Sharpe, Sortino, Calmar or drawdown to a forecast-only result.

## Empirical disposition

- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority
- **Completed real-data backtest:** yes
- **Data scope:** FRED WALCL weekly Wednesday 2017-08-16 to 2026-11-18 (484 observations); Binance BTCUSDT spot 1d UTC 2017-08-17 to 2026-11-24 (3387 candles); validation 2019-2021; test 2022 onward
- **Summary metrics:** {"test_n":255,"test_rmse_improvement_pct":-1.0613233709446463,"validation_n":120,"validation_rmse_improvement_pct":-4.125986307081812}
- **Paired test-loss bootstrap:** {"block_size_events":4,"bootstrap_fraction_positive":0.05,"ci95_high":0.002943798774582669,"ci95_low":-0.03833083561399792,"mean_baseline_minus_augmented_squared_loss":-0.01603322083288992,"observations":255,"reps":2000}
- **Report:** [reports/sessions/2026-11-26/2026-11-26T062647Z_session-fed-balance-sheet-btc-45767439835.md](../reports/sessions/2026-11-26/2026-11-26T062647Z_session-fed-balance-sheet-btc-45767439835.md)
- **Manifest:** [reports/generated/fed-balance-sheet-btc-downside-semivariance/45767439835-attempt-1/manifest.json](../reports/generated/fed-balance-sheet-btc-downside-semivariance/45767439835-attempt-1/manifest.json)
- Forecast screen only; no causal, trading or deployment claim.
