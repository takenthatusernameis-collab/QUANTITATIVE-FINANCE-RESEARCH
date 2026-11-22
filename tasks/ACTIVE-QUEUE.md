# Active Repository Queue

**Updated:** 2026-11-22  
**Canonical active-task pointer:** [ETH/BTC ingestion and no-trade validation](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

## Governing priority

Apply the single authoritative [seven-level adaptive decision hierarchy](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md): P0 hard invariants; P1 compounding meta-process improvements; P2 resolve existing work/highest-value bottlenecks; P3 original research recovery; P4 independent providers/data architectures; P5 formally preregistered hypothesis/model replacement; P6 local polish. The [adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) implements the hierarchy. Do not create duplicate policy documents or task plans.

## Current cycle — 2026-11-22 Spot event-time production validation

- **Adaptive plan:** P0 preserve authorization, provenance, no-synthetic-data, causal timing and no-live-trading invariants; P1 completed: isolate unrelated comments from the research queue; P2 finish and inspect the already-running Spot-only empirical attempt; P3 preserve the original Binance hypothesis; P4 move to the MEXC pilot, then Bitget, if the Spot evidence path fails; continue USD-M funding semantics as an independent workstream.
- **Hygiene preflight:** inspected the 45-entry recursive tree, README and governing documents, current task/queue, five branches, open PRs, open issues, recent commits, workflow runs and artifacts. One open draft control PR (#2) and all five branches were preserved; open-issue search returned zero issues, including zero queue-guardian incidents. No tracked raw data, disposable caches, scratch files or generated clutter were found; no deletion was warranted.
- **Run inventory:** scheduled guardian [run 44999220911](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999220911) completed successfully with `event=schedule`; artifact [14744453706](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999220911/artifacts/14744453706), SHA-256 `051e864f6b15fe13b0c392048fec0a962682fdf26f88957830404a6218c6f840`, records 150/150 repository runs enumerated completely and no queue actions/errors. The later live guardian [run 44999259660](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660) enumerated 152/152 completely, identified 131 research/test runs (latest 50 retained), and recorded no actions/API errors; artifact [14744749673](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660/artifacts/14744749673) SHA-256 `649717e30b9a31c5c054d15b541eb338813d7a95fa082da801c5dbcedec83488`. No eligible cancellation was present, so the actual cancellation action remains unexercised.
- **P1 process improvements:** the ETH/BTC workflow isolates invalid/unrelated issue comments into per-comment concurrency groups while authorized commands retain the shared `eth-btc-research-main` queue; the exact comment allowlist is regression-tested against the shell authorization case statement. All workflow actions were upgraded to verified Node 24 releases: checkout v7.0.1, setup-python v7.1.0, cache v6.1.0 and upload-artifact v7.0.2 (commit [a56aa5b](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a56aa5b327ba35843588b4569a650390e63dd49f)); runtime version assertions are in `research/test_workflow_runtime.py`. CI [45000209665](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45000209665) passed 100 deterministic tests and the synthetic smoke test on [ada4b3d](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ada4b3d82234ada86068d37918cc88a237bc8162), with no Node 20 deprecation warning. First-attempt test runs [44999175158](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999175158) and [45000192696](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45000192696) exposed regex/test-parser defects; corrected revisions pass. End-to-end isolation run [44999259543](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259543) rejected the unrelated queue-guardian comment and skipped research jobs in seconds.
- **Current research execution:** Spot-only empirical run [44998434437](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998434437) started at 2026-11-22 07:29:10 UTC on commit `66b3594`; exact actor/PR/command authorization passed, default-branch checkout, dependency installation and synthetic smoke passed. The Spot-only data preflight remains **IN_PROGRESS**; the strategy step has not started. A second run [44998792132](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44998792132), created by the first queue-guardian comment before the isolation fix, remains pending behind #44998434437. Preserve it as a same-group dependent run; do not cancel or duplicate it.
- **Evidence boundary:** the full-history audit has all 31 synchronized Spot gaps per symbol classified as confirmed no-trade using checksum-verified daily aggregate-trade archives and positive controls; no candles were inserted. USD-M prices are complete at 59,904/59,904 each. Funding histories remain provisional, so the combined/perpetual gate remains closed. Spot-only research does not require funding.
- **Next action:** inspect #44998434437 after it terminates, including the full job logs, all manifests and uploaded artifact. If the Spot preflight passes, review fold-level OOS results, cost/regime sensitivity and the default `spot_borrow_bps_per_day=0` assumption (not net of borrow); derive pooled OOS metrics from `oos_returns.csv` and do not claim bootstrap confidence intervals until a time-aware event-time bootstrap is implemented. If it fails, preserve the exact gate blocker and begin the bounded MEXC pilot rather than repeating the same Binance probe. Continue funding settlement research independently.

## Completed implementation in this session

- Canonical hierarchy added to [General Antifragile Autonomous Operating Mindset](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md), the governing policy.
- [Adaptive execution standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md) now defines provider, data-architecture, timeframe, model, funding and escalation rules. [README](../README.md) now points wake-up agents to the same hierarchy.
- Added executable policy engine [research/adaptive_decision.py](../research/adaptive_decision.py): provider scoring and evidence acceptance; repeated-failure escalation; independent-workstream continuation; distinct experiment identity; spot/perpetual separation; separately preregistered hypothesis replacement; duplicate active-dispatch protection; and the six-input fail-closed gate.
- Added deterministic regression suite [research/test_adaptive_decision.py](../research/test_adaptive_decision.py).
- Integrated the shared six-input gate into [research/run_eth_btc.py](../research/run_eth_btc.py). Unknown, missing or rejected input states and missing manifests fail closed.
- Added independent `spot`, `perpetual`/`um`, and `both` scope gates. Confirmed Spot no-trade gaps require both complete reconciliation and an accepted elapsed-time policy; the Spot scope gate now requires the production event-time policy and provenance evidence to pass; live acceptance is being checked by run #44998434437. Perpetual-only research requires UM prices and final funding acceptance but not Spot coverage.
- Integrated the production Spot event-time walk-forward, event-time benchmarks and continuous-time metrics; the live Spot-only preflight is run #44998434437. Exact archive-object URL/checksum matching is enforced in commit [66b3594](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/66b3594d5979129117c2fc5ed8062f5a9839ccd3).
- Hardened research workflow concurrency so invalid/unrelated PR comments are isolated by comment ID while accepted commands remain serialized. Regression test and CI verification are recorded in the current cycle above.
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
  - Full-history provider gate regression: [ff4ac3c](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ff4ac3c06ed94cf29766679798e4afedf6e5869a)
  - Canonical P6 test-label correction: [a82192b](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/a82192be07c64b10b0966dabc5741f62635a1075)

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

1. **Spot-only empirical run #44998434437:** the production event-time path is integrated and the authorized run is already in progress. Its data-preflight step is the only active research step; inspect its logs, manifests and artifact after completion. If accepted, review OOS metrics with the explicit zero-borrow assumption. If rejected, preserve the exact gate blocker and start the bounded MEXC pilot.
2. **MEXC first independent-provider pilot:** if the Spot preflight fails, test synchronized ETH/USDT and BTC/USDT hourly positive/negative controls; verify pair identity/inception, UTC timestamps, OHLCV, duplicates, pagination, checksums, common timestamps, quote semantics and full-history feasibility. Keep a separate MEXC experiment; do not assume USDT equals USD.
3. **Bitget second independent-provider pilot:** apply the same independent acceptance protocol and separate provenance/experiment identity for ETH/USDT and BTC/USDT (and suitable USD pairs if available).
4. **Funding stream:** continue independent final-settlement research. Establish event semantics, complete payable-event population, historical interval schedule and contract incarnation/retention from authoritative settlement sources. Keep Spot research separate from perpetual claims.
5. **Provider/architecture escalation:** after the second distinct provider fails, move to a materially different data construction rather than repeating provider variants. Record the exact failure and experiment identity.
6. **Backtest gate:** run a market-specific empirical experiment only after its own provenance, coverage, no-trade/missing-data, funding (when applicable), cost and methodology acceptance gates pass. The shared six-input gate protects the original Binance perpetual study.

## Verification status

- Latest verification: [CI run 45000209665](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45000209665) passed **100 deterministic tests** and the synthetic plumbing smoke test on [ada4b3d](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/ada4b3d82234ada86068d37918cc88a237bc8162); the upgraded Node 24 actions produced no deprecation warning. Prior concurrency verification [44999194755](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999194755) passed 98 tests, and policy verification [44989792456](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989792456) passed 82 tests. The suite covers the seven-priority order, provider ranking/acceptance/full-history feasibility, repeated-failure escalation, independent workstreams, immutable experiment identity across provider/construction/timeframe/source changes, Spot/perpetual separation and scoped gates, hypothesis replacement, duplicate-active-dispatch prevention, and fail-closed six-input acceptance.
- Earlier successful snapshots [44989316015](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989316015) and [44989496967](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44989496967) passed 79 tests each. Intermediate failures #81–#86, #89 and #91 exposed implementation/test-fixture/assertion defects; each was corrected in a later commit, and the final run #92 validates the resulting state. Synthetic smoke tests are engineering evidence only—not provider acceptance or empirical strategy validation.
- Previous research CI [44985194153](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44985194153) passed 61 prior deterministic tests plus the synthetic smoke test. It predates the new policy module.
- Latest queue guardian live run [44999259660](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44999259660) succeeded and enumerated 152 repository runs completely with no queue actions/errors; the scheduled trigger remains unverified.
- No live trading, capital deployment or strategy promotion occurred.

## Non-negotiable boundaries

No live orders, capital deployment, live credentials, custody changes or automatic strategy promotion. Respect provider restrictions. Preserve raw market data outside Git and retain compact manifests, hashes and decision summaries.

**Research conclusion:** the original Binance ETH/BTC perpetual study remains **INCONCLUSIVE**. The Spot gap classifications and USD-M price histories are improved, but final funding acceptance remains unresolved and no empirical strategy-performance metrics have been produced.
