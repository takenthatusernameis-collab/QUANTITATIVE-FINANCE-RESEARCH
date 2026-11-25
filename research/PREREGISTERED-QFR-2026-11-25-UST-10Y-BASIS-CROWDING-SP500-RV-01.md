# Preregistration — leveraged-fund net shorts in 10-year Treasury futures and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-25-UST-10Y-BASIS-CROWDING-SP500-RV-01
- **Registered:** 2026-11-25T19:20:37Z, before empirical result inspection.
- **Status:** PREREGISTERED; one bounded real-data walk-forward screen authorized by this specification.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** one official CFTC TFF contract series plus two public FRED series, a fixed conservative publication lag, an existing rolling OLS/bootstrap harness and no new credentials or paid services.
- **Implementation timebox:** start 2026-11-25T19:20:37Z; deadline 2026-11-29T19:20:37Z.
- **Research conclusion deadline:** 2026-12-01T19:20:37Z.
- **Maximum substantive implementation/research cycles:** 4.
- **Expiry rule:** if accepted source coverage, deterministic implementation or the frozen empirical decision is incomplete by the applicable deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. No automatic extension, reset or tuning under this hypothesis ID.

## Distinct mechanism and falsifiable claim

**Mechanism:** leveraged funds' unusually large net-short exposure in 10-year U.S. Treasury futures may proxy crowded cash-futures basis-trade positioning. A disorderly reduction in those positions could coincide with impaired Treasury intermediation and transmit stress to equity markets. This is a cross-market Treasury-futures positioning channel, not the repository's earlier E-mini S&P 500 crowding, Treasury auction-demand, yield-curve, VIX term-structure or yen-appreciation experiments.

**Claim:** a high, strictly lagged leveraged-fund net-short share of open interest in 10-year U.S. Treasury futures adds out-of-sample information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and the VIX level.

The feature is signed:
- net_short_pct_oi = (leveraged_funds_short - leveraged_funds_long) / total_open_interest.
- Positive values indicate net short positioning.
- Its percentile is computed against the previous 156 non-backlog CFTC reports only; the current report is excluded from its own reference distribution.
- High-crowding events are fixed at the prior-history percentile >= 0.90.

This is a proxy for leveraged-fund positioning, not a direct identification of cash-futures basis trades, investor leverage, repo financing, individual funds or forced liquidation. It is a forecast screen, not a causal claim, trading strategy, basis-trade replication or claim of first discovery.

## Literature and novelty boundary

- Ramaswamy, De Vere, McCormick and Searls (Dallas Fed, July 15, 2025), “How sensitive is the Treasury cash-futures basis trade to funding condition shifts?” describes the large leveraged cash-futures basis trade and its sensitivity to intermediation capacity and funding conditions: https://www.dallasfed.org/research/economics/2025/0715.
- European Central Bank (2024), “Financial stability risks from basis trades in the US Treasury and euro area government bond markets,” discusses how repo disruptions can force basis-trade unwinds and potentially transmit volatility across asset classes: https://www.ecb.europa.eu/press/financial-stability-publications/fsr/focus/2024/html/ecb.fsrbox202405_03~09cad3d18d.en.html.
- The CFTC Traders in Financial Futures report identifies the 10-year U.S. Treasury Note contract as code 043602 and reports Leveraged Funds long/short positions and open interest: https://www.cftc.gov/dea/futures/financial_lf.htm.

The bounded contribution is a strict-lag, non-overlapping, chronological forecast test of one public CFTC positioning proxy against a cash-index volatility target. It does not claim to isolate basis trades or establish a tradable risk premium.

## Data sources and acceptance

1. **CFTC Traders in Financial Futures, futures-only:** public reporting dataset gpe5-46if, exact contract code 043602, report-date field report_date_as_yyyy_mm_dd, market-name field contract_market_name, total open interest open_interest_all, leveraged-fund outright long lev_money_positions_long, and outright short lev_money_positions_short. Official current reports use the label UST 10Y NOTE - CHICAGO BOARD OF TRADE; historical reports may use 10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE. Accept only these 10-year Treasury labels with the exact code.
2. **S&P 500 cash price index:** FRED SP500, daily close; https://fred.stlouisfed.org/series/SP500.
3. **CBOE 30-day implied volatility:** FRED VIXCLS, daily close; https://fred.stlouisfed.org/series/VIXCLS.

Fetch CFTC JSON from https://publicreporting.cftc.gov/resource/gpe5-46if.json using exact-code and date filters. Fetch FRED CSVs from https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}&cosd=2016-11-25.

