# Preregistration — SOFR-EFFR repo funding premium and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-26-SOFR-EFFR-REPO-PREMIUM-SP500-RV-01
- **Registered:** 2026-11-26T01:57:13Z, before this hypothesis's empirical result inspection.
- **Status:** REJECTED — REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** four public FRED daily series, one common-date spread calculation, and the repository's existing rolling OLS/paired-bootstrap harness.
- **Implementation timebox:** 2026-11-26T01:57:13Z through 2026-11-29T01:57:13Z.
- **Research conclusion deadline:** 2026-12-01T01:57:13Z.
- **Maximum substantive cycles:** one preregistered screen. Any alternate spread, lookback, model family, target or robustness study requires a new hypothesis ID and preregistration.
- **Expiry:** if accepted source freshness, deterministic tests or the frozen screen is incomplete by the conclusion deadline, close INCONCLUSIVE/INFEASIBLE. Do not retune, extend or relax gates under this ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** SOFR is a broad secured overnight Treasury-repo financing rate; EFFR is the volume-weighted median rate on unsecured overnight federal-funds transactions. A widening in SOFR relative to EFFR can indicate a change in secured funding demand, collateral/intermediation conditions or repo-market frictions that is not fully summarized by the VIX or recent equity realized volatility.

**Claim:** a strictly lagged five-common-observation widening in the SOFR-EFFR spread adds out-of-sample information about next-five-session S&P 500 realized volatility beyond prior-five-session realized volatility, prior-twenty-session realized volatility and signal-date VIX.

The only added feature is:

    repo_spread_5obs_change_bp = 100 * ((SOFR-EFFR)[d] - (SOFR-EFFR)[d-5])

where d is the latest date on which both rates have an observation and is strictly earlier than the S&P 500 signal date. FRED rate units are percentage points, so multiplication by 100 expresses the spread change in basis points. Positive values mean the secured-over-unsecured spread widened over five common observation intervals.

This is a predictive screen, not a causal claim, an identified repo shock, a trading strategy or evidence of a tradable risk premium.

## Literature and novelty boundary

- David-Pur, Galil, Rosenboim and Shapir (2023), “Shedding light on the dynamics of the secured overnight financing rate (SOFR),” International Review of Financial Analysis. The study examines SOFR-EFFR and SOFR-IOER spreads and their relationship with repo-market interventions and calendar effects: https://doi.org/10.1111/irfi.12439.
- Ahn and Ahn (2025), “The promises and pitfalls of the secured overnight financing rate,” Applied Economics Letters. The paper documents SOFR deviations from Treasury-bill rates and an association between abrupt SOFR deviations and increases in VIX: https://doi.org/10.1080/13504851.2024.2302896.
- The New York Fed's Office of Financial Research short-term funding monitor describes SOFR as the broadest secured repo rate and documents the next-business-morning publication schedule for secured and unsecured reference rates: https://www.financialresearch.gov/short-term-funding-monitor/datasets/fnyr/.

The literature already studies SOFR-EFFR spread dynamics and SOFR/VIX associations. The narrow incremental question here is whether a fixed five-observation SOFR-EFFR spread change improves a strictly walk-forward next-five-session S&P 500 volatility forecast after controlling for both recent realized volatility and VIX. No first-discovery claim is made.

## Data sources and acceptance

1. **SOFR:** FRED series SOFR, sourced from the Federal Reserve Bank of New York; daily, percent, not seasonally adjusted: https://fred.stlouisfed.org/series/SOFR.
2. **Effective Federal Funds Rate:** FRED series EFFR, sourced from the Federal Reserve Bank of New York; daily, percent, not seasonally adjusted: https://fred.stlouisfed.org/series/EFFR.
3. **S&P 500 cash price index:** FRED series SP500, daily close: https://fred.stlouisfed.org/series/SP500.
4. **CBOE 30-day implied volatility:** FRED series VIXCLS, daily close: https://fred.stlouisfed.org/series/VIXCLS.

Fetch each CSV from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2018-04-03.

Acceptance gates:

