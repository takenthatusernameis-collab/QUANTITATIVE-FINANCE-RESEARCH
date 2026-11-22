COMMIT TO REPOSITORY THE PENDING TASK

# Original agent-loop prompt

Commit a pending task in this repository for the next agent to execute, and execute the pending task commited by the last agent!

**No verified repository commit means no completed commit assignment.**

## Repository guiding ideal

**Continuously increase the probability that each agent cycle produces trustworthy, reproducible, decision-useful quantitative-finance research, while making the research system more autonomous, resilient, and capable after every cycle.** Success means obtaining a defensible research conclusion—including a negative, null, or inconclusive result when that is what the evidence supports—not manufacturing a profitable strategy or forcing a positive finding.

Operate as an evidence-driven, self-improving research loop:

1. **Prioritize the highest-value uncertainty or bottleneck.** Define the research question, falsifiable hypotheses, baselines, required data, decision criteria, and acceptance gates before inspecting the result. Preserve the research objective when the first proposed method or tool fails.
2. **Protect empirical validity.** Use provenance-complete data, causal and temporal correctness, realistic fees, slippage and funding, frozen specifications, independent holdouts, robustness checks, and appropriate controls for overfitting and multiple testing. Never fabricate, silently omit, or selectively repair evidence; never weaken a gate after seeing results.
3. **Separate evidence from infrastructure success.** A passing unit test, synthetic smoke test, successful workflow dispatch, or complete data download is not proof of an empirical edge. Report uncertainty, limitations, negative findings, and unresolved gaps accurately, with reproducible methods and inspectable artifacts.
4. **Turn friction into learning.** Treat every failure, near miss, unexpected result, and tool, permission, data, compute, runtime, storage, or orchestration bottleneck as a diagnostic signal. Preserve the evidence, identify the root cause, compare materially different secure alternatives, and implement the smallest useful, testable improvement rather than repeating an unchanged failed attempt.
5. **Make improvements antifragile.** Do not merely tolerate or retry failures: use what they reveal to strengthen future performance through bounded retries, idempotency, checkpoints, observability, regression tests, recovery paths, graceful fallbacks, and documented decision rules. Prefer reversible, least-privilege changes and verify that each improvement works end to end.
6. **Measure progress rather than assume it.** Track research validity and reproducibility, data completeness, verified task completion, recovery reliability, recurring bottlenecks, handoff quality, operating cost, and the number and cause of manual interventions. Improve these measures without contaminating holdouts, optimizing vanity metrics, or trading away scientific or security requirements.
7. **Automate what has been proven.** Gradually connect discovery, data acquisition, experiment design, computation, validation, reporting, monitoring, recovery, and task handoff into a reliable, observable, idempotent agentic loop. Each cycle should remove or materially reduce a verified bottleneck, preserve what was learned, and queue the next highest-value task.

**Trajectory:** steadily reduce routine human intervention toward reliable end-to-end operation without routine supervision. Humans should remain involved for genuinely owner-authorized permissions, security-sensitive choices, capital-risk decisions, and other actions that require explicit human authority. Autonomy is a direction to work toward—not permission to bypass authorization, scientific acceptance gates, or safe operating boundaries.

**The governing test for every change is whether it measurably improves the probability of producing valid research and makes the next cycle more capable of completing the work safely, reproducibly, and with less routine intervention.**

### 8. **Never block routine research on manual confirmation.** Historical backtests, data retrieval, CI, audits, code changes and ordinary report generation within existing authorized permissions must be initiated and completed by the agent. A statement such as "the backtest is ready, but I need the owner to manually activate it" is defined as **FAILURE**. Repair the trigger or use another authorized agent-controlled execution path. Only stop a specific action for a genuine security/legal boundary or an explicitly unauthorized live financial action; continue all independent work.

### 9. **Repeated failure requires a different approach.** Do not repeatedly download the same incomplete archives, hit the same blocked endpoint, use the same failing parser, or restate the same blocker. After a meaningful failure, diagnose it and test materially different alternatives: another authorized endpoint/provider, raw trade data, a different data architecture, separate ETH/USD and BTC/USD pipelines with a synchronized ratio (ETHUSD/BTCUSD), another timeframe, or a more feasible model/hypothesis. Use positive controls, provenance, and pre-registered acceptance gates. Never bypass a legal access restriction, fabricate bars, forward-fill, or weaken scientific standards.

### 10. **Keep the research loop moving.**

**Agent-triggered backtest command:** `/qfr-run-eth-btc-empirical` is allowlisted on control PR #2. It automatically runs an all-six-input preflight and only runs the historical strategy backtest if the preflight passes. The agent, not the user, initiates the command. No manual confirmation is a prerequisite for historical backtesting within the existing authorized scope.
 If the original model cannot be implemented with valid accessible data after distinct alternatives, mark that specific experiment INCONCLUSIVE/INFEASIBLE and move to a separately specified, feasible research question. Do not let one provider, one data pair, or one strategy block all quantitative research. Count routine manual interventions as autonomy failures and remove their causes.


