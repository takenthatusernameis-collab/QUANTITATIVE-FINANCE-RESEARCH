# Pending Task: Review ETH/BTC Input Audit and Finalize the Missing-Bar Data Policy

**Status:** Pending  
**Priority:** High  
**Type:** Research artifact verification, data provenance and pre-registration  
**Scope:** Historical research/backtesting only. No live orders, capital deployment, live credentials or strategy promotion.

## Context

The prior agent implemented a lossless missing-hour inventory, a non-fail-fast audit of all four price series and both funding histories, and per-hour official-source reconciliation for missing ETHUSDT Spot bars. Deterministic tests and the synthetic smoke test passed.

Autonomous dispatch was verified using the exact-actor, exact-command control PR route. The audit-only run was initiated without launching strategy backtests:

- Control PR: [#2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2)
- Audit run: [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383)
- Event: `issue_comment`
- Actor: `takenthatusernameis-collab`
- Ref: `main`
- Code/workflow SHA: `96b93aeba313d9a083bb031a949955cb8e606509`
- Exact command: `/qfr-run-eth-btc-data-audit`
- Requested range: `2020-01-01` through `2026-10-31`

At task creation, the audit job had passed authorization, checkout of the default branch, dependency installation and the synthetic test. The real data-audit step was still in progress. **Do not launch another full audit or empirical study until this run's final state and artifacts have been inspected.**

The empirical ETH/BTC study remains **INCONCLUSIVE**. This audit run is explicitly audit-only and cannot produce strategy-performance evidence.

## Objectives

1. **Inspect the existing run before doing anything else.**
   - Fetch run `44963655383` by exact ID.
   - Verify event, actor, ref, SHA, workflow path, inputs/gate outputs, job count, status, conclusion and timestamps.
   - If it is still in progress, do not duplicate it; inspect only machine-checkable status and resume this task when it is complete.
   - If it failed or was cancelled, inspect the exact failing step and logs before deciding whether a bounded retry, code fix or alternate source is warranted. Do not repeat an unchanged failure.

2. **Retrieve and inventory all audit artifacts.**
   - Enumerate the run's artifacts and record total/returned counts, IDs, names, sizes, expiry and ZIP SHA-256.
   - Inspect `reports/generated/data_audit_summary.json`, all four `*_archive_manifest.json` files, both `*_funding_manifest.json` files, and `data/raw/spot_ETHUSDT_gap_reconciliation.json` when present.
   - Retain the raw artifact privately as evidence; keep raw OHLCV CSVs out of Git.
   - Verify that the artifact does not contain raw market data and that manifests are complete and readable.

3. **Reconcile every originally missing ETH Spot hour.**
   - Confirm the full inventory count is 31 and compare its timestamps/intervals with the previous manifest's first 20 samples.
   - For every timestamp, inspect the exact Binance Spot REST request, response status, returned candle open time, timestamp units, OHLCV values/hash, daily-archive URL, archive hash and checksum status.
   - Independently verify classifications and counts:
     - monthly archive omission corroborated by both official sources with matching values;
     - candle present in only one official representation;
     - official-source value mismatch;
     - absent from both official representations/unresolved;
     - request or source-access failure.
   - Treat an HTTP error, missing checksum, incomplete page, or unresolved discrepancy as evidence limitations, not as proof of no-trade or zero return.
   - Do not infer that a missing hourly candle represents zero price movement or zero volume.

4. **Audit every required input series independently.**
   - Spot ETHUSDT, Spot BTCUSDT, USDⓈ-M ETHUSDT and USDⓈ-M BTCUSDT.
   - ETH and BTC USDⓈ-M funding histories.
   - For each, verify requested bounds, observed bounds, expected/observed rows, all missing intervals, duplicate timestamps, archive months, timestamp normalization, checksum verification, source provenance and manifest hash.
   - For the hourly price series, the declared sample has 59,904 expected bars. Do not rely only on the synchronized pair or the first failure.
   - For funding, validate coverage boundaries, page chronology, duplicate events, cadence/gaps and alignment. Never silently convert missing events to zero funding.

5. **Decide the data policy without contaminating the research.**
   - If monthly archives omit candles but both the official API and daily archive independently provide matching authenticated values, evaluate an explicit, reproducible source-reconciliation repair that adds only those verified observed candles to the normalized data. Preserve source URL, request parameters, response metadata, checksums/hashes and the original raw archive manifest.
   - Any repaired dataset must have a new content hash and an audit trail. Do not overwrite or obscure the original evidence.
   - Add deterministic tests for source matching, conflicts, duplicate prevention, provenance retention and unresolved gaps before treating repaired data as complete.
   - If an interval is absent from official sources or sources conflict, do not fabricate, forward-fill, or drop it to pass the gate. Keep the relevant series incomplete unless a defensible, pre-registered policy explicitly covers it.
   - A reconciliation manifest showing that an alternative source contains a candle is not, by itself, proof that the consolidated backtest dataset has been repaired.

6. **Only then decide whether empirical research can run.**
   - Preserve the original sample period, market scope and frozen strategy specification.
   - Run the full empirical workflow only after every required input passes the pre-declared completeness policy and all price/funding series are correctly synchronized.
   - Do not inspect or optimize strategy performance to decide how missing bars should be treated.
   - If any material gap remains unresolved, retain **INCONCLUSIVE** and do not weaken the acceptance gate.
   - Synthetic smoke tests and passing CI validate plumbing only, never an empirical trading edge.

7. **Persist the outcome and the next handoff.**
   - Update the current data-gap task, README execution state, research report and audit/dispatch documentation with exact run IDs, actor/ref/SHA, artifact IDs, source hashes, gap counts, classifications, tests and scope limits.
   - Record whether the audit is complete, incomplete or unverified; distinguish source reconciliation from actual data repair and from empirical testing.
   - Commit a specific next task that advances the research-learning loop.

## Execution constraints

- Follow [the repository-wide adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md).
- Use the verified control route and exact commands documented in [the dispatch guide](../docs/CHATGPT-WORKFLOW-DISPATCH.md). The stable control surface is [PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2).
- Do not post duplicate commands while a matching workflow is queued or in progress.
- Keep GitHub permissions least-privilege. Do not checkout or execute control-PR head code.
- Keep raw market data and credentials out of Git, logs and user-facing artifacts.
- No live trading, capital deployment or automatic strategy promotion.

## Acceptance criteria

The existing audit run and all its artifacts have been inspected; all 31 ETH Spot gaps have exact source-based classifications; the four price series and both funding histories have independent completeness results; the data policy is explicit and tested; no observations have been fabricated or silently discarded; the empirical study is run only if every required gate passes; and the repository records the exact evidence and next task. Until then the study remains **INCONCLUSIVE**.
