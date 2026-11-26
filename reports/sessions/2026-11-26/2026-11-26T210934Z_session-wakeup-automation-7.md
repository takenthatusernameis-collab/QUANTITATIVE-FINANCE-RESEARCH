# Wake-up session — research-factory audit and Wikipedia-attention admission

- **Session:** 2026-11-26T210934Z
- **Current main before this admission:** 7f9ff787355be1cdb9dd87708e8db6bc5c40e3dc
- **Research objective:** continue the already-admitted Bitcoin public-attention hypothesis after its source-feasibility gate passed.
- **Daily research KPI:** MET before this additional study by distinct real-data backtests on 2026-11-26, including MEXC BTC funding run 45850573983 and DeFiLlama stablecoin-supply run 45855398478. This additional hypothesis is not needed to manufacture activity.
- **Active hypothesis:** QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01.
- **Preregistration:** LOW difficulty, two substantive cycles maximum; source preflight is the first cycle. Implementation deadline 2026-11-27T19:02:30Z; final research-conclusion deadline 2026-11-28T19:02:30Z.
- **Verified source feasibility:** Wikimedia run 45881600522 passed with 3,381 daily user-pageview observations from 2017-08-17 through 2026-11-18, zero omitted dates, and a preserved combined response digest. Binance BTCUSDT was confirmed as an active Spot market. The preflight did not run a backtest.
- **Implementation admitted:** add the frozen lagged pageview feature to the existing BTC downside-semivariance walk-forward design; retain the five baseline risk/momentum predictors, two-day embargo, six-day non-overlapping event schedule, 104 fully matured training events, fixed 2019-2021 validation and 2022-11-20 test cutoff, minimum sample gates and deterministic paired-loss bootstrap.
- **Security and integrity:** use only the immutable triggering commit, official public sources, checksummed Binance Vision archives and sequential Wikimedia requests. No raw observations, secrets, paid data, live orders or capital deployment.
- **Tests:** model-specific parser/calendar/timing/event/walk-forward/decision/bootstrap/idempotency tests and the repository admission regression suite run before empirical retrieval.
- **Research output at commit time:** implementation and atomic admission only; the real-data backtest result remains pending until the Actions run and its persisted report/manifest are inspected.
- **Next:** verify the admitted workflow run, its source commit, deterministic tests, source coverage, forecast metrics, paired-loss interval, registry/preregistration update and artifact hashes. If a source or implementation attempt fails, preserve FEASIBILITY_CHECKED rather than misclassifying the hypothesis as a performance NO-GO.

## Completed empirical result

- **Backtest run:** [45898030626](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45898030626), source commit b3eca60343485c62b931c312c4148d9d8125384e.
- **Final hypothesis status:** INCONCLUSIVE. The preregistered minimum samples were met: 159 validation forecasts and 298 test forecasts.
- **Validation RMSE improvement:** -1.5188%; the augmented model was worse than the frozen baseline.
- **Test RMSE improvement:** -0.9141%; the augmented model was also worse than the frozen baseline.
- **Paired test-loss bootstrap:** 2,000 circular-block replications, four-event blocks, seed 20261126; 95% interval [-0.035550, 0.008245] for baseline-minus-augmented squared loss. It crosses zero, so the frozen rejection rule is not met.
- **Wikimedia:** 3,381 daily observations, 38 sequential chunks, 2017-08-17 through 2026-11-18, no omitted dates; combined response SHA-256 b1bc21a94749fa1775ed5a3482e8076734bcfff58a729a75da29c1f6d4023b60.
- **Binance:** 3,388 complete BTCUSDT Spot daily candles, 2017-08-17 through 2026-11-25, 136 verified archives; archive-manifest SHA-256 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe.
- **Interpretation:** the frozen attention feature did not improve either RMSE sample, but the paired uncertainty interval includes zero. This is INCONCLUSIVE, not a statistically established rejection. No causal, trading or deployment claim is supported.
- **No retuning:** the two-cycle LOW timebox has been used; do not tune this hypothesis on the same sample or rerun merely to seek a different outcome.

## Persistence repair

- The research/data step completed and emitted the report and full manifest, but the workflow's persistence step failed because its shell git-add command contained an unmatched trailing quote.
- The exact report and manifest were recovered from the immutable run log and are being committed without rerunning or changing the empirical result.
- The workflow shell quoting is corrected and a regression assertion is added. The workflow repair commit is unmarked, so it cannot re-admit this hypothesis.
