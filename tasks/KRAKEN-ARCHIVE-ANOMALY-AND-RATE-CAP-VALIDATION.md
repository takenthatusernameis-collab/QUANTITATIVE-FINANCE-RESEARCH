# Kraken archive residual anomalies and PI rate-cap audit

**Status:** ARCHIVE/API DIAGNOSTIC, FULL-ROW CENSUS AND EXCEPTION-CONTEXT FOLLOW-UP COMPLETE; INDEPENDENT VALIDATION REQUIRED — 2026-11-23 02:52 UTC  
**Priority:** P1 data-integrity / event-population gate  
**Current gate:** PROVISIONAL_NOT_ACCEPTED; no Kraken backtest or Binance merge.

## Execution and provenance

- The bounded residual-anomaly command completed successfully: [run 45096561519](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45096561519), artifact [14783079210](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45096561519/artifacts/14783079210).
- The runner re-downloaded the official 109,980,750-byte Kraken archive once, verified the previously inspected SHA-256 `65ba6712a6ab657389d2795d3ed77bedb4270841dfe711147ae9df16e366edab`, inspected only PF_XBTUSD, PF_ETHUSD, PI_XBTUSD and PI_ETHUSD, and deleted the raw ZIP/CSV from temporary storage. The uploaded artifact contains the compact manifest only; no raw market data were uploaded or committed.
- The audit found the same six residual archive intervals in all four exact symbols: five two-hour gaps and one three-hour gap. Their exact missing hourly boundaries and incident overlaps are recorded below and in the canonical report.
- Latest pre-follow-up CI [run 45097476971](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45097476971) passed 192 deterministic tests and the synthetic plumbing smoke test. The next commit adds a full-row cap census and archive-incident correlation tests; its own CI must pass before the API-only command is dispatched.

## Exact residual archive intervals

All four symbols have identical interval boundaries:

| Archive interval (UTC) | Duration | Missing hourly boundary/boundaries | Status-history overlap |
|---|---:|---|---|
| 2025-07-10 21:00–23:00 | 2h | 22:00 | Futures REST/WebSocket + Web/Mobile incident 21:27–23:03 |
| 2025-08-31 03:00–05:00 | 2h | 04:00 | Derivatives connectivity incident 03:51–04:47; API scope unspecified |
| 2025-11-01 15:00–18:00 | 3h | 16:00, 17:00 | No matching API/derivatives incident found in inspected mirror |
| 2025-11-02 03:00–05:00 | 2h | 04:00 | No matching API/derivatives incident found in inspected mirror |
| 2025-11-19 04:00–06:00 | 2h | 05:00 | Spot & Futures Web/Mobile incident 03:26–06:10; API scope unspecified |
| 2025-12-04 08:00–10:00 | 2h | 09:00 | No matching API/derivatives incident found in inspected mirror |

The July 10 incident explicitly names Futures REST and WebSocket API connectivity. The August 31 incident names Derivatives but does not establish API scope. The November 19 incident names Spot & Futures Web/Mobile; it does not establish API impact. For the November 19 archive interval, the historical API starts later at 09:00 UTC and cannot cross-check the 05:00 boundary. On December 4, both archive and API contain the interval endpoints but omit 09:00. Incident overlap is not causal proof, and no status-page evidence establishes whether a funding settlement was skipped, delayed, or omitted by either data source. No matching recorded incident is not proof that no service issue occurred.

Deterministic correlation logic and tests now cover all six archive anomalies, exact missing boundaries, incident scopes and overlap durations. The existing API-tail incident correlation remains separate.

## Timestamped PI rate-cap extrema

The targeted API audit retained exact extrema and adjacent records:

| Symbol | Field | Extreme | Value | Timestamp (UTC) | Current inverse cap |
|---|---|---|---:|---|---:|
| PI_XBTUSD | relativeFundingRate | Max | +0.005 | 2026-08-20 09:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Max | +0.005 | 2026-08-20 07:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Max | +0.005 | 2026-08-20 08:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Min | -0.003835161729166667 | 2026-08-20 11:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Max | +0.005 | 2026-10-30 14:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Max | +0.005 | 2026-10-30 15:00 | ±0.0025 |
| PI_ETHUSD | relativeFundingRate | Max | +0.005 | 2026-10-30 16:00 | ±0.0025 |

