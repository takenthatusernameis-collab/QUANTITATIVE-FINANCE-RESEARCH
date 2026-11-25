# Research session — 2026-11-25T17:16:24.041360+00:00

## QFR-2026-11-25-TREASURY-CURVE-VOL-SP500-RV-01

**Disposition: INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule**

### Selection and scope

- The hypothesis tests Treasury yield-curve volatility, not VIX/VXV option-implied term structure or Treasury auction microstructure.
- The same-day research KPI had already been met by earlier distinct real-data backtests; this is an additional preregistered experiment.
- Research/paper simulation only. No live orders, capital deployment, paid data or credentials.

### Source coverage

| Series | First date | Last date | Rows | SHA-256 |
|---|---|---:|---:|---|
| SP500 | 2016-11-28 | 2026-11-24 | 2512 | 6892b6e8b13c7283cb2fe62a453bbe1953a1db4084ae5d795a8ee27ea5a69d11 |
| VIXCLS | 2016-11-25 | 2026-11-24 | 2546 | fc8adf09eed97d58b761eca77de7cee278d79c257dd89b08747b31482bc8fad7 |
| T10Y3M | 2016-11-25 | 2026-11-24 | 2499 | e4a16c263232c2ce13796a7de5ad8205164c4f776aa046083ddf3c377f194ae8 |

### Frozen walk-forward results

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 107 | 204 |
| Baseline RMSE (log1p RV) | 0.33999570 | 0.26604998 |
| Augmented RMSE (log1p RV) | 0.33877689 | 0.26463584 |
| RMSE improvement | 0.3585% | 0.5315% |

- Accepted non-overlapping events: 415 of 415 candidate origins.
- Skipped events: {"curve_observation_gap": 0, "curve_window_too_wide": 0, "incomplete_future_return_window": 0, "incomplete_pre_return_window": 0, "insufficient_curve_history": 0, "invalid_curve_variation": 0, "missing_vix_on_signal_date": 0, "no_strictly_prior_curve_observation": 0, "overlapping_target_window": 0, "stale_curve_observation": 0}.
- Paired test squared-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.673, "ci_95_high": 0.0043301170564916565, "ci_95_low": -0.003324934319772951, "mean_baseline_minus_augmented_squared_log_loss": 0.0007504657250021328, "observations": 204, "reps": 2000, "status": "COMPUTED"}.

### Verified versus unverified

**VERIFIED:** deterministic tests, source schema and coverage acceptance, strict prior-date curve alignment, no forward-fill, gap handling, non-overlapping targets, fully matured training targets and the recorded result under this code/data vintage.

**UNVERIFIED:** historical point-in-time FRED vintages, causal transmission, stability in future regimes, independent source reconstruction and instrument-level economic value.

### Next action

- If BACKTESTED, require independent reconstruction and a separately preregistered instrument-level economic study.
- If REJECTED or INCONCLUSIVE, close under the frozen decision rule; do not tune this hypothesis ID.
- No automatic timebox extension.

## Reproducibility

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45662954265
- Manifest: reports/generated/treasury-curve-volatility/45662954265-attempt-1/manifest.json
- Source: research/treasury_curve_volatility_sp500.py
- Tests: research/test_treasury_curve_volatility_sp500.py


## Wake-up execution addendum — validation repairs and final repository check

- The first CI attempt (run 45662738368) stopped before data retrieval because the synthetic walk-forward fixture omitted output fields and the gap test removed too few observations to exceed the four-calendar-day guard.
- The second CI attempt (run 45662879243) exposed one remaining fixture field and the same gap-test construction issue. The fixture was completed and three consecutive business observations were removed so the test exercises a genuine greater-than-four-calendar-day gap. No empirical data were inspected during either failed test attempt.
- Final run 45662954265 passed all 14 deterministic tests, source retrieval, the preregistered walk-forward forecast and evidence persistence. All workflow steps succeeded.
- The workflow committed the report, manifest and registry update. Final main commit at verification: 7b5fb37ca1733e15b771d36123b178f807621cc6.
- Repository check: no open pull requests or open issues were returned. The historical tasks/ACTIVE-QUEUE.md path is absent on current main; the current README and hypothesis registry are the operative records.
- Daily research KPI: MET before this additional experiment; this distinct real-data experiment added further evidence. No live orders, capital deployment, raw-data commit or paid-data use occurred.
- Research output: one additional rates-uncertainty forecast screen, INCONCLUSIVE. Operational work: one preregistration, model, 14-test suite, least-privilege workflow, two test-fixture repairs and persisted evidence. No time-spent estimate is asserted.
- Next: leave this hypothesis closed and do not tune its feature, horizon, sample or decision rule. Select a new candidate only if it has a materially distinct mechanism and a separate preregistration.
