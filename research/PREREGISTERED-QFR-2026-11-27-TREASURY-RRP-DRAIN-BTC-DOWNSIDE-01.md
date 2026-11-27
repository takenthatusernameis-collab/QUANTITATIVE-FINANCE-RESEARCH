# Preregistration — Treasury cash and ON RRP reserve-drain impulse to Bitcoin downside semivariance

- **Hypothesis ID:** QFR-2026-11-27-TREASURY-RRP-DRAIN-BTC-DOWNSIDE-01
- **Registered:** 2026-11-27T22:29:15Z, before substantive implementation and empirical-result inspection.
- **Status:** IMPLEMENTATION_READY
- **Difficulty:** LOW.
- **Difficulty rationale:** Both inputs are free official FRED series with public CSV access; the BTC archive ingestion, downside target, walk-forward estimator and paired-loss bootstrap already exist as tested repository components. The new work is one aligned feature, one model module, deterministic tests and one frozen screen.
- **Timebox start:** 2026-11-27T22:29:15Z
- **Maximum substantive cycles:** 2
- **Implementation deadline:** 2026-11-28T22:29:15Z
- **Final research-conclusion deadline:** 2026-11-29T22:29:15Z
- **Expiry rule:** At the earlier of two substantive cycles or the stated deadline, publish the strongest defensible conclusion. If source acceptance, implementation or the frozen screen is incomplete, close INCONCLUSIVE/INFEASIBLE; do not infer a performance NO-GO, reset the clock, alter the feature or rerun this hypothesis ID.

## Research question and mechanism

Does a strictly lagged four-week increase in the combined U.S. Treasury General Account (TGA) and Federal Reserve overnight reverse-repurchase (ON RRP) balance add chronological out-of-sample information about next-five-session Bitcoin downside semivariance beyond Bitcoin's own recent downside semivariance and total realized variance?

The mechanism is the reserve-drain/liquidity-absorption channel on the liability side of the Federal Reserve balance sheet. A rising Treasury cash balance removes funds from bank reserves; a rising ON RRP balance absorbs cash into the Federal Reserve's overnight facility. Their sum is a narrow proxy for these two non-reserve liability buckets. The hypothesis is that a sustained increase in this combined drain may coincide with tighter dollar funding conditions and greater BTC left-tail risk.

This is not a claim that TGA plus ON RRP equals total net liquidity, bank reserves or the full supply of dollar funding. It omits Federal Reserve assets, reserve balances, currency and other liabilities. The study deliberately isolates a distinct fiscal-cash / money-market-facility mechanism rather than repeating the prior WALCL-only total-assets feature.

## Literature and novelty boundary

- The Federal Reserve's 2025 note, "Repo Rate Sensitivity to Treasury Issuance and Quantitative Tightening," documents that repo-rate sensitivity to Treasury issuance varies with Fed-provided liquidity and was higher during the 2017–19 QT period: https://www.federalreserve.gov/econres/notes/feds-notes/repo-rate-sensitivity-to-treasury-issuance-and-quantitative-tightening-20250212.html.
- The IMF working paper "Repo Market Volatility and the U.S. Debt Ceiling" examines how TGA balance changes affect repo spreads and how reserves and ON RRP moderate that effect: https://www.elibrary.imf.org/abstract/journals/001/2025/127/article-A001-en.xml.
- Ma, Marshall, Nguyen and Visaltanachoti (2022), "Does bitcoin liquidity resemble the liquidity of other financial assets?", find that deterioration in Bitcoin liquidity contributes to crash risk and large price declines: https://doi.org/10.1177/03128962211069615.
- Llanos, Perote and Vicente-Lorente (2026), "Liquidity, scarcity, and long-run anchoring in Bitcoin demand (2010–2025)," report a long-run association between broad liquidity and Bitcoin demand, while cautioning that channel attribution is not uniquely identified: https://doi.org/10.1016/j.iref.2026.105320.

The repository already tested WALCL-only Federal Reserve total-assets contraction, SOFR-EFFR funding spreads, Treasury auction demand/supply, broad financial stress and stablecoin supply. The present feature is materially distinct: it combines the Treasury's Wednesday cash balance with the NY Fed's daily ON RRP balance on exact common Wednesdays and excludes WALCL. No existing registry entry tests this combined liability-side reserve-drain proxy. The bounded contribution is a forecast screen, not a first claim about liquidity or Bitcoin.

## Data feasibility, definitions and provenance

### Treasury General Account — WDTGAL

- Official series: https://fred.stlouisfed.org/series/WDTGAL
- Source: Board of Governors of the Federal Reserve System, H.4.1.
- Frequency: weekly, as of Wednesday.
- Units: millions of U.S. dollars, not seasonally adjusted.
- Public CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=WDTGAL&cosd=2017-08-16.