These are extrema, not yet the complete count of every out-of-cap API row. The August 20 values are not delisting-boundary observations. The October 30 14:00 and 15:00 values precede the official 16:00 UTC inverse settlement; the 16:00 value is at that settlement boundary. The current inverse contract specification states an hourly cap of ±0.25% and a funding-rate multiplier of 24. The reviewed public parameter changelog contains no PI_XBTUSD/PI_ETHUSD funding-cap change, but this is not proof that no unpublished or omitted parameter change exists.

The instrument API simultaneously reports `isExpired=true` and `tradeable=true` for both PI instruments. This is recorded as a lifecycle metadata conflict, not treated as evidence that the delisted contracts remained active. The official inverse-contract notice states that BTC and ETH inverse contracts settled at 16:00 UTC on 2026-10-30.

## New materially different follow-up

The previous audit inspected extrema only. That is insufficient to count every cap breach. The implementation now:
- Classifies every valid returned `relativeFundingRate` row by the date-appropriate PI/PF cap.
- Records every out-of-cap timestamp and value, per-symbol status counts, and unassessed-row counts.
- Adds an API-only `api-cap-audit` mode that does not download the 110 MB archive or launch a browser.
- Adds exact command `/qfr-audit-kraken-rate-cap-census`, authorized through PR #2, with manifest-only output and no raw API rows retained or uploaded.
- Adds deterministic regression tests for full-row cap counts, exact threshold handling, API-only execution, archive anomaly timestamps, incident scopes and causal restraint.

### Completed API-only full-row cap census

The exact command completed successfully on default-branch code: [run 45100276868](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868), manifest-only artifact [14784609201](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100276868/artifacts/14784609201). Artifact ZIP SHA-256: `053108fa092b053c99f511b262dae51098461ddcc282de313bdac615ffc4ff20`. The run queried only the four exact public API histories; it did not download the historical archive, use credentials/account access, attest a region, bypass CAPTCHA, use a proxy/network workaround, purchase data, trade, retain raw rows, upload raw rows, or commit raw rows.

All **34,256** returned rows were assessed (zero unassessed):
- PF_XBTUSD: 8,845 within cap; 0 exceptions.
- PF_ETHUSD: 8,845 within cap; 0 exceptions.
- PI_XBTUSD: 8,282 within cap; **1 exception**.
- PI_ETHUSD: 8,275 within cap; **8 exceptions**.

The nine PI exceptions are:
| Symbol | Timestamp (UTC) | relativeFundingRate | Current documented cap |
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

The August 20 anomalies are not delisting-boundary observations. The October 29/30 observations cluster near the inverse-contract delisting, but timestamp-to-accrual mapping is unresolved. The reviewed public parameter changelog contains no PI-specific funding-cap change; this cannot exclude unpublished or omitted changes. Do not clip, normalize, or accept any exception.

All four responses passed mechanical integrity checks: zero invalid timestamps, duplicates, out-of-order rows, required-field nulls, or gaps over four hours. Each response still has five two-hour intervals whose settlement interpretation is unknown. The API history begins at 2025-11-19 09:00 UTC, and the endpoint's retention/refresh/completeness policy is undocumented. The census therefore does **not** prove a complete payable-settlement population.

CI [45100169673](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45100169673) passed 153 deterministic tests and the synthetic plumbing smoke test on census commit `08092b73`.

### Completed bounded exception-context follow-up

The updated code/test revision passed CI [45102432282](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102432282): 199 deterministic tests and synthetic plumbing smoke test. The exact API-only command then completed successfully in [run 45102646438](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438), with manifest-only artifact [14786345447](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102646438/artifacts/14786345447). Artifact ZIP SHA-256: `56923db469f03d70285999684af1c72c90c9e65d2d9423d63b92543b557e85d3`. The run queried the four exact public API histories, did not download the archive, and uploaded only the compact manifest.

