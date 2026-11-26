# Preregistration — CME Bitcoin futures leveraged-fund gross-short crowding and BTC downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01
- **Registered:** 2026-11-26T12:23:01Z, before implementation and empirical-result inspection.
- **Initial status:** PREREGISTERED.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** the CFTC TFF futures-only dataset and exact CME Bitcoin contract code are documented, and the repository already contains a tested CFTC/Socrata retrieval pattern plus reusable Coinbase BTCUSD and walk-forward functions. Moderate new work is required for the Bitcoin-specific source validation, gross-short crowding feature, publication timing, event construction, tests, workflow and evidence persistence.
- **Timebox start:** 2026-11-26T12:23:01Z.
- **Maximum substantive cycles:** 4 total.
- **Hard implementation deadline:** 2026-11-29T12:23:01Z.
- **Hard final research-conclusion deadline:** 2026-12-01T12:23:01Z.
- **Expiry rule:** the earlier of four substantive cycles or the five-calendar-day limit governs. If source acceptance, implementation or the complete frozen backtest is unresolved at its applicable deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. No automatic extension, silent clock reset, relaxed gate or same-ID retuning. A materially changed position feature, lag, target, market or model requires a new ID and preregistration.

## Research question and falsifiable claim

Does the prior-only percentile of CME Bitcoin futures leveraged-fund gross short positions as a share of total open interest add chronological out-of-sample information about next-five-observation Coinbase BTCUSD downside semivariance beyond Bitcoin's own recent downside semivariance and realized variance?

The mechanism is **institutional short-side/cash-and-carry crowding**, not a claim that leveraged funds are uniformly bearish. CME futures shorts may hedge spot longs in cash-and-carry basis trades, represent directional positions, or serve other strategies. If a large gross short share reflects a crowded derivatives/relative-value position, its unwinding or associated balance-sheet constraints could coincide with changes in BTC downside risk. The test asks whether the measure adds predictive information; it does not identify trader intent or establish causality.

## Novelty and literature boundary

This is materially distinct from the repository's CFTC E-mini S&P 500 and Treasury-futures studies: the instrument is CME Bitcoin futures, the position feature is **gross leveraged-fund short share of open interest** rather than absolute net positioning, and the proposed economic channel is Bitcoin cash-and-carry/basis-trade crowding rather than equity volatility or Treasury basis-trade exposure. It is also distinct from prior BTC macro-predictor screens (broad dollar, real yields, financial stress and Fed balance-sheet changes) because it uses reported derivatives positioning in the same underlying asset.

- CFTC TFF classifications identify Dealer, Asset Manager, Leveraged Money, Other Reportables and Non-Reportables. The CFTC states that classification is based on a trader's predominant business purpose and does not reveal the specific reason for an individual position: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm.
- CFTC Bitcoin CME contract code 133741 is shown in official historical TFF reports: https://www.cftc.gov/sites/default/files/files/dea/cotarchives/2024/futures/financial_lf030524.htm and https://www.cftc.gov/sites/default/files/files/dea/cotarchives/2026/futures/financial_lf100626.htm.
- BitGo Research (2026) discusses how a substantial part of leveraged-fund CME Bitcoin futures shorts can be associated with the cash-and-carry basis trade, while emphasizing that CME is only part of the wider derivatives market: https://www.bitgo.de/research/lower-but-has-crypto-bottomed/. This is contextual motivation, not proof that every short position is a basis trade.
- CFTC TFF Futures Only dataset: https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if.

No first-in-literature claim is made.

## Data feasibility, source and coverage gates

### CFTC Traders in Financial Futures — Bitcoin CME

- Dataset: TFF Futures Only, Socrata resource gpe5-46if: https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if.
- Contract market code: 133741, BITCOIN - CHICAGO MERCANTILE EXCHANGE.
- Required fields: report_date_as_yyyy_mm_dd, contract_market_name, cftc_contract_market_code, open_interest_all, lev_money_positions_short.
- Source API: https://publicreporting.cftc.gov/resource/gpe5-46if.json.
- The report-date history for this contract begins around 2018-04-10. Require at least 350 exact-code rows and first report no later than 90 days after 2018-04-10; otherwise fail closed.
- Require Tuesday report dates for this frozen historical weekly design, unique dates, positive open interest, nonnegative gross short positions not exceeding total open interest, no unexpected market-name substitution, no future dates and a latest report date no more than 21 calendar days stale.
- Retrieve only the exact contract code and selected fields. Persist the response SHA-256, URL, row count and date coverage; do not commit raw CFTC position observations.

### Publication timing and shutdown catch-up

