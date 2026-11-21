# Pending Research Task: Reconcile ETHUSDT Hourly Data Gaps Before the Full ETH/BTC Study

**Status:** Pending  
**Priority:** High  
**Type:** Data provenance, completeness diagnostics and deterministic validation  
**Scope:** Research/backtesting only. No live orders, capital deployment or raw market-data commits.

## Context

The full-data workflow was dispatched twice on 2026-11-21:

- [Run 44943960222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943960222)
- [Run 44943965775](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943965775)

Both runs used `2020-01-01` through `2026-10-31`, `market=both`, and the same `main` commit. The hosted runner successfully downloaded all 82 monthly Binance Spot ETHUSDT archives and verified all 82 published checksums, but the pipeline stopped because 31 expected hourly bars were absent. There were no duplicate timestamps, no missing archive months, and the longest observed gap was six hours.

Both artifacts contain only `data/raw/spot_ETHUSDT_archive_manifest.json`; the manifest stores only the first 20 missing-hour samples. The raw consolidated CSV was deliberately not uploaded. See `reports/ETH-BTC-POST-DISPATCH-REVIEW-2026-11-21.md`.

This is a data-completeness issue, not a network-permission failure. Do not repeat the same full-data run without changing or validating the data-quality outcome.

## Objectives

1. **Recover the full gap inventory.**
   - Extend `hourly_quality` and the archive manifest to preserve every missing timestamp or a lossless list of contiguous gap intervals, not just the first 20 examples.
   - Record expected and observed row counts, all gap start/end times, gap durations, archive-month attribution and source file hashes.
   - Keep output size bounded and deterministic.

2. **Independently reconcile the 31 ETH spot gaps.**
   - Query Binance's official Spot klines REST endpoint for each missing hour (or a bounded batch covering the gap) and inspect the corresponding archive data.
   - Where available, compare the monthly archive with a daily archive or another official Binance representation.
   - Record the request parameters, response status, returned open times, timestamp units, source URL and retrieval time.
   - Distinguish: (a) a candle present in the official API but absent from the monthly archive; (b) a candle absent from both official representations; and (c) an unresolved source discrepancy.
   - Do not infer that a missing bar means zero return or zero volume without evidence.

3. **Audit all four price series even when one fails.**
   - Add a non-fail-fast data-audit mode or equivalent so it attempts spot ETHUSDT, spot BTCUSDT, USDⓈ-M ETHUSDT and USDⓈ-M BTCUSDT, records each manifest and reports all failures before returning a nonzero status.
   - Do not begin the strategy backtest while any required series fails its declared acceptance policy.
   - Check timestamp-unit conversion, duplicate rows, missing archive months, missing hours, sample bounds and checksums independently for each series.

4. **Audit funding separately.**
   - Verify ETH and BTC funding-event start/end coverage, duplicate timestamps, event gaps, timestamp alignment and missing intervals.
   - Preserve the distinction between no funding event and missing funding data; never silently substitute zero.

5. **Choose and test a defensible missing-bar policy.**
   - Prefer recovering an authenticated source candle when one exists.
   - Never fabricate OHLC values, forward-fill prices or silently drop intervals.
   - If official sources confirm that an interval legitimately has no candle, document how the strategy's open-to-open PnL and synchronized-pair calculations handle that interval. Any policy change must be explicit, causal, tested and documented before inspecting strategy performance.
   - If the gap cannot be reconciled, keep the affected dataset incomplete and the overall research conclusion **INCONCLUSIVE**.

6. **Add deterministic tests.**
   - Test full missing-timestamp/gap-interval serialization.
   - Test REST/archive reconciliation, duplicate detection, timestamp-unit normalization and unresolved gaps.
   - Test that a non-fail-fast audit reports all four price series even when the first one fails.
   - Test that missing funding events cannot be silently converted to zero.

7. **Re-run only after validation.**
   - Run the research test suite and synthetic smoke test.
   - If every required series passes the pre-registered completeness policy, dispatch the existing full empirical workflow with the original date range and market selection.
   - Inspect all run logs, artifacts, manifests and hashes before interpreting any strategy statistics.
   - Keep raw market data out of Git.

## Execution and workflow constraints

- Use the existing `.github/workflows/eth-btc-research.yml` where practical; do not create a second broad data workflow merely to avoid the current quality gate.
- Keep the full-data workflow on-demand and retain `workflow_dispatch` as the manual fallback.
- The repository's issue-comment dispatch bridge is **NOT ENABLED / NOT END-TO-END VERIFIED**. There is no dedicated control issue and the exact ChatGPT-connected comment identity has not been verified. Do not assume the bridge can trigger this task.
- If a new on-demand workflow is genuinely necessary, follow `docs/CHATGPT-WORKFLOW-DISPATCH.md`: unique exact command, dedicated ordinary control issue, exact allowlisted login, non-PR check, full-command equality, and manual `workflow_dispatch` fallback. If those prerequisites are not verified, mark the indirect path **NOT ENABLED**.
- Do not add unguarded `push` or recurring `schedule` triggers.
- Do not expose credentials in source or logs.
- No live trading, capital deployment or automatic strategy promotion.

## Deliverables

- Complete missing-hour inventory or lossless gap intervals.
- Per-series archive/API reconciliation manifests with provenance and hashes.
- Non-fail-fast audit output for all four price series.
- Funding completeness audit.
- Deterministic tests and successful test CI.
- Updated research report, README and execution handoff.
- A supported **GO / NO-GO / INCONCLUSIVE** status. Until all required evidence is complete, retain **INCONCLUSIVE**.

## Acceptance criteria

The 31 ETH spot gaps have been individually reconciled or explicitly classified as unresolved; all four price series and both funding histories have been audited; no data have been fabricated or silently discarded; deterministic tests pass; and the full empirical workflow is run only after the declared data policy passes. A successful synthetic test or a successful archive download alone is not empirical evidence.
