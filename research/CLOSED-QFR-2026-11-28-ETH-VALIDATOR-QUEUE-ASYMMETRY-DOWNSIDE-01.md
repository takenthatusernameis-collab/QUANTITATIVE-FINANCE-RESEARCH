# Closure — Ethereum validator queue asymmetry and ETH downside

**Hypothesis ID:** `QFR-2026-11-28-ETH-VALIDATOR-QUEUE-ASYMMETRY-DOWNSIDE-01`  
**Status:** `CLOSED — INCONCLUSIVE/INFEASIBLE`  
**Admission:** IDEA only; never admitted to model fitting or backtesting.  
**This is a source-feasibility closure, NOT a preregistration or performance rejection.**

## Reason for closure

The proposed feature was a strictly lagged `log1p(exit_wait_days) - log1p(entry_wait_days)` measure intended to add information about next-five-UTC-day ETH downside semivariance beyond recent downside risk, realized variance and momentum.

The source-only audit established that the free CryptoKeyhole history is current-vintage and delayed, with first-published vintages requiring API & Team. The alternative ValidatorQueue.com Git history reconstructs the exact sequence of committed file versions, but Git committer timestamps are not server-side first-publication timestamps. A commit can be pushed after its recorded commit time, and commit timestamps are mutable metadata. They therefore cannot establish that a value was publicly observable at a historical forecast origin.

Without verifiable publication-time evidence, the original point-in-time forecasting claim cannot be tested. The frozen timestamp-proxy schedule also yields only 37 validation and 107 test origins, below the 100/100 split minimum. This is a data-validity failure, not evidence that the proposed mechanism has no predictive value.

## Verified source and reconstruction results

### CryptoKeyhole and Binance

- CryptoKeyhole's free `eth.ValidatorQueueWait` API provides entry/exit queue wait components and is licensed CC BY 4.0, but its historical endpoint returns current-vintage/delayed values. First-published vintages require API & Team; no paid data was authorized.
- The authorized-runner source preflight [#46103698530](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103698530) passed. The two queue components each contained 2,187 final daily observations and full coverage across 2,139 expected dates (2020-12-20–2026-10-28), with one non-final tail point.
- Binance ETHUSDT Spot daily prices were represented by 2,166 rows (2020-12-01–2026-11-05) from 76 checksum-verified archives (71 monthly and five daily), with no missing dates.

### ValidatorQueue full Git-history audit

The source-only workflow [#46109045788](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045788) passed 13 deterministic tests, checked out the external repository at the pinned commit `6d90783883b84129db6f17b3d454f702dc1f8f1f`, and completed the full-history reconstruction.

- Current `historical_data.json`: 1,243 daily rows from 2023-05-21 through 2026-10-25; 11 missing calendar days across five gaps.
- Git history: 1,237 commits. The latest snapshot matches the current file's wait values, all 1,243 row dates map to the history, no dates were removed, and `mapping_complete=true`.
- Wait values were revised 16 times across 16 dates. Most revisions affect the first two weeks of the file in 2023; additional revisions occur on 2025-05-07 and 2025-05-22.
- Queue-balance fields changed in 707 snapshot revisions. These are not the wait-time feature itself, but demonstrate that the underlying history is not immutable.
- 1,234 of 1,243 first Git commit timestamps share the row's UTC date. The p95 first-commit timestamp delay is 4.395 hours; the maximum is 232.452 hours (9.685 days). These are commit-metadata diagnostics only.
- The pinned external workflow schedules updates every three hours and creates commits as `github-actions[bot]`. Five latest inspected `historical_data.json` commits were unsigned. This supports an automated-update interpretation but does not supply server-side push/first-publication times for the historical series.

### Cross-source concordance

After excluding the documented 15-day Pectra mis-scaling interval (2025-05-07–2025-05-21), 1,228 paired dates remain (2023-05-21–2026-10-25).

| Metric | Clean overlap |
|---|---:|
| Entry-wait Pearson correlation | 0.9985 |
| Exit-wait Pearson correlation | 0.9865 |
| Log-asymmetry Pearson correlation | 0.9791 |

Exit-wait correlation is regime-sensitive: 0.7132 pre-Pectra and 0.9839 post-Pectra. These are current-vintage cross-source consistency statistics. They do not prove independent ground truth, stable historical semantics or point-in-time availability.

## Schedule feasibility — diagnostic only

The frozen six-day / 60-event warm-up design yields 37 validation and 107 test origins under the Git committer-time proxy. The validation minimum of 100 is not met.

A non-overlapping five-day / 15-event warm-up grid yields 101 validation and 129 test origins under the same proxy. This alternative was not adopted: it changes the frozen warm-up design, and the proxy still does not establish public availability. Four-day and three-day schedules overlap the five-day target horizon and are invalid.

No timestamp-proxy origin is counted as PIT-accepted. The machine-readable manifest explicitly records `public_availability_verified=false` and `point_in_time_accepted=false`.

## Disposition and future work

Close this identity as **INCONCLUSIVE/INFEASIBLE due to source-timing limitations**. Do not interpret closure as a performance NO-GO, and do not reopen this hypothesis ID for a current-vintage backtest.

A current-vintage association or prospective data-capture study would be materially different. It requires a new hypothesis ID, explicit disclosure of current-vintage/revision risk, a frozen target and feature timing, and a preregistered timebox before substantive implementation or model fitting.

A possible future source-reconstruction route is selective Nimbus `.era` range retrieval with canonical state-root anchoring, slot alignment and deterministic replay. The full public archive is approximately terabyte-scale across about 1,923 eras. No range-read pilot, state-root validation or replay was performed in this session; do not assume feasibility.

## Reproducibility and boundaries

- Code/test/workflow repair: [commit 37ac272](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/37ac272d995c79affcf0ddd858b38df889fb3d12).
- Persisted audit evidence: [commit 18a96fc](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/18a96fc87c8626a42adce59f7a824a1440dc0e9f).
- Machine-readable manifest: [`pit_concordance.json`](../reports/generated/eth-validator-queue-pit-concordance/46109045788-attempt-1/pit_concordance.json).
- Audit report: [session report](../reports/sessions/2026-11-28/2026-11-28T045011Z_session-eth-validator-queue-pit-concordance-46109045788.md).
- Admission guard [#46109045736](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045736) passed 70 tests. The unrelated unadmitted-draft closure guard [#46109045810](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045810) also passed.
- The 2026-11-28 daily real-data backtest KPI was already met by MEXC funding dispersion / BTC realized variance [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This source-only audit did not count toward that KPI.
- No model fit, backtest, raw market-data persistence, paid data acquisition, live orders or capital deployment occurred.
