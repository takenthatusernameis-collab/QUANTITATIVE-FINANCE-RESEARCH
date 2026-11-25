# Hypothesis Registry

This registry records stable hypothesis identities and evidence-backed dispositions. Forecasting backtests are not tradable strategy validation; any such distinction is stated per entry.

| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |
|---|---|---|---|---|---|
| QFR-2026-11-25-UST-AUCTION-ABSORPTION-01 | INCONCLUSIVE | Primary-dealer accepted share was tested for incremental walk-forward prediction of the next five-business-day 10-year yield change beyond bid-to-cover and recent yield movement; weak demand was expected to precede higher yields. | 226 selected 10-year nominal note auctions (2008-05-07 to 2026-10-07); 4,726 H.15 DGS10 observations (2008-01-02 to 2026-11-23). Direct Treasury par-yield cross-check unavailable in run 45542932737. | INCONCLUSIVE — 46 test forecasts; augmented RMSE 11.3290 bp vs baseline 11.4001 bp (+0.624%); both test OOS R² values negative; weak-demand subgroup 3 events with no bootstrap interval. DGS10 proxy result does not validate the exact direct Treasury par-yield target. | [Canonical session report](../reports/sessions/2026-11-25/2026-11-25T035247Z_session-treasury-auction-45542932737.md); [manifest](../reports/generated/treasury-auction-demand/45542932737-attempt-1/manifest.json); [Actions run](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45542932737) |

## Disposition rules

- IDEA: mechanism and falsifiable claim recorded; feasibility not yet established.
- FEASIBILITY_CHECKED: required data and semantics verified, but no complete real-data backtest yet.
- BACKTESTED: reproducible real-data walk-forward experiment completed; outcome may be negative.
- ROBUSTNESS_TESTED: material sensitivity, regime and alternative-explanation checks completed.
- INDEPENDENTLY_VALIDATED: independent reconstruction or genuinely separate source confirms the result.
- REJECTED: evidence falsifies the claim or its incremental value.
- INCONCLUSIVE: data, coverage, sample size or inference cannot support a decision.

A forecasting backtest is not a trading P&L. Do not assign CAGR, Sharpe, Sortino or drawdown to a yield-forecasting result. Tradable evaluation requires a separately validated instrument-price series and realistic execution assumptions.
