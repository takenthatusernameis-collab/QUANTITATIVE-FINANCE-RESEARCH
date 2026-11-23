# ETH/BTC funding-data architecture pivot

**Date:** 2026-11-23  
**Status:** ARCHITECTURE DECISION COMPLETE; ORIGINAL FUNDING STUDY INCONCLUSIVE  
**Scope:** One-cycle screen of four materially different routes. No key, purchase, data download, backtest, or live action.

## Decision

**Primary historical route: Market History's Binance USD-M perpetual funding dataset.** It is the only screened candidate with a clear documented claim of complete event-level Binance history, including delisted contracts and changing 1h/4h/8h intervals. It is not accepted until an authorized sample is obtained and validated.

**Fallback: prospective event capture**, only if official public sources are available from a legally/regionally permitted runner. This creates future observations; it cannot backfill the 2020–2026 study. The prior direct Binance funding REST route returned HTTP 451, so no retry or access bypass is allowed.

## Architecture comparison

| Route | Coverage / feasibility | Cost / permission | Decision |
|---|---|---|---|
| **Market History (primary)** | Claims Binance USD-M perps from first month, delisted contracts included; event rows carry 1h/4h/8h intervals; cursor pagination; nightly updates and monthly archive reconciliation. No keyless funding sample; exact ETHUSDT/BTCUSDT funding rows remain unverified. | 1M-bar one-time minimum **$5**; bought bars never expire. Requires owner authorization for purchase and API key. | **Best historical candidate.** Validate only after authorization. |
| **Prospective capture (fallback)** | Can build a complete dataset prospectively only if the official feed/API is accessible; cannot backfill. | No paid vendor required, but direct REST route previously returned HTTP 451. Do not circumvent. | Future-data fallback; not useful for historical study now. |
| **8h-only Binance archive sensitivity** | Existing official checksummed archive has 8h observations, while Binance's rules allow conditional 1h/4h intervals. It cannot establish the full event population. | No purchase; data already collected. | Separate, explicitly restricted experiment only; not the original full funding-aware study. |
| **Separate exchange dataset** | MEXC pilot returns ~540 days; Bitget 90 days; Bybit 403; OKX symbol search found no records; Kraken histories remain provisional and different venue. | Public routes already screened; no new provider search. | Not a substitute for Binance. Keep venues separate. |

## Market History verification plan (not executed)

- Official [funding docs](https://getmarkethistory.com/docs/funding) describe crypto/perps Binance funding events, including delisted contracts, and 1h/4h/8h intervals.
- [API guide](https://getmarkethistory.com/docs/guides/crypto-funding-rates/) describes timestamp, rate, interval_h, one symbol per request, cursor pagination and monthly validation.
- [Limits and billing](https://getmarkethistory.com/docs/limits) states the one-time minimum is 1M bars for $5 and purchased bars do not expire. The funding endpoint has no keyless sample.
- [Coverage page](https://getmarkethistory.com/coverage/) shows the crypto/perps dataset covering Binance perps from 2019-10-01, but the dynamic symbol catalog could not be independently queried through the available web reader.
- The vendor claims are not independent evidence of completeness. A sample must confirm exact BTCUSDT and ETHUSDT symbol coverage, first/last timestamps, all event intervals, pagination, duplicates, timestamp semantics, monthly reconciliation, and raw-data handling before acceptance.

## Owner prerequisite

Explicit authorization is required for the $5 minimum one-time purchase and API key. No purchase or key was created. Once authorized, execute a **bounded two-symbol probe only** (BTCUSDT and ETHUSDT, 2020-01-01–2026-10-31) and inspect only derived manifests/hashes. Stop if schema, coverage or event semantics fail; do not expand the purchase or provider search.

## Final disposition

The original Binance funding-aware ETH/BTC study remains **INCONCLUSIVE**. There is no accepted full-history funding event population, so no perpetual backtest or funding-dependent conclusion is authorized. The 8h-only archive is not a complete substitute. A separate spot-only experiment may proceed with accepted spot data.

## Sources

- https://getmarkethistory.com/docs/funding
- https://getmarkethistory.com/docs/guides/crypto-funding-rates/
- https://getmarkethistory.com/docs/limits
- https://getmarkethistory.com/coverage/
- Existing provider-screen report: [ETH-BTC-FUNDING-PROVIDER-SCREEN-2026-11-22](ETH-BTC-FUNDING-PROVIDER-SCREEN-2026-11-22.md)
- Existing archive/API and provider findings: [ETH-BTC-FUNDING-GATE-UPDATE-2026-11-22](ETH-BTC-FUNDING-GATE-UPDATE-2026-11-22.md)
