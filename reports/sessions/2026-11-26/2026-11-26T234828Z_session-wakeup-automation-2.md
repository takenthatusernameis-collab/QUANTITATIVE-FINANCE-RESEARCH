# Wake-up session report — 2026-11-26T234828Z

## Objective and repository reconciliation

- Repository: `takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH`; branch: `main`.
- Starting main: `05356f639b525947be82b9c5091db88bc8dbdfc9`.
- Read the exact README entry-point directive and the current self-contained factory contract, including mandatory difficulty-adjusted timeboxes, atomic research admission, direct-agent recovery, immutable execution provenance and timestamped reporting.
- Current tree contains 286 entries. No Actions runs are queued or in progress. No open pull requests or issues were returned.
- The pending task from the preceding wake-up was the preregistered STLFSI4/BTC downside-semivariance experiment. It is now complete; it must not be treated as still queued.

## Completed pending hypothesis

- Hypothesis: `QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01`.
- Initial run [45727248228](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45727248228) completed its workflow but did not produce a valid backtest. Binance REST returned HTTP 451 and the alternate data endpoint supplied a candle that failed the full-UTC-day validation. Its manifest correctly records `INCONCLUSIVE`; it does not count toward the daily backtest minimum.
- Corrected run [45738528717](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45738528717) replaced the failing REST candle path with official Binance Vision archives and per-file checksum verification. All workflow steps succeeded: deterministic model tests, repository admission tests, data retrieval, walk-forward forecast and persistence.
- Evidence was persisted by [commit d723498](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d723498c273b68cd39ce24bb959ea8be5c301d0c). The run-specific report and manifest, preregistration disposition and hypothesis-registry row are present on `main`.

## Frozen empirical result

- BTCUSDT Spot: 3,387 complete daily UTC candles, 2017-08-17 through 2026-11-24; 135 official archives, with archive checksums verified.
- FRED STLFSI4: 484 weekly observations, 2017-08-18 through 2026-11-20.
- Forecast samples: 120 validation observations (2019–2021) and 254 test observations (2022 onward).
- Augmented-model RMSE improvement versus the frozen baseline: **-1.01897% validation** and **-1.23510% test**. Negative means the augmented model was worse in both periods.
- Paired test squared-loss block-bootstrap (2,000 replications, four-event blocks): baseline-minus-augmented mean loss difference `-0.0167702` percentage-points-squared; 95% interval `[-0.0317245, -0.0037903]`. The interval is wholly negative and favors the baseline.
- Final disposition: **REJECTED** under the preregistered rule. This is a forecast-screen result, not a trading P&L or live signal.
- Material limitation retained: STLFSI4 uses the current revised FRED vintage, not historical ALFRED vintages. The publication lag does not eliminate revision/look-ahead risk. No causal or independently validated claim is made.

## Daily research KPI and discovery discipline

- UTC date assessed: **2026-11-26**.
- The minimum was already met by ten distinct successful real-data hypothesis workflows recorded in the prior same-day audit. Repeated attempts of one hypothesis were not counted as separate discoveries.
- No additional backtest was launched in this wake-up. The daily minimum was already satisfied, and no new candidate passed both the repository/literature novelty screen and data-feasibility gate. This avoids creating cosmetic work merely to increase run counts.
- A brief literature screen found that simple cross-exchange funding-rate dispersion/arbitrage has already been studied across 26 exchanges and 749 symbols, while cross-sectional cryptocurrency futures basis and momentum factors are also established. A generic replication of those ideas was therefore not admitted. References: [Zhivkov (2026), The Two-Tiered Structure of Cryptocurrency Funding Rate Markets](https://doi.org/10.3390/math14020346); [Chi et al. (2023), An Empirical Investigation on Risk Factors in Cryptocurrency Futures](https://doi.org/10.1002/fut.22425).
- Simple Bitcoin ETF-flow-to-return forecasting was also not admitted: published work already examines flow/price prediction and price-discovery dynamics, with mixed evidence and material endogeneity concerns. No new hypothesis or parameter variation was created from this screen.

## Verified state and next action

- Current main at report creation: `05356f639b525947be82b9c5091db88bc8dbdfc9`.
- README retains the exact first-line directive `COMMIT TO REPOSITORY THE PENDING TASK`; the wake-up contract remains intact.
- No active/queued Actions runs and no open PRs/issues were found.
- Preserve the STLFSI4 rejection and its frozen evaluation sample. Do not rerun or retune it to seek a different result.
- At the next UTC research cycle, discover a materially distinct mechanism, inspect prior work/literature, verify public data semantics and point-in-time availability, then preregister a difficulty-adjusted timebox before substantive implementation.
- No live orders, capital deployment, paid data, private credentials or strategy promotion occurred.

## End-of-session digest

- **RESEARCH OUTPUT:** completed and independently reconciled the pending STLFSI4/BTC backtest; final result REJECTED.
- **HYPOTHESES/RANKING:** registry already records the final rejection; no new hypothesis admitted.
- **DAILY KPI:** MET for 2026-11-26 by multiple distinct real-data backtests.
- **CHANGED:** added this timestamped wake-up report only.
- **VERIFIED:** corrected run 45738528717 and all steps succeeded; report/manifest and registry disposition persisted in commit d723498; no active runs or open PRs/issues.
- **UNVERIFIED/BLOCKED:** historical point-in-time FRED revisions and future-regime stability remain unverified.
- **RESEARCH VS. OPERATIONS:** no additional backtest was warranted after the daily minimum was met; work focused on closing the pending task and reconciling its evidence.
- **NEXT:** on the next UTC date, admit only a genuinely distinct, source-feasible hypothesis with a frozen timebox.
