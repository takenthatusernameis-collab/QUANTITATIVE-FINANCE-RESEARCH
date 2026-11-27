# Preregistered Research: U.S. Initial-Claims Deterioration and Bitcoin Downside Semivariance

- **Hypothesis ID:** `QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01`
- **Status:** SOURCE_PREFLIGHT_PENDING
- **Registered:** `2026-11-27T15:34:22Z`
- **Difficulty:** LOW
- **Difficulty rationale:** One public weekly FRED series (ICSA), the repository's already-tested Binance BTCUSDT Spot daily-archive pipeline, one prespecified four-week transformation, and the existing OLS/walk-forward/paired-loss framework. No new credentials, paid data, execution infrastructure or custom simulator are required.
- **Timebox start:** `2026-11-27T15:34:22Z`
- **Maximum substantive cycles:** 2
- **Hard implementation deadline:** `2026-11-28T15:34:22Z`
- **Hard final research-conclusion deadline:** `2026-11-29T15:34:22Z`
- **Expiry rule:** Cycle 1 is limited to the frozen source-feasibility preflight. If ICSA schema, weekly coverage, recency, or the official BTC Spot sample archive fails its stated acceptance checks, close this identity as INCONCLUSIVE/INFEASIBLE without substituting a series or provider. If source feasibility passes, cycle 2 may implement and test the single frozen feature, run one real-data backtest, and independently audit the persisted metrics. If implementation is not complete by the implementation deadline or no evidence-based final disposition is recorded by the conclusion deadline, close INCONCLUSIVE/INFEASIBLE. No automatic extension, timebox reset, parameter tuning or alternate feature under this identity.

## 1. Falsifiable question

Does a strictly lagged four-week log change in U.S. seasonally adjusted initial jobless claims add out-of-sample information about next-five-UTC-session BTC downside semivariance beyond recent BTC downside risk, realized variance and momentum?

For the FRED weekly observation at date (w), define the single augmented predictor:

[
x_w = 100 \, \log\left(\frac{ICSA_w}{ICSA_{w-4}}\right)
]

Positive values indicate rising initial claims over four weekly observations. The observation is embargoed for seven calendar days; the signal is evaluated at the BTCUSDT UTC daily close on (w+7). The seven-day lag is a conservative availability rule, not a reconstruction of historical FRED/ALFRED publication vintages.

## 2. Novelty boundary

The information source is U.S. initial unemployment-insurance claims, a weekly labor-market flow indicator. This is distinct from the repository's tested financial-conditions indices, Treasury yields/spreads, Fed balance-sheet levels, policy uncertainty, stablecoin supply, Wikipedia attention, blockspace fees, ETF flows and derivatives funding. Do not reinterpret a different claims series, labor-market release, lag or transformation as this same hypothesis after seeing results.

## 3. Frozen data and acceptance requirements

### FRED ICSA

- Endpoint: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=ICSA&cosd=2017-08-19`
- Series: `ICSA`, Initial Claims, seasonally adjusted; weekly; thousands of persons.
- Accept only a recognized observation-date column and the exact `ICSA` value column.
- Require positive finite values, unique dates on one consistent weekday, weekly gaps of 7 days (a 14-day gap may be retained but breaks any affected five-observation feature window), at least 450 observations, first observation no later than 2017-09-02, and latest observation no more than 14 days stale at retrieval.
- Current FRED vintage only. Historical revisions/publication-time point-in-time availability are not reconstructed; this limitation must be explicit.

### Binance BTCUSDT Spot

- Official Binance Vision 1d UTC kline archives and SHA-256 `.CHECKSUM` sidecars; active Spot `BTCUSDT` confirmed through official exchangeInfo.
- Preflight must validate one recent complete daily archive and its checksum. Full model run must validate every archive, reject gaps/duplicates, exclude incomplete current candles, and require at least 3,000 contiguous daily closes from 2017-08-17.
- Do not silently fill missing observations or combine venues.

Raw source observations must not be committed. Persist source URLs, retrieval timestamp, response/archive hashes, exact coverage, parser/validation outcomes and aggregate results only.

## 4. Frozen model

- Signal dates: each accepted weekly ICSA observation date plus exactly seven calendar days.
- Event eligibility: exact matching BTCUSDT UTC daily close, at least 20 complete prior returns, and five complete future daily returns.
- Target: (log(1 + 10000\,\operatorname{mean}(\min(r_{t+i},0)^2, i=1..5))), i.e. log1p of next-five-session BTC downside semivariance in percent-squared units.
- Baseline features, in this fixed order: prior 5-session downside semivariance (log1p), prior 20-session downside semivariance (log1p), prior 20-session total realized variance (log1p), prior 5-session cumulative log return, and prior 20-session cumulative log return.
- Augmented model: baseline plus exactly one feature, `icsa_change_4w_pct`.
- Training: latest 104 prior events whose signal date and five-session target end are both strictly before the current signal date.
- Event frequency: weekly. Since each target is five sessions and signals are seven calendar days apart, accepted target windows must be non-overlapping and fully matured before the next signal.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Estimator: existing deterministic standardized OLS helper with fixed ridge stabilization; no hyperparameter search or tuning.
- Paired test squared-loss moving-block bootstrap: 2,000 replications, block size 4 weekly events, seed 20261127.
- Minimum sample: at least 30 validation forecasts, 30 test forecasts and a computable paired-loss interval.

## 5. Frozen decision rule

- **PROMISING (forecast screen only):** validation and test RMSE both improve, and the paired test-loss 95% confidence interval lower bound is strictly positive.
- **REJECTED:** validation and test RMSE both worsen, and the paired test-loss 95% confidence interval upper bound is strictly negative.
- **INCONCLUSIVE:** every other outcome, including insufficient sample, mixed period results, or a paired interval crossing zero.

Even PROMISING is not a tradable strategy, causal finding, profitability claim or permission to deploy. No CAGR/Sharpe/drawdown or live-trading claims are applicable to this forecast-only experiment.

## 6. Cycle accounting and completion

1. **Cycle 1 — source feasibility:** deterministic parser/coverage tests plus read-only live ICSA, exchangeInfo and one checksummed BTC archive probe. Record the source-preflight run and exact manifest.
2. **Cycle 2 — implementation and conclusion:** implement only after Cycle 1 passes; run deterministic model tests, one frozen empirical backtest, persist report/manifest, and independently recompute sample counts, RMSE improvements and paired-loss decision from the persisted forecast output.

The candidate is closed after Cycle 2. A new source, feature, lag, target, market or materially different model requires a new hypothesis ID and its own preregistration/timebox.

## 7. Limitations and safeguards

- FRED current-vintage observations may contain revisions; a seven-day embargo does not eliminate vintage look-ahead.
- Initial claims are a macroeconomic flow measure, not direct BTC market positioning, order flow or forced selling.
- The model is a BTC Spot volatility-forecast screen, not an executable strategy or trading P&L.
- No raw observations are committed; no live orders or capital deployment are authorized.
- If any source or timing acceptance criterion fails, preserve the failure evidence and close as INCONCLUSIVE/INFEASIBLE rather than relaxing the protocol.
