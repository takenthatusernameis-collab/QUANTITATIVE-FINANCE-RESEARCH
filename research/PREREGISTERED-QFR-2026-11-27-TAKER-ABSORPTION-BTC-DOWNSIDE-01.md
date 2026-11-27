# Preregistered experiment: BTC daily taker-flow/price-response absorption proxy

- **Hypothesis ID:** QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01
- **Status:** ADMITTED; source feasibility PASS; empirical backtest pending.
- **Preregistration freeze:** 2026-11-27T01:34:56Z
- **Difficulty:** LOW
- **Maximum substantive cycles:** 2
- **Implementation deadline:** 2026-11-28T01:34:56Z
- **Final research-conclusion deadline:** 2026-11-29T01:34:56Z
- **No timebox extension or parameter search is authorized.**

## 1. Falsifiable hypothesis

A daily, signed aggressor-flow/price-response divergence proxy from Binance BTCUSDT Spot adds out-of-sample information about the next five UTC daily returns' downside semivariance beyond recent downside semivariance, realized variance and momentum.

The directional mechanism is:

- Positive net taker-buy imbalance on a down-return day is consistent with aggressive buying being met by passive sell-side liquidity. This is coded as positive signed absorption and is hypothesized to precede higher downside risk.
- Negative net taker-buy imbalance on an up-return day is consistent with aggressive selling being met by passive buy-side liquidity. This is coded as negative signed absorption and is hypothesized to precede lower downside risk.

This is a daily-bar proxy for a price-response mismatch, **not direct observation of resting limit orders or proof of passive liquidity absorption**.

## 2. Novelty boundary

The repository registry contains no prior BTC experiment using Binance daily taker-buy volume interacted with the same-day price response as an incremental downside-semivariance feature. This is materially different from the repository's macro, derivatives, funding, attention, volatility-index and CFTC-positioning hypotheses.

The broader order-imbalance mechanism is not novel to the literature. Koutmos and Wei (2023), *Nowcasting bitcoin's crash risk with order imbalance*, use Bitstamp buyer/seller-initiated volume to nowcast crash risk (DOI: https://doi.org/10.1007/s11156-023-01148-1; full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC10040314/). This experiment does **not** claim to be the first use of Bitcoin order flow. Its narrower contribution is a signed interaction measuring whether daily aggressor imbalance is accompanied by a price move in the same or opposite direction, tested for incremental next-five-day downside-semivariance forecasting against a fixed risk/momentum baseline.

Binance's Spot kline schema exposes total base volume and taker-buy base volume (official schema reference: https://github.com/binance/binance-spot-api-docs/blob/master/sbe/schemas/spot_3_4.xml). The preflight verifies the corresponding 12-column public archive fields and checksums.

## 3. Source-feasibility evidence (completed before model implementation)

- Source: official Binance Vision BTCUSDT Spot 1d UTC monthly/daily kline archives and .CHECKSUM sidecars.
- Preflight run: [45925248340](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925248340), executed on source-preflight commit 6f91629a1f3b5003da516ae1829de1fadf8a0530.
- Preflight manifest SHA-256: 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe.
- Verified archives: 136; verified daily rows: 3,388; coverage: 2017-08-17 through 2026-11-25; missing dates: 0; zero-volume dates: 0; all 3,388 observations have a finite taker-imbalance value.
- Taker imbalance range: -0.650991 to +0.621599; median: -0.008361.
- The 2026-11-26 daily archive returned HTTP 404 at preflight time; 2026-11-25 was available and checksum-verified. The frozen sample therefore ends 2026-11-25. The source preflight implements a bounded three-day trailing-404 publication-lag fallback; non-404 errors and checksum mismatches remain hard failures.
- Timestamp validation covered millisecond and microsecond encodings; all rows were complete UTC daily candles with the documented 12-column schema.
- The final source-preflight run passed both the deterministic schema/coverage tests and the read-only 136-archive probe. It saved no raw observations and executed no backtest.

## 4. Frozen sample, timing and target

- Instrument: Binance BTCUSDT Spot, 1d UTC.
- Price/flow history: 2017-08-17 through 2026-11-25 inclusive.
- Signal origins: eligible daily closes through 2026-11-20; each origin requires 20 complete prior returns and five fully observed future daily returns.
- Signal timestamp: after the UTC daily candle has closed and its archive row is finalized.
- Target window: the five UTC daily log returns immediately after the signal date; no signal-day return is included in the target.
- Target: mean(min(r[t+1:t+5], 0)^2) * 10000, expressed in percentage-points squared; the model target is log1p(target).
- Event schedule: every six calendar days from the first eligible signal date, producing non-overlapping five-session target windows and a one-day separation.
- No imputation of missing price or flow rows. Any missing/invalid feature or target observation is excluded and counted.

## 5. Frozen feature and model

Daily taker imbalance:

I_t = 2 * taker_buy_base_volume_t / total_base_volume_t - 1

Signed absorption proxy:

