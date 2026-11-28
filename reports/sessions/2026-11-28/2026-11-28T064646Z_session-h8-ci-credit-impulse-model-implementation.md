# Research session — H.8 C&I bank-credit impulse / BTC downside, source acceptance and model implementation

## Research output

The new H.8 C&I bank-credit impulse hypothesis passed its frozen public ALFRED source preflight. The source was accepted on immutable mainline commit 3d76c559ae41c92b1befa0bfccc296a5469eb514 in GitHub Actions run [#46115128898](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46115128898).

The preflight made one public request, used no API key or paid data, performed zero retries, and returned HTTP 200. It verified five Sunday vintages, exact vintage columns, no future observations, Wednesday weekly observations, the 3–14 day latest-observation age gate, and 483 observations since 2017-08-16 in the latest frozen vintage.

The five-vintage canonical panel SHA-256 is bb50c137a1e1a1d6ce42b79e17899b027476f92b97103522bc3775c2107196c8. The 2020-03-15 and 2026-11-22 vintages differ on 1,831 of 2,462 common observations. This confirms that current-vintage FRED data would not be a valid substitute for the preregistered point-in-time feature.

The exact preflight JSON was recovered from the successful Actions job log and committed as a durable manifest. No raw macro observations were committed.

## Adaptive plan and priority

1. Preserve the frozen hypothesis, MEDIUM timebox and source order.
2. Persist the accepted source-preflight evidence rather than relying on a 30-day Actions artifact.
3. Implement the weekly ALFRED-vintage feature and frozen walk-forward model without changing the registered target, split, training window or decision thresholds.
4. Re-materialize only the already accepted 136 Binance Vision archives, requiring exact equality of every archive hash, checksum-sidecar hash, row count and date range to the prior accepted manifest. Do not extend the market-data end date or use another venue.
5. Add deterministic tests for vintage timing, stale/missing data, weekly cadence, archive identity, event timing, target non-overlap, training maturity, bootstrap and the admission gate.
6. Admit exactly one immutable empirical run only after CI passes. Keep cycle 4 for independent reconstruction.

The daily 2026-11-28 real-data backtest minimum was already met by the separate MEXC funding-dispersion / BTC realized-variance backtest [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This H.8 workstream is additional research and is not being used to manufacture a quota.

## Repository reconciliation and hygiene

- Main HEAD at session start: 3d76c559ae41c92b1befa0bfccc296a5469eb514.
- The latest H.8 source-preflight run and the repository admission-guard run both completed successfully.
- The source-only workflow had two earlier failed runs due shell assertions that did not match the preregistration text; the final literal-safe assertions were committed and the subsequent run passed.
- The H.8 workstream is distinct from the closed Ethereum validator-queue and unadmitted BTC mining-difficulty drafts.
- No branches, historical reports, accepted market manifests or raw research evidence were deleted.
- No active Actions run or concurrent H.8 empirical execution was present at reconciliation.

## Files committed

- reports/generated/h8-ci-credit-impulse-source-preflight/46115128898-attempt-1/preflight.json — durable copy of the successful ALFRED preflight manifest.
- research/h8_ci_credit_impulse_btc_downside.py — point-in-time vintage retrieval, exact BTC archive-manifest matching, event construction, rolling OLS, bootstrap and evidence persistence.
- research/test_h8_ci_credit_impulse_btc_downside.py — deterministic source, event, maturity, decision and bootstrap tests.
- .github/workflows/h8-ci-credit-impulse-btc-downside.yml — immutable-commit workflow with the atomic [QFR-ADMIT] research: gate and durable evidence persistence.
- research/test_workflow_admission.py — regression coverage for the new empirical workflow.
- research/HYPOTHESIS-REGISTRY.md — H.8 moved from IDEA to FEASIBILITY_CHECKED after source acceptance.
- README.md — current active-workstream handoff and canonical preflight link.

## Source and model specification

- Predictor: 100 * ln(TOTCI latest available in the Sunday ALFRED vintage / fourth prior weekly observation in the same vintage).
- Vintage gate: no future observation; latest observation must be Wednesday and 3–14 days old; four weekly gaps must each be 5–9 days. A failed vintage is excluded, not forward-filled.
- Baseline: prior 5/20-session momentum, prior 5/20-session downside semivariance and prior 20-session total realized variance.
- Augmented model: baseline plus exactly one four-observation TOTCI log-change predictor.
- Target: log1p of mean squared negative BTC log return over the next five UTC daily sessions, multiplied by 10,000.
- Events: every Sunday UTC; target Monday through Friday; target windows do not overlap.
- Rolling training: latest 104 fully matured prior weekly events.
- Validation: 2019–2021. Test: 2022 onward.
- Minimum sample: 100 validation and 100 test forecasts.
- Inference: 2,000 paired circular moving-block bootstrap replications, block size four weekly events, seed 20261128.
- Decision: PROMISING only if both validation and test RMSE improve by at least 1.0% and the paired test-loss 95% interval is entirely above zero; REJECTED only if neither period improves and the interval is entirely below zero; otherwise INCONCLUSIVE.

The previous accepted BTC run retained the archive manifest but not raw daily rows. The model implementation therefore re-materializes only the same 136 official Binance Vision archives and requires every file and checksum field to match the prior manifest hash 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe. No alternate source, additional date or current-vintage price reconstruction is permitted.

## Verification at implementation commit

- ALFRED source preflight run #46115128898: PASS.
- Repository admission guard run #46115128864: PASS.
- The model implementation and regression suite are committed; the subsequent CI run must pass before the atomic empirical admission commit.
- No empirical model fit or backtest has yet been performed by this session.
- The daily KPI is already met by run #46085887442; the H.8 model run is an additional experiment.

## Next

1. Verify the implementation commit's admission-guard CI.
2. If all deterministic tests pass, create one [QFR-ADMIT] research: commit that advances the README handoff to the admitted run.
3. Execute exactly one empirical workflow, preserve its report/manifest/forecast rows, then independently reconstruct the result in cycle 4.
4. Close at the frozen deadline if evidence or execution cannot be validated; never infer a performance NO-GO from a source or implementation failure.
