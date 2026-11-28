# ETH validator queue asymmetry — source-only preflight orchestration

## Decision

The Ethereum validator queue asymmetry candidate remains **IDEA / NOT ADMITTED**. This session implemented the bounded source-only preflight execution path. It did not preregister the model, fit a model, inspect empirical performance or run a backtest.

## Work completed

- Reconciled the current README, hypothesis registry, recent mainline commits, workflow history, open pull requests and the candidate's existing source-preflight implementation.
- Confirmed that `research/eth_validator_queue_source_preflight.py` already contains the read-only CryptoKeyhole and Binance source checks, schedule-feasibility logic, partial-failure manifest generation and explicit `model_fit_performed=false` / `backtest_run=false` outputs.
- Added `.github/workflows/eth-validator-queue-source-preflight.yml` with:
  - a narrow `push` path filter and `workflow_dispatch`;
  - immutable triggering-commit checkout and pinned checkout/Python setup actions;
  - deterministic compile and source-preflight regression tests before network retrieval;
  - public-source retrieval only, with no model fitting or backtest;
  - a 45-minute bounded job and non-cancelling concurrency group;
  - a separate persistence step that commits the generated report and manifest to `main`, including failure/partial-evidence manifests when available.
- Registered the source-only workflow as a non-research workflow in `research/test_workflow_admission.py`, added regression checks for its narrow scope, immutable checkout, evidence persistence and shell syntax, and wired the source-preflight module/tests into `.github/workflows/workflow-admission-tests.yml`.

## Mainline changes

- `4042d6ddcea5b44aec374e95335c504c15e91a83` — register the source-only workflow and add guard tests.
- `ab4b69c8d872e301bc3fcfb4bbc976d4f9984407` — compile and run the source-preflight tests in admission CI.
- `0fbfddb300af0a1534ce73c1a406eaac903d1f76` — add the bounded source-only workflow; current main head at final inspection.

## Verification and outstanding status

- GitHub accepted the new workflow and created source-preflight run [46103027218](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027218).
- The final admission-guard run is [46103027222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027222).
- Both runs were still **QUEUED** at the final status check. Therefore the source preflight, its 11 deterministic tests, live API/archive checks, and persistence step are **not yet verified**.
- Two intermediate CI attempts ([46102964086](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46102964086) and [46102973929](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46102973929)) failed because the guard tests were committed before the workflow file they intentionally inspect existed. Their logs show `FileNotFoundError` for the not-yet-created workflow file; they do not establish a source or model failure. The workflow file was subsequently committed in `0fbfddb`, and the final admission run is queued to test the complete state.
- The prior successful admission run [46101572887](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46101572887) applies to an earlier commit, not the new workflow.
- Draft control PR [#15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/15) remains open and unmerged as required.

## Research interpretation and limitations

No new empirical knowledge or backtest result was produced in this session. The 2026-11-28 daily real-data backtest minimum had already been met by MEXC funding dispersion / BTC realized variance run [46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442).

The candidate remains subject to important limitations already identified in the README:

- The free CryptoKeyhole daily series is current-vintage; first-published historical vintages require a separate API & Team entitlement. A two-day lag does not establish historical point-in-time availability or remove revision risk.
- Pectra changed the entry-queue definition/churn calculation on 2025-05-07; pre- and post-Pectra regimes must remain separately identified.
- Exit-queue components include voluntary exits, slashings and execution-layer exit requests; queue waits are not a direct measure of ETH sales.
- The preflight tests source availability, provenance, coverage, missingness and forecast-schedule feasibility only. A PASS would not itself admit the hypothesis or authorize a model fit.

## Next action

Inspect runs [46103027218](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027218) and [46103027222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027222).

- If source preflight passes, decide whether the current-vintage limitation is acceptable for a clearly labelled exploratory forecast. If it is, freeze a new hypothesis identity, difficulty-adjusted timebox, regime treatment, target, acceptance criteria and expiry rule before model implementation.
- If source preflight fails, classify the exact failure and test a materially different, independently verifiable data architecture or select another hypothesis. Do not repeat an unchanged provider route.
- Do not interpret a source-feasibility failure as a strategy-performance NO-GO.
