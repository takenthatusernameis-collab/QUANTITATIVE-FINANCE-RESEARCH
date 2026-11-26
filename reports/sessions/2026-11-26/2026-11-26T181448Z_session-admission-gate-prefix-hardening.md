# Session report — admission-gate prefix hardening

**Timestamp:** 2026-11-26T18:14:48Z  
**Objective:** Review the current research-factory handoff, complete the highest-value pending work, and persist a verified session record.

## Objective and workstream

The daily empirical-research KPI had already been met before this session. Four new real-data studies were recorded on 2026-11-26:

- Deribit relative DVOL / ETH-BTC realized volatility — run [45834522305](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45834522305)
- EPU / BTC downside semivariance — run [45845595390](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45845595390)
- MEXC BTC funding / Spot downside — run [45850573983](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45850573983)
- DeFiLlama stablecoin supply / BTC downside semivariance — run [45855398478](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45855398478)

No fifth backtest was started. The useful remaining task was a demonstrated governance weakness in the shared admission gate.

## Verified finding

All 23 research workflows used a substring condition:

`contains(github.event.head_commit.message, '[QFR-ADMIT]')`

That condition accepted any commit subject containing the marker, rather than only a complete research-admission commit. The recent MEXC preflight history included two subjects beginning `[QFR-ADMIT] preflight:`:

- `d676aca3` — deterministic-suite preflight
- `0e1cc271` — source-coverage preflight

Those commits ran the separate preflight workflow and did not launch the full MEXC backtest because its path filters did not match. They nevertheless exposed that the shared gate did not distinguish preflight intent from research admission.

## Change committed

The push gate for all 23 research workflows now requires the commit subject to start with:

`[QFR-ADMIT] research:`

The gate uses `startsWith(...)`. Preflight, source-feasibility, fixture, repair, documentation and workflow-scaffolding commits remain unmarked. `workflow_dispatch` remains available for explicitly authorized direct invocation.

The README and shared admission tests were updated to enforce this exact contract.

- [Commit 421dd131 — harden all research workflow gates](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/421dd13100233c6e920129db33e6e9ddc34a34f8)
- [Commit 57bcdec4 — align the KC PRS regression assertion](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/57bcdec4edd3fae6f2e00716fadc21cdb8323caa)

## Verification

The first admission-guard run, [#45874179437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45874179437), correctly detected one stale study-specific assertion in `test_kcprs_policy_skew_dgs2.py`, which still expected the old `contains` expression. That assertion was repaired in the ordinary unmarked commit `57bcdec4`.

The final guard run [#45874334557](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45874334557) passed. It ran 98 tests across the admission, VXN/VIX, KC PRS, WTI, Fed balance-sheet, Deribit and MEXC suites. The exact-prefix test and all-workflow gate test passed.

The workflow-file update triggered 20 matching research workflow runs; all 20 jobs were skipped. The KC PRS workflow triggered by its test-file correction was also skipped. No empirical backtest was launched by either maintenance commit.

## Research disposition and KPI

- **Daily KPI:** MET before this session by the four real-data studies listed above.
- **New hypothesis admitted:** None.
- **New empirical result:** None in this session.
- **Existing dispositions:** Unchanged; no hypothesis was promoted or reopened.
- **Live trading / capital deployment:** None.

## Failures and alternatives

The initial guard run failed only because the KC PRS unit test hard-coded the previous admission expression. The test was updated to assert the exact new prefix and to reject the old substring condition. The guard was rerun successfully.

No workflow dispatch, permission expansion, force-push or manual bypass was used.

## Next action

Preserve the exact `[QFR-ADMIT] research:` prefix for future complete atomic hypothesis admissions. Keep all preflight and same-hypothesis repair commits unmarked. The next substantive research cycle should introduce a materially different data mechanism rather than another small variation of the already screened macro predictors.

## Effort allocation

- Empirical research: 0% in this session; the daily KPI was already met.
- Operations / reproducibility controls: 100%, limited to the verified admission-gate weakness.
