# Preregistered hypothesis — Ethereum DeFi DEX turnover / ETH realized variance

- **Hypothesis ID:** `QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01`
- **Status:** COMPLETED — INCONCLUSIVE; Cycle 3 empirical backtest and Cycle 4 independent audit completed at 2026-11-28T02:58:40Z
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
   `https://api.llama.fi/overview/dexs/ethereum?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume`
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
- Daily hourly gap-repair archive, only for dates with monthly gaps: `https://data.binance.vision/data/spot/daily/klines/ETHUSDT/1h/ETHUSDT-1h-YYYY-MM-DD.zip`, with the same `.CHECKSUM` sidecar. Add only missing hourly rows, and only when every overlapping close matches the monthly archive within the frozen numerical tolerance; preserve unrepaired gaps.
- Frozen price sample: 2021-01-01 00:00 UTC through 2026-10-31 23:00 UTC inclusive. The end is the last fully completed calendar month available for a checksummed monthly archive at preregistration.

### Source acceptance

- Verify the actual DeFiLlama JSON envelopes and row fields; do not infer schema from documentation examples.
- Require at least 2,000 valid daily observations for each DeFiLlama series in the usable envelope, no duplicate dates, a latest date at or after 2026-10-29, and no gap longer than three calendar days. Never forward-fill missing values. Every seven-day feature window must contain all seven exact dates or be excluded.
- Require ETHUSDT to be the exact active Spot symbol with base asset ETH and quote asset USDT.
- Verify every requested Binance monthly archive against its official SHA-256 sidecar. Parse the actual 12-column hourly-kline schema and timestamp units. Require all observed open times to lie on the UTC hourly grid, no duplicates, valid OHLC relationships and finite nonnegative volume fields. The source may contain sparse missing hours only when they are at most 24 in total, at most 0.1% of expected hours, and no more than four consecutive hours; enumerate every gap. Do not fill or interpolate. The model must exclude any forecast whose 24-hour target or 24/168-hour trailing price window contains a missing hourly return. Require at least 300 accepted forecasts in each chronological split after exclusions.
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


## Initial pre-result data-integrity amendment — 2026-11-28T02:00:00Z

The source-only preflight found 14 missing hourly ETHUSDT bars in the 51,120-hour frozen Binance Vision monthly sample. The official daily archive was also checked for the first affected date and contained the same missing hour. No model, validation or test outcome had been inspected when this amendment was made.

The original global gap-free requirement is therefore replaced by the sparse-gap policy in Section 2: at most 24 missing hours, at most 0.1% of expected hours, and no more than two consecutive missing hours. Every gap is retained in provenance. No price, close or return is forward-filled, interpolated, or synthesized. The model excludes any origin whose 24-hour target, 24-hour trailing baseline window, or 168-hour trailing baseline window requires a missing hourly return. The 300-forecast minimum in each split remains binding after exclusions.

This is a pre-result data-integrity amendment to accommodate the observed official archive coverage; the instrument, DeFiLlama predictor, two-day publication lag, feature windows, target, model, chronological splits, bootstrap and decision rules are unchanged. If the sparse-gap limits or post-exclusion sample minima fail, the hypothesis closes INCONCLUSIVE/INFEASIBLE.


## Superseding pre-result sparse-gap amendment — 2026-11-28T02:10:10Z

The complete source-only preflight at 2026-11-28T02:07:22Z verified all 70 monthly ETHUSDT hourly archives and their SHA-256 sidecars. It found 14 absent bars among 51,120 expected hours (0.0274%), with a maximum run of four consecutive missing hours. Seven additional official daily archives were also checksum-verified for the affected UTC dates. Each daily archive reproduced the same missing timestamps; zero rows could be repaired, and no monthly/daily close mismatches or daily-archive download failures occurred. The gaps are: 2021-02-11 04:00 UTC; 2021-03-06 02:00 UTC; 2021-04-20 02:00–03:00 UTC; 2021-04-25 05:00–07:00 UTC; 2021-08-13 02:00–05:00 UTC; 2021-09-29 07:00–08:00 UTC; and 2023-03-24 13:00 UTC.

The initial two-consecutive-hour cap is superseded by a maximum of **four consecutive missing hours**. The total-missing limit (24), missing-fraction limit (0.1%), and all other source, feature, model, sample-count and decision gates remain unchanged. This narrowly accommodates the verified official archive's observed maximum gap; it does not fill or infer any missing price. Every missing timestamp remains in the source manifest. No price, close or return is forward-filled, interpolated or synthesized. Any forecast whose 24-hour target, 24-hour trailing baseline window or 168-hour trailing baseline window requires a missing hourly return must be excluded. The 300-forecast minimum in each split remains binding after exclusions.

