# Preregistered experiment: relative U.S. spot BTC/ETH ETF flow pressure and ETH/BTC returns

- **Hypothesis ID:** QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01
- **Status:** SOURCE_ACCEPTED — read-only source preflight PASS (run 45996756282); frozen hashes below; model implementation and backtest now authorized under the unchanged preregistration.
- **Preregistration freeze:** 2026-11-27T12:08:25Z
- **Difficulty:** MEDIUM
- **Difficulty rationale:** Two independent public ETF-flow histories must be parsed and reconciled, then joined to checksum-verified BTC and ETH Spot archives with a conservative publication embargo. The forecast itself reuses the repository's existing rolling OLS and bootstrap helpers, but cross-source alignment and current-vintage limitations require moderate integration and validation.
- **Timebox start:** 2026-11-27T12:08:25Z
- **Maximum substantive cycles:** 4
- **Implementation deadline:** 2026-11-30T12:08:25Z
- **Final research-conclusion deadline:** 2026-12-02T12:08:25Z
- **Expiry rule:** The earlier of four substantive cycles or five calendar days governs. If either ETF source, its timing/semantics, or the aligned price history fails the frozen preflight, close INCONCLUSIVE/INFEASIBLE without model fitting. If implementation is incomplete by the implementation deadline, close INCONCLUSIVE/INFEASIBLE. If a valid empirical conclusion is not available by the final deadline, close INCONCLUSIVE/INFEASIBLE. Expiry is never a performance NO-GO; no automatic extension, clock reset, gate weakening or same-ID tuning is permitted.

## 1. Falsifiable hypothesis

A strictly lagged relative flow-pressure measure from U.S. spot Bitcoin and Ethereum ETFs adds out-of-sample information about the next five Binance Spot UTC daily ETH/BTC log returns beyond prior BTC and ETH price dynamics and the common component of BTC/ETH ETF flows.

For each asset, calculate a trailing, prior-only 60-observation flow z-score:

`z^{BTC}_t = (F^{BTC}_t - mean(F^{BTC}_{t-60:t-1}))/sd(F^{BTC}_{t-60:t-1})`

`z^{ETH}_t = (F^{ETH}_t - mean(F^{ETH}_{t-60:t-1}))/sd(F^{ETH}_{t-60:t-1})`

The frozen flow features are:
- Common flow pressure: `(z_BTC + z_ETH) / 2`.
- Relative flow pressure: `z_ETH - z_BTC`.

The directional expectation is positive: stronger standardized ETH ETF flows relative to BTC ETF flows should precede ETH outperformance and a rising ETH/BTC ratio.

## 2. Novelty and literature boundary

The repository registry contains no prior hypothesis using the relative difference between U.S. spot BTC and ETH ETF flow shocks to forecast the ETH/BTC ratio. Existing work has studied aggregate ETF flows and BTC/ETH prices or returns, so this project does **not** claim that ETF flows or their relationship with crypto prices are novel.

Relevant prior work:
- Mazur and Polyzos, *Spot Bitcoin ETFs: The Effect of Fund Flows on Bitcoin Price Formation* (working paper; examines aggregate BTC ETF flows and BTC price formation): https://papers.ssrn.com/abstract=5452994
- Oefele (2025), *One year of bitcoin spot ETPs: A brief market and fund flow analysis*, Economics Letters 250, 112304; reports that BTC price changes are a primary driver of ETF flows: https://doi.org/10.1016/j.econlet.2025.112304
- Ashish (2026), *The Impact of Bitcoin ETF Flows on Price Dynamics: Evidence from the Post-Approval Era*, Concordia University thesis; reports no incremental BTC-return predictability from public flows after past returns in its 2024–2025 sample: https://spectrum.library.concordia.ca/id/eprint/997714/
- Chena and Yang (2026), *Who leads in price discovery? Trading frictions and return transmission in spot Bitcoin ETFs*, Applied Economics Letters; examines intraday price discovery within BTC ETFs: https://doi.org/10.1080/13504851.2026.2621132

