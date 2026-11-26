# Research session — DeFiLlama stablecoin-supply source preflight

- **Hypothesis:** QFR-2026-11-26-DEFILLAMA-STABLECOIN-SUPPLY-BTC-DOWNSIDE-01
- **Source preflight run:** [45853947478](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45853947478)
- **Admission guard run:** [45853947485](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45853947485)
- **Triggering commit:** 137d8b9a159ac09f25a851dc51633b112ce8be62
- **Result:** PASS — source schema, historical coverage and market identity gates passed. No backtest was run in this preflight.

## DeFiLlama source

- Endpoint: https://stablecoins.llama.fi/stablecoincharts/all
- Field: totalCirculatingUSD.peggedUSD
- Coverage: 2021-01-01 through 2026-11-22
- Observations: 2,152 daily rows
- Maximum date gap: one day
- Minimum observed aggregate value: USD 27,375,683,581
- Maximum observed aggregate value: USD 312,868,568,046
- Response SHA-256: 4dcbf029ff5dec668c2a1e7302f5596e7b5faf89a02e127e8f1f1325b91793c0

## Binance market identity

- BTCUSDT status: TRADING
- Base/quote: BTC/USDT
- Spot trading allowed: true
- Exchange-info response SHA-256: 1b3dc90cbcff1f550271a531a160fc4e81053a2dea0a88148d65368e6bacebdc

## Validation

- Seven source-parser and coverage tests passed locally and in GitHub Actions.
- Repository workflow-admission guard passed.
- Raw market observations were not saved or committed.
- The DeFiLlama series is current-vintage; historical point-in-time revisions and exact publication timestamps remain unverified.

## Next action

Proceed with the frozen MEDIUM implementation timebox. Do not relax the feature lag, sample, model, target, acceptance sample or decision rule.
