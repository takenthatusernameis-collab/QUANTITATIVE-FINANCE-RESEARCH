# Wake-up session — quantitative finance research factory (2026-11-27T233943Z)

## Repository and operational state

- Default branch: `main`.
- Main before this session: `db2f0f1dd8dd608e245f519b6d0433d40f492907`.
- No queued or in-progress Actions runs were present at initial reconciliation.
- Draft control PR #15 remains open and must remain unmerged.
- Recent run #46078609758 passed the repository admission-guard suite.
- Treasury/ON RRP hypothesis `QFR-2026-11-27-TREASURY-RRP-DRAIN-BTC-DOWNSIDE-01` is closed INCONCLUSIVE/INFEASIBLE after its two-cycle cap; no third attempt is authorized under that ID.
- The 2026-11-27 UTC daily real-data backtest minimum was already met by distinct ETF-relative-flow, BTC blockspace-fee-rate and other completed screens. This wake-up does not count a source preflight as a backtest.

## Research discovery and literature boundary

A materially different, falsifiable funding-instability question was admitted: whether within-day dispersion across the three exact MEXC BTC_USDT eight-hour funding settlements adds information about next-24-hour same-contract realized variance after controlling for the mean funding level and recent realized variance.

The idea is not a parameter variation of the previous MEXC funding-level/downside study: the mechanism is intraday funding instability, the target is same-venue hourly realized variance, and the model explicitly controls for the funding mean. Existing literature already studies funding levels, funding memory and liquidation risk; no first-in-literature claim is made.

## New hypothesis and source-feasibility cycle

- Hypothesis: `QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01`.
- Difficulty: MEDIUM; four substantive cycles maximum.
- Timebox start: `2026-11-27T23:39:43Z`.
- Implementation deadline: `2026-12-01T23:39:43Z`.
- Final conclusion deadline: `2026-12-02T23:39:43Z`.
- Cycle 1 is limited to public MEXC contract metadata, complete funding-history pagination, segmented hourly-kline coverage, canonical hashes and event-window availability. No model fitting or empirical result inspection is allowed before this cycle passes.
- Preferred API host is the currently documented `api.mexc.com`; the previous `contract.mexc.com` host is only a preregistered compatibility diagnostic for route/DNS/connection failures, never a way around 401/403/429/451 restrictions.
- No Binance/Bybit fallback is permitted under this hypothesis. If MEXC source acceptance fails, close INCONCLUSIVE/INFEASIBLE and move to a separately preregistered idea.

## Changes committed

- Added the full preregistration and frozen source/model/decision rules.
- Added deterministic source parser, cadence, coverage and event-window tests.
- Added a source-preflight-only GitHub Actions workflow. It retrieves public MEXC data, stores hashes/coverage and does not fit a model.
- Added this session report and updated the registry/README handoff.
- Removed the stray non-documentary first line from README.

## Verification and limitations

- Repository admission CI and the new source-preflight workflow are triggered by the atomic research-admission commit; their outcomes are not assumed here.
- No MEXC source request or empirical backtest is claimed complete until the corresponding Actions run and persisted manifest are inspected.
- No raw market observations, credentials, private endpoints, live orders or capital deployment are used.

## Next action

Inspect the MEXC source-preflight Actions run. If every frozen gate passes, admit cycle 2 and implement the single frozen model. If any source gate fails, persist the exact diagnosis and close this hypothesis INCONCLUSIVE/INFEASIBLE without substituting a provider or changing the feature.
