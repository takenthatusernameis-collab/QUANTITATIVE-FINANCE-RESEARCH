# Preregistration — VXN/VIX cross-index implied-volatility spread and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-26-VXN-VIX-CROSS-INDEX-SP500-RV-01
- **Registered:** 2026-11-26T02:03:29Z, before this hypothesis's empirical result inspection.
- **Status:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** three public FRED daily series, one common-date log-ratio feature, and the repository's existing rolling OLS/paired-bootstrap harness.
- **Implementation timebox:** 2026-11-26T02:03:29Z through 2026-11-29T02:03:29Z.
- **Research conclusion deadline:** 2026-12-01T02:03:29Z.
- **Maximum substantive cycles:** one preregistered screen. Any alternate spread, lookback, model family, target or robustness study requires a new hypothesis ID and preregistration.
- **Expiry:** if accepted source freshness, deterministic tests or the frozen screen is incomplete by the conclusion deadline, close INCONCLUSIVE/INFEASIBLE. Do not retune, extend or relax gates under this ID.

## Implementation validation note — 2026-11-26

The first hosted attempt, run 45740292998, passed the 13 deterministic hypothesis tests and the three repository admission tests, then failed during evidence persistence because the result-to-preregistration updater was missing from the admitted script. The source retrieval and forecast function had returned to the output-writing stage, but the report/manifest were not committed. The missing updater was implemented in the same session and a regression test now checks idempotent status/report-link updates. No empirical disposition is accepted from that unpersisted attempt; rerun the frozen specification after this repair. This implementation-only correction does not change the feature, data, timing, target, model, splits, bootstrap or decision rule. The repository-wide workflow repair now checks out the immutable triggering commit (`${{ github.sha }}`), verifies `git rev-parse HEAD` against `GITHUB_SHA`, and sets `cancel-in-progress: false` for every research workflow. The repaired VXN/VIX screen is re-admitted as one atomic commit; its manifest source SHA must match the executed checkout.

## Distinct mechanism and falsifiable claim

**Mechanism:** VXN is the CBOE implied-volatility index on Nasdaq-100 options, while VIX is the corresponding index on S&P 500 options. A rise in VXN relative to VIX can reveal a repricing of technology/growth-heavy equity risk that is not fully captured by the broad-market VIX level. If that relative risk repricing is a leading signal of broader equity-market transmission, it may add information about subsequent S&P 500 realized volatility.

**Claim:** a strictly lagged five-observation increase in the Nasdaq-100 versus S&P 500 implied-volatility ratio adds out-of-sample information about next-five-session S&P 500 realized volatility beyond prior-five-session realized volatility, prior-twenty-session realized volatility and signal-date VIX.

The only added feature is:

    vxn_vix_5obs_change = log(VXN/VIX)[d] - log(VXN/VIX)[d-5]

where d is the latest date on which both indices have an observation and is strictly earlier than the S&P 500 signal date. A positive value means the Nasdaq-100 implied-volatility premium relative to the S&P 500 widened over five common observation intervals.

This is a predictive screen, not a causal claim, an identified volatility spillover, a trading strategy or evidence of a tradable risk premium.

## Literature and novelty boundary

- Giot (2005), “Relationships Between Implied Volatility Indexes and Stock Index Returns,” The Journal of Portfolio Management, 31(3), 92–100. The study documents relationships between VIX/VXN and their respective equity indices, including asymmetric effects: https://doi.org/10.3905/jpm.2005.500363.
- Chiang (2012), “The Relationships between Implied Volatility Indexes and Spot Indexes,” Procedia - Social and Behavioral Sciences, 57, 231–235. The study examines VIX/VXN and their underlying indices and reports no obvious lead-lag relationship between Nasdaq-100 and VXN, a useful caution against assuming predictability: https://doi.org/10.1016/j.sbspro.2012.09.1179.
- Iqbal, Bouri, Liu and Kumar (2024), “Volatility spillovers during normal and high volatility states and their driving factors: A cross-country and cross-asset analysis,” International Journal of Finance & Economics, 29(1), 975–995. The paper documents state-dependent volatility transmission across equity and other asset markets: https://doi.org/10.1002/ijfe.2717.

The repository already screened VIX/VXV term structure. This hypothesis is not a maturity-slope variant: it tests cross-index relative implied volatility between Nasdaq-100 and S&P 500 options, with a specific technology/growth concentration and cross-market transmission mechanism. The narrow incremental question is whether the lagged VXN/VIX ratio change improves a fixed next-five-session S&P 500 realized-volatility forecast after controlling for broad VIX and recent realized volatility. No first-discovery claim is made.

## Data sources and acceptance

