# ETH/BTC trusted archive-cache warm-up verification — 2026-11-22

**Status: verified — cache save/restore confirmed.** The separate trusted cache warmer saved a six-archive snapshot on the default branch. A subsequent low-trust `issue_comment` audit restored that exact snapshot under read-only cache mode. All six archive hashes and all six manifest-file hashes were identical across the two runs.

This is an infrastructure result only. The research audit remained **INCOMPLETE** because funding settlement-event semantics are not accepted. No strategy or backtest ran.

## Implementation

- Merged PR [#4](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/pull/4) as commit [289be6e6f4a229b209cea41b3101756f5a1b88f5](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/289be6e6f4a229b209cea41b3101756f5a1b88f5).
- Workflow: [`.github/workflows/eth-btc-cache-warm.yml`](../.github/workflows/eth-btc-cache-warm.yml).
- Trusted triggers: weekly schedule and `workflow_dispatch`; a narrow `main`-only push path provided immediate first-run validation.
- The job checked out `main`, used no secrets, and ran only 2024-01-01 through 2024-01-31 with `--market both --audit-only`. It did not request Spot-gap reconciliation or execute a strategy.
- The queue guardian maps the warmer to its dedicated `binance-archive-cache-warm` concurrency group and runs after its completion.

## Trusted warm run

[Run 45058189936](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058189936) — event `push`, conclusion **success**.

- Started with no prior matching cache.
- All six archive manifests were present and each January 2024 archive had a verified SHA-256 checksum.
- Cache directory: 6 ZIP files, 163,915 bytes uncompressed.
- Cache service saved key: `binance-archives-warm-45058189936-1`.
- Elapsed workflow time: approximately 35 seconds (18:59:53–19:00:28 UTC).
- Audit exit code: 2, as expected for the fail-closed no-reconciliation research gate; `research_gate_complete=false`.
- Artifact [14768500986](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058189936/artifacts/14768500986), 8,130 bytes, contains exactly eight JSON files: six input manifests, `data_audit_summary.json`, and `cache_warm_diagnostics.json`.

## Subsequent low-trust restore

[Run 45058324331](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058324331) — event `issue_comment`, conclusion **failure** with expected audit exit code 2.

- Runner log explicitly reported `Cache mode: read`.
- The research job's run-unique primary key missed, then restored the warm snapshot through restore prefix `binance-archives-warm-`.
- Exact restored key: `binance-archives-warm-45058189936-1`.
- The cache restore completed successfully; the low-trust job's post-cache save step was skipped, preserving the read-only policy.
- Audit summary: `status=INCOMPLETE`, `input_manifest_count=6`, `all_six_manifests_present=true`, `price_series_complete=true`, `funding_series_complete=false`, `reconciliation_complete=true`.
- The funding histories remain provisional because the final payable-settlement population and event semantics are not established. Preflight and empirical strategy steps were skipped; no backtest metrics were produced.
- Artifact [14768023864](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058324331/artifacts/14768023864), 6,988 bytes, contains the six input manifests and audit summary only.

## Hash equality

The two artifact ZIPs were downloaded and inspected. Each corresponding input manifest had an identical file SHA-256, and each manifest's underlying archive SHA-256 was identical across the warm and low-trust audit runs.

| Input | Archive SHA-256 | Manifest-file SHA-256 |
|---|---|---|
| Spot ETHUSDT 1h | `1fdb3a8fa6b77ef30ef17ed4b71b184172ef1f812d83bd0f50bbd08e71a92057` | `a1296ff727f2cdaea9d7a51884611e60accc96eb9bfb48651a4c865f3dd1496c` |
| Spot BTCUSDT 1h | `cf873a185bd5b24b8e00034e49583fcb49928e0c3a45c6fc27a632a683655417` | `8538a7c5ead4d6a116df0f0a8c2317e906566d86436a3490a3dabc3e9b02185e` |
| USD-M ETHUSDT 1h | `2f3d1a6d9292f13b1d6cf86716cbda5b3f6119a310daed1dde5ee3d0d71e2fab` | `0c706f7cce5738630237d9f1c7e8e0349163722cfa2d36fe6eb62e45c043589f` |
| USD-M BTCUSDT 1h | `bf673f3d10804a951e8bac56dd2473486f113025971d43ebe5258ec40f9bfeb3` | `f6cebc8c82841634df9b3490b83b6e500b31e86ec3f86e2d64e69c79bb5f9e8a` |
| USD-M ETHUSDT funding | `5a71469b0b363886df904e784dddefc484dd943334b1fb7454713ce4ed715a4b` | `3293689020999fbb8b08a1a1cf545b3e52f5a9da7fce3776c4fff7e22e8eba51` |
| USD-M BTCUSDT funding | `3e0d30870672aa8f0f937881056e3cfd55913ae5c780cd50b33f2763aa0ba58e` | `324c1a9664edcd37e99a53af096299b45cf83a9223ce912b85b5a969bbec4443` |

**Result:** 6/6 archive hashes matched; 6/6 manifest-file hashes matched.

## Queue and CI verification

- Main CI [45058189909](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058189909) passed 153 deterministic tests and the synthetic plumbing smoke test.
- Queue guardian [45058258362](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45058258362) ran after the warm workflow completed, enumerated 293/293 runs completely, included the warmer in its inventory, and recorded `actions=[]` and `errors=[]`.

## Remaining limits

1. Only the first push-triggered cache save and one low-trust restore have been observed. The weekly scheduled trigger has not yet been observed, so long-term schedule reliability is unknown.
2. The initial cache is small (163,915 bytes on disk), but retention/eviction over repeated runs has not been measured through the available repository interface.
3. The restore and byte-identical manifests demonstrate that the existing downloader reused the cached archive files; the checksum sidecars are still checked remotely. Exact network-byte savings were not independently metered.
4. Do not expand to the full 2020–2026 range until repeated-run cache size, retention and runtime measurements justify it.
5. Funding semantics remain **PROVISIONAL_NOT_ACCEPTED**. This report must not be interpreted as empirical validation or permission to backtest the incomplete perpetual dataset.

## Reproducibility

- Cache workflow: [eth-btc-cache-warm.yml](../.github/workflows/eth-btc-cache-warm.yml)
- Research workflow: [eth-btc-research.yml](../.github/workflows/eth-btc-research.yml)
- Queue guardian: [queue-guardian.yml](../.github/workflows/queue-guardian.yml)
- Canonical queue: [ACTIVE-QUEUE.md](../tasks/ACTIVE-QUEUE.md)
