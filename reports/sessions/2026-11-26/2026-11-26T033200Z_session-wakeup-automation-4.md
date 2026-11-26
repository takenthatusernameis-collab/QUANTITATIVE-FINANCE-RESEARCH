# Wake-up session 4 — research preflight and KC PRS hypothesis admission

**Recorded:** 2026-11-26 03:32 UTC  
**Repository:** https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH  
**Main commit at report time:** 512ce133a86872fdea94e684d2bb65967e175bc2

## Executive outcome

- Reconciled current main, recent session reports, registry, tree, workflows, recent runs, PRs and issues before selecting work.
- No open PRs, no open standalone issues and no active workstream from the prior session were found. Historical branches were preserved; no disposable tracked artifacts were identified for deletion.
- The 2026-11-26 daily real-data backtest minimum had already been met by three distinct completed experiments: STLFSI4 -> BTC downside semivariance (REJECTED), SOFR-EFFR repo premium -> S&P 500 realized volatility (REJECTED), and VXN/VIX cross-index spread -> S&P 500 realized volatility (INCONCLUSIVE).
- Continued with an additional materially distinct information source: Kansas City Fed Policy Rate Skew (KC PRS), an option-implied asymmetry measure for short-term rates one year ahead.
- Preregistered and committed a new bounded 2-year Treasury yield forecasting experiment. No empirical result is claimed yet because the post-fix GitHub Actions run remains queued.

## Preflight and repository hygiene

- Main before implementation: b1419c1d29828f86c55a39c9d95a2d03c8c97191.
- Main after implementation and test-fixture repair: 512ce133a86872fdea94e684d2bb65967e175bc2.
- Repository tree: 178 tracked paths; 16 workflow files; no duplicate hypothesis ID for the new workstream.
- Open PRs: 0. Open standalone issues: 0.
- Previous completed real-data runs inspected:
  - https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45738528717
  - https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45739654076
  - https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45741392870
- No repository cleaning deletion was justified. Historical branches and their research evidence were retained.

## New hypothesis and preregistration

**ID:** QFR-2026-11-26-KCPRS-POLICY-SKEW-DGS2-01

Question: does the latest strictly prior KC PRS observation add incremental chronological out-of-sample forecast information for the next 21-observation change in the 2-year Treasury yield beyond current DGS2 level, recent DGS2 changes and the 10y-2y curve slope?

Prior-work boundary:
- The Kansas City Fed's 2024 Economic Bulletin already documents that KC PRS tends to lead interest-rate cycles and relates it to one-year-ahead federal-funds forecast errors.
- This experiment does not claim discovery of that mechanism. It tests a narrower daily walk-forward forecast extension.
- KC PRS source methodology uses Eurodollar futures options before 2023 and SOFR futures options from 2023 onward. The frozen validation is 2018–2022; the frozen test starts in 2023.
- Source metadata and history were checked before implementation using the FRED KC PRS table, which reports a history beginning 1989-04-03 and current observations through 2026-11-23.
- References:
  - https://www.kansascityfed.org/research/economic-bulletin/how-do-financial-markets-perceive-the-balance-of-risks-to-the-policy-rate/
  - https://www.kansascityfed.org/data-and-trends/kansas-city-fed-policy-rate-skew/
  - https://fred.stlouisfed.org/data/KCPRS

Frozen design:
- Sources: FRED KCPRS, DGS2 and DGS10 daily CSV series.
- KCPRS predictor: latest observation dated strictly before the DGS2/DGS10 signal date; same-day use prohibited.
- Baseline features: current DGS2 level, 21- and 63-observation DGS2 changes, and 10y-2y slope.
- Augmented model adds only KCPRS level.
- Target: next 21 observed Treasury-session DGS2 change in basis points.
- Event spacing: 22 sessions; target windows do not overlap.
- Rolling training window: 52 fully matured prior events.
- Validation: 2018–2022. Test: 2023 onward.
- Minimum: 30 forecasts in each period.
- Paired test inference: 2,000 circular-block bootstrap resamples, three consecutive events per block.
- Frozen decision: PROMISING only if both validation and test RMSE improve and the paired-loss 95% lower bound is positive; REJECTED only if both RMSEs fail to improve and the paired-loss upper bound is negative; otherwise INCONCLUSIVE.
- No trading, causal or deployment claim is authorized.

## Implementation committed

Commit 0ea3ae1c3c8f33c8c84b874d6c09434794dec1fc:
- research/kcprs_policy_skew_dgs2.py
- research/test_kcprs_policy_skew_dgs2.py
- research/PREREGISTERED-QFR-2026-11-26-KCPRS-POLICY-SKEW-DGS2-01.md
- .github/workflows/kcprs-policy-skew-dgs2.yml
- Updated .github/workflows/workflow-admission-tests.yml to compile and run the new regression suite.
- Added the preregistered hypothesis to research/HYPOTHESIS-REGISTRY.md.

Commit 512ce133a86872fdea94e684d2bb65967e175bc2:
- Fixed the synthetic walk-forward fixture to include the source_regime field required by the prediction record.
- The first run exposed a fixture-only KeyError; 12 of 13 new deterministic tests passed before that one failure. The production event builder already emitted the field. The fixture was corrected rather than weakening production checks.

## Validation and execution state at 03:32 UTC

- First research run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45749202492 — FAILED in deterministic tests because the synthetic event fixture omitted source_regime. The live data retrieval step was correctly skipped.
- Post-fix research run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45749415970 — QUEUED; no runner ID/name assigned at last inspection.
- Post-fix admission/regression run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45749416059 — QUEUED.
- The repository's Actions workflow checks out and verifies the exact triggering commit, has cancel-in-progress false, runs deterministic tests before source retrieval, and persists the report, manifest, registry and preregistration update.
- A direct local execution fallback was attempted, but the container could not resolve external DNS (Temporary failure in name resolution). No local FRED download or local empirical run was possible. This is not a reason to weaken the data checks.
- GitHub Status currently reports all systems operational. It records a resolved multi-product incident on 2026-11-25, including Actions degradation between 15:55 and 16:52 UTC. The present queued jobs have no runner assignment; no active status incident is declared. Status: https://www.githubstatus.com/

## Verified / unverified boundary

**Verified**
- Main commits and repository files.
- Preregistration, registry entry, immutable workflow checkout, admission marker and concurrency safeguards.
- 12/13 deterministic tests passed on the first run; the remaining failure was isolated to a synthetic fixture and repaired in main.
- Daily KPI already met by the three earlier real-data backtests.

**Not yet verified**
- Full post-fix deterministic suite.
- Live FRED retrieval and source coverage.
- Accepted event count, walk-forward predictions, metrics, bootstrap and final disposition.
- Automatic persistence of this experiment's report and manifest.

## Next executable action

Monitor the existing post-fix runs; do not dispatch duplicate work while they are queued. When a runner starts, verify the full deterministic suite, actual FRED source coverage, strict-prior KCPRS alignment, non-overlap and target maturity, forecast metrics, bootstrap, and the persistence commit. If runner assignment remains unavailable, diagnose the runner path and use a materially different authorized execution route; do not claim an empirical result or weaken the frozen acceptance rules.
