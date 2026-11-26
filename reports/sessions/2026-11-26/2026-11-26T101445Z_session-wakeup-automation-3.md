# Research session — README wake-up, BAA10Y/BTC downside-risk screen and timebox enforcement (2026-11-26T101445Z)

## Objective and repository reconciliation

- Followed the current self-contained `README.md` wake-up contract; `main` is operational truth.
- Starting main commit: `243e93f9c29894cc58cfde7b8870896516da4374` (2026-11-26T07:40:59Z).
- Reconciled the current tree, hypothesis registry, timestamped session reports, recent workflow runs, branches, open PRs and issues. No open PRs or issues were present; no active Actions runs remained at final verification.
- The daily minimum of one distinct real-data hypothesis backtest had already been met earlier on 2026-11-26. This session therefore ran one additional, materially distinct forecast screen; it does not claim a new daily minimum.
- The current README is the self-contained wake-up contract. The previous `tasks/ACTIVE-QUEUE.md` path is absent on current main and was not treated as an active instruction.

## Governance repair — difficulty-adjusted timeboxes

The current README required difficulty-adjusted expiry but did not state concrete default budgets or make the required preregistration fields sufficiently explicit. Added a mandatory self-contained policy to the README and a regression assertion in `research/test_workflow_admission.py`.

| Difficulty | Maximum substantive cycles | Maximum elapsed time |
|---|---:|---:|
| LOW | 2 | 2 calendar days |
| MEDIUM | 4 | 5 calendar days |
| HIGH | 8 | 10 calendar days |

Every new hypothesis must record its difficulty/rationale, exact UTC start, cycle cap, hard implementation deadline, hard final conclusion deadline, gates and expiry rule before implementation or empirical-result inspection. The earlier of the cycle cap or calendar limit governs. Deadline expiry without valid empirical evidence is INCONCLUSIVE/INFEASIBLE, never a strategy-performance NO-GO. No silent reset or automatic extension.

## New hypothesis and preregistered timebox

- **Hypothesis:** `QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01`.
- **Question:** Does a strictly lagged five-business-observation widening in Moody's Baa corporate-bond yield minus the 10-year Treasury yield add information about next-five-session BTC downside semivariance beyond BTC's own recent downside semivariance and realized variance?
- **Difficulty:** MEDIUM. Public daily source and reusable BTC archive/model infrastructure were available; moderate new event construction, publication-time alignment, tests, workflow integration and persistence were required.
- **Start:** 2026-11-26T10:05:47Z.
- **Maximum:** 4 substantive cycles.
- **Implementation deadline:** 2026-11-29T10:05:47Z.
- **Final conclusion deadline:** 2026-12-01T10:05:47Z.
- The experiment was completed in one admitted cycle. No alternate lag, feature, horizon, asset, threshold or model was tuned.

Novelty was deliberately scoped. Lee and Ryu (2026), *State-Dependent Relationship Between Cryptocurrency Returns and Credit Spreads*, already study credit spreads and cryptocurrency returns. Their reported BTC return relationship is statistically insignificant across quantiles after controlling for the S&P 500. This experiment instead tests incremental forecasting of BTC downside semivariance with a different public yield-spread proxy and a frozen weekly walk-forward model; it makes no first-in-literature claim. Reference: https://doi.org/10.1111/eufm.70010.

## Data feasibility and accepted coverage

- **FRED BAA10Y:** 10,224 daily business-day observations, 1986-01-02 through 2026-11-24. Raw-response SHA-256: `ba047b5add5187dc42a9f85a990cf7e5ce65e0f515d54bf84eb9a6781ca1f6cb`. Series: https://fred.stlouisfed.org/series/BAA10Y.
- **Binance Spot BTCUSDT:** 3,387 completed UTC daily candles, 2017-08-17 through 2026-11-24. All 135 official monthly/daily archives passed their SHA-256 sidecar checks; archive-manifest SHA-256: `1e9dabf9de7315ef922c711f37d3bcd2599ba9be29ac93048b515b31ceaa6748`.
- **Event construction:** 483 Wednesday candidate origins; 481 accepted; two early events skipped for insufficient BTC price history. Five-calendar-day BAA10Y publication embargo, maximum four-day observation age at cutoff, five-session targets and weekly spacing. No stale spread observations, missing BTC returns, incomplete targets or overlapping targets were accepted.
- FRED's BAA10Y notes contain a Moody's proprietary-information notice. No raw BAA10Y or BTC observations were committed or redistributed; the repository retains hashes, coverage metadata and aggregate metrics only. BAA10Y is a yield differential, not a pure option-adjusted default-risk spread.

