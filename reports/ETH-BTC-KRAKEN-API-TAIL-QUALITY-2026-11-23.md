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

## Historical funding-period regime

Kraken's historical inverse-method page states that at 2022-09-29 12:00 UTC the funding calculation/settlement window changed from four hours to one hour. The archive cadence matches that boundary exactly:

- PI: 8,939 four-hour intervals × 4 hours = 35,756 hours, exactly 2018-08-31 16:00 through 2022-09-29 12:00 UTC.
- PF: 1,145 four-hour intervals × 4 hours = 4,580 hours, exactly 2022-03-22 16:00 through 2022-09-29 12:00 UTC.

These four-hour intervals are the documented historical schedule, not missing hourly records. The archive also contains five two-hour and one three-hour intervals outside that expected regime; their exact timestamps were not retained in the compact artifact and are the next targeted extraction. The historical inverse methodology documents pre-cutover n=8 and a ±0.1% per-hour cap. Current inverse PI terms are hourly, n=24, and ±0.25% per hour. Current linear PF terms are hourly, n=8, and ±0.5% per hour. The historical source is inverse-specific, so a pre-cutover PF cap is intentionally not inferred from it.

Source: [Kraken inverse funding-rate method before September 29, 2022](https://support.mtf.kraken.com/hc/en-us/articles/7009378818333-Inverse-Perpetual-Contracts-Funding-Rate-Method-Prior-to-September-29-2022).

## Status-incident correlation for the five common API gaps

Each gap represents one missing hourly timestamp shared by all four symbols. The incident overlap is evidence of contemporaneous service disruption only; it does not prove that the funding settlement itself was paused or that the historical API omitted an otherwise valid event.

| Gap (UTC) | Missing hourly timestamp | Status-history evidence | Classification |
|---|---|---|---|
| 2025-12-04 08:00–10:00 | 09:00 | No matching API/derivatives incident. The nearby Unichain Funding Delays incident ran 02:01–05:52 and was asset-specific, ending before the gap. [Incident history](https://sevanalysis.com/vendors/kraken/) | Unexplained |
| 2026-02-04 11:00–13:00 | 12:00 | Connectivity and Trading Issues (Spot & Futures), Web & Mobile, 11:36–13:18; 84 minutes overlap. The incident explicitly names Futures but does not explicitly name the public API. [Incident history](https://sevanalysis.com/vendors/kraken/) | Futures/web-mobile disruption overlap; API impact unproven |
| 2026-02-13 17:00–19:00 | 18:00 | Futures Exchange Connectivity Issues - Web, Mobile & API (REST and WebSockets), 17:39–18:30; 51 minutes overlap. [Incident history](https://sevanalysis.com/vendors/kraken/) | Direct futures/API incident overlap |
| 2026-05-09 05:00–07:00 | 06:00 | API, Web and Mobile connectivity issue 05:10–06:17; 67 minutes overlap. The same Statuspage incident remained open until May 11 18:15 for later payment/withheld-balance issues, not for the original API-connectivity phase. [Official incident](https://status.kraken.com/incidents/0qxsndnx8q3s) | General API incident overlap; derivatives scope not explicit |
| 2026-10-30 02:00–04:00 | 03:00 | Spot and Derivatives clients affected across Web/Mobile, REST, WebSocket and FIX, 02:42–03:42; 60 minutes overlap. [Official incident](https://status.kraken.com/incidents/zkqc9db292h5) | Direct derivatives/API incident overlap |

Summary: three intervals overlap incidents explicitly affecting futures/derivatives (February 4, February 13 and October 30); one overlaps a general API connectivity phase (May 9); one remains unexplained (December 4). No evidence of a scheduled funding pause was found. All five funding-settlement outcomes remain UNVERIFIED; do not insert zeroes, interpolate, or reclassify an interval as no-funding solely because an incident overlapped.

## API history boundary and refresh policy

The [official historical-funding API reference](https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates) documents only the required symbol query parameter and says the rates array is sorted ascending by timestamp. It documents no since, limit, continuation cursor, retention horizon, or refresh cadence. The observed API lower boundary was 2025-11-19 09:00 UTC, approximately 368 days 15 hours before the 2026-11-23 00:23 UTC probe. This is an observed response boundary, not a documented one-year retention guarantee.

The official archive snapshot ends at 2026-02-01 00:00 UTC. Its 1,767-row overlap with the API matches timestamps and both rate fields exactly per symbol, but no public refresh policy was found. PI history ends at 2026-10-30 16:00 UTC, matching the inverse-contract delisting boundary; PF history extends to the probe's latest server data. The union is a useful coverage construction, not proof that every payable event is present.

## Contract-specific payout units and regression tests

The API exposes two distinct rates: fundingRate is the absolute rate per contract unit; relativeFundingRate is the relative hourly rate. The archive's absolute_rate and relative_rate match those API fields exactly in the shared range. Do not merge them into one field.

- **PF linear:** position quantity is base-asset units (one PF contract unit is one BTC or ETH). The absolute hourly rate is USD per base unit: absolute_rate = relative_rate × index_spot_price. Signed payout in USD is -side_sign × base_units × relative_rate × index_spot_price × elapsed_hours. Current terms: one-hour period, n=8, ±0.5% per hour, USD settlement.
- **PI inverse:** position quantity is USD-notional contracts (one PI contract is USD 1). The absolute hourly rate is base-asset units per USD contract: absolute_rate = relative_rate ÷ index_spot_price. Signed payout in BTC/ETH is -side_sign × USD_contracts × relative_rate ÷ index_spot_price × elapsed_hours. Current terms: one-hour period, n=24, ±0.25% per hour, base-asset settlement.
- **Historical PI before 2022-09-29 12:00 UTC:** four-hour funding period, n=8, ±0.1% per hour. After the cutover, hourly, n=24, ±0.25% per hour.
- Positive rates debit longs and credit shorts; negative rates debit shorts and credit longs. Funding accrues continuously and is proportional to actual holding time; split calculations at rate boundaries and position changes. The multiplier is used when deriving an hourly rate from average premium, not applied again to the already-computed relativeFundingRate or payout.

Kraken's linear example (2 BTC short, 0.03378375% per hour, USD index 37,000) yields USD 24.999975, rounded by Kraken to USD 25.00. Its inverse example (100,000 USD contracts short, 0.00595% per hour, index USD 7,000) yields 0.00085 BTC. These are encoded as Decimal regression tests.

**Unresolved PI rate-cap anomaly:** the compact API manifest records PI_XBTUSD relativeFundingRate minimum -0.000862892604166667 and maximum +0.005; PI_ETHUSD minimum -0.003835161729166667 and maximum +0.005. The positive maxima (0.50%) and PI_ETH minimum (-0.3835%) exceed the current inverse ±0.25% hourly cap. The artifact retained extrema but not their timestamps. They may reflect a delisting/settlement event, a date-specific parameter exception, or malformed data; the evidence does not distinguish these. Do not clip or accept them. The next task must fetch only the public API rows needed to identify the extrema timestamps and compare them with the parameter changelog and instrument lifecycle.

The public API reference says the rates array is sorted ascending but does not explicitly define whether each timestamp labels the start or end of the applicable accrual period. The contract specification says the next period's rate is calculated over the current period and applied from the next boundary. Exact timestamp alignment should be reconciled before a backtest.

Implementation: [8114a18](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8114a181d74c7f4f069276060e013b9bde52ccbc) adds Decimal-based payout and incident-correlation helpers. The corrected follow-up in this commit narrows the May 9 API incident to its 05:10–06:17 connectivity phase and avoids claiming API impact for the February 4 Web/Mobile incident. Local tests cover both formulas, sign, multipliers, caps, elapsed time, all five gaps and causal restraint.


## Decision and next task

**Keep all four Kraken series PROVISIONAL_NOT_ACCEPTED.** The five common API gaps are now classified by status-history overlap, but no incident proves that a funding settlement was skipped or omitted. Four intervals overlap service incidents; December 4 remains unexplained. The historical four-hour schedule is explained by the 2022-09-29 cutover. The official API retention/refresh policy remains undocumented, and the PI API tail contains relative-rate extrema above the current inverse cap with no timestamps in the compact artifact. The archive also retains five two-hour and one three-hour anomalies whose exact timestamps were not retained.

Next, execute [Kraken archive residual-anomaly and PI rate-cap audit](../tasks/KRAKEN-ARCHIVE-ANOMALY-AND-RATE-CAP-VALIDATION.md): extract exact archive gap timestamps and timestamped API extrema; reconcile PI cap values against date-specific specifications, changelog and delisting; and determine historical timestamp-boundary semantics. Use only a targeted checksum-verified ephemeral archive read if required. Do not clip, interpolate, or backtest while any of these issues remain unresolved. No Kraken-to-Binance merge, live trading, credentials, paid service, access restriction bypass, or holdout relaxation.
