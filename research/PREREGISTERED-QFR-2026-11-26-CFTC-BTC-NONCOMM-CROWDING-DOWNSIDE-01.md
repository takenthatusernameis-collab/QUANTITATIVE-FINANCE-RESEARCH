# Preregistration — CFTC Bitcoin non-commercial net-long positioning and BTC downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-CFTC-BTC-NONCOMM-CROWDING-DOWNSIDE-01
- **Registered:** 2026-11-26T11:54:59Z, before repository implementation and before empirical-result inspection.
- **Status:** FEASIBILITY_CHECKED — preregistered; admitted real-data screen pending.
- **Expected difficulty:** MEDIUM.
- **Difficulty rationale:** the CFTC source is public and keyless, and the repository already has a verified Binance BTC archive path and walk-forward primitives. Moderate work is required for exact contract mapping, publication/backlog timing, source schema validation, event construction, tests, workflow admission and durable evidence persistence.
- **Timebox start:** 2026-11-26T11:54:59Z.
- **Maximum substantive cycles:** 4 total.
- **Hard implementation deadline:** 2026-11-29T11:54:59Z.
- **Hard final research-conclusion deadline:** 2026-12-01T11:54:59Z.
- **Expiry rule:** the earlier of the cycle cap or deadline governs. If source acceptance, implementation or the valid empirical screen is incomplete at expiry, close as INCONCLUSIVE/INFEASIBLE with the exact blocker. Expiry is never a performance NO-GO. No automatic extension, clock reset, gate weakening or identical retry. Any materially changed source, contract, position category, lag, feature, target, market or model requires a new hypothesis ID and timebox.

## Research question and falsifiable claim

Does a strictly lagged CFTC Legacy Futures Only non-commercial net-long share of CME Bitcoin futures open interest add chronological out-of-sample information about next-five-session BTC downside semivariance beyond BTC's own recent downside semivariance and realized variance?

The proposed mechanism is position imbalance/crowding: a large one-sided net position may indicate concentrated directional exposure that is vulnerable to forced repositioning. Because the CFTC non-commercial category aggregates different business purposes and the crowded side can vary across regimes, the predictor remains signed but no coefficient sign is imposed ex ante; the regression estimates its mapping using training data only. This is a predictive claim, not a causal claim.

The CFTC category must not be described as pure speculation, a direct measure of leverage, or a direct measure of liquidation risk. Trader classifications reflect predominant business purpose reported to the CFTC, and the Commission does not publish trader identities or individual position motives.

## Novelty and literature boundary

This is not a claim that CFTC positions have never been used to forecast Bitcoin markets. Shi (2022), *Bitcoin futures risk premia*, studies position-based measures, market microstructure factors and macro variables as predictors of subsequent Bitcoin futures price changes. The narrower question here is whether one transparent CFTC Legacy non-commercial directional-position ratio adds information about next-five-session BTC Spot downside semivariance after controlling for recent BTC downside semivariance and realized variance, using a strict availability buffer and chronological walk-forward evaluation.

- Shi, S. (2022), *Bitcoin futures risk premia*, Journal of Futures Markets, 42(12), 2190–2217. DOI: https://doi.org/10.1002/fut.22373.
- CFTC classification and report-timing documentation: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm.

No first-in-literature claim is made.

## Data feasibility and provenance

### CFTC Legacy Futures Only — Bitcoin CME

- Official dataset: Legacy - Futures Only, Socrata resource `6dca-aqww`: https://publicreporting.cftc.gov/Commitments-of-Traders/Legacy-Futures-Only/6dca-aqww.
- API: https://publicreporting.cftc.gov/resource/6dca-aqww.json.
- Exact contract market code: `133741`, BITCOIN - CHICAGO MERCANTILE EXCHANGE. Official historical report examples confirm this code: https://www.cftc.gov/sites/default/files/files/dea/cotarchives/2021/futures/deacmesf020221.htm.
- Report type: futures only. Do not mix with futures-and-options combined or a different Bitcoin contract.
- Required fields: `report_date_as_yyyy_mm_dd`, `market_and_exchange_names`, `cftc_contract_market_code`, `open_interest_all`, `noncomm_positions_long_all`, and `noncomm_positions_short_all`.
- Report dates in the frozen sample must be Tuesdays. Query only from 2017-12-01 through 2026-11-17 inclusive; 2026-11-17 is the latest Tuesday report available at preregistration. Do not append later observations to this hypothesis.
- Require at least 300 valid report rows, first report no later than 2018-03-01, latest report no more than 21 calendar days old at retrieval, no duplicate report dates, report gaps no greater than 14 days, positive finite open interest, finite non-negative long/short positions, exact market identity and absolute net position no greater than open interest. Fail closed on schema drift, truncation or a violated gate.
- CFTC says reports normally contain positions as of Tuesday and are released Friday at 3:30 p.m. Eastern Time; federal holidays may delay release. Historical release dates are available only for the most recent 13 months. Use a fixed **14-calendar-day** availability buffer after the report date. This is deliberately conservative; it does not reconstruct each historical release timestamp.
- Exclude report dates from **2025-09-30 through 2026-01-20 inclusive** because the CFTC documented an interruption and delayed catch-up publication schedule during this period. Do not apply the ordinary 14-day lag to these reports.
- On 2026-10-27 the CFTC announced a plan to move from weekly to semiweekly COT publication by the end of 2026. At preregistration, the official 2026 release calendar still showed the weekly Friday schedule and the current CFTC page showed reports dated 2026-11-17. This hypothesis is frozen to Tuesday weekly observations through 2026-11-17; it is not an ingestion specification for any later semiweekly series. A future cadence or schema change requires a new hypothesis ID and timebox.
- No credentials or paid data are required. Retain the source-response SHA-256, exact query URL, retrieval time, schema and coverage metadata; do not commit raw source rows.

