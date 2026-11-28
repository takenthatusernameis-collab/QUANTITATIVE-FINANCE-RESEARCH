# ETH validator queue source feasibility and point-in-time review

## Research disposition

The bounded CryptoKeyhole/Binance source-only preflight **PASSED** on [run 46103698530](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103698530). The candidate remains **IDEA / NOT ADMITTED** because point-in-time availability is not yet established. No raw observations were retained, no model was fitted and no backtest was run.

## Source-feasibility results

- CryptoKeyhole entry and exit queue components each contained 2,187 final daily observations, plus one non-final tail observation. Both achieved 100% coverage across 2,139 expected dates from 2020-12-20 through 2026-10-28.
- The API catalog initially returned BTC even when asked for the ETH metric. The documented id-inferred route also returned BTC; the explicit `asset=ETH` route returned the correct catalog. The catalog declared the exact metric `eth.ValidatorQueueWait` in days.
- The series response supplied empty component-level unit fields. The implementation now inherits units only from the validated catalog record for the exact same metric ID, rejects conflicting explicit units, records unit provenance and preserves component-shape metadata before validation.
- Binance ETHUSDT daily close coverage passed 76 checksum-verified archives (71 monthly plus five daily), producing 2,166 rows from 2020-12-01 through 2026-11-05 with no missing dates.
- The frozen schedule had 183 validation origins and 111 test origins, 63–100 prior training events and 100% source coverage. The test period contained 21 pre-Pectra and 90 post-Pectra origins; keep these regimes distinct in any later analysis.

The source-only result is not an empirical forecast result. The 2026-11-28 daily real-data backtest minimum had already been met by MEXC funding-dispersion / BTC realized-variance run [46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442).

## Independent point-in-time source assessment

Reviewed the public [ValidatorQueue.com repository](https://github.com/etheralpha/validatorqueue-com):

- `historical_data.json` contains 1,243 unique daily first-read snapshots from 2023-05-21 through 2026-10-25, with no duplicates and five gaps totaling 11 missing dates.
- The updater appends only the first successful reading for each UTC date. The corresponding Git commit timestamp is a conservative upper bound on when that snapshot became public; the JSON date alone is not a publication timestamp.
- The README documents a Pectra scaling defect for 2025-05-07 through 2025-05-21. Excluding those 15 rows, and using the existing six-day origin grid, five-day target and 60-event warm-up, the source supports only 39 validation and 107 test origins (21 pre-Pectra and 86 post-Pectra). It therefore cannot replace the full 100/100 non-overlapping source design.
- `historical_conversion_data.json` contains 482 rows and eight gaps totaling 54 missing days, so it cannot be treated as a complete correction ledger.
- The latest successful historical-data update is 2026-10-25. The scheduled update workflow still runs every three hours, but [run 46101369413](https://github.com/etheralpha/validatorqueue-com/actions/runs/46101369413) failed on 2026-11-28 because Beaconcha.in returned HTTP 429 and reported API rate-limit exhaustion. Do not purchase an upgraded plan or use credentials without authorization.

The archive is a useful partial point-in-time cross-check, not a complete replacement.

## Alternative reconstruction architecture

The community-maintained [Ethereum history-endpoints registry](https://github.com/eth-clients/history-endpoints) lists public mainnet Beacon Chain `.era` mirrors, including Nimbus. The [Era format specification](https://github.com/eth-clients/e2store-format-specs/blob/main/formats/era.md) describes a BeaconState snapshot plus the blocks leading to it for each era; mainnet eras span 8,192 slots (about 27.3 hours). In principle, a verified state plus replay of the blocks within the era can reconstruct daily validator registry/balance and activation/exit queue state without relying on a current-vintage chart series.

This is only a candidate architecture: the endpoint registry explicitly warns that it is community-maintained and individual mirrors may be stale or incorrect. No archive file was downloaded or verified in this session.

## CI and implementation status

- The source preflight and unit-fallback implementation passed the live source run above.
- The expanded 18-test run [46104132708](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46104132708) was pending at the final check.
- Admission run [46103714337](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103714337) found one incorrect expected-error string in a new regression test; the fail-closed implementation was correct. The assertion was corrected in commit `ce554b24`. Final admission reruns [46104132569](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46104132569) and [46104241618](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46104241618) were queued.
- The README now records the source pass, current-vintage limitation, partial PIT archive assessment and next decision.

## Next bounded action

Perform a read-only two-era pilot using the public Nimbus mainnet `.era` mirror:

1. Select one known pre-Pectra era and one post-Pectra era.
2. Verify file checksums where published, era structure, canonical state roots and state/slot alignment.
3. Load the BeaconState and replay only the blocks needed to reach selected daily UTC boundaries.
4. Reconstruct balance-aware activation and exit queue metrics using the correct pre-/post-Pectra churn rules.
5. Compare the reconstructed values against CryptoKeyhole and ValidatorQueue.com on matching timestamps, with explicit timestamp alignment and known-defect exclusions.
6. Measure archive bytes, download cost, replay cost and missing-era risk before considering any full-period reconstruction.

If the pilot is not feasible with public data, either preregister a clearly labelled current-vintage exploratory association or close/reformulate the candidate. Do not claim a tradable point-in-time forecast and do not begin model fitting before that decision and a separate preregistration/timebox.
