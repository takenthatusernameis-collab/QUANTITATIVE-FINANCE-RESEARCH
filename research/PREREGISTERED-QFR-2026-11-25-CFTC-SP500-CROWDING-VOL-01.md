# Preregistration — CFTC leveraged-fund crowding and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-CFTC-SP500-CROWDING-VOL-01
- **Registered:** 2026-11-25, before implementation or empirical result inspection
- **Timebox start:** 2026-11-25T10:29:04Z (UTC; preregistration commit timestamp).
- **Status:** INCONCLUSIVE — closed 2026-11-25 under the frozen decision rule; no tuning or further cycles under this experiment ID.
- **Market:** CME E-mini S&P 500 futures positioning (CFTC code 13874A); S&P 500 cash index close series (FRED SP500)
- **Difficulty:** MEDIUM
- **Difficulty rationale:** both sources are public and keyless; the work requires careful report-publication timing, holiday/backlog exclusions, daily-to-weekly event construction, walk-forward OLS and block-bootstrap inference, but no new venue credentials or paid data.
- **Maximum budget:** 4 substantive agent cycles total.
- **Implementation deadline:** 2026-11-28 10:30 UTC.
- **Final research conclusion deadline:** 2026-11-30 10:30 UTC.
- **Expiry rule:** if the source/timing gates or valid empirical result are incomplete at expiry, close as INCONCLUSIVE/INFEASIBLE with the exact blocker. Expiry is not evidence to reject the economic hypothesis. Do not weaken gates, reset the clock or extend automatically.

## Distinct mechanism and falsifiable claim

**Mechanism:** crowded directional exposure among CFTC-classified leveraged funds may increase the risk of position liquidation, deleveraging and volatility amplification. This is a positioning/crowding risk channel in equity-index futures, distinct from Treasury auction supply or bidder composition.

**Claim:** a high absolute leveraged-fund net position as a share of E-mini S&P 500 open interest, measured against its own trailing 156-report distribution, predicts higher subsequent five-session S&P 500 realized volatility beyond the information in recent realized volatility.

This is a volatility-forecast hypothesis, not a directional-return or tradable-strategy claim. CFTC trader categories reflect predominant business purpose and do not reveal the purpose of any individual position; the category must not be described as pure speculation.

## Data sources and acceptance

