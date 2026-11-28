# Preregistered Research: H.8 Commercial-and-Industrial Credit Impulse and BTC Downside Semivariance

- **Hypothesis ID:** `QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01`
- **Status:** SOURCE PREFLIGHT PENDING; no model fit or backtest is authorized until the frozen source gate passes.
- **Registered:** `2026-11-28T05:49:20Z`
- **Difficulty:** MEDIUM
- **Difficulty rationale:** The proposed predictor is a weekly, revised macroeconomic series. The work requires a public historical-vintage retrieval path, explicit release-time alignment, an immutable accepted BTC Spot input manifest, a bounded walk-forward model, and independent evidence reconstruction. The source gate is small and uses no paid data or credentials.
- **Timebox start:** `2026-11-28T05:49:20Z`
- **Maximum substantive cycles:** 4
- **Hard implementation deadline:** `2026-12-01T05:49:20Z`
- **Hard final research-conclusion deadline:** `2026-12-03T05:49:20Z`
- **Expiry rule:** If the public ALFRED vintage endpoint is inaccessible without a key, fails its exact vintage-column/schema checks, cannot provide at least 450 weekly observations over the frozen BTC overlap, or cannot establish that the as-of-Sunday panel contains no future observations, close this identity as `INCONCLUSIVE/INFEASIBLE`. Do not substitute current-vintage FRED data, another H.8 series, a different lag, or another vendor under this ID. If the model is not implemented by the implementation deadline or the independent conclusion is not recorded by the final deadline, close it as `INCONCLUSIVE/INFEASIBLE`; do not reset or extend the clock.

## 1. Falsifiable question

Does a strictly point-in-time four-observation log change in U.S. commercial-and-industrial (C&I) bank loans add out-of-sample information about the next five UTC daily BTC downside-semivariance observations, beyond BTC's own recent momentum, downside risk and realized variance?

For Sunday UTC signal date (d), use the ALFRED vintage that was available as of that Sunday. Let (L_d) be the latest published H.8 TOTCI observation in that vintage, and (L_{d,-4}) the fourth prior weekly observation in the same vintage. The sole augmented predictor is:

[
x_d = 100\ln\left(\frac{L_d}{L_{d,-4}}\right)
]

Positive values indicate C&I loan expansion over four weekly observation intervals; negative values indicate contraction. Both values must come from the same historical vintage. No value may be taken from today's revised FRED series when an older ALFRED vintage is required.

## 2. Economic mechanism and novelty boundary

The proposed mechanism is the **bank-credit quantity / working-capital channel**. A contraction in C&I lending may reflect tighter credit supply, weaker credit demand, or both, and could coincide with lower risk-bearing capacity in speculative markets. The experiment tests incremental forecasting information only; it does not identify a causal bank-credit shock.

This is distinct from repository experiments on:
- WALCL, which measures Federal Reserve assets rather than commercial-bank loan creation;
- STLFSI4 and BAA10Y, which measure broad financial stress and corporate credit spreads rather than loan quantities;
- Treasury/ON RRP balances, which measure public-sector reserve liabilities;
- exchange funding, ETF flows, stablecoin supply, blockspace fees, attention and realized-volatility predictors.

A repository search for `TOTCI`, `H.8 commercial industrial loans` and bank-credit/BTC-downside phrasing found no existing hypothesis identity using this series. The closest adjacent work is the existing BAA10Y spread screen, which is not a substitute for this quantity-side test.

## 3. Frozen sources and source-acceptance gates

### Predictor source

