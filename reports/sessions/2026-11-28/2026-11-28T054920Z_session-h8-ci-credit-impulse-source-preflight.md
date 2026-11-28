# Research session — H.8 C&I bank-credit impulse / BTC downside (2026-11-28T054920Z)

## Research output

A new, materially distinct hypothesis was frozen under `QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01`: whether point-in-time four-observation growth in U.S. commercial-and-industrial bank loans adds information about next-five-UTC-session BTC downside semivariance beyond BTC's own recent momentum, downside risk and realized variance.

This is a **source-feasibility cycle only**. No model module, BTC download, model fit, empirical backtest, strategy P&L or trading action was created.

The daily real-data backtest minimum for 2026-11-28 was already met by the separate MEXC funding-dispersion/BTC realized-variance experiment (run 46085887442). This source-only preflight is additional and does not count toward that minimum.

## Repository reconciliation

- Main HEAD at session start: `f3391d859c08dd58f76b6aee81933422a744b0ae`.
- The latest 30 Actions runs were all completed; the newest admission guard passed.
- The 2026-11-28 ETH validator-queue workstream is closed INCONCLUSIVE/INFEASIBLE because historical Git commit timestamps did not establish server-side publication times. No model was fitted.
- The 2026-11-27 BTC blockspace-fee-rate experiment is already INCONCLUSIVE on main. Its separate branch remains diverged (21 commits ahead / 152 behind main) and has no open PR; it was not merged or deleted.
- The BTC mining-difficulty proposal remains closed UNADMITTED; its recovery branch is behind main. The old ETF-relative-flow implementation branch is also behind main.
- Open PR #15 is a draft ChatGPT control-dispatch PR, not an empirical research task. No PR was merged or closed in this session.
- No disposable research evidence, manifests, historical reports or source archives were deleted.

## New source thesis

- Predictor: H.8 `TOTCI`, Commercial and Industrial Loans, All Commercial Banks; weekly ending Wednesday, billions of U.S. dollars, seasonally adjusted.
- Mechanism: bank-credit quantity / working-capital channel, not a credit-spread or central-bank-balance-sheet proxy.
- Historical availability: ALFRED as-of vintages. H.8 is normally released Friday at 4:15 p.m. Eastern Time (Thursday when Friday is a federal holiday). The BTC Sunday candle closes at Monday 00:00 UTC; the predictor is read from the preceding Sunday ALFRED vintage. A delayed H.8 release therefore leaves the older value in place rather than leaking the later observation.
- Predictor: 100 times the log ratio of the latest available TOTCI observation to the fourth prior weekly observation, both from the same vintage.
- Target: mean squared negative BTC log return over the next five UTC daily sessions.
- Event spacing: every Sunday, seven calendar days apart, leaving a two-day gap after each five-session target.
- Baseline: prior 5/20-session momentum, downside semivariance and 20-session total realized variance.
- Model, validation/test split, minimum samples, bootstrap and decision rules are frozen in the preregistration.

## Literature and novelty review

The repository has prior WALCL, STLFSI4 and BAA10Y experiments, but none uses H.8 `TOTCI` or point-in-time commercial-bank loan quantities. The adjacent crypto/credit-spread literature tests a different financial variable; BIS work on bank-credit transmission supports the general credit-channel mechanism but does not establish BTC predictability. A 2026 study of cryptocurrency uncertainty and bank intermediation examines the reverse direction. These sources motivate a falsifiable test, not a positive prior.

## Timebox

- Difficulty: MEDIUM.
- Start: 2026-11-28T05:49:20Z.
- Maximum substantive cycles: 4.
- Implementation deadline: 2026-12-01T05:49:20Z.
- Final research-conclusion deadline: 2026-12-03T05:49:20Z.
- Cycle 1: source-only ALFRED vintage preflight.
- Cycle 2: model implementation only if source acceptance passes.
- Cycle 3: one immutable empirical backtest after an atomic `[QFR-ADMIT] research:` commit.
- Cycle 4: independent reconstruction and final disposition.
- No deadline reset or alternate series/vendor under this identity.

## Files committed

- `research/PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md` — frozen hypothesis and timebox.
- `research/h8_ci_credit_impulse_source_preflight.py` — one-request, no-key ALFRED vintage parser and source gates.
- `research/test_h8_ci_credit_impulse_source_preflight.py` — deterministic parser, vintage, staleness, cadence, history and hash tests.
- `.github/workflows/h8-ci-credit-impulse-source-preflight.yml` — read-only source-only workflow; it does not run a model or backtest.
- `research/HYPOTHESIS-REGISTRY.md` — pending source-feasibility identity.
- `research/test_workflow_admission.py` and `.github/workflows/workflow-admission-tests.yml` — regression coverage.
- `README.md` — current active workstream and next-step handoff.

## Verification state at commit time

- Source parser and regression tests are included and will run on the GitHub Actions runner.
- The source-only workflow is triggered by the same atomic push and checks out `github.sha`.
- The ALFRED endpoint has not yet been accepted. The push-triggered workflow must prove no-key access, exact vintage columns, as-of dates, Wednesday observations, weekly cadence, 14-day maximum staleness and at least 450 observations in the frozen overlap.
- If the endpoint is inaccessible or any frozen source gate fails, close this identity as INCONCLUSIVE/INFEASIBLE. Do not use today's FRED values as a fallback.
- No raw source observations are committed; the source-only manifest is uploaded as a 30-day artifact.

## Canonical references

- H.8 release dates: https://www.federalreserve.gov/releases/h8/
- H.8 methodology: https://www.federalreserve.gov/releases/h8/about.htm
- FRED TOTCI: https://fred.stlouisfed.org/series/TOTCI
- ALFRED TOTCI: https://alfred.stlouisfed.org/series?seid=TOTCI
- ALFRED real-time periods: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
- BIS Working Paper 1157: https://www.bis.org/publ/work1157.pdf
- Crypto/credit-spread literature: https://onlinelibrary.wiley.com/doi/full/10.1111/eufm.70010
- Cryptocurrency uncertainty and bank intermediation: https://doi.org/10.1016/j.econlet.2026.113221
