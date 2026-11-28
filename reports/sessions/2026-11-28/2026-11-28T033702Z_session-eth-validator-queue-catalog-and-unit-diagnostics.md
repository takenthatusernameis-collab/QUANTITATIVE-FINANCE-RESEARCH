# ETH validator queue source preflight — catalog and unit diagnostics

## Decision

The Ethereum validator queue asymmetry candidate remains **IDEA / NOT ADMITTED**. No model fit or backtest was run. The two live preflight attempts reached the CryptoKeyhole series but exposed an API catalog-selection inconsistency and omitted component-unit fields. The parser and regression coverage have now been adapted without weakening unit validation.

## Live findings

1. The initial catalog request using `asset=ETH&ids=eth.ValidatorQueueWait` returned a BTC catalog, producing `Unexpected catalog asset: 'BTC'`.
2. The documented id-inferred request `/catalog?ids=eth.ValidatorQueueWait` also returned `asset=BTC`, although its metric list included `eth.ValidatorQueueWait`.
3. The materially different explicit-asset request `/catalog?asset=ETH` returned the ETH catalog. Its target metric was present with:
   - ID `eth.ValidatorQueueWait`;
   - unit `days`;
   - daily `24h` interval;
   - status `delayed`;
   - history start 2020-12-01 UTC and catalog history end 2026-11-28 UTC.
4. The series request returned 427,520 bytes, a CC BY 4.0 license Link header and no `X-CKH-Preview` header. The parser then rejected an empty component-level unit for `eth.ValidatorQueueWait.entry`, despite the validated catalog declaring the same metric in days.

The API documentation says catalog selection can infer an asset from the first requested metric ID, and its series schema describes component units as a property. The live response did not follow the inferred-asset behavior and supplied empty component units. The chart itself documents daily queue waits and the Pectra methodology break.

## Implemented corrections

- Added a bounded catalog fallback: first request by metric ID alone, then request the explicit ETH catalog. Every attempt records its URL, response hash, asset, metric IDs and validation result.
- Preserve OpenAPI and catalog evidence incrementally, rather than losing all partial evidence when a later validation fails.
- Record series metadata and component shape before validating the component values; no raw observations are copied into the manifest.
- If a component omits its unit, inherit the unit only from the already validated catalog entry for the exact same metric ID. An explicit conflicting parent unit is rejected; an explicit component unit still has to be in days.
- Record whether each component unit came from the component, series metric or validated catalog.
- Expanded the source-preflight regression suite to 18 tests, covering catalog fallback, partial-evidence retention, validated-unit inheritance, missing-unit fail-closed behavior, parent/catalog unit conflicts and series-shape diagnostics.

## Execution evidence

- Initial catalog-selection failure: [run 46103027218](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027218).
- First catalog fallback / series-unit failure: [run 46103428482](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103428482).
- Repeated unit failure with the catalog fallback tests passing: [run 46103452616](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103452616).
- Current code and 18-test source-preflight rerun: [run 46103714325](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103714325), **PENDING** at the final status check.
- Current admission-guard verification: [run 46103714337](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103714337), **QUEUED** at the final status check.
- Earlier workflow-wiring admission verification [run 46103027222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103027222) passed. The two earliest intermediate failures were caused by committing the new guard assertions before the workflow file they inspect existed; the later complete-state admission run passed.

## Research and governance boundaries

- No raw source observations were saved, no model was fitted and no backtest was run.
- The source preflight still must validate full queue coverage/finality, Binance ETHUSDT daily archive checksums and the frozen forecast schedule.
- CryptoKeyhole's free daily data is current-vintage. First-published historical vintages are an API & Team feature; a two-day lag does not establish historical point-in-time availability.
- Pectra changed the entry-queue definition/churn calculation on 2025-05-07. Exit queue waits are not a direct measure of ETH sales.
- The candidate remains unadmitted until the source preflight passes and a separate preregistration/timebox is frozen. A source failure is not a strategy-performance NO-GO.

The 2026-11-28 daily empirical-backtest KPI was already met by the MEXC funding-dispersion / BTC realized-variance backtest [run 46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442).

## Next action

Inspect run [46103714325](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103714325) and admission run [46103714337](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46103714337). If source preflight passes, verify the Binance archive population and schedule feasibility before deciding whether current-vintage data is acceptable for an explicitly exploratory forecast. If it fails, classify the exact source or coverage defect and move to a materially different data architecture or hypothesis. Do not start model work on the strength of catalog access alone.
