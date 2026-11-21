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
- Follow the repository-wide [Adaptive Autonomous Research Execution Standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) and its [adaptive dispatch implementation guide](../docs/CHATGPT-WORKFLOW-DISPATCH.md).
- The repository does not yet have a verified autonomous ChatGPT dispatch route. Treat this as an engineering bottleneck to resolve, not as a reason to stop at a human UI action. Inspect the current connected integration's actual capabilities. The observed GitHub connector exposes PR-conversation commenting but not a clearly supported ordinary-issue-comment action or direct workflow-dispatch POST; revalidate before implementation.
- First test whether the connected PR-comment action can initiate a harmless event. If ordinary-issue commenting is unsupported but PR commenting works, evaluate a dedicated, exact-number control PR with a strict actor/command gate. GitHub's `issue_comment` event runs from the default branch; never checkout or execute the control PR head. If this is not secure or supported, pursue an authorized GitHub App/API relay, `repository_dispatch`, or another demonstrably viable autonomous route.
- Keep execution on-demand, idempotent, observable and recoverable. Do not add unguarded `push` or recurring `schedule` triggers, broad permissions, or repeated identical failed dispatch attempts.
- `workflow_dispatch` may remain as a human-owned break-glass recovery path where appropriate, but it is not the normal agent procedure and does not satisfy autonomous acceptance. Do not repeatedly route the human to the Actions UI; identify an owner-only permission/secret prerequisite only when no agent-executable alternative remains.
- Never expose credentials in source or logs.
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