All nine exception rows now retain both `fundingRate` and `relativeFundingRate`, plus at most one preceding/following row. The two fields are arithmetically consistent with Kraken's inverse formula: `implied_index = relativeFundingRate / fundingRate`. The derived levels are plausible but are **not** independent market-price observations and do not establish cap compliance.

Sequence findings:
- PI_XBTUSD 2026-08-20 09:00 is isolated; 08:00 and 10:00 are within cap.
- PI_ETHUSD 2026-08-20 07:00 and 08:00 are consecutive +0.5% observations; 09:00 is within cap. The 11:00 negative exception is isolated between in-cap neighbors.
- PI_ETHUSD 2026-10-29 09:00 is isolated between in-cap neighbors.
- PI_ETHUSD 2026-10-30 13:00 and 14:00–16:00 form a consecutive out-of-cap sequence ending at the official settlement boundary.

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

The response hashes are retained in the same manifest per exact symbol and can be joined to exception rows by symbol. The full list is in the new [independent price/terms validation task](KRAKEN-PI-CAP-ANOMALY-INDEPENDENT-PRICE-VALIDATION.md).

The latest queue guardian [45102678816](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45102678816) enumerated 369 workflow runs with complete enumeration, zero enforcement actions and zero errors. No active research/test runs or open standalone issues remained at that check.

**Decision:** diagnostic work is complete, but Kraken funding remains `PROVISIONAL_NOT_ACCEPTED`. The cap contradiction, API timestamp-to-accrual semantics and full payable-settlement population are still independent blockers. Do not backtest or merge venues.

Next, execute [Kraken PI cap-anomaly independent price and terms validation](KRAKEN-PI-CAP-ANOMALY-INDEPENDENT-PRICE-VALIDATION.md). Start with a bounded Coinbase BTC-USD/ETH-USD spot cross-check; this is a plausibility check, not a substitute for authoritative Kraken funding terms or settlement completeness.

## Remaining acceptance blockers

1. **PI cap anomalies:** all nine out-of-cap rows are now identified and locally contextualized. Reconcile the August 20 and October 29/30 observations with independent spot evidence and authoritative historical contract parameters. Do not clip or normalize them away.
2. **Timestamp boundary semantics:** Kraken's contract specification describes next-period rate setting and hourly accrual, but the historical API reference does not explicitly define whether a row timestamp labels the beginning or end of the applicable accrual period. Keep `api_timestamp_boundary_semantics=UNRESOLVED` and `backtest_alignment_status=BLOCKED_PENDING_API_FIELD_MAPPING` unless official evidence resolves it.
3. **Funding-event population:** the API's observed start is 2025-11-19 09:00 UTC, with no documented retention/refresh/pagination policy. The archive/API union and incident correlations do not prove a complete payable-settlement population. Preserve all missing events as unknown; never substitute zero or interpolate.
4. **Archive residuals:** the July 10, August 31 and November 19 gaps overlap service incidents, but the November 1, November 2 and December 4 gaps have no matching API/derivatives incident in the inspected history. No incident overlap proves a skipped settlement.

## Acceptance criteria

- Exact archive interval pairs and missing hourly boundaries retained for all four symbols.
- Every returned relative-rate row is cap-classified, with every exception timestamped and preserved.
- Official contract cap, parameter-change and delisting evidence remain linked to each exception.
- Archive checksum/provenance verified; raw ZIP/CSV remains ephemeral and absent from Git/artifacts.
- API history boundary and refresh policy either authoritatively documented or explicitly unresolved.
- Funding timestamp boundary semantics either source-verified or explicitly blocking empirical alignment.
- Regression tests and hosted CI pass; canonical report, README and queue updated.

No live trading, paid data, credentials, access-restriction bypass, cross-venue merge, synthetic funding fill, holdout relaxation, or backtest. If completeness or timestamp semantics remain unresolved, preserve PROVISIONAL_NOT_ACCEPTED and continue only with a materially different bounded probe.
