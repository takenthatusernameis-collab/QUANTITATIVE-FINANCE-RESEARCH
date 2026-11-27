# Wake-up session — 2026-11-27T025653Z

## Objective
Complete the pending repository task: consolidate and operationalize the adaptive research decision hierarchy while preserving the current README path and existing research evidence.

## Repository preflight — VERIFIED
- Starting main: `91904b2b2a290f734308f98cef2d4810faea6069`.
- Starting main commit message: `Clarify non-informative directional metric and forecast metric units`.
- No active GitHub Actions runs were present at preflight.
- No open PRs or standalone issues were present.
- The prior BTC taker-absorption backtest already satisfied the 2026-11-27 real-data backtest minimum; no duplicate backtest was dispatched.
- The canonical active queue file is absent on main; the README is the self-contained wake-up contract.
- The latest empirical result remains `INCONCLUSIVE`; no tuning or rerun was undertaken.

## Implemented
- Added a canonical ordered decision hierarchy to README, including hard invariants, state reconciliation, compounding process optimization, original-source recovery, research-specific provider failover, data-architecture alternatives, timeframe/model replacement and hypothesis replacement.
- Preserved the current MEXC-first scoped funding pilot and documented Coinbase-before-Kraken only as a conditional, re-admitted ETH/BTC spot example; no universal vendor ranking was introduced.
- Added explicit stop rules: two identical non-transient failures exhaust a route; two distinct non-transient provider failures advance to a materially different data architecture.
- Preserved spot/perpetual separation and the requirement for final accepted funding settlements before perpetual-futures evaluation.
- Added a pure deterministic decision selector and 18 regression tests covering invariant blocks, duplicate-output reuse, concurrent owners, deadline recovery, provider ordering, repeated failures, two-provider escalation, architecture/timeframe/model fallback, hypothesis replacement and funding separation.
- Added the new module/tests to the repository admission-guard workflow and added a guard test that checks the canonical README contract and CI wiring.
- Removed the one-time top-line instruction after completing it; the README filename and canonical path were not changed.

## Validation
- Local deterministic decision-policy suite: 19/19 passed after follow-up hardening.
- GitHub Actions admission-guard suite: PASS on the implementation commit (run 45931775351) and on the hardened follow-up commit (run 45931844406).
- No empirical market-data test was run in this session; the daily KPI was already satisfied by run 45926394994.
- The policy helper is a pure reference selector. It does not fetch data, dispatch workflows or replace evidence review.

## Research and operations
- Research output: no new empirical hypothesis; the prior valid daily backtest remains the KPI evidence.
- Operations: one canonical decision-policy implementation, one regression suite, and one README/CI integration.
- No source acceptance, profitability or trading claim was added.

## Remaining verification
- Confirm the atomic implementation commit and the triggered admission-guard workflow.
- Record any CI failure and repair it in an unmarked follow-up commit; do not launch a new empirical run for this policy change.

## Follow-up hardening

The first guard run passed, but code review found that the route-stop counter grouped all non-transient errors on a route together. The rule is specifically about two identical non-transient failure classes on the same route. Added an explicit failure-code dimension and a regression proving that two different failure classes do not prematurely exhaust a route. The repeated identical failure case remains covered. The policy suite now contains 19 tests.

## Final verification — VERIFIED

- Canonical implementation commit: [eafc19d](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/eafc19d775c9a0d400ce2af1872c3aac11378c8e).
- Failure-class accounting hardening commit: [c0fae08](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/c0fae081e4d37d18259a94b902c7486db2599efe).
- Admission guard run [45931775351](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45931775351) passed on the initial implementation commit.
- Final admission guard run [45931844406](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45931844406) passed on the hardened follow-up commit. All 19 decision-policy tests and all existing guard regression steps passed.
- The policy-change commits did not admit or duplicate a market-data backtest; the research admission prefix was not used.
- Main immediately before this report update: `c0fae081e4d37d18259a94b902c7486db2599efe`.
