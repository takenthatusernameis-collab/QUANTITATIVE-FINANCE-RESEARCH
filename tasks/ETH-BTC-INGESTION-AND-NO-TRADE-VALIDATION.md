# Pending Task: Repair ETH/BTC Data Ingestion and Validate No-Trade Intervals

**Status:** Pending  
**Priority:** High  
**Type:** Data-source resilience, parser correctness, missing-observation policy, and reproducible audit  
**Scope:** Historical research/backtesting only. No live orders, capital deployment, live credentials, or strategy promotion.

## Objective

Remove the verified ingestion bottlenecks without weakening the ETH/BTC research specification or inventing observations. Produce a provenance-complete audit of all six required inputs and a defensible, tested treatment for the 31 synchronized Spot gaps before any empirical backtest is allowed.

Start from [the 2026-11-22 audit report](../reports/ETH-BTC-AUDIT-ARTIFACT-REVIEW-2026-11-22.md), the current pipeline `research/run_eth_btc.py`, and [the adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md).


## Autonomous execution and adaptive recovery requirements

This is the current controlling task for the unresolved ETH/BTC input and gap problem. Execute all safe steps agent-initiated within existing permissions; never wait for routine user activation, approval, or a workflow UI click. Follow the repository-wide [Adaptive Autonomous Research Execution Standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) and [dispatch runbook](../docs/CHATGPT-WORKFLOW-DISPATCH.md).

- Audit every independent input even when another fails. Continue useful parser, schema, test, provider and methodology work while any one source is blocked.
- After the first meaningful source/parser/runner/dispatch failure, diagnose it and test materially different alternatives. After two independent identical non-transient failures on the same route, stop that route. Use positive controls, negative controls, provenance and immutable hashes.
- If the Binance route remains inaccessible, compare official archive/trade-level construction, an authorized alternative provider, and a separately specified synchronized ETH/USD divided by BTC/USD series. A distinct source or model is a distinct experiment with its own acceptance criteria; do not merge its results into the original Binance study.
- Preserve unresolved gaps and the original experiment's **INCONCLUSIVE** status. Never fabricate, forward-fill, silently drop observations, infer zero funding, or weaken a gate to force execution.
- For any supported safe workflow, cancel run-level `queued`/`pending` status older than 15 minutes unless an earlier run in the exact same concurrency group is actively `in_progress`. A queued dependent job inside an already running workflow is not covered.
- If cancellation is unavailable or fails, record `CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION` and initiate one materially different alternative attempt independently. Give it a separate attempt ID, execution route, working state, cache, manifests, artifacts and output paths. Keep it read-only and prevent shared writes.
- If a workflow is merely waiting for a verified earlier same-group predecessor, preserve it and record that predecessor ID. Never cancel an in-progress run just to clear the queue.
- If an independent alternative also fails, diagnose its new cause; do not repeat it unchanged or create a duplicate attempt storm. Continue to the next materially different safe research slice.
- No live orders, capital deployment, live credentials, custody changes or automatic strategy promotion.

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

## Implementation progress — 2026-11-22

- The routine-manual-gate rule is now explicit in the repository README and adaptive execution standard. Waiting for a user to click or confirm an ordinary historical backtest is defined as **FAILURE**; pause only a specific action that crosses a real security/legal/authorization boundary.
- The control workflow now includes `/qfr-run-eth-btc-empirical`; it runs an all-six-input preflight before strategy computation and needs no routine human confirmation.
- The gap reconciliation probe now uses Binance's documented market-data-only host `data-api.binance.vision`, audits both Spot symbols, and distinguishes API request failure from a successful empty response. See commits `1894e11084af9054a5d5025f9a355c88899a6a13` and `b2e7e12e496edb520a849283c3416f8177f820ef`.
- CI runs `44965875648` and `44965889395` were queued at this update; their outcomes remain unverified. The new endpoint also remains untested until its audit run produces request/positive-control evidence.
- The alternative data-design path is mandatory if the Binance route remains unavailable: source synchronized ETH/USD and BTC/USD independently, compute the observed ratio, validate quote currency and timestamp compatibility, and pre-register the resulting model as a separate experiment. If this is not implementable with credible evidence, replace the hypothesis/model instead of repeating the same failed ingestion path.

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

