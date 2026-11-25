# Preregistration — lagged 10-year TIPS real-yield changes and Bitcoin five-day returns

- **Hypothesis ID:** QFR-2026-11-25-BTC-REAL-YIELD-SHOCK-01
- **Registered:** 2026-11-25T13:25:00Z, before empirical result inspection.
- **Status:** FEASIBILITY_CHECKED — official public daily series and source semantics identified; full row-level coverage, freshness and empirical acceptance remain subject to fail-closed workflow checks.
- **Timebox start:** 2026-11-25T13:25:00Z.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** two public daily series, different seven-day crypto versus five-day Treasury calendars, strict prior-date alignment, signed real-yield observations, non-overlapping five-session targets, rolling OLS and block-bootstrap inference. No credentials, paid data or new venue access.
- **Maximum budget:** 4 substantive agent cycles.
- **Implementation deadline:** 2026-11-28T13:25:00Z.
- **Final research conclusion deadline:** 2026-11-30T13:25:00Z.
- **Expiry rule:** if source acceptance, implementation or the frozen empirical decision is incomplete at expiry, close INCONCLUSIVE/INFEASIBLE with the exact blocker. Do not reset the clock, extend automatically, weaken gates or tune under this ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** changes in long-horizon inflation-adjusted Treasury yields alter the real discount rate and the opportunity cost of holding non-yielding assets. A rise in the 10-year TIPS real yield may therefore tighten financial conditions and reduce demand for duration-sensitive speculative assets, including Bitcoin. This is a real-rate/discount-rate channel, not the nominal broad-dollar channel tested in the separate rejected BTC/USD-index study.

**Claim:** the five-observation change in the 10-year TIPS real yield, measured from the latest observation strictly before the Bitcoin signal date, adds out-of-sample information about the next-five-Bitcoin-session return beyond Bitcoin's own trailing five- and twenty-session momentum and realized volatility. The expected coefficient is negative, but the frozen decision is based on forecast performance and paired-loss inference, not coefficient sign alone.

This is a predictive-forecast hypothesis, not a causal claim, hedge conclusion, directional trading strategy or tradable P&L. It is materially distinct from the repository's broad-dollar, Treasury auction, CFTC positioning and VIX term-structure hypotheses.

## Data sources and acceptance

1. **Bitcoin USD daily close:** FRED series CBBTCUSD, sourced from Coinbase; https://fred.stlouisfed.org/series/CBBTCUSD. FRED identifies this as daily, seven-day data and states that observations are as of 5 PM Pacific Time. The source is copyrighted; do not redistribute raw observations.
2. **10-year TIPS real yield:** FRED series DFII10, sourced from the Board of Governors of the Federal Reserve System, H.15 Selected Interest Rates; https://fred.stlouisfed.org/series/DFII10. FRED identifies it as a daily, not-seasonally-adjusted yield quoted in percentage points. Values may be negative or zero.

Fetch CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25. Require at least 1,500 valid observations per series, finite values, unique dates, positive BTC prices, history beginning no later than 2017-03-01, and latest observations within four calendar days of one another. Require the latest DFII10 observation to be strictly before each BTC signal and no more than four calendar days old. Require five prior yield changes within a 14-calendar-day span. Do not forward-fill either series. Store source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes; do not commit raw source data.

## Timing, features and target

- Bitcoin signal dates are its exact daily observation dates.
- For each Bitcoin signal date t, use the most recent DFII10 observation with date strictly less than t. Never use a same-date yield observation, even if it exists.
- Real-yield change is 100 × (DFII10[d] − DFII10[d−5]) basis points, where d is the latest eligible prior observation and d−5 is five observed Treasury-yield observations earlier. DFII10 is quoted in percentage points; multiplying the difference by 100 converts percentage points to basis points. Do not use a ratio or log return because the yield can be zero or negative.
- Bitcoin baseline features, all known at the signal close: trailing 5-session log return in percent; trailing 20-session log return in percent; trailing 5-session realized volatility in percent; trailing 20-session realized volatility in percent.
- Augmented model adds only the lagged five-observation real-yield change in basis points.
- Target is 100 × log(BTC[t+5] / BTC[t]), using the next five observed daily Bitcoin closes.
- Sample signal origins every six Bitcoin observations. This prevents target overlap when the next five closes are used. Require all 20 preceding daily returns and all five future returns to be valid; do not bridge missing Bitcoin calendar days or impute values.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE of five-session Bitcoin log returns in percentage points; report MAE, directional accuracy and OOS R-squared versus the period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size 4 events, fixed seed 20261127.

## Frozen decision rule

A promising incremental forecast result requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower bound for baseline-minus-augmented squared error is above zero.

Reject only if both validation and test RMSE fail to improve and the paired-loss bootstrap upper bound is below zero, indicating evidence that the augmented model is worse. All other outcomes are INCONCLUSIVE. A BACKTESTED result is not independent validation, a causal claim, an investment recommendation, a hedge finding or permission to deploy live. Do not tune features, horizons, event spacing, model window, date splits or bootstrap settings after seeing results.

## Literature rationale and novelty boundary

- Jareño, González and Almansa (2025), “Interest rate sensitivity of traditional, green, and stable cryptocurrencies: A comparative study across market conditions,” *Quantitative Finance and Economics*, DOI: https://doi.org/10.3934/QFE.2025004. The study decomposes nominal rates into real yields and inflation expectations and reports regime-dependent cryptocurrency rate sensitivity; it motivates, but does not validate, this strict-lag incremental forecasting test.
- Smales (2023), “Cryptocurrency as an alternative inflation hedge?”, *Accounting & Finance*, DOI: https://doi.org/10.1111/acfi.13193. The reported Bitcoin response to inflation-expectation changes is conditional, supporting a conservative test of a distinct real-discount-rate channel rather than a blanket macro-beta assumption.

The bounded contribution is a strict-lag, non-overlapping, rolling out-of-sample forecast test using a public 10-year TIPS real-yield series. It is not a claim of first discovery.

## Explicit limitations

- Coinbase CBBTCUSD observations are stated by FRED to be as of 5 PM Pacific Time and are copyrighted; raw observations must not be redistributed.
- DFII10 is a daily U.S. business-day series. The strict prior-observation rule deliberately excludes same-date values and can leave weekend BTC signals using the latest prior business-day close.
- DFII10 is a market yield, not a direct measure of every investor's expected real return; it embeds TIPS market conventions and risk/liquidity premia.
- FRED observations can be revised; this experiment uses the retrieved current vintage and does not reconstruct historical release vintages.
- The five-session forecast is not a trading strategy. No transaction-cost model, execution model, causal claim, hedge/safe-haven conclusion or live-deployment conclusion is permitted.
- A statistically promising forecast still requires independent reconstruction and a separately specified instrument-level economic study.
