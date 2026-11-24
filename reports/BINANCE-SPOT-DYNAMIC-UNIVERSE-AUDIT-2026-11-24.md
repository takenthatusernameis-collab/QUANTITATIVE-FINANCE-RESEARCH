# Binance Spot Dynamic-Universe and Historical-Coverage Audit — checkpoint

**Checkpoint time:** 2026-11-24 12:53:20 UTC  
**Workstream:** BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24  
**Status:** ACTIVE — second substantive wake-up completed; 2 of 4 cycles used.  
**Scope:** public, read-only Binance Spot metadata and archive feasibility. No strategy, backtest, holdout inspection, credentials, paid data or trading.

## Executive result

The full current Binance Spot symbol catalogue is retrievable and normalizes cleanly. Direct, documented monthly archive object URLs also work for a bounded sample, with SHA-256 sidecars and hourly-bar checks passing for four of five tested symbol-month files.

The archive prefix-list route is not usable in the tested environment: it returned HTTP 200 with HTML rather than an XML ListObjectsV2 response. More importantly, the current catalogue contains many known delisted pairs in status BREAK, but the current status is not an event history and does not establish when a pair first listed, when it stopped trading, whether it was relisted, or whether every historical pair is retained. Official delisting announcements are a possible event source, but their complete historical coverage and pagination have not been established.

**No broader point-in-time universe is accepted yet. No strategy is ready to start.**

## 1. Current Spot catalogue — VERIFIED for the current snapshot

Run: [45396976562](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562)  
Artifact: [binance-spot-universe-audit-45396976562](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562/artifacts/14920684215)

Source: https://data-api.binance.vision/api/v3/exchangeInfo  
Retrieved: 2026-11-24 12:47:52.814 UTC  
HTTP: 200; JSON; X-MBX-USED-WEIGHT-1M: 20  
Raw decoded response bytes: 18,152,734  
Raw response SHA-256: 1547b62532d008d7e2ca92a64d3f60be23d32552a675a96b82f67f515d2b5d53

| Catalogue field | Result |
|---|---:|
| Reported / normalized symbols | 3,751 / 3,751 |
| Parse errors | 0 |
| TRADING | 1,376 |
| BREAK | 2,375 |
| Distinct quote assets | 50 |
| isSpotTradingAllowed = true | 3,711 |
| isSpotTradingAllowed = false | 40 |

The normalized catalogue contains 3,751 unique symbol records with base asset, quote asset, status, permissions, order types and filters. The normalized catalogue is 27,945,027 bytes with SHA-256 86cfc7b96303d1b8c3397469ca4524328109425fb89b24c75e7ca7d572ceda47. The compressed artifact is 496,162 bytes with SHA-256 f6749853ea829a013490e9af394d6b24e39a51e96433cbcfee7ed9070dcd5e66. The artifact contains only manifest.json and catalogue.json; no raw exchange response or market-data ZIP/CSV was uploaded.

The official Binance Public Data repository's helper obtains the current exchangeInfo symbols array. The helper does not filter the array by status, which is consistent with this snapshot retaining many BREAK records. This is useful symbol metadata, but it is not a documented historical membership ledger.

## 2. Archive listing/index route — UNAVAILABLE in the tested form

Initial runner probe: [45395322993](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45395322993)

The single ListObjectsV2 prefix request for data/spot/monthly/klines returned:
- HTTP 200
- Content-Type: text/html
- 2,712 response bytes
- no XML ListBucketResult
- no verified pagination or complete symbol-directory enumeration

The route was stopped on schema ambiguity. No unchanged retry or alternate directory-index path was attempted. This does not prove that every possible official discovery surface is unavailable; it means the tested index route cannot support a completeness claim.

## 3. Direct monthly archive objects — SAMPLE_ONLY

The second run used 5 metadata/API requests and 11 unique archive objects, for 16 HTTP requests total. It downloaded 155,377 archive bytes, well within the 50-request, 12-object and 250-MB limits.

| Symbol / month | Rows | Result | Integrity / coverage |
|---|---:|---|---|
| BTCUSDT / 2026-10 | 744 | ACCEPTED_SAMPLE | Checksum matched; complete UTC month; no missing hours, duplicates, ordering, numeric, OHLC/volume or close-time errors |
| ETHUSDT / 2026-10 | 744 | ACCEPTED_SAMPLE | Same checks passed |
| USDTAED / 2026-10 | 744 | ACCEPTED_SAMPLE | Same checks passed |
| BTCUSDT / 2020-01 | 744 | ACCEPTED_SAMPLE | Checksum matched; complete historical month; same structural checks passed |
| USDCAED / 2026-10 | 4 | REJECTED_OR_INCOMPLETE_SAMPLE | Checksum matched, but only four rows; 740 expected hours absent and one close-time alignment error |

The USDCAED first-kline query returned 2026-10-28 08:00 UTC, so the four-row result is a late-inception/incomplete-month case, not evidence of a full-month archive. It is not accepted as a complete month.

First-kline inception probes returned:
- BTCUSDT: 2017-08-17 04:00 UTC
- ETHUSDT: 2017-08-17 04:00 UTC
- USDCAED: 2026-10-28 08:00 UTC
- USDTAED: 2026-06-04 08:00 UTC

All five downloaded ZIP files had matching SHA-256 CHECKSUM sidecars. The nonexistent-symbol negative control QFRNOTREALUSDT returned the expected HTTP 404 with zero response bytes. No pre-listing archive negative-control request was made.