- Provider: Federal Reserve Board H.8, retrieved as historical vintages through ALFRED.
- Series: `TOTCI`, Commercial and Industrial Loans, All Commercial Banks.
- Frequency: weekly, ending Wednesday.
- Units: billions of U.S. dollars, seasonally adjusted.
- H.8 release timing: generally Friday at 4:15 p.m. Eastern Time; Thursday at 4:15 p.m. when Friday is a federal holiday.
- H.8 observation reference time: close of business Wednesday.
- Historical-vintage endpoint to be tested: `https://alfred.stlouisfed.org/graph/alfredgraph.csv`, with repeated `id=TOTCI` entries and matching `vintage_date` values. No API key, account, paid service or credential is permitted.
- Source documentation: H.8 release calendar, H.8 About page, ALFRED TOTCI series page and FRED real-time-period documentation (URLs in Section 8).
- Signal timing: the BTC Sunday daily candle closes at Monday 00:00 UTC. Use the ALFRED vintage as of the preceding Sunday UTC date. The normal H.8 release occurs on Friday afternoon U.S. Eastern Time, so the Sunday vintage is after the scheduled release. If a release is delayed, the vintage naturally retains the older value; do not backfill the unreleased observation.
- For each signal, the latest H.8 observation must be no more than 14 calendar days old, must be a Wednesday observation, and must have four prior weekly observations with 5–9 day spacing. If these conditions fail, exclude the event; never forward-fill, interpolate, or substitute a later vintage.
- Source preflight sample vintages: 2017-08-20, 2020-03-15, 2022-01-02, 2024-01-07 and 2026-11-22. These are Sundays selected after scheduled H.8 release windows. The preflight makes one bounded GET and checks exact response headers, as-of behavior, observation age, weekly cadence, positive finite values, and historical coverage.
- Require at least 450 TOTCI observations from 2017-08-16 onward in the 2026-11-22 vintage. Require no observation date later than its vintage date. Record—but do not require—a nonzero historical revision count between the 2020 and 2026 vintages.
- The empirical implementation may retrieve weekly Sunday vintages in batches of at most 12 dates, with a 1.5-second inter-request delay and no retries. HTTP 401/403/429/451, malformed responses, wrong columns or insufficient coverage are terminal source failures for this identity.
- Do not use the current-vintage FRED graph/table as a fallback. The ALFRED vintage endpoint must be demonstrated to work without a key before model implementation.

### Price source

- Binance Vision official Spot `BTCUSDT` `1d` UTC klines.
- Reuse the previously accepted 3,388-candle source evidence from 2017-08-17 through 2026-11-25, with 136 checksum-verified archives and archive-manifest SHA-256 `978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe`.
- Canonical evidence: `reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json`.
- Do not redownload or replace accepted price data unless a deterministic integrity check shows the existing manifest is unavailable or inconsistent.

## 4. Timing, events and target

- Event origin: every Sunday UTC date (d), after the Sunday BTC daily candle closes at Monday 00:00 UTC.
- Predictor vintage: ALFRED as of Sunday (d); the feature uses only observations recorded in that vintage.
- The BTC baseline uses completed daily candles through Sunday (d).
- Target: the mean squared negative BTC log return over the next five UTC daily candles, Monday through Friday:
  [
  y_d = 10{,}000\times\frac{1}{5}\sum_{j=1}^{5}\min(r_{d+j},0)^2
  ]
- Events are spaced seven calendar days apart, so five-session target windows do not overlap.
- A target may enter a training fit only after all five daily candles have closed.
- The final eligible event must have all five target candles inside the accepted BTC price manifest.

## 5. Frozen model comparison

- **Baseline:** prior five-session momentum, prior 20-session momentum, prior five-session downside semivariance, prior 20-session downside semivariance, and prior 20-session total realized variance.
- **Augmented:** exactly the baseline plus the single four-observation TOTCI log-change predictor.
- Estimator: standardized rolling OLS with the repository's fixed (1\times10^{-8}) coefficient ridge stabilization.
- Training window: latest 104 fully matured prior weekly events.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum sample: 100 validation forecasts and 100 test forecasts. If either minimum is not met, the performance conclusion is INCONCLUSIVE.
- Primary metric: RMSE of `log1p(next-five-session downside semivariance × 10,000)`.
- Inference: 2,000 paired circular moving-block bootstrap replications of test squared-loss differences, block length four weekly events, fixed seed `20261128`.
- No threshold search, alternate horizon, feature search, hyperparameter tuning, split changes or post-result amendments.

