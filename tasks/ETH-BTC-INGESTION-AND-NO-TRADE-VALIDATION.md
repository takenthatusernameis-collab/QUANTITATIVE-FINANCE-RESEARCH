# Active Task: Repair ETH/BTC Data Ingestion and Validate No-Trade Intervals

**Status:** In progress — Spot-only empirical validation running  
**Updated:** 2026-11-22 07:43 UTC
**Priority:** High  
**Type:** Data-source resilience, parser correctness, missing-observation policy, and reproducible audit  
**Scope:** Historical research/backtesting only. No live orders, capital deployment, live credentials, or strategy promotion.

## Objective

Remove the verified ingestion bottlenecks without weakening the ETH/BTC research specification or inventing observations. Produce a provenance-complete audit of all six required inputs and a defensible, tested treatment for the 31 synchronized Spot gaps before the original combined/perpetual empirical backtest is allowed. The independently gated Spot-only scope may proceed only after its own Spot provenance, no-trade, event-time, cost and methodology checks pass; it must not be presented as perpetual evidence.

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

## Implementation progress — 2026-11-22 (updated 07:41 UTC)

- **Spot gap evidence:** the full-history audit classified all 31 synchronized missing hours for each of ETHUSDT and BTCUSDT as confirmed no-trade intervals using checksum-verified daily aggregate-trade archives and same-day known-active positive controls. The original hourly rows remain absent; no OHLCV candles or zero returns were synthesized.
- **Production event-time integration:** `research/run_eth_btc.py` now routes irregular Spot hourly/daily observations through the production walk-forward, event-time benchmark and continuous-time metrics path in `research/event_time.py`. It uses calendar-time rolling features, next-observed-open execution, actual elapsed holding/borrow durations, funding-event alignment, fold-end liquidation and elapsed-time annualization. Equal-spacing unit-root diagnostics are explicitly skipped for irregular observations.
- **Manifest acceptance:** the Spot gate binds each source CSV to the exact expected monthly kline archive URL/checksum and daily aggTrade archive URL/checksum; it requires synchronized confirmed-no-trade gaps, positive controls, zero duplicate/out-of-order aggregate-trade IDs and complete provenance. Commit [66b3594](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/66b3594d5979129117c2fc5ed8062f5a9839ccd3) tightened exact archive-object matching.
- **Independent market status:** both USD-M price histories pass at 59,904/59,904 bars. Both funding histories have 7,488 rows and coverage/cadence checks but remain `PROVISIONAL_NOT_ACCEPTED` because final-settlement population, event semantics and contract-incarnation coverage are unresolved. Spot-only research is independent of funding; combined/perpetual claims remain gated.
- **Current Spot-only run:** agent-triggered run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) started 2026-11-22 07:29:10 UTC on default-branch SHA `66b3594`. Authorization, default-branch checkout, dependencies and synthetic smoke passed. The Spot-only data preflight is still **IN_PROGRESS**; the empirical strategy step is pending and no strategy metrics have been produced.
- **P1 orchestration improvement:** unrelated/unauthorized PR comments now receive unique per-comment concurrency groups, while allowlisted commands from the verified actor on control PR #2 remain serialized. The workflow allowlist and concurrency allowlist are regression-tested for exact set equality. CI [44999194755](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999194755) passed 98 deterministic tests and the synthetic smoke test. End-to-end isolation test [44999259543](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259543) rejected the queue-guardian command and skipped research without waiting behind the active run.
- **Queue state:** guardian [run 44999259660](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660) enumerated 152 runs completely, recorded zero queue actions/errors, and preserved pending run [44998792132](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998792132) because the earlier same-group run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) remains in progress.
- **Hygiene:** the recursive tree contained 43 paths; no tracked raw market data, scratch files, disposable caches or generated clutter were present. No deletion was warranted; all five branches and the open draft control PR #2 were preserved.

## Required work

### 1. Spot no-trade evidence — accepted; production validation running

