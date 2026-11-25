# Research session — ANFCI tightening shock and S&P 500 volatility (2026-11-25T22:37:41.532627+00:00)

- Hypothesis: QFR-2026-11-25-ANFCI-TIGHTENING-SP500-RV-01
- Status: REJECTED
- Disposition: REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse
- Daily real-data backtest KPI: MET before this additional study by distinct 2026-11-25 experiments
- GitHub run: 45714834063, attempt 1
- Triggering commit: a69ecbe8bd0d99e2d6a39831233a1ca591e405e4

## Preregistered mechanism and method

- Predictor: four-week change in the Chicago Fed Adjusted National Financial Conditions Index (ANFCI). Positive change means financial conditions tightened relative to prevailing economic conditions.
- ANFCI weekly reference date is Friday. The index is treated as unavailable until seven calendar days later; use the first S&P 500 close on or after that date.
- Baseline: prior-five and prior-twenty-session S&P 500 realized volatility plus signal-date log VIX. Augmented model adds only the four-week ANFCI change.
- Target: next-five-session S&P 500 realized volatility; rolling training window 104 prior events whose target end is strictly earlier than the current signal date.
- Validation: 2019–2021. Test: 2022 onward. Primary metric: RMSE in log1p realized-volatility space.

## Data provenance

| Source | First date | Last date | Rows | SHA-256 |
|---|---|---:|---:|---|
| ANFCI | 2016-11-25 | 2026-11-20 | 522 | dec032e8eb139bfd541c8a4e228ab8f0594e9fdce4011e778416b6c2f608ec47 |
| SP500 | 2016-11-28 | 2026-11-24 | 2512 | 6892b6e8b13c7283cb2fe62a453bbe1953a1db4084ae5d795a8ee27ea5a69d11 |
| VIXCLS | 2016-11-25 | 2026-11-24 | 2546 | fc8adf09eed97d58b761eca77de7cee278d79c257dd89b08747b31482bc8fad7 |

## Frozen walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 115 | 210 |
| Baseline RMSE, log1p RV | 0.32873609 | 0.24834593 |
| Augmented RMSE, log1p RV | 0.34562528 | 0.25211829 |
| RMSE improvement | -5.1376% | -1.5190% |

- Accepted non-overlapping weekly events: 430 of 522 weekly observations.
- Skipped events: {"incomplete_return_window": 0, "insufficient_four_week_history": 4, "insufficient_price_history_or_future": 1, "irregular_weekly_feature_window": 0, "missing_vix_on_signal_date": 0, "no_signal_close": 1, "overlapping_target_window": 86, "signal_close_too_far_after_release_lag": 0}.
- Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.0235, "ci_95_high": -1.550528341614419e-05, "ci_95_low": -0.003971623243224489, "mean_baseline_minus_augmented_squared_log_loss": -0.001887930900323847, "observations": 210, "reps": 2000, "status": "COMPUTED"}.

## Verified versus unverified

**VERIFIED:** deterministic timing/alignment tests, source schema and coverage acceptance, strict release lag, exact-date VIX alignment, no forward-fill, non-overlapping targets, fully matured training targets and the recorded result under this code/data vintage.

**UNVERIFIED:** historical point-in-time ANFCI vintages, exact intraday availability beyond the published weekly schedule, stability under future regimes, independent source reconstruction and instrument-level economic value.

## Explicit limitations

- ANFCI is a composite indicator; its constituent financial variables may overlap with market indicators, including information correlated with VIX and equity prices.
- Chicago Fed states that ANFCI history is revised as component data and estimated weights change. This screen uses the current FRED vintage, not historical release vintages; the seven-day lag does not remove revision look-ahead.
- ANFCI is macro-adjusted but not a pure exogenous funding shock or causal measure of forced deleveraging.
- SP500 is a cash price index, not an executable futures series or total-return index. Forecasting only: no trading P&L, transaction-cost model or live-deployment conclusion.
- No raw source data are committed; only retrieval metadata, hashes and aggregate metrics are retained.

## Reproducibility

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45714834063
- Manifest: reports/generated/anfci-tightening-shock/45714834063-attempt-1/manifest.json
- Source: research/anfci_tightening_sp500_volatility.py
- Tests: research/test_anfci_tightening_sp500_volatility.py
