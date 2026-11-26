# Deribit relative DVOL / ETH-BTC realized-volatility session — 2026-11-26T135953Z

## Research result

**Hypothesis:** QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01

**Disposition:** INCONCLUSIVE — INCONCLUSIVE — the frozen chronological and paired-loss criteria do not establish incremental predictive value or decisive inferiority.

The test asks whether the strictly prior common-date log ratio of ETH DVOL to BTC DVOL adds chronological out-of-sample information about the next seven daily observations' relative realized volatility, beyond each asset's own trailing realized volatility.

### Data coverage

| Source | First | Last | Rows |
|---|---|---|---:|
| Coinbase BTCUSD | 2023-03-26 | 2026-11-25 | 1341 |
| Coinbase ETHUSD | 2023-03-26 | 2026-11-25 | 1341 |
| Deribit BTC DVOL | 2023-03-26 | 2026-11-25 | 1341 |
| Deribit ETH DVOL | 2023-03-26 | 2026-11-25 | 1341 |

Common aligned sample: {"dvol_first_date": "2023-03-26", "dvol_last_date": "2026-11-25", "dvol_rows": 1341, "price_first_date": "2023-03-26", "price_last_date": "2026-11-25", "price_rows": 1341}.

### Event and forecast construction

- Accepted events: 187 of 187 candidates.
- Skipped events: {"incomplete_future_returns": 0, "incomplete_prior_returns": 0, "no_strictly_prior_common_dvol": 0, "nonpositive_realized_volatility": 0, "overlapping_target_window": 0, "stale_common_dvol": 0}.
- Signal: Coinbase close on t; latest common Deribit daily candle date strictly earlier than t.
- Target: log of next-seven-observation annualized ETH realized volatility divided by BTC realized volatility.
- Event spacing: seven observations; target windows do not overlap.
- Training: 52 prior events whose target end is strictly earlier than the current signal.
- Validation: 2024-04-01 through 2024-12-31; test: 2025-01-01 onward.

### Forecast results

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 36 | 98 |
| Baseline RMSE | 0.327094 | 0.341770 |
| Augmented RMSE | 0.324225 | 0.346701 |
| RMSE improvement | 0.8772% | -1.4427% |
| Baseline MAE | 0.265048 | 0.278997 |
| Augmented MAE | 0.267551 | 0.282277 |

Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.25, "ci95_high": 0.005559075506429804, "ci95_low": -0.013994571829600524, "mean_baseline_minus_augmented_squared_loss": -0.00339459848956659, "observations": 98, "reps": 2000}.

## Literature boundary

- Chevallier and Sanhaji (2023), “Jump-Robust Realized-GARCH-MIDAS-X Estimators for Bitcoin and Ethereum Volatility Indices,” Stats 6(4), 1339–1370, DOI https://doi.org/10.3390/stats6040082. Their study finds that 30-day implied-volatility indices can improve separate BTC and ETH realized-volatility forecasts. This study does not claim that result is new; it tests a relative ETH/BTC DVOL feature against a joint cross-asset baseline.
- Hoang and Baur (2020), “Forecasting bitcoin volatility: evidence from the options market,” Journal of Futures Markets 40(10), 1584–1602, DOI https://doi.org/10.1002/fut.22144. Their results distinguish short and longer forecasting horizons and find that implied volatility is more useful at longer horizons; this motivates explicit horizon reporting.
- Deribit documents the public daily-candle endpoint and its 1D resolution at https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data. The DVOL index measures 30-day annualized implied volatility; it is not a directional signal.

## Reproducibility

- FRED and Deribit URLs, source hashes, exact coverage, row counts, page cursors and numeric-scale normalization are recorded in the manifest.
- Raw Coinbase observations and raw Deribit response bodies are not committed.
- Deterministic parser, pagination, timestamp, missingness, non-overlap, maturity and decision-rule tests ran before data retrieval.

## Verified / unverified

**VERIFIED:** source retrieval, response hashes, daily candle parsing, source coverage, strict prior-date alignment, complete daily price windows, non-overlapping target returns, matured walk-forward training, chronological metrics and paired block-bootstrap under this data/code vintage.

**UNVERIFIED:** historical point-in-time revisions; generalization beyond the observed Deribit/Coinbase sample; causal interpretation; relative-volatility hedge or portfolio performance; executable fees, spreads, liquidity, funding and slippage.

## Disposition boundary

This is a forecast-only screen, not an ETH/BTC trading strategy. No CAGR, Sharpe, Sortino, Calmar, drawdown or live-trading claim is warranted. A promising result requires independent reconstruction and a separately preregistered tradable strategy study.