- Full-history audit #23 verified all 31 missing hourly intervals for both ETHUSDT and BTCUSDT as `confirmed_no_trade_interval` using checksum-verified daily aggregate-trade archives and same-day known-active positive controls. Both symbol manifests have synchronized gap inventories; no hourly candle was inserted.
- The production gate requires exact expected monthly-kline and daily-aggTrade archive URLs, verified checksums, positive controls, zero duplicate/out-of-order aggregate-trade IDs, synchronized classifications and source-manifest consistency.
- Spot-only run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) is validating the live manifests. If it rejects the data, preserve the exact blocker and move to the independent MEXC pilot rather than repeating identical Binance requests.

### 2. Event-time missing-observation policy — integrated; empirical validation pending

**Implementation status:** production Spot hourly and daily walk-forward folds now use `walk_forward_event_time`, with observed-time rolling features, next-observed-open execution, actual elapsed holding and borrow costs, event-time benchmarks, funding-event alignment, fold-end liquidation and continuous-time elapsed metrics. The policy preserves irregular timestamps; no synthetic OHLCV, forward-filled prices, zero returns or fictitious execution opportunities are introduced. Equal-spacing unit-root/cointegration lag diagnostics are skipped and explicitly labelled for irregular samples.

The manifest-backed acceptance gate is integrated and now checks exact official archive URLs/checksums, synchronized no-trade evidence, same-day positive controls and aggregate-trade integrity. Spot-only empirical run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) is currently in its live data preflight; the strategy step has not started and no performance metrics exist.

**Interpretation constraint:** `--spot-borrow-bps-per-day` defaults to `0.0`. Any Spot results produced under that default are before short-borrow charges and must not be described as fully net or deployable. Actual borrow availability/rates and account-specific fees remain external assumptions.

### 3. USDⓈ-M kline archive parsing — resolved in full-history audit

Full-history audit #23 parsed both USD-M ETHUSDT and BTCUSDT archives across all 82 monthly files, with checksum verification, 59,904/59,904 hourly observations per symbol, zero missing timestamps and zero duplicates. The former January 2022 `Invalid open_time values` parser failure is resolved. Preserve the recognized-schema, timestamp-unit, bounds and checksum regression tests; reopen only if a new archive/schema revision fails.

### 4. Funding route replacement — implemented; settlement semantics remain provisional

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
- Run the audit and, when the selected study's machine-checkable gates pass, launch the Spot-only study through control PR #2 command `/qfr-run-eth-btc-spot-empirical`. Reserve `/qfr-run-eth-btc-empirical` for the original combined study after all six inputs and funding semantics pass. No human confirmation is required for historical research. The backtest must still stop automatically on invalid data. If the ETH/BTC source path remains infeasible, run a separately preregistered alternative dataset/model rather than waiting indefinitely.
- Inspect and hash the new artifacts. Update README, reports, this task, and the next handoff.
- Keep raw market data out of Git. No live trading or capital deployment.

## Acceptance criteria

These criteria govern the original combined/perpetual Binance experiment. A Spot-only run uses the separate market-scope gate and cannot be used to infer perpetual profitability.

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

## Funding event-time cross-check — 2026-11-22 (three representative dates)

Three checksum-backed Binance Vision monthly funding archives were independently cross-checked against Tardis Binance-futures `derivative_ticker` first-of-month samples. Tardis exposes the next funding-event timestamp and a *pre-event estimate*, not the final settled rate.

| Tardis sample date | Binance archive rows per symbol | Event timestamps matched within 15 s (BTC / ETH) | Maximum timestamp offset | Decision |
|---|---:|---:|---:|---|
| 2020-06-01 | 90 | 3/3 / 3/3 | 1 ms | Sample cross-check passes |
| 2024-01-01 | 93 | 4/4 / 4/4 | 0.005 s | Sample cross-check passes |
| 2026-03-01 | 93 | 4/4 / 4/4 | 0.005 s | Sample cross-check passes |

