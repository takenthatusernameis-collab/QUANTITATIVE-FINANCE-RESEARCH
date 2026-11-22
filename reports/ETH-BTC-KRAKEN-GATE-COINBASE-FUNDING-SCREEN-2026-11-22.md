# Kraken, Gate.io and Coinbase funding-source screen — 2026-11-22

## Decision

**Kraken's official historical-funding export is the strongest newly identified no-purchase candidate for a separate venue pilot. It is not yet retrieved or accepted.** The official support page says it exports CSV files for all available Kraken Derivatives markets, one file per trading pair, with history since inception. The page was last updated 2026-02-24. This is a potentially useful independent dataset, but it must not be substituted for Binance USDⓈ-M funding or mixed into the original Binance experiment.

The next step is a bounded anonymous download/inspection through the repository's authorized hosted browser runner. No login, account access, region attestation, captcha bypass, API key, purchase, or raw-data commit is required or authorized.

## Kraken — highest-priority free independent candidate

The official [Export historical funding rates](https://support.kraken.com/articles/export-historical-funding-rates) page states that it exports CSV files for all available Derivatives markets, by trading pair, since inception. It exposes an export link to a ZIP asset.

The page is readable, but the current inspection tools could not inspect the binary ZIP: the web reader rejected its application/octet-stream content and the current container could not retrieve it. This is a tooling limitation, not evidence that Kraken denies access or that the export is unavailable.

The [Kraken Python SDK documentation](https://python-kraken-sdk.readthedocs.io/en/v3.1.5/futures/rest.html) also illustrates the historical funding-rate method for symbols such as `PI_XBTUSD`, with `timestamp`, `fundingRate`, and `relativeFundingRate` fields. Its examples include records beginning in 2018; the SDK documents an unauthenticated `Funding()` client. Treat this as an API cross-check lead, not as proof of complete retention or as a replacement for the export's actual schema.

### Required bounded probe

1. Open the official export page anonymously in the authorized hosted browser.
2. Identify and activate only the public export link; do not sign in, create an account, accept regional attestations, or interact with trading controls.
3. Capture the ZIP to runner-local temporary storage. Record the final URL, response status, content type, content length, download filename and SHA-256.
4. List archive members and identify exact BTC and ETH perpetual instruments. Record contract type (inverse/linear), quote and settlement currency, contract multiplier, and any symbol/incarnation metadata. Do not assume Kraken symbols or payoff conventions match Binance linear USDT contracts.
5. Inspect CSV headers and units. For every relevant file, record row count, minimum/maximum timestamp, duplicate identities, out-of-order rows, missing intervals, cadence distribution, nulls and rate bounds. Preserve the distinction between `fundingRate` and `relativeFundingRate`.
6. Cross-check a representative overlapping period against Kraken's public historical funding API for the same exact instrument. Reconcile timestamps and values without assuming that agreement proves full-history completeness.
7. Upload only compact manifests, hashes, schema summaries and diagnostics. Do not upload raw CSVs or the ZIP, and do not commit market data to Git.
8. If the export includes both BTC and ETH perpetuals with credible coverage, create a separately identified Kraken venue dataset and its own acceptance gates. Keep its price/funding series, contract mechanics, fees and holdout independent of Binance.

**Acceptance boundary:** the support-page statement alone is not enough. The export must be downloaded, inspected, reconciled and validated before any data acceptance or backtest.

## Gate.io — secondary bounded API candidate

The official [Gate API v4 documentation](https://www.gate.com/docs/apiv4/index.html) documents public `GET /futures/{settle}/funding_rate`. It requires `settle` and `contract`, optionally accepts `limit`, does not require authentication, and returns `t` (Unix seconds) and `r` (funding rate).

The documented parameter list does not expose `from`, `to`, a cursor, or a page token. The page also does not establish historical retention or the maximum usable history. Therefore Gate.io is a possible bounded/recent-history probe, but **not yet a full-history source**. If tested, record the actual limit behavior and oldest returned timestamp; do not infer completeness from a full page or a successful response.

## Coinbase — not currently a self-service ingestion route

Coinbase's [US Perpetual-Style Futures funding explanation](https://help.coinbase.com/en/derivatives/perpetual-style-futures/funding-rate) describes hourly funding calculation and twice-daily processing of cash adjustments. It says historical funding data is available upon request. That is not a documented self-service public export/API for autonomous ingestion, and the US Perpetual-Style Futures product is not automatically equivalent to Coinbase International perpetual contracts. Deprioritize this route unless Coinbase publishes a directly accessible historical dataset or API.

## Existing Binance research gate — unchanged

- Both Binance USDⓈ-M price series are accepted at 59,904/59,904 hourly observations with 82/82 monthly archive checksums.
- Both funding archives contain 7,488 rows across the requested 2020-01-01 through 2026-10-31 period, with an observed 8-hour cadence. Their event semantics and complete payable-settlement population remain `UNVERIFIED` / `PROVISIONAL_NOT_ACCEPTED`.
- Official Binance rules document conditional 1-hour and 4-hour intervals, so an 8-hour-only archive cannot establish the complete historical event population.
- Binance Public Data issue [#517](https://github.com/binance/binance-public-data/issues/517) remains open; the latest visible official-thread update is 2026-11-19, with no Binance team response visible as of this screen.
- No perpetual backtest is justified. The separate Spot-only study remains **NO-GO** for both tested mean-reversion variants; this does not reject every possible ETH/BTC strategy.

## Operational evidence from this inspection

- Latest main SHA at inspection: `954d3cf41217c3d6c7bb806fe674bd330866b6ad`.
- Latest research run [45058324331](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058324331) was triggered by the authorized `issue_comment` command on control PR #2. It restored the verified cache and collected all six January 2024 manifests. It exited fail-closed because the combined empirical gate remained incomplete; no backtest ran.
- Main CI [45058189909](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058189909) passed 153 deterministic tests and the synthetic smoke test.
- Queue guardian [45071274736](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45071274736) completed successfully at 2026-11-22 21:17 UTC, enumerated 297 repository runs completely, and recorded no queue actions/errors. Its detailed inventory is intentionally capped at 50 entries.
- Among the latest 100 Actions runs, the guardian had 2 schedule-triggered successes and 17 successful `workflow_run` triggers (plus one cancelled `workflow_run`). The five-minute schedule is still not delivering its declared cadence; completion-triggered enforcement is the more frequently observed path, but cannot detect a run that never completes.

## Explicit non-actions

No raw funding data was downloaded or accepted. No paid provider, API key, account, or trading credential was used. No strategy, research gate, live-trading setting, or capital allocation was changed.
