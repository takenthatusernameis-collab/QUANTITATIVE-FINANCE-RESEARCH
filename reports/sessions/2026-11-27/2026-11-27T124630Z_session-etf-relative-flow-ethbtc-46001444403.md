# BTC/ETH ETF relative-flow forecast for ETH/BTC — 2026-11-27T124630Z

**Hypothesis:** QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01

**Status:** COMPLETE  
**Disposition:** INCONCLUSIVE  
**Reason:** INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish incremental predictive value or decisive inferiority

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444403
- Triggering source commit: 107f1aa5199d6f0e3905b22707bd1da3445392b3
- Frozen source-preflight run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45996756282
- Frozen flow-panel SHA-256: 4d7d2a8c54b5b6eebbf48631f4641ad24d4692a21dc5d6681beba65e4ae79a18
- Frozen BTC archive-manifest SHA-256: f70f8a1b01098cee6f8299514888363b04956f66cf122ffae95579b12e08faf5
- Frozen ETH archive-manifest SHA-256: 0ef90c2cde6888e0ca7512670a84ff2fba17995950870ce847f0d22e635dc314

## Data and provenance

- Farside common BTC/ETH flow panel: 583 rows, 2024-07-23 through 2026-11-16
- Binance BTCUSDT and ETHUSDT Spot 1d UTC: 879 / 879 rows
- Common price range: 2024-07-01 through 2026-11-26
- Checksum-verified archive counts: BTC 54; ETH 54
- Raw observations saved: No

## Frozen signal, target and features

Each common Farside flow observation is embargoed for five calendar days. At the Binance daily close dated five days after the U.S. ETF flow date, each asset's current net flow is standardized against the preceding 60 common valid observations for that same asset. The current observation is excluded from its own z-score.

- Common flow pressure: (z_BTC + z_ETH) / 2
- Relative flow pressure: z_ETH - z_BTC
- Target: cumulative ETH/BTC log return over the next five complete UTC daily candles, in basis points
- Baseline: prior 5-session and 20-session ETH/BTC returns, log prior 20-session ETH/BTC realized variance, prior 5-session BTC and ETH returns, and common ETF flow pressure
- Augmented model: baseline plus relative flow pressure
- Rolling training: 65 most recent events whose five-session target ended strictly before the current signal date

## Event construction

- Candidate origins after warm-up: 262
- Accepted events: 262
- Walk-forward forecasts: 196
- First accepted signal: 2024-10-21
- Last accepted signal: 2026-11-21
- Overlapping five-session target windows: True
- Skipped events: {"incomplete_target": 0, "insufficient_price_history": 0, "invalid_price_returns": 0, "invalid_variance": 0, "missing_signal_anchor": 0, "zero_flow_standard_deviation": 0}

## Forecast results

| Metric | Validation 2025 | Test 2026 |
|---|---:|---:|
| Forecasts | 84 | 112 |
| Baseline RMSE (bps) | 706.6755464035765 | 311.99779016643106 |
| Augmented RMSE (bps) | 710.4849514203687 | 314.8169358128975 |
| RMSE improvement (%) | -0.5390599740119886 | -0.9035787224526823 |

Paired test squared-loss bootstrap: {"block_size_events": 5, "bootstrap_fraction_positive": 0.204, "ci_95_high_bp2": 2428.2418167694427, "ci_95_low_bp2": -5801.035715112694, "observations": 112, "observed_mean_baseline_minus_augmented_squared_loss_bp2": -1767.0820058856775, "reps": 2000, "seed": 20261127, "status": "COMPUTED"}.

## Interpretation and limitations

Farside's current-vintage aggregator tables have no historical as-of snapshots or verified publication timestamps. The fixed five-calendar-day embargo is conservative but does not prove that the values were available at the historical signal time. ETF net flows are creations/redemptions, not secondary-market ETF volume, exchange spot order flow or direct evidence of asset purchases at a particular timestamp.

The result is a forecast screen for ETH/BTC, not a trading P&L. No CAGR, Sharpe, drawdown, profitability or deployment claim is made. No parameter tuning was performed. No raw flow or price observations were saved or committed.

## Evidence files

- Manifest: reports/generated/etf-relative-flow-ethbtc/46001444403-attempt-1/manifest.json
- Preregistration: [frozen protocol](../../../research/PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md)
- Registry: [hypothesis registry](../../../research/HYPOTHESIS-REGISTRY.md)
