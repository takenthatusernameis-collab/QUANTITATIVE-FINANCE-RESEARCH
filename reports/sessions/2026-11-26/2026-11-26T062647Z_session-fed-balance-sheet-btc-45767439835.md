# Research session — Fed balance-sheet impulse and BTC downside semivariance (2026-11-26T062647Z)

- **Hypothesis:** QFR-2026-11-26-FED-BALANCE-SHEET-BTC-DOWNSIDE-01
- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority
- **Daily KPI:** The 2026-11-26 minimum was already met by distinct real-data forecast screens; this is an additional hypothesis screen.
- **GitHub run:** 45767439835, attempt 1
- **Triggering commit:** 82eab87d53a7b16196a7964af40dc63bd9225c9b

## Preregistered method

- Predictor: negative four-week log change in WALCL; positive values mean Federal Reserve total-assets contraction.
- Availability: use the Wednesday observation only at the close of the UTC BTC daily candle dated seven calendar days later.
- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.
- Target: next-five-session BTC downside semivariance, transformed with log1p.
- Rolling training window: 104 prior weekly events; each training target must be fully matured before the current signal.
- Validation: 2019–2021. Test: 2022 onward.

## Data provenance

| Source | First | Last | Rows | SHA-256 / manifest |
|---|---|---|---:|---|
| WALCL | 2017-08-16 | 2026-11-18 | 484 | d8d5b1a1d2f0b98de83790cf077279bf8a1bee8be0b5456d3267d355494cadc6 |
| BTCUSDT | 2017-08-17 | 2026-11-24 | 3387 | 135 archives; 1e9dabf9de7315ef922c711f37d3bcd2599ba9be29ac93048b515b31ceaa6748 |

## Walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 120 | 255 |
| Baseline RMSE (log1p semivariance) | 1.0250361787020226 | 0.8668066907987321 |
| Augmented RMSE (log1p semivariance) | 1.0673290310779027 | 0.8760063127890909 |
| RMSE improvement | -4.125986307081812% | -1.0613233709446463% |

## Paired test-loss uncertainty

- {"block_size_events": 4, "bootstrap_fraction_positive": 0.05, "ci95_high": 0.002943798774582669, "ci95_low": -0.03833083561399792, "mean_baseline_minus_augmented_squared_loss": -0.01603322083288992, "observations": 255, "reps": 2000}

## Interpretation

INCONCLUSIVE — frozen validation/test and paired-loss rules do not establish improvement or decisive inferiority

## Verified / unverified

**VERIFIED:** source schemas, coverage gates, archive checksums, event timing, non-overlapping target windows, walk-forward maturity and metrics, if the backtest completed.
**UNVERIFIED:** historical point-in-time FRED vintages, independent replication, future-regime stability, causality and instrument-level economic value.

## Limitations

- WALCL is total Federal Reserve assets, not bank reserves or a comprehensive net-liquidity measure; valuation changes, facilities and other balance-sheet items can move it independently of policy QT.
- The screen uses the current FRED vintage, not historical ALFRED vintages; a conservative release lag does not remove revision look-ahead.
- H.4.1 is normally released Thursday around 4:30 p.m. Eastern; the fixed seven-day lag is conservative but does not reconstruct every historical release timestamp or revision.
- BTCUSDT is one venue's spot series. Binance Vision archives are checksum-verified, but this is not an exchange-independent consolidated market history.
- Forecast-only: no causal claim, trading P&L, transaction-cost model, profitability, live strategy or deployment conclusion.
- No raw FRED or Binance observations are committed; source hashes and aggregate metrics are retained.
