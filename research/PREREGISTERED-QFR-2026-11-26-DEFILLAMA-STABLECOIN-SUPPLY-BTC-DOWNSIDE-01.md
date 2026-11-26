# Preregistration — aggregate stablecoin-supply contraction and BTC downside semivariance

- **Hypothesis ID:** QFR-2026-11-26-DEFILLAMA-STABLECOIN-SUPPLY-BTC-DOWNSIDE-01
- **Registered:** 2026-11-26T15:46:57Z, before source preflight and implementation.
- **Status:** INCONCLUSIVE
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** one public DeFiLlama aggregate historical endpoint, one existing Binance Vision daily Spot archive pipeline, one lagged 14-day supply-growth feature, a five-session downside-semivariance target, a rolling linear forecast, deterministic schema/timing/maturity tests, one dedicated workflow and durable evidence persistence. Existing repository helpers cover checksum-verified Binance archives, downside-semivariance calculations, standardized OLS, forecast metrics and paired block bootstrap. The primary uncertainty is whether DeFiLlama's current historical aggregate series meets the frozen coverage and schema gates.
- **Timebox start:** 2026-11-26T15:46:57Z.
- **Maximum substantive cycles:** 4 total; the earlier of the cycle cap or five-calendar-day limit governs.
- **Hard implementation deadline:** 2026-11-29T15:46:57Z.
- **Hard final research-conclusion deadline:** 2026-12-01T15:46:57Z.
- **Expiry rule:** if the source preflight, implementation, deterministic tests or frozen empirical screen cannot pass by the applicable deadline/cycle cap, close INCONCLUSIVE/INFEASIBLE with exact evidence. No automatic extension, silent reset, relaxed source gate, altered target/horizon or same-ID tuning.

## Research question and falsifiable claim

Does the strictly lagged 14-calendar-day log change in aggregate USD-pegged stablecoin circulating market capitalization add chronological out-of-sample information about next-five-session BTC downside semivariance beyond Bitcoin's own recent downside semivariance and realized variance?

The mechanism is **crypto-native settlement-liquidity contraction**. Aggregate stablecoin supply growth may proxy the amount of dollar-like settlement capacity available inside crypto markets. A contraction may precede reduced liquidity buffers and greater BTC downside risk; expansion is expected to be associated with lower subsequent downside risk. The predictor is the signed log change: positive values mean supply growth, and the preregistered directional expectation is a negative relationship with future downside risk. Aggregate market capitalization is not exchange inflow, net transfer flow, immediately deployable liquidity or proof of investor intent.

## Novelty and literature boundary

This is not a first-in-literature claim. Prior work documents stablecoin/BTC market interaction and connectedness:

- Hoang and Baur, **“How stable are stablecoins?”**, European Journal of Finance (2024), DOI https://doi.org/10.1080/1351847X.2021.1949369, reports stablecoin/BTC co-movement and evidence that stablecoins can increase Bitcoin trading volume.
- Kristoufek, **“On the role of stablecoins in cryptoasset pricing dynamics”** (2022), https://doi.org/10.1186/s40854-022-00343-8, studies stablecoin demand and cryptoasset pricing dynamics.
- Benedetti, Nikbakht and Pastén-Henríquez, **“Quantile-based connectedness in the crypto-stablecoin network across market conditions”** (2026), https://doi.org/10.1016/j.iref.2026.104912, studies daily stablecoin-supply changes and BTC/ETH connectedness across market quantiles.

The bounded contribution here is a preregistered, strictly lagged, rolling out-of-sample forecast test of aggregate supply growth against a five-session BTC downside-semivariance target, beyond BTC's own recent downside-risk baseline. It is not a replication of the cited QVAR or a causal identification design.

## Source feasibility and coverage gates

### DeFiLlama aggregate stablecoin history

- Endpoint: GET https://stablecoins.llama.fi/stablecoincharts/all.
- Use the documented historical all-stablecoin chart response and extract only the date plus totalCirculatingUSD.peggedUSD fields.
- Interpret this field as DeFiLlama's aggregate circulating USD value for tracked USD-pegged stablecoins. Do not mix it with totalMintedUSD, totalBridgedToUSD, non-USD pegs or current-only market-cap snapshots.
- Require a top-level JSON array; valid positive finite USD values; unique UTC calendar dates; at least 1,800 observations within the frozen sample; first coverage on or before 2021-01-01; last coverage on or after 2026-11-22; and no gap greater than two calendar days in the frozen source window.
- Preserve the exact endpoint, retrieval timestamp, response SHA-256, schema, row count, coverage and gap diagnostics. Do not commit raw observations.
- A read-only source-preflight workflow must pass before model implementation begins. If the endpoint schema, history or freshness fails, close INFEASIBLE without building or backtesting the model.

### Binance BTCUSDT Spot reference

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC; use the repository's existing official Vision archive and SHA-256 sidecar verifier.
- Frozen sample: 2021-01-01 through 2026-11-24 inclusive.
- Require exact daily coverage, unique UTC dates, positive finite closes and every official archive checksum to match. Exclude any incomplete current candle.
- Do not commit raw market observations.

## Frozen feature, signal and target

