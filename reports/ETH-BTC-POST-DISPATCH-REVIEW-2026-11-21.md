# ETH/BTC post-dispatch artifact review

**Date:** 2026-11-21  
**Status:** Empirical study **INCONCLUSIVE** — both full-data attempts stopped at the first spot-series completeness gate  
**Scope:** Research/backtesting only. No live orders or capital deployment.

## Executive finding

The owner dispatched the full-data workflow twice on `main`, using the pre-registered range `2020-01-01` through `2026-10-31` and `market=both`. Both runs completed setup, dependency installation and the synthetic smoke test, then failed on the same real-data validation:

```text
Incomplete spot ETHUSDT data: missing archives=[], duplicates=0, missing hours=31
```

This is **not** an agent-network permission failure: the hosted runner downloaded all 82 requested monthly ETH spot archives and verified every published checksum. The failure is a genuine data-completeness gate. No empirical strategy metrics were produced.

## Workflow inventory and provenance

The complete Actions collection returned `total_count=20` and all 20 run records:

- 18 runs used `.github/workflows/research-tests.yml`.
- 2 runs used `.github/workflows/eth-btc-research.yml`.
- Both empirical runs were `workflow_dispatch` events on `main`, commit `fd93291e73693f6b1f9a534d2c1eb84804f7afeb`.
- Both used start `2020-01-01`, end `2026-10-31`, market `both`.

| Run | Workflow run ID | Result | Artifact |
|---|---:|---|---|
| 1 | [44943960222](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943960222) | Failed at spot ETHUSDT completeness check | [eth-btc-research-1](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943960222/artifacts/14722538907) |
| 2 | [44943965775](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943965775) | Same failure and same data manifest | [eth-btc-research-2](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943965775/artifacts/14722548808) |

Both jobs completed checkout, Python setup, archive-cache step, dependency installation and `--self-test`. The synthetic smoke test passed. The full empirical command failed in `download_klines` at the data-quality gate. Artifact upload then succeeded.

The second attempt did not add new evidence: both artifact manifests have the same SHA-256:
`2201e259c23678b11f05725bbfa051ff0789742cf3aad108aea42703315abe5a`.

## Artifact inspection

Both ZIP artifacts were downloaded and inspected.

| Item | Run 1 | Run 2 |
|---|---:|---:|
| Artifact ID | `14722538907` | `14722548808` |
| ZIP size | 4,711 bytes | 4,711 bytes |
| ZIP SHA-256 | `2c01d0c7800d89808a9e9113eb0824a2cf2613dc3c93d8be0268c3f9605e9b0d` | `06a03195503edbf4fdf5193f1c73e9738a80efa67698bdf31c72ebc881b7a4e3` |
| Expiry | 2026-12-21 | 2026-12-21 |

Each ZIP contains exactly one file: `data/raw/spot_ETHUSDT_archive_manifest.json`. The artifacts contain no raw market-data CSV, funding manifest, generated report or performance table. The raw-data exclusion is consistent with repository policy.

### Spot ETHUSDT archive manifest

- Requested sample: `2020-01-01 00:00 UTC` through `2026-10-31 23:00 UTC`.
- Monthly archives: 82 expected, 82 downloaded; no missing archive months.
- Published archive checksums: 82/82 verified.
- Timestamp units recorded by archive: milliseconds for older files and microseconds for newer files.
- Observed rows: 59,873; expected hourly bars: 59,904.
- Duplicate timestamps: 0.
- Missing hourly bars: **31** (approximately 0.052% of the expected sample).
- Observed first and last timestamps match the requested boundaries.
- Longest observed gap: **6 hours**.
- Manifest completeness flag: `false`.
- Consolidated CSV SHA-256 recorded by the runner: `10e9e037eef8c34ec2bd98964cc1b8be52cf5c741ca84e7f2925948fea1ac79b`.

The manifest stores only the first 20 missing-hour samples, not all 31 timestamps. Those samples begin in February 2020 and include a five-hour consecutive gap on 2020-02-19 UTC. The full consolidated CSV was not included in the artifact, so the remaining timestamps cannot be recovered from these artifacts alone.

## What was not tested

The pipeline stops at the first failed download/quality check: spot ETHUSDT. Consequently, these inputs were not validated in either run:

- spot BTCUSDT;
- USDⓈ-M ETHUSDT and BTCUSDT;
- ETH and BTC funding-event coverage and alignment;
- synchronized pair completeness;
- walk-forward folds, volatility regimes, fees/slippage/spread scenarios, benchmark accounting, turnover, drawdowns, bootstrap intervals and stress outputs.

No GO or NO-GO conclusion can be drawn. The empirical conclusion remains **INCONCLUSIVE**.

## Test CI and source revision

The latest test workflow run, [44943912907](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/44943912907) (run 18), passed on the current `main` commit. Its log records 17 deterministic tests passing and the synthetic plumbing smoke test passing.

A compare from the previously validated research-code commit `d7c3fc0b9ea75475a20b8d82c94aca6084073460` to current `main` `fd93291e73693f6b1f9a534d2c1eb84804f7afeb` shows documentation-only changes. No research source or workflow code changed after that validated code revision.

## Interpretation and next action

The data gate should **not** be weakened, and missing candles must not be forward-filled or synthesized without an explicit, pre-registered market-data policy. The next task is `tasks/ETH-BTC-DATA-GAP-RECONCILIATION.md`:

1. Preserve all 31 missing timestamps or compact gap intervals in the manifest.
2. Cross-check each missing ETH spot interval against Binance's official Spot klines API and any available independent archive representation.
3. Run a non-fail-fast data audit for all four market/symbol series so one early gap does not hide other data-quality problems.
4. Determine whether each gap is a source omission, an archive defect or a legitimate no-trade interval. Preserve source provenance and do not invent bars.
5. Add deterministic tests for gap reconciliation and completeness reporting.
6. Re-run the full empirical workflow only after the pre-registered data policy and all required series pass validation.

## Automation and activation status

The issue-comment dispatch bridge remains **NOT ENABLED / NOT END-TO-END VERIFIED**. The repository currently has no dedicated ordinary control issue, and the actual ChatGPT-connected comment identity and ordinary-issue commenting path have not been verified. Keep the manual `workflow_dispatch` fallback. Do not add broad `push` or recurring `schedule` triggers to bypass this requirement.

## Final status

- Artifact-review task: **COMPLETE**.
- Full-data empirical study: **INCONCLUSIVE / BLOCKED BY 31 MISSING SPOT ETHUSDT HOURLY BARS**.
- Live trading or capital deployment: **NOT AUTHORIZED**.