### 4. Funding route replacement — implemented; verification pending

- The HTTP-451 `fapi.binance.com/fapi/v1/fundingRate` route has been removed from `research/run_eth_btc.py` in favor of the official Binance Vision USDⓈ-M monthly `fundingRate` ZIP route. The implementation requires a verified `.CHECKSUM`, parses the candidate `calc_time/funding_interval_hours/last_funding_rate` schema, validates UTC month bounds and numeric/interval fields, and writes archive hashes and per-month failures.
- Deterministic regression tests cover checksum rejection, schema ingestion, the pipeline's `fundingRate` output contract, and fail-closed semantics. Latest test run [44973336934](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44973336934) was pending at the last check; do not claim a pass until verified.
- Next execute a bounded representative ETH and BTC month probe via the authorized hosted runner. Confirm the actual archive exists, its published checksum matches, the production schema matches the parser, and timestamps/interval metadata are internally consistent before expanding to the full requested history.
- Binance public-data issue [#517](https://github.com/binance/binance-public-data/issues/517) leaves settlement-population/event semantics unresolved. The downloader therefore retains data/manifests with `event_semantics=UNVERIFIED` and `completeness_status=PROVISIONAL_NOT_ACCEPTED`, then raises to block empirical use. This is an intentional fail-closed state, not a successful funding-completeness result.
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
## Latest audit execution — 2026-11-22

Agent-triggered audit run [44969155096](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44969155096) completed with the expected data-quality failure on commit `41b85ddde32e346cb705d5cd4843ad6b003dda95`. Authorization, default-branch checkout, dependency installation and synthetic plumbing test passed. The all-series audit ran; empirical preflight/backtest steps were skipped; artifact upload succeeded.

- Artifact ID: `14732529254`; name `eth-btc-research-9`; size 31,488 bytes; ZIP SHA-256 `dbf237352b0067ff043d36b04c90a843a233b7430cbe80ceddef97814c5718a3`.
- Spot ETHUSDT: 59,873 of 59,904 hourly rows; 31 missing hours; zero duplicates; all requested date bounds observed.
- Spot BTCUSDT: 59,873 of 59,904 hourly rows; same 31 missing hours; zero duplicates; all requested date bounds observed.
- For both Spot symbols, all 31 gap-specific requests to `https://data-api.binance.vision/api/v3/klines` returned HTTP 200 with zero rows. The corresponding daily kline archives also contained no candle for the requested hours. Each gap is correctly classified `both_kline_sources_empty_trade_status_unverified`; this is **not proof of zero trades or a confirmed no-trade interval**.
- USDⓈ-M ETHUSDT and BTCUSDT parsing both failed on the January 2022 monthly archive with `Invalid open_time values`.
- Both USDⓈ-M funding API retrievals failed with HTTP 451 from `fapi.binance.com`; this remains a route restriction/failure, not evidence of zero funding.
- The uploaded artifact contains the summary, two Spot monthly manifests and two Spot gap-reconciliation manifests. The summary contains all six input statuses, but dedicated failed-input manifests for the two USDⓈ-M price series and two funding series are absent from the ZIP; repair this artifact/manifest persistence gap.
- Overall status remains **INCOMPLETE / INCONCLUSIVE**. No empirical backtest ran and no strategy performance metrics were generated.

### Required adaptive next steps

1. Do not repeat the identical kline REST queries or infer zero activity. Full audit run 44971182002 found 31 missing Spot hours per symbol. For all 31, the daily archive had no candle and the aggregate-trade positive control failed; the aggregate-trade endpoint returned HTTP 200 with zero rows. Every gap remains aggregate_trade_positive_control_failed_unresolved. This is not evidence of no trading. Use a materially different source or data construction with known-active positive controls; do not repeat the same one-hour probes and classify the gaps as no-trade.
2. Production parser compatibility is verified by full audit run 44971182002: all 82 monthly archives per symbol for all four price series downloaded and passed checksums, with zero parse errors. Both USDⓈ-M series have 59,904/59,904 hourly bars, zero gaps and zero duplicates. Both Spot series parsed to 59,873/59,904 bars; their remaining 31 gaps each are a reconciliation issue, not a parser failure. Preserve the unresolved classification for every missing hour.
3. **Implemented, not yet accepted:** the blocked `fapi.binance.com` route has been removed in favor of monthly Binance Vision USDⓈ-M `fundingRate` archives. The implementation requires `.CHECKSUM` verification, validates the three-column `calc_time/funding_interval_hours/last_funding_rate` schema and UTC month bounds, records per-month hashes/provenance, and preserves a consolidated CSV/manifest. It deliberately records `event_semantics=UNVERIFIED` and `completeness_status=PROVISIONAL_NOT_ACCEPTED`, then fails closed. Next run a bounded representative January 2024 archive probe through the authorized hosted runner and independently reconcile settlement-population semantics before any funding completeness claim.
4. **Implemented and verified for run 44971182002:** artifact 14733503636 contains all six input manifests, the data-audit summary and both Spot gap-reconciliation manifests (nine files total); no raw CSVs were uploaded. Retain this check for the new funding-archive route and verify that its per-symbol manifests are present even when the event-semantics gate rejects the series.
5. In parallel, evaluate a separately specified synchronized ETH/USD divided by BTC/USD research dataset from an authorized provider. Keep it as a distinct experiment with independent data gates; do not blend it with the incomplete Binance sample.
6. Run the full empirical study only when that experiment's own six-input/data/methodology gates pass. The original Binance ETH/BTC conclusion remains **INCONCLUSIVE** until its own evidence is sufficient.



## Implementation and verification update — 2026-11-22 03:31 UTC

- The Spot aggregate-trade gap path now requires a finite positive-volume known-active control and records the selected timestamp/source/volume. Commits [96979f0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/96979f0bf27bdb38e58151e4987760bfffecf6be) and [42138f4](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/42138f490aab8274c575748d9a12ab6c81c6e8ef) implement and test positive-volume control selection. Production gap reconciliation remains unverified.
- The kline parser supports recognized header/no-header schemas and timestamp aliases/units, and the six-input audit writes fail-closed manifests. These code paths have deterministic coverage, but production archive compatibility and all-six artifact persistence still require a hosted-runner audit.
- The blocked funding REST route was replaced by checksum-verified monthly Binance Vision fundingRate archives in [9850f2d](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9850f2d2598ffcd1d25c0fefc1ce2b6e0f997977), with UTC month-bound correction [e3c883e](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/e3c883edf8c55a9df70b232e39b3905aa3295074), pipeline-schema mapping [7384c15](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/7384c15cbc8b0cf3c4a712132bd5cc119aca541e), compatibility assertion [86dcd42](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/86dcd42cb06e220f11fd7b3197e6c3fea9392f1e), and manifest provenance correction [261a235](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/261a2351a040d7d0f3f36f0c7c1a1e46d7b8a831). This is an implemented route replacement, not accepted funding history.
- Public Binance issue [#517](https://github.com/binance/binance-public-data/issues/517) remains open (last updated 2026-11-19; four comments). No Binance-team clarification is visible in the current public comment history. Historical settlement-population completeness, contract-incarnation coverage and decision-time schedule semantics therefore remain unresolved; keep the archive provisional.
- Test run [44973336934](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44973336934) failed one of 46 tests because its synthetic funding CSV fixture encoded literal backslash-n sequences. The fixture was corrected in [ec74947](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ec74947522422356b1b9a5ff04c7ca228df5e15b). Post-fix CI passed: run [44980449997](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44980449997) passed 46 tests and the synthetic smoke test; run [44980801176](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44980801176) passed 48 tests and the synthetic smoke test.
- Queue-run observability was implemented in [d746d0a](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d746d0abc596a8a2908c6efed0e75676099e37c1) and tested in [d61f09c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/d61f09c6c960778b44825bc462d9073a2025c3ee). The first dry-run exposed a missing PR-comment permission; after adding pull-requests:write, dry-run comment 7073685954 triggered queue-guardian run [44981622191](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44981622191). Its artifact 14738435165 confirms complete enumeration of 78 repository runs, no queue actions/errors, and status_comment.state=created with bot comment 7073687762. The bot-owned status comment is now visible on PR #2.
- Added bounded audit-only command /qfr-probe-eth-btc-funding-2024-01 in commit [0630670](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/06306704f21a8d86e2878b7de27fa3426089defa); research-tests now watches that workflow file in [8bdf5f0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8bdf5f03df98d1fb790aa6c3556984df93947d40). CI passed in runs [44981394352](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44981394352) and [44981400044](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44981400044). The bounded command was posted as PR comment 7073695430, but its exact run ID was not visible in the last status snapshot; no duplicate command has been sent.

**Current decision:** original Binance ETH/BTC research remains **INCONCLUSIVE**. No backtest or strategy performance metrics are authorized until the six inputs, gap classifications and funding semantics pass their declared gates.


## Audit artifact resolution — 2026-11-22 03:40 UTC

The prior full-audit command was resolved without launching a duplicate. PR comment 7072165218 maps to run 44971182002 (event issue_comment, actor takenthatusernameis-collab, main commit 8fa50dd), which completed with conclusion failure because the audit correctly exited 2 on incomplete inputs. The authorization gate, checkout, dependencies and synthetic plumbing test succeeded; empirical preflight and backtest were skipped. Artifact 14733503636 (48,040 bytes; ZIP SHA-256 fa27161253ba556e96e4d5444cfdded4e9eacebadefec9ce05acc53763281b4f) contains nine files: summary, six input manifests and two Spot gap-reconciliation manifests. All six manifests were present; summary status is INCOMPLETE.

All 82 monthly archives for each of the four price series were downloaded with verified checksums and zero parse errors. USD-M ETH/BTC are complete at 59,904 hourly rows each, with no missing or duplicate timestamps. Spot ETH/BTC each contain 59,873 of 59,904 expected hourly bars, with 31 missing timestamps and 31 unresolved aggregate-trade positive-control failures. The gap endpoint returned HTTP 200 with no trades for the selected probes, but the known-active control did not pass; therefore no missing hour is classified as no-trade. The funding manifests in this run still reflect the old REST endpoint and HTTP 451, because the monthly archive replacement was committed after this run.

The test-fixture correction is CI-verified: 46 tests passed in run 44980449997 and 48 tests passed in run 44980801176, both with the synthetic smoke test. The subsequent queue-guardian permission and bounded-probe workflow changes also passed CI in runs 44981394352 and 44981400044. The first queue-guardian status-comment attempt returned 403 Resource not accessible by integration; after adding pull-requests:write, dry-run run 44981622191 created the bot-owned status comment successfully. The status-comment observability path is now end-to-end verified.

The public Binance issue #517 remains open, last updated 2026-11-19, with no Binance-team clarification visible in the four-comment thread. Funding event population and historical semantics remain provisional. Do not run the empirical backtest.


## Bounded funding probe dispatch — 2026-11-22 03:42 UTC

The exact allowlisted command /qfr-probe-eth-btc-funding-2024-01 was posted to control PR #2 as comment 7073695430 after CI passed. It resolved to run [44981678667](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44981678667), event issue_comment, actor takenthatusernameis-collab, default-branch SHA 168b79c3, with the fixed 2024-01-01 through 2024-01-31 range, market=both and reconcile=false. It audited all six inputs and could not launch empirical strategy computation. Artifact [14737094815](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44981678667/artifacts/14737094815) is a 6,599-byte ZIP with SHA-256 6d10bdd91fa0aef28988d399f647b524e4e0770097e8f197bcecde85899d2da5; it contains seven files: the summary and all six input manifests, with no raw CSVs. All four price series are complete at 744/744 hourly bars, each with a checksum-verified monthly archive, zero parse errors, zero gaps and zero duplicates. Both funding archives downloaded and passed .CHECKSUM verification; each header was detected and the schema was calc_time/funding_interval_hours/last_funding_rate. ETHUSDT and BTCUSDT each have 93 rows, zero duplicate timestamps, observed interval_hours=[8.0], start 2024-01-01 00:00 UTC, end 2024-01-31 16:00 UTC, median event gap 8 hours and maximum gap 8.0000008 hours. The manifests explicitly set event_semantics=UNVERIFIED and completeness_status=PROVISIONAL_NOT_ACCEPTED because issue #517 leaves settlement-population semantics unresolved. The workflow correctly exited 2 after preserving the data and manifests; summary status is INCOMPLETE, price_series_complete=true, funding_series_complete=false, all_six_manifests_present=true. No strategy computation ran.

## Wake-up plan — 2026-11-22

**Adaptive antifragile plan, ordered by expected information gain:**

1. Preserve the scientific gate: no empirical backtest until the six inputs, Spot gap classifications, and actual funding-settlement population are independently accepted.
2. Test a materially different funding-data path before scaling the Binance archive: Tardis.dev's free first-day-of-month derivative_ticker sample for ETHUSDT and BTCUSDT. It is sourced from Binance's real-time WebSocket ticker stream and exposes the next funding timestamp and rate estimate. Use it to test event-time observability and cross-check Binance archive timestamps; do not treat its pre-event rate estimate as the final settled rate.
3. Reject misleading alternatives explicitly: Tardis's separate generated fundingRate channel begins only 2026-10-16 and is an hourly REST snapshot of the latest 1,000 settlements, with documented interruption-related omissions; CoinGlass funding OHLC close is predicted, not the final settled rate, and does not supply the historical settlement interval. Neither can certify the 2020–2026 payable-settlement population.
4. In parallel, retain the current Binance monthly archive and its checksum/schema manifests; compare only on overlapping events, and keep all source identities and conclusions separate.
5. Meta-process: record queue-guardian trigger, run ID, SHA and dry-run/live mode in every artifact/status comment; verify CI and the harmless end-to-end dry-run. Separately verify that a real schedule event occurs before claiming live enforcement.
6. Hygiene preflight: preserve the five divergent branches and open control PR #2; delete nothing without proof of merge/abandonment. The complete tree has 37 tracked paths, no tracked scratch/cache/raw-data clutter, no open queue-guardian incidents, and no active Actions runs at inspection. Remote inspection cannot establish local untracked files.

**Acceptance for the next probe:** both Tardis sample files must download with HTTP 200, pass gzip/CSV/schema validation, contain meaningful non-empty funding timestamps/rates for both symbols, and yield inspectable pre-event observations with timestamp age/gap diagnostics. This validates only the sample and event-schedule observability—not the final settlement rate, complete history, or the Binance archive's entire settlement population.

## Independent funding-source screening — 2026-11-22

**Binance API semantics:** the official USDⓈ-M funding-history endpoint documents fundingTime, fundingRate, markPrice associated with a funding-fee charge, and rateType (Regular/Special); it has a maximum page size of 1,000 and requires pagination when the requested interval exceeds that limit. The fundingInfo endpoint returns adjusted cap/floor and fundingIntervalHours for symbols with adjustments, but the documented response is a current snapshot rather than a historical effective-dated schedule. Binance's funding FAQ documents dynamic interval changes, including automatic adjustments after cap/floor settlements and the 2026-01-02 rule reverting eligible 1-hour contracts to 4-hour settlement after 16 consecutive cycles at or below 0.025% absolute funding. A fixed 8-hour schedule must not be assumed.

**Third-party provider results:**

- [PowakaData free sample](https://github.com/powakadata/powakadata-crypto-funding-sample) was inspected directly. Its BTCUSDT and ETHUSDT files each contain 577 rows, split into two contiguous 8-hour blocks: 200 early rows and 377 rows from 2026-02-17 16:00 UTC through 2026-06-23 00:00 UTC. BTC has a 54,864-hour gap from 2019-11-15 16:00 to 2026-02-17 16:00; ETH has a 52,992-hour gap from 2020-02-01 16:00 to 2026-02-17 16:00. Neither file contains January 2024 observations, and the sample stops before the requested 2026-10-31 end date. The repository supplies no per-file source manifest/checksum or detailed collection methodology. It is useful only as a partial cross-check, not a complete history.
- [Tardis Binance USDS-M Futures coverage](https://docs.tardis.dev/historical-data-details/binance-futures) documents the real-time WebSocket markPrice channel from 2020-02-13 and a no-key downloadable sample on the first day of each month. Its normalized derivative_ticker fields identify the *next* funding event and a rate estimate; the documentation explicitly warns that the last pre-event estimate can differ from the rate ultimately settled. This is useful for event-time/as-of schedule observability, not as a final settlement-rate ledger. The separate generated fundingRate channel begins only 2026-10-16, polls the REST history endpoint hourly, retains the latest 1,000 settlements, and can miss settlements that leave that window during a recording interruption. It is not suitable for complete 2020–2026 history.
- [CoinGlass funding-rate OHLC](https://docs.coinglass.com/reference/fr-ohlc-histroy) is not an acceptable settlement ledger: its close is a predicted rate, its interval is only the candle aggregation interval, and it does not provide the historical settlement interval applied to each record.

**Decision:** none of the screened third-party sources currently proves a complete, final-settlement funding population for both ETHUSDT and BTCUSDT over 2020-01-01 through 2026-10-31. Preserve the Binance archive as PROVISIONAL_NOT_ACCEPTED. Continue with the bounded Tardis first-of-month sample probe to test whether its WebSocket-derived next-event timestamps and pre-event estimates can independently reconcile a representative event schedule; do not promote those estimates to settled funding rates.

## Tardis vs Binance January 2024 event cross-check — 2026-11-22

**Run:** [44983540393](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44983540393), triggered by control-PR comment 7073975746 at commit ef470621. The run completed successfully. Artifact [14739051517](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44983540393/artifacts/14739051517) is 4,734 bytes; ZIP SHA-256: ba20e4b17a11aa1b2b7f045f25106a854b5b66096c31677a2a28852c8b9c0624. It contains only three JSON files (summary and two symbol manifests); raw Tardis CSVs and Binance ZIPs remain in the ephemeral runner cache and are not uploaded.

- Tardis returned HTTP 200 for both 2024-01-01 files. BTCUSDT: 107,023 rows, 107,023 unique local timestamps, zero out-of-order timestamps, maximum local gap 6.768949 seconds. ETHUSDT: 106,646 rows, 106,645 unique local timestamps, zero out-of-order timestamps, maximum local gap 5.938971 seconds. Neither symbol had a local-timestamp gap over 60 seconds. The final pre-event observations were 0.39–0.98 seconds before their corresponding event timestamps.
- Both Binance Vision January 2024 monthly funding archives returned HTTP 200 and passed the official .CHECKSUM SHA-256 sidecar. Each contained 93 rows, zero duplicate timestamps, and observed interval_hours=[8.0].
- For each symbol, all four Tardis next-event timestamps visible in the day (2024-01-01 00:00, 08:00, 16:00 and 2024-01-02 00:00 UTC) exactly matched Binance archive calc_time timestamps: 4/4 (100%) on this one-day sample.
- Three pre-event rate comparisons per symbol were possible. Only the 08:00 estimate matched exactly; the two later estimates differed from the archive's last_funding_rate. Mean absolute differences: BTC 5.2667e-7, ETH 4.6000e-7; maximum: BTC 1.03e-6, ETH 9.5e-7. This empirically confirms that the last Tardis pre-event rate estimate must not be substituted for the final archive rate.

**Decision:** the sample strongly supports interpreting Binance archive calc_time as the event timestamp for the observed January 2024 ETH/BTC events. It does not establish that the archive contains every payable event across the full 2020–2026 history, and it does not validate final-rate semantics beyond the sample. Keep event_semantics=PARTIALLY_SUPPORTED_SAMPLE_ONLY and completeness_status=PROVISIONAL_NOT_ACCEPTED. No strategy backtest ran.

**Next validation:** repeat the same checksum-verified cross-check on 2020-06-01 (early post-Tardis collection-stabilization sample) and 2026-03-01 (after Binance's 2026-01-02 interval-reversion policy), then compare event-time coverage and interval changes. Tardis documents known data gaps/latency issues before 2020-05-14, so do not use pre-2020-05-14 samples as positive completeness evidence. Full 2020-01–2026-10 coverage remains unproven.
