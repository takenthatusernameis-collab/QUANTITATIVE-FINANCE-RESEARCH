# Preregistration — Bitcoin public-attention shocks and downside semivariance

- **Hypothesis ID:** `QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01`
- **Registered:** `2026-11-26T19:02:30Z`, before the source-feasibility workflow is committed or executed.
- **Status:** `FEASIBILITY_CHECKED` — the read-only source preflight passed; no backtest has run.
- **Difficulty:** `LOW`.
- **Difficulty rationale:** one official, no-key daily pageview endpoint; one existing Binance BTCUSDT Spot archive pipeline; one frozen attention feature; one existing downside-semivariance forecast design; deterministic source, timing and maturity tests. The primary uncertainty is live endpoint availability, full historical coverage and stable response semantics from GitHub-hosted runners.
- **Timebox start:** `2026-11-26T19:02:30Z`.
- **Maximum substantive cycles:** 2 total; the earlier of the cycle cap or the hard deadline governs.
- **Hard implementation deadline:** `2026-11-27T19:02:30Z`.
- **Hard final research-conclusion deadline:** `2026-11-28T19:02:30Z`.
- **Expiry rule:** if source feasibility, deterministic implementation, the admitted real-data backtest or the frozen conclusion cannot be completed by the applicable deadline/cycle cap, close as `INFEASIBLE` or `INCONCLUSIVE` with exact evidence. No automatic extension, silent clock reset, altered lag, changed target, moved split, shortened training window or same-ID tuning.

## Research question and falsifiable claim

Does a strictly lagged seven-calendar-day change in English-Wikipedia user pageviews for the `Bitcoin` article add chronological out-of-sample information about next-five-session BTC downside semivariance beyond BTC's own recent downside risk, realized variance and momentum?

The proposed mechanism is **public-attention shock / attention-driven participation**. An abrupt increase in public attention may coincide with a broader arrival of information and greater disagreement or speculative participation, preceding elevated downside risk. The directional expectation is that a positive pageview shock is associated with higher subsequent downside semivariance. Pageviews are only a public-attention proxy; they do not identify investors, trading intent, sentiment or the cause of the attention.

## Novelty and literature boundary

This is not a first-in-literature claim. Nyakurukwa and Seetharam, **“Beyond the hype: examining the relationship between Wikipedia attention and realised skewness for crypto assets”** (2023), study Wikipedia attention and next-day realised skewness for four major cryptocurrencies over 2020–2022 and report a positive time-varying relationship. This preregistration asks a narrower, different forecasting question: whether lagged Bitcoin-article pageview growth adds information about a five-session **downside-semivariance** target beyond a frozen Bitcoin risk-and-momentum baseline, using chronological walk-forward evaluation and non-overlapping events.

Urquhart, **“What causes the attention of Bitcoin?”** (2018), reports that realised volatility and volume are significant drivers of next-day Bitcoin attention. This reverse-direction evidence is an important alternative explanation. The proposed lag, embargo and baseline controls reduce—but do not eliminate—reverse-causality and omitted-variable concerns. No causal interpretation is permitted.

## Source-feasibility gates

### Wikimedia pageviews

