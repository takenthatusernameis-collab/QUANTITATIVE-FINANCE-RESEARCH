# Bitcoin blockspace fee-rate source-feasibility session

**Session time:** 2026-11-27T13:55:51Z  
**Initial main HEAD:** `f7515df575f60565c193528412bcfdb58f4dc88c`  
**Final source-preflight commit:** `a8657aef1b75b5fad371d310442c7834dbf2a9bb`

## 1. Initial repository reconciliation

- Re-read the current README, hypothesis registry, latest session reports, recent commits, branches, pull requests, issues, and recent GitHub Actions runs.
- No open pull requests, no open standalone issues, and no active Actions executions were found at initial inspection.
- The current mainline already contains the November 27 ETF-relative-flow experiment and the earlier taker-absorption real-data experiment. The daily real-data backtest minimum was therefore already met; this session does not claim another backtest or count synthetic tests as empirical research.
- Compared remaining historical branches against main. The mining-difficulty branch contains a closed, unadmitted draft and its closure validation; it was not reopened, merged, dispatched, or treated as an active hypothesis. Other diverged branches are historical snapshots, not adopted as current workstreams.

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

## 4. Source semantics and corrected preflight

The Mempool.space public API endpoint `/api/v1/mining/blocks/fee-rates/3y` was verified with one read-only request. The first run revealed that the source is 12-hour-binned, not a row-per-block history. Inspection of the pinned implementation established:
- the three-year range uses a 43,200-second grouping interval;
- the SQL groups by `UNIX_TIMESTAMP(blockTimestamp) DIV div`;
- `avgFee_75` is the mean of underlying block p75 fee-rate values inside each 12-hour bin;
- the API timestamp is the average timestamp of the bin's blocks.

The feature was clarified before any model implementation: daily median of the two 12-hour-bin `avgFee_75` averages. The first and last raw UTC dates are partial rolling-window boundaries and are excluded. Every included day must have exactly two bins, one in each half-day.

<badge color="success">Source accepted</badge>

**Final source-preflight run:** [46013880038](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46013880038)

- HTTP 200; exactly one GET; zero retries; no payment.
- 2,193 raw 12-hour rows across 1,097 raw UTC dates.
- First and last partial dates excluded: 2023-11-27 and 2026-11-27.
- 1,095 contiguous completed UTC dates accepted: 2023-11-28 through 2026-11-26.
- Exactly two 12-hour bins per included date.
- Latest completed date one calendar day stale.
- Response size: 319,519 bytes.
- Raw response SHA-256: `0709dcedb6270446fecaebc0dfaac1957a0031f6bceca08e66cdeef99a317cf4`.
- No raw observations were saved; the manifest contains schema, coverage, summary statistics and the response hash only.

**Durable evidence**
- [Committed preflight manifest](../reports/generated/btc-blockspace-fee-rate-source-preflight/46013880038-attempt-1/preflight.json)
- [Actions artifact 15205116653](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46013880038/artifacts/15205116653)
- Artifact ZIP SHA-256: `85fd006ef335792a02258fb562d3b387a89d295f3007c38c9fa5a87d8680d5fd`; 1,172 bytes; 30-day retention.
- The manifest is committed to main so the evidence remains available after the Actions artifact expires.

Implementation references:
- [Mempool 12-hour range selection](https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/api/mining/mining.ts#L785-L799)
- [Mempool fee-rate aggregation query](https://github.com/mempool/mempool/blob/f2d4384575c1dd8450afa228cdb8c93840a434f0/backend/src/repositories/BlocksRepository.ts#L901-L926)

## 5. Engineering and CI

- Added the preregistration, one-request source-preflight module, and deterministic regression suite.
- Added a source-only GitHub Actions workflow with read-only repository permissions, immutable triggering-commit checkout, and a source-manifest artifact.
- Registered the preflight workflow as non-research in the admission guard and extended guard CI to compile and test it.
- The initial CI exposed two test-fixture/Markdown-escaping issues. Both were corrected with ordinary unmarked repair commits; no expensive backtest was triggered.
- Final source-preflight deterministic suite: 13 tests passed.
- Final workflow-admission guard: passed.
- The closed mining-difficulty draft closure regression workflow also passed; that draft remains closed and unadmitted.

No model implementation, model fit, holdout inspection, backtest, raw-data persistence, paid API call, or live-trading action occurred in this cycle.

## 6. Next gate: Cycle 2

Implement the already frozen model and deterministic tests before the implementation deadline, 2026-11-30T13:55:51Z.

- Reuse the accepted Binance Vision BTCUSDT 1d UTC source evidence in `reports/generated/taker-absorption-btc-downside/45926394994-attempt-1/manifest.json`.
- Use the accepted Mempool 12-hour-bin schema and one-day embargo; do not change the p75 feature, baseline, target, sample split, or decision rule.
- Only after deterministic validation should the single real-data backtest be run.
- Final independent audit and disposition are due by 2026-12-02T13:55:51Z.

## 7. Research disposition at this checkpoint

`SOURCE_ACCEPTED_IMPLEMENTATION_PENDING`. The source and coverage gates passed. No empirical model-performance conclusion exists yet; no GO/NO-GO decision or live-trading recommendation is warranted.
