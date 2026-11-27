# Wake-up session 7 — BTC/ETH relative ETF-flow forecast completed

- **Session timestamp:** 2026-11-27T12:38:56Z
- **Objective:** Reconcile the current mainline state, continue the highest-value admitted research workstream, complete its real-data experiment, and verify durable evidence.
- **Mainline before admission:** `e63aae7093c5d76e494da116fe418efa60e68d8d`.
- **Research hypothesis:** `QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01`.

## RESEARCH OUTPUT

The previously source-accepted BTC/ETH relative U.S. spot ETF-flow hypothesis was fully implemented and run against the frozen sample. The implementation and deterministic tests were prepared on `agent/etf-relative-flow-implementation-20261127`; the branch was six commits ahead of main, had no open PR, and its latest commit was recent. Its exact-commit admission-guard run passed all ETF parser, model/event, and persistence tests. The complete tested tree was therefore admitted to main in one atomic commit rather than pushing intermediate research commits.

- Atomic admission commit: `107f1aa5199d6f0e3905b22707bd1da3445392b3`.
- Commit subject: `[QFR-ADMIT] research: BTC/ETH ETF relative-flow ETH/BTC forecast`.
- The empirical workflow checked out and verified that exact SHA.
- Real-data backtest: [workflow run 46001444403](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444403) — **success**.
- Source preflight: [run 45996756282](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45996756282) — **success**. A second read-only preflight on the admitted commit, [run 46001444511](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444511), also succeeded.
- Mainline admission guard: [run 46001444388](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444388) — **success**.
- Closed mining-difficulty draft regression: [run 46001444469](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46001444469) — **success**.

### Frozen sample and event construction

- Farside common BTC/ETH ETF-flow panel: **583** reconciled observations, 2024-07-23 through 2026-11-16.
- Binance BTCUSDT and ETHUSDT Spot 1d UTC: **879** daily observations per symbol, 2024-07-01 through 2026-11-26; **54 checksum-verified archives per symbol**.
- Flow-panel SHA-256 and both archive-manifest SHA-256 values reproduced exactly.
- **262** eligible events; **196** walk-forward forecasts; zero event-construction skips.
- Five-calendar-day flow embargo, prior-only 60-observation z-scores, every-second-common-flow-date event schedule, and 65 fully matured training events were preserved as preregistered.

### Empirical result

**Disposition: INCONCLUSIVE.** The relative-flow feature did not improve RMSE in either chronological period, but the paired test-loss confidence interval crosses zero, so the frozen rule does not permit decisive rejection.

| Metric | Validation 2025 | Test 2026 |
|---|---:|---:|
| Forecasts | 84 | 112 |
| Baseline RMSE | 706.6755 bp | 311.9978 bp |
| Baseline + relative-flow RMSE | 710.4850 bp | 314.8169 bp |
| RMSE improvement | -0.5391% | -0.9036% |

- Paired test squared-loss difference (baseline minus augmented): **-1,767.08 bp²**.
- 95% five-event circular-block bootstrap interval: **[-5,801.04, 2,428.24] bp²**.
- Bootstrap fraction positive: **20.4%**.
- Test directional accuracy was 50.89% for the baseline and 43.75% for the augmented model; this was secondary and did not alter the preregistered decision rule.
- Both models had negative out-of-sample R² against the test-period mean benchmark. No useful standalone forecasting edge was established.

The result is a forecast screen, not a trading strategy or P&L. No CAGR, Sharpe, drawdown, profitability or live deployment claim is authorized.

## HYPOTHESES / RANKING

The registry now records the hypothesis as **BACKTESTED / INCONCLUSIVE**, not PROMISING or REJECTED. The experiment is closed at its frozen specification; do not retune the same hypothesis ID or reinterpret an uncertain result as a NO-GO.

## CHANGED

- Admitted the complete, tested implementation and workflow atomically on main: `107f1aa5199d6f0e3905b22707bd1da3445392b3`.
- The workflow persisted the experiment report, manifest, registry disposition and preregistration execution result in commit `3e0c9e7f965b5c8a417ba54b00e0767ba08674c9`.
- Research report: [2026-11-27T124630Z_session-etf-relative-flow-ethbtc-46001444403.md](2026-11-27T124630Z_session-etf-relative-flow-ethbtc-46001444403.md).
- Manifest: [46001444403-attempt-1/manifest.json](../../generated/etf-relative-flow-ethbtc/46001444403-attempt-1/manifest.json).
- Preregistration: [QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01](../../../research/PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md).
- Registry: [HYPOTHESIS-REGISTRY.md](../../../research/HYPOTHESIS-REGISTRY.md).

## VERIFIED

- Exact admitted source commit was checked out by the research workflow.
- Deterministic parser, event-timing, no-look-ahead, rolling-model, bootstrap, persistence and admission tests passed.
- Frozen flow-panel and BTC/ETH archive-manifest hashes matched.
- All 262 candidate events were accepted; all 196 predictions were generated.
- Report and manifest hashes were checked by the persistence helper; registry and preregistration were updated on main.
- Mainline evidence persistence commit: `3e0c9e7f965b5c8a417ba54b00e0767ba08674c9`.

## UNVERIFIED / LIMITATIONS

- Farside's historical tables are current-vintage and do not provide historical as-of snapshots or verified publication timestamps. The five-calendar-day embargo is conservative but does not prove exact historical availability.
- The sample starts in July 2024 because the ETH spot ETF flow history begins then; it covers a limited number of regimes.
- The experiment forecasts ETH/BTC returns only. It did not test a tradable strategy, fees, execution, leverage or portfolio returns.
- The bootstrap interval is wide and crosses zero; the incremental feature is not established as useful or decisively harmful.

## DAILY KPI

**MET.** This session completed one new preregistered real-market walk-forward backtest and recorded its evidence-backed disposition. A negative or inconclusive result counts; no profitability claim is made.

## RESEARCH VS. OPERATIONS

Research was the primary output: one complete real-data forecast experiment and an evidence-backed inconclusive disposition. Repository/CI work was supporting execution: branch reconciliation, atomic admission, test verification and evidence persistence. Exact wall-clock effort split was not instrumented.

## NEXT

Select a materially distinct, falsifiable hypothesis on a future wake-up. Search the registry and prior reports first, freeze its difficulty-adjusted timebox and acceptance gates before implementation, and prefer a mechanism/source that does not simply retune relative BTC/ETH ETF flow pressure. Keep all work paper-research only.
