# Wake-up session — 2026-11-26T022103Z

- **Objective:** Reconcile the current main branch, finish the admitted VXN/VIX research screen after its failed first attempt, repair result-handoff defects, and harden workflow execution provenance.
- **Starting main:** `ec82dca85762b4e60789a49729a73dcdfd29ac05`.
- **Ending main before this report:** `b55125cb3f8927294320dfde797f9c32be20fdf1`.
- **Daily real-data backtest KPI:** **MET** — three distinct preregistered real-data forecast screens completed on UTC date 2026-11-26. Negative and inconclusive results count; no profitability claim is made.

## Research output

### 1. STLFSI4 and BTC downside semivariance — REJECTED

- Run: [45738528717](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45738528717).
- Data: 3,387 complete BTCUSDT daily candles (2017-08-17 to 2026-11-24) and 484 weekly STLFSI4 observations (2017-08-18 to 2026-11-20).
- Walk-forward forecasts: validation/test 120/254.
- RMSE improvement over baseline: -1.0190% / -1.2351%.
- The paired test-loss bootstrap upper confidence bound is below zero; the augmented predictor is worse under the frozen decision rule.
- Limitation: STLFSI4 is a revised current FRED vintage, not a historical point-in-time ALFRED reconstruction. Forecast-only; no tradable P&L.

### 2. SOFR-EFFR repo premium and S&P 500 realized volatility — REJECTED

- Run: [45739654076](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45739654076).
- Data: SOFR, EFFR, SP500 and VIXCLS from 2018-04-03 to 2026-11-24; 359 accepted non-overlapping events.
- Walk-forward forecasts: validation/test 51/204.
- RMSE improvement over baseline: -0.1321% / -2.1813%.
- Paired test squared-loss 95% CI: [-0.007117, -0.000111], wholly below zero. The augmented predictor is rejected.
- Limitations: current FRED vintages, no historical point-in-time revisions; the secured/unsecured spread is a proxy, not an exogenous liquidity shock. Forecast-only.

### 3. VXN/VIX cross-index implied-volatility spread and S&P 500 realized volatility — INCONCLUSIVE

- First attempt [45740292998](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45740292998) passed its 13 hypothesis tests and three admission tests, retrieved the source series and reached output persistence, then failed because `update_preregistration` was missing. No result from that attempt was accepted.
- The missing updater was implemented and regression-tested. The frozen screen was re-admitted on immutable commit `a7445a32c69843021a24377567d3b209dae5f591`.
- Successful run: [45741392870](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741392870). The immutable-checkout assertion and deterministic tests passed; the report and manifest were persisted by commit `172c0b2f1cfdf0f03c8462b54dc7a9e4f2aefb87`.
- Data: VXNCLS 2,515 rows, VIXCLS 2,546 rows, SP500 2,512 rows; coverage begins 2016-11-25/28 and ends 2026-11-24. All 415 candidate non-overlapping events were accepted; none were skipped.
- Walk-forward forecasts: validation/test 107/204.
- Baseline RMSE: 0.33999570 / 0.26604998. Augmented RMSE: 0.34356429 / 0.26871718.
- RMSE improvement: -1.0496% / -1.0025%.
- Paired test squared-loss 95% CI: [-0.003155, +0.000393], crossing zero. Both RMSE comparisons worsen, but the frozen rejection rule also requires the paired-loss upper bound below zero; therefore the correct disposition is **INCONCLUSIVE**, not REJECTED.
- Current FRED vintages do not reconstruct historical point-in-time CBOE dissemination or revisions. This is a forecast screen, not a causal result, tradable strategy or P&L.

## Engineering and operational repairs

1. **Immutable execution provenance:** all 14 research workflows and the admission-test workflow now check out `ref: ${{ github.sha }}`, rather than mutable `main`. The VXN workflow additionally asserts that `git rev-parse HEAD` equals `GITHUB_SHA`. The VXN manifest records the same source commit as the triggering run.
2. **Preserve admitted runs:** all 14 research workflows now set `cancel-in-progress: false`; a later push can no longer cancel an in-progress admitted backtest.
3. **Same-session replacement invariant:** the README now explicitly requires immediate implementation, regression tests, validation and handoff updates when a component is diagnosed as needing replacement. Independent work must continue behind fail-closed gates when an external prerequisite remains.
4. **Preregistration handoff:** the updater now avoids duplicated status prefixes and repeated terminal punctuation. The persisted VXN preregistration status was corrected from the duplicated label to one canonical `INCONCLUSIVE` label.
5. **Regression coverage:** added checks for immutable workflow checkout, non-cancellation, same-session replacement policy, VXN result handoff and registry-row upsert. The admission workflow now compiles both VXN source and test modules before running the suites.
6. **Failure-driven corrections:** CI run [45741581401](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741581401) exposed a Python f-string syntax error; [45741636389](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741636389) then exposed a misplaced `status_label` assignment that caused a `NameError` in the registry path. Both defects were corrected in this session, and a dedicated registry-upsert regression test was added.
7. **Final validation:** [45741797913](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741797913) completed successfully: Python compilation passed, all 6 workflow-admission tests passed, and all 16 VXN/VIX tests passed. The VXN empirical run [45741392870](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741392870) also completed successfully. No Actions runs remained in progress at the final inspection.

## Verified / unverified

**VERIFIED**
- Three distinct real-data backtests completed on 2026-11-26 and were recorded in the hypothesis registry.
- VXN/VIX source coverage, event construction, timing, walk-forward metrics and paired bootstrap were persisted in the generated manifest and session report.
- The VXN run's `source_commit_sha` matches its triggering commit.
- All 14 research workflows use immutable triggering-SHA checkout and disable in-progress cancellation; the repository admission tests verify both policies.
- Latest deterministic validation passed: 6 admission tests and 16 VXN/VIX tests.

**UNVERIFIED**
- Historical point-in-time FRED/CBOE vintages and independent reconstruction of the VXN/VIX result.
- Future-regime stability, independent replication, instrument-level economic value and trading profitability.
- Any strategy promotion or live deployment; none was attempted or authorized.

## Research vs. operations

- Research output: three completed real-data screens; two rejected and one inconclusive.
- Operations: substantial same-session workflow and handoff repairs needed to make the VXN result reproducible and prevent mutable-branch execution/cancellation.
- Wall-clock effort was not instrumented; no fabricated percentage split is reported.

## Next

- Do not retune or rerun the VXN/VIX feature under the same hypothesis ID; its preregistration authorized one frozen screen.
- Select a materially distinct next hypothesis from the registry, review prior work and literature, verify source feasibility first, then preregister before inspecting results.
- Continue to report negative and inconclusive outcomes without relaxing scientific gates. No strategy was promoted.
