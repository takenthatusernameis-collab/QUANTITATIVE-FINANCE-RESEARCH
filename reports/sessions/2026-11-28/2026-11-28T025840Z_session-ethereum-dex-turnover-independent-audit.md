# Session report — Ethereum DEX turnover / ETH RV independent audit and closure

- **Session timestamp:** 2026-11-28T02:58:40Z
- **Objective:** Reconcile the live README, preregistration, hypothesis registry, source-preflight evidence, admitted backtest and persisted forecasts; complete Cycle 4 independently; close the workstream without altering its frozen model or decision rules.
- **Main branch at inspection:** `a2bb38e52eca820463c9c7a3e587b202287af0dd`
- **Workstream:** `QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01`

## 1. Work completed

1. Read the live README, preregistration, hypothesis registry, source-preflight manifest, backtest manifest and all 1,392 persisted forecast rows.
2. Inspected the exact admitted workflow commit, the full backtest job steps, admission-guard CI, open PRs/issues, queued/in-progress Actions and recursive main tree.
3. Independently reconstructed timing, feature windows, training maturity, forecast target bounds, non-overlap, squared errors, split metrics and the paired-loss moving-block bootstrap.
4. Reconciled the stale README, preregistration and registry status from IMPLEMENTING to CLOSED — INCONCLUSIVE.
5. Added a distinct, not-yet-admitted ETH validator-queue asymmetry research idea. Its source is documented and appears feasible, but it has not yet been fetched by the authorized runner; it is not an active workstream or a backtest.

## 2. Verified source and execution evidence

- Cycle 1 source preflight [run 46097000508](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46097000508) passed on source commit `aa59537e1a7938bddd8b4fd0b64bad4c73f271be`. The admitted workflow pins the exact artifact ID `15243896011`, ZIP SHA-256 `5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49`, and extracted manifest SHA-256 `1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6`.
- DeFiLlama supplied 2,128 daily DEX-volume and 2,128 daily TVL observations each, 2021-01-01 through 2026-10-29. Frozen-window canonical hashes: DEX `8fdf8625a388b619d4426791f14a78bbb6bb3820ee535aa60cbd82a67c8e0696`; TVL `0d21055246d26652c684847a5c85ff1abbe7ab4e3010a1e6e8ca8f2e77cac7fe`.
- Binance ETHUSDT Spot metadata was accepted. Seventy monthly and seven daily cross-check archives passed SHA-256 verification. The hourly sample contained 51,106 of 51,120 expected bars; 14 missing bars (0.0274%), maximum four consecutive. Daily archives reproduced all seven gap dates and repaired zero bars. Canonical close SHA-256: `64b2b592fe094ed576ec8582fe788d146293afabc2274bbb83650d0cd34c5a6c`.
- The admitted immutable source commit was `024f91ba2e8ec039bc53d9ccd1b3540c3fb4d350`. Backtest [run 46098199964](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46098199964) completed successfully. Every job step succeeded, including deterministic source/model/admission tests, exact accepted-preflight-artifact verification, frozen-source refetch, the single preregistered walk-forward forecast and evidence persistence. Admission guard [run 46098199972](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46098199972) also passed.

## 3. Independent Cycle 4 audit

The audit re-parsed `reports/generated/ethereum-dex-turnover-eth-rv/46098199964-attempt-1/forecast_rows.csv` rather than relying on the report's rounded figures.

| Check | Independent result |
|---|---|
| Persisted forecasts | 1,392: 723 validation, 669 test |
| Duplicate forecast dates | 0 |
| Signal timestamp | Every signal equals 00:00 UTC on its row date |
| Target bounds | Every target starts at signal and ends exactly 24 hours later |
| Target overlap | None across the complete ordered forecast set |
| Predictor dates | Every seven-day DEX/TVL feature window is exactly t−8 through t−2 |
| Training window | Every forecast uses 252 events; every training target ends strictly before the signal |
| Stored squared errors | Recomputed from target and predictions; all match within floating-point tolerance |
| Validation exclusions | Exactly eight missing origins, 2023-03-24 through 2023-03-31, consistent with the 2023-03-24 13:00 UTC hourly archive gap contaminating the 168-hour trailing feature |
| Test exclusions | No calendar-date gaps in the 2025-01-01 through 2026-10-31 test forecast rows |

Independently recomputed metrics:

