# Preregistered hypothesis — Ethereum DeFi DEX turnover / ETH realized variance

- **Hypothesis ID:** `QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01`
- **Status:** PREREGISTERED — source feasibility pending
- **Registered:** 2026-11-28T01:42:11Z
- **Frozen UTC:** 2026-11-28T01:42:11Z
- **Timebox start:** 2026-11-28T01:42:11Z
- **Difficulty:** MEDIUM
- **Difficulty rationale:** Requires two independently versioned DeFiLlama daily series, checksummed hourly exchange archives, UTC publication-lag alignment, a new hourly realized-variance target builder, walk-forward inference and independent reconstruction.
- **Maximum substantive cycles:** 4
- **Implementation deadline:** 2026-11-30T01:42:11Z
- **Final research-conclusion deadline:** 2026-12-03T01:42:11Z
- **Expiry rule:** At the earlier of four substantive cycles or the final deadline, publish the strongest defensible conclusion. If source acceptance, implementation or valid execution remains incomplete, close INCONCLUSIVE/INFEASIBLE; never infer a performance rejection from missing data or elapsed time. No automatic extension or same-ID tuning.

## 1. Research question and falsifiable claim

Does a strictly lagged seven-day Ethereum decentralized-exchange turnover ratio add out-of-sample information about the next 24-hour realized variance of ETHUSDT Spot beyond ETH's own recent realized variance and absolute return?

**Mechanism:** DEX notional turnover relative to Ethereum DeFi total value locked (TVL) measures the intensity with which capital is being reallocated through decentralized trading venues. A surge in turnover may indicate elevated position churn, collateral rotation, arbitrage activity or liquidation-related trading that is not fully represented by ETH's own recent price variance. The hypothesis predicts a positive incremental association between higher lagged turnover and subsequent ETH realized variance.

This is materially distinct from the completed DeFiLlama stablecoin-supply/BTC downside study: the predictor is DEX trading activity normalized by deployed DeFi capital, not aggregate stablecoin supply; the target is hourly ETH realized variance, not BTC downside semivariance. It is also distinct from the completed BTC blockspace-feerate and MEXC funding-dispersion screens.

## 2. Frozen source specification and feasibility gates

### DeFiLlama (free, keyless endpoints)

1. Ethereum DEX daily notional volume:
   `https://api.llama.fi/overview/dexs/ethereum?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true`
   Use the documented `totalDataChart` daily aggregate, not protocol-level selection or a post-hoc subset.
2. Ethereum DeFi TVL:
   `https://api.llama.fi/v2/historicalChainTvl/Ethereum`
   Use the documented daily `date` / `tvl` observations.

Official documentation: https://api-docs.defillama.com/llms-free.txt (DEX volume and TVL endpoints). No paid endpoint, account, API key or paid data is authorized.

### Binance Vision (official Spot archives)

- Instrument: ETHUSDT Spot, active trading status required.
- Metadata: `https://data-api.binance.vision/api/v3/exchangeInfo?symbol=ETHUSDT`
- Monthly hourly archive: `https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-YYYY-MM.zip`
- Checksum sidecar: append `.CHECKSUM` to each archive URL.
- Frozen price sample: 2021-01-01 00:00 UTC through 2026-10-31 23:00 UTC inclusive. The end is the last fully completed calendar month available for a checksummed monthly archive at preregistration.

### Source acceptance

- Verify the actual DeFiLlama JSON envelopes and row fields; do not infer schema from documentation examples.
- Require at least 2,000 valid daily observations for each DeFiLlama series in the usable envelope, no duplicate dates, a latest date at or after 2026-10-29, and no gap longer than three calendar days. Never forward-fill missing values. Every seven-day feature window must contain all seven exact dates or be excluded.
- Require ETHUSDT to be the exact active Spot symbol with base asset ETH and quote asset USDT.
- Verify every requested Binance monthly archive against its official SHA-256 sidecar. Parse the actual 12-column hourly-kline schema and timestamp units. Require exactly one observation per expected UTC hour across the frozen price window, no duplicates, no missing hours, valid OHLC relationships, and finite nonnegative volume fields.
- Save response/archive hashes, exact coverage, schemas, retrieval timestamp and source hosts. Do not commit raw archives or raw source observations.
- If the DEX volume endpoint requires a paid plan, is unavailable, or lacks adequate history, stop that source route; do not use a paid key or substitute an unverified scraper. Record the exact failure and close INCONCLUSIVE/INFEASIBLE if no materially different free and authorized source passes within the timebox.

