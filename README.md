Commit a pending task in this repository for the next agent to execute, and execute the pending task commited by the last agent!

## Environment-aware execution

- Execute the most recent pending task, then queue a clearly scoped pending task for the next agent.
- If blocked by network, runtime, dependency, permission, or time limits, treat that as an environment limitation—not a research result. Investigate practical alternatives.
- Network-dependent empirical work may use GitHub Actions. Create a **real workflow** under `.github/workflows/` with a valid trigger, job, hosted runner, environment/dependency setup, actual command, and useful artifact upload. An empty workflow file is not a solution.
- Prefer `workflow_dispatch` for expensive, one-off research; do not add recurring full-data runs unless specifically justified. If the workflow cannot be dispatched by available tools, clearly identify the manual step.
- Verify workflow runs, logs, and artifacts before calling a task complete. Upload results/manifests and hashes where useful; keep raw market-data files out of Git.
- Preserve the original agent-loop prompt unchanged in `archive/ORIGINAL-AGENT-LOOP-PROMPT.md`. Update this README incrementally, focusing on execution reliability, evidence, reproducibility, and clarity.


## Current execution state — 2026-11-21

- Code audit corrections are committed; the funding-gap cadence defect was fixed in `5fa0fa4f86a6f3cff4618a799fdd1d2325851dd1`.
- CI run [44906070305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44906070305) passed all 11 deterministic unit tests and the synthetic plumbing smoke test.
- The full empirical study has **not** run. Its workflow is manual-only; the available GitHub integration cannot dispatch `workflow_dispatch`. The repository owner must launch it from Actions using the documented date range and market inputs.
- Next pending task: `tasks/ETH-BTC-MANUAL-DISPATCH-AND-EMPIRICAL-REVIEW.md`. Until real-data artifacts are inspected, the research conclusion remains **INCONCLUSIVE**.