The bounded contribution here is different: relative BTC-versus-ETH ETF flow pressure, a five-calendar-day information embargo, and a cross-asset ETH/BTC return target, with past BTC/ETH returns and common flow pressure as controls.

## 3. Source-feasibility protocol — required before model implementation

Public source pages:
- Farside Bitcoin ETF all-data table: https://farside.co.uk/bitcoin-etf-flow-all-data/
- Farside Ethereum ETF all-data table: https://farside.co.uk/ethereum-etf-flow-all-data/
- Binance Vision official Spot 1d UTC archives and SHA-256 sidecars for BTCUSDT and ETHUSDT.

Farside identifies the tables as generated automatically and disclaims liability for data errors. The tables are aggregator data, not official issuer filings or a point-in-time archive. The source pages can update and historical values may be revised. The experiment is therefore a current-vintage forecast screen, not proof that the same observations were available at the historical decision time.

Frozen source gates:
1. Parse the full historical tables; validate date uniqueness, fund-column/Total schema, finite numeric values, and reconciliation of each Total to its numeric fund components within one-decimal rounding tolerance.
2. Treat a dash as missing, not zero. Exclude rows with no numeric fund observations (including all-dash market holidays). Do not impute missing fund or daily flow values.
3. Require BTC and ETH flow dates to align from the ETH series inception (2024-07-23) through the eligible cutoff, with at most five unmatched dates and at least 450 common observations.
4. Apply a fixed **five-calendar-day embargo** to each U.S. ETF trade date before using the flow observation. This is a conservative delay, not a verified historical publication timestamp.
5. Freeze a common flow-panel SHA-256 over sorted `date|BTC total|ETH total` rows through the eligible cutoff.
6. Retrieve BTCUSDT and ETHUSDT Spot 1d UTC monthly/daily archives from 2024-07-01 through the latest common published daily candle, verify every official .CHECKSUM sidecar, and require exact daily continuity for both symbols.
7. Freeze each symbol's archive-manifest SHA-256 and the common price end date. The admitted model run must reproduce the frozen flow-panel and archive-manifest hashes exactly. If Farside revises an eligible historical row or Binance archive hashes/coverage differ, fail closed; do not silently refresh the preregistered sample.
8. The source-preflight workflow is read-only and must not fit a model, calculate forecast metrics, or run a backtest.

## 4. Frozen signal, target and event construction

- Flow source dates: common BTC and ETH ETF U.S. trading dates from 2024-07-23 onward.
- Flow observation becomes eligible only after five full calendar days.
- Signal anchor: Binance UTC daily close dated five calendar days after the ETF flow date.
- Target: cumulative log return of the ETH/BTC close ratio over the next five complete UTC daily candles, multiplied by 10,000 to express basis points. The signal-anchor day's return is excluded.
- Flow z-scores: each day's total ETF net flow in USD millions, standardized against the mean and population standard deviation of the preceding 60 valid observations for that same ETF market. The current flow is excluded from its own normalization window. Zero/undefined trailing standard deviation blocks that observation.
- Event schedule: every second common valid ETF flow date after the 60-observation warm-up. Five-day target windows can overlap; training observations are included only after their target end date is strictly before the current signal date. The paired-loss bootstrap uses five-event circular blocks to account for overlapping targets and serial dependence.
- No forward fill, backfill, holiday imputation, missing-flow-as-zero conversion or cross-source date substitution.

## 5. Frozen forecast model and decision rule

Baseline features:
- Prior-five-session ETH/BTC cumulative log return.
- Prior-20-session ETH/BTC cumulative log return.
- Log of prior-20-session ETH/BTC realized variance.
- Prior-five-session BTC cumulative log return.
- Prior-five-session ETH cumulative log return.
- Common ETF flow pressure.

Augmented model: the same baseline plus exactly one feature, relative ETF flow pressure.

- Rolling training window: 65 most recent fully matured events.
- Estimator: repository rolling standardized OLS helper with its fixed 1e-8 coefficient ridge stabilization; no hyperparameter tuning.
- Validation signal dates: 2025-01-01 through 2025-12-31.
- Test signal dates: 2026-01-01 through the frozen last eligible signal date.
- Minimum accepted forecasts: 45 validation and 60 test.
- Primary metric: RMSE of five-session ETH/BTC cumulative return in basis points.
- Paired test-loss inference: 2,000 circular moving-block bootstrap replications, block size five events, seed 20261127.

