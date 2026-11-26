# Preregistered hypothesis: KC PRS policy-rate skew and 2Y Treasury yield changes

- **Hypothesis ID:** QFR-2026-11-26-KCPRS-POLICY-SKEW-DGS2-01
- **Registered:** 2026-11-26, before retrieval of the empirical source series for this experiment.
- **Status:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** three public daily series, one lagged options-implied risk-asymmetry feature, one Treasury-yield target, and the repository's existing rolling OLS / circular-block bootstrap harness.
- **Implementation timebox:** 2026-11-26T03:15:00Z through 2026-11-29T03:15:00Z.
- **Owner:** autonomous research factory.
- **Research class:** forecasting only; no trading strategy or causal claim.

## Novelty and prior-work boundary

The Kansas City Fed's 2024 Economic Bulletin introduces the KC Policy Rate Skew (KC PRS), documents that it tends to lead interest-rate cycles, and relates it to one-year-ahead federal-funds forecast errors. The source methodology uses Eurodollar options before 2023 and SOFR options from 2023 onward.

This experiment does not claim discovery of the KC PRS mechanism. Its bounded incremental question is whether the latest strictly prior KC PRS level adds chronological out-of-sample forecast information for the next 21-observation change in the 2-year Treasury constant-maturity yield beyond a baseline containing the current 2-year yield, its recent changes, and the 10y-2y curve slope. The test period begins in 2023, after the KC PRS source switched to SOFR options.

Prior literature / source:
- Bundick, Doh and Smith (2024), Federal Reserve Bank of Kansas City, “How Do Financial Markets Perceive the Balance of Risks to the Policy Rate?” https://www.kansascityfed.org/research/economic-bulletin/how-do-financial-markets-perceive-the-balance-of-risks-to-the-policy-rate/
- KC PRS data and methodology / source-regime note: https://www.kansascityfed.org/data-and-trends/kansas-city-fed-policy-rate-skew/
- FRED KCPRS series: https://fred.stlouisfed.org/series/KCPRS
- FRED DGS2: https://fred.stlouisfed.org/series/DGS2
- FRED DGS10: https://fred.stlouisfed.org/series/DGS10

## Falsifiable prediction

Higher (more positive) strictly prior KCPRS readings indicate greater option-implied upside risk to short-term interest rates one year ahead. Conditional on current DGS2 level, recent DGS2 changes and the 10y-2y slope, the augmented model should forecast the next 21-observation DGS2 yield change with lower RMSE than the baseline in both validation and test periods.

The null is that KCPRS adds no incremental out-of-sample information, or that its incremental forecast value is unstable / statistically uncertain under the frozen evaluation.

## Data and feasibility requirements

- KCPRS: daily Kansas City Fed Policy Rate Skew, percentage points; source history begins 1989-04-03.
- DGS2: daily 2-year Treasury constant-maturity yield, percent.
- DGS10: daily 10-year Treasury constant-maturity yield, percent.
- Retrieval: public FRED graph CSV endpoint, one request per series, with exact URLs, retrieval time, row counts, date coverage and SHA-256 hashes recorded.
- Minimum accepted rows: 7,500 per series.
- Earliest accepted observation: no later than 30 calendar days after 1989-04-03.
- Latest accepted observations: no future dates and no more than five calendar days stale at retrieval.
- Reject duplicate dates, invalid/non-finite values, non-positive DGS2/DGS10 values, unrecognized CSV schemas, or any within-series gap above five calendar days.
- Require at least 7,500 common KCPRS/DGS2/DGS10 dates.
- Do not forward-fill missing observations or infer values from charts.

## Signal, feature and target construction

- Signal date: date t, using DGS2 and DGS10 daily observations.
- KCPRS availability: use the latest KCPRS observation with date strictly earlier than t. Same-date KCPRS values are prohibited even if present in the downloaded CSV.
- Baseline features:
  1. DGS2 level at t, in percentage points.
  2. DGS2 change over the previous 21 observed Treasury sessions, in basis points.
  3. DGS2 change over the previous 63 observed Treasury sessions, in basis points.
  4. DGS10 minus DGS2 curve slope at t, in basis points.
- Augmented feature: latest strictly prior KCPRS level, in percentage points. No other feature, threshold or transformation is permitted.
- Target: 100 × (DGS2 at t+21 observed Treasury sessions − DGS2 at t), in basis points.
- Event origins are spaced 22 observed Treasury sessions apart. Each 21-session target therefore matures before the next signal; no target windows overlap.
- Require a KCPRS observation no more than five calendar days before each signal. Skip and count stale or missing observations; never forward-fill.

## Model and chronological evaluation

- Baseline and augmented models: rolling ordinary least squares using the repository's deterministic training-only feature standardization and ridge-stabilized normal equations.
- Rolling training window: 52 prior events. Every training event must have signal_date earlier than the current signal and target_end_date strictly earlier than the current signal.
- Validation: signal dates 2018-01-01 through 2022-12-31.
- Test: signal dates 2023-01-01 onward.
- Minimum forecasts: 30 in each period.
- Primary metric: RMSE in basis points. MAE, directional accuracy and out-of-sample R² are descriptive secondary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block length three consecutive events, fixed seed 20261129.
- No parameter search, alternate horizon, alternative target, feature expansion or date-split changes after result inspection.

## Frozen decision rule

- **Promising / BACKTESTED:** at least 30 forecasts in each period; augmented RMSE improves in both validation and test; and the 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented loss is above zero.
- **Rejected:** augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- **Inconclusive:** all other outcomes, including inadequate coverage, fewer than 30 forecasts in either period, mixed RMSE results or confidence intervals crossing zero.
- Even a promising forecast remains BACKTESTED only. It is not independently validated, causal, or a tradable yield-curve strategy.

## Structural breaks and limitations

- KC PRS uses Eurodollar futures options before 2023 and SOFR futures options from 2023 onward. Validation is the earlier Eurodollar-options regime; the frozen 2023+ test is the SOFR-options regime. A regime change limits direct comparability and must be stated.
- FRED current vintages are used; historical point-in-time revisions are not reconstructed.
- DGS2 is a market-yield proxy, not the realized federal funds rate. It embeds term-premium and other market components.
- The KC PRS is a one-year-ahead option-implied risk-asymmetry measure; this experiment tests only incremental predictive information for a 21-session DGS2 change.
- No causal inference, trading P&L, execution-cost model, live order, capital deployment or strategy promotion is authorized.
- Do not commit raw FRED source rows; retain hashes, coverage, aggregate metrics and reproducible code.

## Empirical disposition

- **Final status:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule.
- **Completed real-data backtest:** yes.
- **Data scope:** KCPRS/DGS2/DGS10 daily current FRED vintages; common source envelope 1989-04-03 to 2026-11-24; 425 accepted non-overlapping events; validation 2018-2022 n=56; test 2023 onward n=44.
- **Summary:** validation/test n=56/44; RMSE improvement=-7.8081%/-4.5637%.
- **Report:** [../reports/sessions/2026-11-26/2026-11-26T033358Z_session-kcprs-policy-skew-45749415970.md](../reports/sessions/2026-11-26/2026-11-26T033358Z_session-kcprs-policy-skew-45749415970.md).

Forecasting screen only. No causal, trading, profitability or deployment claim.
