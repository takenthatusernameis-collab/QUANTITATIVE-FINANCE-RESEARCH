# Preregistration — Treasury yield-curve volatility and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-TREASURY-CURVE-VOL-SP500-RV-01
- **Registered:** 2026-11-25T17:15:00Z, before empirical result inspection.
- **Status:** INCONCLUSIVE — closed on 2026-11-25T17:16:24Z under the frozen decision rule; one successful real-data run completed after two deterministic-test repairs. No tuning or further cycles under this hypothesis ID.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** three public daily series, strict prior-date alignment for the Treasury spread, rolling feature construction, an existing walk-forward OLS harness and block-bootstrap inference. No credentials, paid data, new venue or custom infrastructure.
- **Implementation timebox:** start 2026-11-25T17:15:00Z; deadline 2026-11-29T17:15:00Z.
- **Research conclusion deadline:** 2026-12-01T17:15:00Z.
- **Maximum substantive implementation/research cycles:** 4.
- **Expiry rule:** if accepted source coverage, deterministic implementation or the frozen empirical decision is incomplete by the applicable deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. No automatic extension, reset or tuning under this hypothesis ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** uncertainty about the future path of monetary policy, term premia and expected cash flows can be reflected in fluctuations of the Treasury yield-curve slope. Volatility of the 10-year-minus-3-month spread is therefore a distinct rates-uncertainty input, rather than merely the level of the curve or the option-implied volatility curve.

**Claim:** the strictly lagged 20-observation realized variation of the U.S. 10-year-minus-3-month Treasury spread adds out-of-sample information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and the VIX level.

This is a forecasting screen, not a causal claim, trading strategy, volatility-premium trade or claim of first discovery. It is materially distinct from the repository's VIX/VXV option-implied term-structure test: the predictor here is the realized volatility of a Treasury yield-curve spread. It is also distinct from Treasury auction-demand studies, which test auction microstructure and yield responses.

## Literature rationale and novelty boundary

- Megaritis, Anastasios, Alexandros Kontonikas, Nikolaos Vlastakis and Athanasios Triantafyllou (2024), “The term structure of interest rates as predictor of stock market volatility,” *International Journal of Finance & Economics*, DOI: https://doi.org/10.1002/ijfe.3029. The paper reports forecasting power from volatility of the U.S. Treasury yield-curve slope for stock-market volatility at horizons from one to twelve months. It motivates this shorter-horizon retail-data screen but does not validate the present feature, horizon, sample or decision rule.
- Jubinski, Daniel (2011), “Equity volatility, bond yields, and yield spreads,” *Journal of Futures Markets*, DOI: https://doi.org/10.1002/fut.20521. This paper documents relationships between equity volatility and bond yields/spreads, providing adjacent economic motivation rather than direct validation of this forecast.
- FRED series notes identify T10Y3M as the daily spread between the 10-year and 3-month Treasury constant-maturity rates. The series is quoted in percentage points and can be zero or negative.

The bounded contribution is a strict-lag, non-overlapping, rolling out-of-sample test using publicly accessible daily data. It is a replication/screen at a shorter horizon, not a first-discovery claim.

## Data sources and acceptance

1. **S&P 500 cash price index:** FRED SP500, daily close; source S&P Dow Jones Indices LLC; https://fred.stlouisfed.org/series/SP500.
2. **CBOE 30-day implied volatility:** FRED VIXCLS, daily close; source CBOE; https://fred.stlouisfed.org/series/VIXCLS.
3. **10-year minus 3-month Treasury spread:** FRED T10Y3M, daily, percent/not seasonally adjusted; source Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/T10Y3M.

Fetch CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25. Require at least 1,500 valid observations per series, unique dates, finite values, history beginning no later than 2017-03-01, and latest observations within four calendar days of one another. SP500 and VIXCLS must be strictly positive. T10Y3M is signed and may be zero or negative; do not impose a positivity restriction. Require a common recent end no earlier than 2026-11-17. Do not forward-fill any series. Store source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes. Do not commit raw source data.

If any source fails acceptance, do not backtest on an incomplete or stale sample. Record the exact failure and close INCONCLUSIVE/INFEASIBLE rather than relaxing the thresholds after seeing the response.

## Timing, feature and target construction

