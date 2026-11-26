# Wake-up research session — 2026-11-26T060839Z

## Objective and starting state

- Reconciled current main, repository tree, registry, recent session reports, Actions runs and open PRs/issues before selecting work.
- Starting main HEAD: 303684829aff3cea2102895dde2f428c666ef537.
- No Actions runs were in progress at preflight.
- No open PRs or standalone open issues were found. Historical PR #2 is closed, unmerged and explicitly superseded; it is not an active dispatch route.
- The current README is the complete operating contract. The current tree has no tasks/ directory or standing legacy task file.
- The 2026-11-26 real-data backtest minimum was already met by multiple distinct screens (including STLFSI4/BTC, SOFR-EFFR/S&P 500, VXN/VIX/S&P 500, KC PRS/DGS2 and WTI/S&P 500). This session is additional research, not a quota repair.

## Current research evidence reconciled

- STLFSI4 -> BTC downside semivariance: REJECTED. The augmented model worsened validation and test RMSE; paired-loss inference favored the baseline.
- SOFR-EFFR repo premium -> S&P 500 realized volatility: REJECTED.
- VXN/VIX cross-index implied-volatility spread -> S&P 500 realized volatility: INCONCLUSIVE.
- KC PRS policy-rate skew -> DGS2 change: INCONCLUSIVE; augmented RMSE worsened in both chronological periods, but the paired interval crossed zero.
- WTI repricing -> S&P 500 realized volatility: INCONCLUSIVE; validation improved 1.6097%, test worsened 1.1223%, and paired test-loss interval was entirely negative. The run's empirical calculation succeeded, but its final evidence-persistence step failed on a concurrent registry update. The subsequent handoff-format repair passed admission CI run 45760136410.
- The WTI persistence failure and status-formatting defect were repaired in main; no duplicate WTI experiment was dispatched.

## Candidate and novelty assessment

Selected a materially distinct balance-sheet quantity mechanism rather than retuning any prior indicator:

**QFR-2026-11-26-FED-BALANCE-SHEET-BTC-DOWNSIDE-01**

Question: does a strictly lagged four-week contraction in Federal Reserve total assets add incremental information about next-five-session BTC downside semivariance beyond BTC's own recent downside semivariance and total realized variance?

Novelty boundary:
- WALCL is a weekly total-assets stock from the Fed's H.4.1 release, not the STLFSI4 composite financial-stress index.
- The predictor tests aggregate balance-sheet quantity changes, not option-implied policy skew, market stress, dollar returns, real yields or FOMC announcement surprises.
- Prior literature examines monetary-policy shocks and crypto volatility; the registered contribution is narrower and does not claim first discovery.
- WALCL is explicitly not described as pure QT, bank reserves or net liquidity.

## Source feasibility and timing

- FRED WALCL is public, weekly as of Wednesday, in millions of U.S. dollars, and sourced from the Board of Governors' H.4.1 release.
- The Federal Reserve says H.4.1 is normally released Thursday around 4:30 p.m. Eastern, with holiday shifts to the next business day.
- The preregistered signal uses a WALCL Wednesday observation only at the close of the BTC UTC daily candle dated seven calendar days later. This is deliberately conservative and avoids using the same-week observation before its normal release.
- Binance BTCUSDT 1d UTC archive ingestion reuses the repository's previously verified official monthly/daily Vision archive parser and per-file checksum sidecar checks. The new run revalidates all current source coverage.
- Data sources: https://fred.stlouisfed.org/series/WALCL ; https://www.federalreserve.gov/releases/h41/ ; https://github.com/binance/binance-public-data.

## Frozen experiment

- Predictor: negative 100 times ln(WALCL[t] / WALCL[t-4]); positive means four-week total-assets contraction.
- Baseline: prior-five and prior-twenty-session BTC downside semivariance plus prior-twenty-session total realized variance.
- Augmented model: baseline plus only the four-week WALCL contraction proxy.
- Target: log1p next-five-session BTC downside semivariance.
- Signal: UTC BTC daily close seven calendar days after the WALCL Wednesday observation.
- Rolling OLS: 104 prior weekly events; every training target must be fully matured before the current signal.
- Validation: 2019–2021. Test: 2022 onward.
- Paired test-loss uncertainty: 2,000 circular-block bootstrap replications, four events per block.
- Decision: promising only if both chronological RMSEs improve and the paired-loss 95% lower bound is positive; reject only if both RMSEs worsen and the upper bound is negative; otherwise inconclusive.
- One frozen screen only. No retuning or repeat under this hypothesis ID.

