# Active Repository Queue

**Canonical active-task pointer.** Updated 2026-11-22. All wake-up agents must read this file after the general mindset and hygiene preflight, then inspect linked run/incident state before creating new work.

## Current operating priority

**Higher-order meta-process optimization is the first engineering priority after hard safety/scientific invariants.** Keep the queue guardian, autonomous dispatch, artifact persistence and repository hygiene reliable. The objective is to remove recurring manual interventions and avoid repeated failures across future cycles, not to create documentation churn.

## Active task

### P0 — Complete adaptive ETH/BTC ingestion and no-trade validation

Canonical task: [ETH-BTC ingestion and no-trade validation](ETH-BTC-INGESTION-AND-NO-TRADE-VALIDATION.md).

Latest run: [44969155096](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44969155096), completed with data-audit failure (not a dispatch failure and not an empirical result). Artifact ID `14732529254`, ZIP SHA-256 `dbf237352b0067ff043d36b04c90a843a233b7430cbe80ceddef97814c5718a3`.

Current evidence:
- Both Spot series have 31 missing hours and zero duplicate timestamps.
- All 31 gap-specific official public-host kline requests returned HTTP 200 with zero rows, and daily kline archives also contained no candle. The gaps remain `both_kline_sources_empty_trade_status_unverified` until aggregate-trade evidence and known-active positive controls pass.
- Both USDⓈ-M kline parsers fail on the January 2022 monthly archive (`Invalid open_time values`).
- Both funding retrievals from `fapi.binance.com` returned HTTP 451; this route must not be repeated unchanged or bypassed.
- The audit artifact omitted separate failed manifests for the two USDⓈ-M price inputs and both funding inputs. Make failure manifests first-class outputs and test their upload.
- No empirical backtest ran. The original study remains **INCONCLUSIVE**.

Next executable steps, in order of information value:
1. Test trade-level positive controls and the 31 gaps for both Spot symbols using official `aggTrades` requests or checksum-verified daily archives. Check pagination, timestamps and schema. Only verified empty trade coverage may support a no-trade classification.
2. Fix the January 2022 USDⓈ-M parser from inspected raw schema and a deterministic fixture.
3. Replace blocked funding REST ingestion with a verified lawful archive route or authorized independent provider.
4. Persist all six success/failure manifests in the audit artifact, with provenance and hashes; no raw CSV upload.
5. In parallel, explore synchronized ETH/USD and BTC/USD series from an independent authorized provider as a separate experiment.
6. Launch historical empirical work only after that experiment's own data and methodology gates pass.

## Meta-process and automation work

- [Queue guardian](../.github/workflows/queue-guardian.yml): scheduled every five minutes. Verify a **scheduled** run performs live enforcement; the completed PR-comment dry-run only validates inspection/plumbing.
- [Queue guardian implementation](../research/queue_guardian.py) and [tests](../research/test_queue_guardian.py). Last verified CI run [44968997867](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44968997867) passed 37 deterministic tests and the synthetic smoke test.
- Preserve the 15-minute cancellation rule and earlier active same-concurrency-group predecessor exception. If cancellation fails, record the orphan and launch one independent alternative attempt; deduplicate issue/run lineage.
- Continue testing the artifact failure-manifest coverage gap and scheduled watchdog operation. Do not claim live cancellation is proven until a scheduled run shows the expected API action and durable incident evidence.

## Cleanup and handoff rules

- Keep this file as the one canonical active queue; update it in place.
- Mark completed/superseded task plans; preserve historical reports and data provenance.
- Keep logs, raw CSVs, plots, and large outputs in retained artifacts/storage, not Git. Keep compact manifests, hashes and decision summaries.
- At every cycle: brainstorm session plan → conservative hygiene cleanup → inspect queue incidents/active runs → remove the highest-leverage manual dependency → execute current tasks → verify, measure and hand off.
- Never create a duplicate run while an existing canonical attempt is active. Never treat a successful trigger or synthetic test as empirical evidence.