The gap set is confined to 2021 and one isolated hour in 2023; no gap lies in the frozen 2025–2026 test period. The 2023 gap still invalidates every affected validation origin/window under the strict exclusion rule. The DeFiLlama DEX and TVL series each passed their 2,128-row daily coverage checks, and Binance metadata confirmed active ETHUSDT Spot trading. No model fit, validation/test metric, forecast row or empirical outcome had been inspected when this amendment was made. This is a source-integrity amendment only; it does not change the hypothesis, instrument, predictor, lag, feature windows, target, estimator, chronological splits, bootstrap or decision rules.

## Source-feasibility disposition — 2026-11-28T02:13:41Z

Cycle 1 is complete: the read-only source-preflight workflow [run 46097000508](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46097000508) passed on source commit aa59537e1a7938bddd8b4fd0b64bad4c73f271be. Its GitHub artifact ID is 15243896011; the artifact ZIP SHA-256 is 5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49; the extracted preflight.json SHA-256 is 1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6. The backtest workflow is pinned to this exact artifact, source commit and manifest hash.

DeFiLlama returned 2,128 daily DEX-volume observations and 2,128 daily Ethereum TVL observations each from 2021-01-01 through 2026-10-29, with maximum adjacent-date gap one day. Frozen-window canonical SHA-256 values are DEX 8fdf8625a388b619d4426791f14a78bbb6bb3820ee535aa60cbd82a67c8e0696 and TVL 0d21055246d26652c684847a5c85ff1abbe7ab4e3010a1e6e8ca8f2e77cac7fe. Binance metadata confirmed active ETHUSDT Spot trading. All 70 monthly archive and all seven daily gap-check archive checksums verified. The combined hourly close series contains 51,106 of 51,120 expected bars; 14 remain missing (0.0274%), maximum consecutive run four hours. The daily archives independently reproduced all seven gap dates and repaired zero rows. Canonical close SHA-256: 64b2b592fe094ed576ec8582fe788d146293afabc2274bbb83650d0cd34c5a6c.

No raw observations were saved. All missing bars remain explicit; every forecast whose target, 24-hour trailing baseline window or 168-hour trailing baseline window requires a missing hourly return is excluded. The post-exclusion minimum remains 300 validation and 300 test forecasts. This source-feasibility pass is not a model fit or backtest. Cycle 2 implementation is now in progress; the frozen specification and decision rules are unchanged.

## Cycle 4 independent audit and closure — 2026-11-28T02:58:40Z

The single admitted empirical run [46098199964](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46098199964) completed successfully on immutable source commit `024f91ba2e8ec039bc53d9ccd1b3540c3fb4d350`. All job steps succeeded, including deterministic tests, exact accepted-preflight-artifact verification, frozen-source refetch, the one preregistered walk-forward forecast and evidence persistence. Admission guard [46098199972](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46098199972) passed.

Cycle 4 independently re-parsed all 1,392 persisted forecast rows (723 validation, 669 test). There were no duplicate forecast dates. Every signal timestamp matched 00:00 UTC; every target began at the signal and ended exactly 24 hours later; all targets were globally non-overlapping. Every DEX/TVL feature window was exactly t−8 through t−2. Every forecast used 252 training events, with the final training target strictly matured before the signal. All stored squared errors were reproduced from the target and prediction columns. The eight absent validation origins were exactly 2023-03-24 through 2023-03-31, consistent with the isolated 2023-03-24 13:00 UTC missing hourly return contaminating the 168-hour trailing feature. No test forecast dates were missing.

Independent metrics:

| Split | Baseline RMSE | Augmented RMSE | RMSE improvement | Baseline MAE | Augmented MAE |
|---|---:|---:|---:|---:|---:|
| Validation | 0.887682530 | 0.891535848 | −0.434087% | 0.687199397 | 0.692695988 |
| Test | 0.879506070 | 0.880798316 | −0.146929% | 0.671567923 | 0.674836322 |

The 669 test paired loss differences were independently decoded and bootstrapped with NumPy `default_rng(20261128)`, 2,000 circular moving-block replications, block size seven, the same wraparound construction and quantile method. The independent result exactly reproduced the manifest: mean baseline-minus-augmented squared loss `−0.0022747450467157683`, 95% interval `[−0.011202103506137949, +0.006070043616085962]`, bootstrap fraction positive `0.305`.

The frozen decision rule is unchanged. Both validation and test RMSE worsen, but REJECTED additionally requires the paired-loss 95% interval upper bound to be strictly below zero. The interval crosses zero, so the final disposition is **INCONCLUSIVE**. This is a forecast-only result, not causal evidence, P&L, tradability, a strategy edge or authorization to trade. No same-ID retuning is permitted.

The refetched raw DeFiLlama TVL response hash differs from the preflight raw response hash; however, the canonical hash and coverage over the frozen sample window match exactly. No in-window TVL value changed. This does not remove the current-vintage/revision caveat; the two-day lag is not proof of point-in-time availability.

The original MEDIUM four-cycle cap and deadlines were not extended or reset. Cycles 1–4 are complete; the hypothesis is **CLOSED — INCONCLUSIVE**. The daily 2026-11-28 backtest KPI had already been met by the separate MEXC funding-dispersion/BTC-RV backtest [46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442); this DEX run was additional research output.