### Overnight reverse repo — RRPONTSYD

- Official series: https://fred.stlouisfed.org/series/RRPONTSYD
- Source: Federal Reserve Bank of New York Temporary Open Market Operations.
- Frequency: daily.
- Units: billions of U.S. dollars, not seasonally adjusted.
- Public CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=RRPONTSYD&cosd=2017-08-16.

### Combined feature source

- Retrieval: one public FRED graph CSV request for WDTGAL and RRPONTSYD.
- Keep only exact Wednesday rows where both components are present. Do not forward-fill, interpolate, or substitute zero for a missing observation.
- Convert RRPONTSYD from billions to millions by multiplying by 1,000.
- Combined drain in millions USD: WDTGAL + 1000 * RRPONTSYD.
- Require at least 400 complete common Wednesday observations, a start no later than 2017-08-30, no gap greater than 14 days, no future dates, a latest common Wednesday no more than 10 calendar days old, and strictly positive finite component and combined values.
- Preserve the exact request URL, retrieval time, raw-response SHA-256, component units, row counts, first/last dates and skipped-component diagnostics.
- The FRED current vintage is used. Historical ALFRED point-in-time vintages are not reconstructed.

### Bitcoin spot — BTCUSDT

- Instrument: Binance Spot BTCUSDT, interval 1d, UTC.
- Source: official Binance Vision monthly/daily kline archives and .CHECKSUM sidecars: https://github.com/binance/binance-public-data.
- Active-market check: https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT.
- Require at least 3,000 completed daily candles, history beginning no later than 2017-08-19, latest completed candle no more than two calendar days old, no missing UTC date, positive finite closes and no future date.
- Verify every archive against its official SHA-256 sidecar; reject duplicate dates, incomplete days, mixed timestamp units within an archive and missing calendar dates. Exclude the incomplete current candle.
- Do not commit raw observations.

## Frozen feature, signal and target

- Weekly observation date: exact common Wednesday for WDTGAL and RRPONTSYD.
- Signal: close of the Binance BTCUSDT UTC daily candle dated seven calendar days after that Wednesday. This conservative lag exceeds the ordinary Thursday H.4.1 publication time and is fixed before the result.
- Predictor: 100 * ln(DRAIN[t] / DRAIN[t-4]), where t and t-4 are five consecutive common weekly Wednesday observations. Positive values mean the combined TGA + ON RRP drain increased over four weeks.
- Skip any five-observation window that is not exactly weekly. Do not fill missing component observations.
- BTC log return: ln(close[t] / close[t-1]).
- Downside semivariance over n daily returns: 10,000 times the mean of min(return, 0)^2, in percentage-points squared, not annualized.
- Baseline features: log1p of prior-five-session BTC downside semivariance; log1p of prior-twenty-session downside semivariance; log1p of prior-twenty-session total realized variance.
- Augmented model: baseline plus only the four-week TGA + ON RRP drain increase.
- Target: log1p of next-five-UTC-session BTC downside semivariance.
- Weekly signal origins are seven days apart; five-session target windows must be fully matured before the next signal. No overlapping targets or incomplete future windows are accepted.

## Walk-forward model and evaluation

- Baseline and augmented models: ridge-stabilized ordinary least squares, with feature standardization estimated on training data only.
- Rolling training window: 104 prior weekly events. Every training event's signal and target end must both be strictly earlier than the current signal date.
- Validation: signal dates 2019-01-01 through 2021-12-31.
- Test: signal dates 2022-01-01 onward.
- Minimum: at least 30 forecasts in each period; otherwise INCONCLUSIVE.
- Primary metric: RMSE in log1p downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four consecutive weekly events, fixed seed 20261127.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 30 validation and 30 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- INCONCLUSIVE: all other outcomes, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale sources or incomplete data.
- A promising forecast remains BACKTESTED only. Current-vintage FRED revisions and lack of independent reconstruction prevent independent validation or strategy promotion.
- No result-dependent retuning, alternate horizons, extra predictors, threshold search or repeat run under this hypothesis ID is authorized.

## Limitations and safety

- WDTGAL plus ON RRP is a narrow liability-side reserve-drain proxy, not full net liquidity, bank reserves or a complete measure of dollar funding conditions.
- TGA and ON RRP can move for different operational reasons; adding them is a transparent accounting proxy, not proof that each dollar has identical marginal market impact.
- The series are current FRED vintages; historical publication timestamps and ALFRED vintages are not reconstructed.
- The fixed seven-day lag is conservative but does not remove all historical revision/look-ahead risk.
- BTCUSDT is one venue's spot history; checksummed archives establish file integrity, not consolidated-market representativeness.
- Forecasting only. No live orders, capital deployment, trading P&L, causal claim or deployment authorization.
- No raw source observations are committed.

