# Kraken archive residual anomalies and PI rate-cap audit

**Status:** PENDING — next autonomous research cycle  
**Priority:** P1 data-integrity / event-population gate  
**Current gate:** PROVISIONAL_NOT_ACCEPTED; no Kraken backtest or Binance merge.

## Background

The completed [Kraken API-tail and payout-semantics report](../reports/ETH-BTC-KRAKEN-API-TAIL-QUALITY-2026-11-23.md) establishes:

- The official archive contains five two-hour and one three-hour intervals outside the documented four-hour historical schedule. The compact artifact retained cadence counts but not exact timestamps.
- The API tail has five common two-hour gaps across PF_XBTUSD, PF_ETHUSD, PI_XBTUSD and PI_ETHUSD. Four overlap service incidents; the 2025-12-04 interval remains unexplained. None proves a skipped or omitted funding settlement.
- The PI API summary contains relativeFundingRate extrema beyond the current inverse ±0.25% per-hour cap: PI_XBTUSD maximum +0.005; PI_ETHUSD maximum +0.005 and minimum -0.003835161729166667. Their timestamps were not retained, so no cap breach or exception is yet confirmed.
- The archive/API overlap is exact for 1,767 rows per symbol, but the official API documents no retention, refresh, since, limit or continuation policy.

## Adaptive execution plan

1. Reuse artifact [14780177851](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45088431644/artifacts/14780177851), its SHA-256, and the exact API/archive overlap before any download. Do not repeat the broad archive probe unchanged.
2. Query the public historical-funding API for the four exact symbols and retain only the timestamped rows for each absolute/relative minimum and maximum, plus adjacent rows. Record serverTime, response count, request URL, response hash and instrument lifecycle metadata. No credentials or undocumented query parameters.
3. Compare PI extrema with the applicable inverse rate caps, contract-specific parameter changelog, historical method and 2026-10-30 delisting. Determine whether each is a normal hourly rate, special final/delisting event, parameter exception, or malformed record. Do not clip or normalize away an outlier.
4. If the archive's exact residual timestamps cannot be recovered from the compact artifact, perform one checksum-verified download of the existing official 109,980,750-byte archive. Inspect only the four exact PF/PI BTC/ETH CSV members, extract timestamp pairs and adjacent rows for the five two-hour and one three-hour intervals, compare them with the API overlap, and delete the ZIP/CSV from runner-local temporary storage. Never upload or commit raw market data.
5. Correlate the residual archive anomalies with status history using exact incident phases, not merely overall incident-resolution timestamps. Keep API, derivatives, payment and asset-specific incidents separate.
6. Establish whether the public API timestamp labels the beginning or end of the applicable funding accrual interval. Use official docs or a deterministic public example; if not explicit, preserve the uncertainty and block backtest alignment.
7. Add deterministic tests for any newly established historical regime, rate-cap exception, anomaly classification and timestamp alignment. Update the report, README, active queue and handoff.

## Acceptance criteria

- Exact timestamp pairs and adjacent records for every residual archive anomaly, per symbol.
- Timestamped PI/PF rate extrema with date-appropriate cap and parameter evidence.
- No unexplained cap violation silently clipped, interpolated or accepted.
- Archive checksum and source provenance verified; raw ZIP/CSV remains ephemeral and absent from Git/artifacts.
- API history boundary and refresh policy either authoritatively documented or explicitly unresolved; no invented pagination/retention assumption.
- Funding timestamp boundary semantics either source-verified or explicitly blocking empirical alignment.
- Regression tests and hosted CI pass; canonical report and queue updated.

No live trading, paid data, credentials, access-restriction bypass, cross-venue merge, synthetic funding fill, or holdout relaxation. If any completeness or semantics requirement remains unresolved, preserve PROVISIONAL_NOT_ACCEPTED and continue with a materially different bounded probe rather than repeating a known-failing route.