1. **CFTC TFF Futures Only dataset:** `https://publicreporting.cftc.gov/resource/gpe5-46if.json`, official dataset `gpe5-46if`. Filter exactly `cftc_contract_market_code='13874A'`; do not combine with the futures-and-options dataset or the consolidated S&P 500 contract. Use report date, open interest, leveraged-money long and short positions. Keep spreading positions separate; net = outright long minus outright short.
2. **FRED S&P 500 daily close:** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2016-11-25`. Drop missing observations; never forward-fill. Hash source responses and retain retrieval timestamps, schema, row counts and exact coverage. Do not commit raw source data.
3. Verify one row per report date for code 13874A, positive open interest, finite nonnegative positions, plausible net/open-interest bounds, chronological coverage, no duplicate dates, and a sufficient number of events. Fail closed on missing/renamed fields or incomplete pagination.
4. CFTC states that historical COT data are not updated after publication, but historical release dates are available only for the latest 13 months. Reports are generally published Friday at 3:30 p.m. ET from Tuesday positions; holidays can delay publication. Use a conservative **14-calendar-day** availability lag: the signal is the first S&P 500 close on or after report_date + 14 days. This is a fixed conservative timing convention, not a claim that it reconstructs each historical release timestamp.
5. Exclude report dates from **2025-09-30 through 2026-01-20 inclusive** because CFTC's documented 2025 publication interruption and catch-up schedule makes ordinary-lag assumptions invalid for that period. Do not backfill those observations. Inspect the current CFTC release schedule before any future update because the Commission announced a plan to move to twice-weekly publication by the end of 2026; do not assume the weekly schedule persists after a change.

## Frozen feature and target construction

- Leveraged-fund net share: `(lev_money_positions_long - lev_money_positions_short) / open_interest_all`. Exclude spreading positions from the net numerator.
- Crowding feature: absolute net share's empirical percentile among the **156 preceding valid COT reports only**. The current report is never included in its own reference distribution.
- High-crowding event: percentile >= 0.90, fixed in advance.
- Signal date: first available SP500 close on or after report_date + 14 calendar days. No close before this date may be used.
- Daily log return: `ln(close_t / close_(t-1))`; do not fill missing prices. Reject a return interval with more than four calendar days between observed closes.
- Baseline predictors available at signal close: log1p of trailing five-session realized volatility and log1p of trailing twenty-session realized volatility. Realized volatility is the square root of the sum of squared daily log returns, expressed in percent.
- Augmented model: baseline plus the trailing-156-report crowding percentile.
- Target: log1p of the square root of the sum of squared **next five** daily log returns after the signal close, expressed in percent. The target window must start strictly after the signal date and contain five consecutive observed sessions.
- Exclude overlapping target windows. No annualization, imputation, future-derived features or look-ahead joins.

## Walk-forward design

- Rolling training window: 104 prior eligible weekly events.
- A training event is eligible only if its target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Models: ordinary least squares with an intercept; no hyperparameter search or post-result feature changes.
- Inference: 2,000 deterministic circular-block bootstrap replications, block length four weekly events, fixed seed recorded in code.

## Preregistered decision rule

A promising result requires **all** of the following:

1. At least 30 test forecasts and at least 30 validation forecasts.
2. Augmented log-RV RMSE improves over baseline in both validation and test.
3. The 95% circular-block bootstrap lower bound for paired test squared-log-loss improvement (baseline loss minus augmented loss) is above zero.
4. High-crowding test events have greater mean next-five-session realized volatility than other test events, and the 95% circular-block bootstrap lower bound for that difference is above zero.

If both validation and test RMSE fail to improve and the high-crowding mean difference is non-positive, reject the hypothesis. All other outcomes are INCONCLUSIVE. No threshold, horizon, feature, training-window or split changes are permitted after empirical results are inspected.


## Empirical outcome and closure — 2026-11-25

- **Primary run:** [45596043728](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45596043728); [session report](../reports/sessions/2026-11-25/2026-11-25T103307Z_session-cftc-sp500-crowding-45596043728.md).
- **Deterministic replay:** [45596081332](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45596081332); identical CFTC/FRED response hashes and identical metrics. This confirms reproducibility, not independent validation.
- **Validation/test forecasts:** 116 / 197.
- **Augmented RMSE improvement over baseline:** validation -0.0023%; test -2.6406%. The augmented model underperformed in the test period.
- **Paired test squared-log-loss bootstrap:** 95% interval [-0.010763, 0.000095]; it crosses zero.
- **High-crowding event study:** mean next-five-session realized-volatility difference +0.2578 percentage points; 95% block-bootstrap interval [-0.2016, 0.6831]; it crosses zero.
- **Disposition:** INCONCLUSIVE. The augmented model did not improve the baseline, while the positive high-crowding event difference is statistically uncertain. The preregistered rejection condition was not met because the event-study mean difference was positive; the promotion criteria were not met either.
- **Closure:** stop this experiment now. Do not change the threshold, horizon, features, training window or split and do not spend remaining budget on parameter tuning. A future study must have a materially distinct mechanism and a new hypothesis ID/timebox.


## Limitations

- COT is a weekly aggregate and lags the underlying Tuesday positions; the 14-day buffer sacrifices recency to reduce timing risk.
- The CFTC does not publish historical release timestamps beyond the most recent 13 months; the fixed lag and documented backlog exclusion cannot prove exact historical intraday availability for every week.
- Leveraged Funds is a CFTC business-purpose classification, not a direct measure of speculative intent, leverage, liquidation risk or trader identity.
- FRED SP500 is a cash index close, not an executable futures price or total-return series. The output is a forecast evaluation, not strategy P&L, risk-adjusted trading performance or causal evidence.
- Any apparent predictive value requires a separate instrument-level execution study and independent validation before economic or trading claims.
