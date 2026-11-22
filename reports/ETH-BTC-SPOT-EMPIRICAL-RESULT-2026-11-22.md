# ETH/BTC Spot-Only Empirical Result — 2026-11-22

## Decision

**NO-GO for the two tested Spot mean-reversion variants.** The fixed 1:1 and rolling-hedge implementations lose money across the full pooled out-of-sample (OOS) period at baseline modeled costs, and their 95% block-bootstrap CAGR/Sharpe intervals remain entirely below zero. This is a conclusion about these tested specifications—not a rejection of every possible ETH/BTC relative-value strategy.

The original Binance USDⓈ-M/perpetual study remains **INCONCLUSIVE** until funding settlement population, event semantics and contract-incarnation coverage are accepted. Spot results must not be treated as perpetual evidence.

## Run and artifact

- GitHub Actions run: [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437)
- Artifact: [eth-btc-research-24](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437/artifacts/14746369761)
- Artifact ID: `14746369761`; 2,202,803 bytes; SHA-256: `dba9bb76fd332429673b3c54a6f9e5fd306e3487de0380a35d856226abda4f69`
- Executed on default-branch commit `66b3594` (pre-pooled-summary code). The pooled OOS metrics and bootstrap inference below were independently recomputed from the uploaded `spot_1h_oos_returns.csv` and `spot_1d_oos_returns.csv`; no raw market data was added to Git.
- Scope: Binance Spot ETHUSDT/BTCUSDT, 2020-01-01 through 2026-10-31. Twenty rolling walk-forward OOS folds, 730-day training windows, 90-day test windows; OOS begins 2021-12-31 and runs through 2026-10-31. Total OOS elapsed time: 1,765.17 days for hourly event-time metrics; 1,766 daily returns for daily aggregation.
- Variants: `fixed_1x1` and `rolling_hedge`. Hourly test: 42,383 rows per variant, 42,363 positive-duration observations. Daily test: 1,766 rows per variant. Fold boundaries are kept separate and no inter-fold returns are inserted.

## Data-quality result

| Item | ETHUSDT | BTCUSDT |
|---|---:|---:|
| Monthly kline archives | 82/82 checksum-verified | 82/82 |
| Observed hourly bars | 59,873/59,904 | 59,873/59,904 |
| Missing synchronized hourly bars | 31 | 31 |
| Gap classification | 31/31 confirmed no-trade | 31/31 |
| Daily aggregate-trade gap archives | 15/15 parsed and checksum-verified | 15/15 |
| Gap-hour aggregate trades | 0 in every gap | 0 in every gap |
| Archive positive controls | 15/15 pass | 15/15 pass |
| Aggregate-trade ID/timestamp integrity | no duplicates or out-of-order records | no duplicates or out-of-order records |

The daily archive evidence is primary: the corresponding missing hours contain no aggregate trades, and each archive has a known active-hour positive control. The REST gap queries returned HTTP 200/empty responses, but their active-hour positive controls did not pass; the classification is therefore supported by the checksum-verified daily archives and archive controls, not by REST controls. Missing candles remain missing. The production event-time policy uses observed UTC elapsed time and does not forward-fill or synthesize bars.

## Frozen strategy/cost assumptions

- Mean-reversion entry `z=2`, exit `z=0.5`, stop `z=4`, maximum hold 7 calendar days.
- Hourly lookback 720 bars; daily lookback 30 bars.
- Fee assumption 10 bps per leg per side, slippage 2 bps, spread 1 bp.
- Historical Spot borrow charge assumed **0 bps/day**. Borrow availability/rates are not verified; the short-Spot results are optimistic and theoretical to that extent.
- No funding is applied to Spot.
- The 1.5x and 2.0x cost cases multiply modeled trading costs only; they are point estimates. Bootstrap confidence intervals are for baseline 1.0x costs.

## Pooled OOS performance

Metrics are compounded across sequential OOS folds, with the hourly metrics using observed elapsed-time annualization. All values are net of modeled baseline costs.

### Hourly strategy (event-time)

| Variant | Cost | Total return | CAGR | Volatility | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|---:|
| fixed_1x1 | 1.0x | -54.89% | -15.19% | 12.37% | -1.33 | -55.34% |
| fixed_1x1 | 1.5x | -64.23% | -19.16% | 12.44% | -1.71 | -64.49% |
| fixed_1x1 | 2.0x | -71.63% | -22.95% | 12.53% | -2.08 | -71.81% |
| rolling_hedge | 1.0x | -57.53% | -16.24% | 13.64% | -1.30 | -61.14% |
| rolling_hedge | 1.5x | -66.67% | -20.34% | 13.70% | -1.66 | -68.93% |
| rolling_hedge | 2.0x | -73.86% | -24.24% | 13.78% | -2.02 | -75.20% |

### Daily strategy (1d)

| Variant | Cost | Total return | CAGR | Volatility | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|---:|
| fixed_1x1 | 1.0x | -20.79% | -4.71% | 11.31% | -0.37 | -27.76% |
| fixed_1x1 | 1.5x | -29.19% | -6.89% | 11.35% | -0.57 | -30.12% |
| fixed_1x1 | 2.0x | -36.70% | -9.02% | 11.40% | -0.77 | -36.70% |
| rolling_hedge | 1.0x | -36.59% | -8.99% | 9.18% | -0.98 | -42.48% |
| rolling_hedge | 1.5x | -42.89% | -10.94% | 9.20% | -1.21 | -46.96% |
| rolling_hedge | 2.0x | -48.57% | -12.85% | 9.23% | -1.44 | -51.10% |

Fold consistency is poor: hourly fixed_1x1 had 3/20 positive-CAGR folds and rolling_hedge 5/20; daily both had 8/20 positive-CAGR folds. At baseline hourly costs, the variants generated 178 and 177 trades, with mean holds of 4.07 and 3.13 days; daily generated 86 and 76 trades, with mean holds of 5.66 and 4.87 days.

## Hourly uncertainty: 1.0x cost

Fold-stratified moving-block bootstrap, sampled by calendar-time duration, **1,000 replications per block length**, 95% percentile intervals. Blocks do not cross OOS fold boundaries. The optimized post-processing sampler is distributionally equivalent to the repository's weighted `rng.choice` start selection; 20 seeded draws were cross-checked.

### Primary 7-day block

| Variant | CAGR 95% CI | Sharpe 95% CI | Total return 95% CI | Max DD 95% CI |
|---|---|---|---|---|
| fixed_1x1 | -23.73% to -5.48% | -2.107 to -0.466 | -73.39% to -24.07% | -75.36% to -33.32% |
| rolling_hedge | -26.20% to -7.66% | -2.052 to -0.616 | -77.35% to -32.27% | -79.59% to -40.25% |

### Block-length sensitivity — CAGR 95% CI

| Variant | 3-day | 7-day | 14-day |
|---|---|---|---|
| fixed_1x1 | -24.27% to -6.46% | -23.73% to -5.48% | -24.73% to -7.41% |
| rolling_hedge | -27.01% to -6.38% | -26.20% to -7.66% | -24.69% to -8.70% |

Every block-length interval remains below zero. This is not a marginal, cost-only failure.

## Fold-compounded benchmark comparison

Benchmark total returns are compounded from the per-fold summaries. Daily benchmark fold returns are reconstructed from their reported CAGR and exclusive test-window dates. Sharpe/volatility for the benchmark chain is not reconstructed.

| Benchmark | 1h total return | 1h CAGR | 1d total return | 1d CAGR |
|---|---:|---:|---:|---:|
| BTC buy-and-hold | +58.41% | +9.99% | +47.58% | +8.38% |
| ETH buy-and-hold | -40.85% | -10.29% | -39.25% | -9.79% |
| 50/50 ETH/BTC buy-and-hold | +6.64% | +1.34% | +4.14% | +0.84% |
| 50/50 ETH/BTC rebalanced | -2.04% | -0.42% | +1.25% | +0.26% |
| Long ETH / short BTC buy-and-hold | -29.84% | -7.07% | -24.15% | -5.56% |

The strategies underperformed the 50/50 benchmarks and no-trade (0%) at both frequencies. Hourly strategies also underperformed ETH buy-and-hold despite ETH itself declining over the OOS period. Both daily variants beat ETH buy-and-hold (they lost less), but still underperformed the 50/50 and BTC benchmarks; daily rolling_hedge also underperformed the long-ETH/short-BTC buy-and-hold benchmark.

## Interpretation / action

- **Reject promotion of both tested Spot variants.** Their pooled OOS CAGRs and Sharpe ratios are negative; baseline-cost bootstrap CIs remain negative; higher-cost scenarios worsen the results.
- Do not tune thresholds against these holdouts and then relabel the same folds as out-of-sample. Any changed model is a new experiment with fresh, later holdout data and preregistered parameters.
- Spot borrow costs/availability are unverified and modeled as zero; real borrow costs would not rescue the tested results and would make short-Spot results worse.
- This is a Spot-specific result. Perpetual funding acceptance remains provisional and the original Binance USDⓈ-M study remains inconclusive.
- No live trading, capital deployment or strategy promotion occurred.

## Infrastructure notes

The empirical run was pinned to the older SHA and used Node-20-era action versions, so its log contains deprecation warnings; the default branch has since upgraded those actions and CI verified the new versions. The archive-cache save was denied: this `issue_comment` trigger receives the secure default read-only cache mode. The backtest completed, but its downloaded Binance archives were not persisted to the shared cache, so the separate USDⓈ-M run may redownload. Do **not** bypass the read-only cache restriction casually; the safer process improvement is a dedicated trusted scheduled cache-warm workflow using default-branch code and official, checksum-verified data, rather than enabling cache writes for low-trust `issue_comment` triggers.

## Next independent workstream

The USDⓈ-M-only empirical command was dispatched through the verified control-PR route on 2026-11-22 (comment [7076935878](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7076935878)). Its run ID and status could not yet be verified from the available connector's run-list interface. The next cycle should inspect the live queue-guardian status/artifact and the USDⓈ-M run, then diagnose the funding acceptance gate; do not duplicate the command while it may be active.