Disposition:
- **PROMISING:** validation and test RMSE both improve, and the paired test-loss 95% confidence interval's lower bound is above zero. This remains a forecast-screen result, not a trading strategy.
- **REJECTED:** validation and test RMSE both worsen, and the paired test-loss 95% confidence interval's upper bound is below zero.
- **INCONCLUSIVE:** every other outcome, including insufficient sample size, source mismatch or uncertain inference.

No alternate feature, lag, normalization window, event spacing, target horizon, split, model or acceptance threshold is permitted under this hypothesis ID.

## 6. Limitations and prohibitions

- Farside's current-vintage table has no historical as-of snapshots or verified publication timestamps. A five-calendar-day embargo reduces partial-row risk but does not establish exact historical availability.
- ETF net flows are creations/redemptions reported by an aggregator; they are not ETF secondary-market trading volume, exchange spot order flow or direct evidence of BTC/ETH purchases at a specific timestamp.
- The ETH ETF sample begins 2024-07-23, limiting the history and the number of independent regimes.
- Forecasting ETH/BTC returns is not a trading P&L. No CAGR, Sharpe, drawdown, profitability, strategy promotion or live deployment claim is allowed.
- No paid data, credentials, raw flow/price observations committed to the repository, live orders or capital deployment are authorized.

## 7. Source-preflight result

**PASS — source acceptance completed before model implementation.** No model was fitted and no forecast/backtest metric was calculated.

- Preflight workflow: [run 45996756282](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45996756282), successful on source commit `8538e696c78a590916145a8c0cbcb313cc901ae1`.
- Retrieved at: 2026-11-27T12:12:55.115464Z.
- Farside BTC all-data table: 722 numeric flow rows, 2024-01-11 through 2026-11-25; 12 fund columns; 10–12 numeric fund components per valid row; raw HTML SHA-256 `d2153caf28eed0b74305a382e66152f77e3a9fc80edf4f640b4c78df006bb316`.
- Farside ETH all-data table: 590 numeric flow rows, 2024-07-23 through 2026-11-25; 11 fund columns; 8–11 numeric fund components per valid row; raw HTML SHA-256 `e139796b2efa57a6de1b221f2a3e6a4a2efbdd5731f81b19bd476b66cbdef5a4`.
- Common reconciled BTC/ETH flow panel: 583 rows, 2024-07-23 through 2026-11-16; zero unmatched dates; cutoff 2026-11-16; panel SHA-256 `4d7d2a8c54b5b6eebbf48631f4641ad24d4692a21dc5d6681beba65e4ae79a18`.
- Fixed five-calendar-day flow embargo; five subsequent daily price bars fully mature by the frozen price end.
- Binance BTCUSDT Spot 1d UTC: 2024-07-01 through 2026-11-26 inclusive; 879 daily rows; 54 checksum-verified monthly/daily archives; zero missing dates; archive-manifest SHA-256 `f70f8a1b01098cee6f8299514888363b04956f66cf122ffae95579b12e08faf5`.
- Binance ETHUSDT Spot 1d UTC: same 879-day coverage; 54 checksum-verified monthly/daily archives; zero missing dates; archive-manifest SHA-256 `0ef90c2cde6888e0ca7512670a84ff2fba17995950870ce847f0d22e635dc314`.
- Frozen common price end date: 2026-11-26.
- Eligible signal anchors: 2024-07-28 through 2026-11-21; the last possible five-day target ends 2026-11-26.
- All numeric fund components reconciled to each published Total within the preregistered one-decimal rounding tolerance. All-dash rows were excluded rather than treated as zero.
- Raw observations were not saved or committed. The source preflight performed no model fitting, forecast evaluation or backtest.

**Admission rule:** the model implementation must reproduce the frozen flow-panel SHA-256, both archive-manifest SHA-256 values, and the exact 2026-11-26 price end date. Any mismatch fails closed; the sample cannot be silently refreshed.

