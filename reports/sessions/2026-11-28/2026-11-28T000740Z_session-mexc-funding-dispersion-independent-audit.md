# Independent audit — MEXC funding dispersion / BTC realized variance

- **Hypothesis:** `QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01`
- **Audit cycle:** 4 of 4; completed `2026-11-28T00:07:40Z`
- **Final disposition:** INCONCLUSIVE; workstream closed
- **Source preflight:** [run #46085255885](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085255885), source commit `aa76af09051a7b5b7482eafa3a0b86896a378569`
- **Backtest:** [run #46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442), executed source commit `27069ede30075052a137ad2b999bc491110da9e2`
- **Persisted evidence commit:** `287638a7d42e65884f39e6e75a9c332637429d46`

## 1. Provenance audit

- The accepted preflight manifest reports `PASS`, active `BTC_USDT` perpetual metadata, `quoteCoin=USDT`, `settleCoin=USDT`, and `futureType=1`.
- Funding history: 1,590 exact settlements, 530 complete UTC dates from 2025-06-15 through 2026-11-26; zero incomplete dates in the frozen window. Both pages were retrieved from `https://api.mexc.com`.
- Hourly prices: 12,929 of 12,929 expected bars from 2025-06-07 00:00 UTC through 2026-11-27 16:00 UTC; 100% coverage, zero missing hours, zero consecutive missing-hour runs.
- No fallback host was used. The model manifest's canonical funding hash `427f4b141673a6e43108d7033c91494af554c507527e8e51330ac95c0fbafd2f` and hourly-close hash `b3fc8ef0cd1f695c18499e191294214914eee96d846b70b71c7c83c541c8468e` exactly match the accepted preflight manifest.
- The workflow re-fetched both sources, checked the frozen hashes and host, and completed its deterministic source/model/admission tests before model fitting. The run log reports 58 admission tests passed; the model and source-preflight test suites also passed.
- Raw observations were not committed; request/page/segment hashes, coverage and canonical hashes were persisted.

## 2. Forecast-row reconstruction

Independently parsed `reports/generated/mexc-funding-dispersion-btc-rv/46085887442-attempt-1/forecast_rows.csv` (391 data rows).

| Integrity check | Result |
|---|---:|
| Validation / test rows | 61 / 330 |
| Training size | 120 for every forecast |
| Signal timestamp | Every row at 17:00 UTC |
| Target horizon | Exactly 24 hours for every row |
| Chronology | Consecutive daily signals; validation ends 2025-12-31, test begins 2026-01-01 |
| Stored squared errors | Exact reconstruction from target and predictions; maximum difference 0 |

The implementation also uses only training rows whose target end is strictly earlier than the current signal (`target_end_ts < signal_ts`), preserving the preregistered maturity embargo. The 24-hour target begins at the 17:00 UTC signal; the signal follows the 16:00 settlement by one hour.

## 3. Independent metric reconstruction

| Split | Baseline RMSE | Augmented RMSE | Baseline MAE | Augmented MAE |
|---|---:|---:|---:|---:|
| Validation (n=61) | 0.934294511506 | 0.924561420961 | 0.728378166597 | 0.717299647600 |
| Test (n=330) | 0.903469489590 | 0.907203014898 | 0.721764743873 | 0.726108795908 |

- Validation RMSE improvement: `+1.041758%`.
- Test RMSE improvement: `-0.413243%`.
- Mean paired test loss (baseline squared error minus augmented squared error): `-0.00676019162053`; negative favors the baseline.
- Re-ran the preregistered circular moving-block bootstrap from the persisted paired test-loss series using NumPy `default_rng(20261127)`, 2,000 replications and seven-observation blocks. The independently reconstructed 95% interval is `[-0.02088867, +0.00740868]`, matching the manifest to displayed precision and crossing zero.

## 4. Frozen decision and interpretation

The preregistered PROMISING rule requires both validation and test RMSE to improve and the paired-loss interval lower bound to be positive. The REJECTED rule requires both RMSE values to worsen and the interval upper bound to be negative. Neither rule is met: validation improves, test worsens, and the interval crosses zero. The correct disposition is **INCONCLUSIVE**.

This is a forecast-only result for one MEXC perpetual and a roughly 17-month sample. It is not evidence of a tradable edge, strategy P&L, causality or cross-venue generality. The historical API does not provide a complete publication-time audit; a one-hour lag after the final funding settlement does not prove the historical record was observable at that exact signal time. No same-ID tuning, additional run or reuse of the validation/test sample is justified.

## 5. Daily KPI and next action

- The 2026-11-28 UTC minimum of one new real-data hypothesis backtest was met by run #46085887442. The earlier failed attempt and source-only preflight do not count.
- Cycle 4 of the MEDIUM four-cycle timebox is complete before its implementation and final-conclusion deadlines. Close the workstream as INCONCLUSIVE; do not extend or reset the timebox.
- Next research cycle: discover a materially different mechanism, check the registry/literature and data feasibility, then preregister a new ID and difficulty-adjusted timebox before implementation. Do not retune this hypothesis.

## 6. Operational reconciliation

- Main was at `287638a7d42e65884f39e6e75a9c332637429d46` before this audit commit. No queued, in-progress, waiting or pending workflow runs were present at reconciliation.
- Draft control PR #15 remains the command surface. Current `main` bridge and documentation allow only `/qfr-probe-dispatch-bridge` and `/qfr-run-initial-claims-btc-downside`; the historical Treasury/RRP command was allowed by the listener at its then-current source commit, but is not in the current allowlist. No new dispatch was attempted.
- No live trading, account access, orders or capital deployment occurred.

