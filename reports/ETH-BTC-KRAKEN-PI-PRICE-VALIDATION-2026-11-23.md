# Kraken PI cap-anomaly independent spot and terms validation — 2026-11-23

**Diagnostic status: COMPLETE**  
**Research acceptance: NOT ACCEPTED**  
**Scope:** nine inverse PI funding-rate cap exceptions; independent BTC/USD and ETH/USD spot plausibility; authoritative contract terms. No backtest, trading, credentials, paid data, raw-data commit, or cross-venue merge.

## Execution and provenance

- Authorized command comment: [PR #2 comment 7092167915](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7092167915).
- Successful research run: [45116028859](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859).
- Manifest-only artifact: [14791133228](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859/artifacts/14791133228), ZIP SHA-256 `0071722e55c0b9cb3f95548dcb36872753f5c71175f8ecef8ba6718372657ddc`, 4,286 bytes.
- The first bounded attempt, [run 45115641203](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45115641203), failed closed because each of four requests produced one out-of-window row. The endpoint's observed behavior was consistent with an inclusive end boundary. The request now ends one second before the exclusive analysis bound; a deterministic regression test locks this behavior.
- Code/test correction: [commit 8420754](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8420754d5edb927b420c6ea5f4fd19ca0dbf4700). Hosted CI [run 45115907842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45115907842) passed **209 deterministic tests** and the synthetic plumbing smoke test.
- The successful run retained only selected candle summaries, product metadata summaries and response SHA-256 hashes. Raw Coinbase responses and candle arrays were not retained or uploaded; no raw market data was committed.

## Bounded Coinbase spot result

The exact products were BTC-USD and ETH-USD. Both product metadata responses reported the expected base/quote currencies, status online and trading_disabled=false. Two known-active positive controls at 2026-08-20 12:00 UTC passed.

Four narrow hourly windows returned 21 valid candles in total:

| Window | Product | Analysis interval (UTC, start-inclusive/end-exclusive) | API end parameter | Valid candles |
|---|---|---|---|---:|
| W1 | BTC-USD | 2026-08-20 08:00–13:00 | 2026-08-20 12:59:59 | 5 |
| W2 | ETH-USD | 2026-08-20 06:00–13:00 | 2026-08-20 12:59:59 | 7 |
| W3 | ETH-USD | 2026-10-29 08:00–11:00 | 2026-10-29 10:59:59 | 3 |
| W4 | ETH-USD | 2026-10-30 12:00–18:00 | 2026-10-30 17:59:59 | 6 |

All four windows had zero invalid rows, duplicate timestamps, unaligned timestamps or out-of-window rows. Each of the nine exception timestamps had an exact-hour candle and a complete t−1/t/t+1 three-hour comparison window. All nine implied Kraken index levels fell inside the corresponding three-hour Coinbase spot low/high envelope.

| Kraken symbol | Exception timestamp (UTC) | Implied USD index | Same-hour Coinbase close basis | Nearest close in 3h window, absolute basis |
|---|---|---:|---:|---:|
| PI_XBTUSD | 2026-08-20 09:00 | 71,523.85 | +0.299467% | 0.005718% |
| PI_ETHUSD | 2026-08-20 07:00 | 2,260.87 | −0.472385% | 0.010615% |
| PI_ETHUSD | 2026-08-20 08:00 | 2,250.08 | +1.337730% | 0.004889% |
| PI_ETHUSD | 2026-08-20 11:00 | 2,284.98 | +0.431076% | 0.010941% |
| PI_ETHUSD | 2026-10-29 09:00 | 2,316.17 | +0.102324% | 0.015975% |
| PI_ETHUSD | 2026-10-30 13:00 | 2,231.70 | −0.431958% | 0.026885% |
| PI_ETHUSD | 2026-10-30 14:00 | 2,222.47 | +0.490895% | 0.018448% |
| PI_ETHUSD | 2026-10-30 15:00 | 2,234.23 | −0.470408% | 0.038044% |
| PI_ETHUSD | 2026-10-30 16:00 | 2,224.13 | +0.246388% | 0.018434% |

The nearest-three-hour-close absolute basis ranged from **0.004889% to 0.038044%** (median **0.015975%**). Same-hour close basis ranged as far as +1.337730%, which demonstrates why an unproven timestamp alignment must not be forced. This is strong local price-plausibility evidence, not equality to Kraken's derivatives index, proof of the funding timestamp, or cap validation.

### October 30 settlement context

Kraken's delisting notice lists PI_ETHUSD settlement at **$2,235.76** for the 15:00–16:00 London observation on 2026-10-30. The Coinbase ETH-USD 15:00–16:00 UTC candle had low **$2,218.07**, high **$2,258.64**, and close **$2,229.61**; the published settlement lies inside that candle's range and is 0.275833% above its close. London was on UTC on this date.

The Kraken inverse specification says the inverse contracts settle at 16:00 UTC against CME CF reference rates. The delisting notice describes a 60-minute, time-segmented, volume-weighted TWAP with deviation safeguards. CME CF's official ETHUSD_RR methodology uses the 15:00–16:00 London observation window, twelve five-minute partitions, a volume-weighted median per partition, and an equally weighted average of those partition values. These descriptions are compatible at the high level of window and partitioning; Kraken's additional deviation safeguards and the exact historical CME CF value were not independently reconstructed here. The Coinbase candle comparison is only a separate-venue plausibility check.

## Authoritative terms review

- The Kraken inverse Coin-M specification page available in the Romanian locale is dated **29 September 2026**. It states an hourly permissible relative funding-rate range of **±0.25%**, multiplier **n=24**, inverse absolute/relative rate definitions, continuous accrual and hourly settlement or settlement when net position changes. It also says the rate for the next period is calculated over the current one-hour period.
- The public derivatives parameters changelog says “Last updated: October 1, 2026”, but its latest dated entry is **4 September 2025**. No PI_XBTUSD or PI_ETHUSD funding-cap change appears in the published entries. The changelog does show a PF_OGNUSD-specific maximum relative-rate change from 0.25% to 0.5% in October 2023 and back to 0.25% in November 2023. Instrument-specific overrides therefore exist, but this is not evidence that PI inherited one.
- The current dated specification predates the 29–30 October exceptions but postdates 20 August. No authoritative pre-20-August snapshot or PI-specific effective-dated cap change was verified. The cap applicable on 20 August therefore remains historically unproven; the public changelog does not resolve the later October observations either.
- The Kraken historical-funding API reference documents the required symbol parameter and ascending timestamp order, but does not define whether a timestamp labels the accrual-period start, end, rate-setting boundary or another instant. It documents no cursor, since/limit parameter, retention horizon or refresh guarantee. The contract's economic timing is documented; the API field-to-accrual mapping is not.

## Response provenance

Product metadata response hashes:
- BTC-USD: `d2bfd4363396ca895bed3a49a2e3f265c7c043efbb50b04ccf87fd5df6197137`
- ETH-USD: `06101801afd8d4f2eb2f4a300ee03574121b4db5c24cf2e1f9640de333d05a12`

Candle response hashes:
- W1 BTC-USD: `8b0b95f6b8928acf78cca7d35027fdac2d5d5dfa07a556c909950ceb21d52c84`
- W2 ETH-USD: `e0b72707c36c402b0bc048e83796c93759af5d193555ce384f96fd8ee63b1b5b`
- W3 ETH-USD: `66bcdf888180e1cf4a631f7b9633764758599d470bed95f84c2748889c9c525f`
- W4 ETH-USD: `91b5aa27d38f48fed5f2b8c876b2d4b8b2c85714386b3caaa256845e6e18c246`

## Decision

The bounded independent price/terms diagnostic is complete. The nine implied levels are locally plausible against Coinbase, but **all nine still exceed the published ±0.25% hourly inverse cap**. No PI-specific historical exception was found in the published changelog, and the cap on 20 August remains unverified. Do not clip, discard, interpolate, or accept the exceptions.

All four Kraken funding series remain **PROVISIONAL_NOT_ACCEPTED**. API timestamp-to-accrual semantics and complete payable-settlement population remain separate hard blockers. No Kraken or Binance perpetual backtest, cross-venue merge, live trading or capital deployment is authorized.

## Sources

- [Coinbase Exchange Get Product Candles](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles)
- [Coinbase Exchange Get Single Product](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproduct)
- [Kraken inverse Coin-M contract specifications](https://support.kraken.com/ro/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives) (Romanian locale; the English route currently redirects to the generic delistings article)
- [Kraken derivatives parameters changelog](https://support.kraken.com/articles/13049711807636-derivatives-platform-parameters-changelog)
- [Kraken derivatives delisting notice](https://support.kraken.com/articles/7526425887508-derivatives-contracts-trading-suspensions-delistings)
- [Kraken historical funding rates API](https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates)
- [CME CF Ether-Dollar Reference Rate methodology](https://docs.cfbenchmarks.com/CME%20CF%20Reference%20Rates%20Methodology.pdf)
- [CME Group reference-rate FAQ](https://www.cmegroup.com/articles/faqs/cme-cf-cryptocurrency-benchmarks-faq.html)

## Next task

Continue with [Kraken PI cap exceptions, API timestamp semantics and settlement-population completeness](../tasks/KRAKEN-PI-API-SEMANTICS-AND-SETTLEMENT-COMPLETENESS.md). Do not repeat the Coinbase windows or re-download the historical Kraken archive unchanged.
