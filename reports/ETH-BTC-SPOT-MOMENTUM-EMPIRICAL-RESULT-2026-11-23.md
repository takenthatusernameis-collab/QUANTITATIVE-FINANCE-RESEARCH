# ETH/BTC Spot Relative-Momentum Rotation — Empirical Conclusion

**Date:** 2026-11-23  
**Experiment:** `ETH-BTC-SPOT-MOMENTUM`  
**Terminal decision:** **NO-GO** (research-only; frozen specification)  
**Substantive cycle:** 1 of 4 maximum; closed early after a valid empirical conclusion.

## Run and reproducibility

- **Authorized command:** `/qfr-run-eth-btc-spot-momentum` on control PR #2.
- **Event/actor:** `issue_comment` on open PR #2; actor `takenthatusernameis-collab`. Authorization and the exact-command gate passed.
- **GitHub Actions run:** [45190869167](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45190869167) — completed successfully; research job and report/artifact upload succeeded.
- **Run commit:** `8fd3e014be38ca679ead36bfe4b1d4063cc5ae0f` (default branch).
- **Artifact:** [14832209111](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45190869167/artifacts/14832209111), `eth-btc-spot-momentum-63`, 6,620,925 bytes, SHA-256 `a31b520c65705520269062ae7f7cd5f7619aa5aa6a38e1e6b006c6cda2659547`. Contains generated reports, metrics, bootstrap, returns/equity curves, signals, recovery periods, plots and data manifests; no raw hourly market-data CSVs were uploaded. GitHub artifact retention expires 2026-12-23 15:18 UTC.
- **Implementation/CI:** [implementation handoff](ETH-BTC-SPOT-MOMENTUM-IMPLEMENTATION-2026-11-23.md); [CI run 45190529404](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45190529404) passed 240 deterministic tests.

## Accepted data and OOS sample

- Binance Spot only: `ETHUSDT` and `BTCUSDT`, hourly bars, requested history 2020-01-01 through 2026-10-31.
- 82/82 monthly archives per symbol were checksum-verified; no missing archive months or parse errors.
- Each symbol has 59,873 observed hourly rows versus 59,904 expected. All 31 missing bars per symbol were confirmed no-trade gaps by the accepted aggregate-trade archive reconciliation; no candles were synthesized or forward-filled.
- Data acceptance: **accepted**, no blockers; observed UTC elapsed-time policy `observed-utc-elapsed-v2`.
- Pooled OOS: 2022-01-01 00:00 UTC through 2026-10-31 23:00 UTC; 42,359 observed opens, representing 42,358 positive-duration return intervals (the first OOS point has zero elapsed duration).

### Source hashes

| Source file | SHA-256 |
|---|---|
| `spot_ETHUSDT_1h.csv` | `10e9e037eef8c34ec2bd98964cc1b8be52cf5c741ca84e7f2925948fea1ac79b` |
| `spot_ETHUSDT_archive_manifest.json` | `2ebe80e84bc2c58accbacb8d2082107fafb816f8bceb5b2b10c78880ab70770c` |
| `spot_ETHUSDT_gap_reconciliation.json` | `79c5f2730da9b1e018b2ffc2c4bbfb9700e95b6603d3d0a5aaa0f2bf0490931e` |
| `spot_BTCUSDT_1h.csv` | `83cd8937026dd8953e8fac244cbbd0be20aeaa32fa94739b1b6cc3d88f2dd0fd` |
| `spot_BTCUSDT_archive_manifest.json` | `55ec9ecbc55c8531de2bd0166705cefcbf501507afe806aebd9184e42a13acbc` |
| `spot_BTCUSDT_gap_reconciliation.json` | `85391f2ba1b53e3471dc738f01db676b79fa7fcafcb29bc4142cee2fb7b63c98` |

## Frozen strategy

At each daily UTC close, calculate `ETHUSDT/BTCUSDT` and its 200-day SMA (current completed close plus prior 199 valid daily closes). Hold 100% ETH when the ratio is above the SMA, otherwise 100% BTC. Execute at the first observed hourly open at or after the next UTC midnight. No leverage, shorts, funding, additional filters, parameter search or venue mixing.

