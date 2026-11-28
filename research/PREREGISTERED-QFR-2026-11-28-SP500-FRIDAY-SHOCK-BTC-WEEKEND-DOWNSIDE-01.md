# Preregistration — Friday S&P 500 downside shock and Bitcoin weekend downside risk

- **Hypothesis ID:** QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01
- **Registered:** 2026-11-28T07:46:26Z, before source feasibility inspection or empirical-result inspection.
- **Status:** IDEA — source feasibility pending; no model fitting or backtest authorized until a source-only preflight passes.
- **Expected Difficulty:** HIGH
- **Difficulty rationale:** Two-source daily/hourly reconstruction, checksum-backed historical hourly archives, cross-market close-time embargo, weekly non-overlapping target windows, and strict walk-forward maturity checks require more than a routine daily-frequency screen.
- **Timebox start:** 2026-11-28T07:46:26Z
- **Maximum substantive cycles:** 8
- **Hard Implementation deadline:** 2026-11-30T07:46:26Z
- **Hard Final research-conclusion deadline:** 2026-12-08T07:46:26Z
- **Expiry rule:** At the earlier of eight substantive cycles or the final deadline, publish the strongest defensible conclusion. If source acceptance, implementation, immutable execution or independent audit is incomplete, close INCONCLUSIVE/INFEASIBLE; do not infer a performance NO-GO, extend the clock, weaken gates or repeat the same failed route under this identity. A materially different source, timing window, feature, target, market or model requires a new identity and preregistration.

## Research question and distinct mechanism

Does a negative Friday S&P 500 close-to-close return contain incremental information about the downside semivariance of Bitcoin during the following Saturday 12:00 UTC to Sunday 12:00 UTC window, beyond Bitcoin's own immediately prior downside risk, realized variance and absolute return?

The proposed channel is cross-market risk transmission across trading calendars. The S&P 500 cash market closes for the weekend while Bitcoin continues trading. A negative equity-session return may reveal a broad risk-off shock whose effects continue to propagate through portfolio deleveraging, collateral constraints or cross-asset risk limits during the subsequent crypto-only weekend window. This is a predictive association, not a causal claim.

This is not a generic S&P-to-Bitcoin daily correlation screen. The event is anchored to the Friday cash-market close, the crypto forecast window begins only after a fixed 15–16 hour embargo, the target is hourly Bitcoin downside semivariance, and weekly origins have non-overlapping 24-hour targets.

## Literature and novelty boundary

- Boucher (2026), “Realized-Volatility Connectedness Across Equities, Foreign Exchange, Commodities, and Cryptocurrencies: Daily Variance Decompositions and Trading-Session Evidence,” reports that equity futures are robust net transmitters in its connectedness framework while Bitcoin is approximately neutral on average; it also reports increased Bitcoin exposure to non-crypto shocks after 2019. It does not test the frozen one-sided Friday-close-to-Saturday/Sunday downside-semivariance forecast specified here: https://www.spboucher.ai/research/wp6.
- “A crypto-stock weekend effect: Predicting Monday stock returns using weekend cryptocurrency returns” (2025) studies the reverse direction, finding that negative weekend crypto returns predict Monday equity returns. It does not establish that Friday equity shocks predict subsequent Bitcoin weekend downside risk: https://doi.org/10.1016/j.frl.2025.108661.
- Dehouche (2021), “Scale matters: The daily, weekly and monthly volatility and predictability of Bitcoin, Gold, and the S&P 500,” documents frequency-dependent Bitcoin volatility properties, motivating an explicitly hourly target rather than assuming daily and intraday risk are interchangeable: https://arxiv.org/abs/2103.00395.

The bounded contribution is a preregistered, strict-lag, weekly, single-Bitcoin forecast test of the direction from a Friday U.S. equity close to a subsequent crypto-only weekend window. It does not claim first discovery of equity/crypto spillovers, weekend effects or volatility connectedness.

## Source feasibility and point-in-time boundary

### S&P 500 cash index

- Source: FRED daily S&P 500 series, series ID SP500, sourced from S&P Dow Jones Indices LLC.
- Public CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2017-08-18.
- Required coverage: at least 2,200 positive, finite, unique daily observations; first observation no later than 2017-09-01; latest observation no more than five calendar days old; weekdays only; no observation gap above seven calendar days.
- Predictor: for each Friday observation, max(0, -10,000 × ln(SP500_close_Friday / SP500_close_previous_trading_day)), measured in basis points. The previous observation is the immediately preceding published trading-day observation, not an interpolated date.
- Signal timestamp: Saturday 12:00 UTC after the Friday observation. This gives a 15-hour embargo after the 16:00 New York cash close during Eastern Standard Time and a 16-hour embargo during Eastern Daylight Time.
- FRED supplies observation dates, not historical intraday first-publication timestamps or ALFRED vintages for this index. The embargo is conservative but does not prove exact historical availability. Record this limitation in every result; do not describe the signal as fully point-in-time certified or tradable.

### Bitcoin Spot hourly bars

