# Kraken PI cap-anomaly independent price and terms validation

**Status:** COMPLETED — bounded diagnostic only, 2026-11-23 05:10 UTC  
**Priority:** P1 data-integrity / independent-provider cross-check  
**Research gate:** all four Kraken funding series remain `PROVISIONAL_NOT_ACCEPTED`; no backtest or cross-venue merge.

## Objective

Independently investigate the nine Kraken inverse PI funding-rate rows that exceed the currently documented ±0.25% hourly relative-rate cap. Determine whether the rate fields are internally coherent, whether the implied index levels are plausible against an independent spot source, and whether authoritative historical terms explain the cap discrepancy.

This is a bounded diagnostic, not permission to accept funding rows or run a strategy backtest.

## Completed evidence to reuse

- Full-row API cap census: [run 45100276868](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868), artifact [14784609201](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868/artifacts/14784609201).
- Bounded exception-context audit: [run 45102646438](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438), manifest-only artifact [14786345447](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438/artifacts/14786345447), ZIP SHA-256 `56923db469f03d70285999684af1c72c90c9e65d2d9423d63b92543b557e85d3`.
- All 34,256 API rows were assessed. PF_XBTUSD and PF_ETHUSD had zero cap exceptions; PI_XBTUSD had one; PI_ETHUSD had eight.
- The latest context manifest retains only each exception and at most one preceding/following row, including both `fundingRate` and `relativeFundingRate`. No raw API history or archive was uploaded; no historical ZIP was re-downloaded.
- Code/test commits: [9c9beaa](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9c9beaa75455c0fab7e7c5885ce1367332e3723e) and [6ba9616](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/6ba961667adaafc08589dc4c93af453555eb16aa).
- CI [45102432282](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102432282) passed 199 deterministic tests and the synthetic plumbing smoke test.
- Queue guardian [45102678816](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102678816) enumerated 369 runs with enumeration complete, zero enforcement actions and zero errors.

## Exact cap exceptions and local pattern

| Symbol | Timestamp (UTC) | relativeFundingRate | fundingRate | Implied USD index level |
|---|---|---:|---:|---:|
| PI_XBTUSD | 2026-08-20 09:00 | +0.005 | 6.9906751384e-08 | 71,523.85 |
| PI_ETHUSD | 2026-08-20 07:00 | +0.005 | 2.211538036243e-06 | 2,260.87 |
| PI_ETHUSD | 2026-08-20 08:00 | +0.005 | 2.222143212686e-06 | 2,250.08 |
| PI_ETHUSD | 2026-08-20 11:00 | -0.003835161729166667 | -1.678422449722e-06 | 2,284.98 |
| PI_ETHUSD | 2026-10-29 09:00 | +0.003261576116071429 | 1.408176479305e-06 | 2,316.17 |
| PI_ETHUSD | 2026-10-30 13:00 | +0.003248896366666667 | 1.455794401876e-06 | 2,231.70 |
| PI_ETHUSD | 2026-10-30 14:00 | +0.005 | 2.249749152969e-06 | 2,222.47 |
| PI_ETHUSD | 2026-10-30 15:00 | +0.005 | 2.237907467002e-06 | 2,234.23 |
| PI_ETHUSD | 2026-10-30 16:00 | +0.005 | 2.248070031878e-06 | 2,224.13 |

The implied level is derived as `relativeFundingRate / fundingRate` from Kraken's inverse relationship `absolute_rate = relative_rate / index_spot_price`. It is a derived consistency diagnostic, **not** an independent price observation or proof of cap compliance.

Local sequence findings:
- PI_XBTUSD 2026-08-20 09:00 is isolated; 08:00 and 10:00 are within cap.
- PI_ETHUSD 2026-08-20 07:00 and 08:00 are consecutive +0.5% rows; 09:00 is within cap. The 11:00 negative exception is isolated between in-cap neighbors.
- PI_ETHUSD 2026-10-29 09:00 is isolated between in-cap neighbors.
- PI_ETHUSD 2026-10-30 13:00 and 14:00–16:00 form a consecutive out-of-cap sequence ending at the official inverse-contract settlement boundary.

