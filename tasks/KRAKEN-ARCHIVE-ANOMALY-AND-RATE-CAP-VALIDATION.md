# Kraken archive residual anomalies and PI rate-cap audit

**Status:** ARCHIVE/API DIAGNOSTIC COMPLETE; FULL-ROW CAP CENSUS IN PROGRESS — 2026-11-23 02:02 UTC  
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

After this commit's hosted CI passes, dispatch the API-only command once, verify the run and artifact, and update this task/report with the actual full-row violation counts. Do not repeat the archive download.

## Remaining acceptance blockers

1. **PI cap anomalies:** identify every out-of-cap API row from the API-only census. Reconcile the August 20 values and pre-settlement October 30 values with date-specific contract parameters or independent evidence. Do not clip or normalize them away.
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
