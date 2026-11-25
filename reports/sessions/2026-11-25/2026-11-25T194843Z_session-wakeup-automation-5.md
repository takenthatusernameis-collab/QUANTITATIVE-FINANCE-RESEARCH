# Research session — repository wake-up audit (2026-11-25T194843Z)

## Objective

Reconcile the current default branch, recent real-data research, workflow execution history and candidate data sources. Avoid duplicating completed daily research or reopening frozen hypotheses.

## Research output

No new backtest was run in this session. The UTC 2026-11-25 minimum was already met by multiple distinct real-data walk-forward studies recorded earlier today. This session performed a post-run scientific audit and a bounded new-source screen.

### Latest 10-year Treasury basis-crowding study

- Hypothesis: `QFR-2026-11-25-UST-10Y-BASIS-CROWDING-SP500-RV-01`.
- Final workflow run: [45688135035](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45688135035).
- Final test suite: 25 tests passed; data retrieval, empirical run and evidence persistence all completed successfully.
- Data: CFTC TFF futures-only code 043602, 1,067 weekly rows from 2006-06-13 to 2026-11-17; FRED SP500 2,512 rows and VIXCLS 2,546 rows, common price coverage through 2026-11-24.
- Accepted event sample: 419; validation forecasts: 116; test forecasts: 198.
- Augmented-model RMSE improvement: 4.8230% validation and 2.3343% test.
- Paired test squared-loss bootstrap 95% CI: [-0.000609, 0.007489], crossing zero.
- High-crowding minus other-event realized volatility: -0.8135 percentage points; 95% block-bootstrap CI [-1.2331, -0.3903], entirely below zero.
- **Disposition remains INCONCLUSIVE.** The forecast RMSE improves in both periods, but the preregistered directional event study contradicts the claim that high net-short crowding precedes higher volatility, while paired-loss inference is not conclusive. The feature is also only a leveraged-fund positioning proxy, not direct basis-trade identification. Do not promote, tune or reinterpret the frozen hypothesis.

### Workflow execution bottleneck

The recent UST basis-crowding, Treasury-curve, JPY carry-unwind and E-mini CFTC crowding workflows each had one or more failed deterministic-test attempts before a successful final run. The failed attempts stopped at the test step; the real-data retrieval step was skipped, so these were implementation/fixture failures rather than bad empirical datasets.

Observed examples:
- UST basis-crowding: two test-stage failures before the successful 25-test run.
- Treasury curve: two test-stage failures involving a gap expectation and fixture keys before the successful run.
- JPY carry-unwind: one test-stage failure from a fixture target-key mismatch before the successful run.
- E-mini CFTC crowding: one test-stage failure involving fixture assumptions before successful replays.

The workflows use path-filtered `push` triggers on `main`. Separate incremental commits to the model, tests and workflow therefore started real Actions jobs before the implementation was stable. This is a demonstrated, avoidable source of failed/cancelled runs. The README now requires atomic, test-ready admission for these workflows.

## New source screen — financial stress and Bitcoin downside risk

A possible distinct future hypothesis is whether the weekly St. Louis Fed Financial Stress Index (STLFSI4), with a conservative publication lag, adds information about subsequent Bitcoin downside semivariance beyond Bitcoin's own recent volatility and momentum.

- FRED identifies STLFSI4 as a weekly Friday-ending index built from 18 financial-market series; its long history begins in 1993 and its values are subject to revision: https://fred.stlouisfed.org/series/STLFSI4.
- Prior literature has examined financial stress and Bitcoin volatility/returns, so the repository must frame any contribution as a strict-lag, chronological incremental forecast test—not a first-discovery or causal claim: https://doi.org/10.24135/afl.v14i.1006 and https://doi.org/10.1016/j.qref.2018.04.003.
- FRED's Coinbase BTC series CBBTCUSD states that reproduction is prohibited without prior written permission: https://fred.stlouisfed.org/series/CBBTCUSD. Do not copy or redistribute that raw series in the repository. A public Binance BTCUSDT daily-kline source may be evaluated instead, subject to endpoint, coverage, UTC-close and terms checks.
- The Cboe SKEW dashboard warns against automated extraction of its delayed quote table; it was not admitted as an automated data source: https://www.cboe.com/data/quotes/skew/dashboard/.

**Disposition:** IDEA / feasibility screen only. No data were fetched for this candidate, no model was fitted and no metrics were computed. Do not preregister until the exact Binance source and the STLFSI4 publication-availability convention have been verified.

## Hypotheses and ranking

- UST 10Y basis-crowding: INCONCLUSIVE; frozen.
- Other same-day BTC macro and S&P 500 volatility forecast screens remain at their recorded registry dispositions; no status changes made.
- No candidate is promoted to an executable or tradable strategy.

## Daily KPI

**MET before this session** by multiple distinct real-data backtests on 2026-11-25. No additional backtest was required for the minimum, and no cosmetic parameter variant was run.

## Changes

- Updated `README.md` with an atomic-commit rule for path-filtered main-branch research workflows, based on the observed premature test-stage runs.
- Added this timestamped session report.
- No research source code, data, model specification, workflow permissions, credentials, branch protections or trading controls were changed.

## Verified

- Main before this session: `190ba7b3025b6a1d9dfd386cd35eac3d6162100d`.
- Latest completed empirical workflow: run 45688135035; 25 deterministic tests passed and evidence persistence succeeded.
- The UST basis-crowding report and manifest agree on the sample counts, metrics and INCONCLUSIVE disposition.
- Recent failed workflow attempts terminated before real-data retrieval.

## Unverified / blocked

- No new STLFSI4/Binance dataset was retrieved or backtested.
- Binance historical-data terms, complete coverage, exact UTC close semantics and STLFSI4 point-in-time release availability remain to be verified before admission.
- No independent reconstruction of the UST basis-crowding result was performed in this session.

## Research versus operations

- Research: post-run statistical interpretation and a new-source/literature feasibility screen.
- Operations: workflow-history diagnosis and a narrowly scoped README process correction.
- No live orders, capital deployment, paid data or credentials.

## Next

Verify Binance BTCUSDT daily history and STLFSI4 release timing from primary sources. If both pass acceptance, preregister one distinct, strictly lagged downside-semivariance forecast with frozen event construction and chronological validation/test periods before inspecting results. Otherwise record the exact data blocker and select a different mechanism.
