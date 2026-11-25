# Preregistration — lagged broad-dollar momentum and Bitcoin five-day returns

- **Hypothesis ID:** QFR-2026-11-25-BTC-LAGGED-BROAD-USD-MOMENTUM-01
- **Registered:** 2026-11-25T12:15:14Z, before empirical result inspection.
- **Status:** FEASIBILITY_CHECKED — official public daily series and source semantics identified; full row-level coverage, freshness and empirical acceptance remain subject to the workflow's fail-closed checks.
- **Timebox start:** 2026-11-25T12:15:14Z.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** two public daily series, distinct 7-day crypto versus 5-day FX calendars, strict lagging of the dollar observation, non-overlapping five-session targets, rolling OLS and block-bootstrap inference. No credentials, paid data or new venue access.
- **Maximum budget:** 4 substantive agent cycles.
- **Implementation deadline:** 2026-11-28T12:15:14Z.
- **Final research conclusion deadline:** 2026-11-30T12:15:14Z.
- **Expiry rule:** if source acceptance, implementation or the frozen empirical decision is incomplete at expiry, close INCONCLUSIVE/INFEASIBLE with the exact blocker. Do not reset the clock, extend automatically, weaken gates or tune under this ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** a persistent broad appreciation of the U.S. dollar can tighten dollar-denominated financial conditions and alter global risk-taking. Because the dollar index and Bitcoin observations have different trading calendars and close times, any incremental information should be tested with a strictly lagged dollar signal rather than same-date alignment.

**Claim:** the five-observation log return of the nominal broad U.S. dollar index, measured using the latest dollar-index observation strictly before the Bitcoin signal date, adds out-of-sample information about the next-five-Bitcoin-session return beyond Bitcoin's own trailing five- and twenty-session momentum and realized volatility. The expected coefficient is negative, but the frozen decision is based on forecast performance and paired-loss inference, not coefficient sign alone.

This is a predictive-forecast hypothesis, not a causal claim, hedge conclusion, directional trading strategy or tradable P&L. It is materially distinct from the repository's prior Treasury auction, CFTC positioning and VIX term-structure hypotheses.

## Data sources and acceptance

1. **Bitcoin USD daily close:** FRED series CBBTCUSD, sourced from Coinbase; https://fred.stlouisfed.org/series/CBBTCUSD. FRED identifies this as daily, seven-day data and states that observations are as of 5 PM Pacific Time. The source is copyrighted; do not redistribute raw observations.
2. **Nominal broad U.S. dollar index:** FRED series DTWEXBGS, sourced from the Board of Governors of the Federal Reserve System, H.10 Foreign Exchange Rates; https://fred.stlouisfed.org/series/DTWEXBGS. FRED identifies this as daily data.

Fetch CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25. Require at least 1,500 valid observations per series, positive finite values, unique dates, history beginning no later than 2017-03-01, and latest observations within four calendar days of one another. Require the broad-dollar series to have at least six prior observations within the 14 calendar days preceding each signal. Do not forward-fill either series. Store source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes; do not commit raw source data.

## Timing, features and target

- Bitcoin signal dates are its exact daily observation dates.
- For each Bitcoin signal date t, use the most recent DTWEXBGS observation with date strictly less than t. Never use a same-date dollar observation, even if it exists. This conservative one-observation lag avoids assuming synchronized publication/close timestamps.
- Dollar momentum is 100 × log(DXY[d] / DXY[d-5]), where d is the latest eligible prior dollar observation and d-5 is five prior dollar-index observations earlier.
- Bitcoin baseline features, all known at the signal close: trailing 5-session log return in percent; trailing 20-session log return in percent; trailing 5-session realized volatility in percent; trailing 20-session realized volatility in percent.
- Augmented model adds only the lagged five-observation broad-dollar return in percent.
- Target is 100 × log(BTC[t+5] / BTC[t]), using the next five observed daily Bitcoin closes.
- Sample signal origins every six Bitcoin observations. This prevents target overlap when the next five closes are used. Require all six dates in the target interval and all 20 preceding daily returns to be valid; do not bridge missing Bitcoin calendar days or impute values.
- For the dollar series, use five observed index changes over the latest six eligible observations; require the latest eligible observation to be strictly before t and no more than 14 calendar days old.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE of five-session Bitcoin log returns in percentage points; report MAE and directional accuracy as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size 4 events, fixed seed 20261126.

## Frozen decision rule

A promising incremental forecast result requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper bound is below zero, indicating evidence that the augmented model is worse. All other outcomes are INCONCLUSIVE. A BACKTESTED result is not independent validation, a causal claim, an investment recommendation, a hedge finding or permission to deploy live. Do not tune features, horizons, event spacing, model window, date splits or bootstrap settings after seeing results.

## Literature rationale and novelty boundary

- Conlon, Corbet and McGee (2024), “Enduring relief or fleeting respite? Bitcoin as a hedge and safe haven for the US dollar,” *Annals of Operations Research*, DOI: https://doi.org/10.1007/s10479-024-05884-y. This examines Bitcoin's hedge/safe-haven relationship to dollar exchange rates; it motivates cross-market relevance but does not validate this lagged broad-index forecasting test.
- Al-Mansouri (2025), “Bitcoin vs. the US Dollar: Unveiling Resilience Through Wavelet Analysis of Price Dynamics,” *Journal of Risk and Financial Management*, DOI: https://doi.org/10.3390/jrfm18050259. The paper reports weak and sporadic Bitcoin coupling with dollar strength in its wavelet analysis. That is a reason to test incremental predictive value conservatively, not evidence that the present model should work.

The bounded contribution is a strict-lag, non-overlapping, rolling out-of-sample forecast test using a broad trade-weighted dollar index, not a claim of first discovery.

## Explicit limitations

- Coinbase CBBTCUSD observations are stated by FRED to be as of 5 PM Pacific Time and are copyrighted; raw observations must not be redistributed.
- DTWEXBGS is a daily U.S. business-day index. The strict prior-observation rule deliberately introduces a lag and can leave weekend Bitcoin signals with a stale Friday observation.
- FRED observations can be revised; this experiment uses the retrieved current vintage and does not reconstruct historical release vintages.
- The five-session forecast is not a trading strategy. No transaction-cost model, execution model, causal claim, hedge/safe-haven conclusion or live-deployment conclusion is permitted.
- A statistically promising forecast still requires independent reconstruction and a separately specified instrument-level economic study.
