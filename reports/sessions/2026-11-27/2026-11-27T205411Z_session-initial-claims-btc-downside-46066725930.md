# Research session — U.S. initial claims and BTC downside semivariance (2026-11-27T205411Z)

- **Hypothesis:** QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01
- **Status:** INCONCLUSIVE
- **Decision:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule
- **Daily KPI:** The 2026-11-27 minimum was already met by the distinct ETF-relative-flow and BTC blockspace-fee-rate real-data screens; this is an additional hypothesis backtest.
- **Implementation timebox:** LOW; 2 substantive cycles maximum; implementation deadline 2026-11-28T15:40:06Z; final research-conclusion deadline 2026-11-29T15:40:06Z.
- **GitHub run:** 46066725930, attempt 1
- **Triggering commit:** a1a0303e760ad89dd76529740199dff6aa720d1c

## Cycle accounting

- Cycle 1 source feasibility: PASS; preflight run #46028463525.
- Cycle 2 implementation, deterministic validation, real-data backtest and independent audit: see linked evidence.

## Frozen method

- Predictor: 100 × ln(ICSA[w] / ICSA[w−4]); positive means initial claims rose over four weekly observations.
- Availability: FRED weekly observation ending Saturday, signal at the BTC UTC close seven calendar days later.
- Baseline: prior 5/20-session downside semivariance, prior 20-session realized variance and prior 5/20-session cumulative log returns.
- Augmented model: baseline plus exactly one four-week initial-claims change feature.
- Target: log1p of next-five-session BTC downside semivariance; signal-day return excluded.
- Rolling training: latest 104 fully matured weekly events. Validation: 2019–2021. Test: 2022 onward.
- Estimator: existing standardized OLS helper; no parameter tuning.

## Data provenance

| Source | Coverage | Rows / archives | SHA-256 |
|---|---|---:|---|
| FRED ICSA | 2017-08-19 to 2026-11-21 | 484 weekly observations | 2bcf8c35377a4280459bc015dc53cba21cbcd992a916a7fd0d29bd5d09aed0bb |
| Binance BTCUSDT Spot | 2017-08-17 to 2026-11-25 | 3388 candles; 136 archives | 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe |
| Frozen Binance sample archive | 2026-11-23 | SHA-256 verified | d778c53e3a42ec9e6ae13f39401b530028a37c78b94be1cfd80aec7706e3d96a |

## Event construction

- Accepted events: 478
- First/last signal: 2017-09-23 / 2026-11-14
- Skipped events: {"incomplete_target": 1, "insufficient_price_history": 0, "invalid_claims_feature": 0, "invalid_returns": 0, "irregular_weekly_window": 0, "missing_signal_anchor": 1}
- Every five-session target was fully matured before the next weekly signal.

## Walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 119 | 255 |
| Baseline RMSE | 1.0968906043231066 | 0.8542368540456668 |
| Augmented RMSE | 1.452944239614357 | 0.852846082732052 |
| RMSE improvement | -32.46026849787558% | 0.16280862936645432% |

## Paired test-loss uncertainty

- {"block_size_events": 4, "bootstrap_fraction_positive": 0.584, "ci_95_high": 0.02572600248452626, "ci_95_low": -0.021474627916361365, "mean_baseline_minus_augmented_squared_loss": 0.0023741619784319553, "observations": 255, "replications": 2000, "seed": 20261127, "status": "COMPUTED"}

## Interpretation

INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule

## Verified / unverified

**VERIFIED:** ICSA schema and weekly coverage, frozen FRED response hash, active BTCUSDT Spot status, Binance archive checksum integrity, event timing, non-overlapping target windows, walk-forward sample construction and arithmetic in the persisted forecast output.
**UNVERIFIED:** historical point-in-time FRED revisions/publication timing, independent data-source replication, causal interpretation, future-regime stability and instrument-level economic value.

## Limitations

- FRED ICSA is current-vintage data; historical ALFRED vintages and exact historical publication timestamps were not reconstructed. The seven-day lag is conservative but does not eliminate revision look-ahead.
- ICSA measures weekly initial unemployment-insurance claims, not layoffs alone, unemployment stocks or real-time labor-market expectations.
- The feature is one four-week log change in a single national series; no alternative transformations, lags, series or parameters were tested.
- This is one of many exploratory repository hypothesis screens; nominal paired-loss intervals do not correct for repository-wide multiple testing or selection bias. Any promising result requires independent confirmation.
- BTCUSDT is one venue's Spot close. Binance archive checksums establish file integrity, not exchange-independent consolidated prices.
- This is a forecast-only screen, not an executable strategy, trading P&L, causal claim or live deployment recommendation.
- No raw ICSA observations or raw BTC price rows are committed; the manifest contains source hashes, coverage and derived forecast rows only.

## Reproducibility

- Source preflight: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463525
- Empirical workflow: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066725930
- Implementation: research/initial_claims_btc_downside.py
- Tests: research/test_initial_claims_btc_downside.py
