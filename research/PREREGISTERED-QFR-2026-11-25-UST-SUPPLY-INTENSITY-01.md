# Preregistration — Treasury 10-year auction supply intensity

- **Hypothesis ID:** QFR-2026-11-25-UST-SUPPLY-INTENSITY-01
- **Registered:** 2026-11-25, before the first empirical run
- **Status:** IDEA pending field-coverage verification
- **Distinct mechanism:** supply/duration absorption, not bidder-composition or bid-to-cover effects

## Falsifiable claim

A larger announced 10-year nominal Treasury offering relative to the preceding 12 valid same-tenor offerings predicts a higher next-business-day change in the 10-year reference yield, adding out-of-sample information beyond bid-to-cover and the preceding five-observation yield move.

This is a supply-intensity level proxy, not an issuance surprise relative to a contemporaneous market expectation.

## Data and timing

- Auction source: public Treasury Fiscal Data legacy auctions_query endpoint.
- Universe: nominal fixed-rate 10-year Treasury Notes only.
- Required field: offering_amt, joined by CUSIP and auction date.
- Signal availability: record_date, the Treasury row publication date. The official Treasury description states that the amount to be auctioned is announced several days before the auction.
- Yield source: FRED DGS10, with the existing Treasury XML cross-check recorded separately.
- Target: first-to-second observed DGS10 change strictly after record_date, in basis points.
- Missing offering amounts are never imputed. At least 95% positive coverage is required; otherwise the run is inconclusive.

## Feature and model

- Supply intensity: log(current offering_amt / median(previous 12 valid 10-year nominal offering amounts)).
- Baseline OLS features: bid-to-cover and the preceding five-observation DGS10 change.
- Augmented OLS features: baseline plus supply intensity.
- Rolling training window: 52 prior events.
- Leakage control: a prior event is eligible only if its target end date is strictly earlier than the current record_date.
- Validation: 2019–2022.
- Test: 2023 onward.
- High-supply diagnostic: current supply intensity at or above the nearest-rank 75th percentile of the preceding 52 available supply-intensity observations.

## Preregistered decision rule

A promising result requires all of the following:

1. At least 30 chronological test forecasts.
2. Augmented RMSE improves over baseline in both validation and test periods.
3. The 95% circular-block bootstrap lower bound for paired test squared-loss improvement is above zero.
4. High-supply events have a positive mean next-business-day yield change relative to other test events, and the 95% circular-block bootstrap lower bound for that difference is above zero.

If both validation and test RMSE fail to improve and the high-supply event effect is non-positive, reject the hypothesis. All other outcomes are inconclusive. A positive forecast result is only BACKTESTED, not independently validated or tradable.

## Literature rationale

Seth Kopchak, “The absorption effect of US Treasury auctions,” Review of Quantitative Finance and Accounting (2014), reports short-lived relative-yield effects associated with additional Treasury cash-flow supply around auction calendars. This motivates testing supply intensity at the 10-year tenor; it does not establish that the proposed proxy or target should work.

## Explicit limitations

- Offering size is not an exogenous supply surprise.
- DGS10 is a reference yield, not an executable futures or ETF price.
- A daily target does not isolate intraday auction-window repricing.
- Results do not generalize automatically to other tenors or security types.
- No causal, tradable, or live-deployment claim is permitted.
