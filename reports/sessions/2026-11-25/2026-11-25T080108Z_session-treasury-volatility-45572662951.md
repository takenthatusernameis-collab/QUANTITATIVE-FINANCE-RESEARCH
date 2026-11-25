# Session report — Treasury auction demand and yield volatility (2026-11-25T080108Z)

- Hypothesis: QFR-2026-11-25-UST-AUCTION-VOLATILITY-01
- Status: INCONCLUSIVE
- Disposition: INCONCLUSIVE — mixed or statistically uncertain volatility-forecast evidence
- Daily real-data backtest KPI: MET
- GitHub run: 45572662951, attempt 1
- Triggering commit: 9b5753f134a693387a413430a2abdba327db85c0
- Data scope: 10-year nominal Treasury Notes 2008-05-07 to 2026-11-10; FRED DGS10 (Board of Governors H.15 via FRED); Treasury XML all-years cross-check attempted 2008-01-02 to 2026-11-23

## Preregistered method

Target: root-sum-square of five consecutive observed daily DGS10 changes strictly after record_date, transformed with log1p. Baseline: pre-event five-change variation plus bid-to-cover. Augmented: baseline plus primary-dealer accepted share. Rolling 52-event OLS; training targets must end strictly before the forecast record_date. High-stress labels use only the preceding 26 auctions.

## Data provenance

- Auction rows returned: 1430
- Selected nominal 10-year auctions: 226
- Updated API merge: MERGED_VERIFIED_SLICE; appended=1
- Yield source: FRED DGS10 (Board of Governors H.15 via FRED); Treasury XML all-years cross-check attempted
- Yield observations: 4726
- Yield coverage: 2008-01-02 to 2026-11-23
- Treasury XML cross-check: VERIFIED

## Forecast results

| Metric | Validation 2019–2022 | Test 2023 onward |
|---|---:|---:|
| Forecast count | 50 | 46 |
| Baseline RMSE, log1p | 0.469634 | 0.395509 |
| Augmented RMSE, log1p | 0.484415 | 0.404907 |
| RMSE improvement | -3.147204% | -2.376276% |
| Baseline RMSE, variation bp | 6.047163 | 4.877838 |
| Augmented RMSE, variation bp | 6.275385 | 4.996338 |

## Test-period uncertainty

- Paired squared-log-loss 95% block interval: [-0.027944, 0.010815]
- High-stress events: None; other events: None
- High-stress minus other variation: None bp
- Event-study 95% block interval: [None, None] bp

## Scientific disposition

INCONCLUSIVE — mixed or statistically uncertain volatility-forecast evidence

This is a daily reference-yield variation forecast, not a tradable strategy backtest. It does not measure intraday Treasury futures volatility. No causal or live-trading claim is made.

## Limitations

- No missing yield observations are filled; each window requires six actual observations.
- Aggregate bidder classes are not individual bidder identities or structural demand curves.
- Updated API rows are admitted only through the existing reconciled, overlap-verified adapter.
- DGS10 is not an executable quote; no P&L or risk-adjusted trading claim is permitted.

## Reproducibility

- Manifest: reports/generated/treasury-auction-volatility/45572662951-attempt-1/manifest.json
- Source: research/treasury_auction_volatility.py
- Tests: research/test_treasury_auction_volatility.py
