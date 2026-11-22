# ETH/BTC Funding Provider Screen — 2026-11-22

## Decision

**Bitget full-history funding download is not substantiated and is blocked from the US-hosted runner by a regional restriction. OKX has an official archive page advertising funding history since March 2022, but its file schema/scope remain unverified. Market History remains the strongest cost-first candidate for the Binance study; it is not accepted and requires owner authorization for a key and paid minimum purchase. No request, purchase, credential handling, raw download, or perpetual backtest was performed.**

## Bitget: correction to the previous route assumption

- Official [Data Download Center](https://www.bitget.com/legacy-docs/uta/data-download-center) maps market downloads to the [History data download](https://www.bitget.com/data-download) page.
- That page lists **candlestick charts, transaction history, and depth data** for Spot and Futures. Funding-rate history is not listed as a downloadable market-data category.
- The official [Funding Rate History API documentation](https://www.bitget.com/docs/catalog/market/derivatives) states the API returns the **last 90 days**.
- Bitget's [historical funding-rate website guide](https://www.bitget.com/support/articles/12560603837210) explains navigation to the history tab and filters by futures type, pair and time period. It does not document a CSV/export control.
- The funding page is dynamic and was not inspected through a real browser. Therefore, the accurate finding is **full-history funding download not documented/substantiated**—not a claim that no UI export exists.

## Separate-venue OKX pilot (not a Binance substitute)

The official [OKX Historical Market Data](https://www.okx.com/historical-data) page renders anonymously and exposes a Funding rate Download button. The page advertises historical perpetual funding from **March 2022 onwards**. A bounded Playwright probe recorded the page, controls, and screenshot; the download button was not clicked. The page's download scope, exact file format/schema, instrument coverage, and event completeness remain unverified.

OKX's official [Get funding rate history API](https://www.okx.com/docs-v5/en/#rest-api-public-data-get-funding-rate-history) returns at most **three months** per request, up to **400 records**, with `before`/`after` pagination. It exposes `fundingTime`, forecast `fundingRate`, and actual `realizedRate`; interval changes must be inferred from event timestamps. This API is useful for recent cross-checks, not the full archive.

A separate-venue OKX study may be viable from March 2022, but it cannot replace Binance USD-M inputs in the original hypothesis. No data were downloaded or accepted.

## Ranked provider candidates


| Rank | Provider | Coverage claim / access | Cost and limitation |
|---|---|---|---|
| 1 | [Market History](https://getmarkethistory.com/docs/funding/) | Binance USD-margined perpetuals from contract first month, delisted contracts included; row-level interval (1h/4h/8h); monthly checks against Binance files; daily update | Funding requires API key and paid bars; no keyless funding sample. Site states $5 minimum one-time purchase of 1M bars, bought bars never expire. **Candidate only**; source methodology/completeness still needs validation. |
| 2 | [CandleFeed](https://candlefeed.ai/data/binance/) | Advertises funding from Jan 2020 and full-history on Builder | $29/month Builder; Free is limited to five symbols and 30 days, plus 100 free API calls. |
| 3 | [HexaTape](https://hexatape.com/history/) | Advertises funding history from 2019 | $249/month API; free 30-day samples. Too expensive as the first route for this narrow two-symbol study. |

### Market History claims requiring independent verification

The vendor describes crypto/perps funding rows as settled event rates, one row per funding event, with timestamp, decimal rate, and interval_h (1, 4, or 8). It claims all Binance USD-margined perpetuals since late 2019, including delisted contracts, and says monthly rows are rechecked against Binance monthly files. This is promising because the archive's 8-hour-only funding manifests are unable to certify historical 1-hour/4-hour settlements.

However, this is a vendor claim. The provider's underlying event capture, full settlement-population guarantee, symbol-incarnation coverage, source independence, and reconciliation behavior around documented schedule changes are not yet independently established. Reconciliation against Binance monthly files alone cannot establish completeness for events missing from those archives.

### Cost / authorization boundary

The provider's pricing page states a $5 minimum purchase for 1 million bars, purchased bars do not expire, and funding data requires purchased bars rather than the free monthly bar allowance. Two 8-hour contracts over the study period would require only roughly 15,000 events, but the exact row count and charge must be confirmed after querying the provider's coverage/price estimator. No API key is present in the research environment, and **no data purchase is authorized**.

### Next bounded probe (only after explicit owner authorization)

1. Use an owner-created, least-privilege provider key stored as a GitHub Actions secret; never place it in repository files, logs, reports or artifacts.
2. Confirm the provider's exact symbol coverage, first/last timestamps, contract identity, event semantics, and quoted cost for BTCUSDT and ETHUSDT before requesting data.
3. Query only BTCUSDT and ETHUSDT, 2020-01-01 through 2026-10-31, follow every cursor, and save only compact manifests plus page/response hashes. Keep raw data in runner-only storage.
4. Check row counts, timestamp ordering, duplicates, interval distribution (1/4/8h), coverage, rate finiteness, and symbol labels. Do not infer missing settlements as zero.
5. Reconcile representative dates against Binance monthly files and independent event-time evidence around schedule-change dates. Preserve disagreements and source provenance.
6. Do not promote the provider or open the funding gate without complete population/contract-incarnation evidence and deterministic acceptance tests.

## Official/vendor sources (reviewed 2026-11-22)

- OKX Historical Market Data: https://www.okx.com/historical-data
- OKX public funding-rate-history API: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-funding-rate-history
- Bitget anonymous UI probe: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021291959 (HTTP 200; blocked by regional restriction dialog; no bypass)
- OKX anonymous UI probe: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021709395 (page rendered; button identified; no download)
- OKX probe artifact: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021709395/artifacts/14753937981 (SHA-256 `4d85dbba73b3fae65770d9d3635a4557cab51768e8127b19cf7047200684cce4)
- CI after probe/classifier/OKX workflow changes: [45021633877](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021633877), [45021446714](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021446714), both passed.


- Bitget Data Download Center: https://www.bitget.com/legacy-docs/uta/data-download-center
- Bitget historical data download page: https://www.bitget.com/data-download
- Bitget funding API docs (90-day limit): https://www.bitget.com/docs/catalog/market/derivatives
- Bitget website guide: https://www.bitget.com/support/articles/12560603837210
- Market History funding docs: https://getmarkethistory.com/docs/funding/
- Market History crypto funding guide: https://getmarkethistory.com/docs/guides/crypto-funding-rates/
- Market History pricing: https://getmarkethistory.com/
- CandleFeed Binance data page: https://candlefeed.ai/data/binance/
- HexaTape history API page: https://hexatape.com/history/