## 3. Signal timing and feature construction

- Forecast origins occur daily at 00:00 UTC.
- The DeFiLlama input window ends two complete UTC dates before the signal date. For signal date (t), use exactly dates (t-8,ldots,t-2), inclusive.
- Frozen feature:
  [
  mathrm{DEXTurnover}_{7d,t}
  =
  rac{sum_{d=t-8}^{t-2}mathrm{EthereumDEXNotionalVolume}_d}
       {rac{1}{7}sum_{d=t-8}^{t-2}mathrm{EthereumDeFiTVL}_d}.
  ]
  The augmented model uses (log(1+mathrm{DEXTurnover}_{7d,t})). Do not alter the seven-day window, chain, numerator, denominator or two-day lag after inspecting outcomes.
- The two-day lag is a conservative publication/revision buffer, not proof of historical point-in-time availability. DeFiLlama historical values may be revised; report this limitation explicitly.
- Price features use only hourly ETHUSDT close-to-close log returns with close timestamps strictly before the signal:
  - trailing 24-hour realized variance;
  - trailing 168-hour realized variance;
  - absolute trailing 24-hour cumulative log return.
- Target is the sum of squared hourly log returns over the next 24 hours, beginning at the signal. Convert to basis-point-squared units before applying (log(1+x)).
- Origins are daily and target windows are exactly 24 hours, so accepted target windows must not overlap. Reject incomplete hourly windows; never synthesize prices or returns.

## 4. Frozen model and chronological evaluation

- Baseline features: `log1p(pre_RV24_bp2)`, `log1p(pre_RV168_bp2)`, and `log1p(abs_pre_return24_bps)`.
- Augmented features: baseline features plus `log1p(DEXTurnover_7d)`.
- Estimator: repository standardized expanding/rolling OLS helper with fixed numerical stabilization (10^{-8}); use a fixed 252-event rolling training window and require at least 180 strictly matured prior events. Do not select hyperparameters from validation or test results.
- Target: `log1p(next_24h_RV_bp2)`.
- Validation: 2023-01-01 through 2024-12-31.
- Test: 2025-01-01 through 2026-10-31.
- Require at least 300 accepted validation forecasts and 300 accepted test forecasts. If either minimum is unmet, disposition is INCONCLUSIVE/INFEASIBLE.
- Compare baseline and augmented RMSE/MAE on identical accepted forecast rows. Record counts, exclusions, training-window sizes, event timestamps, target bounds and all source hashes.
- Paired test-loss inference: circular moving-block bootstrap on baseline-minus-augmented squared error, 2,000 replications, block size 7 daily events, seed `20261128`.

## 5. Frozen decision rules

- **PROMISING:** validation and test RMSE both improve, and the paired test-loss 95% confidence interval lower bound is strictly above zero.
- **REJECTED:** validation and test RMSE both worsen, and the paired test-loss 95% confidence interval upper bound is strictly below zero.
- **INCONCLUSIVE:** every other valid empirical outcome, including mixed split performance or a confidence interval crossing zero.
- **INCONCLUSIVE/INFEASIBLE:** source, coverage, implementation, execution or minimum sample gates fail before a valid empirical result.

A positive forecast result is not causal evidence, trading P&L, a strategy edge or authorization to trade. No strategy promotion, live orders, capital deployment, same-ID retuning, parameter search or validation/test reuse is permitted.

## 6. Timebox execution plan

1. **Cycle 1 — source feasibility:** verify DeFiLlama schemas/coverage and the complete checksummed ETHUSDT hourly archive window.
2. **Cycle 2 — implementation:** build the frozen turnover feature, hourly target, walk-forward model, inference, deterministic tests and guarded workflow.
3. **Cycle 3 — empirical execution:** run one immutable, atomically admitted real-data backtest and persist report, manifest and forecast rows.
4. **Cycle 4 — independent audit:** reconstruct timing, event maturity, metrics, bootstrap and source hashes from persisted artifacts; close the workstream.

The cycle cap and hard deadlines govern even if a workflow queue is delayed. Repairs do not reset the clock. Any materially changed source, lag, feature, target, instrument or model requires a new hypothesis ID and preregistration.