## 6. Frozen decision rule

- **GO (research-only):** augmented RMSE improves by at least 1.0% in both validation and test, and the paired test-loss 95% confidence interval for baseline loss minus augmented loss is entirely above zero.
- **REJECTED:** augmented RMSE does not improve in either period and the paired test-loss 95% confidence interval is entirely below zero.
- **INCONCLUSIVE:** every other valid empirical outcome, including mixed validation/test signs, an interval crossing zero, or insufficient sample size.
- **INCONCLUSIVE/INFEASIBLE:** source acceptance fails, the timebox expires, or a valid empirical result cannot be independently reconstructed.

No result under this ID authorizes live trading, portfolio allocation, strategy promotion or a claim of tradable profitability.

## 7. Known limitations

1. H.8 is an estimated aggregate balance sheet built from a reporting panel and Call Report data; it is not a direct observation of every U.S. bank loan.
2. TOTCI is seasonally adjusted and can be revised. ALFRED vintage retrieval is therefore mandatory; a current-vintage FRED series is not an acceptable substitute.
3. ALFRED vintage dates have day-level, not intraday, resolution. The Sunday signal convention is deliberately after the scheduled Friday H.8 release, with a stale-data gate for delays.
4. C&I loan growth mixes credit supply and credit demand; the feature is not an identified exogenous lending shock.
5. Binance BTCUSDT Spot is one venue and the target is a forecast screen, not an executable strategy or P&L.
6. The test does not establish causality, economic value after trading costs, regime stability or live deployability.

## 8. References and adjacent literature

- Federal Reserve Board, H.8 release dates: https://www.federalreserve.gov/releases/h8/
- Federal Reserve Board, H.8 About: https://www.federalreserve.gov/releases/h8/about.htm
- FRED series TOTCI: https://fred.stlouisfed.org/series/TOTCI
- ALFRED series TOTCI: https://alfred.stlouisfed.org/series?seid=TOTCI
- FRED real-time periods: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
- ALFRED vintage-date documentation: https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html
- Cornelli, De Fiore and Gambacorta, “Fintech vs bank credit: How do they react to monetary policy?” BIS Working Paper 1157. This supports the relevance of the bank-credit channel but does not test BTC downside forecasting: https://www.bis.org/publ/work1157.pdf
- “State-Dependent Relationship Between Cryptocurrency Returns and Credit Spreads,” *European Financial Management*. This is adjacent crypto/credit-spread evidence; the present hypothesis instead tests bank-loan quantities and downside semivariance: https://onlinelibrary.wiley.com/doi/full/10.1111/eufm.70010
- Boungou and Yatie, “Cryptocurrency uncertainty and bank intermediation,” *Economics Letters* (2026). This examines the reverse direction from crypto uncertainty to bank balance-sheet decisions, not the preregistered bank-credit-to-BTC forecast: https://doi.org/10.1016/j.econlet.2026.113221

## 9. Cycle log

- **Cycle 1 — source feasibility:** freeze this protocol, validate the public ALFRED vintage CSV route, and record a source-only manifest. No BTC retrieval, model fit or backtest.
- **Cycle 2 — implementation:** only after Cycle 1 passes, implement the as-of-vintage panel, event construction, model, deterministic tests and immutable workflow.
- **Cycle 3 — empirical execution:** run the one frozen real-data backtest after the atomic `[QFR-ADMIT] research:` admission commit.
- **Cycle 4 — independent audit:** reconstruct source vintages, event timestamps, matured training windows, forecast rows, metrics and bootstrap before recording the final disposition.

The daily empirical backtest minimum for 2026-11-28 was already met by the separate MEXC funding-dispersion/BTC realized-variance experiment. This source-only preflight is additional work and does not count as a backtest.
