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

**Unresolved PI rate-cap anomaly:** the API-only full-row census found nine PI rows above the currently documented inverse ±0.25% hourly cap (one PI_XBTUSD, eight PI_ETHUSD). A bounded follow-up retained both rate fields and immediate neighboring rows for all nine. Their absolute/relative values are arithmetically consistent with Kraken's inverse formula, but this does not explain the cap discrepancy or establish settlement validity. Exact timestamps, sequence patterns, response hashes and implied index levels are in the [completed context audit and next independent validation task](../tasks/KRAKEN-PI-CAP-ANOMALY-INDEPENDENT-PRICE-VALIDATION.md).

The public API reference says the rates array is sorted ascending but does not explicitly define whether each timestamp labels the start or end of the applicable accrual period. The contract specification says the next period's rate is calculated over the current period and applied from the next boundary. Exact timestamp alignment should be reconciled before a backtest.

Implementation: [8114a18](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8114a181d74c7f4f069276060e013b9bde52ccbc) adds Decimal-based payout and incident-correlation helpers. The corrected follow-up in this commit narrows the May 9 API incident to its 05:10–06:17 connectivity phase and avoids claiming API impact for the February 4 Web/Mobile incident. Local tests cover both formulas, sign, multipliers, caps, elapsed time, all five gaps and causal restraint.


## Decision and next task

**Keep all four Kraken series PROVISIONAL_NOT_ACCEPTED.** The bounded Coinbase independent price/terms diagnostic is complete in [the PI price-validation report](ETH-BTC-KRAKEN-PI-PRICE-VALIDATION-2026-11-23.md). All nine implied levels are locally plausible against Coinbase, but all nine still exceed the published ±0.25% hourly cap and no PI-specific historical exception was found in the public changelog. API timestamp-to-accrual semantics and complete payable-event population remain unresolved.

Next, execute [Kraken PI cap exceptions, API timestamp semantics and settlement-population completeness](../tasks/KRAKEN-PI-API-SEMANTICS-AND-SETTLEMENT-COMPLETENESS.md). Do not repeat the Coinbase windows, re-download the same archive unchanged, backtest, clip, interpolate, or merge venues.

## Targeted residual-anomaly and PI rate-cap audit — 2026-11-23

**Diagnostic run:** [45096561519](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45096561519), successful. **Manifest artifact:** [14783079210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45096561519/artifacts/14783079210). The run re-downloaded the official 109,980,750-byte export once, verified the prior archive SHA-256 `65ba6712a6ab657389d2795d3ed77bedb4270841dfe711147ae9df16e366edab`, inspected only the four exact PF/PI BTC/ETH perpetual CSVs, and deleted raw ZIP/CSV data from runner-local temporary storage. The artifact retained only a compact manifest; no raw market data were uploaded or committed.

### Exact archive residual intervals

The same six intervals occur in all four exact symbols:

| Interval (UTC) | Duration | Missing hourly boundary/boundaries |
|---|---:|---|
| 2025-07-10 21:00–23:00 | 2h | 22:00 |
| 2025-08-31 03:00–05:00 | 2h | 04:00 |
| 2025-11-01 15:00–18:00 | 3h | 16:00, 17:00 |
| 2025-11-02 03:00–05:00 | 2h | 04:00 |
| 2025-11-19 04:00–06:00 | 2h | 05:00 |
| 2025-12-04 08:00–10:00 | 2h | 09:00 |