- Instrument: Binance Spot BTCUSDT, interval 1h, UTC.
- Source: official Binance Vision monthly and daily kline ZIP archives with their adjacent SHA-256 CHECKSUM sidecars: https://github.com/binance/binance-public-data.
- Public archive root: https://data.binance.vision/data/spot/.
- Required coverage: hourly bars from 2017-08-18 00:00 UTC through the end of the latest matured target window; every archive and checksum sidecar must be fetched and verified; no duplicate or out-of-window accepted timestamps; at most 24 missing/affected UTC hours, an effective missing fraction at most 0.05%, and no more than four consecutive affected hours. Pre-result source-parser amendment after run 46124207470: some official historical BTC archives contain off-grid open timestamps and invalid close-time rows. Never round, repair or insert them. Exclude and enumerate every malformed raw row. For the frozen missingness limits, map each malformed timestamp to its containing UTC hour solely as an affected-hour diagnostic, count each distinct affected hour inside the required [2017-08-18 00:00 UTC, latest target end) interval once, and take the union with genuinely absent expected hourly bars so an hour is never double-counted. Rows outside the required interval and multiple malformed rows in one affected hour do not inflate the number of missing hours, but all raw anomalies remain visible in the manifest. Apply the unchanged 24-hour, 0.05% and four-consecutive-hour limits to this union. A close_time exactly equal to open_time plus one interval is accepted as an end-exclusive boundary convention and separately counted.
- Validate the exact hourly windows needed for each event. Missing hours must not be interpolated or bridged. Exclude an event if any baseline or target return window is incomplete. Malformed archive rows are never timestamp-rounded; they are excluded, enumerated and treated as potential missing hourly observations.
- Preserve archive URLs, archive SHA-256 values, checksum-file SHA-256 values, row counts, timestamp units and coverage diagnostics in the source manifest. Do not commit raw market observations.

### Source-preflight acceptance

The read-only source preflight must verify both sources, checksum-backed hourly archive coverage, the latest fully matured Friday event, and the number of weekly events that remain after exact hourly-window completeness and the 104-event matured-training rule. Require at least 60 eligible validation forecasts (2019–2021) and 60 eligible test forecasts (2022 onward). The preflight must explicitly record backtest_run=false and raw_observations_saved=false. No model fitting is permitted during source preflight.

## Frozen forecast design — only after source preflight PASS

- Event schedule: every Friday with a valid S&P 500 close and a complete Bitcoin feature/target window. One event per week.
- Signal timestamp: Saturday 12:00 UTC.
- Target window: Saturday 12:00 UTC through Sunday 12:00 UTC, exactly 24 hourly close-to-close returns.
- Predictor: Friday downside return in basis points, defined above. Positive values mean a negative Friday S&P 500 return; zero means a non-negative Friday return.
- Baseline features:
  - log1p of Bitcoin downside semivariance over the immediately preceding 24 hourly returns;
  - log1p of Bitcoin downside semivariance over the immediately preceding 168 hourly returns;
  - log1p of Bitcoin realized variance over the immediately preceding 168 hourly returns;
  - absolute cumulative Bitcoin return over the immediately preceding 24 hours, in basis points.
- Augmented model: baseline features plus only the Friday S&P 500 downside-return feature.
- Hourly downside semivariance and realized variance are the mean of squared hourly log returns in basis-point units, with negative returns clipped to zero only for downside semivariance. The target is log1p of the 24-hour target downside semivariance.
- Walk-forward model: ridge-stabilized OLS using feature standardization estimated on the training sample only; the most recent 104 prior eligible weekly events; every training target must have matured strictly before the current signal timestamp.
- Validation: Friday event dates 2019-01-01 through 2021-12-31.
- Test: Friday event dates 2022-01-01 onward.
- Minimum: at least 60 forecasts in each split after training maturity and source-window exclusions.
- Primary metric: RMSE in log1p downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular moving-block bootstrap replications, block length four weekly events, seed 20261128.

## Frozen decision rule

- BACKTESTED / PROMISING SCREEN: at least 60 validation and 60 test forecasts; augmented RMSE improves in both periods; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- INCONCLUSIVE: all other outcomes, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale sources, incomplete hourly windows or unresolved point-in-time limitations.
- A promising result remains forecast-only. It does not establish causality, executable trading performance, profitability or deployment readiness.
- No result-dependent retuning, alternate embargoes, alternate weekend windows, extra predictors, threshold searches or repeat run under this hypothesis ID is authorized.

## Safety and limitations

- FRED SP500 is a current-vintage daily series with no historical intraday first-publication timestamps in this design. The 15–16 hour embargo reduces timing risk but cannot certify historical availability.
- Binance BTCUSDT is one venue and one quote currency; archive checksums establish file integrity, not consolidated-market representativeness.
- Hourly archive gaps are not silently filled. An incomplete feature or target window excludes that event.
- The target is a forecast of weekend downside semivariance, not a trading strategy or P&L series. Do not report CAGR, Sharpe, Sortino, Calmar or drawdown.
- No live orders, capital deployment, causal inference or deployment authorization is permitted.
