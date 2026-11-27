# Preregistered Research: Bitcoin Blockspace Fee-Rate Pressure and Downside Semivariance

- **Hypothesis ID:** \`QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01\`
- **Registered:** \`2026-11-27T13:55:51Z\`
- **Difficulty:** MEDIUM
- **Difficulty rationale:** One public Mempool.space three-year block-feerate endpoint, an already verified Binance Vision BTCUSDT Spot 1d UTC source, one prespecified feature, strict UTC aggregation, and the repository's existing walk-forward/paired-loss framework. The main uncertainty is endpoint schema/coverage and the short three-year history; no credentials, paid data, or new execution infrastructure are intended.
- **Timebox start:** \`2026-11-27T13:55:51Z\`
- **Maximum substantive cycles:** 4
- **Hard implementation deadline:** \`2026-11-30T13:55:51Z\`
- **Hard final research-conclusion deadline:** \`2026-12-02T13:55:51Z\`
- **Expiry rule:** If the public source cannot provide the frozen \`avgFee_75\` field, at least 900 distinct UTC dates spanning at least 900 days, and a latest completed date no more than three days stale without payment or access circumvention, close this identity as \`INCONCLUSIVE/INFEASIBLE\`. Do not substitute another endpoint, percentile, metric, or vendor under this ID. If implementation is not complete by the implementation deadline, or a final evidence-based decision is not recorded by the conclusion deadline, close it as \`INCONCLUSIVE/INFEASIBLE\`; do not silently reset the clock or extend the budget.

## 1. Falsifiable question

Does a strictly lagged seven-calendar-day increase in Bitcoin blockspace fee pressure add out-of-sample information about the next five UTC daily BTC downside-semivariance observations, beyond BTC's own recent downside risk, realized variance, and momentum?

The sole augmented predictor is the seven-day change in the logarithm of the daily median of the per-block 75th-percentile transaction feerate:

\[
x_t = \log(1 + \operatorname{median}_{b \in d_{t-1}}(\text{avgFee}_{75,b}))
      - \log(1 + \operatorname{median}_{b \in d_{t-8}}(\text{avgFee}_{75,b}))
\]

The source's \`avgFee_75\` is measured in sat/vB. The daily aggregation is the median across canonical block observations whose timestamps fall within the same UTC date. The seven-day change is computed only after the daily series is complete.

## 2. Economic mechanism and novelty boundary

Blockspace is scarce and transactions compete through fees for inclusion priority. A rise in the upper-quartile block feerate can therefore reflect stronger willingness to pay for scarce settlement capacity or congestion in the transaction-fee market. That network-demand / blockspace-price mechanism is distinct from:

- the previously closed, unadmitted mining-difficulty proposal, which concerned a supply-side retarget/hashrate proxy;
- exchange funding, open interest, ETF flows, stablecoin supply, Wikipedia attention, and macroeconomic rate/liquidity predictors;
- VIX/VXN and options-implied volatility predictors.

This is an incremental forecasting test, not a first-discovery, causal, forced-selling, miner-stress, or directional-price claim. A higher fee rate does not by itself establish market stress or predict a BTC decline.

## 3. Frozen sources and source-acceptance gates

### Predictor source

- Provider: Mempool Open Source Project.
- Endpoint: \`https://mempool.space/api/v1/mining/blocks/fee-rates/3y\`
- Expected response: oldest-to-newest per-block observations containing \`timestamp\`, \`avgFee_0\`, \`avgFee_10\`, \`avgFee_25\`, \`avgFee_50\`, \`avgFee_75\`, \`avgFee_90\`, \`avgFee_100\`, and \`avgHeight\`.
- The official API documentation describes this endpoint as returning historical average block-feerate percentiles for a trailing interval up to three years and warns that rate limits are enforced.
- Source preflight must use one GET only. No retry on HTTP 429; no payment, credentials, proxy, browser scraping, or alternate endpoint.
- Accept only if the schema is exact, timestamps are valid UTC Unix seconds, the \`avgFee_75\` field is finite and nonnegative when present, observations are oldest-to-newest, at least 900 distinct UTC dates span at least 900 days, and the newest completed UTC date is no more than three days stale.
- Aggregate \`avgFee_75\` by UTC date using the median of that day's block observations. A date with no valid fee-rate observation remains missing; do not interpolate or forward-fill.
- The source is a current-vintage historical block-feerate series, not an archived point-in-time mempool snapshot. The one-day feature embargo below is conservative but does not reconstruct historical API publication timestamps.

### Price source

- Binance Vision official Spot \`BTCUSDT\` \`1d\` UTC klines, with archive and sidecar checksum verification.
- Existing accepted source evidence is available in \`reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json\`: 3,388 complete UTC daily candles from 2017-08-17 through 2026-11-25, with verified archive checksums. Reuse this accepted source evidence; do not repeat a full historical price preflight unless the model implementation requires a new date range.

### Frozen sample window

- Predictor history requested: trailing three-year API window, with a minimum accepted span of 900 days.
- Common model window: 2023-11-27 through the latest date for which both a complete Binance UTC daily candle and the required lagged fee-rate feature exist.
- Do not extrapolate or fill before the predictor's first observed date.

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
- Minimum sample: 25 validation forecasts and 60 test forecasts. If either minimum is not met, the performance conclusion is \`INCONCLUSIVE\`.
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
2. The API series is current-vintage and does not provide point-in-time revisions or historical publication timestamps.
3. \`avgFee_75\` is a block-level fee-rate percentile, not a direct mempool backlog, transaction-count, exchange-flow, or investor-positioning measure.
4. Blockspace fee demand may respond to BTC price and volatility. The baseline controls price momentum and realized risk, but residual endogeneity remains.
5. The public API enforces rate limits. One source-preflight request is allowed; an HTTP 429 is recorded without retry.

## 8. Adjacent literature and source references

- Ilk, N., Shang, G., Fan, S., and Zhao, J. L. (2021), “Stability of Transaction Fees in Bitcoin: A Supply and Demand Perspective,” *MIS Quarterly* 45(2), 563–692. The study motivates a supply/demand interpretation of the Bitcoin fee market; it does not test this forward downside-semivariance forecast. https://aisel.aisnet.org/misq/vol45/iss2/5/
- Brown, C. M., Chiu, J., and Koeppl, T. V. (2022), “What Drives Bitcoin Fees? Using Segwit to Assess Bitcoin’s Long-Run Sustainability,” Bank of Canada Staff Working Paper 2022-2. The paper studies congestion and price effects on fee rates; it does not establish incremental market-risk predictability. https://doi.org/10.34989/swp-2022-2
- “Bitcoin blackout: Proof-of-work and the risks of mining centralization” (2026), *Journal of Financial Stability*. Adjacent evidence discusses mempool congestion, fee pressure, and secondary-market responses around a capacity shock; it does not validate this signal or target. https://doi.org/10.1016/j.jfs.2026.101569
- Mempool REST API documentation: https://mempool.space/docs/api/rest
- Mempool API implementation: https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/frontend/src/app/components/block-fee-rates-graph/block-fee-rates-graph.component.ts

## 9. Cycle log

- Cycle 1: freeze this preregistration and perform one read-only source/schema/coverage preflight. No model fit or backtest is permitted in this cycle.
- Cycle 2: only if source preflight passes, implement the frozen parser, event construction, model, and deterministic tests.
- Cycle 3: run the single frozen real-data backtest after deterministic validation.
- Cycle 4: independently audit timing, data provenance, metrics, and the frozen decision rule; persist the final disposition.
