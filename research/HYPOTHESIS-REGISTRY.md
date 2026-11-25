# Hypothesis Registry

This registry records stable hypothesis identities and evidence-backed dispositions. Forecasting backtests are not tradable strategy validation; any such distinction is stated per entry.

| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |
|---|---|---|---|---|---|
| QFR-2026-11-25-UST-AUCTION-ABSORPTION-01 | IDEA | Auction bidder composition (primary-dealer accepted share) adds out-of-sample predictive information about the next five-business-day change in the 10-year Treasury par yield beyond bid-to-cover and recent yield movement. Weak demand should predict higher subsequent yields. | Official Treasury 10-year nominal note auction results plus official daily Treasury par-yield curve; from first verifiable bidder-class coverage through latest complete date. | Pending first real-data walk-forward forecast backtest. | Session report and generated manifest will be linked after the run. |

## Disposition rules

- IDEA: mechanism and falsifiable claim recorded; feasibility not yet established.
- FEASIBILITY_CHECKED: required data and semantics verified, but no complete real-data backtest yet.
- BACKTESTED: reproducible real-data walk-forward experiment completed; outcome may be negative.
- ROBUSTNESS_TESTED: material sensitivity, regime and alternative-explanation checks completed.
- INDEPENDENTLY_VALIDATED: independent reconstruction or genuinely separate source confirms the result.
- REJECTED: evidence falsifies the claim or its incremental value.
- INCONCLUSIVE: data, coverage, sample size or inference cannot support a decision.

A forecasting backtest is not a trading P&L. Do not assign CAGR, Sharpe, Sortino or drawdown to a yield-forecasting result. Tradable evaluation requires a separately validated instrument-price series and realistic execution assumptions.
