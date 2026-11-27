# Independent audit — Bitcoin blockspace fee-rate pressure and BTC downside semivariance

- **Audit timestamp:** 2026-11-27T15:29:39.849Z
- **Hypothesis:** `QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01`
- **Final disposition:** INCONCLUSIVE
- **Cycle:** 4 of 4 — complete
- **Implementation commit:** [2930958302d11ad609bb53a2299952436a7f4b86] (https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/2930958302d11ad609bb53a2299952436a7f4b86)
- **Admission commit:** [8ec52261714abc586bd42df962a7ba0c9d41e34a] (https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8ec52261714abc586bd42df962a7ba0c9d41e34a)
- **Deterministic CI:** [run #46024683649](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024683649)
- **Empirical backtest:** [run #46024917193](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024917193)
- **Primary report:** [2026-11-27T152638Z_session-btc-blockspace-feerate-46024917193.md](2026-11-27T152638Z_session-btc-blockspace-feerate-46024917193.md)
- **Manifest:** [reports/generated/btc-blockspace-fee-rate-btc-downside/46024917193-attempt-1/manifest.json](../../generated/btc-blockspace-fee-rate-btc-downside/46024917193-attempt-1/manifest.json)

## 1. Independent source and provenance checks

- Initial read-only source preflight [run #46013880038](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46013880038) passed at 14:13:15Z. A second preflight [run #46024917231](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024917231) was triggered redundantly by the later admission commit; both preflight executions used one GET and zero retries. The model backtest itself also used exactly one GET. Mempool response: one GET, zero retries, HTTP 200, no payment; response SHA-256 `41738f90d16c9a7cd856435b0fe3f8164d0f743ba994b64d4987bfb4be4ceaa1`.
- The response contained 2,193 ordered 12-hour rows across 1,097 raw UTC dates. The first and last partial dates (2023-11-27 and 2026-11-27) were excluded. The accepted window contains 1,095 contiguous completed UTC dates from 2023-11-28 through 2026-11-26, with two bins per included date and a one-day publication lag.
- Binance BTCUSDT Spot 1d data contains 1,094 contiguous candles from 2023-11-28 through 2026-11-25, retrieved from 61 monthly/daily archives.
- I independently compared every downloaded archive URL, archive SHA-256 and checksum-sidecar SHA-256 against the previously accepted full-history manifest: **61/61 matched**. The reused full-history manifest hash is `978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe`; the model-window subset manifest hash is `337663735a90c3f86418aa550de5a715477f3e3a98493229af828e6496ae1e7a`.
- The manifest records `raw_observations_saved=false`; no raw fee-rate or price observations were committed.

## 2. Timing and sample construction

- 179/179 candidate event origins were accepted; no events were skipped for missing lags, gaps, invalid returns or incomplete targets.
- Signal origins are six UTC calendar days apart. Each target covers exactly the next five daily returns; all target windows are non-overlapping and fully matured before the next signal.
- The first signal is 2023-12-18 and the last is 2026-11-20; the final target ends 2026-11-25.
- The first 65 events are the rolling training warm-up, leaving 114 forecasts: 29 validation forecasts and 85 test forecasts. Both frozen minimum sample requirements are satisfied.

## 3. Independent metric arithmetic and decision-rule replay

| Period | Baseline RMSE | Augmented RMSE | Recomputed improvement |
|---|---:|---:|---:|
| Validation 2025-H1 (n=29) | 0.8872549546059562 | 0.8917247810925903 | -0.5037815188779992% |
| Test 2025-07-01 onward (n=85) | 0.7174010643964365 | 0.7208686337088329 | -0.4833515706188392% |

The improvement formula was independently recalculated as `100 * (baseline_RMSE - augmented_RMSE) / baseline_RMSE`; both values match the persisted report and manifest.

The paired test squared-loss moving-block bootstrap used 2,000 replications, block size five and seed 20261127. Its mean baseline-minus-augmented loss difference is -0.004987299868099742; the 95% interval is [-0.016317454039132775, +0.005471370322788428], with 16.55% positive replications.

- **GO is not met:** neither period reaches the required +1.0% improvement; both improvements are negative.
- **REJECTED is not met:** although both RMSE improvements are negative, the paired-loss confidence interval is not entirely below zero; it crosses zero.
- **INCONCLUSIVE is therefore the exact frozen-rule outcome.** It must not be relabeled as a performance NO-GO or promoted as an edge.

## 4. CI and workflow audit

- 13/13 model regression tests passed, including fee-lag timing, target construction, event spacing, no-overlap, 65-event training maturity, sample minimums, decision thresholds, bootstrap determinism and accepted archive-hash matching.
- The source-preflight regression tests and full repository workflow-admission suite passed.
- The backtest workflow checked out the exact admission commit and completed all steps successfully. Evidence persistence to main also succeeded.
- The separate read-only source-preflight workflow was redundantly triggered by the admission commit because its path filter included the preregistration status file and its own workflow file. Run [#46024917231](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46024917231) succeeded with one GET and no data-integrity impact. This audit includes a path-filter correction so future status-only updates do not repeat source probes; the global admission guard still validates workflow-file changes.

## 5. Final disposition and stop decision

**CLOSED — INCONCLUSIVE.** All four preregistered cycles are complete. Implementation and final conclusion were both completed before their respective hard deadlines. No parameter tuning, alternative percentile, altered lag, new target or second backtest was attempted after seeing the result.

Do not reopen this hypothesis ID. A materially different fee-market mechanism, data vintage, feature or target requires a new hypothesis ID, literature/novelty review and difficulty-adjusted timebox before implementation. This was a forecast-only research screen, not an executable strategy, trading P&L or live-deployment recommendation.

## 6. Daily KPI and next action

The 2026-11-27 minimum of one distinct real-data hypothesis backtest was already met by the BTC/ETH ETF-relative-flow experiment (run #46001444403); this blockspace experiment is an additional completed backtest. The next agent should select a genuinely distinct evidence-first research question rather than cosmetically tune this closed model.