A_t = max(I_t, 0) * max(-r_t, 0) - max(-I_t, 0) * max(r_t, 0)

- Positive A_t: net taker buying while price falls (sell-side absorption proxy).
- Negative A_t: net taker selling while price rises (buy-side absorption proxy).
- Zero otherwise. A zero-volume candle has undefined imbalance and is not converted to zero.

Fixed baseline features:
- log1p of prior-five-session downside semivariance.
- log1p of prior-20-session downside semivariance.
- log1p of prior-20-session total realized variance.
- Prior-five-session cumulative log return.
- Prior-20-session cumulative log return.

Augmented model: the same baseline plus exactly one feature, signed_taker_absorption.

Model:
- Each forecast uses the latest 104 previously observed, fully matured non-overlapping events.
- Standardized OLS with the repository's fixed 1e-8 coefficient ridge stabilization; no hyperparameter tuning.
- Validation: signal dates from 2019-01-01 through 2021-12-31.
- Test: signal dates from 2022-01-01 through 2026-11-20.
- Minimum accepted forecasts: validation 60, test 100.
- Primary metric: RMSE of log1p downside semivariance.

## 6. Frozen inference and disposition

- Paired baseline-minus-augmented squared-loss difference on the chronological test sample.
- Circular moving-block bootstrap: 2,000 replications, block size 4 events, seed 20261127.
- **PROMISING / BACKTESTED:** validation and test RMSE both improve, and the paired-loss 95% confidence interval's lower bound is above zero. This is a forecast-screen result only, not a trading strategy.
- **REJECTED:** validation and test RMSE both worsen, and the paired-loss 95% confidence interval's upper bound is below zero.
- **INCONCLUSIVE:** every other outcome, including insufficient sample size or failed source/coverage validation.
- No alternate feature formula, threshold, lookback, asset, target horizon, split or model is permitted in this experiment.

## 7. Mandatory limitations and stop conditions

- Binance-only spot aggressor-flow is venue-specific and may not represent consolidated Bitcoin order flow.
- Daily aggregates do not reveal order-book depth, cancellations, trader identity or actual passive absorption. The term “absorption” is interpretive shorthand for the preregistered price-response mismatch proxy.
- A forecast backtest is not a trading P&L. No CAGR, Sharpe, drawdown or deployment claim is allowed.
- Any checksum mismatch, malformed 12-field row, duplicate/missing daily date, invalid taker volume, or non-finite value blocks the backtest.
- If the implementation deadline is reached, commit the completed independent work and report the exact blocker. Do not silently extend the timebox.


## 8. Atomic execution admission

- Admission parent commit: `5f645f5de49d49afb37406d4ff565e48b4dde0bc`.
- Final pre-admission deterministic CI: [run 45925665470](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925665470), completed successfully on the admission parent. It compiled the research modules and passed workflow-admission, source-preflight, BTC downside-model and evidence-persistence regression suites, as well as the existing registered-hypothesis regression suites.
- Frozen source-preflight: [run 45925248340](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925248340), completed successfully on code commit `6f91629a1f3b5003da516ae1829de1fadf8a0530`; 136 checksum-verified archives, 3,388 complete UTC daily rows, 2017-08-17 through 2026-11-25, no missing dates, no zero-volume days, and all 3,388 rows have finite taker imbalance. Archive-manifest SHA-256: `978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe`.
- The final atomic admission commit uses the exact `[QFR-ADMIT] research:` prefix. The push-triggered workflow must check out that exact `github.sha`, rerun the deterministic suites, re-fetch and checksum-verify the frozen archive population, require the exact preflight manifest hash, execute the frozen walk-forward forecast and paired bootstrap, then persist the report/manifest with report-hash and registry/preregistration-digest verification.
- Earlier non-admission pushes were correctly skipped by the research admission gate; no empirical backtest has run yet. The current commit is the first authorized empirical execution for this frozen hypothesis.
- The two-cycle LOW-difficulty budget and both frozen UTC deadlines remain unchanged. No feature, model, target, sample, split, threshold or acceptance rule is changed by this admission.

## 8. Execution result

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994
- Triggering source commit: 7e968673f39e26001ea45f6664129efe77240db2
- Status: COMPLETE
- Decision: INCONCLUSIVE
- Validation/test forecasts: 159/298
- Validation/test RMSE improvement: 0.3119332997745025/-1.0491040022776774
- Paired test-loss bootstrap: {"block_size_events": 4, "bootstrap_fraction_positive": 0.045, "ci_95_high": 0.0018984357165540003, "ci_95_low": -0.037146350903781586, "observations": 298, "observed_mean_baseline_minus_augmented_squared_loss": -0.015970332330204357, "reps": 2000, "seed": 20261127, "status": "COMPUTED"}
- Report: ../reports/sessions/2026-11-27/2026-11-27T020646Z_session-taker-absorption-btc-downside-45926394994.md
- Manifest: ../reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json

Evidence is mixed, statistically uncertain or insufficient under the frozen rule.