- CFTC reports are generally based on positions as of Tuesday and published Friday at 3:30 p.m. Eastern: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm and https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm.
- Signal date: the first Coinbase BTCUSD daily close on or after report date + 14 calendar days. This fixed lag is deliberately conservative for the historical weekly Tuesday/Friday schedule; the signal is not placed on the report date.
- Exclude report dates 2025-09-30 through 2026-01-20 inclusive from both feature history and events. The CFTC documented a federal-appropriations lapse, delayed releases and a chronological catch-up schedule for this period: https://www.cftc.gov/PressRoom/PressReleases/9138-25 and https://www.cftc.gov/PressRoom/PressReleases/9147-25.
- The CFTC announced a plan to move to twice-weekly publication by the end of 2026: https://www.cftc.gov/PressRoom/PressReleases/9316-26. This frozen experiment remains a historical Tuesday-report study. A changed report cadence must fail closed under the Tuesday validation and requires a new timing specification; do not silently adapt this hypothesis.

### Coinbase BTCUSD spot reference

- FRED series: CBBTCUSD, Coinbase daily BTCUSD price at 5 p.m. Pacific Time: https://fred.stlouisfed.org/series/CBBTCUSD.
- Public CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=CBBTCUSD&cosd=2016-11-25.
- Require at least 3,000 positive finite observations, first observation no later than 2017-03-01, latest observation no more than three calendar days stale, no future date and no calendar gap greater than four days. Individual event windows require every daily return in the pre-history and target to be present; missing returns are never filled or bridged.
- Use the current FRED vintage. Historical ALFRED point-in-time vintages are not reconstructed. Raw CBBTCUSD observations are not committed or redistributed.

## Frozen feature, signal and target

- Position feature: lev_money_positions_short / open_interest_all, using the CFTC TFF Futures Only row for code 133741.
- Crowding rank: rank the current gross-short share against the immediately preceding 52 valid, non-backlog CFTC reports only. Percentile is (less + 0.5 * equal) / 52; the current observation is excluded from its own history. No future reports, interpolation or smoothing are permitted.
- High-crowding event: prior-only percentile at or above 0.90.
- Signal: first CBBTCUSD close on or after the CFTC report date plus 14 calendar days; if the first available close is more than one day after the availability date, skip the event.
- Baseline predictors: log1p of prior-five-observation BTC downside semivariance; log1p of prior-twenty-observation downside semivariance; log1p of prior-twenty-observation total realized variance.
- Augmented model: baseline predictors plus the gross-short-share 52-report prior-only percentile.
- Target: log1p of next-five-observation BTC downside semivariance, measured as the mean of squared negative daily log returns multiplied by 10,000 (percentage-points squared, not annualized).
- Weekly report events must have non-overlapping five-observation target windows. A training target must end strictly before the current signal date.

## Walk-forward model and evaluation

- Baseline and augmented models use the repository's standardized, ridge-stabilized OLS predictor; all scaling and fitting use training observations only.
- Rolling training window: 52 prior mature weekly events.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum acceptance sample: at least 30 forecasts in both validation and test.
- Primary metric: RMSE in log1p downside-semivariance space; MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four weekly events, fixed seed 20261126.
- Secondary event study: difference in mean next-five-observation downside semivariance between high-crowding and other test events, with the same four-event block bootstrap. Require at least five observations in each group.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; the paired test squared-loss 95% lower confidence bound is above zero; and the high-crowding event-study difference is positive with its 95% lower confidence bound above zero.
- REJECTED: augmented RMSE fails to improve in both periods; the paired test squared-loss 95% upper confidence bound is below zero; and the high-crowding event-study difference is nonpositive with its 95% upper confidence bound below zero.
- INCONCLUSIVE: every other outcome, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale sources, cadence changes or incomplete data.
- A promising result remains a forecast-only BACKTESTED screen. It is not independent validation or a trading strategy.

## Limitations and safety

- CFTC trader classes are based on predominant business purpose, not the intent of each position. Gross leveraged-fund shorts can include basis trades, directional shorts and other activity.
- CME Bitcoin futures are not the global crypto derivatives market; offshore perpetual swaps, offshore leverage and spot holdings are not captured.
- The CFTC history is a revised current dataset. Exact historical release timestamps are not available for the full history; the fixed 14-day lag and documented shutdown-backlog exclusion are conservative controls, not point-in-time reconstruction.
- CBBTCUSD is one venue's daily reference price, not a consolidated executable price or a futures P&L series.
- No causal inference, transaction-cost model, trading profitability, live orders, capital deployment or strategy promotion is authorized.
- Do not assign CAGR, Sharpe, Sortino, Calmar or drawdown to this forecast-only result.

## Empirical disposition

- Status: PENDING — no empirical results inspected at preregistration.
- Expiry: publish the strongest defensible conclusion by the hard final research-conclusion deadline; unresolved source or execution failure is INCONCLUSIVE/INFEASIBLE, never a performance NO-GO.
