# Preregistration — VIX term-structure slope and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-VIX-TERM-STRUCTURE-SP500-RV-01
- **Registered:** 2026-11-25, before empirical result inspection.
- **Timebox start:** 2026-11-25T11:49:27Z.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** three keyless public daily series, exact-date alignment, one-session timing gap, rolling OLS, non-overlapping five-session targets and block-bootstrap inference; no credentials, paid data or new venue access.
- **Maximum budget:** 4 substantive agent cycles.
- **Implementation deadline:** 2026-11-28T11:50:00Z.
- **Final research conclusion deadline:** 2026-11-30T11:50:00Z.
- **Expiry rule:** if source acceptance, implementation or the frozen empirical decision is incomplete at expiry, close INCONCLUSIVE/INFEASIBLE with the exact blocker. Do not reset the clock, extend automatically, weaken gates or tune under this ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** the relative pricing of near-term and three-month S&P 500 option-implied volatility captures the market's horizon-specific assessment of jump/clustering risk and variance risk premia. A near-term inversion (VIX at or above VXV) may indicate that risk is concentrated in the immediate horizon.

**Claim:** the simple daily log slope log(VIXCLS / VXVCLS) adds out-of-sample information about next-five-session S&P 500 realized volatility beyond recent realized volatility and the VIX level; inverted observations should have higher subsequent five-session realized volatility than non-inverted observations.

This is a forecast hypothesis, not a directional-return, volatility-premium trading or tradable-strategy claim. It is not presented as the first study of VIX term structure. The bounded contribution is a retail-accessible, two-tenor, strict walk-forward test with a five-session target and explicit non-overlap/timing controls.

## Data sources and acceptance

1. **S&P 500 cash price index:** FRED SP500, daily close, source S&P Dow Jones Indices LLC; https://fred.stlouisfed.org/series/SP500.
2. **CBOE 30-day implied volatility:** FRED VIXCLS, daily close; https://fred.stlouisfed.org/series/VIXCLS.
3. **CBOE 3-month implied volatility:** FRED VXVCLS, daily close; https://fred.stlouisfed.org/series/VXVCLS.

Fetch CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25. Require at least 1,500 valid observations per series, a common recent end within four calendar days, positive finite values, unique dates and history beginning no later than 2017-03-01. Do not forward-fill missing observations. Store source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes; do not commit raw source data.

## Timing, target and event construction

- Use exact S&P 500 trading dates for signal origins.
- The signal is formed at the prior S&P 500 session close, using that date's VIX/VXV closes and S&P 500 returns. The target begins at the next S&P 500 session, preserving the fact that CBOE volatility-index closes occur after the cash-index close.
- Compute pre-event realized volatility as root-sum-square log returns over the preceding 5 and 20 S&P 500 sessions, ending at the signal date.
- Compute slope as log(VIXCLS / VXVCLS). Positive values indicate inversion; the binary event rule is VIXCLS >= VXVCLS.
- Target is root-sum-square log returns over the next 5 S&P 500 sessions, transformed as log(1 + target volatility in percent).
- Sample event origins every 6 S&P 500 sessions, ensuring five-session target windows do not overlap and each prior target ends strictly before the next signal date.
- Never bridge a return across a price gap greater than four calendar days. Drop incomplete windows; do not impute.

## Model and chronological evaluation

- Baseline OLS features: log(1 + pre-event RV5), log(1 + pre-event RV20), log(VIXCLS).
- Augmented OLS features: baseline plus log(VIXCLS / VXVCLS).
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space; report MAE and OOS R-squared versus the test-period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size 4 events, fixed seed 20261126.
- Inversion event study: compare next-five-session realized volatility for VIXCLS >= VXVCLS versus contango events; 2,000 circular-block bootstrap replications, block size 4 events, fixed seed 20261127.

## Frozen decision rule

A promising forecast result requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower bound is above zero (positive values favor the augmented model).
4. Inverted-term-structure events have higher mean test-period target volatility than contango events, and the 95% bootstrap lower bound for that difference is above zero.

Reject only if both validation and test RMSE fail to improve and the inversion-event mean difference is non-positive. All other outcomes are INCONCLUSIVE. A BACKTESTED result is not independent validation, a causal claim, a strategy P&L or permission to deploy live. Do not tune the slope formula, target horizon, event spacing, model window, event rule or date split after seeing results.

## Literature rationale and novelty boundary

- Chang, Kai-Jiun, Mao-Wei Hung and Yaw-Huei Wang (2018), “Volatility information implied in the term structure of VIX,” Journal of Futures Markets, DOI: https://doi.org/10.1002/fut.21964. The study reports that term-structure variables add to level-only realized-volatility forecasts. It motivates the question but does not validate this simple two-index slope or the present horizon/split.
- Johnson, Travis L. (2017), “Risk Premia and the VIX Term Structure,” Journal of Financial and Quantitative Analysis, DOI: https://doi.org/10.1017/S0022109017000825. The paper links term-structure shape to variance risk premia and synthetic variance-linked returns; this is adjacent evidence, not the same target.
- Li, Tianjiao, Pakorn Aschakulporn and Jin E. Zhang (2025), “VIX term structure and future realized volatility,” Applied Economics, DOI: https://doi.org/10.1080/00036846.2025.2601895. This is directly related; the present experiment is a bounded retail-data replication/screen, not a claim of first discovery.

## Explicit limitations

- SP500 is a cash price index, not an executable futures series or total-return index.
- VIX and VXV are option-implied indices, not directly investable assets; the two-tenor slope is not the full multi-maturity principal-component term structure used in some papers.
- FRED indicates observations may be revised. This experiment uses the current retrieved vintage and does not reconstruct historical release vintages; record that limitation.
- CBOE VIX/VXV closes occur after the S&P 500 cash close; the one-session gap is mandatory.
- Forecasting only. No transaction-cost model, causal claim, tradable strategy or live-deployment conclusion is permitted.
- CBOE/S&P source data are not redistributed; only aggregate metrics and hashes are retained.