- SOFR and EFFR: at least 1,700 observations each and at least 1,700 common dates; first valid observation no later than 2018-05-03; latest common date no more than five calendar days old at retrieval; latest individual series dates within three calendar days.
- SP500 and VIXCLS: at least 1,500 observations each; first valid observation no later than 2018-05-03; latest dates within four calendar days; common latest date no more than eight calendar days old.
- Reject duplicate dates, invalid dates, non-finite values and non-positive values in all four series. SOFR-EFFR spread values may be positive or negative.
- Use only exact common SOFR/EFFR observation dates. Do not forward-fill, interpolate, synthesize or carry a rate across a gap greater than five calendar days.
- Record exact URLs, retrieval time, row counts, coverage and SHA-256 hashes. Do not commit raw source observations.
- If any source fails acceptance, record the exact failure and close INCONCLUSIVE/INFEASIBLE. Do not relax the gates after seeing the response.

## Timing, feature and target construction

- The SOFR and EFFR observations are published on the following business morning (secured rate approximately 8:00 a.m. ET; EFFR approximately 9:00 a.m. ET). To avoid same-date availability ambiguity, at S&P 500 signal date t use only the latest common rate observation date d < t.
- Require the latest common rate date to be no more than five calendar days before the signal date.
- The fixed feature is the five-common-observation change in SOFR-EFFR spread, in basis points, as defined above. Require six common spread observations including the start and end points; every adjacent observation gap in this feature window must be no greater than five calendar days.
- Signal origins are every sixth S&P 500 trading observation, beginning only after 20 prior price returns are available. Require the same-date VIX observation.
- Baseline predictors: log(1 + pre_rv5) and log(1 + pre_rv20) where realized volatility is expressed in percent, plus log(VIXCLS) on the signal date.
- The augmented model adds only repo_spread_5obs_change_bp.
- Compute realized volatility as the root-sum-square of daily S&P 500 log returns multiplied by 100. Use the preceding five and twenty S&P 500 sessions for baseline features and the next five sessions for the target.
- Do not bridge a price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Event origins are six S&P 500 sessions apart, so five-session target windows do not overlap. A training target must end strictly before the current signal date.

## Model and chronological evaluation

- Baseline OLS features: pre_rv5_log, pre_rv20_log, log_vix.
- Augmented OLS features: baseline plus repo_spread_5obs_change_bp.
- Standardize using each training window only; fit separate rolling OLS models.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and out-of-sample R-squared versus period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four events, fixed seed 20261127.

## Frozen decision rule

A promising incremental forecast requires all of:

1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero. All other outcomes are INCONCLUSIVE. Do not change the spread definition, five-observation lookback, strict prior-date rule, target horizon, event spacing, date splits, training window, bootstrap settings or decision thresholds after seeing results.

Even a promising forecast is not independent validation, a causal finding, an executable strategy, trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- FRED observations are current vintages; historical point-in-time ALFRED vintages are not reconstructed. Later revisions can create look-ahead relative to historical release time.
- SOFR is a broad secured Treasury-repo rate; EFFR is an unsecured federal-funds transaction rate. Their spread is a proxy that can reflect collateral composition, dealer intermediation, calendar effects and Federal Reserve operations, not a pure exogenous liquidity shock.
- The strict prior-date rule avoids same-date rate publication look-ahead but does not reconstruct intraday historical publication timestamps.
- The predictor is correlated with other funding and monetary-policy variables; the baseline controls for VIX and recent realized volatility but does not establish causal independence.
- SP500 is a cash price index, not an executable futures series or total-return index.
- FRED data are not redistributed; no raw observations are committed.
- Forecasting only: no transaction-cost model, tradable strategy, live-trading conclusion or deployment authorization.

## Empirical disposition

- **Final status:** REJECTED — REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse.
- **Completed real-data backtest:** yes.
- **Data scope:** FRED SOFR/EFFR daily from 2018-04-03 to 2026-11-24 (common end 2026-11-24); SP500/VIXCLS 2018-04-03 to 2026-11-24; 359 accepted non-overlapping six-session-spaced events; validation 2019-2021; test 2022 onward.
- **Summary:** validation/test n=51/204; RMSE improvement=-0.1321%/-2.1813%.
- **Report:** [../reports/sessions/2026-11-26/2026-11-26T020146Z_session-sofr-effr-repo-premium-45739654076.md](../reports/sessions/2026-11-26/2026-11-26T020146Z_session-sofr-effr-repo-premium-45739654076.md).

Forecasting screen only. No causal, trading, profitability or deployment claim.
