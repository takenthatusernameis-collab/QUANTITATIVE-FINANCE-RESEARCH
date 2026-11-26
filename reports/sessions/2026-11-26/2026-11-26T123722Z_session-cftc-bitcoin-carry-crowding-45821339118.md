# Session report — CFTC Bitcoin futures short crowding and BTC downside semivariance (2026-11-26T123722Z)

- Hypothesis: QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01
- Status: INCONCLUSIVE
- Disposition: INCONCLUSIVE/INFEASIBLE — bounded source, timing or execution gate failed: ValueError: Unexpected market name for Bitcoin contract code 133741: 'BITCOIN'
- Completed real-data backtest: False
- Daily research KPI: MET before this additional study by distinct real-data hypothesis backtests on 2026-11-26; this run did not count toward the KPI
- GitHub run: 45821339118, attempt 1
- Triggering commit: 8f2bd3b352ae4f3ae720cc79daec4709f77326c3
- Data scope: not established

## Preregistered method

- CFTC market: Bitcoin, CME, contract code 133741, TFF futures-only dataset gpe5-46if.
- Availability: first Coinbase BTCUSD close on or after the CFTC report date plus 14 calendar days.
- Feature: gross leveraged-fund short positions / total open interest, ranked against the prior 52 non-backlog reports only; high crowding is a prior-only percentile at or above 90%.
- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.
- Target: log1p of next-five-observation BTC downside semivariance.
- Rolling training window: 52 prior events with target_end_date strictly earlier than the current signal.
- Validation: 2019–2021. Test: 2022 onward. Paired loss and event-study uncertainty use 2,000 four-event circular-block bootstrap replications.

## Data provenance

- CFTC rows: None; coverage: None to None; SHA-256: None
- Coinbase CBBTCUSD rows: None; coverage: None to None; SHA-256: None
- Accepted events: None; skipped: None

## Walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | None | None |
| Baseline RMSE, log1p semivariance | None | None |
| Augmented RMSE, log1p semivariance | None | None |
| RMSE improvement | None% | None% |

## Test-period uncertainty and event study

- Paired squared-loss bootstrap: None
- High-crowding event study: None

## Scientific interpretation

INCONCLUSIVE/INFEASIBLE — bounded source, timing or execution gate failed: ValueError: Unexpected market name for Bitcoin contract code 133741: 'BITCOIN'

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

- Manifest: reports/generated/cftc-bitcoin-carry-crowding/45821339118-attempt-1/manifest.json
- Source: research/cftc_btc_carry_crowding.py
- Tests: research/test_cftc_btc_carry_crowding.py
- Preregistration: research/PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md

## Execution error

ValueError: Unexpected market name for Bitcoin contract code 133741: 'BITCOIN'
