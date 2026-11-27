# Wake-up 7 — autonomous dispatch and initial-claims research completion

**Session timestamp:** 2026-11-27T205900Z  
**Repository:** `takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH`  
**Main at close:** `9a2ecb4b940a9b0529d81cb345ae57199cff87eb`

## Objective and outcome

Resolve the admitted U.S. initial-claims/BTC downside research bottleneck without requiring a human to launch a workflow manually; complete the one preregistered real-data run; independently audit its persisted evidence; and make the autonomous dispatch route reusable and documented.

**Outcome:** autonomous ChatGPT-to-GitHub Actions dispatch is now operational and end-to-end verified through a dedicated draft control PR. The admitted hypothesis completed successfully and was closed **INCONCLUSIVE** under its frozen criteria. No same-ID rerun or retuning is authorized.

## Autonomous dispatch implementation

- Created [draft control PR #15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/15) as the dedicated PR-comment command surface. Keep it open and in draft; never merge it. The prior control PR #2 is superseded.
- Added `.github/workflows/chatgpt-control-pr-dispatch.yml` on `main`. It accepts only `issue_comment: created`, PR #15, actor `takenthatusernameis-collab`, and exact full-body matches for two fixed commands.
- Added `.github/workflows/dispatch-bridge-probe.yml`, a no-permission, no-checkout harmless target.
- Added provenance inputs to the initial-claims target workflow: `source_comment_id`, `source_control_pr`, and `source_actor`.
- The bridge has only `actions: write` and `pull-requests: write`; it dispatches fixed workflow filenames on `main`, never checks out or executes PR-head content, never uses `pull_request_target`, and never treats comment text as shell input.
- It serializes comments per control PR and adds a `github-actions[bot]` rocket reaction after a successful dispatch. Redelivery of the same comment is a no-op.
- Added regression coverage for exact authorization, least privilege, absence of PR-head execution, provenance and Bash syntax. The non-research bridge/probe workflows are explicitly excluded from the research admission-gate and immutable-checkout classifiers.

### Dispatch proof and repair history

1. First harmless probe comment `7227919604`: target probe [#46066554372](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066554372) succeeded, but bridge [#46066546997](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066546997) failed after dispatch because the PR-comment reaction endpoint returned HTTP 403. This was a permission issue after the target dispatch, not a dispatch failure.
2. Diagnosed and fixed the permission boundary by adding `pull-requests: write` and capturing the reaction API's HTTP response and error body.
3. Second harmless probe comment `7227938046`: bridge [#46066680693](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066680693) and target [#46066689151](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066689151) both succeeded; the idempotency reaction persisted.
4. Actual research command comment `7227943059`: bridge [#46066716510](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066716510) succeeded and dispatched target [#46066725930](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46066725930), which succeeded.

Target run provenance log confirmed:
- event: `workflow_dispatch`;
- actor: `github-actions[bot]`;
- source control PR: `15`;
- source actor: `takenthatusernameis-collab`;
- source comment ID: `7227943059`;
- ref: `refs/heads/main`;
- exact source SHA: `a1a0303e760ad89dd76529740199dff6aa720d1c`.

No human UI dispatch was used. The `workflow_dispatch` event is an internal event emitted by the bridge. Direct manual dispatch remains break-glass only.

## Research output

Hypothesis: `QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01`.

- Cycle 1 source feasibility: PASS, [preflight #46028463525](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46028463525).
- Cycle 2: implementation, deterministic tests, one real-data backtest, persistence and independent arithmetic audit completed.
- FRED ICSA: 484 weekly observations, 2017-08-19 through 2026-11-21; response SHA-256 `2bcf8c35377a4280459bc015dc53cba21cbcd992a916a7fd0d29bd5d09aed0bb`.
- Binance BTCUSDT Spot: 3,388 daily candles, 2017-08-17 through 2026-11-25, from 136 archives; all 136 archive checksums verified; archive-manifest SHA-256 `978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe`.
- Event construction: 478 accepted weekly events; five-session target windows did not overlap; seven-day observation-to-signal lag; 104-event rolling training window.

| Metric | Validation 2019–2021 | Test 2022 onward |
|---|---:|---:|
| Forecasts | 119 | 255 |
| Baseline RMSE | 1.0968906043 | 0.8542368540 |
| Augmented RMSE | 1.4529442396 | 0.8528460827 |
| RMSE improvement | -32.4603% | +0.1628% |

Paired test-loss moving-block bootstrap: 2,000 replications, block size 4, seed 20261127; mean baseline-minus-augmented squared loss 0.00237416198; 95% interval [-0.02147463, +0.02572600], which crosses zero.

**Final disposition: INCONCLUSIVE.** Validation performance deteriorates materially, test improvement is negligible, and paired-loss uncertainty crosses zero. The frozen PROMISING/REJECTED criteria are not met. This is a forecast-only screen, not a causal finding, executable strategy, trading P&L or economic-value test.

### Independent evidence audit

- Parsed all 374 persisted forecast rows; 119 validation and 255 test observations, with no malformed rows.
- Independently recomputed validation/test RMSE and MAE; results match the manifest to floating-point precision.
- Independently recomputed the mean paired test-loss difference; it matches the manifest within 3.1e-18.
- Confirmed the manifest records all 136 archive checksums as verified.
- No raw ICSA observations or raw BTC price rows were committed; only provenance, manifest, derived forecast rows and report were persisted.

Evidence:
- [Research report](2026-11-27T205411Z_session-initial-claims-btc-downside-46066725930.md)
- [Manifest](../../generated/initial-claims-btc-downside/46066725930-attempt-1/manifest.json)
- [Forecast rows](../../generated/initial-claims-btc-downside/46066725930-attempt-1/forecast_rows.csv)
- [Evidence persistence commit 018ec02](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/018ec02cca7ba00fefa66788a99262b73af00558)

## CI and repository state

- Final [research workflow admission/dispatch CI #46067137673](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46067137673): success; 56 admission/dispatch regression tests passed, followed by all configured research regression suites.
- [BTC mining-difficulty unadmitted-draft closure CI #46067137633](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46067137633): success.
- Intermediate CI failures were caused by the new infrastructure workflows being misclassified as research workflows and then by exact wording assertions in the new documentation tests. The classifier, permissions assertion and wording were corrected; the final CI above passes.
- No queued, in-progress or waiting Actions runs remained at close.
- Control PR #15 remains open and in draft.
- Main close SHA: `9a2ecb4b940a9b0529d81cb345ae57199cff87eb`.

## Timebox, KPI and next action

The LOW timebox remained unchanged: start `2026-11-27T15:40:06Z`; implementation deadline `2026-11-28T15:40:06Z`; final conclusion deadline `2026-11-29T15:40:06Z`. The conclusion was completed before both deadlines. No extension or reset occurred.

The 2026-11-27 daily real-data backtest minimum had already been met by distinct ETF-relative-flow and BTC blockspace-fee-rate screens. This initial-claims backtest was additional production.

Do not reopen or retune this hypothesis ID. Next research action: identify a materially distinct predictive mechanism, establish free-source feasibility and preregister a new difficulty-adjusted timebox before implementation. Keep the current dispatch bridge as the default agent activation route; add future commands only through exact allowlist updates and regression tests.

Approximate session effort: 70% automation/repository operations and 30% empirical result verification/research.

No live trading, capital deployment, paid data acquisition or strategy promotion occurred.
