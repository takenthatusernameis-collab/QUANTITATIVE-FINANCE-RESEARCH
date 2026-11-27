# Bitcoin blockspace fee-rate source-feasibility session

**Session time:** 2026-11-27T13:55:51Z  
**Initial main HEAD:** `f7515df575f60565c193528412bcfdb58f4dc88c`

## 1. Initial repository reconciliation

- Re-read the current README, repository overview, active queue, hypothesis registry, latest session reports, recent commits, branches, pull requests, issues, and recent GitHub Actions runs.
- No open pull requests, no open standalone issues, and no active Actions executions were found at inspection.
- The current mainline already contains the November 27 ETF-relative-flow experiment and the earlier taker-absorption real-data experiment. The daily real-data backtest minimum was therefore already met; this session does not claim another backtest or count synthetic tests as empirical research.
- Compared the remaining historical branches against main. The mining-difficulty branch contains a closed, unadmitted draft and its closure validation; it was not reopened, merged, dispatched, or treated as an active hypothesis. Other diverged branches are historical snapshots, not adopted as current workstreams.

## 2. Candidate selection

Selected a demand-side blockspace-price hypothesis: the daily median of Bitcoin block-level 75th-percentile feerates may contain incremental information about future BTC downside semivariance.

This is materially distinct from the closed mining-difficulty proposal. Difficulty is a supply-side retarget/hashrate proxy; block feerates measure the price users pay to compete for scarce blockspace. It is also distinct from the already tested exchange funding, ETF flow, stablecoin supply, Wikipedia attention, and macro predictors.

The Mempool.space API documentation identifies the `/api/v1/mining/blocks/fee-rates/:timePeriod` endpoint, supports a trailing three-year window, describes oldest-to-newest historical block-feerate percentiles, and warns that rate limits are enforced. The project's own chart implementation maps `avgFee_75` to the 75th-percentile series and labels the displayed unit as sat/vB. No Mempool request was made during the first preflight attempt: deterministic tests correctly blocked source retrieval after one stale-data fixture asserted the wrong validation order. The fixture has been widened to retain the minimum history while exercising the staleness gate; the next run will be the first live API request.

Adjacent literature:
- Ilk et al. (2021), *MIS Quarterly*, studies the supply/demand structure of Bitcoin transaction fees.
- Brown, Chiu and Koeppl (2022), Bank of Canada Staff Working Paper 2022-2, studies congestion and price effects on Bitcoin fees.
- A 2026 *Journal of Financial Stability* paper studies a Bitcoin capacity shock and related mempool/fee-market responses.

These works motivate the mechanism but do not validate this particular lagged predictor or downside-semivariance target.

## 3. Frozen admission and timebox

Created preregistration `QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01` before model implementation or empirical-result inspection.

- Difficulty: MEDIUM.
- Maximum substantive cycles: 4.
- Timebox start: 2026-11-27T13:55:51Z.
- Hard implementation deadline: 2026-11-30T13:55:51Z.
- Hard final research-conclusion deadline: 2026-12-02T13:55:51Z.

The preregistration freezes one feature: seven-calendar-day change in the log of the daily median of per-block `avgFee_75`, with a one-full-UTC-day embargo. The target is next-five-UTC-day BTC downside semivariance, with six-day-spaced non-overlapping events. It also freezes the baseline, chronological validation/test windows, minimum sample sizes, walk-forward estimator, bootstrap design, decision thresholds, and infeasibility rule.

## 4. Engineering changes

- Added a one-request, read-only Mempool source-preflight module.
- Added deterministic schema, timestamp, coverage, staleness, and no-retry tests.
- Added a source-only GitHub Actions workflow with read-only repository permissions, immutable triggering-commit checkout, and a source-manifest artifact.
- Registered the preflight workflow as a non-research workflow in the admission guard and extended the guard CI to compile and test it.
- Added a `SOURCE_PREFLIGHT_PENDING` registry entry.
- No model implementation, model fit, holdout inspection, backtest, raw-data persistence, paid API call, or live-trading action occurred in this cycle.

## 5. First deterministic-run correction

The first post-commit CI exposed a test-fixture issue, not a source or model issue: the stale-series fixture removed six dates and therefore failed the earlier 900-date minimum before reaching the staleness assertion. No network request was made because the workflow is ordered to run deterministic tests first. The fixture was corrected to preserve the minimum coverage while remaining stale. The admission guard and the separate closed-draft regression suite passed on the corrected commit; the source-preflight rerun remains pending.

## 6. Next gate

Inspect the source-preflight workflow run and its artifact.

- If the exact `avgFee_75` schema, 900-day minimum coverage, recency, and UTC timestamp checks pass without payment or retries, proceed to Cycle 2.
- If the endpoint requires payment, returns HTTP 429, lacks the frozen field, or fails coverage, do not switch endpoint or feature under this identity. Record the failure and close as `INCONCLUSIVE/INFEASIBLE`.
- Do not fit a model before source acceptance and deterministic model tests.

## 7. Research disposition at this checkpoint

`SOURCE_PREFLIGHT_PENDING`. This is not an empirical performance result, not a GO/NO-GO decision, and not a tradable strategy.
