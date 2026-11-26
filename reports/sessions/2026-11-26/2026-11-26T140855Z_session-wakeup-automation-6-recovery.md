# Wake-up session report — automation turn 6 (2026-11-26T14:08:55Z)

## Repository reconciliation

- Repository: `takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH`; default branch: `main`.
- Starting main: `80a397d5e271803a6a4fe9d2f0f944a93c1d2469`.
- Final main after this session's governance repair: `3b174fba588335f03a6fa5542f6794686a3e7a13`.
- Reviewed the current self-contained README wake-up contract, registry, latest session reports, relevant source and preregistration files, current workflow runs, open PRs/issues and repository tree.
- The old `tasks/` directory is absent on current main; the README, hypothesis registry and timestamped reports are the active durable state.
- No open PRs, open issues or in-progress Actions runs remained at final verification.

## Research output and daily KPI

The UTC-date daily real-data backtest minimum was already met before this wake-up. The current-day registry and persisted manifests show multiple distinct completed real-data forecast screens, including the BAA10Y/BTC, CFTC Bitcoin crowding and Deribit relative-DVOL studies. This session did not create a quota-only experiment or claim another backtest.

I independently reviewed the two newest completed studies:

### CFTC CME Bitcoin leveraged-fund gross-short crowding

- Hypothesis: `QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01`.
- Final accepted run: [45821991487](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45821991487), source commit `464a6cf4f7361c3af25325ea3ea98366b5eafbf0`.
- Coverage: 450 CFTC TFF observations from 2018-04-10 to 2026-11-17; 3,652 Coinbase/FRED BTCUSD daily observations; 375 accepted weekly events. The documented CFTC shutdown catch-up interval was excluded.
- Validation/test forecasts: 85 / 238.
- RMSE improvement: -2.4072% / -1.1170%.
- Paired test-loss 95% block-bootstrap interval: [-0.05335, 0.01964], crossing zero.
- High-crowding versus other-event downside-semivariance difference: -1.0485 percentage-points squared; 95% interval [-2.4307, 0.3485].
- Disposition: **INCONCLUSIVE** under the frozen rule. The feature is not a direct measure of bearish intent, and the result is forecast-only.

### Deribit relative DVOL and ETH/BTC realized volatility

- Hypothesis: `QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01`.
- Final accepted run: [45834522305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45834522305), source commit `363211845204dd130b5402b9d3aea794c0a0387d`.
- Coverage: 1,341 daily observations for each of BTC DVOL, ETH DVOL, Coinbase BTCUSD and Coinbase ETHUSD, 2023-03-26 to 2026-11-25; 187 accepted non-overlapping events.
- Validation/test forecasts: 36 / 98.
- RMSE improvement: +0.8772% validation, -1.4427% test.
- Paired test-loss 95% block-bootstrap interval: [-0.013995, 0.005559], crossing zero.
- Disposition: **INCONCLUSIVE**. The study is a relative-volatility forecast screen, not an ETH/BTC trading strategy or P&L result.

Neither study should be retuned under its existing hypothesis ID or promoted to live trading.

## Verified process failure and same-session repair

The CFTC implementation history exposed a concrete breach of the README's atomic-admission policy. Multiple same-hypothesis correction commits retained the `[QFR-ADMIT]` marker and each triggered a push workflow, although their diffs were incomplete bundles. Examples include:

- `0d83a9109359902ee4d263ddc7c4d0a14cae5bb2`: test-only correction.
- `730145541be61d0f62823bd346704edd2bf782fd`: implementation-only correction.
- `b74ce51bf5d1d430474ed64e35875aa169bc6056`: workflow-only correction.
- `8f2bd3b352ae4f3ae720cc79daec4709f77326c3`: test-only correction.
- Later same-hypothesis retries also used the marker before the final accepted run.

The sequence produced repeated executions, including failed runs [45821064419](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45821064419), [45821197853](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45821197853) and [45821201065](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45821201065). The final CFTC evidence was ultimately accepted only from run 45821991487. This is a demonstrated process bottleneck, not a reason to discard the final validated result.

### Corrective change

- Added a mandatory **Failed-admission recovery** rule to `README.md`: same-hypothesis repairs must use ordinary unmarked commits; after deterministic suites pass, the authorized retry uses `workflow_dispatch` against the verified current commit; record the exact `source_commit_sha`; inspect persisted diagnostics before any post-retrieval rerun; reserve `[QFR-ADMIT]` for a genuinely new complete atomic admission.
- Added a regression test to `research/test_workflow_admission.py` so future agents cannot silently omit this recovery rule.
- The first guard run, [45835862342](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45835862342), correctly exposed two brittle assertion strings that omitted literal Markdown backticks. Those assertions were corrected in a follow-up test-only commit.
- Final guard run [45836007143](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45836007143) completed successfully. Compilation, the admission-policy suite, VXN/VIX, KC PRS, WTI, Fed-balance-sheet and Deribit regression steps all passed.

## Durable changes

- Commit `d9956304e8c1edb8f578562144281c8aefa50af3`: README recovery rule and regression-test addition.
- Commit `3b174fba588335f03a6fa5542f6794686a3e7a13`: corrected the two literal-string assertions.
- Final verified main head: `3b174fba588335f03a6fa5542f6794686a3e7a13`.
- Changed files: `README.md`, `research/test_workflow_admission.py`.

## Verified / unverified

**VERIFIED**
- Both latest studies' final run IDs, source SHAs, coverage, sample counts, metrics and INCONCLUSIVE dispositions match their committed manifests/reports and registry.
- Multiple incomplete same-hypothesis marker commits and repeated workflow executions are visible in Git history and Actions.
- The new recovery rule is present on main and its regression test passes.
- Final admission-guard workflow run succeeded; no active runs, open PRs or open issues remained at final inspection.

**UNVERIFIED**
- Independent replication of either forecast result from a separate implementation/provider.
- Historical point-in-time revisions for all source datasets.
- Any causal interpretation, executable trading edge, costs-adjusted strategy performance or live suitability.

## Research versus operations

- Research: independent audit of two current-day real-data screens; no new hypothesis was necessary because the daily minimum was already met.
- Operations: one verified workflow-admission bottleneck was corrected in the README and regression suite. The first test run failed due to assertion-string formatting and was repaired in this session.
- No live orders, capital deployment or strategy promotion occurred.

## Next

1. Select a materially distinct information source and mechanism; do not retune the two INCONCLUSIVE studies.
2. Preregister the new hypothesis and its difficulty-adjusted timebox before implementation or result inspection.
3. For any same-hypothesis pre-data failure, repair with unmarked commits, validate, then use one explicit workflow dispatch. Do not repeat the marker-push retry pattern.
