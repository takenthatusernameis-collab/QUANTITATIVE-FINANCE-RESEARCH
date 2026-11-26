# Wake-up session report — automation turn 6 (2026-11-26T12:44:09.507Z)

## Repository reconciliation

- Repository: takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH
- Branch: main
- Main head after empirical evidence persistence: 47f3155f689b18538b5eb76aa7888485eff3d9a9
- README operating contract reviewed; the daily real-data backtest minimum was already met on 2026-11-26 by the earlier BAA10Y/BTC downside-semivariance experiment. This wake-up therefore performed additional research rather than creating a quota-only experiment.
- The repository has no tasks/ACTIVE-QUEUE.md; the hypothesis registry and timestamped reports remain the durable research state.

## Research action selected

Admitted and tested a distinct Bitcoin derivatives-positioning hypothesis:

- Hypothesis: QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01
- Mechanism: prior-only percentile of CME Bitcoin futures leveraged-fund gross shorts / total open interest as a proxy for short-side/cash-and-carry crowding.
- Difficulty: MEDIUM; four substantive cycles / five calendar days.
- Registered: 2026-11-26T12:23:01Z.
- Implementation deadline: 2026-11-29T12:23:01Z.
- Final conclusion deadline: 2026-12-01T12:23:01Z.
- Frozen data cutoff: CFTC report date 2026-11-17; Coinbase BTCUSD price observations through 2026-11-26.

The feature was not interpreted as uniformly bearish positioning. CFTC leveraged-fund classifications can include cash-and-carry, directional and other positions. The test was predictive, not causal.

## Data acquisition and quality

- CFTC TFF Futures Only, exact CME Bitcoin contract code 133741: 450 report rows, 2018-04-10 to 2026-11-17.
- Coinbase CBBTCUSD via FRED: 3,652 daily observations, 2016-11-25 to 2026-11-25.
- Known delayed-publication catch-up reports from 2025-09-30 through 2026-01-20 were excluded from feature history and events (17 rows).
- 375 accepted weekly events; 52 early reports lacked the frozen 52-report prior-only positioning history. Four BTC return windows were incomplete and skipped; no return interpolation or filling.
- CFTC response SHA-256: 0cb78b07cf2a380504432489a29f96ccc07f48043023c8897b5d67dff854dd20.
- FRED response SHA-256: d31b13b29bae8cd1bda89cf5d728772262db139ff1b83130ec6bfd4b95b3eb73.

## Implementation and validation

The admitted workflow required deterministic tests before source retrieval and persisted the exact run evidence. Several bounded implementation corrections were made without changing the registered feature, target, publication lag, model, thresholds or decision rule:

1. Corrected the workflow checkout-ref expression after the first runner attempt exposed an escaping defect.
2. Matched the CFTC API's canonical contract label (BITCOIN) while retaining exact contract-code validation.
3. Allowed historical holiday-shifted report dates, including 2018-12-24, while rejecting report-date intervals shorter than six days to fail closed on a twice-weekly cadence change.
4. Corrected the shutdown-backlog regression fixture so it tests exclusion of the 17 documented backlog reports from the prior percentile history.

Final GitHub Actions run: 45821991487 — success.
- 18 deterministic tests passed.
- Exact admitted commit: 464a6cf4f7361c3af25325ea3ea98366b5eafbf0.
- Evidence persistence commit: 47f3155f689b18538b5eb76aa7888485eff3d9a9.

## Empirical result

<badge>INCONCLUSIVE</badge>

| Metric | Validation 2019–2021 | Test 2022–2026-11-26 |
|---|---:|---:|
| Forecasts | 85 | 238 |
| Baseline RMSE | 0.966865 | 0.842701 |
| Augmented RMSE | 0.990140 | 0.852114 |
| RMSE improvement | -2.4072% | -1.1170% |

The augmented model worsened RMSE in both chronological periods. However, the paired test squared-loss 95% confidence interval was [-0.05335, 0.01964], crossing zero. The high-crowding event study found 46 high-crowding and 192 other test observations; mean next-five-observation downside semivariance was 2.2630 versus 3.3115 percentage-points squared, a difference of -1.0485 with 95% CI [-2.4307, 0.3485].

The frozen rejection criteria were not satisfied because both confidence intervals cross zero. The frozen promising criteria were also not satisfied. Therefore the correct disposition is INCONCLUSIVE, not REJECTED and not a promising screen.

## Durable artifacts

- [Experiment session report](2026-11-26T124128Z_session-cftc-bitcoin-carry-crowding-45821991487.md)
- [Generated manifest](../generated/cftc-bitcoin-carry-crowding/45821991487-attempt-1/manifest.json)
- [Preregistration and empirical disposition](../../research/PREREGISTERED-QFR-2026-11-26-CFTC-BTC-CARRY-CROWDING-DOWNSIDE-01.md)
- [Hypothesis registry](../../research/HYPOTHESIS-REGISTRY.md)
- [Successful GitHub Actions run](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45821991487)

## Decision and next action

- Close this hypothesis as INCONCLUSIVE under its frozen criteria. Do not retune or rerun the same ID to seek a favorable result.
- Keep the experiment in the registry as a forecast-only result; no strategy, live orders or capital deployment is authorized.
- On a future wake-up, choose a genuinely distinct information source or predictive mechanism rather than cosmetic variations of this positioning feature.
- No active-queue file was present to update. The registry and this session report are the durable state.
