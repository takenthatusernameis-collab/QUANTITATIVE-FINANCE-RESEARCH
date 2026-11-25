# Preregistration — Treasury auction demand stress and subsequent yield volatility

- **Hypothesis ID:** QFR-2026-11-25-UST-AUCTION-VOLATILITY-01
- **Registered:** 2026-11-25, before the first empirical run
- **Status:** IDEA pending source and window validation
- **Distinct mechanism:** auction-demand fragility predicts the magnitude of subsequent yield variation, not the sign of the yield change. This is a risk/volatility channel, not a re-estimation of the rejected supply-level direction hypothesis.

## Falsifiable claim

Weak 10-year Treasury auction demand—low bid-to-cover combined with high primary-dealer absorption—predicts greater next-window daily 10-year yield variation than can be explained by pre-auction yield variation and bid-to-cover alone.

The mechanism is dealer risk-bearing and post-auction price adjustment. It does not assume that dealer share is a structural measure of demand elasticity.

## Data and timing

- Auction source: public U.S. Treasury Fiscal Data legacy auctions_query, with the existing updated-v2 adapter only when every candidate row is reconciled to official result XML and at least one exact legacy overlap is verified.
- Universe: nominal fixed-rate original-term 10-year Treasury Notes.
- Auction features: bid_to_cover_ratio and primary_dealer_accepted / competitive accepted amount.
- Yield source: FRED DGS10 (Board of Governors H.15), with the existing direct Treasury XML cross-check recorded separately.
- Signal timestamp: record_date, following the repository's conservative publication-timing convention.
- Pre-event control: root-sum-square of the five consecutive observed daily DGS10 changes ending at the latest observation on or before record_date.
- Target: root-sum-square of the first five consecutive observed daily DGS10 changes beginning strictly after record_date. This is a daily reference-yield variation proxy, not intraday futures volatility.
- Exactly six observed yield levels are required for each five-change window. No missing observations are filled.

## Feature and model

- Target transform: log(1 + target variation in basis points).
- Baseline OLS features: log(1 + pre-event five-observation yield variation) and bid-to-cover.
- Augmented OLS features: baseline plus primary-dealer accepted share.
- Rolling training window: 52 prior auction events.
- Leakage control: a training event is eligible only if its five-observation target end date is strictly earlier than the current record_date.
- Validation: 2019–2022. Test: 2023 onward.
- High-stress diagnostic: mean of the trailing-26-event percentile of dealer share and reverse percentile of bid-to-cover; fixed threshold 0.75. The score uses prior events only.

## Preregistered decision rule

A promising result requires all of the following:

1. At least 30 chronological test forecasts.
2. Augmented RMSE in log-variation space improves over baseline in both validation and test.
3. The 95% circular-block bootstrap lower bound for paired test squared-log-loss improvement is above zero.
4. High-stress test events have greater mean target variation than other events, and the 95% circular-block bootstrap lower bound for that difference is above zero.

If both validation and test RMSE fail to improve and the high-stress mean difference is non-positive, reject the hypothesis. All other outcomes are inconclusive. Do not tune the threshold or model after observing results.

## Literature rationale

- Lee A. Smales (2020), “The effect of treasury auctions on 10-year Treasury note futures,” *Accounting & Finance*, DOI: https://doi.org/10.1111/acfi.12635. Using 15-minute intervals for 2000–2017, the study reports higher post-auction volatility and lower return volatility following higher bid-to-cover outcomes. This motivates a volatility-channel test but does not validate a daily DGS10 proxy.
- Rui Albuquerque, José Miguel Cardoso-Costa and José Afonso Faias (2024), “Price elasticity of demand and risk-bearing capacity in sovereign bond auctions,” *Review of Financial Studies*, DOI: https://doi.org/10.1093/rfs/hhae027. The study links dealer demand elasticity to same-bond secondary-market volatility and post-auction returns. Aggregate bidder shares here do not estimate its structural elasticity measure.

## Explicit limitations

- DGS10 is a reference yield, not an executable futures or ETF price.
- Daily root-sum-square yield variation is a coarse proxy; it cannot isolate immediate post-auction or 15-minute volatility.
- Aggregate primary/direct/indirect shares are not individual bidder identities, bid curves or a structural elasticity estimate.
- record_date is used as a conservative signal-availability timestamp; no intraday publication timestamp is available in this test.
- No causal, tradable, or live-deployment claim is permitted.