The inverse specification currently documents ±0.25% per hour. The reviewed public parameter changelog contains no PI-specific funding-cap change, but absence from the public changelog is not proof that no unpublished or omitted parameter change occurred. August 20 anomalies are not delisting events. The October 30 timestamps overlap the delisting/settlement boundary, but API timestamp-to-accrual semantics remain unresolved.

Response hashes are preserved per exact symbol in the same manifest and joinable to exceptions by symbol:
- PF_XBTUSD: `6b7df2d3860f0b116b4b90482ac7c7f203fdf7bb5c43aaa090f00a3d55262340`
- PF_ETHUSD: `50ab8de1d6bd84626c448d5a7f933dacdcbd89d33a2fce676228e7a83b04bd44`
- PI_XBTUSD: `de1a8cfbadec23b563696de4a2c6ee5d8d404e7a5f423198ea39dac9b545b547`
- PI_ETHUSD: `7f781d0b37d4f695717f0a5092a9a7ce9b601bdbf2a29105663a96c432621907`

## Official delisting-settlement cross-check

Kraken's official delisting notice states that PI_ETHUSD settled at **$2,235.76**, using a 60-minute observation from 15:00 to 16:00 London time on 2026-10-30. The notice describes a volume-weighted, time-segmented TWAP with deviation safeguards against spot transactions on constituent exchanges. On that date London was on UTC.

The PI_ETHUSD API exception rows imply these index levels from `relativeFundingRate / fundingRate`:
- 13:00 UTC: $2,231.70 (0.1816% below settlement).
- 14:00 UTC: $2,222.47 (0.5944% below settlement).
- 15:00 UTC: $2,234.23 (0.0684% below settlement).
- 16:00 UTC: $2,224.13 (0.5202% below settlement).

The 15:00 implied level is close to the official settlement value, but the API row may label the start or end of a funding interval and Kraken's index need not equal the settlement TWAP. This is a useful plausibility clue, **not** proof of API timestamp semantics, cap validity or exact settlement-price identity. Compare it with independent spot candles and retain the basis/time uncertainty.

The inverse contract specification was last updated September 29, 2026 and explicitly states the ±0.25% hourly permissible range and the inverse absolute/relative-rate relationship. The public parameter changelog was last updated October 1, 2026, but its latest dated entry is September 4, 2025. It documents an instrument-specific PF_OGNUSD maximum relative funding-rate increase from 0.25% to 0.5% on October 1, 2023, then a reduction from 0.005 to 0.0025 on November 24, 2023. This proves instrument-specific funding-cap overrides have existed, but the reviewed changelog contains no PI_XBTUSD or PI_ETHUSD funding-cap change. It does not rule out an unpublished or omitted PI change.

