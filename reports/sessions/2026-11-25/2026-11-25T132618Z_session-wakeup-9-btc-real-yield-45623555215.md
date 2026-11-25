# Wake-up session report — 2026-11-25T132618Z

## Repository state and selection

- Default branch: main; source commit: db4afd3fea810e92c678fabed0945748432c0403.
- No open PRs or issues were present at selection.
- Earlier on 2026-11-25, three distinct Treasury real-data backtests and one CFTC real-data backtest had already met the daily minimum; the same-day VIX study was an additional experiment. This is another materially distinct cross-asset forecast hypothesis.
- Prior repository hypotheses were checked in research/HYPOTHESIS-REGISTRY.md; this is not a parameter variation of the Treasury, CFTC or VIX studies.
- Research/paper simulation only. No live orders, capital deployment, paid data, credentials or external permissions.

## Research output

### QFR-2026-11-25-BTC-REAL-YIELD-SHOCK-01

**Disposition: REJECTED — REJECTED — the augmented model fails to improve either period and paired-loss inference indicates it is worse.**

The study tests whether the lagged five-observation change in the 10-year TIPS real yield adds predictive information about the next five Bitcoin daily returns beyond Bitcoin's own momentum and realized volatility.

- CBBTCUSD coverage: 2016-11-25 to 2026-11-24 (3651 valid observations).
- DFII10 coverage: 2016-11-25 to 2026-11-23 (2498 valid observations).
- Accepted non-overlapping origins: 601; candidate origins: 605; skipped: {"incomplete_btc_pre_return_window": 3, "incomplete_btc_target_window": 1, "insufficient_real_yield_history": 0, "no_strictly_prior_real_yield_observation": 0, "overlapping_target_window": 0, "stale_real_yield_observation": 0}.
- Signal: BTC observation date t; the latest DFII10 observation is strictly prior to t.
- Target: next five observed daily BTC closes, measured as log return in percentage points.
- Event spacing: six BTC observations; target windows do not overlap.
- Rolling training window: 104 fully matured prior events.
- Validation: 2019–2021; test: 2022 onward.

| Metric | Validation | Test |
|---|---:|---:|
| Forecasts | 178 | 298 |
| Baseline RMSE (%) | 8.902267 | 6.054285 |
| Augmented RMSE (%) | 9.028444 | 6.127806 |
| RMSE improvement | -1.4174% | -1.2144% |
| Baseline directional accuracy | 0.5281 | 0.4899 |
| Augmented directional accuracy | 0.5618 | 0.4732 |

- Paired test squared-error bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.0015, "ci_95_high_pct2": -0.26779361055211903, "ci_95_low_pct2": -1.5828770744775202, "mean_baseline_minus_augmented_squared_error_pct2": -0.8956344137407214, "observations": 298, "reps": 2000, "status": "COMPUTED"}.

## Literature and novelty boundary

- Jareño, González and Almansa (2025), “Interest rate sensitivity of traditional, green, and stable cryptocurrencies: A comparative study across market conditions,” *Quantitative Finance and Economics*, DOI: https://doi.org/10.3934/QFE.2025004. The study decomposes nominal rates into real yields and inflation expectations and reports regime-dependent cryptocurrency rate sensitivity; it motivates, but does not validate, this strict-lag incremental forecasting test.
- Smales (2023), “Cryptocurrency as an alternative inflation hedge?”, *Accounting & Finance*, DOI: https://doi.org/10.1111/acfi.13193. The reported Bitcoin response to inflation-expectation changes is conditional, supporting a conservative test of a distinct real-discount-rate channel rather than a blanket macro-beta assumption.

## Reproducibility and data integrity

- Source URLs, exact row counts/coverage, retrieval time and SHA-256 hashes are in reports/generated/btc-real-yield-shock/45623555215-attempt-1/manifest.json.
- No raw source data are committed. Coinbase CBBTCUSD observations are copyrighted and are not redistributed.
- Deterministic timing, missingness, non-overlap, walk-forward maturity and decision-rule tests ran in the workflow.

## Verified versus unverified

**VERIFIED:** public source retrieval and CSV parsing; source coverage and hashes; strict prior-date real-yield alignment; no forward-fill; exact BTC daily return continuity; non-overlapping target windows; fully matured training targets; chronological validation/test metrics and paired block-bootstrap under this code/data vintage.

**UNVERIFIED:** historical point-in-time FRED vintages; stability in future regimes; causal real-yield-to-BTC transmission; executable spot/perpetual performance; transaction costs, slippage, liquidity and economic value.

## Daily KPI and research versus operations

**DAILY KPI: MET before this additional study**, according to earlier same-day session reports. This session adds one distinct, preregistered real-data cross-asset forecast test.

Research: one new lagged 10-year TIPS real-yield mechanism tested against a Bitcoin-only momentum/volatility baseline. Operations: source retrieval, deterministic checks, report/manifest persistence and registry update.

## Next

- If BACKTESTED, require independent reconstruction and a separately preregistered instrument-level economic study before any strategy claim.
- If REJECTED or INCONCLUSIVE, close under the frozen decision rule; do not tune this hypothesis ID.
- No automatic timebox extension.
