# Research session — Bitcoin Wikipedia attention and BTC downside semivariance

- **Hypothesis:** QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01
- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule
- **Daily KPI:** MET before this additional study by distinct 2026-11-26 real-data backtests, including MEXC BTC funding run 45850573983 and DeFiLlama stablecoin-supply run 45855398478.
- **Timebox:** LOW; two substantive cycles maximum; implementation deadline 2026-11-27T19:02:30Z; final research-conclusion deadline 2026-11-28T19:02:30Z.
- **GitHub run:** 45898030626, attempt 1
- **Triggering commit:** b3eca60343485c62b931c312c4148d9d8125384e

## Preregistered method

- Signal: close of Binance BTCUSDT UTC daily candle on date d.
- Feature: log1p(Wikipedia user pageviews[d-2]) minus log1p(pageviews[d-9]).
- Baseline: prior-five and prior-twenty-session downside semivariance, prior-twenty-session realized variance, and prior-five/prior-twenty-session BTC log returns.
- Augmented model: frozen baseline plus the single Wikipedia-attention feature.
- Target: next-five-session BTC downside semivariance in percentage-points-squared units, forecast in log1p space.
- Event spacing: six calendar days; 104 prior fully matured training events.
- Validation: 2019-2021; test: 2022-11-20.

## Source coverage and provenance

| Source | First | Last | Rows | Digest / archive manifest |
|---|---|---|---:|---|
| Wikimedia Bitcoin pageviews | 2017-08-17 | 2026-11-18 | 3381 calendar; 3381 observed | b1bc21a94749fa1775ed5a3482e8076734bcfff58a729a75da29c1f6d4023b60 |
| Binance BTCUSDT Spot | 2017-08-17 | 2026-11-25 | 3388 | 136 archives; 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe |

- Reconstructed documented zero-view dates: 0.
- Pageview response chunks: 38.
- Raw pageviews and market observations are not committed.

## Walk-forward results

| Metric | Validation 2019-2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 159 | 298 |
| Baseline RMSE, log1p semivariance | 1.0488537669869709 | 0.87015502774617 |
| Augmented RMSE, log1p semivariance | 1.0647841913352571 | 0.878108981441773 |
| RMSE improvement | -1.518841315129126% | -0.9140846679016309% |

## Paired test-loss uncertainty

- {"block_size_events": 4, "bootstrap_fraction_positive": 0.1085, "ci_95_high": 0.008245217625406073, "ci_95_low": -0.035549994406648563, "observations": 298, "observed_mean_baseline_minus_augmented_squared_loss": -0.01390561097676914, "reps": 2000, "seed": 20261126, "status": "COMPUTED"}

## Interpretation

INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule

## Verified / unverified

**VERIFIED:** current source schemas, frozen coverage, response digests, Binance archive checksums, feature embargo, non-overlapping targets, matured rolling training and computed forecast metrics.
**UNVERIFIED:** historical point-in-time pageview revisions/publication timestamps, investor-specific interpretation, causality, independent replication and instrument-level economic value.

## Limitations

- Wikipedia pageviews proxy public interest; they do not identify investors, sentiment, search intent or order flow.
- Pageview counts can be affected by news, article edits, platform changes and non-investor activity.
- The current API vintage is used. Historical point-in-time revisions and exact historical publication timestamps are not reconstructed; the two-day embargo is not proof of historical availability.
- The documented zero-view reconstruction applies only to omitted daily dates; no interpolation or forward-fill is performed.
- BTCUSDT is one venue's Spot series, not consolidated executable prices or derivatives P&L.
- This is an observational forecast screen, not causal evidence, a trading strategy or a live signal.
- No raw pageview or market observations are committed; response digests and Binance archive checksums are retained.