Acceptance gates:
- CFTC: at least 800 unique weekly observations; first accepted report no later than 2006-09-11; latest report within 21 calendar days of retrieval; exact contract code and an accepted 10-year market label on every row; finite nonnegative outright positions; positive open interest; net position magnitude no greater than open interest.
- FRED: at least 1,500 valid observations per series; unique dates; finite, strictly positive values; history beginning no later than 2017-03-01; latest dates within four calendar days of one another; common recent end no earlier than 2026-11-17.
- Exclude the known CFTC publication-backlog report dates 2025-09-30 through 2026-01-20 from both percentile history and event construction. Do not treat delayed reports as if they were available on their nominal dates.
- Do not forward-fill, interpolate or synthesize observations. Record source URLs, retrieval time, row counts, exact coverage and SHA-256 hashes. Do not commit raw source data.

If any source fails acceptance, do not backtest on an incomplete or stale sample. Record the exact failure and close INCONCLUSIVE/INFEASIBLE rather than relaxing thresholds after seeing the response.

## Timing, feature and target construction

- A CFTC position observation is treated as unavailable until 14 calendar days after its report date. This conservative lag is fixed for the entire sample; the first S&P 500 trading close on or after that availability date is the signal close.
- The 14-day lag is not claimed to reconstruct exact historical CFTC release timestamps. The known publication-backlog interval is separately excluded.
- At each report, compute net-short share of total open interest as defined above. Compute its percentile using only the prior 156 valid, non-backlog reports. Use the mid-rank for ties. Do not include the current report in its own history.
- High crowding is a prior-history percentile of at least 0.90. No other threshold or position transformation is permitted.
- Use the signal-date S&P 500 close and same-date VIX close. The target begins on the next S&P 500 session.
- Baseline predictors: log(1 + pre-event S&P 500 RV5 in percent), log(1 + pre-event S&P 500 RV20 in percent), and log(VIXCLS) on the signal date.
- The augmented model adds only the 156-report net-short percentile.
- Compute realized volatility as the root-sum-square of daily S&P 500 log returns multiplied by 100. Use the preceding five and twenty sessions for baseline features and the next five sessions for the target.
- Do not bridge a price-return gap greater than four calendar days. Drop incomplete windows; do not impute.
- Sample CFTC event origins in chronological order. Keep a target only if its five-session window does not overlap the preceding accepted target window.

## Model and chronological evaluation

- Baseline OLS features: log(1 + pre-event RV5), log(1 + pre-event RV20), log(VIXCLS).
- Augmented OLS features: baseline plus the 156-report net-short percentile.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Primary metric: RMSE in log1p realized-volatility space. Report MAE and out-of-sample R-squared versus the period mean as supplementary metrics.
- Paired test squared-loss inference: 2,000 circular-block bootstrap replications, block size four events, fixed seed 20261125.
- Test-period high-crowding event study: difference in next-five-session realized volatility between high-crowding and other events, with the same 2,000-replication circular-block bootstrap and block size four.

## Frozen decision rule

A promising incremental forecast requires all of:
1. At least 30 validation and 30 test forecasts.
2. Augmented RMSE improves over baseline in both validation and test.
3. The 95% paired squared-loss bootstrap lower confidence bound for baseline-minus-augmented squared error is above zero.
4. High-crowding events have higher mean subsequent realized volatility than other test events, and the event-study 95% bootstrap lower confidence bound is above zero.

Reject only if both validation and test RMSE fail to improve, the paired-loss bootstrap upper confidence bound is below zero, and high-crowding events do not have higher subsequent realized volatility with the event-study upper confidence bound below zero. All other outcomes are INCONCLUSIVE. Do not change the predictor, lookback, lag, event spacing, horizon, date split, training window, bootstrap settings or decision thresholds after seeing results.

Even a promising forecast is not independent validation, a causal finding, a direct basis-trade measurement, an executable strategy, trading P&L or permission to deploy. Any later instrument-level study requires a separate preregistration and realistic execution assumptions.

## Explicit limitations

- CFTC trader categories classify predominant business purpose; leveraged-fund positions are not synonymous with basis-trade positions.
- The 14-day publication lag is conservative, not an exact reconstruction of each historical report's public release time.
- The 2025 publication interruption is excluded; future CFTC publication-calendar changes require a new timing check.
- CFTC positions are weekly and aggregate; they do not identify counterparties, cash Treasury holdings, repo funding, leverage, maturity matching or forced liquidation.
- FRED current-vintage observations are used; historical release vintages are not reconstructed.
- SP500 is a cash price index, not an executable futures series or total-return index.
- Forecasting only: no causal claim, transaction-cost model, tradable strategy, live-deployment conclusion or raw-data redistribution.