- **2020-06-01:** Tardis downloaded successfully for both symbols (BTC 184,454 rows; ETH 160,635), with no local timestamp gaps over 60 seconds. Binance monthly archives passed their published checksums, had zero duplicate timestamps, and reported 8-hour intervals. Each symbol matched all three visible next-event timestamps within 15 seconds. Artifact [14739152083](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44983958409/artifacts/14739152083), ZIP SHA-256 `9f35f9f4b0878374c64eef8910f0f8a74e11b9675453da922bc8848898a31c3a`.
- **2024-01-01:** each Binance archive contained 93 checksum-verified rows and all four visible Tardis next-event timestamps matched. Only one of three pre-event rate estimates per symbol matched the archive rate exactly; this supports keeping the estimate distinct from the settled/archive rate. Artifact [14739051517](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44983540393/artifacts/14739051517), ZIP SHA-256 `ba20e4b17a11aa1b2b7f045f25106a854b5b66096c31677a2a28852c8b9c0624`.
- **2026-03-01:** each Binance archive contained 93 checksum-verified rows; all four visible Tardis next-event timestamps matched within 15 seconds. Only one of three pre-event rate estimates per symbol matched exactly. Artifact [14739431671](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44984500046/artifacts/14739431671), ZIP SHA-256 `3263ca8179db34126b0e4ca3996ab0d19273b07ac4fc01f5f4dcb22f64ed88e9`.