Sources: [Kraken inverse Coin-M contract specifications](https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives), [Kraken delisting notice](https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings), and [Kraken derivatives parameters changelog](https://support.kraken.com/articles/13049711807636-derivatives-platform-parameters-changelog).

## Adaptive execution plan

1. **Inspect before dispatch.** Check the current default-branch head, open PR #2, matching comments/runs, provider policies, and any new official documentation. Do not repeat the cap census or archive download unchanged.
2. **Independent spot-price pilot — Coinbase first.** This is a narrow spot-index plausibility check, not a change to the funding-provider priority: the independent funding-source screen remains MEXC first, Bitget second, then Coinbase/Kraken and other verified venues. Use the public Coinbase Exchange candle endpoint for exact `BTC-USD` and `ETH-USD` windows surrounding the nine exception timestamps. Start with one known-active control and a bounded set of exception windows. Verify product identity, coverage, UTC bar boundaries, OHLCV invariants, duplicates and response provenance. The endpoint limits requests to 300 candles; request only the needed windows.
3. **Compare, do not force equality.** Compare the implied inverse index levels with the independent spot observations. Kraken's derivatives index may be a basket and the API timestamp may label a different boundary, so report basis differences and timing uncertainty. This cross-check can establish plausibility, not exact settlement or cap validity.
4. **Independent fallback.** If Coinbase coverage or semantics fail, test Kraken Spot historical candles or another lawful, independently verifiable source. Keep each venue separate and do not forward-fill.
5. **Historical terms investigation.** Search official dated inverse specifications, archived public parameter pages and the derivatives parameter changelog for any PI-specific funding-cap exception effective on 2026-08-20 and 2026-10-29/30. Use the documented PF_OGNUSD 0.25%→0.5%→0.25% change as proof that instrument-specific overrides are possible, not as evidence that PI inherited that exception. Do not infer a PI cap change from observed data.
6. **Resolve or fail closed.** If no authoritative evidence explains the nine exceptions, preserve them as rejected/unaccepted observations and keep the Kraken funding source provisional. Continue the independent funding-provider hierarchy as a separate venue experiment; do not merge it into Binance or Kraken.
7. **Preserve separate blockers.** Even if the cap discrepancy is explained, the API timestamp-to-accrual mapping and full payable-settlement population remain independent acceptance gates.

## Acceptance criteria

- All nine exception windows are compared against an independently sourced, exact-product spot series with timestamps, bar conventions and response hashes retained.
- Implied index versus external spot differences are quantified and interpreted without assuming the two indices are identical.
- Any historical PI cap change is supported by an authoritative, dated source; otherwise it remains unresolved.
- No clipping, interpolation, synthetic settlements, forward-fill, credentials, paid data, access-restriction bypass, trading or raw-data commit.
- Deterministic tests are added for any newly established mapping or rule; hosted CI passes.
- The report, README and active queue are updated with exact evidence and the next decision.

**Do not run a Kraken funding backtest, merge Kraken with Binance, or accept the nine exceptions while any cap, timestamp-semantic or event-population requirement remains unresolved.**


## Results — 2026-11-23

**Diagnostic completion:** [report](../reports/ETH-BTC-KRAKEN-PI-PRICE-VALIDATION-2026-11-23.md), [successful run 45116028859](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859), manifest-only artifact [14791133228](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859/artifacts/14791133228), artifact ZIP SHA-256 `0071722e55c0b9cb3f95548dcb36872753f5c71175f8ecef8ba6718372657ddc`.

- Four bounded Coinbase BTC-USD/ETH-USD windows returned 21 valid hourly candles. Product identity/status checks and both known-active positive controls passed. All nine exception timestamps had an exact-hour candle and complete t−1/t/t+1 windows; all nine implied levels fell inside their three-hour spot envelopes.
- Nearest three-hour Coinbase close absolute basis was 0.004889%–0.038044%, median 0.015975%. This is independent price-plausibility evidence only; it does not prove that Coinbase equals Kraken's index or establish the Kraken API timestamp.
- The first run [45115641203](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45115641203) failed closed on one out-of-window candle per request. The API end boundary was corrected to one second before the exclusive analysis bound and covered by a deterministic test in [commit 8420754](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8420754d5edb927b420c6ea5f4fd19ca0dbf4700). CI [45115907842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45115907842) passed 209 deterministic tests and synthetic smoke.
- The inverse specification dated 29 September 2026 states ±0.25% per hour, n=24 and next-period rate calculation over the current one-hour window. The public parameters changelog contains no PI-specific funding-cap change; it does demonstrate an instrument-specific PF_OGNUSD override in 2023. No authoritative pre-20-August PI cap snapshot was verified.
- The PI delisting notice's 15:00–16:00 London observation is compatible at a high level with CME CF ETHUSD_RR's one-hour, twelve five-minute partition methodology. The exact historical CME CF rate and Kraken's deviation safeguards were not reconstructed.
- Coinbase response hashes and selected candle summaries only were retained. No raw candle arrays or raw responses were retained/uploaded; no raw market data was committed.

**Decision:** this bounded diagnostic satisfies the task's price-comparison and public-terms-review scope, but does not resolve the nine cap exceptions. All four Kraken series remain PROVISIONAL_NOT_ACCEPTED. The historical PI cap, API timestamp-to-accrual mapping and complete payable-event population remain independent hard blockers. No backtest or cross-venue merge.

**Next task:** [Resolve Kraken PI cap exceptions, API timestamp semantics and settlement-population completeness](KRAKEN-PI-API-SEMANTICS-AND-SETTLEMENT-COMPLETENESS.md).
