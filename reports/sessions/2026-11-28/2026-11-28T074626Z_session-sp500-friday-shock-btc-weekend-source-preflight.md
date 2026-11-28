# Session report — Friday S&P 500 shock / Bitcoin weekend source feasibility

- **Timestamp:** 2026-11-28T07:46:26Z
- **Objective:** Reconcile the current mainline and admit one materially distinct cross-market weekend-risk hypothesis only if its source and event timing can be verified.
- **Hypothesis:** QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01.
- **Status:** IDEA / SOURCE PREFLIGHT PENDING. No model fitting or backtest has been run.

## Reconciliation

- Mainline before this session: 7eb8ad3962ee83a2c773b05a5b306a4a14694de2.
- Latest completed research evidence: H.8 C&I / BTC downside forecast and independent reconstruction, run 46122370665, both successful. The correct disposition is INCONCLUSIVE; validation and test RMSE both worsen, while the paired-loss confidence interval crosses zero.
- No active Actions runs were present at reconciliation. Draft control PR #15 remains open and unmerged.
- The 2026-11-28 daily real-data backtest minimum was already satisfied by the completed MEXC funding-dispersion / BTC realized-variance backtest #46085887442. This new source-only preflight is additional work and does not count as a backtest.

## Research selection and design

- Selected a new direction: Friday S&P 500 downside shock -> subsequent Saturday/Sunday BTC downside semivariance.
- The hypothesis differs from existing BTC macro screens by using a Friday cash-market event, a fixed 15–16 hour post-close embargo, an hourly crypto target and a non-overlapping Saturday 12:00–Sunday 12:00 UTC window.
- Preregistered the feature, target, 104-event walk-forward training rule, validation/test split, paired-loss bootstrap, source acceptance criteria, point-in-time limitation, and HIGH difficulty timebox before source retrieval.
- The source preflight checks FRED SP500 daily coverage and official Binance BTCUSDT 1h archive checksums/coverage. It also checks exact event-window completeness and minimum eligible validation/test sample sizes. It must not fit a model or save raw observations.

## Process safeguards

- Added the source-only workflow to the admission guard's non-research workflow allowlist.
- Added deterministic tests for FRED parsing, source freshness, archive path construction, hourly gaps, weekly event maturity and the 24-hour target window.
- Added the new preregistration and source-preflight paths to the global admission-guard workflow.
- Kept the source-preflight workflow read-only and excluded shared admission-harness files from its path filters.

## Evidence and validation

- First preflight run 46124207470: deterministic tests passed after fixture corrections, but archive acquisition failed closed on three historical Binance BTC rows: one close_time exactly at the interval end, one off-grid open_time, and one close_time earlier than open_time. The shared ETH parser was intentionally not modified because its acceptance contract differs.
- No empirical result, model fit, trading P&L or strategy claim is made.
- The FRED SP500 series lacks historical intraday first-publication timestamps. The 15–16 hour embargo reduces timing risk but does not certify historical point-in-time availability.
- The source preflight fetched roughly nine years of monthly Binance hourly archives plus daily archives for the current partial month and verified their adjacent SHA-256 sidecars. The first parser rejected three historical row conventions. A pre-result preregistration amendment now accepts exact interval-end close timestamps, excludes and enumerates off-grid/invalid-close rows without rounding, and counts them against the existing 24-hour/0.05%/four-consecutive-hour limits. The corrected preflight is rerunning. No raw observations were committed and no model was fitted.

## Next action

If source preflight passes, implement the frozen hourly walk-forward forecast and deterministic tests, then run one immutable admitted real-data backtest and an independent reconstruction within the timebox. If source coverage or sample-size gates fail, record the exact blocker and close INCONCLUSIVE/INFEASIBLE without fitting a model or relaxing criteria.
