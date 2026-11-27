# Preregistered Research: Bitcoin Blockspace Fee-Rate Pressure and Downside Semivariance

- **Hypothesis ID:** `QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01`
- **Status:** IMPLEMENTATION_READY — implementation commit `2930958302d11ad609bb53a2299952436a7f4b86`; 13 deterministic model tests, source-preflight regression tests and full workflow-admission suite passed in CI run [#46024683649](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024683649); empirical backtest pending.
- **Registered:** `2026-11-27T13:55:51Z`
- **Difficulty:** MEDIUM
- **Difficulty rationale:** One public Mempool.space three-year block-feerate endpoint, an already verified Binance Vision BTCUSDT Spot 1d UTC source, one prespecified feature, strict UTC aggregation, and the repository's existing walk-forward/paired-loss framework. The main uncertainty is endpoint schema/coverage and the short three-year history; no credentials, paid data, or new execution infrastructure are intended.
- **Timebox start:** `2026-11-27T13:55:51Z`
- **Maximum substantive cycles:** 4
- **Hard implementation deadline:** `2026-11-30T13:55:51Z`
- **Hard final research-conclusion deadline:** `2026-12-02T13:55:51Z`
- **Expiry rule:** If the public source cannot provide the frozen `avgFee_75` field, two 12-hour bins per complete UTC date, at least 900 contiguous complete UTC dates, and a latest completed date no more than three days stale without payment or access circumvention, close this identity as `INCONCLUSIVE/INFEASIBLE`. Do not substitute another endpoint, percentile, metric, or vendor under this ID. If implementation is not complete by the implementation deadline, or a final evidence-based decision is not recorded by the conclusion deadline, close it as `INCONCLUSIVE/INFEASIBLE`; do not silently reset the clock or extend the budget.

## 1. Falsifiable question

Does a strictly lagged seven-calendar-day increase in Bitcoin blockspace fee pressure add out-of-sample information about the next five UTC daily BTC downside-semivariance observations, beyond BTC's own recent downside risk, realized variance, and momentum?

For UTC date \(d\), define \(F_d\) as the median of the two 12-hour-bin `avgFee_75` values assigned to that date. Each source row's `avgFee_75` is itself the average of the underlying per-block 75th-percentile transaction feerates within that 12-hour bin. The single augmented predictor is:

\[
x_t = \log(1 + F_{t-1}) - \log(1 + F_{t-8})
\]

The source's `avgFee_75` is measured in sat/vB. The first and last raw UTC dates in the rolling three-year response are partial boundary dates and are excluded. Every included UTC date must contain exactly two 12-hour bins: one timestamped in 00:00–11:59 UTC and one in 12:00–23:59 UTC.

## 2. Economic mechanism and novelty boundary

Blockspace is scarce and transactions compete through fees for inclusion priority. A rise in the upper-quartile block feerate can therefore reflect stronger willingness to pay for scarce settlement capacity or congestion in the transaction-fee market. That network-demand / blockspace-price mechanism is distinct from:

- the previously closed, unadmitted mining-difficulty proposal, which concerned a supply-side retarget/hashrate proxy;
- exchange funding, open interest, ETF flows, stablecoin supply, Wikipedia attention, and macroeconomic rate/liquidity predictors;
- VIX/VXN and options-implied volatility predictors.

This is an incremental forecasting test, not a first-discovery, causal, forced-selling, miner-stress, or directional-price claim. A higher fee rate does not by itself establish market stress or predict a BTC decline.

## 3. Frozen sources and source-acceptance gates

### Predictor source

- Provider: Mempool Open Source Project.
- Endpoint: `https://mempool.space/api/v1/mining/blocks/fee-rates/3y`
- Expected response fields: `timestamp`, `avgFee_0`, `avgFee_10`, `avgFee_25`, `avgFee_50`, `avgFee_75`, `avgFee_90`, `avgFee_100`, and `avgHeight`.
- The official API documentation describes historical block-feerate percentiles for a trailing interval up to three years and warns that rate limits are enforced.
- Source-code inspection of the pinned Mempool implementation confirms that a three-year interval uses a 43,200-second grouping interval. The SQL groups block timestamps by `UNIX_TIMESTAMP(blockTimestamp) DIV div`, averages each block's fee-span percentile within the bin, and reports the average timestamp and height for the bin. Thus the response is **12-hour aggregates**, not one row per individual block.
- `avgFee_75` is the average of the underlying per-block 75th-percentile fee-rate values inside each 12-hour bin. The daily predictor \(F_d\) is the median of the two 12-hour-bin averages on UTC date \(d\).
- The rolling three-year response begins and ends at arbitrary intraday times. Exclude the first and last raw UTC dates. For every remaining date require exactly two rows, with one average timestamp before 12:00 UTC and one at/after 12:00 UTC. Require at least 900 contiguous completed UTC dates after boundary exclusion.
- Timestamps must be valid Unix seconds, ordered oldest-to-newest. `avgFee_75` must be finite and nonnegative when present. Do not interpolate or forward-fill missing dates or half-day bins.
- The newest included completed UTC date must be one to three calendar days before the preflight run date. Do not count the current UTC date as complete, even if the API already returns a partial current-day bin.
- Source preflight must use one GET only. No retry on HTTP 429; no payment, credentials, proxy, browser scraping, or alternate endpoint.
- The source is current-vintage historical block-feerate data, not an archived point-in-time mempool snapshot. The one-day feature embargo below is conservative but does not reconstruct historical API publication timestamps.

### Price source

- Binance Vision official Spot `BTCUSDT` `1d` UTC klines, with archive and sidecar checksum verification.
- Existing accepted source evidence is available in `reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json`: 3,388 complete UTC daily candles from 2017-08-17 through 2026-11-25, with verified archive checksums. Reuse this accepted source evidence; do not repeat a full historical price preflight unless the model implementation requires a new date range.

### Frozen sample window

- Predictor history requested: trailing three-year API window, with a minimum accepted span of 900 contiguous completed dates after dropping the first and last partial UTC dates.
- Common model window: 2023-11-28 through the latest date for which both a complete Binance UTC daily candle and the required lagged fee-rate feature exist.
- Do not extrapolate or fill before the predictor's first completed date.

## 4. Timing, events, and target

- A signal formed at the close of BTC UTC day \(t\) may use only the completed daily fee-rate aggregates for \(t-1\) and \(t-8\). This imposes one full UTC-day embargo.
- The target uses the five BTC daily log returns for \(t+1,\ldots,t+5\):
  \[
  y_t = 10{,}000 \times \frac{1}{5}\sum_{j=1}^{5}\min(r_{t+j},0)^2
  \]
- Events are sampled every six UTC calendar days, so five-session target windows do not overlap.
- No target observation may enter a training fit until all five target candles have closed.

## 5. Frozen model comparison

- **Baseline features:** prior five-day BTC momentum, prior 20-day BTC momentum, prior five-day downside semivariance, prior 20-day downside semivariance, and prior 20-day total realized variance.
- **Augmented model:** exactly the baseline plus the single \(x_t\) blockspace-feerate feature.
- Estimator: standardized expanding/rolling OLS using the latest 65 fully matured prior events. No hyperparameter search, threshold search, or post-holdout feature changes.
- Validation period: signal dates 2025-01-01 through 2025-06-30.
- Test period: signal dates 2025-07-01 through the latest eligible date.
- Minimum sample: 25 validation forecasts and 60 test forecasts. If either minimum is not met, the performance conclusion is `INCONCLUSIVE`.
- Primary metric: RMSE of \(\log(1+y_t)\). Report MAE and directional/level diagnostics only as secondary diagnostics; they cannot override the primary rule.
- Inference: 2,000 paired moving-block bootstrap replications of test squared-loss differences, block length five events, with a fixed seed recorded in the manifest.

## 6. Frozen decision rule

- **GO (research-only):** augmented RMSE improves by at least 1.0% in both validation and test, and the paired test-loss 95% confidence interval for baseline loss minus augmented loss is entirely above zero.
- **REJECTED:** augmented RMSE does not improve in either period and the paired test-loss 95% confidence interval is entirely below zero.
- **INCONCLUSIVE:** every other valid empirical outcome, including mixed validation/test signs, an interval crossing zero, or insufficient sample size.
- **INCONCLUSIVE/INFEASIBLE:** source acceptance fails or the timebox expires without a valid completed backtest.

No result under this ID authorizes live trading, portfolio allocation, or a claim of tradable profitability.

## 7. Known limitations

1. The endpoint is limited to a trailing three-year history, which constrains sample size and regime coverage.
2. The endpoint returns 12-hour aggregates of block-level fee-rate percentiles, not raw per-block observations. The daily median of two bins is a prespecified aggregation, not a true daily median of every block's p75.
3. The series is current-vintage and does not provide point-in-time revisions or historical publication timestamps.
4. `avgFee_75` is a blockspace fee-rate percentile, not a direct mempool backlog, transaction-count, exchange-flow, or investor-positioning measure.
5. Blockspace fee demand may respond to BTC price and volatility. The baseline controls price momentum and realized risk, but residual endogeneity remains.
6. The public API enforces rate limits. One GET per preflight/backtest execution; no retries on HTTP 429.

## 8. Adjacent literature and source references

- Ilk, N., Shang, G., Fan, S., and Zhao, J. L. (2021), “Stability of Transaction Fees in Bitcoin: A Supply and Demand Perspective,” *MIS Quarterly* 45(2), 563–692. The study motivates a supply/demand interpretation of the Bitcoin fee market; it does not test this forward downside-semivariance forecast. https://aisel.aisnet.org/misq/vol45/iss2/5/
- Brown, C. M., Chiu, J., and Koeppl, T. V. (2022), “What Drives Bitcoin Fees? Using Segwit to Assess Bitcoin’s Long-Run Sustainability,” Bank of Canada Staff Working Paper 2022-2. The paper studies congestion and price effects on fee rates; it does not establish incremental market-risk predictability. https://doi.org/10.34989/swp-2022-2
- “Bitcoin blackout: Proof-of-work and the risks of mining centralization” (2026), *Journal of Financial Stability*. Adjacent evidence discusses mempool congestion, fee pressure, and secondary-market responses around a capacity shock; it does not validate this signal or target. https://doi.org/10.1016/j.jfs.2026.101569
- Mempool REST API documentation: https://mempool.space/docs/api/rest
- Mempool implementation: https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/repositories/BlocksRepository.ts#L901-L926
- Mempool three-year interval binning: https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/api/mining/mining.ts#L785-L799

## 9. Preregistration amendment — 2026-11-27T14:08:03Z

The first live source response and the Mempool implementation inspection clarified that the three-year endpoint is 12-hour-binned. The original draft's phrase “per-block observations” was therefore too strong. Before any model implementation or performance-result inspection, the feature was clarified to the median of the two 12-hour-bin averages of per-block p75 values per completed UTC date. The first and last raw dates are excluded because the rolling window cuts through both dates; each included date must have exactly two half-day bins.

This is a source-semantics correction, not a search across percentiles or alternative predictors. The hypothesis, feature direction, target, baseline, model, sample split, decision thresholds, difficulty, and timebox are unchanged. No model fit or backtest has been run.

## 10. Cycle log

- Cycle 1: freeze this preregistration and perform a read-only source/schema/coverage preflight. The first response confirmed the field schema but exposed a boundary-date handling issue; corrected validation must verify 12-hour bins and exclude both partial boundary dates. No model fit or backtest is permitted in this cycle.
- Cycle 2 — COMPLETED 2026-11-27T15:24:45Z: implemented the frozen parser integration, accepted-source checksum reuse, event construction, walk-forward OLS comparison, paired block bootstrap, deterministic regression tests and gated workflow. Implementation commit `2930958302d11ad609bb53a2299952436a7f4b86`; 13 model tests plus source-preflight and full admission-guard suites passed in CI run #46024683649. No empirical backtest ran in that unmarked implementation commit.
- Cycle 3: run the single frozen real-data backtest after deterministic validation.
- Cycle 4: independently audit timing, data provenance, metrics, and the frozen decision rule; persist the final disposition.


## 11. Implementation acceptance — 2026-11-27T15:24:45Z

- **Implementation commit:** [2930958302d11ad609bb53a2299952436a7f4b86](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/2930958302d11ad609bb53a2299952436a7f4b86).
- **Model regression suite:** 13/13 deterministic tests passed, including exact fee-lag timing, next-five-session target construction, six-day event spacing, no target overlap, 65-event training maturity, sample minimums, decision thresholds, deterministic bootstrap and accepted archive-hash matching.
- **Source-preflight regression suite:** passed.
- **Repository admission guard:** all workflow-admission tests passed, including the new workflow's exact job-level gate, immutable triggering commit, narrow path filters, preregistration guard and Bash syntax checks.
- **CI evidence:** [global admission/test run #46024683649](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024683649).
- The research workflow's push event for the unmarked implementation commit was correctly **skipped** in [run #46024683640](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024683640). No empirical source retrieval, backtest or performance-result inspection occurred before this acceptance gate.
- Cycle 2 is complete. Cycle 3 may now execute the single frozen empirical backtest; Cycle 4 remains reserved for independent audit.
