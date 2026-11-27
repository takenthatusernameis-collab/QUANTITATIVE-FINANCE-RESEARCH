# Wake-up reconciliation — 2026-11-27T18:37:20Z

## Objective

Reconcile current mainline, research evidence, pending workstreams, GitHub Actions state and the next authorized execution.

## Mainline and concurrency

- Default branch: `main`.
- Mainline before this report: `ed35ad1eeb21aa6b3f068cf4cf4013d3de4eb203` (2026-11-27T15:57:55Z).
- Repository is writable by the connected owner identity; main is currently unprotected.
- No open pull requests were returned.
- No Actions runs were queued or in progress at inspection time.
- Latest recorded run: admission guard #46029502425, success; associated initial-claims research workflow #46029502308 was skipped because the documentation commit was not an admission commit.

## Research evidence and daily KPI

The 2026-11-27 minimum of one genuinely new real-data hypothesis backtest was already exceeded before this wake-up. The following distinct forecast screens have persisted empirical outputs:

- BTC taker-flow/price-response downside forecast, run [#45926394994](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994): 457 walk-forward forecasts (159 validation / 298 test); validation RMSE improvement +0.3119%, test -1.0491%; paired test-loss 95% interval crosses zero; INCONCLUSIVE.
- BTC/ETH ETF relative-flow ETH/BTC forecast, run [#46001444403](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444403): validation/test RMSE improvements -0.5391% / -0.9036%; paired test-loss interval crosses zero; INCONCLUSIVE.
- BTC blockspace fee-rate downside forecast, run [#46024917193](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024917193): validation/test RMSE improvements -0.5038% / -0.4834%; INCONCLUSIVE and independently audited/closed.

No new hypothesis or parameter variant was admitted in this session. No additional backtest was run because the daily minimum was already met and the current highest-value work is to finish the admitted recovery without weakening its gate.

## Current admitted workstream — initial claims / BTC downside

Hypothesis: `QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01`.

- Corrected source preflight [#46028463525](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463525) passed: 484 weekly FRED ICSA observations, Saturday cadence, 480 complete five-observation windows, and an active BTCUSDT Spot market with a checksummed official Binance Vision sample archive.
- First empirical attempt [#46028463325](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463325) persisted a failure manifest with `completed_backtest=false`, null validation/test metrics and `KeyError: 'target_bp'`. No forecast rows or empirical conclusion were produced. The final workflow assertion also failed because it omitted the manifest path.
- Repair commit [1799d68](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1799d68c7a5678c60dae657de1a83e06df07d334) restored the target mapping, added a regression assertion and fixed the final manifest argument.
- Repair CI [#46029106335](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46029106335) passed 259 tests across 20 suites, including all 8 model-specific tests.
- The repaired push-triggered research run [#46029106561](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46029106561) was correctly skipped because the repair commit was unmarked. Later documentation push #46029502308 was also correctly skipped.
- Current status remains IMPLEMENTATION_READY; empirical result NOT RUN. The one authorized retry must be a `workflow_dispatch` on `main` using [initial-claims-btc-downside.yml](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/workflows/initial-claims-btc-downside.yml).
- The connected GitHub integration available in this session does not expose a workflow-dispatch operation. No dispatch was attempted, no marker commit was created, and no authorization gate was bypassed.

## Timebox and next action

The frozen LOW-difficulty timebox remains unchanged:

- Start: 2026-11-27T15:40:06Z.
- Hard implementation deadline: 2026-11-28T15:40:06Z.
- Hard final conclusion deadline: 2026-11-29T15:40:06Z.
- If the authorized dispatch does not occur by the final deadline, close INCONCLUSIVE/INFEASIBLE. Do not extend or reset the clock, and do not call the implementation failure a performance NO-GO.

After dispatch, verify the run's exact source commit, completed-backtest flag, forecast sample counts, metrics, paired-loss bootstrap, persisted report/manifest/CSV, and registry/preregistration digests. Independently recompute the disposition from the persisted forecast rows.

## Session outcome

- Research output: no new empirical result; daily minimum was already met.
- Operations: mainline, workflow history, current admission state and recovery gate reconciled; exact manual-dispatch blocker confirmed.
- Changes: this timestamped reconciliation report only.
- Research data: none downloaded or committed.
- Security and research boundaries: unchanged; no credentials, workflow permissions, admission markers, holdouts or live-trading settings modified.
