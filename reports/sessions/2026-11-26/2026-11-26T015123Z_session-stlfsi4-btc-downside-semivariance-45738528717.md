# Research session — STLFSI4 and BTC downside semivariance (2026-11-26T01:51:23.747353+00:00)

- **Hypothesis:** QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01
- **Status:** REJECTED
- **Disposition:** REJECTED — both chronological periods worsen and paired-loss inference favors the baseline
- **Daily KPI:** This distinct real-data backtest completed on UTC date 2026-11-26; the 2026-11-25 minimum was already met by earlier experiments.
- **GitHub run:** 45738528717, attempt 1
- **Triggering commit:** 6ac99579b019ff0eb0cce64e02a24074d498807e

## Preregistered method

- Predictor: four-week change in STLFSI4; positive means increasing financial stress.
- Signal: close of the Binance BTCUSDT UTC daily candle dated seven calendar days after the Friday observation; historical bars are read from checksum-verified official Vision archives.
- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session realized variance.
- Target: mean squared negative BTC log returns over the next five UTC daily sessions.
- Rolling training window: 104 prior weekly events; every training target must be fully matured before the signal.
- Validation: 2019–2021. Test: 2022 onward. Primary metric: RMSE in log1p downside-semivariance space.

## Data provenance

| Source | First | Last | Rows | Hashes |
|---|---|---:|---:|---|
| STLFSI4 | 2017-08-18 | 2026-11-20 | 484 | f39053f0fdc3cd2ceaf942587aa57fe000b490fda26f02cefa243763d6b7279e |
| BTCUSDT | 2017-08-17 | 2026-11-24 | 3387 | 135 archives; manifest SHA-256 1e9dabf9de7315ef922c711f37d3bcd2599ba9be29ac93048b515b31ceaa6748 |

## Frozen results

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 120 | 254 |
| Baseline RMSE | 0.99931883 | 0.82142171 |
| Augmented RMSE | 1.00950156 | 0.83156709 |
| RMSE improvement | -1.0190% | -1.2351% |

- Accepted events: 478 of 484.
- Skipped: {"incomplete_target": 1, "insufficient_history": 0, "invalid_returns": 0, "irregular_stress_window": 0, "missing_signal": 1}.
- Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.004, "ci_95_high_bp2": -0.0037903051971731384, "ci_95_low_bp2": -0.03172449392485483, "observations": 254, "observed_mean_baseline_minus_augmented_squared_loss_bp2": -0.016770207106700682, "reps": 2000, "status": "COMPUTED"}.

## Verified / unverified

**VERIFIED:** public BTCUSDT spot symbol status, complete daily candle coverage and UTC continuity; FRED weekly-Friday schema and freshness; conservative release lag; deterministic tests; event maturity and result under this code/data vintage.

**UNVERIFIED:** historical point-in-time STLFSI4 vintages, future-regime stability, cross-venue replication, economic value and trading profitability.

## Limitations

- STLFSI4 is revised. This screen uses the current FRED vintage, not historical ALFRED vintages; publication lag does not remove revision look-ahead.
- FRED labels STLFSI4 weekly ending Friday and subject to revision. Its calendar lists 9:00 a.m. US Central releases on Wednesdays with holiday shifts; Friday plus seven calendar days is a conservative signal date.
- STLFSI4 is a composite of 18 weekly financial variables, not an exogenous shock or causal measure.
- BTCUSDT is one venue's spot series. Binance Vision archive files are checksummed but may be revised by the publisher; the snapshot is identified by per-file SHA-256 hashes. This is a forecast screen, not a trading strategy, executable P&L, or tradable-premium claim.
- No raw FRED or Binance observations are committed; only source hashes, retrieval metadata and aggregate metrics are retained.

## Reproducibility

- Workflow: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45738528717
- Source: research/stlfsi4_btc_downside_semivariance.py
- Tests: research/test_stlfsi4_btc_downside_semivariance.py
