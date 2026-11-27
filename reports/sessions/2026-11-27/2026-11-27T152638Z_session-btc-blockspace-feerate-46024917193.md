# Research session — Bitcoin blockspace fee-rate pressure and BTC downside semivariance (2026-11-27T152638Z)

- **Hypothesis:** QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01
- **Status:** INCONCLUSIVE
- **Decision:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish incremental predictive value or decisive inferiority
- **Daily KPI:** The UTC 2026-11-27 minimum was already met by the distinct ETF-relative-flow real-data forecast screen; this is an additional hypothesis backtest.
- **Implementation timebox:** MEDIUM; 4 substantive cycles maximum; implementation deadline 2026-11-30T13:55:51Z; final conclusion deadline 2026-12-02T13:55:51Z.
- **GitHub run:** 46024917193, attempt 1
- **Triggering commit:** 8ec52261714abc586bd42df962a7ba0c9d41e34a

## Frozen method

- Predictor: log1p of the daily median of two 12-hour-bin avgFee_75 averages at t-1 minus the same value at t-8; one full UTC-day embargo.
- Baseline: prior 5- and 20-session BTC momentum, prior 5- and 20-session downside semivariance, and prior 20-session total realized variance.
- Augmented model: baseline plus exactly one blockspace fee-pressure feature.
- Target: log1p of next-five-session BTC downside semivariance; signal-day return excluded.
- Event spacing: every six UTC calendar days; five-session target windows do not overlap.
- Rolling training: latest 65 fully matured prior events. Validation: 2025-H1. Test: 2025-07-01 onward.
- Estimator: standardized OLS with the repository's fixed 1e-8 coefficient ridge stabilization; no tuning.

## Data provenance

| Source | Coverage | Rows / events | SHA-256 |
|---|---|---:|---|
| Mempool avgFee_75 | 2023-11-28 to 2026-11-26 | 1095 completed dates | 41738f90d16c9a7cd856435b0fe3f8164d0f743ba994b64d4987bfb4be4ceaa1 |
| Binance BTCUSDT | 2023-11-28 to 2026-11-25 | 1094 candles; 61 archives | 337663735a90c3f86418aa550de5a715477f3e3a98493229af828e6496ae1e7a |
| Previously accepted full BTC history | 2017-08-17 to 2026-11-25 | 3,388 daily candles | 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe |

## Walk-forward results

| Metric | Validation 2025-H1 | Test 2025-07-01 onward |
|---|---:|---:|
| Forecasts | 29 | 85 |
| Baseline RMSE, log1p semivariance | 0.8872549546059562 | 0.7174010643964365 |
| Augmented RMSE, log1p semivariance | 0.8917247810925903 | 0.7208686337088329 |
| RMSE improvement | -0.5037815188779992% | -0.4833515706188392% |

## Paired test-loss uncertainty

- {"block_size_events": 5, "bootstrap_fraction_positive": 0.1655, "ci_95_high": 0.005471370322788428, "ci_95_low": -0.016317454039132775, "mean_baseline_minus_augmented_squared_loss": -0.004987299868099742, "observations": 85, "reps": 2000, "seed": 20261127, "status": "COMPUTED"}

## Interpretation

INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish incremental predictive value or decisive inferiority

## Verified / unverified

**VERIFIED:** accepted Mempool schema and coverage, one-day embargo, Binance archive checksum identity against previously accepted evidence, event maturity, walk-forward mechanics and the frozen metrics under this code/data vintage.
**UNVERIFIED:** point-in-time API publication/revision history, independent source replication, causal interpretation, future-regime stability and instrument-level economic value.

## Limitations

- Mempool's three-year endpoint is current-vintage and does not reconstruct historical API publication timestamps or point-in-time revisions; the frozen one-day embargo does not eliminate all vintage risk.
- Each avgFee_75 value is an average of underlying block-level p75 feerates within a 12-hour bin; the daily feature is the median of two bin averages, not the median of all block-level p75 values in a UTC day.
- The fee-rate series is a blockspace price/congestion proxy, not a direct measure of transaction count, backlog, exchange flows, investor positioning or forced selling.
- The model is a BTC Spot forecast screen, not an executable strategy or P&L. No trading profitability, causal or live-deployment claim is made.
- The price series is one venue's BTCUSDT Spot close. The downloaded archive subset was checksum-matched to the previously accepted 2017-08-17 through 2026-11-25 source manifest.
- No raw fee-rate or price observations are saved or committed; only hashes, source metadata and aggregate results are retained.

## Reproducibility

- Workflow: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024917193
- Implementation: research/btc_blockspace_fee_rate_btc_downside.py
- Tests: research/test_btc_blockspace_fee_rate_btc_downside.py


## Independent audit — 2026-11-27T15:29:39.849Z

The separate Cycle 4 audit confirmed the following:

- All 61 downloaded Binance archive and checksum-sidecar hashes exactly match the previously accepted full-history manifest.
- Mempool accepted 1,095 contiguous completed UTC dates from 2023-11-28 through 2026-11-26 using one GET and zero retries; the two partial boundary dates were excluded.
- All 179 six-day-spaced event origins passed; five-session target windows do not overlap. The 65-event warm-up leaves 29 validation and 85 test forecasts.
- Independently recomputed validation and test RMSE improvements are -0.5037815188779992% and -0.4833515706188392%, respectively.
- The 2,000-replication paired-loss 95% interval is [-0.016317454039132775, +0.005471370322788428], crossing zero. The frozen decision is **INCONCLUSIVE**, not REJECTED.
- No raw observations were saved. The result remains forecast-only and does not establish a trading edge.

Full audit: [Cycle 4 independent audit](20261127T152939Z_session-btc-blockspace-feerate-independent-audit.md).
