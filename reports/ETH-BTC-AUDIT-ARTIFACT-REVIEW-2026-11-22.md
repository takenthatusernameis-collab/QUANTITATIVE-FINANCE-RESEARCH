# ETH/BTC audit artifact review and data-policy decision

**Review date:** 2026-11-22 UTC  
**Status:** Audit artifact review completed; six-input acceptance not met; empirical study remains **INCONCLUSIVE**.  
**Scope:** Historical research and data engineering only. No live trading, capital deployment, credentials, or strategy promotion.

## 1. Execution verification

| Field | Verified value |
|---|---|
| Workflow run | [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383) |
| Run enumeration | `total_count=24`; 24 records returned |
| Event | `issue_comment` / `created` |
| Actor | `takenthatusernameis-collab` |
| Control surface | [Open draft PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2) |
| Exact command | `/qfr-run-eth-btc-data-audit` |
| Comment ID | `7071128780` |
| Workflow path | `.github/workflows/eth-btc-research.yml` |
| Ref / commit | `main` / `96b93aeba313d9a083bb031a949955cb8e606509` |
| Requested range / market | `2020-01-01` through `2026-10-31`; `both` |
| Final run state | Completed; conclusion `failure` at the data-quality step |

The authorization job passed and its logs verified the exact event, open PR #2, exact actor, and whole-body command. The research job checked out the default branch, installed dependencies, and passed the synthetic plumbing test. The real-data audit completed with exit code 2 because required inputs were incomplete. The empirical-study step was skipped. Artifact upload succeeded. The separate harmless-smoke job was skipped for this audit command.

This is a successful command-to-workflow dispatch and artifact-retrieval test, but not a successful data audit or empirical study. The workflow's failure is not a dispatch failure.

## 2. Artifact inventory

GitHub reported one artifact and one was returned:

- Artifact: `eth-btc-research-4`, ID `14730731258`, 23,851 bytes, not expired.
- ZIP SHA-256: `82a8f6e9c6bb82d2ec43af8107a2b2f487321c8a54f84de0bf1693f1da602704`.

The ZIP contains exactly four readable JSON files; it contains no raw OHLCV CSV:

| Artifact file | Bytes | SHA-256 |
|---|---:|---|
| `data/raw/spot_ETHUSDT_archive_manifest.json` | 54,003 | `9cf1f47b594ba8d44bc9b81d9b2eefdd8170ade429c9bfdac70423198fc6b183` |
| `data/raw/spot_BTCUSDT_archive_manifest.json` | 54,003 | `57e86656541a6d815aea26bc8ddf235ac1562afd97b90c16c3fd5cf9eb8f646c` |
| `data/raw/spot_ETHUSDT_gap_reconciliation.json` | 56,692 | `9b9aa56edf0b795903f85b35c770d2c0b91f3eb7499f4b4dc63a7aa26b750872` |
| `reports/generated/data_audit_summary.json` | 113,021 | `deb927043be3118d62d7201f1cf1b0dd61ca100681838f56636612b7057f3a78` |

The consolidated CSV hashes recorded in the two spot manifests are ETHUSDT `10e9e037eef8c34ec2bd98964cc1b8be52cf5c741ca84e7f2925948fea1ac79b` and BTCUSDT `83cd8937026dd8953e8fac244cbbd0be20aeaa32fa94739b1b6cc3d88f2dd0fd0`. The CSV files themselves were not uploaded.

No USDⓈ-M kline manifests or funding manifests were present because those downloads failed before the pipeline wrote their manifests. This is an audit-output persistence gap as well as a data-access/parsing blocker.

## 3. Spot-series findings

| Series | Monthly archives | Checksums verified | Rows | Expected | Missing hours | Duplicates |
|---|---:|---:|---:|---:|---:|---:|
| Spot ETHUSDT | 82 | 82 | 59,873 | 59,904 | 31 | 0 |
| Spot BTCUSDT | 82 | 82 | 59,873 | 59,904 | 31 | 0 |