- Official endpoint family: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/`.
- Project: `en.wikipedia.org`; article: `Bitcoin`; access: `all-access`; agent: `user`; granularity: `daily`.
- Frozen pageview coverage window: `2017-08-17` through `2026-11-18`, inclusive.
- The API documentation states that pageview data begin on `2015-07-01`.
- Use the required descriptive `User-Agent` header with the repository URL as contact information. Send requests sequentially and wait between requests; no parallel request fan-out.
- The official Wikimedia access policy states that API data are CC0 1.0, requires a `User-Agent`, and directs clients to wait for each request to finish before sending another.
- The official tutorial documents that zero-view days may be omitted from the response. Reconstruct only those omitted daily dates as zero; do not interpolate or forward-fill. Reject more than one consecutive omitted date, duplicate dates, out-of-window dates, malformed timestamps, negative/non-integer counts, wrong project/article/access/agent dimensions, stale endpoints or insufficient coverage.
- Require at least 3,000 observed pageview rows, coverage reaching within one day of both frozen boundaries, and no run of more than one omitted calendar day. Preserve per-chunk response SHA-256 values and a combined digest. Do not commit raw observations.
- Use bounded retries only for transient HTTP/network failures. A non-retryable 4xx response fails the preflight.

### Binance BTCUSDT Spot

- Instrument: Binance Spot `BTCUSDT`, interval `1d`, UTC.
- Use the repository's existing official Binance Vision archive and SHA-256 sidecar verifier; no private endpoints, API keys or paid data.
- Signal dates: first eligible date after the existing 20-session baseline warm-up, through `2026-11-20` inclusive. The five-calendar-session target must be fully matured through `2026-11-25`.
- Require complete daily UTC candles, unique dates, positive finite OHLC values and verified archive checksums. Exclude incomplete candles.
- No raw market observations are committed to Git.

A read-only source preflight must pass before model implementation begins. The preflight does not run a backtest. If Wikimedia or Binance source acceptance fails, close `INFEASIBLE` without implementing or backtesting the model.

### Completed source-preflight evidence

- GitHub Actions run: [45881600522](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881600522), success.
- Wikimedia API: 38 sequential chunks; 3,381 daily rows from 2017-08-17 through 2026-11-18; zero omitted dates; maximum consecutive omission 0; observed views range 2,176–344,686.
- Combined SHA-256 of the 38 pageview responses: `b1bc21a94749fa1775ed5a3482e8076734bcfff58a729a75da29c1f6d4023b60`.
- Binance exchangeInfo: `BTCUSDT`, `TRADING`, Spot trading allowed; response SHA-256 `3f9e1acedee1a539f106bb591b97828d28d13a264a8f4a1959b22649bea11e41`.
- Source preflight saved no raw observations and executed no backtest.
- The API request path uses `en.wikipedia.org`, while the response's `project` field is `en.wikipedia`; the parser now validates these separately.


## Frozen feature, signal and target

- Signal time: close of Binance BTCUSDT Spot UTC daily candle on date `d`.
- Pageview feature: `log1p(views[d-2]) - log1p(views[d-9])`. This is a same-weekday seven-calendar-day log change with a two-calendar-day embargo. Both exact daily values must exist after the documented zero-day reconstruction. No interpolation, forward-fill, alternative article, language, access type, agent type or lag substitution is allowed.
- Baseline predictors: `log1p` of prior-five-session downside semivariance, prior-twenty-session downside semivariance and prior-twenty-session total realized variance, plus prior-five-session and prior-twenty-session BTC close-to-close returns.
- Augmented model: the same frozen baseline plus the one pageview-growth feature. No additional features, interactions, thresholds, regime splits, model search or parameter tuning are permitted under this ID.
- Target: next-five-calendar-session BTC downside semivariance, `mean(min(r, 0)^2) * 10,000`, in percentage-points-squared units, forecast in `log1p` space.
- Event schedule: one signal every six calendar days. Five-session target windows must not overlap.
- Rolling training window: 104 prior events whose target end date is strictly earlier than the current signal date.
- Validation: signal dates `2019-01-01` through `2021-12-31`.
- Test: signal dates `2022-01-01` through `2026-11-20`.
- Minimum accepted sample: at least 60 validation and 100 test forecasts. If the frozen source/sample cannot yield these counts, close `INCONCLUSIVE/INFEASIBLE`; do not move the split or shorten the training window.

## Frozen model and decision rule

- Baseline and augmented forecasts use the repository's standardized, ridge-stabilized OLS predictor. Scaling and fitting use training observations only.
- Primary metric: RMSE in `log1p` downside-semivariance space. MAE is descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four events, fixed seed `20261126`.
- **PROMISING FORECAST SCREEN:** both validation and test RMSE improve and the paired test squared-loss 95% lower confidence bound is strictly above zero.
- **REJECTED:** both validation and test RMSE worsen and the paired test squared-loss 95% upper confidence bound is strictly below zero.
- **INCONCLUSIVE:** every other result, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale/incomplete sources or failed implementation gates.
- A promising result remains forecast-only. It is not independent validation, a tradable strategy, causal evidence or a live-trading signal.

## Implementation acceptance

- Source parser tests cover the official response envelope, exact project/article/access/agent dimensions, daily UTC timestamps, zero-view omissions, duplicates, malformed values, out-of-range rows and invalid counts.
- Coverage tests prove chunk boundaries are inclusive, non-overlapping and complete; a single documented omitted zero-view day is reconstructed as zero, while longer gaps fail closed.
- Timing tests prove the feature uses only `d-2` and `d-9`, the target begins after signal date `d`, target windows do not overlap and missing required pageview observations are not filled.
- Walk-forward tests prove the 104-event fully matured training requirement, chronological validation/test split and sample-count gates.
- Decision-rule, bootstrap, report/manifest and idempotent registry/preregistration update tests pass.
- The complete research workflow must compile and run its model-specific suite plus the repository workflow-admission regression suite before empirical source retrieval.
- Record the triggering commit SHA, pageview response digests, Binance archive checksums, report and manifest.

## Limitations and safety

- Wikipedia pageviews are a proxy for public interest, not investor-specific attention, search volume, sentiment or order flow.
- Pageview counts may be influenced by news coverage, article edits, platform changes, access-method composition and non-investor activity.
- `agent=user` follows Wikimedia's documented traffic classification; it does not prove every remaining request is a human investor.
- The two-day embargo is conservative operational timing, not proof of historical point-in-time availability or absence of later data corrections.
- The forecast test is observational and cannot establish causality.
- Paper research only. No live orders, capital deployment, paid data or private exchange credentials.
