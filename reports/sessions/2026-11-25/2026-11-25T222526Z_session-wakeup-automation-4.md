# Research factory wake-up — 2026-11-25T222526Z

## Objective

Reconcile main, registry and recent Actions; admit one materially distinct real-data hypothesis; verify the positive [QFR-ADMIT] path; restore the user's original commit directive at the top of the scheduled README.

## Repository audit

- main before this session: 558b39b8d2742518e34ad6d39cc0ea02f1dbcb15.
- The README documented [QFR-ADMIT], but its first line no longer contained the user's exact phrase. This session restores COMMIT TO REPOSITORY THE PENDING TASK as line one.
- Registry: ten distinct 2026-11-25 real-data hypotheses; three REJECTED, seven INCONCLUSIVE, none promoted to trading.
- The 2026-11-25 daily real-data backtest KPI was already MET. Latest admission-guard run before this session, [45703452010](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45703452010), succeeded. No active Actions runs, open issues or open PRs were returned by the inspected endpoints.

## Research selection

Admitted QFR-2026-11-25-ANFCI-TIGHTENING-SP500-RV-01: test whether the four-week change in the Chicago Fed Adjusted National Financial Conditions Index adds information about next-five-session S&P 500 realized volatility beyond recent realized volatility and VIX. This is distinct from prior Treasury-curve, CFTC-positioning, yen, VIX-term-structure and auction mechanisms. Related literature supports testing financial-conditions information in volatility models but does not establish this specific ANFCI/S&P 500 result (Opschoor, van Dijk & van der Wel, 2014, DOI 10.1016/j.jempfin.2014.10.003).

### Source and timing evidence

- Chicago Fed: ANFCI is weekly, released 8:30 a.m. ET Wednesday (Thursday on specified holiday weeks), covering the previous Friday; it adjusts financial conditions for prevailing economic conditions: https://www.chicagofed.org/research/data/nfci/current-data.
- Official calendar: November 25, 2026 release for the week ending November 20, 2026: https://www.chicagofed.org/research/data/data-release-calendar.
- FRED identifies ANFCI as weekly ending Friday. Its page showed November 13 before the scheduled November 25 release; the workflow must verify actual CSV freshness. The preregistered ten-day gate fails closed if the new week has not reached FRED.
- Chicago Fed warns that historical ANFCI values are revised. Current-vintage data do not establish historical point-in-time values.

## Implementation admitted

Atomic admission commit a69ecbe8bd0d99e2d6a39831233a1ca591e405e4 includes the preregistration, event/backtest runner, deterministic tests, least-privilege Actions workflow, registry entry, this session report and README first-line restoration. Eleven ANFCI tests and all three admission-guard regression tests passed locally. The new workflow includes workflow_dispatch and the exact job-level admission condition; the guard test scans every research workflow dynamically.

The positive admission path was then exercised by the actual push. Research workflow [45714834063](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45714834063) and admission-guard workflow [45714833981](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45714833981) both completed successfully. The research workflow fetched all three FRED sources, passed deterministic tests, generated its report/manifest, updated the registry and committed evidence.

## Daily KPI

**MET before this additional study** by multiple distinct real-data walk-forward backtests completed on 2026-11-25. This ANFCI study is additional research, not quota-driven duplication.

## Execution result

- Data: ANFCI 522 weekly rows (2016-11-25 to 2026-11-20); SP500 2,512 daily rows and VIXCLS 2,546 daily rows (both through 2026-11-24). Source hashes and exact URLs are in the generated manifest.
- Event construction: 430 accepted non-overlapping weekly events from 522 observations; 115 validation forecasts and 210 test forecasts.
- Validation RMSE (log1p RV): baseline 0.32873609; augmented 0.34562528; change -5.1376%.
- Test RMSE (log1p RV): baseline 0.24834593; augmented 0.25211829; change -1.5190%.
- Test paired squared-loss bootstrap: mean baseline-minus-augmented loss -0.00188793; 95% CI [-0.00397162, -0.00001551]; 2.35% of bootstrap samples positive.
- Frozen decision: **REJECTED**. Adding the ANFCI four-week change worsened RMSE in both periods, and the paired-loss interval indicates the augmented model is worse.
- Research evidence commit: [b444ae0b7532174e1136ca5fafb38cf5965fb8c1](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/b444ae0b7532174e1136ca5fafb38cf5965fb8c1).
- Generated report: [ANFCI session report](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/blob/main/reports/sessions/2026-11-25/2026-11-25T223740Z_session-anfci-tightening-shock-45714834063.md); manifest: [manifest.json](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/blob/main/reports/generated/anfci-tightening-shock/45714834063-attempt-1/manifest.json).

## Verified / unverified

**VERIFIED:** repository/registry state; official ANFCI release semantics and calendar; local compilation; eleven ANFCI tests; three admission-guard tests; exact marker and atomic commit preparation.

**VERIFIED:** positive [QFR-ADMIT] branch executed; both Actions runs succeeded; FRED CSV freshness/coverage/hashes passed; report, manifest and REJECTED registry disposition were persisted to main.

**LIMITATIONS:** current-vintage ANFCI revisions are a material point-in-time limitation. The hypothesis is REJECTED under its frozen rule; no retuning or follow-up is permitted under this ID. No causal inference, executable strategy, trading P&L or live-trading action is authorized.

## Next

Verify the single intended ANFCI workflow runs from the marked commit, inspect its full result, confirm the freshness gate and source hashes, then verify the report, manifest and final registry disposition are committed to main. If source acceptance fails, preserve INCONCLUSIVE/INFEASIBLE; do not relax the preregistration.
