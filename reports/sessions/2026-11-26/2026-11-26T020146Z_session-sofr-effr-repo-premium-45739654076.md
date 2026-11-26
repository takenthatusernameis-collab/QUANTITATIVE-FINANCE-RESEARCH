# Research session — SOFR-EFFR repo funding premium and S&P 500 volatility (2026-11-26T02:01:49.707258+00:00)

- Hypothesis: QFR-2026-11-26-SOFR-EFFR-REPO-PREMIUM-SP500-RV-01
- Status: REJECTED
- Disposition: REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse
- Daily real-data backtest KPI: This distinct real-data backtest completed on UTC date 2026-11-26; the 2026-11-26 minimum was already met by the earlier STLFSI4 screen.
- GitHub run: 45739654076, attempt 1
- Triggering commit: 70779dbf0f442d4de4a0da1928f256f09cd55cbe

## Preregistered mechanism and method

- Predictor: five-common-observation change in the SOFR minus EFFR spread, in basis points; positive means the secured overnight repo rate widened relative to the unsecured effective federal funds rate.
- Signal: S&P 500 close on date t; use only the latest common SOFR/EFFR observation dated strictly before t.
- Baseline: prior-five and prior-twenty-session S&P 500 realized volatility plus signal-date log VIX. Augmented model adds only the five-observation SOFR-EFFR spread change.
- Target: next-five-session S&P 500 realized volatility; event origins are spaced six S&P 500 observations apart.
- Rolling training window: 104 prior events whose target end is strictly earlier than the current signal date.
- Validation: 2019–2021. Test: 2022 onward. Primary metric: RMSE in log1p realized-volatility space.

## Data provenance

| Source | First date | Last date | Rows | SHA-256 |
|---|---|---:|---:|---|
| SOFR | 2018-04-03 | 2026-11-24 | 2159 | 555f9196c39ce58e0db105f4b15cb8248ab7b1e222d1a0b08248138f344800b7 |
| EFFR | 2018-04-03 | 2026-11-24 | 2171 | 21f9a4a13c6a57190460d955a87383f75f8025443405abbbbea71653ea40fdb9 |
| SP500 | 2018-04-03 | 2026-11-24 | 2175 | b9d6b7dd63cd2118e18f015de4a77e03fe2e3d449ed749f94a69037737f8c6d6 |
| VIXCLS | 2018-04-03 | 2026-11-24 | 2208 | fcb51ac72610621e2df10ddf77dc707525d0e1f6714e80dd0d72efa3736d4e97 |

## Frozen walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 51 | 204 |
| Baseline RMSE, log1p RV | 0.30627173 | 0.26935296 |
| Augmented RMSE, log1p RV | 0.30667640 | 0.27522830 |
| RMSE improvement | -0.1321% | -2.1813% |

- Accepted non-overlapping events: 359 of 359 candidate S&P 500 origins.
- Skipped events: {"incomplete_price_window": 0, "insufficient_five_observation_spread_history": 0, "irregular_funding_observation_window": 0, "missing_vix_on_signal_date": 0, "no_strictly_prior_common_rate_observation": 0, "overlapping_target_window": 0, "stale_common_rate_observation": 0}.
- Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.021, "ci_95_high": -0.00011120124824089034, "ci_95_low": -0.0071170259488151635, "mean_baseline_minus_augmented_squared_log_loss": -0.003199601622904665, "observations": 204, "reps": 2000, "status": "COMPUTED"}.

## Verified versus unverified

**VERIFIED:** deterministic parser, timing, prior-observation, event-maturity and decision tests; FRED source schema and coverage acceptance; exact-date VIX alignment; no same-date rate observations; non-overlapping target windows; and the recorded result under this code/data vintage.

**UNVERIFIED:** historical point-in-time SOFR/EFFR vintages, future-regime stability, independent source reconstruction and instrument-level economic value.

## Explicit limitations

- SOFR and EFFR can be revised; current FRED vintages are used, not historical ALFRED vintages.
- SOFR-EFFR spread dynamics can reflect calendar effects, policy operations, collateral composition and other funding conditions; this screen does not identify a causal channel.
- SOFR is a secured Treasury-repo rate; EFFR is an unsecured overnight federal-funds transaction rate. The spread is a proxy, not a pure liquidity shock.
- SP500 is a cash price index, not an executable futures series or total-return index.
- No raw source data are committed; only retrieval metadata, hashes and aggregate metrics are retained.
- Forecasting only: no trading P&L, transaction-cost model, live strategy or deployment conclusion.

## Reproducibility

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45739654076
- Manifest: ../../generated/sofr-effr-repo-premium-sp500-rv/45739654076-attempt-1/manifest.json
- Source: ../../../research/sofr_effr_repo_premium_sp500_rv.py
- Tests: ../../../research/test_sofr_effr_repo_premium_sp500_rv.py
