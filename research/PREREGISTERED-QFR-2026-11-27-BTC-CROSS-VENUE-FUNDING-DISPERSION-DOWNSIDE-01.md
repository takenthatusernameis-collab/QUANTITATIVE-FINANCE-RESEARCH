# Preregistered experiment: BTC cross-venue perpetual funding dispersion and next-session Spot downside loss

- **Hypothesis ID:** QFR-2026-11-27-BTC-CROSS-VENUE-FUNDING-DISPERSION-DOWNSIDE-01
- **Status:** PREREGISTERED; source preflight pending; no model or backtest executed.
- **Preregistration freeze:** 2026-11-27T04:37:33Z
- **Difficulty:** MEDIUM
- **Difficulty rationale:** two independent public perpetual-funding APIs, separate pagination contracts, settlement-time and interval reconciliation, a cross-venue matched-event panel, a new dispersion feature, and a one-session Spot downside target. Existing MEXC and Binance Spot archive helpers can be reused, but the Binance USD-M funding route and exact common-event population require fresh deterministic tests.
- **Timebox start:** 2026-11-27T04:37:33Z
- **Maximum substantive cycles:** 4 total
- **Hard implementation deadline:** 2026-11-30T04:37:33Z
- **Hard final research-conclusion deadline:** 2026-12-02T04:37:33Z
- **Expiry rule:** the earlier of four substantive cycles or five calendar days governs. No automatic extension, silent clock reset, relaxed source gate, same-ID formula change or duplicate backtest is authorized.

## 1. Falsifiable hypothesis

Does the daily mean absolute difference between exact, matched eight-hour BTC perpetual funding settlements on MEXC and Binance USD-M add chronological out-of-sample information about the next Binance Spot BTCUSDT daily downside loss beyond recent Spot downside risk and realized variance?

The mechanism is **cross-venue funding dispersion / leverage-demand fragmentation**. A larger same-time funding-rate difference may indicate that leveraged demand, contract basis, inventory or arbitrage constraints are not being equalized across the two venues. The preregistered prediction is that unusually large dispersion is associated with greater next-session BTC Spot downside loss.

This is a predictive claim only. It does not claim that funding dispersion is an executable arbitrage opportunity, a causal liquidation signal, a consolidated measure of global leverage, or a measure of any user's realized funding cashflow.

## 2. Novelty and literature boundary

The repository already tested the prior-day sum of MEXC BTC_USDT funding rates as a single-venue feature for next-session BTC Spot downside loss (QFR-2026-11-26-MEXC-BTC-FUNDING-DOWNSIDE-01); that result was INCONCLUSIVE. This experiment is not a retune of that feature: it uses the **mean absolute, timestamp-matched MEXC-versus-Binance funding-rate difference**, a different market-structure mechanism. The same one-session target and baseline are retained deliberately so the incremental results can be compared without changing the target or split.