1. **Nasdaq-100 implied volatility:** FRED series VXNCLS, sourced from Cboe; daily close: https://fred.stlouisfed.org/series/VXNCLS.
2. **S&P 500 implied volatility:** FRED series VIXCLS, sourced from Cboe; daily close: https://fred.stlouisfed.org/series/VIXCLS.
3. **S&P 500 cash price index:** FRED series SP500, daily close: https://fred.stlouisfed.org/series/SP500.

Fetch each CSV from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25.

Acceptance gates:

- VXNCLS and VIXCLS: at least 1,500 observations each and at least 1,500 common dates; first common observation no later than 2016-12-25; latest common date no more than five calendar days old at retrieval; latest individual series dates within three calendar days.
- SP500: at least 1,500 observations; first valid observation no later than 2016-12-25; latest SP500 and VIXCLS dates within four calendar days; common latest price date no more than eight calendar days old.
- Reject duplicate dates, invalid dates, non-finite values and non-positive values in all three series.
- Use only exact common VXN/VIX observation dates. Do not forward-fill, interpolate, synthesize or carry an implied-volatility index across a gap greater than five calendar days.
- Record exact URLs, retrieval time, row counts, coverage and SHA-256 hashes. Do not commit raw source observations.
- If any source fails acceptance, record the exact failure and close INCONCLUSIVE/INFEASIBLE. Do not relax the gates after seeing the response.

## Timing, feature and target construction

- At S&P 500 signal date t use only the latest common VXN/VIX observation date d < t. This one-session-or-more lag avoids relying on same-date close publication ordering.
- Require the latest common VXN/VIX date to be no more than five calendar days before the signal date.
- The fixed feature is the five-common-observation change in log(VXN/VIX), as defined above. Require six common index observations including the start and end points; every adjacent observation gap in this feature window must be no greater than five calendar days.
- Signal origins are every sixth S&P 500 trading observation, beginning only after 20 prior price returns are available. Require the same-date VIX observation for the baseline.
- Baseline predictors: log(1 + pre_rv5) and log(1 + pre_rv20), where realized volatility is expressed in percent, plus log(VIXCLS) on the signal date.
- The augmented model adds only vxn_vix_5obs_change.
- Compute realized volatility as the root-sum-square of daily S&P 500 log returns multiplied by 100. Use the preceding five and twenty S&P 500 sessions for baseline features and the next five sessions for the target.
- Do not bridge a price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Event origins are six S&P 500 sessions apart, so five-session target windows do not overlap. A training target must end strictly before the current signal date.

## Model and chronological evaluation

- Baseline OLS features: pre_rv5_log, pre_rv20_log, log_vix.
- Augmented OLS features: baseline plus vxn_vix_5obs_change.
- Standardize using each training window only; fit separate rolling OLS models.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and out-of-sample R-squared versus period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four events, fixed seed 20261128.

## Frozen decision rule

A promising incremental forecast requires all of:

1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper confidence bound is below zero. All other outcomes are INCONCLUSIVE. Do not change the ratio definition, five-observation lookback, strict prior-date rule, target horizon, event spacing, date splits, training window, bootstrap settings or decision thresholds after seeing results.

Even a promising forecast is not independent validation, a causal finding, an executable strategy, trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- FRED observations are current vintages; historical point-in-time revisions are not reconstructed. Later corrections can create look-ahead relative to historical release time.
- VXN and VIX reference different index constituents and option markets. Their ratio can reflect index composition, concentration and relative option demand rather than a pure causal volatility spillover.
- The strict prior-date rule avoids same-date publication ambiguity but does not reconstruct intraday historical dissemination timestamps.
- The baseline controls for broad VIX level and recent S&P 500 realized volatility but not every sector-specific or cross-index risk factor.
- SP500 is a cash price index, not an executable futures series or total-return index.
- FRED data are not redistributed; no raw observations are committed.
- Forecasting only: no transaction-cost model, tradable strategy, live-trading conclusion or deployment authorization.

## Empirical disposition

- **Final status:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule.
- **Completed real-data backtest:** yes.
- **Data scope:** FRED VXNCLS/VIXCLS daily from 2016-11-25 to 2026-11-24 (common end 2026-11-24); SP500 2016-11-28 to 2026-11-24; 415 accepted non-overlapping six-session-spaced events; validation 2019-2021; test 2022 onward.
- **Summary:** validation/test n=107/204; RMSE improvement=-1.0496%/-1.0025%.
- **Report:** [../reports/sessions/2026-11-26/2026-11-26T021719Z_session-vxn-vix-cross-index-45741392870.md](../reports/sessions/2026-11-26/2026-11-26T021719Z_session-vxn-vix-cross-index-45741392870.md).

Forecasting screen only. No causal, trading, profitability or deployment claim.
