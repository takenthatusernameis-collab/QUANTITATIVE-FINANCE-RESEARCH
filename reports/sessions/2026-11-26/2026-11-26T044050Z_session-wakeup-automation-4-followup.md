# Wake-up research session — 2026-11-26 04:40:50 UTC

## Objective

Continue the README-governed research cycle. Inspect current repository state, avoid duplicate runs, choose a distinct falsifiable hypothesis, preregister it, implement deterministic tests and an immutable workflow, then preserve a complete handoff.

## Initial repository state

- Main HEAD before this session: 53593718e5fc9cdf198dab41e3f3c40e05883776.
- Latest research stream: KC Fed policy-skew versus DGS2, with VXN/VIX cross-index and SOFR/EFFR screens also recorded today.
- No active Actions runs at inspection.
- No open pull requests or standalone open issues. Eleven branches remain, including historical automation/dependency branches; none was adopted as a substitute for the current main workstream.
- Daily real-data backtest minimum was already met by distinct experiments earlier in this research cycle. This session adds a separate experiment and does not count synthetic tests as a real-data backtest.

## Candidate triage

- High-yield OAS was not selected: the FRED series page states that from April 2026 it exposes only three years of observations, insufficient for the planned long chronological evaluation without a separately licensed source.
- Moody's Baa-minus-Treasury proxy was not selected because its source terms carry redistribution restrictions; avoid embedding derived proprietary-series results in this public research repository.
- Selected a distinct energy-market mechanism: lagged WTI Cushing spot-price repricing as an incremental predictor of next-five-session S&P 500 realized volatility.

## Material data-semantic finding

FRED/EIA WTI includes a negative Cushing spot observation of -$36.98/barrel on 2020-04-20. A log-return feature would be mathematically invalid. The preregistration therefore uses asinh(WTI / 50) changes, with a fixed $50/barrel scale, preserving negative values. The deterministic tests explicitly cover this case. WTI is always taken from the latest valid observation strictly before the S&P 500 signal date; no same-date price, forward-fill or synthetic value is allowed.

## New hypothesis

- ID: QFR-2026-11-26-WTI-SHOCK-SP500-RV-01.
- Baseline: prior 5- and 20-session S&P 500 realized volatility plus same-date VIX.
- Augmented feature: five-observation WTI asinh change using six valid WTI observations.
- Target: next-five-session S&P 500 realized volatility.
- Origins: six S&P 500 sessions apart; 104 matured prior events for each rolling fit.
- Validation: 2019–2021. Test: 2022 onward.
- Decision: both periods must improve and the paired test squared-loss bootstrap 95% lower bound must be positive for PROMISING; otherwise retain INCONCLUSIVE unless the frozen rejection rule is met.

## Work prepared

- research/wti_shock_sp500_rv.py — source parser, coverage gates, strict-prior event construction, negative-price-safe feature, walk-forward OLS, metrics, paired block bootstrap, registry/preregistration persistence.
- research/test_wti_shock_sp500_rv.py — deterministic source, negative-price, no-forward-fill, no-lookahead, non-overlap, maturity, decision and synthetic end-to-end tests.
- research/PREREGISTERED-QFR-2026-11-26-WTI-SHOCK-SP500-RV-01.md — frozen hypothesis, source semantics, model, splits and decision rule.
- .github/workflows/wti-shock-sp500-rv.yml — admission-gated, immutable-checkout workflow with tests before live retrieval and evidence persistence.
- .github/workflows/workflow-admission-tests.yml — expanded compile and regression coverage.
- research/HYPOTHESIS-REGISTRY.md — new FEASIBILITY_CHECKED entry.
- This wake-up report.

## Validation before admission

- New WTI deterministic tests: 15 passed locally, including a synthetic end-to-end walk-forward.
- Workflow admission guard tests: 6 passed locally.
- Python compilation passed for the new module and tests.
- Both workflow YAML files parsed successfully.
- Local test harness used a minimal stub matching the existing repository helper interfaces; GitHub Actions will verify against the actual repository helper module.
- No live source fetch or empirical backtest is claimed before the admitted workflow completes.

## Verified / unverified

- VERIFIED: source pages and daily coverage are available; negative WTI history is real and retained; strict-prior timing, event spacing, target maturity, no-imputation rules and frozen decision logic are covered by deterministic tests.
- UNVERIFIED: complete current FRED CSV coverage, source freshness at execution, accepted event count, forecast metrics, bootstrap inference and the hypothesis disposition.
- Research remains forecast-only. No causal claim, trading P&L, live orders or capital deployment.

## Next action

Push the complete unit as one atomic [QFR-ADMIT] commit. Inspect both admission and research workflow runs. If live source checks fail, preserve an INCONCLUSIVE failure manifest and repair only the identified source/semantic defect; do not relax the preregistered gates or duplicate the run.