The sample algorithm was deterministic and selected the least-populated available non-USDT quote/status strata. In this run it selected AED pairs; both non-seed base assets were stablecoins. This proves a bounded object route, not representative asset-class coverage. The historical-month sample was BTCUSDT only.

The official [Binance Public Data README](https://github.com/binance/binance-public-data/blob/master/README.md) documents symbol-specific monthly object URLs and companion CHECKSUM files. It does not provide a verified complete historical symbol/month index in the evidence collected here.

## 4. Delisted-pair retention cross-check — SAMPLE_ONLY

A bounded cross-check compared 106 unique pair symbols sampled from 17 official pair-removal announcements dated 2023–2026 against the 2026-11-24 exchangeInfo catalogue:
- 105 were present with status BREAK.
- ACMTRY was present with status TRADING.

The ACM/TRY case is a concrete relisting example: Binance announced its removal for 2024-12-27, then announced ACM/TRY as a new trading pair for 2025-11-26. The current TRADING status therefore does not reveal the earlier suspension interval.

Additional legacy checks found 20 current catalogue pair records associated with nine tokens named in Binance token-delisting notices from 2018 and 2019; all 20 were present with status BREAK. The 2018 notice named BCN, CHAT, ICN and TRIG; the 2019 notice named CLOAK, MOD, SALT, SUB and WINGS. The notices said all trading pairs for those tokens would cease, but did not enumerate these 20 pair records individually.

This is meaningful evidence that the current exchangeInfo response retains many older removed pairs. It is not proof that it retains every pair ever listed, and BREAK is not a delisting timestamp. The current catalogue does not provide the listing date, delisting date, suspension interval or relisting history needed for point-in-time membership.

Representative official sources:
- [Binance Delisting announcements category](https://www.binance.com/en-GB/support/announcement/c-161?navId=161)
- [Binance FAQ: how to view delisting information](https://www.binance.com/en/support/faq/detail/2068a768949b4ccab0cd7ac962465ddd)
- [2018 token-delisting notice](https://www.binance.com/en/support/announcement/detail/360017720731)
- [2019 token-delisting notice](https://www.binance.com/en/support/announcement/detail/360023570292)
- [ACM/TRY removal, 2024-12-27](https://www.binance.com/en/support/announcement/detail/f1b4fd16b90947aeaa25721940c4b594)
- [ACM/TRY reopening, 2025-11-26](https://www.binance.com/en/support/announcement/detail/52d33c3e07344e51848368a67b8e584c)
- [2026-09-25 pair-removal notice](https://www.binance.com/en/support/announcement/detail/545ca5ad28254999b793bcf1ddd51f93)

The official [Binance Public Data issue #479](https://github.com/binance/binance-public-data/issues/479) remains open as of this checkpoint. It asks for a complete historical Spot symbol manifest and archive-boundary clarification; the inspected issue snapshot contained user follow-ups but no maintainer answer. This is a lead, not proof that no such internal or undocumented record exists.

## 5. Current evidence classification

| Dimension | Classification | Reason |
|---|---|---|
| Current Spot catalogue | VERIFIED | Full 3,751-symbol response normalized with zero parse errors and retained hashes |
| Current symbol identity / status / quote / permissions | VERIFIED for this snapshot | All returned records normalized |
| Archive prefix listing and pagination | UNAVAILABLE in tested form | HTTP 200 HTML, not XML; pagination not established |
| Direct monthly archive objects | SAMPLE_ONLY | Four accepted symbol-month samples; one incomplete sample |
| Archive checksum and schema handling | SAMPLE_ONLY | Tested files and sidecars passed or were explicitly rejected |
| Product inception | SAMPLE_ONLY | Four first-kline probes only |
| Presence of sampled delisted pairs in current catalogue | SAMPLE_ONLY | 106 pair symbols plus 20 legacy pair records checked |
| Complete delisted-symbol inventory | UNKNOWN | No official completeness guarantee or exhaustive reconciliation |
| Point-in-time membership and listing/delisting dates | UNKNOWN | Current status is not an event history; relisting example demonstrates the distinction |
| Universe-wide historical archive completeness | UNKNOWN | No complete archive index or exhaustive symbol-month validation |

## 6. Next bounded action

The workstream remains ACTIVE at cycle 2/4. The next wake-up should:
1. Inspect whether the official Binance announcement category exposes a stable, paginated historical event list for both new-pair listings and removals; use visible documented page behavior only, not undocumented private APIs.
2. Cross-check a small, deterministic sample of older listing/removal/relisting events against the current catalogue, keeping token delistings distinct from pair removals.
3. Do not repeat the 11-object archive sample. At most one archive object remains under the pilot cap; use it only if a pre-listing negative control has a clear, isolated request path.
4. If no documented completeness guarantee or reproducible event ledger can be established, close INCONCLUSIVE/INFEASIBLE with the exact missing dimensions. Do not admit a strategy or broaden the universe by assumption.

## 7. Engineering verification

Main CI [45397358320](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45397358320) passed on commit c67b6d686475c5bbc96c43516bcd248d442d020e:
- 346 deterministic tests passed in 15.555 seconds.
- Synthetic pipeline smoke test passed.

This is engineering/CI evidence only. It is not historical-data acceptance or strategy validation.
