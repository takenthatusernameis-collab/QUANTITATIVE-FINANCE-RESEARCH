Commit a pending task in this repository for the next agent to execute, and execute the pending task commited by the last agent!

## Environment-aware execution

- Execute the most recent pending task, then queue a clearly scoped pending task for the next agent.
- If blocked by network, runtime, dependency, permission, or time limits, treat that as an environment limitation—not a research result. Investigate practical alternatives.
- Network-dependent empirical work may use GitHub Actions. Create a **real workflow** under `.github/workflows/` with a valid trigger, job, hosted runner, environment/dependency setup, actual command, and useful artifact upload. An empty workflow file is not a solution.
- Prefer `workflow_dispatch` for expensive, one-off research; do not add recurring full-data runs unless specifically justified. If the workflow cannot be dispatched by available tools, clearly identify the manual step.
- Verify workflow runs, logs, and artifacts before calling a task complete. Upload results/manifests and hashes where useful; keep raw market-data files out of Git.
- Distinguish run enumeration from run inspection. An empty commit-associated workflow-run response may only mean no pull-request-triggered run was returned; it is not proof of no Actions run. When the complete run collection is accessible, record its total count and returned count before asserting that a workflow has no runs. If the available interface cannot list all runs, mark run existence/status **UNVERIFIED** and provide the exact owner-side Actions UI step. Inspect jobs/logs/artifacts only for known run IDs; do not claim exhaustive verification without a complete run listing.
- Preserve the original agent-loop prompt unchanged in `archive/ORIGINAL-AGENT-LOOP-PROMPT.md`. Update this README incrementally, focusing on execution reliability, evidence, reproducibility, and clarity.

## Current execution state — 2026-11-21

- The code audit corrections are merged. The funding-gap cadence defect was fixed in `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`; the subsequent metric/reporting audit was merged in `305bf5c70a14d8a8167dbbd4a22ec95f775402f7`.
- The latest test CI run, [44929570103](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44929570103) (run 16), completed successfully. Its `test` job passed all 17 deterministic unit tests and the synthetic plumbing smoke test. The test workflow produced zero artifacts, as expected. This is test CI, not the full empirical study.
- The run was on code commit `d7c3fc0b9ea75475a20b8d82c94aca6084073460`. The four commits from that SHA through current `main` HEAD `02088237366f963a4ce58429839e9329d6041efa` changed only README/task documentation; no research source or workflow files changed after the passing run.
- The complete Actions run collection returned `total_count=16` and all 16 records. Every run used `.github/workflows/research-tests.yml`; none used `.github/workflows/eth-btc-research.yml`. Therefore no full-data run was present in the complete run listing at the time of this check.
- The full empirical workflow exists at `.github/workflows/eth-btc-research.yml` and remains manual-only. The current GitHub integration can enumerate runs and inspect jobs, logs and artifacts, but exposes no `workflow_dispatch` action. It cannot start a new full-data run.
- The repository owner must open **Actions → ETH-BTC networked empirical research → Run workflow** on `main`, with start `2020-01-01`, end `2026-10-31`, market `both`. Do not add push or scheduled triggers to bypass this manual gate.
- Until that full real-data run completes and its artifacts/data-quality evidence are inspected, the ETH/BTC research conclusion remains **INCONCLUSIVE**. No live trading or capital deployment.
- Current next pending task: `tasks/ETH-BTC-POST-DISPATCH-ARTIFACT-REVIEW.md` (inspect the owner-dispatched full-data run and its artifacts; if no run exists, report the exact manual blocker).
