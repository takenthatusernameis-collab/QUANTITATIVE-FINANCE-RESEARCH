# Bitcoin blockspace fee-rate source-feasibility session

**Session time:** 2026-11-27T13:55:51Z  
**Initial main HEAD:** `f7515df575f60565c193528412bcfdb58f4dc88c`

## 1. Initial repository reconciliation

- Re-read the current README, repository overview, active queue, hypothesis registry, latest session reports, recent commits, branches, pull requests, issues, and recent GitHub Actions runs.
- No open pull requests, no open standalone issues, and no active Actions executions were found at initial inspection.
- The current mainline already contains the November 27 ETF-relative-flow experiment and the earlier taker-absorption real-data experiment. The daily real-data backtest minimum was therefore already met; this session does not claim another backtest or count synthetic tests as empirical research.
- Compared the remaining historical branches against main. The mining-difficulty branch contains a closed, unadmitted draft and its closure validation; it was not reopened, merged, dispatched, or treated as an active hypothesis. Other diverged branches are historical snapshots, not adopted as current workstreams.

## 2. Candidate selection and economic distinction

Selected a demand-side blockspace-price hypothesis. A higher upper-quartile transaction feerate can reflect stronger willingness to pay for scarce settlement capacity. This is distinct from the closed mining-difficulty proposal: difficulty is a supply-side retarget/hashrate proxy; fee rates measure the price of blockspace. It is also distinct from the already tested exchange funding, ETF flow, stablecoin supply, Wikipedia attention, and macro predictors.

Adjacent literature:
- Ilk et al. (2021), *MIS Quarterly*, studies the supply/demand structure of Bitcoin transaction fees.
- Brown, Chiu and Koeppl (2022), Bank of Canada Staff Working Paper 2022-2, studies congestion and price effects on Bitcoin fees.
- A 2026 *Journal of Financial Stability* paper studies a Bitcoin capacity shock and related mempool/fee-market responses.

These works motivate the mechanism but do not validate this particular lagged predictor or downside-semivariance target.

## 3. Frozen admission and timebox

Created preregistration `QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01` before model implementation or performance-result inspection.

- Difficulty: MEDIUM.
- Maximum substantive cycles: 4.
- Timebox start: 2026-11-27T13:55:51Z.
- Hard implementation deadline: 2026-11-30T13:55:51Z.
- Hard final research-conclusion deadline: 2026-12-02T13:55:51Z.

The preregistration freezes one feature: seven-calendar-day change in the log of the daily median of the two 12-hour-bin averages of block-level p75 feerates, with a one-full-UTC-day embargo. The target is next-five-UTC-day BTC downside semivariance, with six-day-spaced non-overlapping events. It also freezes the baseline, chronological validation/test windows, minimum sample sizes, walk-forward estimator, bootstrap design, decision thresholds, and infeasibility rule.

## 4. First source-preflight evidence and schema correction

The first corrected-workflow source-preflight run was [46013134908](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46013134908). It completed successfully and made exactly one read-only GET:

- HTTP 200; no payment; zero retries.
- 319,519 response bytes; SHA-256 `ae6bad8494d4c06a41105e512ef536007eb56ac1fc3710f181f528fa856230d1`.
- 2,193 rows across 1,097 raw UTC dates.
- Raw first timestamp: 2023-11-27T18:50:20Z.
- Raw last timestamp: 2026-11-27T12:51:46Z.
- Exact expected fields were present, including `avgFee_75`.

A deeper inspection of the pinned Mempool implementation found an important source-semantics detail:
- `mining.ts` selects a 43,200-second divisor for a three-year history.
- `BlocksRepository.ts` groups by `UNIX_TIMESTAMP(blockTimestamp) DIV div` and averages each block's fee-span percentiles inside each bin.
- The response is therefore two 12-hour aggregates per complete UTC date, not individual per-block observations.
- The first date is partial because the rolling window starts at 18:50 UTC; the current final date is partial because the response ends at 12:51 UTC.

The first preflight code counted both boundary dates as complete. That coverage result is superseded and is not accepted. The preregistration has been amended before any model implementation: the feature is the daily median of the two 12-hour-bin p75 averages; the first and last raw dates are excluded; every included date must contain one bin in each UTC half-day; and at least 900 contiguous completed dates must remain.

Implementation references:
- [Mempool 12-hour range selection](https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/api/mining/mining.ts#L785-L799)
- [Mempool fee-rate aggregation query](https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/repositories/BlocksRepository.ts#L901-L926)

## 5. Engineering and CI

- Added the preregistration and a one-request, read-only source-preflight module.
- Added deterministic schema, 12-hour-bin, UTC-boundary, coverage, staleness, and no-retry tests.
- Added a source-only GitHub Actions workflow with read-only repository permissions, immutable triggering-commit checkout, and a source-manifest artifact.
- Registered the preflight workflow as non-research in the admission guard and extended guard CI to compile and test it.
- The first test run found a stale-data fixture that reached the 900-date gate before the staleness gate. The fixture was corrected without changing the source acceptance rule.
- The corrected admission guard and closed-draft regression workflows passed. The first live preflight passed HTTP/schema checks, but its boundary-day coverage is superseded pending the corrected rerun.

No model implementation, model fit, holdout inspection, backtest, raw-data persistence, paid API call, or live-trading action occurred in this cycle.

## 6. Next gate

Run the corrected source preflight once. It must:
- exclude the first and last raw UTC dates;
- verify exactly two 12-hour bins per included date, one in each half-day;
- verify at least 900 contiguous completed dates;
- verify the latest completed date is one to three days stale;
- retain one GET, zero retries, no payment, and no raw observations saved.

If it passes, proceed to Cycle 2. If not, close this identity as `INCONCLUSIVE/INFEASIBLE`; do not switch endpoint or feature.

## 7. Research disposition at this checkpoint

`SOURCE_PREFLIGHT_CORRECTION_PENDING`. The source endpoint and field schema are verified, but complete-day coverage has not yet been accepted. This is not an empirical performance result, not a GO/NO-GO decision, and not a tradable strategy.
