# Pending Research Task: Review the Owner-Dispatched ETH/BTC Empirical Run

**Status:** Pending owner-side manual dispatch; no full-data run was present in the complete Actions run listing on 2026-11-21  
**Priority:** High  
**Type:** Empirical artifact validation and evidence-based strategy review  
**Scope:** Research/backtesting only. No live orders or capital deployment.

## Context

The manual-only workflow is `.github/workflows/eth-btc-research.yml`. The complete Actions run listing returned 16 runs; all 16 used `.github/workflows/research-tests.yml`, and none used the full-data workflow. The latest test run, [44929570103](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44929570103), passed all 17 deterministic unit tests and the synthetic plumbing smoke test. Its zero artifacts are expected for the test workflow.

The available GitHub integration can enumerate and inspect workflow runs but has no action to dispatch a new `workflow_dispatch` run. The repository owner must open **Actions → ETH-BTC networked empirical research → Run workflow** and submit:
- branch: `main`
- start: `2020-01-01`
- end: `2026-10-31`
- market: `both`

Do not add push or scheduled triggers to bypass this manual gate. Do not treat synthetic test output as empirical evidence.

## Network and execution-environment fallback

If the agent's own network access is denied while obtaining research inputs or inspecting a required external source, distinguish explicit permission denial from transient timeouts. After two independent explicit network-permission denials, stop repeating the blocked request and use a suitably scoped GitHub Actions runner for the network-dependent work where feasible. Record the exact error, attempt count, workflow run ID, commit SHA, logs and artifacts. Keep secrets out of code and logs. The issue-comment dispatch bridge is not usable until its dedicated control issue, approved identity and trigger have been configured and tested; otherwise use the exact manual dispatch fallback in this task. If the Actions runner is also blocked, report that environment blocker and keep the conclusion **INCONCLUSIVE**.

## Workflow activation policy

The repository-wide workflow activation rule in [docs/CHATGPT-WORKFLOW-DISPATCH.md](../docs/CHATGPT-WORKFLOW-DISPATCH.md) applies to this task and to any auxiliary workflow created while completing it.

- The full ETH/BTC study should retain `workflow_dispatch` as the owner/manual fallback and, once the shared control issue and actual ChatGPT-connected GitHub identity have been verified, gain its own exact `issue_comment: created` command gate (reserved command: `/run-eth-btc-research`).
- Any additional workflow created for network-permission failures, alternate data retrieval, diagnostics, dependency/runtime problems, validation, reporting, or another subtask must also have its own unique command on that same dedicated control issue, with the exact approved-author, issue-number, non-PR and full-command checks. Do not leave an on-demand agent workflow manual-only when the indirect route can be configured in the same change.
- Do not assume the bridge is enabled merely because its design is documented. If the control issue or approved author identity is not yet verified, mark the indirect route **NOT ENABLED**, keep the manual fallback, and record the missing prerequisite.
- Do not replace these guarded activation paths with broad `push` or recurring `schedule` triggers. Native-event CI workflows remain separate and need not receive comment commands unless ChatGPT also needs to start them on demand.

## Required work

1. Enumerate current Actions runs and identify a run whose workflow path is `.github/workflows/eth-btc-research.yml`. If none exists, report the exact owner-side dispatch step above and stop; do not invent a run ID or claim that data was tested.
2. For a verified full-data run, inspect every job and step, fetch logs, and inspect the artifact inventory. Record the run ID, commit SHA, status, conclusion, artifact names, sizes and hashes where available.
3. Download and inspect the generated report, CSV summaries, charts, data-quality JSON, archive/checksum manifests, funding manifests and run manifest. Keep raw market-data CSVs out of Git.
4. Validate the 2020-01-01 through 2026-10-31 sample bounds, per-symbol hourly continuity, row counts, duplicate timestamps, missing hours, skipped archive months, timestamp units, archive checksum results, funding-event coverage, event alignment and missing funding intervals. Do not let missing data silently become zero observations.
5. Review out-of-sample folds and volatility regimes, net returns after the stated cost scenarios, benchmark accounting, funding attribution, turnover, drawdowns, bootstrap uncertainty and stress scenarios. Separate statistical cointegration from a durable net trading edge.
6. Disclose the limits of illustrative fees, spread/slippage proxies, spot borrow availability/costs and omitted liquidation, partial-fill, queue-position and outage mechanics.
7. Update the dated research report, README and task status with reproducible evidence and a **GO / NO-GO / INCONCLUSIVE** conclusion. Keep the conclusion **INCONCLUSIVE** if the full-data run or required evidence is unavailable.

## Safety and research controls

- Preserve the pre-registered entry/exit/stop thresholds and walk-forward design; do not optimize after seeing out-of-sample results.
- Keep the manual `workflow_dispatch` trigger as a fallback; a strictly gated `issue_comment: created` trigger using the documented bridge is permitted once its control issue and approved identity are verified. Do not add unguarded `push` or recurring `schedule` triggers.
- No live trading, capital deployment or raw market-data commits.

## Acceptance criteria

A verified full-data workflow run has completed successfully; all jobs, logs and artifacts have been inspected; data-quality checks and result tables are validated; hashes and run provenance are recorded; and the conclusion is evidence-based. If owner dispatch has not occurred, record the exact blocker and leave the empirical conclusion **INCONCLUSIVE**.