**Interpretation:** these independent samples support the interpretation of Binance archive `calc_time` as the event timestamp for the sampled ETH/BTC settlements. They do **not** establish complete payable-settlement coverage across 2020-01-01–2026-10-31, historical contract-incarnation coverage, or a complete effective funding schedule. Tardis explicitly reports that its final pre-event estimate can differ from the rate ultimately settled. The public Binance issue [#517](https://github.com/binance/binance-public-data/issues/517) remains open. Keep both funding inputs `PROVISIONAL_NOT_ACCEPTED`; do not replace final rates with Tardis estimates or infer zero funding. No empirical backtest is justified by these sample cross-checks.

## Independent USD-quoted price-source screening — 2026-11-22

A promising independent path has been identified, but no production data has been ingested or accepted yet:

- **Coinbase Exchange public candles:** official documentation for `GET /products/{product_id}/candles` supports 1-hour bars (`granularity=3600`), returns OHLCV in the order `[time, low, high, open, close, volume]`, caps a request at 300 candles, and explicitly says intervals with no ticks are not published. The current Coinbase Exchange market page lists both `BTC-USD` and `ETH-USD` as Full Trading. A 2020-01 through 2026-10 hourly history would require approximately 200 bounded requests per symbol, with overlap/deduplication and exact expected-grid checks. This is a strong candidate for a separately identified synchronized USD cross-rate `ETH-USD / BTC-USD`, and its no-tick omission semantics may help distinguish genuine no-trade hours from missing data. **Not yet verified:** historical product inception dates, full interval coverage, endpoint accessibility from the hosted runner, archive stability, and exact trade/no-trade behavior for the requested sample dates.
  - Docs: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
  - Current markets: https://exchange.coinbase.com/markets
- **Kraken downloadable OHLCVT:** Kraken's official full-history dataset provides 60-minute OHLCVT from each market's first trade through 2026-09-30; it omits intervals with no trades and explicitly says missing candles indicate no trades. It includes a build manifest and quarterly incremental archives, but the full archive is split into approximately 2 GB parts, making selective acquisition and storage more expensive. Pair availability, checksums/manifest semantics and an efficient two-pair extraction route still require verification.
  - Docs: https://support.kraken.com/en-us/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data

**Next bounded experiment:** start with the MEXC pilot, then Bitget as the second independent-provider candidate. For each, probe synchronized ETH/USDT and BTC/USDT (plus suitable USD-quoted pairs where available) over known-active and negative/missing-data windows; verify HTTP status, product identity, pair inception, row ordering, UTC bucket boundaries, OHLCV invariants, pagination limits, duplicate handling, common timestamp coverage, checksums and full-history feasibility. Validate quote-currency semantics and never assume USDT/USD equals one. Only after both pass their bounded controls should a representative month/full-history plan be approved. Keep each venue a separate experiment; Coinbase and Kraken remain subsequent independent candidates. Do not blend venue datasets or infer perpetual funding from spot prices.

## Current execution follow-up — 2026-11-22 05:16 UTC

### Full-history audit #23 resolved

Run [44986170330](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986170330) completed at 05:16:08 UTC with expected data-quality conclusion **INCOMPLETE** (exit code 2). Authorization, default-branch checkout, Python/dependency setup, synthetic smoke test and artifact upload passed. Both empirical preflight and strategy backtest were skipped.

Artifact [14740847028](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986170330/artifacts/14740847028) contains nine files (summary, six input manifests, two Spot gap-reconciliation manifests), 71,320 bytes, SHA-256 `a69e7247f2aaf09f049461a80b823084d8fe3384036494548f000815dada7204`. Raw market-data CSVs were not uploaded.

| Input | Observations | Data result |
|---|---:|---|
| Spot ETHUSDT | 59,873 / 59,904 hourly | 31 absent hourly candles |
| Spot BTCUSDT | 59,873 / 59,904 hourly | Same 31 absent hours |
| USD-M ETHUSDT | 59,904 / 59,904 | Complete |
| USD-M BTCUSDT | 59,904 / 59,904 | Complete |
| ETHUSDT funding | 7,488 events | Timestamp/cadence coverage passes; semantics provisional |
| BTCUSDT funding | 7,488 events | Timestamp/cadence coverage passes; semantics provisional |

**Spot gap resolution:** both reconciliation manifests classify all 31/31 missing hours as `confirmed_no_trade_interval`. Classification is backed by checksum-verified daily aggregate-trade archives and successful known-active archive positive controls. There are zero unresolved gap classifications in either reconciliation manifest. This is not a repair of the original hourly candle CSVs: preserve the absent rows and build an explicit event-time/irregular-time treatment that retains elapsed duration. Never generate synthetic OHLCV, assign zero return, or count a multi-hour gap as one hourly observation.

**Perpetual price resolution:** both USD-M parsers now pass the January 2022 archive and all 82 monthly archive checksums; each series contains 59,904/59,904 hourly bars, zero duplicates and zero missing timestamps. The formerly recurring futures parser blocker is resolved for this full-history run.

**Funding remains the hard research blocker:** Binance Vision monthly archives provide 7,488 rows per symbol, zero duplicate timestamps, requested start/end coverage and approximately eight-hour cadence. Both funding manifests nevertheless remain `PROVISIONAL_NOT_ACCEPTED` because the complete final-settlement population, historical event semantics and contract-incarnation/retention have not been independently established. Three Tardis samples corroborate next-event timestamps only; Tardis pre-event funding-rate estimates are not final settled rates.

The audit summary confirms all six manifests are present, `price_series_complete=false`, `funding_series_complete=false`, `reconciliation_complete=true`, and status `INCOMPLETE`. No strategy computation or performance metric was produced. Original Binance ETH/BTC perpetual research remains **INCONCLUSIVE**.

### Adaptive hierarchy implementation

The canonical seven-priority hierarchy now lives in [the General Antifragile Autonomous Operating Mindset](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md). The [Adaptive Autonomous Research Execution Standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) defines provider, architecture, time-frequency, hypothesis and funding failover. Machine-checkable policy is implemented in `research/adaptive_decision.py`; tests are in `research/test_adaptive_decision.py`; the original six-input audit now calls the shared fail-closed gate in `research/run_eth_btc.py`.

Implementation commits:
- Mindset: [378609c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/378609c7d3bf76ce7ce6bb9ec9997b6538e7054f)
- Execution standard: [0d4378f](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/0d4378f189c043caf885257b7a53de5d29264767)
- README: [386ff38](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/386ff38f430cf47c43eab1f2557d1a87c0ca29f6)
- Policy engine: [a811c49](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a811c49223565dc5d3d24c60b408690d0ee0988b)
- Policy tests: [5576fc0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/5576fc048fffaf0c4080788750f52b4f55f1fc2c)
- Six-input gate integration: [8625d40](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8625d40b8684ee975d7664ca8b01a17247dd659e)
- Scoped gate implementation: [37fe290](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/37fe290682c5047743d584aa7df7808e90fe84cd)
- Scoped pipeline integration: [6ab1adb](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/6ab1adba7d61c9de608bc8bbc7a541beac227bd4)
- Scoped workflow commands: [f728398](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/f72839867ed1aacf0d5a0f33e7859d9c6abb48b0)
- Spot reconciliation/time-policy fix: [b13ab5c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/b13ab5c66e8f64c8e674145c1c27b4a1811f159b)
- Full-history provider feasibility gate: [0e2bfa0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/0e2bfa07aa6903107dc0794e0401fb108bae0021)
- Priority and provider-order regression tests: [1d700ce](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1d700ceec9d56acb697493815eab507aecbf092d)
- Full-history acquisition-feasibility gate test: [ff4ac3c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ff4ac3c06ed94cf29766679798e4afedf6e5869a)
- Canonical P6 hierarchy-test label correction: [a82192b](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a82192be07c64b10b0966dabc5741f62635a1075)

### Independent Spot/perpetual acceptance and dispatch scopes

The machine-checkable research gate now has three explicit scopes:
- **Spot:** only `spot_ETHUSDT` and `spot_BTCUSDT` plus their provenance manifests are required. Perpetual funding is not a dependency. If the hourly series has missing bars, Spot acceptance additionally requires complete independent no-trade reconciliation and a separately accepted event-time/elapsed-time PnL, signal, execution and annualization policy. The event-time accounting is now integrated into the production Spot walk-forward and benchmark pipeline in `research/run_eth_btc.py`, using `research/event_time.py`; deterministic tests cover irregular intervals, next-observation execution, actual holding durations, elapsed-time borrow, funding-event mapping and calendar-time annualization. The live manifest-backed Spot gate is being evaluated by run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437); do not treat integration or CI success as empirical acceptance until that run's preflight and artifacts are inspected.
- **Perpetual / USD-M:** requires `um_ETHUSDT`, `um_BTCUSDT`, `funding_ETHUSDT`, and `funding_BTCUSDT`, with their manifests. Spot gaps do not block this independent scope. Both funding series remain provisional, so the gate is currently closed.
- **Both:** requires all six inputs and both market-specific conditions.