Official timing and backlog references:
- CFTC COT FAQ and release timing: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm.
- CFTC 2025 backlog announcement: https://www.cftc.gov/PressRoom/PressReleases/9147-25.
- CFTC semiweekly plan announced 2026-10-27: https://www.cftc.gov/PressRoom/PressReleases/9316-26.
- Current 2026 release schedule: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm.

### Bitcoin Spot — BTCUSDT

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC.
- Source: official Binance Vision monthly/daily Spot kline archives with per-archive `.CHECKSUM` sidecars: https://github.com/binance/binance-public-data.
- Active-market check: https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT.
- Require at least 3,000 completed daily candles, history beginning no later than 2017-08-19, latest completed candle no more than two calendar days old, no missing UTC date, positive finite closes, no future date and verified per-archive SHA-256 sidecars. Exclude the incomplete current candle.
- Do not commit raw BTC observations.

## Frozen feature, signal and target

- CFTC directional net-long share: `(noncomm_positions_long_all - noncomm_positions_short_all) / open_interest_all`. Positive values indicate net-long non-commercial positioning. Spreading positions are excluded from the directional numerator.
- Signal date: BTCUSDT UTC daily close exactly 14 calendar days after the CFTC Tuesday report date. BTC trades continuously, so the exact date must exist in the verified daily price history; never substitute an earlier close.
- BTC log return: `ln(close[t] / close[t-1])`.
- Downside semivariance over n daily returns: `10000 * mean(min(return, 0)^2)`, in percentage-points squared, not annualized.
- Baseline features: log1p of prior-five-session BTC downside semivariance; log1p of prior-twenty-session downside semivariance; log1p of prior-twenty-session total realized variance.
- Augmented model: baseline plus only the CFTC non-commercial net-long share.
- Target: log1p of next-five-UTC-session BTC downside semivariance.
- Weekly signal origins must have fully matured, non-overlapping five-session targets before the next accepted signal. Do not forward-fill CFTC observations, interpolate prices or use future report data.

## Walk-forward model and evaluation

- Baseline and augmented models: ridge-stabilized ordinary least squares; feature standardization is estimated on training data only.
- Rolling training window: 104 prior accepted report events. Every training event's signal and target end must both be strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum: at least 30 forecasts in each period; otherwise INCONCLUSIVE.
- Primary metric: RMSE in log1p downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four consecutive accepted report events, fixed seed 20261126.

## Frozen decision rule

- **BACKTESTED / PROMISING SCREEN:** at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- **REJECTED:** augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- **INCONCLUSIVE:** all other outcomes, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale/irregular source data, source schema changes or incomplete data.
- A promising forecast remains BACKTESTED only. CFTC category semantics, historical release-time uncertainty, single-venue BTC data and lack of independent reconstruction prevent independent validation or strategy promotion.
- No result-dependent retuning, alternate horizons, extra predictors, threshold search or repeat run under this hypothesis ID is authorized.

## Limitations and safety

- Non-commercial is a business-purpose classification, not a pure measure of speculative intent, leverage, liquidation exposure or trader identity.
- CFTC historical release timestamps are not available for the full sample; the fixed 14-day buffer and backlog exclusion are conservative timing controls, not exact point-in-time reconstruction.
- CFTC category composition can change when traders enter, leave or update their business-purpose classification.
- The 2025 publication backlog is excluded; the planned semiweekly transition is outside this frozen sample.
- BTCUSDT is one venue's Spot history; checksummed archives establish file integrity, not consolidated-market representativeness.
- Forecasting only. No live orders, capital deployment, trading P&L, causal claim or deployment authorization.
- Do not assign CAGR, Sharpe, Sortino, Calmar or drawdown to this forecast-only result.

## Empirical disposition

- **Status:** FEASIBILITY_CHECKED — preregistered; admitted real-data screen pending.
- **Completed real-data backtest:** no.
- No empirical result has been inspected. The first admitted workflow must run deterministic tests before source retrieval, apply every frozen acceptance gate and persist either a valid empirical result or an explicit INCONCLUSIVE/INFEASIBLE blocker.


## Pre-admission clarification — 2026-11-26

Before the first admitted real-data run and before any empirical result was inspected, the mechanism wording was clarified to match the frozen model: the signed non-commercial net-position share is tested for incremental predictive information without imposing a positive coefficient sign. The CFTC classification does not justify a universal long-side-only directional restriction. No data, feature, horizon, model, split, timebox or decision threshold changed.
