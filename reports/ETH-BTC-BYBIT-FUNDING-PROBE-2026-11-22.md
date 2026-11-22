# Bybit Funding-History Availability Probe — 2026-11-22

## Purpose

Determine whether Bybit's public linear funding-history endpoint is reachable from the repository's hosted GitHub Actions runner for two bounded symbols and three date samples. This is an independent exchange pilot, not Binance evidence or a strategy backtest.

## Probe specification

- Symbols: BTCUSDT, ETHUSDT (linear perpetuals)
- Sample end times: 2020-01-01 UTC, 2022-01-01 UTC, and run-time UTC
- API limit: 200 rows per request
- Requests: 6 total, with up to 3 attempts per sample only for transient/network/429/5xx errors; HTTP 403 is permanent and not retried
- Raw response cache: ephemeral runner only
- Uploaded artifact: compact manifests only

## Result

**All six requests returned HTTP 403 Forbidden.**

No rows were received for either symbol at any sample date. The probe did not retry 403 and uploaded only per-symbol manifests. The run is marked failed/partial rather than success because no samples were accessible.

This means the Bybit public funding-history route is **blocked from the GitHub hosted runner**. It does not establish whether the endpoint is universally inaccessible, what the venue's full historical retention is, or whether another lawful non-blocked environment can access it. No proxy, geo/IP workaround, or captcha bypass was attempted. No data were accepted and no backtest was run.

## Evidence and reproducibility

- [Workflow run 45012785615](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45012785615)
- [Artifact 14750381483](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45012785615/artifacts/14750381483) — SHA-256 of ZIP: e490f7da2a20ae54908f4ee441e701aa515baf6553f6c3fd5651d2b2f1d3bfdd
- Probe implementation: [research/bybit_funding_probe.py](../research/bybit_funding_probe.py)
- Command allowlist and tests: [research/test_bybit_funding_probe.py](../research/test_bybit_funding_probe.py), [research/test_workflow_concurrency.py](../research/test_workflow_concurrency.py)
- CI [run 45012683817](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45012683817) — 134 deterministic tests passed; synthetic pipeline smoke test passed.

## Decision

Bybit is not accepted as a funding-data provider through this runner. Stop further identical probes; the access error is not a data-retention conclusion.

## Next bounded task

Investigate the [official OKX historical-data download page](https://www.okx.com/historical-data), which advertises funding-rate archives from March 2022. Confirm the dynamic download route, schema, exact instrument coverage and completeness before running any sample. Treat any OKX data as a separate venue study; it cannot replace Binance history. The Market History purchase/key remains owner-authorized only.
