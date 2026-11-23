# Kraken PI cap-anomaly independent price and terms validation

**Status:** PENDING — 2026-11-23 02:52 UTC  
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

## Adaptive execution plan

1. **Inspect before dispatch.** Check the current default-branch head, open PR #2, matching comments/runs, provider policies, and any new official documentation. Do not repeat the cap census or archive download unchanged.
2. **Independent spot-price pilot — Coinbase first.** Use the public Coinbase Exchange candle endpoint for exact `BTC-USD` and `ETH-USD` windows surrounding the nine exception timestamps. Start with one known-active control and a bounded set of exception windows. Verify product identity, coverage, UTC bar boundaries, OHLCV invariants, duplicates and response provenance. The endpoint limits requests to 300 candles; request only the needed windows.
3. **Compare, do not force equality.** Compare the implied inverse index levels with the independent spot observations. Kraken's derivatives index may be a basket and the API timestamp may label a different boundary, so report basis differences and timing uncertainty. This cross-check can establish plausibility, not exact settlement or cap validity.
4. **Independent fallback.** If Coinbase coverage or semantics fail, test Kraken Spot historical candles or another lawful, independently verifiable source. Keep each venue separate and do not forward-fill.
5. **Historical terms investigation.** Search official dated inverse specifications, archived public parameter pages and the derivatives parameter changelog for any PI-specific funding-cap exception effective on 2026-08-20 and 2026-10-29/30. Do not infer a cap change from observed data.
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
