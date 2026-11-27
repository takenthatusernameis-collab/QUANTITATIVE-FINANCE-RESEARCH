# Recovery session — U.S. initial claims / BTC downside forecast

- **Timestamp:** 2026-11-27T15:55:25Z
- **Hypothesis:** `QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01`
- **Current state:** IMPLEMENTATION_READY; empirical evaluation pending one explicit workflow dispatch.
- **Timebox:** LOW; maximum 2 substantive cycles; start 2026-11-27T15:40:06Z; implementation deadline 2026-11-28T15:40:06Z; final conclusion deadline 2026-11-29T15:40:06Z.
- **Current main commit:** `1799d68c7a5678c60dae657de1a83e06df07d334`.

## Cycle 1 — source feasibility

**PASS.** Corrected source-preflight run [#46028463525](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463525) verified:

- FRED ICSA: 484 weekly observations, 2017-08-19 through 2026-11-21, Saturday cadence, 480 complete five-observation windows, latest observation six days old.
- Correct units: number of claims, seasonally adjusted. The earlier preflight artifact had an inaccurate units label; the corrected rerun retained the same source response hash and fixed the metadata.
- Binance exchangeInfo confirmed BTCUSDT active Spot trading.
- Official Binance Vision 2026-11-23 daily BTCUSDT archive and checksum sidecar both verified against SHA-256.
- No raw source observations were saved and no backtest was run during preflight.

## Cycle 2 — implementation attempt and repair

The first admitted execution [#46028463325](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463325) passed deterministic tests and source retrieval but stopped before empirical evaluation with `KeyError: 'target_bp'`. The model's target dictionary entry had been swallowed by a literal newline escape in a comment. The final workflow assertion also omitted the manifest path argument and raised `IndexError` after the failure manifest had been persisted.

No validation/test forecasts were generated; no RMSE comparison or paired-loss bootstrap was computed. The first run is not an empirical result and does not count as a new backtest.

**Repair:** unmarked commit [`1799d68`](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1799d68c7a5678c60dae657de1a83e06df07d334) restores the actual `target_bp` dictionary entry, adds a regression assertion for the target transform, fixes the final manifest argument, updates the preflight reference to the corrected source run, and aligns report deadlines with the committed preregistration.

## Verification

- [Admission/repair CI #46029106335](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46029106335): success.
- 259 tests across 20 repository test suites passed, including all 8 new model-specific tests.
- The model-specific suite verified strict seven-day signal lag, target starts after signal, non-overlapping five-session targets, skipping irregular weekly windows, invariance of pre-signal features to future-price changes, 104 fully matured training events, deterministic bootstrap, frozen decision rules and idempotent evidence persistence.
- [Research workflow #46029106561](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46029106561) was skipped as required because the repair commit was unmarked. No unauthorized marker retry was attempted.

## Blocker and next action

The implementation is now **IMPLEMENTATION_READY** under the deterministic acceptance tests, but the one real-data backtest still requires an authorized `workflow_dispatch` on `main` using the [initial-claims BTC downside workflow](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/workflows/initial-claims-btc-downside.yml).

The connected GitHub tool surface available in this automation does not expose a workflow-dispatch action. The repository's recovery policy explicitly forbids using another `[QFR-ADMIT] research:` push as a substitute. Therefore the run is left fail-closed for a manual dispatch. If no authorized dispatch occurs by 2026-11-29T15:40:06Z, close this hypothesis as INCONCLUSIVE/INFEASIBLE; do not extend or reset the timebox and do not describe the implementation failure as a performance NO-GO.

## Daily KPI and research position

The 2026-11-27 minimum had already been met by distinct ETF-relative-flow and BTC blockspace-fee-rate real-data forecast screens. This initial-claims attempt did not produce another valid backtest and is not counted. No raw ICSA observations or BTC prices were committed. No live orders or capital deployment are authorized.

## Files and durable evidence

- [Preregistration](../../research/PREREGISTERED-QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01.md)
- [Hypothesis registry](../../research/HYPOTHESIS-REGISTRY.md)
- [Corrected source preflight #46028463525](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463525)
- [First failed empirical attempt #46028463325](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463325)
- [Repair CI #46029106335](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46029106335)
- [Repair commit 1799d68](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1799d68c7a5678c60dae657de1a83e06df07d334)