Both spot series have the requested first and last timestamps, no missing monthly archive, and a six-hour maximum spacing between observed bars. Their 31 missing timestamps are exactly the same. The BTC result is an independent monthly-manifest result, not an independent daily-source reconciliation.

### Complete 31-hour inventory

The 31 missing hours form 15 contiguous intervals:

| UTC date | Missing UTC hour(s) | Hours | Daily archive rows | Daily archive SHA-256 |
|---|---|---:|---:|---|
| 2020-02-09 | 02:00 | 1 | 23 | `02d670705fcac1689a5bc784003f20ae629902783adc682d382a5fe4e97c21b0` |
| 2020-02-19 | 12:00–16:00 | 5 | 19 | `a07b8dec3632c3e7ea5ff7dac48f12b3638283f3ee34564870fe9fb07830c7ad` |
| 2020-03-04 | 10:00 | 1 | 23 | `19b5f8b32c4664cc3f5600a3390b047488e316a3898a35739d7b1657a553dd7d` |
| 2020-04-25 | 02:00–03:00 | 2 | 22 | `f5f4fb6e3cbcbd15ec8a5c3ba1116482a58c17b05e332b4cac8b15330d19c8d0` |
| 2020-06-28 | 02:00–04:00 | 3 | 21 | `df4b39a2cc91cfb4ad1040b8875ed943971093d9eee0f7cab615f9fe952e66be` |
| 2020-11-30 | 06:00 | 1 | 23 | `305d51854828ef12ec6143e2b0e193c1dc17745a27bb0816919c6e59b985a1c9` |
| 2020-12-21 | 15:00–17:00 | 3 | 20 | `1861baf64d3678293f7d6c5ca4b2cb3444d439dcf80cbb7fe2da0f6c87a07878` |
| 2020-12-25 | 02:00 | 1 | 23 | `68b57906d9977cf7cdd420e1813918295a8d526bdf39299a9d729de9706113c6` |
| 2021-02-11 | 04:00 | 1 | 23 | `f27d5d4a2af7149a77689e69fe2905cb6d9eefb4e8b3d390558f4b8dc825e734` |
| 2021-03-06 | 02:00 | 1 | 23 | `d80d3d5fc9e4e6b102a0d95955672f18737a9f0d032e57f99413615daa294c50` |
| 2021-04-20 | 02:00–03:00 | 2 | 22 | `61b1ea57906dc9aacddf7fd790f3550f6bb226d1ac72093398667941d3c38ad4` |
| 2021-04-25 | 05:00–07:00 | 3 | 21 | `e516945eccba21b90c4d97ea2a580c65551e2d4c378f5313e569babb7a7815d4` |
| 2021-08-13 | 02:00–05:00 | 4 | 20 | `fd21c14c628ae95fcca06f493da507a796ba216a4f1f4468077d23161f2b3901` |
| 2021-09-29 | 07:00–08:00 | 2 | 22 | `a9f1eb29c0d710997ddeccb461293fc1c395d349901fcee1322aaeb4965b1232` |
| 2023-03-24 | 13:00 | 1 | 23 | `7b9d19487c37b354003717872987ae5ecb2178b4ff0de1ecdd5a5c84da2f10b1` |

The 15 daily Spot ETH archives were all downloaded and all 15 checksum sidecars verified. None of the 31 missing timestamps appears in its corresponding daily archive. The monthly archives and daily archives therefore agree on the absence of those rows; checksum verification proves archive integrity, not that the omitted intervals were no-trade intervals.

### REST reconciliation limitation and classification defect

All 31 per-hour requests to `https://api.binance.com/api/v3/klines` failed with HTTP 451. The recorded `api_status` is null and each entry contains an `HTTPError: 451` message. No successful empty REST response was obtained.

