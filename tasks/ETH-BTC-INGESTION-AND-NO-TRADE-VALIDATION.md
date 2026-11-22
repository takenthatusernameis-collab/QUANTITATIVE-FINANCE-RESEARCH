# Pending Task: Repair ETH/BTC Data Ingestion and Validate No-Trade Intervals

**Status:** Pending  
**Priority:** High  
**Type:** Data-source resilience, parser correctness, missing-observation policy, and reproducible audit  
**Scope:** Historical research/backtesting only. No live orders, capital deployment, live credentials, or strategy promotion.

## Objective

Remove the verified ingestion bottlenecks without weakening the ETH/BTC research specification or inventing observations. Produce a provenance-complete audit of all six required inputs and a defensible, tested treatment for the 31 synchronized Spot gaps before any empirical backtest is allowed.

Start from [the 2026-11-22 audit report](../reports/ETH-BTC-AUDIT-ARTIFACT-REVIEW-2026-11-22.md), the current pipeline `research/run_eth_btc.py`, and [the adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md).

## Verified starting evidence

- Audit run [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383) successfully passed the exact-actor PR-comment authorization gate, default-branch checkout, dependency installation, and synthetic smoke test. The real-data audit ended with exit code 2; the empirical step was skipped.
- The artifact ZIP SHA-256 is `82a8f6e9c6bb82d2ec43af8107a2b2f487321c8a54f84de0bf1693f1da602704` (artifact ID `14730731258`). It contains two Spot manifests, one ETH Spot gap-reconciliation manifest, and one audit summary; no raw CSV.
- Spot ETHUSDT and BTCUSDT each have 82/82 monthly archives checksum-verified, no missing archive months, 59,873 rows against 59,904 expected, 31 missing hours, and zero duplicate timestamps. The two symbols have the same missing timestamps.
- Fifteen daily ETH Spot archives were downloaded and checksum-verified; none contains the corresponding missing candle. All 31 hosted-runner REST requests to `api.binance.com` failed with HTTP 451.
- The current gap classifier incorrectly conflates a failed REST request with a successful empty response. The top-level `daily_archives` manifest is also not populated, even though per-gap entries contain the 15 archive records.
- USDⓈ-M ETHUSDT and BTCUSDT kline parsing fails at the January 2022 archive with `Invalid open_time values`. The exact CSV schema/header condition is not yet verified.
- ETH and BTC funding API retrieval both fail with HTTP 451. No funding manifests were emitted.
- The current backtest uses successive-observation `pct_change()` and hourly annualization. Simply allowing missing timestamps would treat a multi-hour change as one hourly return and is not acceptable.

## Mandatory alternative-first execution rule

**Do not wait for manual activation or confirmation for routine historical quantitative research.** The agent must use the verified control-PR command, an authorized API route, or another existing connected trigger to start audits and backtests itself. "Wait for the owner to click Run workflow/confirm the backtest" is a task failure. Historical backtests are research-only; they do not authorize live trading, capital deployment or strategy promotion.

The `/qfr-run-eth-btc-empirical` command now performs a non-fail-fast preflight over all four price series and both funding histories. The strategy step is conditional on preflight success. The workflow requires no manual confirmation; an incomplete preflight stops strategy execution and uploads diagnostic manifests.

A data-quality failure must not freeze the whole research program. It must trigger a change in the approach. The current Binance-specific plan is one candidate route, not a mandatory architecture. Test a representative slice and positive control, then change provider, endpoint, archive format, market-data representation, venue, time resolution, or model when evidence justifies it. After two independent identical non-transient failures on one route, stop repeating it. Preserve the exact error and move to a materially different route.

**Required alternative data construction:** independently source ETH/USD and BTC/USD price series from an authorized provider (preferably the same venue/provider and identical bar conventions), then construct the cross-rate from synchronized observed prices:
`ETHBTC_t = ETHUSD_t / BTCUSD_t`, or equivalently the log spread `ln(ETHUSD_t) - ln(BTCUSD_t)`. Validate quote currency, timestamps, timezone, OHLC construction, observation completeness, duplicates, market conventions, source hashes and fees. Use only common observed timestamps; do not forward-fill or invent candles. If mixing USD with USDT/USDC, retrieve and validate the conversion rate rather than assuming parity. Compare the resulting synthetic cross-rate with a direct ETHBTC feed where feasible. This is a distinct data construction whose specification and acceptance criteria must be recorded.

If the ETH/BTC ratio remains impractical with credible accessible data, do not spend unlimited cycles preserving the original formulation. Mark that exact experiment INCONCLUSIVE/INFEASIBLE, and formulate a separate feasible model or research hypothesis with its own pre-registration and validation. A different model is preferable to repeatedly implementing an unrealistic one, but never describe a different study as validation of the original.

Do not bypass legal/provider access restrictions (including HTTP 451); switch to a lawful, authorized provider. Do not weaken the original data gates, fabricate missing observations, or call a restricted endpoint through an evasive proxy. Continue independent research while one route is blocked.

## Required work

### 1. Repair Spot REST access and independently validate all 31 gaps

