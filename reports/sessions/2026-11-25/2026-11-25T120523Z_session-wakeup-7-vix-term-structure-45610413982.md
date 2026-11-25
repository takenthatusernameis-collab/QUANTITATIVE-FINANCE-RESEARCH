# Wake-up session report — 2026-11-25T12:05:23Z

## Repository state and selection

- Default branch at dispatch: main; source commit 1a8e476938f71535451453bcd9c3d2326b33123a.
- No open pull requests, open issues or in-progress Actions runs were present at selection.
- Earlier on 2026-11-25, three distinct Treasury real-data backtests and one CFTC real-data backtest had already met the daily minimum. This is an additional, materially distinct option-implied-volatility term-structure hypothesis.
- The prior CFTC crowding experiment is closed INCONCLUSIVE; no further tuning was performed under that ID.
- Research/paper simulation only. No live orders, capital deployment, paid data, credentials or external permissions.

## Research output

### QFR-2026-11-25-VIX-TERM-STRUCTURE-SP500-RV-01

**Disposition: INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen decision rule.**

The hypothesis tests whether the simple 30-day/3-month CBOE implied-volatility slope contains incremental information about next-five-session S&P 500 realized volatility beyond recent realized volatility and the VIX level.

- Data: FRED/CBOE SP500, VIXCLS and VXVCLS daily observations.
- Aligned price coverage: 2016-11-25 to 2026-11-23.
- Valid non-overlapping forecast origins: 415; candidates: 415; skipped: {'missing_vix_on_signal_date': 0, 'missing_vxv_on_signal_date': 0, 'incomplete_pre_return_window': 0, 'incomplete_future_return_window': 0, 'overlapping_target_window': 0}.
- Signal: prior S&P 500 session close, using VIX/VXV and realized-volatility features known by that close.
- Target: next five S&P 500 sessions' root-sum-square log-return volatility, transformed with log1p.
- Event spacing: 6 sessions; targets do not overlap.
- Rolling training window: 104 fully matured prior events.
- Validation: 2019–2021; test: 2022 onward.

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 107 | 204 |
| Baseline RMSE (log1p RV) | 0.3288139316582688 | 0.2787163459531654 |
| Augmented RMSE (log1p RV) | 0.3032865660750782 | 0.27636062800969613 |
| RMSE improvement | 7.763468370835567% | 0.8452026505345794% |

- Paired squared-log-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.734, "ci_95_high": 0.005237632415723959, "ci_95_low": -0.002656211355817704, "mean_baseline_minus_augmented_squared_log_loss": 0.001307604787570931, "observations": 204, "reps": 2000, "status": "COMPUTED"}.
- Inverted-term-structure event study: {"block_size_events": 4, "ci_95_high_rv_pct": 3.8575693996789724, "ci_95_low_rv_pct": 0.674104597721906, "contango_n": 192, "high_inversion_n": 12, "high_minus_contango_mean_rv_pct": 2.2229281269438985, "mean_contango_rv_pct": 1.9902289666876216, "mean_high_inversion_rv_pct": 4.21315709363152, "reps": 1998}.
- Interpretation: RMSE improved by 7.76% in validation and 0.85% in test, but the paired test-loss interval crosses zero. The positive inversion-event difference (+2.223 percentage points; 95% interval +0.674 to +3.858) is based on only 12 inverted test events, so the frozen promotion rule is not met.

## Literature and novelty boundary

- Chang, Hung & Wang (2018), “Volatility information implied in the term structure of VIX,” *Journal of Futures Markets*, DOI: https://doi.org/10.1002/fut.21964. Their study reports incremental realized-volatility forecasting information in term-structure variables. This is prior evidence, not proof that the simple VIX/VXV slope, five-session horizon or present walk-forward design works.
- Johnson (2017), “Risk Premia and the VIX Term Structure,” *Journal of Financial and Quantitative Analysis*, DOI: https://doi.org/10.1017/S0022109017000825. The paper relates term-structure shape to variance risk premia and synthetic variance-linked returns; that is adjacent, not the same target.
- Li, Aschakulporn & Zhang (2025), “VIX term structure and future realized volatility,” DOI: https://doi.org/10.1080/00036846.2025.2601895, is directly related. The present test is a bounded retail-data replication/screen of a simple two-tenor slope, not a claim of first discovery.

## Reproducibility and data integrity

- Deterministic tests: see the workflow run.
- Source response SHA-256 hashes, row counts, exact coverage, retrieval time, code commit and metrics are in reports/generated/vix-term-structure/45610413982-attempt-1/manifest.json.
- No raw market-data files were committed.
- FRED current-vintage data were used; historical revisions were not reconstructed.

## Verified versus unverified

**VERIFIED:** source HTTP retrieval and CSV parsing; source row counts and date coverage; exact-date alignment; one-session signal/target gap; non-overlapping target windows; strict target maturity; deterministic walk-forward metrics and bootstrap under this code/data vintage.

**UNVERIFIED:** historical point-in-time FRED vintages; persistence in future regimes; executable futures/ETF performance; transaction costs; causal interpretation; economic value.

## Daily KPI and research versus operations

**DAILY KPI: MET before this additional study.** The three Treasury hypotheses and one CFTC hypothesis already completed real-data backtests today. This experiment adds another distinct, preregistered real-data result.

Research: one new cross-horizon implied-volatility mechanism tested against a realized-volatility and VIX-level baseline. Operations: source retrieval, deterministic tests, report/manifest persistence and registry update only as needed.

## Next action

- If promising, require an independently coded/source-checked validation and then a separate instrument-level economic study; do not promote this forecast to a trading strategy.
- If rejected or inconclusive, close this hypothesis under its frozen decision rule. Do not tune the term-slope formula, event threshold, horizon, model window or date split under this ID.
- No automatic timebox extension.
