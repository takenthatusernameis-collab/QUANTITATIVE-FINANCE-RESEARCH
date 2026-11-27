# BTC taker-flow/price-response downside forecast — 2026-11-27T020646Z

**Hypothesis:** QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01

**Status:** COMPLETE  
**Disposition:** INCONCLUSIVE  
**Reason:** Evidence is mixed, statistically uncertain or insufficient under the frozen rule.

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994
- Triggering source commit: 7e968673f39e26001ea45f6664129efe77240db2
- Source-preflight run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925248340
- Source-preflight archive-manifest SHA-256: 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe

## Data and provenance

- Instrument: Binance BTCUSDT Spot 1d UTC
- Frozen source coverage: 2017-08-17 through 2026-11-25
- Checksum-verified archives: 136
- Archive-manifest SHA-256: 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe
- Observed daily rows: 3388
- Missing dates: 0
- Zero-volume days: 0
- Raw observations committed: No

## Frozen feature and target

The single augmented feature is signed_taker_absorption:
max(taker_imbalance,0) * max(-signal_day_return,0) minus
max(-taker_imbalance,0) * max(signal_day_return,0).

The target is the mean squared negative log return over the next five UTC daily sessions,
scaled by 10,000. The signal-day return is excluded from the target. Every six-day event
origin has a five-session forward window, so accepted target windows do not overlap.

## Event construction

- Candidate origins: 561
- Accepted events: 561
- Walk-forward forecasts: 457
- Validation forecasts: 159
- Test forecasts: 298
- First accepted signal: 2017-09-06
- Last accepted signal: 2026-11-18

## Forecast results

| Metric | Validation | Test |
|---|---:|---:|
| Baseline log-semivariance RMSE | 1.0488537669869709 | 0.87015502774617 |
| Augmented log-semivariance RMSE | 1.0455820428217992 | 0.8792838589682755 |
| RMSE improvement (%) | 0.3119332997745025 | -1.0491040022776774 |

Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.045, "ci_95_high": 0.0018984357165540003, "ci_95_low": -0.037146350903781586, "observations": 298, "observed_mean_baseline_minus_augmented_squared_loss": -0.015970332330204357, "reps": 2000, "seed": 20261127, "status": "COMPUTED"}.

## Interpretation and limitations

The signed feature is a daily aggressor-flow/price-response mismatch proxy. Binance Spot is one venue,
and daily aggregates do not reveal order-book depth, cancellations, trader identity or actual passive
liquidity absorption. The experiment is a forecast screen, not a trading P&L or deployment test.

No strategy profitability, CAGR, Sharpe, drawdown or live-trading claim is made. The disposition follows
the frozen validation/test and paired-loss rules; no parameter retuning was performed.

## Evidence files

- Manifest: [reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json](../../generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json)
- Preregistration: [frozen protocol](../../../research/PREREGISTERED-QFR-2026-11-27-TAKER-ABSORPTION-BTC-DOWNSIDE-01.md)
- Registry: [hypothesis registry](../../../research/HYPOTHESIS-REGISTRY.md)