The workflow now allowlists `/qfr-run-eth-btc-spot-empirical`, `/qfr-run-eth-btc-um-empirical`, and existing combined `/qfr-run-eth-btc-empirical`. Preflight receives the same market scope as the empirical run. The audit still gathers all six manifests to preserve independent information. A Spot-only outcome must never be represented as evidence of perpetual-strategy profitability.

### Next executable research actions

1. **Spot-only event-time empirical validation:** inspect active run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) after completion, including its preflight output, full logs, six-input summary, Spot manifests, gap manifests and artifact hashes. If the Spot gate passes, review hourly/daily OOS results, fold counts, trades, turnover, drawdowns, confidence/robustness outputs and the zero-borrow assumption. If it fails, preserve the exact gate blocker and start the bounded MEXC pilot; do not repeat the same Binance probe.
2. **MEXC first independent-provider pilot:** bounded synchronized ETH/USDT and BTC/USDT hourly positive/negative controls; verify pair identity/inception, UTC timestamps, OHLCV, duplicates, pagination, checksums, common timestamps, quote semantics and full-history feasibility. Keep a separate MEXC experiment; do not assume USDT equals USD.
3. **Bitget second independent-provider pilot:** apply the same independent acceptance protocol and separate provenance/experiment identity to ETH/USDT and BTC/USDT (and suitable USD pairs if available).
4. **Further open-ended provider discovery:** pilot Coinbase Exchange synchronized ETH-USD/BTC-USD and Kraken ETH/USD/BTC/USD OHLCVT, then continue screening lawful, independently verifiable exchanges and historical-data vendors. Candidates include, but are not limited to, OKX, Bybit, Gate.io, KuCoin and specialist archives. Verify current product availability and permitted access.
5. **Trade-level and architecture alternatives:** investigate raw trades and other materially different constructions. After two distinct provider failures, change data architecture instead of endlessly repeating provider-specific variants.
6. **Funding acceptance:** continue a separate final-settlement population investigation. Do not use pre-event Tardis rate estimates as final rates or allow the spot-only workstream to imply perpetual profitability.
7. Run the original Binance perpetual empirical workflow only after all six input, Spot semantics, funding settlement, synchronization and methodology gates pass. A distinct spot-only or alternative-provider study must have its own experiment identity and preregistration.