---

# Agent operating standard

Every agent must follow [docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md](docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md). This is the repository-wide standard for current and future research, engineering, and automation tasks.

## Mission and operating rules

- Execute the highest-priority pending task, then leave a specific, evidence-based next task.
- Optimize for trustworthy, reproducible quantitative research learning and progressively autonomous execution. Treat the first proposed method as an option, not a constraint.
- When a tool, API, permission, trigger, runtime, data source, or storage path blocks progress, diagnose the precise cause, inspect actual connected capabilities, generate materially different secure alternatives, and test the smallest safe proof. Do not stop at the first blocked route or repeat an identical denied operation.
- **Adaptive autonomous orchestration:** every on-demand agent task must have a demonstrated machine-triggerable execution path. Select the route from actual available capabilities—direct workflow dispatch, issue-comment event, PR-comment event where securely gated, GitHub App/API relay, repository dispatch, or another authorized mechanism. Do not hard-code one event type as the only acceptable solution.
- Do not make routine human UI actions the agent's operating plan or count them as autonomous completion. A manual workflow control may remain as a break-glass owner recovery path, but it must not displace the agent's responsibility to remove the automation bottleneck.
- If a genuinely owner-only permission, app installation, or secret is required, complete all independent work, prepare the smallest scoped setup, identify the exact prerequisite once, and continue all other feasible work. Never request broad access or expose credentials.
- Network-dependent tasks may use an authorized hosted runner when the agent environment is blocked. Use bounded retries for transient faults; after two independent identical explicit permission denials, switch route/environment rather than retrying unchanged. Preserve requests, logs, source metadata, manifests, hashes, and artifacts.
- Use real workflows with a valid trigger, least-privilege permissions, pinned dependencies where practical, actual commands, useful logs, checkpoint/recovery where needed, and inspectable artifacts. Avoid broad `push` triggers and recurring `schedule` jobs unless evidence justifies them.
- Preserve data completeness, source provenance, causality, holdout independence, realistic fees/slippage/funding, survivorship controls, frozen strategy specifications, and statistical validation. Never fabricate, forward-fill, silently drop, or weaken research gates to force a pass.
- No live trading, capital deployment, live credentials, or automatic strategy promotion without separate explicit authorization.
- Verify end-to-end execution, actor, event, workflow path, commit, parameters, logs, artifacts, and outputs before claiming success. Synthetic tests validate plumbing, not empirical strategy performance.
- Preserve negative results and failure evidence. Update persistent documentation so the next agent inherits what was learned rather than rediscovering the same blocker. Keep raw market data out of Git.
- For complete run enumeration, record total and returned counts. If the available interface cannot establish full run existence/status, mark it **UNVERIFIED** and identify the next machine-checkable verification step.

## Dispatch implementation guidance

Start with [docs/CHATGPT-WORKFLOW-DISPATCH.md](docs/CHATGPT-WORKFLOW-DISPATCH.md), but follow its adaptive decision process rather than assuming an ordinary issue-comment bridge is available. Test the actual connected integration. If it supports PR comments but not ordinary issue comments, evaluate the tightly gated control-PR route; otherwise evaluate a scoped GitHub App/API relay or another secure event-driven mechanism. Any chosen path must pass a harmless ChatGPT-triggered end-to-end test before it is treated as active.

## Historical execution state — 2026-11-21 (post-dispatch review)

This snapshot is superseded by the 2026-11-22 audit artifact review below.

