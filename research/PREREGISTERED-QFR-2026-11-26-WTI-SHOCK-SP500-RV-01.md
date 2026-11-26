# Preregistered hypothesis: lagged WTI repricing and S&P 500 realized volatility

- **Hypothesis ID:** QFR-2026-11-26-WTI-SHOCK-SP500-RV-01
- **Status:** FEASIBILITY_CHECKED
- **Registered:** 2026-11-26 UTC
- **Research class:** daily real-data forecast screen, not a trading strategy or causal study.

## Research question and mechanism

Does a strictly lagged five-observation change in the EIA WTI Cushing spot price add chronological out-of-sample information about next-five-session S&P 500 realized volatility beyond recent S&P 500 realized volatility and the VIX close?

The mechanism is energy-market repricing: a rapid crude-price increase may reflect supply disruption, geopolitical risk, input-cost pressure or inflation uncertainty not fully summarized by recent equity volatility and VIX. The directional prior is that a positive WTI shock is associated with higher subsequent equity realized volatility. This tests incremental predictive value, not causality.

This is distinct from the repository's dollar, real-yield, Treasury-curve, auction, financial-conditions, repo-funding, implied-volatility and CFTC-positioning screens: its information source is a physical energy-market price.

## Source feasibility

- WTI: FRED DCOILWTICO, sourced from EIA daily WTI Cushing, Oklahoma spot prices. The FRED series page reports daily frequency, history beginning 1986-01-02 and a latest observation of 2026-11-24 in the 2026-11-25 update. FRED labels the series public domain with citation requested.
- Equity price: FRED SP500, daily S&P 500 price index; its available daily history bounds the common sample from November 2016.
- Implied volatility: FRED VIXCLS, daily CBOE VIX close.
- Sources: https://fred.stlouisfed.org/series/DCOILWTICO ; https://fred.stlouisfed.org/data/DCOILWTICO ; https://fred.stlouisfed.org/series/SP500 ; https://fred.stlouisfed.org/series/VIXCLS
- Retrieve public FRED CSVs from 2016-11-25 onward. No API key, paid data or private source is required.

The WTI history contains a legitimate negative Cushing spot observation of -$36.98/barrel on 2020-04-20. It must be retained, not discarded or coerced to a positive value. Therefore a log return is invalid for this series. The preregistered feature uses the inverse-hyperbolic-sine transform with a fixed $50/barrel scale.

## Frozen signal, feature and target

- Signal: S&P 500 close on date t, with same-date VIX close as a baseline input.
- WTI availability: latest valid WTI observation dated strictly before t. Same-date WTI is prohibited.
- WTI feature: asinh(WTI[d] / 50) - asinh(WTI[d-5] / 50), with WTI in USD/barrel and a fixed $50/barrel scale. d is the latest valid WTI observation strictly before t; d-5 is five valid WTI observations earlier (six observations, five intervals). The transform remains finite for zero and negative prices.
- Missingness: no forward-fill, interpolation, synthetic prices or zero returns. Require WTI observation age no more than five calendar days and no gap above five calendar days inside the six-observation feature window. If a check fails, skip the event and count the reason. Historical source gaps are recorded, not imputed or treated as a global failure.
- Baseline: log1p prior-five-session and prior-twenty-session S&P 500 realized volatility, plus log VIX on t.
- Augmented model: add only the five-observation WTI asinh change.
- Target: log1p of next-five-session S&P 500 realized volatility, computed as square root of summed squared daily log returns and expressed in percent before log1p.
- Event spacing: signal origins every six S&P 500 observations, so five-session target windows do not overlap.

## Walk-forward evaluation

- Model: ridge-stabilized ordinary least squares; feature standardization is estimated on training data only.
- Training: 104 prior events. Every training target must have ended strictly before the current signal date.
- Validation: 2019-01-01 through 2021-12-31.
- Test: 2022-01-01 onward, using only information available at each sequential forecast origin.
- Minimum sample: at least 30 forecasts in each period; otherwise INCONCLUSIVE.
- Primary metric: RMSE in log1p realized-volatility space. MAE and out-of-sample R-squared are descriptive.
- Paired uncertainty: 2,000 deterministic circular-block bootstrap replications on test squared-loss differences, block length four consecutive non-overlapping events.

## Frozen decision rule

- BACKTESTED / PROMISING: at least 30 forecasts in each period; augmented RMSE improves in both validation and test; and the paired test squared-loss 95% lower confidence bound for baseline-minus-augmented loss is above zero.
- REJECTED: augmented RMSE fails to improve in both periods and the paired-loss bootstrap upper confidence bound is below zero.
- INCONCLUSIVE: every other outcome, including mixed RMSE results, a confidence interval crossing zero, insufficient samples, stale sources or incomplete data.

No result-dependent retuning, alternate horizon, feature expansion, threshold search or repeated run under this hypothesis ID is authorized. A failed data or execution gate is not a completed backtest.

## Limitations and boundaries

- WTI Cushing is a location-specific physical benchmark, not a global crude basket or futures return series; quality, storage, transport and regional basis effects matter.
- Strict prior-date alignment avoids same-date publication ambiguity but does not reconstruct intraday historical dissemination timestamps.
- FRED/EIA current vintages are used; historical point-in-time revisions are not reconstructed.
- The baseline does not control for every macroeconomic or geopolitical confounder.
- FRED SP500 is a cash price index, not an executable futures or total-return series.
- Forecast improvement would not establish causality, profitability, tradability, independent validation or deployment readiness.
- Persist source URLs, retrieval time, coverage, hashes and aggregate metrics only. Do not commit raw source rows.
- No live orders, capital deployment or strategy promotion are authorized.

## Empirical disposition

- **Status:** FEASIBILITY_CHECKED; no empirical result yet.
- **Execution:** awaiting the atomic admission commit and its immutable GitHub Actions run.
