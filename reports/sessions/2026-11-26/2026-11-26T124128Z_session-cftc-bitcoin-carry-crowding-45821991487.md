# Session report — CFTC Bitcoin futures short crowding and BTC downside semivariance (2026-11-26T124128Z)

- Hypothesis: QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01
- Status: INCONCLUSIVE
- Disposition: INCONCLUSIVE — the frozen validation/test and paired-event criteria do not establish incremental predictive value or decisive inferiority
- Completed real-data backtest: True
- Daily research KPI: MET before this additional study by distinct real-data hypothesis backtests on 2026-11-26; this run is additional research, not a quota claim
- GitHub run: 45821991487, attempt 1
- Triggering commit: 464a6cf4f7361c3af25325ea3ea98366b5eafbf0
- Data scope: CFTC TFF futures-only Bitcoin CME contract 133741, 2018-04-10 to 2026-11-17 (450 rows; known 2025-09-30 to 2026-01-20 catch-up period excluded from events/history); FRED/Coinbase CBBTCUSD 2016-11-25 to 2026-11-25 (3652 daily observations); 375 accepted weekly events

## Preregistered method

- CFTC market: Bitcoin, CME, contract code 133741, TFF futures-only dataset gpe5-46if; report-date cutoff 2026-11-17.
- Availability: first Coinbase BTCUSD close on or after the CFTC report date plus 14 calendar days; sample as-of date 2026-11-26.
- Feature: gross leveraged-fund short positions / total open interest, ranked against the prior 52 non-backlog reports only; high crowding is a prior-only percentile at or above 90%.
- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.
- Target: log1p of next-five-observation BTC downside semivariance.
- Rolling training window: 52 prior events with target_end_date strictly earlier than the current signal.
- Validation: 2019–2021. Test: 2022 onward. Paired loss and event-study uncertainty use 2,000 four-event circular-block bootstrap replications.

## Data provenance

- CFTC rows: 450; coverage: 2018-04-10 to 2026-11-17; SHA-256: 0cb78b07cf2a380504432489a29f96ccc07f48043023c8897b5d67dff854dd20
- Coinbase CBBTCUSD rows: 3652; coverage: 2016-11-25 to 2026-11-25; SHA-256: d31b13b29bae8cd1bda89cf5d728772262db139ff1b83130ec6bfd4b95b3eb73
- Accepted events: 375; skipped: {'known_publication_backlog': 17, 'insufficient_prior_position_history': 52, 'availability_date_not_reached': 1, 'no_signal_close': 0, 'signal_close_too_far_after_lag': 0, 'insufficient_btc_pre_history': 1, 'incomplete_btc_return_window': 4, 'overlapping_target_window': 0}

## Walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 85 | 238 |
| Baseline RMSE, log1p semivariance | 0.9668652188985765 | 0.8427012318770031 |
| Augmented RMSE, log1p semivariance | 0.9901395999151835 | 0.8521143314575398 |
| RMSE improvement | -2.40720015175647% | -1.117015049280313% |

## Test-period uncertainty and event study

- Paired squared-loss bootstrap: {'observations': 238, 'reps': 2000, 'block_size_events': 4, 'mean_baseline_minus_augmented_squared_loss': -0.015953467668311457, 'ci95_low': -0.053352059202934406, 'ci95_high': 0.019637359679962507, 'bootstrap_fraction_positive': 0.197}
- High-crowding event study: {'high_n': 46, 'other_n': 192, 'mean_high_semivariance_pct2': 2.263007598693932, 'mean_other_semivariance_pct2': 3.311503936452216, 'high_minus_other_mean_semivariance_pct2': -1.0484963377582837, 'reps': 2000, 'block_size_events': 4, 'ci95_low': -2.430690592742438, 'ci95_high': 0.34845402918518076}

## Scientific interpretation

INCONCLUSIVE — the frozen validation/test and paired-event criteria do not establish incremental predictive value or decisive inferiority

The leveraged-fund category is not a direct measure of bearish intent. CME Bitcoin futures shorts may include cash-and-carry basis positions as well as directional and other strategies. This study tests a predictive association, not trader intent, causality or a tradable strategy.

## Limitations

- CFTC classifications are based on predominant business purpose and do not reveal the intent of each position.
- CFTC data cover CME Bitcoin futures only, not offshore perpetual swaps or the global derivatives market.
- A fixed 14-day lag is conservative for the historical weekly Tuesday/Friday schedule; the 2025 shutdown catch-up reports are excluded. CFTC announced a move toward twice-weekly publication by the end of 2026, so a future schedule change requires a new timing specification.
- Current CFTC data can reflect revised historical classifications and positions; exact historical publication timestamps are not available for the full history.
- CBBTCUSD is Coinbase's daily 5 p.m. Pacific price series distributed by FRED; raw observations are not committed or redistributed.
- Current FRED vintage is used; historical ALFRED vintages are not reconstructed.
- Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.

## Reproducibility

- Manifest: reports/generated/cftc-bitcoin-carry-crowding/45821991487-attempt-1/manifest.json
- Source: research/cftc_btc_carry_crowding.py
- Tests: research/test_cftc_btc_carry_crowding.py
- Preregistration: research/PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md
