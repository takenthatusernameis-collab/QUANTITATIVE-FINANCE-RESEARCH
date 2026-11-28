# Session report — Friday S&P 500 / Bitcoin weekend source-infeasibility closure

- **Timestamp:** 2026-11-28T10:15:17Z.
- **Mainline at wake-up:** `1c474fc7fcd62c3f6cfa6486f74a42f15f832583`.
- **Objective:** Reconcile the current mainline, finish the source-recovery decision for the active S&P/BTC weekend hypothesis, and repair a newly exposed admission-test regression.
- **Hypothesis:** `QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01`.
- **Disposition:** CLOSED — INCONCLUSIVE/INFEASIBLE (source feasibility); no model fit or backtest.

## Research/source result
- FRED SP500 passed with 2,331 observations from 2017-08-18 through 2026-11-25. Historical intraday first-publication timestamps remain unavailable.
- Event feasibility passed with 91 validation and 246 test forecasts after the 104-event matured-training rule.
- Primary Binance Vision BTCUSDT 1h archives supplied 81,033 of 81,204 required hours; 171 affected hours (0.21058%) and a 75-hour maximum consecutive gap.
- The bounded, checksum-verified official daily-archive recovery supplied 43 exact missing hours. It still left 129 affected/missing hours (0.158859%) and a 33-hour maximum consecutive gap.
- One conflicting close remained at 2020-12-21T13:00Z: monthly 22,646.53 versus daily 22,681.32. Both archives/CHECKSUM sidecars were verified. The conflict was not overwritten or averaged.
- Frozen limits remain 24 hours, 0.05%, four consecutive hours and zero conflicts. Final source-only run [#46126649110](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46126649110) fails acceptance. Deterministic tests passed; no model was fitted, no backtest ran, and no performance inference is possible.
- Close the identity as INCONCLUSIVE/INFEASIBLE. Do not repeat the same route, weaken the source gate, or call this a strategy NO-GO.

## CI regression diagnosis and repair
- Latest mainline run [#46134088157](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46134088157) failed two subtests in `test_canonical_decision_hierarchy_is_executable_and_guarded`.
- The README had correctly removed a fixed legacy spot-provider fallback sequence, but the test still required the obsolete literal phrases `Coinbase USD-quoted legs` and `Kraken OHLCVT`.
- The test is updated to assert the current policy instead: provider routes are selected afresh for each research question, and there is no fixed instrument universe, whitelist, exchange or historical start date.
- The closure guard then exposed a second issue: the source-preflight module had a closure record but remained callable. Added an unconditional guard to `run_preflight()` and the CLI entrypoint, added a regression test, and retired the workflow by removing its push trigger and disabling its job.
- This is a stale-test repair, not a reason to restore the removed vendor ordering. The admission-guard CI run must pass before the session is considered verified.

## Daily KPI and queue
- The 2026-11-28 real-data backtest minimum was already met by the independent MEXC funding-dispersion / BTC realized-variance experiment [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This session's source closure and CI repair are not additional backtests.
- After committing the closure, registry/README correction and test repair, no active admitted research workstream remains. The next wake-up must select a materially distinct mechanism, check novelty and data feasibility, and freeze its difficulty-adjusted timebox before implementation.

## Files changed
- `README.md`: replace stale "current workstream" status with the final source-only closure and evidence.
- `research/HYPOTHESIS-REGISTRY.md`: change the row from IDEA/source-preflight-pending to INCONCLUSIVE/INFEASIBLE with final metrics and links.
- `research/test_workflow_admission.py`: remove stale assertions for fixed legacy provider names; assert the current general source-selection policy and that the retired workflow is inert.
- `research/sp500_weekend_btc_source_preflight.py` and its tests: add and verify the permanent fail-closed execution guard.
- `.github/workflows/sp500-weekend-btc-source-preflight.yml`: remove automatic push execution and disable the job.
- `research/CLOSED-QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01.md`: permanent closure record.
- `reports/sessions/2026-11-28/2026-11-28T101517Z_session-sp500-btc-weekend-source-infeasibility-closure.md`: this report.

## Final verification — 2026-11-28T10:32:13Z

- The first post-closure CI attempt found that the new inert-workflow assertions had accidentally been applied to the still-active stablecoin preflight test. The stablecoin assertions were restored, and the inert-workflow checks were scoped to the closed S&P preflight.
- The closed-draft regression workflow [#46135616461](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46135616461) completed successfully.
- The repository admission-guard workflow [#46135616499](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46135616499) completed successfully. Compilation, workflow admission checks, adaptive hierarchy tests and all configured research regression suites passed.
- The closed S&P source-preflight workflow is inert (no push trigger; job disabled), and the module's `run_preflight()` and CLI entrypoint fail closed. Its pure parser and closure-guard tests pass.
- The closure remains source-only: no model fit, no backtest, and no performance inference. The 2026-11-28 daily real-data backtest minimum remains satisfied by MEXC funding dispersion / BTC realized variance [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442).

The repository is ready for the next wake-up to select a materially distinct, source-feasible hypothesis and preregister its timebox. No active admitted research workstream remains.