- Test Binance's official public market-data-only host `https://data-api.binance.vision` for `/api/v3/klines` and `/api/v3/aggTrades`. The official documentation lists these endpoints on that host: https://developers.binance.me/en/docs/products/spot/faqs/market_data_only.
- Test a small missing-hour window and a known-active adjacent control window first. Record exact URL, parameters, HTTP status, retrieval time, response count, returned open times, and response/content hashes.
- Then validate all 31 timestamps for both ETHUSDT and BTCUSDT. A successful empty kline response alone is not proof of no trading.
- Use aggregate trades as the decisive trade-activity cross-check. The historical aggregate-trades connector previously returned empty results for both missing and known-active controls; do not repeat that route without a successful positive control.
- If the REST aggregate-trades route is blocked or unreliable, retrieve the corresponding official Binance Vision daily `aggTrades` archives for the 15 affected dates and both symbols, verify every `.CHECKSUM`, and inspect all trades in each missing hour. Keep the download bounded and resumable.
- Distinguish at least: candle present in one official source; candle absent but trades present; no trades in all validated trade sources; source request failed; source disagreement. A failed request must never be classified as an empty successful response.
- Persist all per-gap evidence and populate the top-level daily-source inventory. Set `reconciliation_complete=true` only when every required source check completed successfully and every gap has a defensible classification.

### 2. Define and test the missing-observation policy

- Do not create synthetic OHLCV candles, forward-fill, set missing returns or volume to zero, or silently drop intervals.
- If trade-level evidence confirms a no-trade interval, preserve the raw timestamp gap and design an explicit, pre-registered event-time/irregular-time policy. It must retain elapsed duration, avoid inventing signal or execution opportunities, and correctly handle funding events and holding periods across gaps.
- If the gap is not conclusively a no-trade interval, keep the series incomplete and the study **INCONCLUSIVE**.
- Add tests proving that an elapsed two-to-six-hour interval cannot be counted as a one-hour return or one-hour holding period. Do not simply relax `load_pair`'s continuity check.
- Evaluate the policy using synthetic fixtures only; do not inspect strategy performance to choose among missing-data treatments.

### 3. Fix USDⓈ-M kline archive parsing

- Inspect the exact January 2022 ETHUSDT and BTCUSDT archive CSV members and their first/last rows, column count, optional header, timestamp scale, and numeric validity.
- Support only explicitly recognized schemas (including a header row if the source actually uses one). Never drop arbitrary malformed rows to make parsing pass.
- Validate timestamp units and date bounds, monotonicity, duplicates, finite OHLCV values, expected archive coverage, and checksum sidecars.
- Add deterministic tests for header/no-header archives, millisecond/microsecond timestamps, invalid rows, and the exact January 2022 failure fixture.

### 4. Replace or adapt funding retrieval

- Diagnose the HTTP 451 response to `fapi.binance.com` and test materially different official data routes rather than retrying the same endpoint unchanged.
- Evaluate the official Binance Vision USDⓈ-M monthly `fundingRate` archive route and its checksum sidecars. Inspect the actual CSV schema before implementing the parser; do not assume a fixed eight-hour cadence.
- Audit ETH and BTC funding from 2020-01-01 through 2026-10-31 for requested/observed bounds, pages or archive months, timestamp normalization, duplicate events, chronology, cadence/gaps, and content hashes.
- Missing funding events must remain missing/failed evidence; never substitute zero funding.

### 5. Make the non-fail-fast audit genuinely complete

- Ensure every one of the four price series and two funding series receives a manifest even when retrieval or parsing fails. Each manifest must contain requested bounds, source, status, exact error, partial row counts when available, and hashes of all acquired inputs.
- Keep the summary explicit about total inputs attempted, successful manifests, failed inputs, and returned artifacts. Do not let an exception prevent later independent inputs from being audited.
- Ensure the uploaded artifact contains the six manifests, audit summary, and gap-reconciliation evidence while excluding raw market-data CSVs.

### 6. Verify and hand off

- Add deterministic regression tests for source failover, positive controls, gap classification, parser schemas, funding completeness, elapsed-time return handling, and failure-manifest persistence.
- Run the complete research test suite and synthetic smoke test. Record exact CI run IDs and commit SHA.
- Run the audit and, when the selected study's machine-checkable gates pass, launch the empirical backtest through the agent-triggered [control PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2) command `/qfr-run-eth-btc-empirical`. No human confirmation is required for historical research. The backtest must still stop automatically on invalid data. If the ETH/BTC source path remains infeasible, run a separately preregistered alternative dataset/model rather than waiting indefinitely.
- Inspect and hash the new artifacts. Update README, reports, this task, and the next handoff.
- Keep raw market data out of Git. No live trading or capital deployment.

## Acceptance criteria

1. All 31 Spot gaps have source-backed classifications for both ETHUSDT and BTCUSDT, including a working positive-control test for trade-level evidence.
2. All four hourly price series and both funding histories have independently complete, checksum/provenance-backed manifests.
3. The missing-observation policy is pre-registered, elapsed-time correct, and covered by deterministic tests; no synthetic bars or zero-return assumptions are introduced.
4. All six manifests and the summary are present in the audit artifact, including explicit failure records where applicable; no raw CSV is uploaded.
5. CI and the audit-only workflow pass their declared engineering and data-quality gates.
6. The repository records the exact run, commit, artifact, hashes, limitations, and one next task.

Until every criterion passes, keep the original Binance ETH/BTC experiment **INCONCLUSIVE** and do not backtest that incomplete dataset. Do not block all research: independently implement and backtest a separately specified alternative (for example, synchronized ETH/USD divided by BTC/USD from another authorized provider) once its own data and methodology gates pass. No manual confirmation is required for the agent to launch any historical backtest within its authorized scope.