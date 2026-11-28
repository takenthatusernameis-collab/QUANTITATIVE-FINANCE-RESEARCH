# Independent audit — H.8 C&I credit impulse / BTC downside semivariance

- **Audit status:** PASS
- **Hypothesis:** QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01
- **Original backtest:** #46119814521
- **Audit run:** #46122370665
- **Audited at:** 2026-11-28T07:43:01.290243+00:00
- **Decision:** INCONCLUSIVE

## Source and event reconstruction

- ALFRED: 484 weekly vintages across 41 requests; canonical batch hashes match the original run.
- Binance Spot: 3388 BTCUSDT daily candles across 136 checksum-verified archives; archive-manifest hash matches.
- Events: 477 accepted weekly Sunday events, from 2017-09-10 to 2026-11-15; final target ends 2026-11-20.

## Independent forecast reconstruction

- Reconstructed 373 forecasts: 118 validation and 255 test.
- Every training window contains 104 fully matured prior events.
- Independently recomputed OLS predictions, target values, squared errors, validation/test metrics and paired moving-block bootstrap match the persisted evidence within the recorded numerical tolerance.

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 118 | 255 |
| Baseline RMSE | 1.112084343999 | 0.910563460304 |
| Augmented RMSE | 1.145047341255 | 0.922348150120 |
| RMSE improvement | -2.964073% | -1.294219% |

- Paired test-loss 95% CI: [-0.056887653244, 0.008394558023].
- Bootstrap: 2000 circular moving-block replications, block size 4, seed 20261128.

## Disposition

INCONCLUSIVE — both validation and test RMSE worsen, but the paired test-loss 95% interval crosses zero; the preregistered rejection rule is not met.

This confirms the preregistered INCONCLUSIVE forecast-screen result. It does not establish a causal credit shock, economic value after costs, trading profitability, or permission to promote a strategy.

## Limitations

- ALFRED and Binance data were re-fetched and their canonical source/archive hashes revalidated; the original raw observations were not retained as repository files.
- The audit reuses the admitted source transport and archive adapters but independently reconstructs vintage features, events, matured training windows, OLS fits, every forecast, metrics, and bootstrap inference.
- ALFRED vintage dates have day-level rather than intraday first-publication resolution.
- The study is a single-venue BTCUSDT forecast screen, not causal identification, executable P&L, profitability, or strategy promotion.
- The nominal paired bootstrap does not correct repository-wide multiple testing or research-selection bias.

## Reproducibility

- Original manifest: `reports/generated/h8-ci-credit-impulse-btc-downside/46119814521-attempt-1/manifest.json`
- Original forecast rows: `reports/generated/h8-ci-credit-impulse-btc-downside/46119814521-attempt-1/forecast_rows.csv`
- Independent audit JSON: `reports/generated/h8-ci-credit-impulse-btc-downside/independent-audit/46122370665-attempt-1/audit.json`