- Use exact S&P 500 trading dates for signal origins.
- The signal is formed after the signal-date cash-index close and before the next S&P 500 session begins. The target starts on the next S&P 500 session.
- Baseline predictors:
  - log(1 + pre-event S&P 500 RV5 in percent);
  - log(1 + pre-event S&P 500 RV20 in percent);
  - log(VIXCLS) observed on the signal date.
- The Treasury feature uses only T10Y3M observations dated **strictly before** the S&P 500 signal date. Same-date T10Y3M values are excluded to avoid close-time/publication ambiguity.
- Let d be the latest T10Y3M observation strictly before signal date t. Require t−d no greater than four calendar days.
- Compute the 20-observation yield-curve realized variation as the root-sum-square of the 20 daily T10Y3M changes, converted from percentage points to basis points. Require 21 valid observations, no adjacent observation gap above four calendar days, and a total window span no greater than 35 calendar days. Do not forward-fill, interpolate or bridge gaps.
- Augmented model adds only log(1 + CurveRV20 in basis points) to the baseline features.
- Compute S&P 500 realized volatility as the root-sum-square of daily log returns, multiplied by 100, over the preceding five and twenty sessions for baseline features and the next five sessions for the target.
- Do not bridge an S&P 500 price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Sample event origins every six S&P 500 sessions. The next-five-session target windows must not overlap, and each training target must end strictly before the current signal date.
- Target: log(1 + next-five-session S&P 500 realized volatility in percent).

## Model and chronological evaluation

- Baseline OLS features: log(1 + pre-event RV5), log(1 + pre-event RV20), log(VIXCLS).
- Augmented OLS features: baseline plus log(1 + CurveRV20 in basis points).
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and OOS R-squared versus the period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four events, fixed seed 20261128.

## Frozen decision rule

A promising incremental forecast requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero, indicating that the augmented model is worse. All other outcomes are INCONCLUSIVE. Do not change the predictor, window, horizon, event spacing, date split, training window, bootstrap settings or decision thresholds after seeing results.

A promising forecast is not independent validation, a causal finding, an executable strategy, a trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- SP500 is a cash price index, not an executable futures series or total-return index.
- T10Y3M is a constructed spread of constant-maturity Treasury rates; it is not a directly traded yield-curve instrument.
- The T10Y3M observation date is not an intraday publication timestamp. The strict prior-date rule deliberately adds a lag to avoid same-day look-ahead.
- FRED observations can be revised; this experiment uses the retrieved current vintage and does not reconstruct historical release vintages.
- The feature is a simple 20-observation realized variation, not the more elaborate term-structure-volatility specifications in the cited paper.
- Forecasting only: no causal claim, transaction-cost model, tradable strategy, live-deployment conclusion or raw-data redistribution.


## Empirical disposition

- **Final status:** INCONCLUSIVE. The augmented model's RMSE improved slightly in both chronological periods, but the paired test squared-loss bootstrap interval crosses zero; the frozen statistical promotion criterion therefore fails.
- Accepted data: SP500 2,512 rows (2016-11-28 to 2026-11-24); VIXCLS 2,546 rows (2016-11-25 to 2026-11-24); T10Y3M 2,499 rows (2016-11-25 to 2026-11-24). All three met the preregistered synchronized-coverage gate. No event was dropped for missing/stale curve observations or incomplete windows.
- Non-overlapping origins: 415/415; validation forecasts: 107; test forecasts: 204.
- Validation RMSE: baseline 0.33999570; augmented 0.33877689; improvement +0.3585%.
- Test RMSE: baseline 0.26604998; augmented 0.26463584; improvement +0.5315%.
- Test paired squared-log-loss difference (baseline minus augmented): +0.00075047; 2,000-replication circular-block bootstrap 95% CI [-0.00332493, +0.00433012]; 67.3% of bootstrap draws positive. The interval includes zero.
- **Decision:** no promotion, no claim of statistically established incremental forecast value, no trading-strategy inference. Close this hypothesis ID; any materially different follow-up requires a new preregistration.
- **Evidence:** [GitHub Actions run 45662954265](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45662954265); [session report](../reports/sessions/2026-11-25/2026-11-25T171622Z_session-treasury-curve-volatility-45662954265.md); [generated manifest](../reports/generated/treasury-curve-volatility/45662954265-attempt-1/manifest.json).