Baseline modeled costs: **10 bps per one-way leg**. Sensitivities: 5, 10, 15, 20, 25 and 50 bps per leg. These are scenarios, not historical fill-cost estimates.

## Baseline performance (10 bps/leg)

| Variant | Net total return | Net CAGR | Sharpe | Max drawdown | Turnover/year |
|---|---:|---:|---:|---:|---:|
| 200d relative momentum | +6.66% | +1.34% | 0.024 | -77.98% | 22.35 |
| BTC buy-and-hold | +67.46% | +11.26% | 0.213 | -67.38% | 0.41 |
| ETH buy-and-hold | -38.79% | -9.66% | -0.152 | -76.67% | 0.41 |
| 50/50 ETH/BTC buy-and-hold | +14.33% | +2.81% | 0.051 | -69.63% | 0.41 |
| 50/50 monthly rebalanced | +10.36% | +2.06% | 0.036 | -70.06% | 0.91 |

The strategy spent 32.24% of elapsed time in ETH and 67.76% in BTC, with 53 rotations.

## Cost sensitivity

| Cost (bps/leg) | Net total return | Net CAGR | Sharpe | Max drawdown |
|---:|---:|---:|---:|---:|
| 5 | +12.58% | +2.48% | 0.043 | -77.54% |
| 10 | +6.66% | +1.34% | 0.024 | -77.98% |
| 15 | +1.04% | +0.22% | 0.004 | -78.42% |
| 20 | -4.28% | -0.90% | -0.016 | -78.85% |
| 25 | -9.33% | -2.01% | -0.036 | -79.27% |
| 50 | -30.91% | -7.37% | -0.136 | -81.25% |

The 15-bps case remains barely positive in total return, but it still fails the frozen BTC-comparison criteria; at 20 bps it loses money.

## Paired moving-block bootstrap — excess CAGR versus BTC

1,000 paired replications per block length, 95% percentile CI, identical contiguous observed-time blocks and elapsed-duration-weighted start probabilities.

| Block length | 95% lower bound | 95% upper bound |
|---:|---:|---:|
| 3 days | -27.32% | +9.16% |
| 7 days | -28.04% | +11.24% |
| 14 days | -28.20% | +11.26% |

All lower confidence bounds are far below zero.

## Decision against frozen GO criteria

**All six promotion criteria failed:**

1. Baseline net CAGR did not exceed BTC.
2. Baseline Sharpe did not exceed BTC.
3. Strategy maximum drawdown was worse than BTC.
4. The 95% bootstrap lower bound was not positive for any of the 3/7/14-day blocks.
5. The 15-bps stress case did not preserve the promotion decision.
6. The 20-bps stress case was unprofitable and did not preserve the decision.

**Conclusion: NO-GO.** The frozen 200-day relative-momentum rotation is not competitive with BTC buy-and-hold over this pooled OOS sample under the preregistered criteria. Do not tune, add filters or reinterpret this OOS sample to rescue the same experiment. Any materially revised strategy is a new, separately preregistered hypothesis and requires an independent/later holdout.

## Independent calculation check

The baseline 10-bps total return, elapsed-time CAGR, continuous-time Sharpe, maximum drawdown and elapsed interval count were independently recalculated from the artifact's `spot_momentum_oos_returns.csv` using the repository's `event_time_metrics` formulas. They match the published `spot_momentum_metrics.csv` values to floating-point precision. This confirms consistency between the report and the generated return series; it is not a substitute for independent raw-market-data reproduction.

## Operational note and limitations

The issue-comment run used read-only cache mode and restored the available warm-cache key (164,742 bytes). Its post-job archive-cache write was denied because the low-trust event token has no writable cache scope. This did not invalidate the study: the archive manifests show the complete requested monthly history and checksum verification. It means this run did not persist a new archive cache.

Modeled costs are scenarios; actual execution slippage, liquidity, order-book impact, partial fills, taxes and account-specific fees are not represented. This is a research-only conclusion. No live trading or capital deployment is authorized.
