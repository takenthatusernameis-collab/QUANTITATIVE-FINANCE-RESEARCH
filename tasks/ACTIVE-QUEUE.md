# Active Repository Queue

**Updated:** 2026-11-22 04:45 UTC  
**Canonical active-task pointer:** [ETH/BTC ingestion and no-trade validation](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

## Operating priority

Optimize the probability of trustworthy, reproducible research while removing verified manual-intervention and orchestration bottlenecks. Preserve scientific and security gates. Do not create duplicate task plans, reports, runs, incidents or artifacts.

## Current verified state

### Research implementation and tests

- Daily checksum-verified Binance Spot `aggTrades` archive fallback is implemented in [commit cdb9e76](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/cdb9e76ca690651e256f3c5dfe585361e7a21b27). Initial fixture failures were diagnosed and corrected in [commit bd5375f](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/bd5375f00b01b50241191cac422fb6be107d438e).
- [Research CI run 44985194153](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44985194153) passed 61 deterministic tests and the synthetic plumbing smoke test on code commit `19ddf6bd`. This validates engineering/plumbing only, not production data completeness or strategy performance.
- Three representative Tardis/Binance funding samples (2020-06-01, 2024-01-01 and 2026-03-01) matched the visible next-funding-event timestamps within 15 seconds for both ETHUSDT and BTCUSDT. Tardis `funding_rate` remains a pre-event estimate, not the final settled rate. These samples do not prove full payable-settlement completeness.
- Binance public-data issue [#517](https://github.com/binance/binance-public-data/issues/517) remains open (last updated 2026-11-19). Keep Binance funding `PROVISIONAL_NOT_ACCEPTED` until the complete event population and contract/history semantics are authoritative.

### Active empirical audit

- Full six-input audit run [44986170330](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986170330) was triggered by control-PR comment [7074321816](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7074321816), event `issue_comment`, actor `takenthatusernameis-collab`, checked-out SHA `0b1aaccd`.
- Authorization, dependency installation and synthetic plumbing smoke test passed. The non-fail-fast all-series audit was **IN_PROGRESS** at 2026-11-22 04:44 UTC; no artifact was available at that check. Empirical preflight/backtest had not started.
- **Do not dispatch a duplicate audit.** Resolve this exact run, inspect its logs and artifact, and record all six manifests plus both Spot-symbol gap classifications and positive-control outcomes.

### Queue guardian and orchestration

- Live queue-guardian run [44986166616](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986166616) executed from control-PR comment [7074321256](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2#issuecomment-7074321256), event `issue_comment`, mode `LIVE_ENFORCEMENT`, SHA `0b1aaccd`.
- Its report enumerated 117 repository workflow runs completely; 100 belonged to the two monitored research/test workflows, with the latest 50 retained. It recorded `actions=[]`, `errors=[]`, and updated the bot-owned status comment. This verifies the live PR-comment enforcement path; it does **not** verify the five-minute scheduled trigger.
- The prior complete run inventory contained no `schedule` event for the queue guardian. Scheduled enforcement remains **UNVERIFIED** until a genuine schedule-triggered run is observed.
- The open `[QFR queue guardian]` issue search returned zero incidents. Preserve the 15-minute cancellation threshold and exact earlier active same-group predecessor exception.

### Hygiene and repository state

- The latest recursive default-branch inspection found 39 tracked paths and no tracked cache/bytecode, scratch, raw market-data or generated-report clutter. Remote inspection cannot establish local untracked working-tree state.
- Five branches and open draft control PR #2 were preserved. Delete or archive nothing without verified merge/abandonment and active-run ancestry.
- Keep raw market data, bulky logs and generated outputs in retained artifacts/storage; keep compact manifests, hashes and decision summaries in Git.

## Next executable actions

1. Resolve run 44986170330; inspect the final job result, logs and artifact. Confirm all six manifests exist and classify every Spot gap for both symbols using checksum-verified trade archives and passing known-active controls.
2. Keep funding provisional until authoritative evidence establishes event semantics, contract incarnation/retention and the complete payable-settlement population. The three Tardis samples are schedule cross-checks, not a full settlement ledger.
3. If any source remains blocked, switch to a materially different lawful provider or a separately specified synchronized ETH/USD divided by BTC/USD experiment. Do not merge alternative-source results into the original Binance study, fabricate observations, forward-fill or relax acceptance gates.
4. Verify an actual scheduled queue-guardian event separately from the successful live PR-comment run. Until then, retain the agent-triggered live route as a bounded fallback and do not claim cron enforcement is verified.
5. Run empirical strategy computation only after the selected experiment's complete data, missing-observation, funding and methodology gates pass. Record a negative or inconclusive result when warranted.

## Non-negotiable boundaries

No live orders, capital deployment, live credentials, custody changes or automatic strategy promotion. Routine historical research and validation must remain agent-triggered within existing authorized scope.

**Research conclusion:** the original Binance ETH/BTC study remains **INCONCLUSIVE**. No empirical strategy metrics or valid backtest have been produced.