| Split | Baseline RMSE | Augmented RMSE | RMSE improvement | Baseline MAE | Augmented MAE |
|---|---:|---:|---:|---:|---:|
| Validation | 0.887682530 | 0.891535848 | −0.434087% | 0.687199397 | 0.692695988 |
| Test | 0.879506070 | 0.880798316 | −0.146929% | 0.671567923 | 0.674836322 |

The paired test-loss mean was independently reconstructed as `−0.0022747450467157683`. I decoded the 669 persisted paired loss differences and reran the exact NumPy `default_rng(20261128)` circular moving-block procedure (2,000 replications, block size seven, same wraparound construction and quantile method). It reproduced the manifest exactly:

- Mean baseline-minus-augmented squared loss: `−0.0022747450467157683`
- 95% interval: `[−0.011202103506137949, +0.006070043616085962]`
- Bootstrap fraction positive: `0.305`

The interval crosses zero. Both chronological splits have worse augmented RMSE and MAE, but the frozen REJECTED rule additionally requires the upper confidence bound to be strictly below zero. That requirement is not met. The correct disposition is **INCONCLUSIVE**, not REJECTED and not PROMISING.

### Source-vintage reconciliation

The refetched raw DeFiLlama TVL response SHA-256 differs from its preflight response SHA-256. The canonical SHA-256 over the frozen sample window is unchanged, and the implementation explicitly compares that canonical hash plus the frozen coverage fields before accepting the source. Thus the raw response changed, but no value in the accepted frozen window changed. This does not solve the broader current-vintage/revision limitation: the two-day lag is not proof of historical point-in-time publication.

## 4. Research disposition and boundaries

- Cycle 1 source feasibility: PASS.
- Cycle 2 implementation and deterministic regression suite: PASS.
- Cycle 3 immutable admitted empirical execution and evidence persistence: PASS.
- Cycle 4 independent audit: PASS.
- Final hypothesis disposition: **CLOSED — INCONCLUSIVE**.
- The original MEDIUM four-cycle cap and deadlines were not extended or reset.
- The daily real-data backtest KPI for 2026-11-28 had already been met by MEXC funding dispersion / BTC realized variance [run 46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This DEX backtest is additional research output; the source-only preflight was not counted as a backtest.
- No P&L, transaction costs, tradability, causal effect, strategy edge or live-trading evidence was evaluated. No strategy promotion or same-ID tuning is authorized.

## 5. Repository and automation state

- No queued or in-progress Actions runs at final inspection.
- One open pull request remains: draft control PR [#15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/15); it was not merged or altered.
- No open issues were found.
- Recursive main tree: 428 entries, not truncated. There is no `tasks/` directory in the current tree; the README and research registry are the current canonical handoff. No obsolete queue file was recreated.
- The original README path and name remain unchanged.

## 6. Next candidate — not admitted

A materially different candidate is **Ethereum validator entry/exit queue asymmetry → ETH downside risk**. CryptoKeyhole documents a free, keyless daily `eth.ValidatorQueueWait` chart with entry/exit wait components and history from December 2020. Its methodology uses its own execution and consensus nodes; before Pectra the entry queue is reconstructed from validators awaiting activation at 32 ETH each, while after Pectra it uses deposits in the consensus-state queue and ETH-denominated churn rules. Free chart data is CC BY 4.0; first-published vintages are an API & Team feature, so a no-key study would be current-vintage only.

Candidate feature: `log1p(exit_wait_days) - log1p(entry_wait_days)`, strictly lagged, to represent queue asymmetry; candidate target: next-five-UTC-day ETH downside semivariance. This is not frozen or admitted. The Pectra methodology break and lack of first-published vintages are material limitations.

Next action: run a bounded, read-only authorized-runner source preflight for the exact API catalog/series schema, entry/exit component IDs, daily coverage/finality/gaps and the checksummed ETHUSDT daily archive. Only if the source passes and the six-day-spaced walk-forward schedule can meet the preregistered minimum sample sizes should a new hypothesis be frozen. Do not begin model implementation or backtesting under this idea before that feasibility gate.

## 7. Effort and status

- Research/evidence audit: approximately 65%.
- Repository reconciliation and durable handoff: approximately 25%.
- Next-hypothesis source/literature screen: approximately 10%.
- Daily research KPI: **SATISFIED**.
- New empirical result this session: none; the completed DEX run was independently audited, not rerun.