## Empirical result

**Disposition: INCONCLUSIVE — no promotion.**

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 122 | 255 |
| Baseline RMSE | 1.0195223 | 0.8668067 |
| Augmented RMSE | 1.0757759 | 0.8698559 |
| RMSE improvement | -5.5176% | -0.3518% |

- Test paired squared-loss mean (baseline minus augmented): `-0.00529536`.
- 95% four-event block-bootstrap interval: `[-0.02255655, 0.01141123]`, 2,000 replications.
- The augmented model worsened RMSE in both chronological periods, but the paired test-loss interval crosses zero. The frozen rejection criterion therefore was not met.
- **Disposition: INCONCLUSIVE.** Do not describe this as a proven lack of predictive value, do not promote it, and do not retune the same hypothesis.

## Implementation, tests and workflow recovery

- Added `research/baa10y_btc_downside_semivariance.py`, its deterministic test suite, the preregistration and a path-filtered GitHub Actions workflow.
- Added the timebox policy to `README.md` and regression coverage to `research/test_workflow_admission.py`.
- The first admitted run (`45799152738`) failed two deterministic test assertions because the synthetic spread fixture was not monotonic and the stale-observation fixture removed too much history. No data retrieval or empirical run occurred in that attempt.
- Corrected the synthetic fixture and stale-window setup; allowed skipped weekly candidate events while still enforcing the Wednesday schedule and non-overlapping matured targets.
- The second admitted run [45799291521](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45799291521) passed the experiment-specific deterministic tests and workflow-admission regression suite, completed the full real-data screen, and persisted the report/manifest/registry/preregistration update.
- The separate repository admission-guard run [45799152814](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45799152814) also passed.

## Durable artifacts and commits

- Preregistration: [research/PREREGISTERED-QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01.md](../../../research/PREREGISTERED-QFR-2026-11-26-BAA10Y-BTC-DOWNSIDE-01.md)
- Implementation: [research/baa10y_btc_downside_semivariance.py](../../../research/baa10y_btc_downside_semivariance.py)
- Tests: [research/test_baa10y_btc_downside_semivariance.py](../../../research/test_baa10y_btc_downside_semivariance.py)
- Workflow: [.github/workflows/baa10y-btc-downside-semivariance.yml](../../../.github/workflows/baa10y-btc-downside-semivariance.yml)
- Experiment report: [2026-11-26T101330Z_session-baa10y-btc-downside-45799291521.md](2026-11-26T101330Z_session-baa10y-btc-downside-45799291521.md)
- Manifest: [reports/generated/baa10y-btc-downside-semivariance/45799291521-attempt-1/manifest.json](../../generated/baa10y-btc-downside-semivariance/45799291521-attempt-1/manifest.json)
- Registry and preregistration now record the terminal INCONCLUSIVE disposition.
- Atomic research admission commit: `3debfd54e3fc46674d507b0c166301a4410f6b51`.
- Deterministic-test repair/admission commit: `3dc44a0cae30dfba83aa1e617d68c83fe64faab6`.
- Evidence persistence commit: `b6d59efdfcd06c323cf48e358c3acae4b27ffc0e`.

## Verified / unverified

**VERIFIED:** main contains the implementation, tests, workflow, preregistration, README timebox policy, registry row, report and manifest; BAA10Y and BTC source coverage; all 135 Binance archive checksums; 481 accepted events; exact walk-forward metrics; deterministic test and admission-guard success; no open PRs/issues or active runs at final check.

**UNVERIFIED:** historical point-in-time FRED vintages, exact historical BAA10Y publication timestamps, independent reconstruction from a separate BTC venue, causal interpretation, future-regime stability and instrument-level economic value.

## Daily KPI and next action

- **Daily KPI:** already MET before this additional experiment by distinct real-data backtests on 2026-11-26. The initial failed test attempt does not count.
- **Next:** treat the BAA10Y hypothesis as closed INCONCLUSIVE. Do not tune it. Discover another materially distinct mechanism only after checking the registry, literature, source feasibility, licensing and publication timing; preregister its difficulty-adjusted timebox before implementation.
- **Research versus operations:** one additional real-data forecast screen; the remaining effort was the demonstrated README timebox-policy gap, implementation, deterministic test repair, workflow admission and durable evidence persistence.