The current canonical queue is [tasks/ACTIVE-QUEUE.md](ACTIVE-QUEUE.md). Final GitHub Actions run [44989792456](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989792456) passed 82 deterministic tests and the synthetic plumbing smoke test on the final policy/test revision [a82192b](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a82192be07c64b10b0966dabc5741f62635a1075). The suite covers hierarchy order, provider scoring/acceptance/full-history feasibility, stop/escalation rules, independent workstreams, experiment identity, Spot/perpetual separation and scope gates, hypothesis replacement, duplicate-active-dispatch checks, and fail-closed six-input acceptance. Runs #81–#86, #89 and #91 were intermediate code/test revisions whose defects were fixed in subsequent commits; run #92 is the final passing verification. Deterministic and synthetic checks validate engineering behavior only—not production provider quality or strategy profitability.


## Current execution follow-up — 2026-11-22 07:41 UTC

- The scheduled queue guardian [44999220911](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999220911) completed successfully with `event=schedule` on SHA `9c4b723`; artifact [14744453706](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999220911/artifacts/14744453706), SHA-256 `051e864f6b15fe13b0c392048fec0a962682fdf26f88957830404a6218c6f840`, confirms 150/150 repository runs enumerated, 130 research/test runs (latest 50 retained), no actions/errors, and an updated status comment. This verifies the scheduled activation path; no eligible cancellation was present, so cancellation execution itself remains untested. The later live guardian [44999259660](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660) enumerated 152/152 runs completely with no actions/errors; artifact [14744749673](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660/artifacts/14744749673) SHA-256 `649717e30b9a31c5c054d15b541eb338813d7a95fa082da801c5dbcedec83488`.
- Workflow queue isolation was implemented in [8f82759](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8f82759981dd0f655334ffbdc55043830a52d824) and regression-tested in [9c4b723](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/9c4b72302a1f4583c2d00396724fae4e439861ef). Final CI [44999194755](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999194755) passed 98 tests and the synthetic smoke test. The earlier test run [44999175158](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999175158) failed only because the new test's regex was over-escaped; the correction is covered by the passing run.
- Isolation was exercised end-to-end by [44999259543](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259543): the `/qfr-queue-guardian-live` comment was rejected by the research authorization gate, all research jobs were skipped, and the run completed while #44998434437 remained active.
- The Spot-only empirical attempt [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) remains **IN_PROGRESS** in the preflight step. Its strategy step has not started. Run [44998792132](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998792132) remains pending behind it as the verified same-group predecessor exception; do not cancel it or create another attempt.
- Research conclusion remains **INCONCLUSIVE pending live Spot acceptance and OOS output**. USD-M funding remains provisional. No live trading, capital deployment or strategy promotion occurred.