## Implementation prepared for atomic admission

- research/fed_balance_sheet_btc_downside_semivariance.py — FRED WALCL parser, official Binance archive ingestion, strict release lag, non-overlapping event construction, walk-forward model, metrics, paired bootstrap and idempotent evidence persistence.
- research/test_fed_balance_sheet_btc_downside_semivariance.py — parser, release timing, feature sign, target maturity, irregular-week handling, walk-forward maturity, decision and registry-idempotency regression tests.
- research/PREREGISTERED-QFR-2026-11-26-FED-BALANCE-SHEET-BTC-DOWNSIDE-01.md — frozen hypothesis, data semantics, split and decision rule.
- .github/workflows/fed-balance-sheet-btc-downside-semivariance.yml — immutable triggering-SHA checkout, exact-source assertion, deterministic tests before retrieval, admission marker, non-cancellation and bounded concurrent-persistence recovery.
- Updated workflow-admission-tests.yml and test_workflow_admission.py to compile and test the new workflow and research module.
- Added the new hypothesis to HYPOTHESIS-REGISTRY.md.
- This session report is included in the same atomic commit.

## Pre-push synthetic logic check

A deterministic synthetic weekly-WALCL/daily-BTC alignment check produced 476 valid candidate events, 120 validation forecasts and 252 test forecasts after a 104-event rolling maturity window. The first signal was seven days after the first five-observation WALCL window; each five-session target ended before the next weekly signal. This is a plumbing check only, not a real-data backtest and not a daily-KPI contribution.

## Validation boundary and next action

- VERIFIED before admission: repository state, prior empirical results, public source definitions and release schedule, prior official BTC archive route, frozen event-time design, and synthetic event-alignment sanity check.
- PENDING hosted validation: the new deterministic unittest suite, workflow-admission regression suite, live FRED/Binance source acceptance, actual forecast metrics, paired bootstrap and evidence persistence.
- No real-data result is claimed before the admitted workflow completes.
- No raw market data, credentials, paid data, live orders or capital deployment are used.
- Next: inspect the atomic admission and research runs. If tests pass, verify live coverage, 104-event maturity, zero-imputation rules, chronological forecasts, paired inference and persistence commit. If source acceptance fails, retain an explicit INCONCLUSIVE failure manifest and change only the demonstrated source/semantic defect; do not relax the frozen hypothesis.


## Post-admission trigger-isolation repair

The atomic admission commit unintentionally queued three workflows on the same triggering commit: the new Fed balance-sheet experiment, the shared admission guard, and the already-completed KC PRS experiment. Inspection showed the KC PRS workflow explicitly included .github/workflows/workflow-admission-tests.yml in its push path filter. Because the admitted commit changed that shared test workflow, the unrelated KC PRS job was queued despite its hypothesis already having a final INCONCLUSIVE disposition.

- Queued KC PRS run: 45767439656. At the time of this repair it remained QUEUED; the available GitHub integration exposed no workflow-run cancellation action, so cancellation could not be performed or claimed.
- Removed the shared admission-test workflow from the KC PRS path filter. Its own guard workflow remains triggered by .github/workflows/** changes.
- Added a regression assertion that shared admission-harness changes cannot re-trigger the KC PRS experiment, and documented the rule in README.
- The repair commit deliberately omits [QFR-ADMIT], so it cannot admit another research backtest. The guard workflow should run and verify the change.
- The new Fed research run and admission guard remain separately queued for commit 82eab87d53a7b16196a7964af40dc63bd9225c9b; their outcomes are not yet known.

This is a workflow-trigger isolation defect, not a reason to repeat either empirical experiment. Preserve the queued-run record and do not describe the KC PRS job as cancelled unless GitHub reports that state.


## Persistence-path correction

A final static workflow review found that the post-run persistence step imported the research module from the repository root without adding the research directory to Python's module search path. The research run itself would have succeeded, but the evidence-persistence step could fail with ModuleNotFoundError after the expensive backtest. Corrected the command to add research to sys.path before importing the idempotent document updater, and added an admission regression test for that exact requirement. The already-queued run on the immutable 82eab87 commit retains its original workflow definition; if it reaches persistence and fails there, recover its report/manifest from the job logs and persist them without re-running the empirical screen.
