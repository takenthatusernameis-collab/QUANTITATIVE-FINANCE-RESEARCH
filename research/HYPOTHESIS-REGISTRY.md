# Hypothesis Registry

This registry records stable hypothesis identities and evidence-backed dispositions. Forecasting backtests are not tradable strategy validation; any such distinction is stated per entry.

| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |
|---|---|---|---|---|---|
| QFR-2026-11-25-UST-AUCTION-ABSORPTION-01 | INCONCLUSIVE | Primary-dealer accepted share adds incremental walk-forward predictive information about the next five-business-day 10-year yield change beyond bid-to-cover and recent yield movement; weak demand is expected to precede higher yields. | 10-year nominal Treasury notes, source auction coverage 2008-05-07 to 2026-11-10 (complete five-day target events through 2026-10-07); FRED DGS10 (Board of Governors H.15 via FRED); Treasury XML all-years cross-check attempted daily yield observations 2008-01-02 to 2026-11-23 | INCONCLUSIVE — mixed predictive evidence; do not promote or claim an economic edge; test OOS n=46, augmented RMSE=11.329 bp, baseline RMSE=11.4001 bp, RMSE improvement=0.624%, hybrid merge=MERGED_VERIFIED_SLICE, v2 appended=1; paired squared-loss delta=1.61689 bp^2, 95% block-bootstrap CI=[-2.050153, 5.153464] bp^2; weak-demand events=3; updated auctions API probe=SAMPLE_ONLY, 10-year nominal rows=2, population crosswalk=RECONCILED_SAMPLE_ONLY, legacy overlap=VERIFIED | [../reports/sessions/2026-11-25/2026-11-25T070316Z_session-treasury-auction-45565139776.md](../reports/sessions/2026-11-25/2026-11-25T070316Z_session-treasury-auction-45565139776.md) |

## Disposition rules

- IDEA: mechanism and falsifiable claim recorded; feasibility not yet established.
- FEASIBILITY_CHECKED: required data and semantics verified, but no complete real-data backtest yet.
- BACKTESTED: reproducible real-data walk-forward experiment completed; outcome may be negative.
- ROBUSTNESS_TESTED: material sensitivity, regime and alternative-explanation checks completed.
- INDEPENDENTLY_VALIDATED: independent reconstruction or genuinely separate source confirms the result.
- REJECTED: evidence falsifies the claim or its incremental value.
- INCONCLUSIVE: data, coverage, sample size or inference cannot support a decision.

A forecasting backtest is not a trading P&L. Do not assign CAGR, Sharpe, Sortino or drawdown to a yield-forecasting result. Tradable evaluation requires a separately validated instrument-price series and realistic execution assumptions.
| QFR-2026-11-25-UST-SUPPLY-INTENSITY-01 | REJECTED | Announced 10-year nominal offering size relative to the trailing 12 valid same-tenor auctions adds incremental information about the next observed business-day DGS10 change beyond bid-to-cover and prior five-day yield movement; higher relative supply is expected to raise yields. | Legacy Treasury auctions_query nominal 10-year Notes 2008-05-07 to 2026-10-07; FRED DGS10 (Board of Governors H.15 via FRED); Treasury XML all-years cross-check attempted observations 2008-01-02 to 2026-11-23 | REJECTED — neither chronological forecast period improves and high-supply events do not precede higher yields; test OOS n=46, augmented RMSE=5.596 bp, baseline RMSE=5.543 bp, improvement=-0.9552%, high-supply mean difference=-0.6276 bp | [../reports/sessions/2026-11-25/2026-11-25T073609Z_session-treasury-supply-45569410213.md](../reports/sessions/2026-11-25/2026-11-25T073609Z_session-treasury-supply-45569410213.md) |
