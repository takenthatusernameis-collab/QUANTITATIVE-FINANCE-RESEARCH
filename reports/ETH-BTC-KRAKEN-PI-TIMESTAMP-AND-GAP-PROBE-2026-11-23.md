# Kraken PI timestamp mapping and gap-event probe

**Date:** 2026-11-23  
**Status:** TIMESTAMP_MAPPING_SAMPLE_CORROBORATED; GAP AUDIT BLOCKED; DATA NOT ACCEPTED  
**Research boundary:** No backtest, venue merge, paid access, credentials, raw-data retention or trading.

## 1. Timestamp-mapping probe

Run [45122891576](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45122891576) succeeded. Manifest-only artifact [14795015222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45122891576/artifacts/14795015222), ZIP digest `sha256:3170b1ff4bdc4dd759f7157ad96efcf39b55c3199c21f2df843c8543e5292267`.

### Method
- Sample date: 2026-10-01 UTC.
- Exact symbols: `PI_XBTUSD`, `PI_ETHUSD`.
- Public Kraken API historical rates and Tardis `cryptofacilities/derivative_ticker` daily CSV gzip files.
- For each next funding event, select the latest pre-event ticker observation no older than 300 seconds, then compare its `funding_rate` with Kraken's `relativeFundingRate` at T and T−1h.
- No raw CSV or API response retained in the artifact; only summary, source hashes and diagnostics.

### Findings

| Metric | PI_XBTUSD | PI_ETHUSD |
|---|---:|---:|
| Tardis ticker rows | 49,188 | 48,931 |
| Next funding events | 24 | 24 |
| Usable pre-event observations | 24/24 | 24/24 |
| API event-time rows present | 24/24 | 24/24 |
| Exact relative-rate match at T−1h | 24/24 | 24/24 |
| Exact relative-rate match at T | 0/24 | 0/24 |
| Median absolute difference at T−1h | 0 | 0 |
| Median absolute difference at T | 0.00000515696875 | 0.00006385345417 |
| Kraken API rows | 8,283 | 8,283 |
| API first timestamp | 2025-11-19 09:00 UTC | 2025-11-19 09:00 UTC |
| API last timestamp | 2026-10-30 16:00 UTC | 2026-10-30 16:00 UTC |
| API duplicates / out-of-order / invalid rates | 0 / 0 / 0 | 0 / 0 / 0 |

**Interpretation:** The sample supports the Kraken API timestamp denoting the rate-setting window start (period start), with the funding event one hour later. The matched field is `relativeFundingRate`; the `fundingRate` absolute field did not provide the match. This does not establish settled-rate equivalence, universal historical semantics, or completeness.

### Source hashes
- Tardis PI_XBTUSD compressed file: 1,109,739 bytes; SHA-256 `44cff2c5000e203f850cfd2cc3b36bddc9c420a74715b267b5549c496fe404fc`.
- Tardis PI_ETHUSD compressed file: 1,021,937 bytes; SHA-256 `f6541638b277dfd6cdc1c68362544aba969477e1b3a1005be8c222f6ae107269`.
- Kraken PI_XBTUSD response: 907,685 bytes; SHA-256 `13d76ff117b43b733be60fcbce61b650b5b7646c302602139ede3d090c4b45d1`.
- Kraken PI_ETHUSD response: 907,404 bytes; SHA-256 `ae37e148cdd8b9eb79304dcfef37fcb77d64444a259d7efcb62c8621571f2`.

## 2. Gap-event and delisting probe

Run [45128398130](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45128398130) failed closed; manifest-only artifact [14796542872](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45128398130/artifacts/14796542872), ZIP digest `sha256:a57d81dcda0be133835cb2f4fbff19627c9e54b01831aaadd94865d03cc56bf6`.

The audit requested Tardis daily files for both PI symbols on five known API-gap dates:

- 2025-12-04 08:00–10:00 UTC
- 2026-02-04 11:00–13:00 UTC
- 2026-02-13 17:00–19:00 UTC
- 2026-05-09 05:00–07:00 UTC
- 2026-10-30 02:00–04:00 UTC

All 10 Tardis requests returned **HTTP 401 Unauthorized**. No Tardis gap-event observations or delisting context were obtained; the manifest has `gap_results=[]`. Do not repeat this route without materially new authorization/evidence. No access restriction was bypassed.

## 3. Remaining blockers

- **PI cap exceptions:** nine rows remain above the published ±0.25% hourly cap; effective-dated PI-specific cap authority was not found. A different contract's exception cannot be extrapolated.
- **Funding event population:** five common two-hour gaps and API/archive residual coverage remain unexplained. The API documentation has no published pagination/retention/completeness guarantee, and the Tardis gap route was inaccessible.
- **Delisting:** Kraken publishes PI_ETHUSD settlement at $2,235.76 for 15:00–16:00 London on 2026-10-30, but the exact CME CF historical reference value and Kraken-specific deviation safeguards were not independently reconstructed.

## 4. Scientific disposition

All four Kraken series remain **PROVISIONAL_NOT_ACCEPTED**. The timestamp mapping is only sample-corroborated; rate cap and payable-event completeness are not established. Do not backtest Kraken or Binance perps, cross-venue merge, clip, interpolate, zero-fill, or retain raw data.

## 5. Sources

- Kraken historical funding API: https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates
- Kraken inverse contract specification: https://support.kraken.com/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives
- Tardis `derivative_ticker` schema and caveat: https://docs.tardis.dev/downloadable-csv-files/data-types
- Tardis sampled PI_XBTUSD: https://datasets.tardis.dev/v1/cryptofacilities/derivative_ticker/2026/10/01/PI_XBTUSD.csv.gz
- Tardis sampled PI_ETHUSD: https://datasets.tardis.dev/v1/cryptofacilities/derivative_ticker/2026/10/01/PI_ETHUSD.csv.gz
- Kraken inverse delisting notice: https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings
