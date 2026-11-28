# Research session — H.8 C&I credit impulse and BTC downside semivariance (2026-11-28T070841Z)

- **Hypothesis:** QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01
- **Status:** BACKTESTED
- **Decision:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule
- **Daily KPI:** The 2026-11-28 UTC minimum was already met by the separate MEXC funding-dispersion / BTC realized-variance backtest #46085887442; this H.8 study is additional research.
- **Timebox:** MEDIUM; four cycles maximum; implementation deadline 2026-12-01T05:49:20Z; final conclusion deadline 2026-12-03T05:49:20Z.
- **GitHub run:** 46119814521, attempt 1
- **Triggering commit:** 85fa08166b24e363f66d7d054b917a821449c0a4

## Cycle accounting

- Cycle 1 source feasibility: PASS; ALFRED preflight run #46115128898.
- Cycle 2 model implementation and deterministic validation: completed in the admitted source commit.
- Cycle 3 immutable empirical run: #46119814521; cycle 4 independent reconstruction remains pending.

## Frozen method

- Predictor: 100 × ln(TOTCI latest available in each Sunday ALFRED vintage / fourth prior weekly observation in the same vintage).
- Vintage gates: no future observation; latest observation Wednesday and 3–14 days old; four weekly gaps each 5–9 days.
- Baseline: prior 5/20-session momentum, prior 5/20-session downside semivariance and prior 20-session total realized variance.
- Augmented model: baseline plus exactly one four-observation TOTCI log change.
- Target: log1p of next-five-session BTC downside semivariance; signal-day return is excluded from the target.
- Rolling training: latest 104 fully matured weekly events. Validation: 2019–2021. Test: 2022 onward.
- Estimator: repository standardized OLS helper with fixed ridge stabilization; no parameter tuning.

## Data provenance

| Source | Coverage | Rows / requests | SHA-256 |
|---|---|---:|---|
| ALFRED H.8 TOTCI | 2017-08-20 to 2026-11-22 | 484 Sunday vintages; 41 requests | sample panel bb50c137a1e1a1d6ce42b79e17899b027476f92b97103522bc3775c2107196c8 |
| Binance BTCUSDT Spot | 2017-08-17 to 2026-11-25 | 3388 candles; 136 archives | 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe |

## Event construction

- Candidate Sunday vintages: 483
- Accepted events: 477
- First/last signal: 2017-09-10 / 2026-11-15
- Last target end: 2026-11-20
- Skipped events: {"incomplete_target": 0, "insufficient_price_history": 3, "invalid_credit_feature": 0, "invalid_price_returns": 0, "missing_signal_anchor": 0, "source_vintage_gate": 3}
- Vintage-gate reasons: {"stale_or_early_latest_observation": 3}

## Walk-forward results

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 118 | 255 |
| Baseline RMSE (log1p semivariance) | 1.112084343998653 | 0.9105634603041463 |
| Augmented RMSE (log1p semivariance) | 1.1450473412550195 | 0.9223481501203709 |
| RMSE improvement | -2.9640734926492645% | -1.2942194948486383% |

## Paired test-loss uncertainty

- {"block_size_events": 4, "bootstrap_fraction_positive": 0.0925, "ci_95_high": 0.008394558023369324, "ci_95_low": -0.056887653243827066, "mean_baseline_minus_augmented_squared_loss": -0.021600294789409807, "observations": 255, "replications": 2000, "seed": 20261128, "status": "COMPUTED"}

## Interpretation

INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule

## Verified / unverified

**VERIFIED:** accepted ALFRED preflight identity and vintage sample hash, 0-key/0-retry ALFRED retrieval, per-vintage as-of timing gates, exact match of all 136 Binance archive/checksum hashes to the prior accepted manifest, daily price coverage, weekly event construction, fully matured 104-event training windows, non-overlapping targets and deterministic forecast/bootstrap arithmetic.
**UNVERIFIED:** independent reconstruction, server-side intraday first-publication timestamps, independent market-source replication, causal interpretation, future-regime stability and instrument-level economic value.

## Limitations

- ALFRED vintage dates have day-level, not intraday, resolution; the Sunday convention follows the scheduled Friday H.8 release and rejects stale vintages, but it does not prove exact intraday first-publication time.
- TOTCI is a seasonally adjusted aggregate and may be revised; the model uses the exact Sunday vintage rather than today's current-vintage FRED series.
- C&I loan growth mixes credit supply and credit demand and is not an identified exogenous lending shock.
- BTCUSDT is one venue's Spot close; archive checksums establish file integrity, not consolidated exchange-independent prices.
- The accepted prior BTC run retained the archive manifest but not raw daily rows; the same 136 official archives were re-materialized and every archive hash, checksum hash, date and row count was matched to that manifest.
- This is a forecast-only screen, not causal identification, trading P&L, profitability, a strategy promotion or live deployment evidence.
- The result is one exploratory hypothesis among many; nominal bootstrap intervals do not adjust for repository-wide multiple testing or selection bias.

## Reproducibility

- ALFRED source preflight: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46115128898
- BTC accepted source manifest: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/blob/main/reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json
- Empirical workflow: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46119814521
- Implementation: research/h8_ci_credit_impulse_btc_downside.py
- Tests: research/test_h8_ci_credit_impulse_btc_downside.py
