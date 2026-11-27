# Wake-up session — 2026-11-27T020203Z

## Objective

Reconcile the live main branch and execute the pending source-feasible research task without duplicating work or weakening the frozen protocol.

## Research output — completed

- Hypothesis: `QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01`.
- Real-data backtest: [Actions run 45926394994](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994), completed successfully on exact admission commit `7e968673f39e26001ea45f6664129efe77240db2`.
- Evidence persistence commit: [a87e750](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a87e7509ebd564dfeab85f631cb543dbea02811c).
- Disposition: **INCONCLUSIVE**, exactly as required by the frozen rule.
- Candidate origins/events: 561/561; walk-forward forecasts: 457; validation/test forecasts: 159/298.
- Validation RMSE improvement: **+0.3119%**. Test RMSE improvement: **−1.0491%**.
- Paired test squared-loss bootstrap: 2,000 replications, block size 4, seed 20261127; baseline-minus-augmented mean loss difference **−0.0159703**; 95% CI **[−0.0371464, +0.00189844]**. The interval crosses zero. Only 4.5% of bootstrap draws favored the augmented model.
- Both models also had negative OOS R² versus the unconditional-mean benchmark in validation and test. This is a weak absolute forecasting result; the preregistered decision concerns incremental performance against the fixed risk/momentum baseline.
- The manifest's generic `directional_accuracy=1.0` is not informative here because both the log-semivariance target and predictions are nonnegative; it was not a preregistered decision input. The shared helper's `*_bp` field names are legacy labels—the reported RMSE/MAE values are in log1p semivariance units, not basis points.
- The validation improvement and test deterioration are mixed evidence. The test CI does not establish decisive inferiority, so neither PROMISING nor REJECTED is justified.
- No trading P&L, profitability, Sharpe, drawdown or live deployment was evaluated.

## Source feasibility — VERIFIED

- Latest successful source preflight: [run 45925248340](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925248340), code commit `6f91629a1f3b5003da516ae1829de1fadf8a0530`.
- 136 checksum-verified Binance Vision BTCUSDT Spot 1d UTC archives; 3,388 rows; coverage 2017-08-17 through 2026-11-25; zero missing dates and zero zero-volume days; all 3,388 rows have finite taker imbalance.
- Frozen archive-manifest SHA-256: `978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe`. The empirical run reproduced this exact hash.
- The 2026-11-26 archive was unavailable at preflight time; the frozen sample end remains 2026-11-25.
- The corrected source-preflight report is [here](2026-11-27T015513Z_session-taker-absorption-source-preflight-45925248340.md).

## Implementation and validation — VERIFIED

- Pre-admission CI [45925665470](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925665470) passed on parent `5f645f5de49d49afb37406d4ff565e48b4dde0bc`, including compilation, workflow admission, 11 source-preflight tests, 14 model tests, 2 persistence tests and existing research regression suites.
- Post-admission guard CI [45926395000](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926395000) passed.
- The empirical workflow passed exact-`github.sha` checkout, immutable-source assertion, deterministic tests, frozen source retrieval, forecast execution, evidence persistence and final COMPLETE-manifest gate.
- The evidence report is `reports/sessions/2026-11-27/2026-11-27T020646Z_session-taker-absorption-btc-downside-45926394994.md`; the manifest is `reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json`.
- The registry now records BACKTESTED / INCONCLUSIVE with metrics and evidence links.

## Same-session handoff correction

The evidence-persistence helper updated the registry but failed to update the preregistration's top status because it only matched the original `PREREGISTERED` literal. Since the atomic admission had changed the status to `ADMITTED`, the result document retained a stale pending status and duplicated section number 8.

I corrected the helper to update any top-level `- **Status:**` line and to normalize the execution-result heading to section 9. The regression fixture now starts from the actual ADMITTED state and verifies preservation of the admission section, BACKTESTED status, and unique section numbering. This is a reporting/handoff fix only; it does not change the frozen model, data, target, split, bootstrap or disposition.

The manifest's `prereg_sha256` remains the digest of the preregistration version at evidence-persistence time. The later status/heading repair is a post-run handoff annotation; the exact triggering protocol remains recoverable from admission commit `7e968673f39e26001ea45f6664129efe77240db2`.

## Repository reconciliation and hygiene

- Main at evidence persistence: `a87e7509ebd564dfeab85f631cb543dbea02811c`.
- No tracked `__pycache__`, `.pyc`, CSV/ZIP raw data, log, scratch, temp or cache artifacts were present at pre-admission inspection; the only generated output added was the intentional JSON manifest.
- No open PRs or issues. Fifteen branches remained; no branch was deleted without evidence of safe retirement.
- Root remains `.github/`, `README.md`, `reports/`, `research/`; no duplicate design-map or active-queue files were present. The original README path/name is unchanged.
- Earlier guard CI failures during rapid fixture/handoff edits were corrected; the final pre-admission and post-admission guard runs passed.

## KPI, timebox and next action

- Daily real-data backtest KPI: **SATISFIED** — one genuinely new, preregistered real-data hypothesis was completed today. INCONCLUSIVE is a valid outcome; no result was manufactured.
- The frozen LOW-difficulty two-cycle budget and both UTC deadlines were not extended or reset.
- Next: use this negative/mixed evidence to avoid repeating the same daily taker-imbalance proxy. Explore a materially different market microstructure mechanism only under a new ID and frozen timebox. Do not tune this hypothesis post hoc or promote it to trading.


## Final follow-up verification

- The status/heading handoff correction was implemented in [commit 9154de9](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9154de9186d1295e3358344955f03dc240f4935a): the evidence updater now transitions any top-level status line, including ADMITTED, and normalizes the execution-result heading to section 9.
- Its first CI attempt, [45926670900](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926670900), exposed an escaped-newline mistake in the new test fixture. The production updater had preserved the admission section and replaced the result heading correctly; the fixture was repaired in [commit f478f61](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/f478f611334badf9bd853371ff9f2466b11fc23e).
- Final regression CI [45926735225](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926735225) completed successfully, including all 14 taker-absorption model tests and 2 evidence-persistence tests plus the repository's existing research regression suites.
- The ordinary follow-up push correctly skipped the expensive backtest workflow in [45926735261](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926735261); no second empirical run or admission-marker commit was created.
- Final follow-up main commit: `f478f611334badf9bd853371ff9f2466b11fc23e`. The empirical result and its persisted manifest remain unchanged.
