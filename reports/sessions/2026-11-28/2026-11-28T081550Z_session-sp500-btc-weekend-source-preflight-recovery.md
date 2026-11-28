# Session report — Friday S&P 500 / Bitcoin weekend source-preflight recovery

- **Timestamp:** 2026-11-28T08:15:50Z.
- **Objective:** Reconcile the current mainline and repair the source-feasibility gate without weakening the preregistered data-quality limits.
- **Hypothesis:** QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01.
- **Status:** IDEA / SOURCE PREFLIGHT PENDING. No model was fitted and no backtest was run.

## Reconciliation

- Mainline at wake-up: `1b67ca4b22ff8ea2e1c3c616fbe83ac2827e5b93`.
- The 2026-11-28 daily real-data backtest minimum was already met by the completed MEXC funding-dispersion / BTC realized-variance experiment [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This session is a source-only recovery and does not count as another backtest.
- No active run owned the S&P/BTC source-preflight task. The latest source-preflight run was [#46124440696](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46124440696).

## Failure diagnosis

- Run #46124440696 passed all 10 deterministic source/timestamp/archive/event-feasibility tests.
- Its source step checksum-verified and downloaded the requested Binance archives, then failed with `Too many invalid Binance archive rows: 44 > 24`.
- The gate compared raw malformed rows across complete archive files with a limit defined in missing **hours**. That over-counted rows outside the required sample interval and could count multiple malformed rows in the same UTC hour more than once.
- The parser's core safety behavior was correct: off-grid and invalid-close rows were excluded without timestamp rounding, interpolation or synthetic candle insertion. The failure was in translating raw row anomalies into the frozen hourly-missingness measure.
- No raw market observations were committed, no model was fitted, and no empirical result or performance inference exists.

## Recovery implemented

- Each malformed row remains enumerated with its raw timestamp and archive provenance.
- For missingness accounting only, each anomaly is assigned to its containing UTC hour bucket; this does not repair or insert a price observation.
- Only affected buckets inside the required `[2017-08-18 00:00 UTC, latest target end)` interval count.
- Distinct affected hours are unioned with genuinely absent expected hourly bars, so overlapping evidence is counted once.
- The original limits remain unchanged: at most 24 affected hours, at most 0.05% effective missingness, and at most four consecutive affected hours.
- The source manifest now retains raw anomaly counts, in-scope raw counts, unique affected-hour counts, detailed anomaly rows and the exact effective missing-hour set. Expected source-gate failures return a diagnostic manifest rather than discarding all acquisition diagnostics.

## Validation

- Added deterministic tests for in-window scoping, deduplication, union with actual gaps, and rejection above the 24-hour ceiling.
- The pre-result preregistration clarifies the operational meaning of an affected hour without changing the numerical acceptance thresholds, feature, target, embargo, sample splits or model specification.
- The repaired source-only workflow is triggered by the atomic mainline commit. Its actual run result must be inspected before any model implementation is authorized.

## Timebox and next action

- The original HIGH difficulty timebox, eight-cycle cap, implementation deadline `2026-11-30T07:46:26Z`, and final conclusion deadline `2026-12-08T07:46:26Z` remain unchanged; no clock reset or extension.
- If source preflight passes, implement only the frozen model and tests, then run one immutable admitted real-data backtest and an independent reconstruction.
- If the unique in-window affected-hour union still breaches any frozen limit or the event sample is insufficient, preserve the diagnostic evidence and close INCONCLUSIVE/INFEASIBLE without fitting a model or relaxing criteria.

## Effort allocation

- Approximate effort: 65% source/data-method diagnosis and research design; 35% implementation, deterministic validation and repository operations.

## Follow-on result — exact source coverage and daily-archive recovery

- The corrected source-only preflight [#46125803757](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46125803757) passed all 13 deterministic tests and produced a complete diagnostic manifest.
- The prior concern that the 44 malformed rows might be inflated by out-of-scope dates or duplicate hour buckets was **not borne out**: all 44 rows are inside the required window and affect 44 distinct UTC hours.
- FRED passed: 2,331 positive daily observations, 2017-08-18 through 2026-11-25; latest observation age 3 days; maximum calendar gap 4 days. Historical intraday first-publication timestamps remain unavailable, so the registered point-in-time limitation persists.
- Binance monthly/current-month daily archives were checksum-verified, but only 81,033 of 81,204 required hourly bars were present. The effective gap is 171 hours (0.21058%), maximum consecutive gap 75 hours; the frozen limits are 24 hours, 0.05%, and four consecutive hours. Coverage therefore remains FAIL.
- The sample-size gate passes independently: 440 accepted weekly events, 90 eligible validation forecasts and 246 eligible test forecasts after 104 matured training events. This does not override the failed source-coverage gate.
- No model was fitted, no backtest was run, and no performance inference is authorized.
- Next bounded source-recovery experiment: fetch official Binance daily BTCUSDT 1h archives for dates containing primary missing/anomalous hours, excluding dates already retrieved. Verify each ZIP/CHECKSUM; fill only exact missing UTC-hour bars; require exact equality on every overlap; remove conflicting hours and fail closed. If the daily archives do not recover coverage below the original thresholds, close this source formulation INCONCLUSIVE/INFEASIBLE rather than relaxing the limits or fitting a model.