- For a BTC signal date d, use DeFiLlama's aggregate USD-pegged circulating market-cap observations at dates d−2 and d−16.
- Feature: stablecoin_supply_14d_log_change = ln(mcap[d−2] / mcap[d−16]). Both source observations must exist exactly; no forward-fill, interpolation or calendar bridging. A missing feature date causes the event to be skipped and counted.
- Signal: close of Binance BTCUSDT Spot UTC daily candle d. The two-day data embargo is intended to reduce publication-time ambiguity; it does not prove historical point-in-time availability.
- Baseline predictors: log1p of prior-five-session downside semivariance, prior-twenty-session downside semivariance and prior-twenty-session total realized variance.
- Augmented model: the same baseline predictors plus the one frozen stablecoin-supply log-change feature. No additional feature, threshold, interaction, regime split or parameter search is permitted under this hypothesis ID.
- Target: next-five-session BTC downside semivariance, mean(min(r,0)^2) * 10,000, in percentage-points-squared units and transformed with log1p for forecasting.
- Event schedule: one signal every six calendar days; five-session target windows must not overlap.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates 2022-01-01 through 2023-12-31.
- Test: signal dates 2024-01-01 through 2026-11-24.
- Minimum acceptance sample: at least 60 validation and 100 test forecasts. If the frozen source/sample cannot yield these counts, close INCONCLUSIVE/INFEASIBLE; do not move the split or shorten the training window.

## Frozen model and decision rule

- Baseline and augmented forecasts use the repository's standardized, ridge-stabilized OLS predictor; scaling and fitting use training observations only.
- Primary metric: RMSE in log1p downside-semivariance space; MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four events, fixed seed 20261126.
- **PROMISING FORECAST SCREEN:** both validation and test RMSE improve and the paired test squared-loss 95% lower confidence bound is strictly above zero.
- **REJECTED:** both validation and test RMSE worsen and the paired test squared-loss 95% upper confidence bound is strictly below zero.
- **INCONCLUSIVE:** every other result, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale or incomplete sources, or failed implementation gates.
- A promising result remains forecast-only. It is not independent validation, a tradable strategy, causal evidence or a live-trading signal.

## Implementation acceptance

- Parser tests cover the documented DeFiLlama response envelope, UTC timestamp/date conversion, exact totalCirculatingUSD.peggedUSD field, duplicates, malformed values, missing fields and non-positive supply.
- Source tests cover the frozen date range, minimum history, maximum gap and exact two-day/fourteen-day feature alignment.
- Event tests prove that the signal uses only d−2 and d−16 stablecoin observations, the target starts after signal date d, target windows do not overlap, and missing observations are skipped without filling.
- Walk-forward tests prove the 104-event fully matured training requirement.
- Decision-rule, bootstrap, report/manifest and idempotent registry/preregistration update tests pass.
- The complete workflow compiles and runs the model-specific suite plus repository workflow-admission regression suite before empirical source retrieval.
- The triggering commit SHA, source response hash, Binance archive checksums, report and manifest are retained.

## Limitations and safety

- DeFiLlama's aggregate stablecoin market-cap history is a current-vintage aggregate; historical point-in-time revisions and exact publication timestamps are not reconstructed. The two-day lag is a conservative operational embargo, not proof against all revision/look-ahead risk.
- Aggregate supply is not equivalent to exchange-resident liquidity, net inflows, available collateral, trading volume or investor positioning.
- The series aggregates multiple USD-pegged stablecoin designs and chains; issuer-specific and chain-specific heterogeneity is not identified.
- Binance BTCUSDT is one venue's Spot reference series, not a consolidated executable price.
- No raw DeFiLlama or Binance observations are committed or redistributed.
- No causal claim, trading P&L, transaction-cost-adjusted performance, position-sizing rule, leverage return, live order, capital deployment or strategy-promotion conclusion is authorized.

## Source-preflight disposition

- **Status:** PASS — source coverage was revalidated during the empirical run
- **DeFiLlama coverage:** 2021-01-01 through 2026-11-22; 3285 source rows; maximum gap 1 days.
- **DeFiLlama response SHA-256:** 4dcbf029ff5dec668c2a1e7302f5596e7b5faf89a02e127e8f1f1325b91793c0.
- **Binance BTCUSDT:** 2021-01-01 through 2026-11-24; 94 checksum-verified archives.
- Read-only source feasibility preflight: [run 45853947478](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45853947478).

## Empirical disposition

- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule
- **Completed real-data backtest:** True
- **Data scope:** DeFiLlama USD-pegged stablecoin supply 2021-01-01 to 2026-11-22; Binance BTCUSDT Spot 1d UTC 2021-01-01 to 2026-11-24
- **Summary metrics:** {"accepted_events": 355, "forecast_n": 251, "test_n": 175, "test_rmse_improvement_pct": -0.6314251216636976, "validation_n": 76, "validation_rmse_improvement_pct": 2.3150260518596006}
- **Paired test-loss bootstrap:** {"block_size_events": 4, "bootstrap_fraction_positive": 0.369, "ci_95_high_bp2": 0.02871936529767865, "ci_95_low_bp2": -0.05043627055454288, "observations": 175, "observed_mean_baseline_minus_augmented_squared_loss_bp2": -0.00784734509847834, "reps": 2000, "status": "COMPUTED"}
- **Source/implementation blocker:** None
- **Report:** [reports/sessions/2026-11-26/2026-11-26T160524Z_session-stablecoin-supply-btc-downside-45855398478.md](../reports/sessions/2026-11-26/2026-11-26T160524Z_session-stablecoin-supply-btc-downside-45855398478.md)
- **Manifest:** [reports/generated/stablecoin-supply-btc-downside/45855398478-attempt-1/manifest.json](../reports/generated/stablecoin-supply-btc-downside/45855398478-attempt-1/manifest.json)
- Forecast-only; no causal, executable-trading or deployment claim.