The current reconciliation code nevertheless assigns all 31 rows to `absent_from_both_official_representations_unresolved`. That label conflates an API access failure with a successful API response containing no candle. The correct result is **API unavailable; daily archive candle absent; final classification unresolved**. The code also leaves the top-level `daily_archives` object empty even though the 15 daily archive records are embedded in the per-gap entries. Both defects must be fixed before relying on reconciliation summaries.

A supplementary connected Binance spot-kline read returned neighboring ETHUSDT candles but no candle rows inside the 15 gap intervals. It did not expose sufficient raw HTTP/status provenance to replace the failed hosted-runner evidence. The connected aggregate-trades action returned empty results for both missing windows and adjacent known-candle control windows, so that action failed its positive-control check and was not accepted as no-trade evidence.

## 4. USDⓈ-M and funding findings

| Input | Result | Exact blocker |
|---|---|---|
| USDⓈ-M ETHUSDT 1h | Failed | `ValueError: Invalid open_time values` in the January 2022 monthly archive |
| USDⓈ-M BTCUSDT 1h | Failed | `ValueError: Invalid open_time values` in the January 2022 monthly archive |
| ETHUSDT funding | Failed | HTTP 451 from `fapi.binance.com/fapi/v1/fundingRate` |
| BTCUSDT funding | Failed | HTTP 451 from `fapi.binance.com/fapi/v1/fundingRate` |

The kline parser reads CSV with `header=None` and rejects any nonnumeric `open_time`. A header/schema variant is a plausible explanation for the January 2022 failures, but the exact archive row was not present in the uploaded artifact; this cause is **not yet confirmed**. The two funding API failures are access failures, not evidence of missing funding events. No funding or USDⓈ-M completeness claim is supported.

The summary reports `INCOMPLETE`, `complete=false`, `price_series_complete=false`, `funding_series_complete=false`, and `reconciliation_complete=false`.

## 5. Missing-bar data policy

**Decision: preserve all 31 intervals as unresolved and keep the empirical gate closed.**

- Do not synthesize OHLCV rows, forward-fill prices, assign zero returns or zero volume, or silently remove these timestamps.
- Do not call the gaps confirmed no-trade intervals. The official daily archives omit the candles, while the hosted-runner REST requests were blocked; the available aggregate-trades connector failed its positive-control check.
- Do not merely relax the hourly completeness check. `load_pair` currently requires a complete hourly index, while the backtest uses `pct_change()` on successive observed opens. If the gate were relaxed without changing the return model, a two-to-six-hour price change could be treated as one hourly return, distorting holding periods and hourly annualization.
- First establish trade-level evidence using a working official Spot `aggTrades` endpoint or checksum-verified daily aggregate-trade archives, including known-active positive-control windows.
- If a no-trade interval is established, pre-register and test an event-time/irregular-time treatment that preserves the actual elapsed duration and prevents signals or executions from being invented during unobservable hours.

Binance documents a public market-data-only Spot host, `data-api.binance.vision`, including `/api/v3/klines` and `/api/v3/aggTrades`; the next task should test it against both missing intervals and known-active control intervals. The official Binance public-data repository documents daily/monthly archives, `.CHECKSUM` sidecars, and the Spot timestamp-unit change to microseconds from 2025-01-01:

- https://developers.binance.me/en/docs/products/spot/faqs/market_data_only
- https://developers.binance.com/en/docs/products/spot/rest-api
- https://github.com/binance/binance-public-data

## 6. Verification and decision

- CI run [44963445206](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963445206), run 20, passed the deterministic-unit-test step and synthetic plumbing smoke-test step.
- The audit run itself passed its synthetic plumbing smoke test and uploaded the four-file artifact.
- No strategy backtest ran and no cointegration, return, Sharpe, drawdown, funding-PnL, or other empirical performance result was generated.
- The research conclusion remains **INCONCLUSIVE**. There is no strategy GO/NO-GO decision. The next action is the ingestion and no-trade validation task: [ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md](../tasks/ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

Raw OHLCV data remain outside Git. The private run artifact is retained as execution evidence; the repository contains only manifests, hashes, code, and reports.