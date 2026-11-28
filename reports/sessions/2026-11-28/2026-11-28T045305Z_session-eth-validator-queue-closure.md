# Wake-up session — Ethereum validator queue source audit and closure

**Date:** 2026-11-28  
**Research disposition:** ETH validator-queue asymmetry closed INCONCLUSIVE/INFEASIBLE (source timing); no model fit or backtest.

## Research output

Completed a full Git-history reconstruction and cross-source concordance audit for the unadmitted Ethereum validator-queue hypothesis. The audit was source-only. It did not fit a model or inspect strategy performance.

The key correction is that Git committer timestamps are not server-side first-publication timestamps. The previous working assumption that they were a conservative public-availability upper bound was not supportable. A commit may be pushed after its committer timestamp, and the timestamp is mutable metadata. The reconstructed chronology is therefore an unverified proxy, not point-in-time evidence.

## Verified findings

- CryptoKeyhole's free daily queue history is current-vintage/delayed; first-published vintages require API & Team.
- Binance ETHUSDT daily data passed source preflight: 2,166 rows, 2020-12-01–2026-11-05, 76 checksum-verified archives, no missing dates.
- ValidatorQueue's pinned Git history reconciles all 1,243 current daily rows to 1,237 commits. The latest snapshot matches the current wait values; no row dates were removed; 16 wait-value revisions occurred across 16 dates and queue-balance fields changed in 707 snapshot revisions.
- The archive has 11 missing calendar days across five gaps. The documented 15-day Pectra mis-scaling interval was excluded from cross-source concordance.
- Clean current-vintage overlap is 1,228 days. Entry-wait, exit-wait and log-asymmetry Pearson correlations are 0.9985, 0.9865 and 0.9791 respectively. Exit-wait correlation changes from 0.7132 pre-Pectra to 0.9839 post-Pectra.
- The frozen 6-day / 60-event timestamp-proxy schedule yields 37 validation and 107 test origins. A 5-day / 15-event warm-up grid reaches 101 / 129 only under the same unverified proxy; it was not adopted.

## Engineering changes

Commit [37ac272](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/37ac272d995c79affcf0ddd858b38df889fb3d12):

- Corrected the deterministic same-day revision fixture that had incorrectly placed the later revision on the previous date.
- Made vintage reconstruction robust to unsorted Git snapshots and made `value_as_of` select the latest eligible timestamp.
- Pinned the external ValidatorQueue checkout and raw history URL to commit `6d90783883b84129db6f17b3d454f702dc1f8f1f`; the loader now asserts the expected SHA.
- Removed the false claim that Git commit time verifies public availability. The manifest now explicitly marks public availability and PIT acceptance false.
- Added deterministic source-pin, timestamp-order and PIT-gate regression coverage; added an admission-guard test for immutable external checkout.

## Verification

- Source-only Git-history audit [#46109045788](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045788): success; 13 deterministic tests passed; complete manifest/report persisted in commit [18a96fc](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/18a96fc87c8626a42adce59f7a824a1440dc0e9f).
- Admission guard [#46109045736](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045736): success; 70 tests passed.
- Unadmitted-draft closure guard [#46109045810](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46109045810): success.

## Disposition

Closed as INCONCLUSIVE/INFEASIBLE because historical public availability cannot be established from the available sources and the frozen timestamp-proxy schedule fails the validation sample minimum. This is not a performance NO-GO. A current-vintage or prospective study requires a new hypothesis ID and preregistration/timebox.

The 2026-11-28 daily real-data backtest KPI was already met by MEXC funding dispersion / BTC realized variance [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). No additional backtest was launched to inflate the quota.

## Boundaries and next step

No raw market observations were persisted, no paid data was acquired, no Nimbus era files were downloaded, and no live orders or capital deployment occurred.

Next wake-up: discover a distinct hypothesis with source-side publication/vintage metadata and adequate historical coverage. Do not reopen the closed validator-queue identity.