- The latest test CI run, [44943912907](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943912907) (run 18), passed on current `main`: all 17 deterministic unit tests and the synthetic plumbing smoke test passed. This validates code/test plumbing only.
- The complete Actions run listing returned `total_count=20` and all 20 records. It contains 18 research-test runs and two full-data runs from `.github/workflows/eth-btc-research.yml`.
- Full-data runs [44943960222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943960222) and [44943965775](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943965775) were both dispatched on `main` commit `fd93291e73693f6b1f9a534d2c1eb84804f7afeb`, using `2020-01-01` through `2026-10-31` and `market=both`. Both passed setup, dependency installation and the synthetic smoke test, then failed at the first real-data gate: `Incomplete spot ETHUSDT data: missing archives=[], duplicates=0, missing hours=31`.
- The hosted runner successfully downloaded all 82 expected monthly ETH spot archives and verified all 82 published checksums. The manifest reports 59,873 rows versus 59,904 expected, 31 missing hourly bars, zero duplicates, a six-hour maximum gap, correct requested sample boundaries, and `complete=false`. This is a source/data-completeness failure, not a network-permission denial.
- Both run artifacts contain only `data/raw/spot_ETHUSDT_archive_manifest.json`. The manifest content hash is `2201e259c23678b11f05725bbfa051ff0789742cf3aad108aea42703315abe5a`; the manifest records only the first 20 of 31 missing timestamps. No raw CSV, funding manifest, generated report or strategy metric was produced.
- The pipeline stopped at spot ETHUSDT. Spot BTCUSDT, both USDⓈ-M series, funding histories, pair synchronization and all empirical strategy metrics remain unvalidated. The research conclusion is **INCONCLUSIVE**.
- Autonomous ChatGPT dispatch is **END-TO-END VERIFIED FOR THE HARMLESS SMOKE PATH** through the exact-actor, exact-command PR-comment bridge on [control PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2). Smoke run [44963633770](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963633770) succeeded on `main` as actor `takenthatusernameis-collab`; no PR-head code is checked out or executed. The full non-fail-fast data-audit and official-source gap-reconciliation run [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383) is currently in progress. Dispatch verification does not establish data completeness or empirical performance.
- The post-dispatch artifact review is complete. The data-gap task [`tasks/ETH-BTC-DATA-GAP-RECONCILIATION.md`](tasks/ETH-BTC-DATA-GAP-RECONCILIATION.md) is in progress: complete gap/provenance reporting, non-fail-fast auditing, source reconciliation, regression tests and the autonomous PR-comment dispatch route are committed. Audit-only run [44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383) is still executing; do not duplicate it. Next pending handoff: [`tasks/ETH-BTC-AUDIT-ARTIFACT-REVIEW-AND-DATA-POLICY.md`](tasks/ETH-BTC-AUDIT-ARTIFACT-REVIEW-AND-DATA-POLICY.md), which requires inspecting its completed artifacts, classifying all 31 gaps and finalizing the data policy before any empirical rerun.
- Detailed evidence, run IDs, artifact IDs, hashes and scope limitations: [`reports/ETH-BTC-POST-DISPATCH-REVIEW-2026-11-21.md`](reports/ETH-BTC-POST-DISPATCH-REVIEW-2026-11-21.md).


## Current execution state — 2026-11-22 (audit artifact review)

- Audit-only command `/qfr-run-eth-btc-data-audit` on [control PR #2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/2) triggered [run 44963655383](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963655383). The exact actor `takenthatusernameis-collab`, `issue_comment: created`, PR #2, whole-body command, `main` ref, workflow path, and SHA `96b93aeba313d9a083bb031a949955cb8e606509` were verified in the authorization logs.
- The run completed with a data-audit failure (exit code 2), not a dispatch failure. Authorization, default-branch checkout, dependency installation and synthetic smoke test passed; the empirical step was skipped; artifact upload succeeded.
- GitHub reported 24 Actions runs and returned all 24. The run produced one artifact, ID `14730731258`, 23,851 bytes, ZIP SHA-256 `82a8f6e9c6bb82d2ec43af8107a2b2f487321c8a54f84de0bf1693f1da602704`. It contains two Spot manifests, one gap-reconciliation manifest and one audit summary; no raw CSV.
- Spot ETHUSDT and BTCUSDT each have 82/82 monthly archives checksum-verified, 59,873/59,904 rows, 31 missing hours and zero duplicates. The same 31 timestamps are absent in both. Fifteen daily ETH archives were checksum-verified, but the 31 corresponding candles are absent; all 31 hosted-runner REST requests failed with HTTP 451. The current classifier incorrectly treats request failure like a successful empty response.
- USDⓈ-M ETHUSDT and BTCUSDT archive parsing fails at January 2022 with `Invalid open_time values`. ETH and BTC funding retrieval both fail with HTTP 451. No futures or funding manifests were emitted, so four of six required inputs lack valid completeness results.
- **Decision: INCONCLUSIVE.** Do not forward-fill, synthesize bars, assign zero returns/volume, or relax the hourly gate. The current backtest would misstate a multi-hour return as one hourly return if continuity were relaxed without an elapsed-time redesign.
- The audit review and full evidence are in [reports/ETH-BTC-AUDIT-ARTIFACT-REVIEW-2026-11-22.md](reports/ETH-BTC-AUDIT-ARTIFACT-REVIEW-2026-11-22.md). Next pending task: [tasks/ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md](tasks/ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).
- CI run [44963445206](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44963445206) passed the deterministic unit-test and synthetic smoke-test steps. This is engineering evidence only, not market-data completeness or strategy performance.
- The PR-comment dispatch route is now verified for both the harmless smoke command and the audit-only command. PR #2 remains open and draft as the stable control surface. No empirical backtest or live action was performed.