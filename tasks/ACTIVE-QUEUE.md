# Active Repository Queue

**Updated:** 2026-11-22  
**Canonical active-task pointer:** [ETH/BTC ingestion and no-trade validation](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

## Governing priority

Apply the single authoritative [seven-level adaptive decision hierarchy](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md): P0 hard invariants; P1 compounding meta-process improvements; P2 resolve existing work/highest-value bottlenecks; P3 original research recovery; P4 independent providers/data architectures; P5 formally preregistered hypothesis/model replacement; P6 local polish. The [adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) implements the hierarchy. Do not create duplicate policy documents or task plans.

## Session plan and repository hygiene

- Inspected the README, governing mindset, execution standard, hygiene policy, active queue, recent commits, open PRs, branches, open issues, workflow inventory, active runs and audit artifacts before editing.
- One open PR remains: draft control PR #2. Five existing branches were preserved. No open queue-guardian incidents were returned. The latest complete workflow inventory contained 117 runs.
- No disposable tracked cache, raw market data, generated report or scratch files required deletion. All existing evidence, reports, branches, PRs and active workflow outputs were preserved.
- No overlapping audit was dispatched. Existing full audit #23 was resolved and its artifact inspected before implementing the new decision policy.

## Completed implementation in this session

- Canonical hierarchy added to [General Antifragile Autonomous Operating Mindset](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md), the governing policy.
- [Adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) now defines provider, data-architecture, timeframe, model, funding and escalation rules. [README](../README.md) now points wake-up agents to the same hierarchy.
- Added executable policy engine [research/adaptive_decision.py](../research/adaptive_decision.py): provider scoring and evidence acceptance; repeated-failure escalation; independent-workstream continuation; distinct experiment identity; spot/perpetual separation; separately preregistered hypothesis replacement; duplicate active-dispatch protection; and the six-input fail-closed gate.
- Added deterministic regression suite [research/test_adaptive_decision.py](../research/test_adaptive_decision.py).
- Integrated the shared six-input gate into [research/run_eth_btc.py](../research/run_eth_btc.py). Unknown, missing or rejected input states and missing manifests fail closed.
- Added independent `spot`, `perpetual`/`um`, and `both` scope gates. Confirmed Spot no-trade gaps require both complete reconciliation and an accepted elapsed-time policy; the current Spot time-policy flag remains false. Perpetual-only research requires UM prices and final funding acceptance but not Spot coverage.
- Added exact allowlisted commands on control PR #2: `/qfr-run-eth-btc-spot-empirical`, `/qfr-run-eth-btc-um-empirical`, and the original combined `/qfr-run-eth-btc-empirical`. The preflight uses the selected market scope; the audit still records all six inputs.
- Provider acceptance now also requires verified full-history acquisition feasibility. Experiment identities include timeframe and source version; regression tests lock the seven-level hierarchy and provider-order tie-breaks.
- Commits:
  - Governing mindset: [378609c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/378609c7d3bf76ce7ce6bb9ec9997b6538e7054f)
  - Execution standard: [0d4378f](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/0d4378f189c043caf885257b7a53de5d29264767)
  - README: [386ff38](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/386ff38f430cf47c43eab1f2557d1a87c0ca29f6)
  - Decision engine: [a811c49](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a811c49223565dc5d3d24c60b408690d0ee0988b)
  - Decision regression tests: [5576fc0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/5576fc048fffaf0c4080788750f52b4f55f1fc2c)
  - Shared empirical gate integration: [8625d40](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8625d40b8684ee975d7664ca8b01a17247dd659e)
  - Independent scope gates: [37fe290](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/37fe290682c5047743d584aa7df7808e90fe84cd)
  - Scoped research-pipeline integration: [6ab1adb](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/6ab1adba7d61c9de608bc8bbc7a541beac227bd4)
  - Scoped workflow commands: [f728398](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/f72839867ed1aacf0d5a0f33e7859d9c6abb48b0)
  - Scope-policy fix: [b13ab5c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/b13ab5c66e8f64c8e674145c1c27b4a1811f159b)
  - Full-history feasibility gate: [0e2bfa0](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/0e2bfa07aa6903107dc0794e0401fb108bae0021)
  - Final policy/test strengthening: [1d700ce](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/1d700ceec9d56acb697493815eab507aecbf092d)

## Latest full-history audit — resolved

Run [44986170330](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986170330) completed at 2026-11-22 05:16:08 UTC with expected data-quality conclusion **INCOMPLETE**. Authorization, default-branch checkout, dependency installation, synthetic plumbing test and artifact upload passed. The empirical preflight/backtest steps were skipped.

Artifact [14740847028](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986170330/artifacts/14740847028): 71,320 bytes; ZIP SHA-256 `a69e7247f2aaf09f049461a80b823084d8fe3384036494548f000815dada7204`. Nine files contain the summary, all six input manifests and both Spot gap-reconciliation manifests; no raw market-data CSV was uploaded.

| Input | Observed | Result |
|---|---:|---|
| Spot ETHUSDT | 59,873 / 59,904 hourly bars | 31 missing candles |
| Spot BTCUSDT | 59,873 / 59,904 hourly bars | Same 31 missing hours |
| USD-M ETHUSDT | 59,904 / 59,904 | Complete |
| USD-M BTCUSDT | 59,904 / 59,904 | Complete |
| ETHUSDT funding | 7,488 events | Coverage/cadence pass; settlement semantics provisional |
| BTCUSDT funding | 7,488 events | Coverage/cadence pass; settlement semantics provisional |

**Important Spot finding:** all 31 gaps for each symbol were classified `confirmed_no_trade_interval` (31/31) using checksum-verified daily aggregate-trade archives and successful known-active archive positive controls. Both per-symbol reconciliation manifests report `reconciliation_complete=true`; no unresolved gaps remain in those inventories. This is trade-level evidence of no trades, not a repaired hourly candle series. Do not synthesize OHLCV or assign a one-hour return to a multi-hour elapsed interval. Implement and validate an explicit event-time/irregular-time treatment before using these Spot observations.

**Perpetual price finding:** both USD-M hourly histories now parse and pass the full 59,904-row coverage, duplicate and timestamp checks. The prior January 2022 parser failure is resolved in this run.

**Funding finding:** both Binance Vision archives contain 7,488 rows, zero duplicates, requested boundary coverage and approximately eight-hour observed cadence. Their manifests remain `PROVISIONAL_NOT_ACCEPTED` because complete final-settlement population, event semantics and contract-incarnation coverage are not established. Tardis corroborates sampled next-event timestamps but its pre-event rates are not final settled rates. Do not substitute them.

Summary: all six manifests are present; both perps pass; both spot candle grids remain incomplete despite all missing intervals now being classified as no-trade; both funding datasets remain unaccepted. The empirical result remains **INCONCLUSIVE** and no strategy metrics were produced.

## Independent research-scope gates

- The executable decision engine now separates `spot`, `perpetual`/`um`, and `both` research scopes. Spot-only research does not depend on funding manifests; perpetual-only research does not depend on Spot completeness; combined research still requires all six inputs.
- Confirmed Spot no-trade intervals do not create hourly candles. Spot research with missing hourly observations additionally requires an accepted event-time/elapsed-time PnL, signal, execution and annualization policy. The current empirical pipeline intentionally leaves `spot_time_policy_accepted=false`, so Spot backtests with these gaps remain blocked.
- Perpetual research remains blocked until the final settled funding population and historical contract semantics are independently accepted.
- Control PR #2 commands: `/qfr-run-eth-btc-spot-empirical`, `/qfr-run-eth-btc-um-empirical`, and the existing combined `/qfr-run-eth-btc-empirical`. Each preflight is scoped to the requested market; the all-six audit still records every independent input.

## Current blockers and next executable actions

1. **Spot-only event-time path:** design and test a separate event-time/irregular-time return and position-accounting path that preserves elapsed duration and no-trade intervals, including holding periods, execution opportunities, annualization and transaction costs. Keep the original strict hourly experiment gated until its pre-registered data semantics are met.
2. **Independent spot provider pilot:** test Coinbase Exchange ETH-USD and BTC-USD 1-hour candles on one known-active 24-hour window, one candidate missing/no-trade interval and one representative month. Validate product history, response completeness, OHLCV, timestamps, controls, hashes, common timestamps and ratio construction. Maintain a separately identified Coinbase experiment.
3. **Next provider:** test Kraken full-history ETH/USD and BTC/USD OHLCVT with a bounded pair/window pilot if Coinbase fails its acceptance gates. Then screen other authorized providers; compare independent sources only on common coverage.
4. **Funding stream:** continue independent final-settlement research. Establish event semantics, complete payable-event population, historical interval schedule and contract incarnation/retention from authoritative settlement sources. Keep Spot research separate from perpetual claims.
5. **Provider/architecture escalation:** after the second distinct provider fails, move to a materially different data construction rather than repeating provider variants. Record the exact failure and experiment identity.
6. **Backtest gate:** run a market-specific empirical experiment only after its own provenance, coverage, no-trade/missing-data, funding (when applicable), cost and methodology acceptance gates pass. The shared six-input gate protects the original Binance perpetual study.

## Verification status

- Corrected final scope-policy CI run [44989316015](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989316015) passed 79 deterministic tests and the synthetic plumbing smoke test. Experiment identity regression run [44989496967](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989496967) also passed 79 tests plus the smoke test.
- Full-history feasibility and priority-ordering additions are being verified in serialized runs [44989539027](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989539027) and [44989591317](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989591317). Earlier failures #81–#86 were intermediate-commit defects (literal newline escape, missing test import, unreconciled Spot acceptance logic, and a fixture not yet updated for the newly required full-history gate); each was corrected and the later 79-test runs passed. Do not treat a failed intermediate SHA as the final code state.
- Previous research CI [44985194153](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44985194153) passed 61 prior deterministic tests plus the synthetic smoke test. It predates the new policy module.
- Queue guardian live PR-comment run [44986166616](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44986166616) succeeded and enumerated 117 runs with no queue actions/errors; the scheduled trigger remains unverified.
- No live trading, capital deployment or strategy promotion occurred.

## Non-negotiable boundaries

No live orders, capital deployment, live credentials, custody changes or automatic strategy promotion. Respect provider restrictions. Preserve raw market data outside Git and retain compact manifests, hashes and decision summaries.

**Research conclusion:** the original Binance ETH/BTC perpetual study remains **INCONCLUSIVE**. The Spot gap classifications and USD-M price histories are improved, but final funding acceptance remains unresolved and no empirical strategy-performance metrics have been produced.