The broader cross-exchange funding-spread mechanism is already in the literature. Zhivkov (2026), *The Two-Tiered Structure of Cryptocurrency Funding Rate Markets*, studies funding-rate dynamics across 26 exchanges and reports differences in integration between centralized and decentralized venues (https://doi.org/10.3390/math14020346). De Blasis and Webb (2022), *Arbitrage, contract design, and market structure in Bitcoin futures markets*, document contract-design and market-structure differences in Bitcoin futures (https://doi.org/10.1002/fut.22305). No first-in-literature claim is made. The narrower contribution is a long-window, two-CEX, timestamp-matched forecast screen for next-session BTC Spot downside loss.

## 3. Frozen public sources and source-feasibility gates

### MEXC BTC_USDT perpetual funding

- Official endpoint: GET https://contract.mexc.com/api/v1/contract/funding_rate/history.
- Parameters: symbol=BTC_USDT, page_num, page_size=1000.
- Official documentation: https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate-history
- Retrieve every page using stable totalCount/totalPage, exact page progression and response SHA-256 hashes.
- Require success=true, code=0, exact symbol=BTC_USDT, finite fundingRate, integer millisecond settleTime, and collectCycle=8.
- Each settlement must be exactly on 00:00, 08:00 or 16:00 UTC. Reject duplicate timestamps and off-grid times.
- A missing settlement is not imputed. It makes that UTC date incomplete.

### Binance USD-M BTCUSDT perpetual funding

- Official endpoint: GET https://fapi.binance.com/fapi/v1/fundingRate.
- Parameters: symbol=BTCUSDT, inclusive startTime/endTime in Unix milliseconds, limit=1000.
- Official documentation: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- The endpoint documents ascending results and a maximum page size of 1,000. Paginate with the next startTime equal to the last returned fundingTime + 1 ms; reject repeated, unsorted, out-of-range or duplicate rows.
- Require exact symbol=BTCUSDT, finite fundingRate, integer millisecond fundingTime, and timestamps on 00:00, 08:00 or 16:00 UTC.
- The historical series must have no observed sub-eight-hour interval. Gaps that are integer multiples of eight hours are treated as missing observations and counted; an observed one-hour, four-hour or other off-grid interval fails the source gate rather than being normalized or silently discarded.
- Require boundary observations at 2025-06-14 16:00 UTC and 2026-11-24 00:00 UTC. These bound the first and last in-sample funding days.

### Frozen common sample and BTC Spot reference

- Funding comparison window: 2025-06-15 through 2026-11-23 inclusive.
- Match only exact common settlement timestamps. Each accepted UTC date must contain precisely the three common slots 00:00, 08:00 and 16:00 UTC on both venues.
- Require at least 400 complete matched dates, no more than 5% incomplete dates in the frozen calendar window, a maximum run of three consecutive incomplete dates, and matched observations on both the first and last frozen dates.
- Require the MEXC and Binance USD-M funding series to be complete enough to satisfy those same matched-date gates. Do not forward-fill, interpolate, rescale hourly rates to eight-hour rates, or synthesize missing settlements.
- Instrument/target reference: official Binance Vision BTCUSDT Spot 1d UTC archives with checksum sidecars, 2025-06-10 through 2026-11-23 inclusive. The five pre-window dates are needed for the frozen prior-five-session baseline. Require exact daily coverage, unique dates, valid positive closes, checksum verification and no zero-volume days.
- Require at least 400 accepted daily forecast events after prior-history and next-session target construction.
- Preserve exact request URLs, retrieval timestamps, page counts, API metadata, response hashes, archive checksums, coverage and aggregate manifest hashes. Do not save or commit raw funding or price observations.

If any source, cadence, timestamp, boundary, matched-date or event-count gate fails, stop before model implementation and close this hypothesis as **INCONCLUSIVE/INFEASIBLE**. Do not shorten the sample, move the split, change venues, infer missing funding as zero, or relax the eight-hour common-event rule.

## 4. Frozen feature, signal and target

For UTC date d, define the single augmented feature:

D_d = (10,000 / 3) × sum over h in {00,08,16} of abs(f_MEXC[d,h] - f_Binance[d,h]).

- f_MEXC and f_Binance are the published funding rates for the exact same settlement timestamp.
- D_d is the mean absolute cross-venue funding-rate difference per eight-hour settlement, scaled to basis points.
- No clipping, winsorization, sign selection, annualization, alternative aggregation, threshold, regime split or additional feature is permitted.
- Signal availability: after the Binance Spot UTC daily candle for date d has closed. The feature uses only the three funding records timestamped on date d, all of which must already have settled.
- Target: max(-r[d+1],0)^2 × 10,000, where r[d+1] is the next Binance BTCUSDT Spot UTC daily close-to-close log return. The model target is log1p(target). This is a one-session downside-loss forecast, not trading P&L.

## 5. Frozen baseline, model and chronological evaluation

- Baseline features: log1p prior-one-session downside loss, log1p prior-five-session downside semivariance, and log1p prior-five-session total realized variance.
- Augmented model: the same baseline plus exactly one feature, mean_abs_funding_spread_bps.
- Model: repository standardized, ridge-stabilized OLS; scaling and fitting use training observations only.
- Rolling training window: latest 104 prior daily events whose target is fully matured before the current signal date.
- Validation signal dates: 2025-10-01 through 2026-02-28.
- Test signal dates: 2026-03-01 through 2026-11-23.
- Minimum forecasts: validation 60, test 120.
- Primary metric: RMSE in log1p next-session downside-loss space; MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block size seven daily events, seed 20261127.
- Preserve the exact accepted event population and every exclusion count.

## 6. Frozen decision rule and limitations

- **PROMISING forecast screen:** both validation and test RMSE improve, and the paired test squared-loss 95% confidence interval's lower bound is strictly above zero.
- **REJECTED:** both validation and test RMSE worsen, and the paired test squared-loss 95% confidence interval's upper bound is strictly below zero.
- **INCONCLUSIVE:** every other outcome, including mixed RMSE, confidence intervals crossing zero, insufficient samples, incomplete sources or a failed cadence gate.
- A PROMISING result remains a forecast-only screen, not independent validation or a trading strategy.
- MEXC and Binance may use different mark/index prices, premium calculations, interest assumptions, caps, contract parameters and operational rules. The feature is therefore a published-rate dispersion proxy, not a frictionless arbitrage spread or a standardized cashflow difference.
- The two exchanges are not the global perpetual market. Funding rates are not proof of trader identity, directional inventory or passive liquidity.
- No perpetual funding P&L, transaction-cost-adjusted return, leverage return, CAGR, Sharpe, Sortino, Calmar, drawdown, live order, capital deployment or strategy-promotion claim is authorized.
- Spot-price validation and perpetual-futures P&L acceptance remain separate. This experiment forecasts a Spot downside target from published funding-rate observations only.

## 7. Source-preflight-only first cycle

The first cycle is strictly source feasibility and deterministic parser/alignment validation. It must not fit a model, inspect forecast performance, tune the feature or produce a backtest. A passing preflight permits a separate atomic model implementation/admission commit under this same frozen identity and timebox. A failed preflight closes the hypothesis as INCONCLUSIVE/INFEASIBLE.

## 8. Timebox and expiry

- The MEDIUM budget is at most four substantive cycles and five calendar days from the frozen start, whichever expires first.
- The implementation deadline is 2026-11-30T04:37:33Z.
- The final research-conclusion deadline is 2026-12-02T04:37:33Z.
- At expiry, publish the strongest defensible conclusion. If source acceptance, implementation or execution remains unresolved, close INCONCLUSIVE/INFEASIBLE; do not infer a performance NO-GO from missing data or elapsed time.
- Do not silently reset the clock, automatically extend it, weaken the source gates, or rerun a completed empirical result merely to seek a different outcome.
