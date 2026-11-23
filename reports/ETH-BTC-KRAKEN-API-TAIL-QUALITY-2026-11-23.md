# Kraken API-tail and archive/API union quality — 2026-11-23

**Decision status: PROVISIONAL_NOT_ACCEPTED**  
**Scope:** public historical funding data for four exact Kraken Futures instruments. No backtest, live trading, credential use, paid data, or cross-venue merge.

## Execution and provenance

- Autonomous command comment: [PR #2 comment 7088301037](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7088301037).
- Authorized research workflow: [run 45088431644](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45088431644), issue_comment, actor takenthatusernameis-collab, ref main, commit a9095a4c111606347ea7268bb29e6440cc41e7ad; authorization and inspection jobs succeeded.
- Compact evidence artifact: [14780177851](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45088431644/artifacts/14780177851), 69,041 bytes, SHA-256 49b3237f1102cfef1684d89bfadac3bc555c578f264856a4b0b00dc2112f811c.
- The artifact contains only manifest.json and the page screenshot. The 109,980,750-byte ZIP was inspected in runner-local temporary storage and deleted. No raw ZIP or CSV was uploaded or committed. Archive SHA-256: 65ba6712a6ab657389d2795d3ed77bedb4270841dfe711147ae9df16e366edab.
- Code/test revision: [a9095a4](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a9095a4c111606347ea7268bb29e6440cc41e7ad). CI [run 45088233403](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45088233403) passed 162 deterministic tests and the synthetic plumbing smoke test.

## Per-instrument coverage

| Exact symbol | Contract type | Instrument status | Archive rows | Archive range (UTC) | API rows | API range (UTC) |
|---|---|---|---:|---|---:|---|
| PF_XBTUSD | Linear / flexible futures | Active | 30,431 | 2022-03-22 16:00 – 2026-02-01 00:00 | 8,843 | 2025-11-19 09:00 – 2026-11-23 00:00 |
| PF_ETHUSD | Linear / flexible futures | Active | 30,431 | 2022-03-22 16:00 – 2026-02-01 00:00 | 8,843 | 2025-11-19 09:00 – 2026-11-23 00:00 |
| PI_XBTUSD | Inverse futures | Expired / delisted | 38,225 | 2018-08-31 16:00 – 2026-02-01 00:00 | 8,283 | 2025-11-19 09:00 – 2026-10-30 16:00 |
| PI_ETHUSD | Inverse futures | Expired / delisted | 38,225 | 2018-08-31 16:00 – 2026-02-01 00:00 | 8,283 | 2025-11-19 09:00 – 2026-10-30 16:00 |

The inverse contracts' API endpoint coverage ends at their 30 October 2026 delisting/settlement. The active linear contracts' response extends through the probe's latest server data, 23 November 2026 00:00 UTC. The four symbols remain separate; no PF/PI or BTC/ETH pooling was performed.

## API row-quality results

All four API responses passed the mechanical row-integrity checks:

- Zero invalid rows or timestamps.
- Zero duplicate timestamps.
- Zero out-of-order timestamps; response order is non-decreasing.
- Zero null/blank timestamp, fundingRate, or relativeFundingRate values.
- Zero intervals greater than four hours.
- Each response contains 5 two-hour intervals; all other observed intervals are one hour. Maximum API interval: two hours.

The same five two-hour intervals occur in all four instruments:

| Previous UTC timestamp | Next UTC timestamp | Observed interval |
|---|---|---:|
| 2025-12-04 08:00 | 2025-12-04 10:00 | 2h |
| 2026-02-04 11:00 | 2026-02-04 13:00 | 2h |
| 2026-02-13 17:00 | 2026-02-13 19:00 | 2h |
| 2026-05-09 05:00 | 2026-05-09 07:00 | 2h |
| 2026-10-30 02:00 | 2026-10-30 04:00 | 2h |

This synchronized pattern may indicate a common venue-wide schedule, pause, or source-level omission. The probe does not classify the intervals as legitimate no-settlement periods or missing events. They remain an explicit follow-up.

The archive itself has zero invalid timestamps, duplicates, out-of-order rows, nulls, or gaps over four hours. Its observed interval distribution differs by contract family:

- PF: 29,279 one-hour intervals, 1,145 four-hour intervals, five two-hour intervals and one three-hour interval.
- PI: 29,279 one-hour intervals, 8,939 four-hour intervals, five two-hour intervals and one three-hour interval.

Do not infer that every four-hour or two-hour interval is a confirmed no-trade/no-funding interval. Preserve actual timestamps and interval lengths.

## Archive/API reconciliation and timestamp union

For each exact symbol, the archive and API overlap from 2025-11-19 09:00 UTC through 2026-02-01 00:00 UTC:

- 1,767 timestamps matched per symbol.
- The timestamp sets within shared coverage are identical.
- absolute_rate matches API fundingRate exactly: zero mismatches.
- relative_rate matches API relativeFundingRate exactly: zero mismatches.
- The full source sets are not equal because the archive contains earlier history and the API contains a later tail.

| Metric per symbol | PF linear | PI inverse |
|---|---:|---:|
| Archive unique timestamps | 30,431 | 38,225 |
| API unique timestamps | 8,843 | 8,283 |
| Exact overlap | 1,767 | 1,767 |
| Archive-only timestamps | 28,664 | 36,458 |
| API-only tail timestamps | 7,076 | 6,516 |
| Archive/API timestamp union | 37,507 | 44,741 |
| Union start | 2022-03-22 16:00 UTC | 2018-08-31 16:00 UTC |
| Union end | 2026-11-23 00:00 UTC | 2026-10-30 16:00 UTC |
| Union gaps over four hours | 0 | 0 |
| Maximum union interval | 4h | 4h |

The union is a timestamp-coverage calculation only. It does not merge rate values, establish every expected funding event, or prove complete provider history.

## Contract-specific rate semantics

The API fields map to the archive's two distinct fields, but their payout interpretation must remain contract-specific:

- **Linear PF contracts:** absolute payout = contracts × absolute funding rate × elapsed time; relative payout = contracts × (relative funding rate × spot price) × elapsed time. Kraken's current linear specification describes hourly periods, funding multiplier n=8, and a per-hour rate bound of ±0.5%.
- **Inverse PI contracts:** absolute payout = contracts × absolute funding rate × elapsed time; relative payout = contracts × (relative funding rate / spot price) × elapsed time. Kraken's inverse specification describes hourly periods, funding multiplier n=24, and a per-hour rate bound of ±0.25%.
- For both families, positive funding means longs pay shorts; negative funding means shorts pay longs. Do not normalize the absolute and relative columns into one field or apply the PF formula to PI.

References: [Kraken historical funding-rates API](https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates), [linear Multi-Collateral contract specifications](https://support.kraken.com/articles/4844359082772-linear-multi-collateral-derivatives-contract-specifications), and [inverse Coin-M contract specifications](https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives).

The official API reference documents symbol as the query parameter and states that the returned rates array is sorted ascending by timestamp. It does not document a since, limit, or continuation cursor. Therefore, do not assume undocumented pagination or infer full-history completeness from a successful response.

## Decision and next task

**Keep all four Kraken series PROVISIONAL_NOT_ACCEPTED.** The row-quality checks and exact overlap are strong consistency evidence, but do not independently establish complete event population. The synchronized five two-hour intervals need explanation, and the API's returned history boundary/retention is not documented.

Next, investigate the five common two-hour intervals against Kraken's official status/maintenance history and an independent lawful source; determine whether they represent scheduled funding pauses, venue-wide outages, or missing records. Validate the PF and PI payout formulas/units with deterministic examples from the official specifications. Establish whether the archive plus API tail is a defensible complete history for each exact instrument. If completeness or semantics remain unresolved, preserve the provisional status and do not backtest or merge Kraken into Binance.

No live trading, credentials, paid service, access restriction bypass, or empirical strategy evaluation occurred.