An independent status-history mirror records three exact service-incident overlaps: (1) July 10, 21:27–23:03 UTC, “Futures Exchange Connectivity Issues - Web, Mobile & API (REST & WebSockets)” (explicit API scope); (2) August 31, 03:51–04:47 UTC, “Connectivity Issues - Derivatives” (API scope not specified); and (3) November 19, 03:26–06:10 UTC, “Connectivity Issues (Spot & Futures) - Web & Mobile” (API scope not specified). No matching API/derivatives incident was found in the inspected history for November 1, November 2 or December 4. These are contemporaneous service overlaps, not causal evidence about whether a funding settlement occurred. Sources: [Kraken incident history mirror](https://sevanalysis.com/vendors/kraken/) and [Kraken's status API documentation](https://status.kraken.com/api).

The public historical API begins at 2025-11-19 09:00 UTC, so it cannot cross-check the 05:00 November 19 boundary or earlier anomalies. On December 4, API and archive both contain the 08:00 and 10:00 endpoints but omit 09:00. The missing event population remains unresolved.

### Timestamped PI relative-rate extrema

| Symbol | Extreme | Value | Timestamp (UTC) | Current cap |
|---|---|---:|---|---:|
| PI_XBTUSD | Max | +0.005 | 2026-08-20 09:00 | ±0.0025 |
| PI_ETHUSD | Max | +0.005 | 2026-08-20 07:00 | ±0.0025 |
| PI_ETHUSD | Max | +0.005 | 2026-08-20 08:00 | ±0.0025 |
| PI_ETHUSD | Min | -0.003835161729166667 | 2026-08-20 11:00 | ±0.0025 |
| PI_ETHUSD | Max | +0.005 | 2026-10-30 14:00 | ±0.0025 |
| PI_ETHUSD | Max | +0.005 | 2026-10-30 15:00 | ±0.0025 |
| PI_ETHUSD | Max | +0.005 | 2026-10-30 16:00 | ±0.0025 |

The official inverse specification states an hourly relative-rate range of ±0.25% and a 24-hour multiplier of 24. The August 20 extrema are not delisting-boundary events. The October 30 14:00 and 15:00 values precede the 16:00 UTC inverse settlement; the 16:00 value is at that boundary. The reviewed public parameter changelog shows no PI_XBTUSD/PI_ETHUSD funding-cap change, but this does not prove that no unpublished or omitted parameter change exists. Both PI instruments' current metadata simultaneously says `isExpired=true` and `tradeable=true`; this is a flagged lifecycle conflict, not proof of continued tradability. The official notice says inverse BTC/ETH contracts settled at 16:00 UTC on October 30.

Sources: [Kraken inverse contract specification](https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives), [Kraken derivatives parameter changelog](https://support.kraken.com/ro/articles/13049711807636-derivatives-platform-parameters-changelog), and [Kraken delisting notice](https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings).

## API-only full-row cap census — 2026-11-23

The all-row audit completed in [run 45100276868](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868), with manifest-only artifact [14784609201](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868/artifacts/14784609201). Artifact SHA-256: `053108fa092b053c99f511b262dae51098461ddcc282de313bdac615ffc4ff20`. It queried the four public API histories only; no archive download, credentials, account access, region attestation, CAPTCHA bypass, proxy, purchase, trading, or raw-row retention/upload/commit occurred.

All 34,256 rows were cap-assessed with zero unassessed rows:

| Symbol | Rows | Within documented cap | Exceeds documented cap |
|---|---:|---:|---:|
| PF_XBTUSD | 8,845 | 8,845 | 0 |
| PF_ETHUSD | 8,845 | 8,845 | 0 |
| PI_XBTUSD | 8,283 | 8,282 | 1 |
| PI_ETHUSD | 8,283 | 8,275 | 8 |

The nine PI exceptions are preserved exactly:

| Symbol | Timestamp (UTC) | relativeFundingRate | Current inverse cap |
|---|---|---:|---:|
| PI_XBTUSD | 2026-08-20 09:00 | +0.005 | ±0.0025 |
| PI_ETHUSD | 2026-08-20 07:00 | +0.005 | ±0.0025 |
| PI_ETHUSD | 2026-08-20 08:00 | +0.005 | ±0.0025 |
| PI_ETHUSD | 2026-08-20 11:00 | -0.003835161729166667 | ±0.0025 |
| PI_ETHUSD | 2026-10-29 09:00 | +0.003261576116071429 | ±0.0025 |
| PI_ETHUSD | 2026-10-30 13:00 | +0.003248896366666667 | ±0.0025 |
| PI_ETHUSD | 2026-10-30 14:00 | +0.005 | ±0.0025 |
| PI_ETHUSD | 2026-10-30 15:00 | +0.005 | ±0.0025 |
| PI_ETHUSD | 2026-10-30 16:00 | +0.005 | ±0.0025 |

All nine exceed the currently documented inverse hourly cap. The August 20 values are not near the delisting. The October 29/30 values cluster near the October 30 16:00 UTC settlement, but the API timestamp-to-accrual mapping is unresolved. The public parameter changelog contains no PI-specific funding-cap change in the reviewed entries; this cannot exclude unpublished or omitted changes.

Every returned row passed mechanical timestamp/order/duplicate/null checks; no interval exceeds four hours. The five common two-hour gaps remain unexplained as settlement events. The API begins at 2025-11-19 09:00 UTC and has no documented retention/refresh/cursor policy. This census does not establish complete settlement-population coverage.

The new implementation adds a bounded exception-context capture: for each cap exception it retains only the exception row and at most one preceding/following row, including both `fundingRate` and `relativeFundingRate`. It does not retain the full API response. Code/test commits: [9c9beaa](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9c9beaa75455c0fab7e7c5885ce1367332e3723e) and [6ba9616](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/6ba961667adaafc08589dc4c93af453555eb16aa). Final CI and the refreshed manifest are pending.

**Decision:** all four Kraken series remain `PROVISIONAL_NOT_ACCEPTED`. No Kraken backtest, cross-venue merge or empirical performance claim is authorized. API timestamp semantics and complete payable-settlement population remain independent hard blockers.


## Official delisting-settlement cross-check

Kraken's official delisting notice lists PI_ETHUSD settlement at $2,235.76 for the 15:00–16:00 London-time observation on 2026-10-30. It describes a volume-weighted, time-segmented TWAP with deviation safeguards against spot transactions on constituent exchanges. London was on UTC on that date.

The four consecutive/near-consecutive PI_ETHUSD API exception rows imply:
| API timestamp (UTC) | Implied USD index | Difference from $2,235.76 settlement |
|---|---:|---:|
| 2026-10-30 13:00 | $2,231.70 | -0.1816% |
| 2026-10-30 14:00 | $2,222.47 | -0.5944% |
| 2026-10-30 15:00 | $2,234.23 | -0.0684% |
| 2026-10-30 16:00 | $2,224.13 | -0.5202% |

The 15:00 implied value is close to the official settlement, but the API row may label the start or end of a funding interval and the Kraken index need not equal the settlement TWAP. This is a plausibility clue only; it does not resolve timestamp semantics or explain the cap breaches.

The inverse specification, last updated September 29, 2026, explicitly states the ±0.25% hourly permissible range and defines the absolute/relative inverse-rate relationship. The public parameters changelog was last updated October 1, 2026, but its latest dated entry is September 4, 2025. It does document a PF_OGNUSD-specific maximum relative funding-rate increase from 0.25% to 0.5% on October 1, 2023, then a reduction from 0.005 to 0.0025 on November 24, 2023. This demonstrates that instrument-specific overrides are possible, but no PI_XBTUSD/PI_ETHUSD funding-cap change appears in the published entries. Absence from the changelog does not exclude an unpublished or omitted PI change.

Sources: [Kraken inverse contract specifications](https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives), [Kraken delisting notice](https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings), and [Kraken parameters changelog](https://support.kraken.com/articles/13049711807636-derivatives-platform-parameters-changelog).

## Bounded PI exception-context audit — 2026-11-23

The follow-up completed in [run 45102646438](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438), manifest-only artifact [14786345447](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438/artifacts/14786345447). Artifact SHA-256: `56923db469f03d70285999684af1c72c90c9e65d2d9423d63b92543b557e85d3`. CI [45102432282](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102432282) passed 199 deterministic tests and synthetic smoke. No archive download or raw-row upload occurred.

The nine exception rows now include both API rate fields and at most one adjacent row on either side. Their ratio `relativeFundingRate / fundingRate` yields the following implied USD index levels under the documented inverse formula:

| Symbol | Timestamp (UTC) | Implied USD index level |
|---|---|---:|
| PI_XBTUSD | 2026-08-20 09:00 | 71,523.85 |
| PI_ETHUSD | 2026-08-20 07:00 | 2,260.87 |
| PI_ETHUSD | 2026-08-20 08:00 | 2,250.08 |
| PI_ETHUSD | 2026-08-20 11:00 | 2,284.98 |
| PI_ETHUSD | 2026-10-29 09:00 | 2,316.17 |
| PI_ETHUSD | 2026-10-30 13:00 | 2,231.70 |
| PI_ETHUSD | 2026-10-30 14:00 | 2,222.47 |
| PI_ETHUSD | 2026-10-30 15:00 | 2,234.23 |
| PI_ETHUSD | 2026-10-30 16:00 | 2,224.13 |

This demonstrates arithmetic consistency between the absolute and relative API fields; it does **not** independently validate the implied market/index prices or establish that the relative rates complied with the documented cap.

The adjacent-row pattern shows isolated PI_XBTUSD 2026-08-20 09:00 and PI_ETHUSD 2026-08-20 11:00 exceptions; consecutive PI_ETHUSD 07:00/08:00 exceptions on August 20; an isolated PI_ETHUSD 2026-10-29 09:00 exception; and a consecutive PI_ETHUSD 13:00–16:00 sequence on October 30 ending at the delisting boundary. The August anomalies are not delisting events. The October timestamp-to-accrual mapping remains unresolved.

The response hashes are retained per exact symbol in the same manifest and joinable to exceptions by symbol:
- PF_XBTUSD: `6b7df2d3860f0b116b4b90482ac7c7f203fdf7bb5c43aaa090f00a3d55262340`
- PF_ETHUSD: `50ab8de1d6bd84626c448d5a7f933dacdcbd89d33a2fce676228e7a83b04bd44`
- PI_XBTUSD: `de1a8cfbadec23b563696de4a2c6ee5d8d404e7a5f423198ea39dac9b545b547`
- PI_ETHUSD: `7f781d0b37d4f695717f0a5092a9a7ce9b601bdbf2a29105663a96c432621907`

The public inverse specification still states ±0.25% per hour. The reviewed public parameter changelog contains no PI-specific funding-cap change, but cannot exclude unpublished/omitted terms. All four series remain `PROVISIONAL_NOT_ACCEPTED`; event-population completeness and API timestamp semantics remain separate hard blockers. See [the next independent validation task](../tasks/KRAKEN-PI-CAP-ANOMALY-INDEPENDENT-PRICE-VALIDATION.md).
