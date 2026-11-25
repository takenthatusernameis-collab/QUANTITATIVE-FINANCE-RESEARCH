# Preregistration — lagged yen-appreciation shock and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-JPY-CARRY-UNWIND-SP500-RV-01
- **Registered:** 2026-11-25T18:26:40Z, before empirical result inspection.
- **Status:** IDEA / FEASIBILITY CHECK IN PROGRESS.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** three public daily series, a one-sided five-observation FX shock, strict prior-date alignment, an existing walk-forward OLS harness and block-bootstrap inference. No credentials, paid data, new venue or custom infrastructure.
- **Implementation timebox:** start 2026-11-25T18:26:40Z; deadline 2026-11-29T18:26:40Z.
- **Research conclusion deadline:** 2026-12-01T18:26:40Z.
- **Maximum substantive implementation/research cycles:** 4.
- **Expiry rule:** if accepted source coverage, deterministic implementation or the frozen empirical decision is incomplete by the applicable deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. No automatic extension, reset or tuning under this hypothesis ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** the Japanese yen is a funding and safe-haven currency. A rapid yen appreciation can force investors to reduce yen-funded carry positions and liquidate risk assets. This portfolio-balance/deleveraging channel is distinct from Treasury-curve volatility, VIX/VXV term structure, Treasury auction demand, CFTC E-mini positioning, and the previously tested broad-dollar and real-yield predictors.

**Claim:** a strictly lagged five-observation yen-appreciation shock adds out-of-sample information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and the VIX level.

The USD/JPY quote in FRED series DEXJPUS is Japanese yen per one U.S. dollar. A fall in DEXJPUS therefore represents yen appreciation. The frozen one-sided shock is:

`yen_appreciation_5 = max(0, -100 × log(DEXJPUS_latest / DEXJPUS_five_observations_earlier))`

The model adds only `log1p(yen_appreciation_5)` to the baseline. No threshold, event selection or parameter tuning is permitted.

This is a forecasting screen, not a causal claim, direct observation of carry positioning, trading strategy or claim of first discovery.

## Literature rationale and novelty boundary

- Liu, Ming-Hua, Dimitris Margaritis and Alireza Tourani-Rad (2012), “Risk appetite, carry trade and exchange rates,” *Global Finance Journal* 23(1), 48–63, DOI: https://doi.org/10.1016/j.gfj.2012.01.004. The study examines Yen exchange rates, equity indices and VIX and reports asymmetric adjustment in carry currencies during changes in risk appetite. It motivates the cross-market channel but does not validate this specific one-sided five-observation shock or S&P 500 volatility target.
- Guyot, Opale, Heather A. Montgomery and Peiqing Yang (2026), “Risk Premiums, Market Volatility, and Exchange Rate Dynamics: Evidence from the Yen Carry Trade,” *Risks* 14(3), 46, DOI: https://doi.org/10.3390/risks14030046. The paper studies daily JPY/USD risk-transmission dynamics and discusses Yen appreciation under heightened equity-market risk. It is adjacent evidence, not validation of the present forecast.
- FRED identifies DEXJPUS as the daily Japanese Yen to U.S. Dollar spot exchange rate, sourced from the Board of Governors of the Federal Reserve System, quoted in JPY per USD and based on noon buying rates in New York City: https://fred.stlouisfed.org/series/DEXJPUS.

The bounded contribution is a strict-lag, non-overlapping, rolling out-of-sample test using public daily data. It is a replication/screen of a specific carry-unwind proxy, not a first-discovery claim.

## Data sources and acceptance

1. **S&P 500 cash price index:** FRED SP500, daily close; https://fred.stlouisfed.org/series/SP500.
2. **CBOE 30-day implied volatility:** FRED VIXCLS, daily close; https://fred.stlouisfed.org/series/VIXCLS.
3. **Japanese yen per U.S. dollar:** FRED DEXJPUS, daily noon buying rate; source Board of Governors of the Federal Reserve System; https://fred.stlouisfed.org/series/DEXJPUS.

Fetch CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25. Require at least 1,500 valid observations per series, unique dates, finite positive values, history beginning no later than 2017-03-01, and latest observations within four calendar days of one another. SP500, VIXCLS and DEXJPUS must be strictly positive. Require a common recent end no earlier than 2026-11-17. Do not forward-fill any series. Store source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes. Do not commit raw source data.

If any source fails acceptance, do not backtest on an incomplete or stale sample. Record the exact failure and close INCONCLUSIVE/INFEASIBLE rather than relaxing the thresholds after seeing the response.

## Timing, feature and target construction

- Use exact S&P 500 trading dates for signal origins.
- The signal is formed after the signal-date S&P 500 and VIX closes. The target starts on the next S&P 500 session.
- Baseline predictors:
  - log(1 + pre-event S&P 500 RV5 in percent);
  - log(1 + pre-event S&P 500 RV20 in percent);
  - log(VIXCLS) observed on the signal date.
- The FX feature uses only DEXJPUS observations dated **strictly before** the S&P 500 signal date. Same-date FX observations are excluded to avoid fixing/publication-time ambiguity.
- Let d be the latest DEXJPUS observation strictly before signal date t. Require t−d no greater than four calendar days.
- Require six valid DEXJPUS observations ending at d to construct five changes. Require no adjacent observation gap above four calendar days and total window span no greater than 14 calendar days. Do not forward-fill, interpolate or bridge gaps.
- Compute the one-sided yen-appreciation shock as max(0, -100 × log(FX_latest / FX_5_observations_earlier)), where FX is JPY per USD. A falling USD/JPY quote is yen appreciation. A zero value means the five-observation window did not show yen appreciation.
- The augmented model adds only log(1 + yen_appreciation_5) to the baseline features.
- Compute S&P 500 realized volatility as the root-sum-square of daily log returns, multiplied by 100, over the preceding five and twenty sessions for baseline features and the next five sessions for the target.
- Do not bridge an S&P 500 price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Sample event origins every six S&P 500 sessions. The next-five-session target windows must not overlap, and each training target must end strictly before the current signal date.

## Model and chronological evaluation

- Baseline OLS features: log(1 + pre-event RV5), log(1 + pre-event RV20), log(VIXCLS).
- Augmented OLS features: baseline plus log(1 + five-observation yen-appreciation shock).
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and OOS R-squared versus the period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four events, fixed seed 20261129.

## Frozen decision rule

A promising incremental forecast requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero, indicating that the augmented model is worse. All other outcomes are INCONCLUSIVE. Do not change the predictor, window, horizon, event spacing, date split, training window, bootstrap settings or decision thresholds after seeing results.

A promising forecast is not independent validation, a causal finding, an executable strategy, a trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- DEXJPUS is a daily noon buying reference rate, not an executable FX price or intraday carry-position series.
- A one-sided yen-appreciation shock is only a proxy for potential carry unwind; it does not observe investor leverage, positioning, funding costs or forced liquidation.
- SP500 is a cash price index, not an executable futures series or total-return index.
- FRED current-vintage observations are used; historical release vintages are not reconstructed.
- The strict prior-date rule deliberately adds a lag to avoid same-day FX fixing/publication ambiguity.
- Forecasting only: no causal claim, transaction-cost model, tradable strategy, live-deployment conclusion or raw-data redistribution.
