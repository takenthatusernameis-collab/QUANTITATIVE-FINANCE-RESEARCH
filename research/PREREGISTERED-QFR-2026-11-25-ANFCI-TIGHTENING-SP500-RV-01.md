# Preregistration — macro-adjusted financial-conditions tightening and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-ANFCI-TIGHTENING-SP500-RV-01
- **Registered:** 2026-11-25T22:25:26Z, before empirical result inspection.
- **Status:** PREREGISTERED; one bounded real-data walk-forward screen is authorized by this specification.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** one public weekly Chicago Fed index plus two public FRED daily series; no credentials, paid data, or external dependencies.
- **Implementation timebox:** 2026-11-25T22:25:26Z through 2026-11-29T22:25:26Z.
- **Research conclusion deadline:** 2026-12-01T22:25:26Z.
- **Maximum substantive implementation/research cycles:** 1 preregistered screen. Any follow-up, alternate feature or robustness study requires a new preregistration.
- **Expiry rule:** if accepted source freshness, deterministic implementation or the frozen empirical result is incomplete by the conclusion deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. Do not extend, retune or relax gates under this hypothesis ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** the Chicago Fed Adjusted National Financial Conditions Index (ANFCI) summarizes a broad set of risk, credit and leverage conditions after adjusting for prevailing economic conditions. A sharp four-week tightening in this macro-adjusted composite may capture a broad deterioration in financial intermediation and risk-bearing capacity that precedes elevated equity-market volatility.

**Claim:** a positive four-week change in the strictly lagged ANFCI adds out-of-sample information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and the VIX level.

The predictor is fixed as:

\`anfci_4w_change = ANFCI_t - ANFCI_(t-4 weekly observations)\`

Positive values mean tightening over four weekly observations. The current observation is not ranked or transformed using future data. No threshold search, sign reversal, alternative lookback or feature substitution is permitted.

This is a forecast screen, not a causal claim, an identified funding shock, a trading strategy or evidence of a tradable risk premium.

## Literature and novelty boundary

- Opschoor, A., van Dijk, D. and van der Wel, M. (2014), “Predicting Volatility and Correlations with Financial Conditions Indexes,” *Journal of Empirical Finance*, 29, 435–447, DOI: https://doi.org/10.1016/j.jempfin.2014.10.003. Their study uses a Bloomberg Financial Conditions Index in volatility/correlation models for U.S. deposit-bank stocks. It motivates testing financial-conditions information but does not establish that the Chicago Fed ANFCI's four-week change improves a short-horizon S&P 500 forecast.
- The Chicago Fed describes ANFCI as isolating a component of financial conditions uncorrelated with economic conditions: https://www.chicagofed.org/research/data/nfci/current-data.
- The Chicago Fed release calendar specifies weekly releases at 8:30 a.m. ET, normally Wednesday, covering the previous Friday; when a federal holiday falls on Wednesday or earlier, the release moves to Thursday: https://www.chicagofed.org/research/data/data-release-calendar.

The repository has already tested individual cross-market shocks, Treasury-curve movement, VIX term structure, CFTC positioning and Treasury auction/supply mechanisms. This experiment tests a distinct macro-adjusted, multi-indicator financial-conditions composite and its four-week change. It does not claim first discovery of financial-conditions/volatility relationships.

## Data sources and acceptance

1. **Chicago Fed Adjusted National Financial Conditions Index:** FRED series \`ANFCI\`, weekly ending Friday; https://fred.stlouisfed.org/series/ANFCI. Fetch CSV from \`https://fred.stlouisfed.org/graph/fredgraph.csv?id=ANFCI&cosd=2016-11-25\`.
2. **S&P 500 cash price index:** FRED \`SP500\`, daily close; https://fred.stlouisfed.org/series/SP500.
3. **CBOE 30-day implied volatility:** FRED \`VIXCLS\`, daily close; https://fred.stlouisfed.org/series/VIXCLS.

Acceptance gates:

- ANFCI: at least 400 unique weekly observations; first accepted date no later than 2017-02-23; latest observation no more than 10 calendar days old at retrieval. The freshness threshold is deliberately strict because the Chicago Fed's release calendar specifies a weekly Wednesday/Thursday release; if FRED has not yet incorporated the scheduled latest week, do not backtest on the stale vintage.
- SP500 and VIXCLS: at least 1,500 valid observations each; first date no later than 2017-02-23; latest dates within four calendar days; common latest date no more than eight calendar days old.
- Reject duplicate dates, invalid dates, non-finite values and non-positive SP500/VIX values. ANFCI may be negative or positive.
- Do not forward-fill, interpolate or synthesize observations. Require four consecutive weekly ANFCI dates exactly seven calendar days apart for each feature observation. Missing weeks invalidate affected events.
- Record exact URLs, retrieval time, row counts, coverage and SHA-256 hashes. Do not commit raw source data.
- If any source fails acceptance, record the exact failure and close INCONCLUSIVE/INFEASIBLE. Do not relax the gates after seeing the response.

## Timing, feature and target construction

- The ANFCI observation date is the Friday at the end of its reference week. Treat it as unavailable until seven calendar days later, then use the first S&P 500 trading close on or after that date. This is conservative relative to the published Wednesday release and also covers the specified Thursday holiday-week shift.
- At each accepted weekly observation, calculate the four-week change from the ANFCI value exactly four consecutive weekly observations earlier. No same-week, future or revised-release timing is inferred.
- Use the signal-date S&P 500 close and same-date VIX close. The target begins on the next S&P 500 session.
- Baseline predictors: log(1 + pre-event S&P 500 RV5 in percent), log(1 + pre-event S&P 500 RV20 in percent), and log(VIXCLS) on the signal date.
- The augmented model adds only \`anfci_4w_change\`.
- Compute realized volatility as the root-sum-square of daily S&P 500 log returns multiplied by 100. Use the preceding five and twenty sessions for baseline features and the next five sessions for the target.
- Do not bridge a price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Keep events only when their five-session target windows do not overlap. Adjacent weekly windows may meet at the next signal close, but a training target must end strictly before the current signal date.

## Model and chronological evaluation

- Baseline OLS features: \`pre_rv5_log\`, \`pre_rv20_log\`, \`log_vix\`.
- Augmented OLS features: baseline plus \`anfci_4w_change\`.
- Standardize features using each training window only; fit a separate rolling OLS for each model.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and out-of-sample R-squared versus the period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four weekly events, fixed seed 20261126.

## Frozen decision rule

A promising incremental forecast requires all of:

1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero. All other outcomes are INCONCLUSIVE. Do not change the predictor, lookback, lag, target horizon, date split, training window, bootstrap settings or decision thresholds after seeing results.

Even a promising forecast is not independent validation, a causal finding, an executable strategy, trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- Chicago Fed states that the historical NFCI/ANFCI series can be revised as component data and estimated weights change, with revisions sometimes more pronounced near the beginning of a month. This screen uses the current FRED vintage; historical point-in-time releases are not reconstructed. The seven-day release lag does not remove revision look-ahead.
- ANFCI is a composite indicator, not an exogenous funding shock. Its constituents may overlap with information correlated with VIX and equity prices.
- The macro adjustment does not identify a causal transmission channel, investor leverage, forced deleveraging or a specific funding-market event.
- The seven-day timing rule is conservative but does not reconstruct exact historical intraday publication timestamps.
- SP500 is a cash price index, not an executable futures series or total-return index.
- FRED/Chicago Fed data are not redistributed; no raw source data are committed.
- Forecasting only: no transaction-cost model, tradable strategy, live-trading conclusion or deployment authorization.
