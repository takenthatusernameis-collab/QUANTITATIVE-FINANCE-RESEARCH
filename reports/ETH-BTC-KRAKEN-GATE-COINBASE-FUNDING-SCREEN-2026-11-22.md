# Kraken, Gate.io and Coinbase funding-source screen — 2026-11-22

## Decision

**Kraken's official historical-funding export has now been retrieved and inspected through the anonymous hosted runner. It is a strong no-purchase candidate for a separate venue pilot, but remains PROVISIONAL_NOT_ACCEPTED:** the ZIP's BTC/ETH files stop at 2026-02-01, and the public API tail has not yet been independently certified as complete. The support page says the export covers available Derivatives markets by trading pair since inception, but that claim does not establish that the currently served ZIP is refreshed through the present. Keep Kraken separate from Binance USDⓈ-M funding and preserve its distinct contract families.

The next step is to audit the full returned API tail and reconcile it with the archive for each exact symbol, as detailed in the hosted-runner inspection section below. No login, account access, region attestation, captcha bypass, API key, purchase, or raw-data commit is required or authorized.

## Kraken — highest-priority free independent candidate

The official [Export historical funding rates](https://support.kraken.com/articles/export-historical-funding-rates) page states that it exports CSV files for all available Derivatives markets, by trading pair, since inception. It exposes an export link to a ZIP asset.

At the initial source screen, the binary ZIP could not be inspected by the available tools. The later authorized hosted-runner probe below resolved that tooling limitation using runner-local temporary storage; no provider restriction or authentication was involved.

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

The 109,980,750-byte raw ZIP was downloaded only to runner-local temporary storage, inspected, and deleted; no raw CSV or ZIP was uploaded or committed. The data remain unaccepted. No paid provider, API key, account, or trading credential was used. No strategy, research gate, live-trading setting, or capital allocation was changed.

## Post-screen CI verification — 2026-11-22 21:34 UTC

The repository's test workflow was updated so documentation-only changes now run the regression suite. CI [run 45072764306](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45072764306) on commit [358f1bc](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/358f1bca7ec574cab325e7ee812580d66df88189) passed 153 deterministic tests and the synthetic plumbing self-test. This validates the documentation/automation changes; it is not empirical funding-data or strategy evidence.


## Hosted-runner archive inspection — 2026-11-22 22:43 UTC

- Authorized issue-comment dispatch [run 45079169566](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45079169566) completed successfully. Its manifest-only/screenshot artifact [14776366974](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45079169566/artifacts/14776366974) is 66,959 bytes with SHA-256 `3f5dc2b5962ce7b20802a930feff3147e3fe76eda504813bfd9b484edc19eb58`. The downloaded ZIP was 109,980,750 bytes, valid, and SHA-256 `65ba6712a6ab657389d2795d3ed77bedb4270841dfe711147ae9df16e366edab`; it was deleted after inspection. No raw data entered Git or the artifact.
- The archive contains 963 members, including 482 macOS metadata members. Four exact BTC/ETH perpetual files were identified from the public instrument catalogue:
  - `PF_XBTUSD` and `PF_ETHUSD`: `flexible_futures`, currently not expired; 30,431 rows each, from 2022-03-22 16:00 UTC through 2026-02-01 00:00 UTC.
  - `PI_XBTUSD` and `PI_ETHUSD`: `futures_inverse`, marked expired in the current instrument response; 38,225 rows each, from 2018-08-31 16:00 UTC through 2026-02-01 00:00 UTC.
- Each file had zero invalid timestamps, duplicate timestamps, out-of-order timestamps, or gaps longer than four hours. The dominant observed intervals were one and four hours. The archive's `tradeable` column contains instrument-symbol strings (for example, `PF_XBTUSD`), not booleans; preserve it as a categorical identifier. The parser now annotates this observed symbol-valued field explicitly, and its regression fixture matches the real export shape. CI [run 45080735068](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45080735068) passed 160 deterministic tests and the synthetic plumbing smoke test.
- The archive's `absolute_rate` maps exactly to API `fundingRate`; `relative_rate` maps exactly to `relativeFundingRate`. For each of the four symbols, the 2025-11-19 through 2026-02-01 overlap contained 1,767 archive and 1,767 API rows: timestamp sets were identical, with zero missing/extra timestamps and zero mismatches in either rate field (maximum absolute difference 0). This is strong overlap-integrity evidence, not proof of complete API history.
- The public API returned 8,841 rows for each PF symbol (2025-11-19 through 2026-11-22 22:00 UTC) and 8,283 rows for each PI symbol (2025-11-19 through 2026-10-30 16:00 UTC). Relative to the archive, that represents 7,074 provisional API-tail rows per PF symbol and 6,516 per PI symbol. The API response itself does not establish its complete historical event population. The export's 2026-02-01 cutoff is stale relative to the probe date, despite the support page's “since inception” description.
- Kraken's official [inverse contract specifications](https://support.kraken.com/au/articles/360022835911-inverse-crypto-collateral-perpetual-contract-specifications-derivatives) and [linear contract specifications](https://support.kraken.com/articles/4844359082772-linear-multi-collateral-derivatives-contract-specifications) distinguish the absolute payout per one contract unit per hour from the relative rate referenced to spot; payout conversion differs by contract family. Do not pool PF linear and PI inverse histories or compare their absolute-rate magnitudes as if they shared units.

**Decision:** the export/API overlap is promising enough to advance to a separate Kraken data-quality pilot, but neither full-history completeness nor empirical acceptance is established. The Binance funding gate remains unchanged. No backtest or strategy execution occurred.

**Next executable task:** extend the bounded probe to audit the entire returned API tail (timestamp validity/order/duplicates, nulls, cadence and gaps), compute the archive/API union and cutoff coverage for each exact symbol, and emit a provenance-complete provisional manifest. Keep PF and PI series separate; do not infer API completeness from overlap alone. Preserve raw data only in approved runner-local/cache storage, upload manifests only, add deterministic tests, and keep the research gate closed until completeness and contract semantics pass.
