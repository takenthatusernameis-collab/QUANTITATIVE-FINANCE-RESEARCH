# ETH/BTC Funding Schedule Spot Samples and Queue Reliability Update — 2026-11-22

## Decision

**Funding remains PROVISIONAL_NOT_ACCEPTED. No perpetual backtest is authorized.** The three additional Tardis first-of-month samples improve independent event-timestamp corroboration around Binance's documented funding-interval changes, but they are narrow one-day observations. All three sampled days show the default 8-hour timestamps for BTCUSDT and ETHUSDT; this does not establish that conditional 1-hour or 4-hour events never occurred outside those days, nor that the archive contains the complete payable-settlement population.

## Scope and method

For each date (2025-06-01, 2025-10-01, 2026-02-01), the research workflow downloaded public Binance Futures `derivative_ticker` CSV.gz files from Tardis.dev for BTCUSDT and ETHUSDT, parsed exchange/local timestamps, funding timestamp and pre-event funding-rate estimate, and compared the next-event timestamps with the official Binance Vision monthly `fundingRate` archive. Archive ZIP checksums were verified. Raw Tardis files were retained only in the runner cache; the uploaded artifacts contain manifests and summaries.

Tardis documents `funding_timestamp` as the next event time and `funding_rate` as the rate for that next event, which can change before the event; its last pre-event value can differ from the final rate applied. These probes therefore test schedule/time alignment—not final settlement rates or population completeness. See [Tardis data types](https://docs.tardis.dev/downloadable-csv-files/data-types) and [Binance Futures historical data details](https://docs.tardis.dev/historical-data-details/binance-futures).

## Results

### Event-time and archive cadence

| Sample date (UTC) | BTC archive rows | ETH archive rows | Archive intervals | Tardis-to-archive matches (BTC / ETH) | Maximum offset (BTC / ETH) |
|---|---:|---:|---|---|
| 2025-06-01 | 90 | 90 | 8h only | 4/4 / 4/4 | 2 ms / 1 ms |
| 2025-10-01 | 93 | 93 | 8h only | 4/4 / 4/4 | 0 ms / 0 ms |
| 2026-02-01 | 84 | 84 | 8h only | 4/4 / 4/4 | 4 ms / 4 ms |

Every sample's Tardis dataset was `SAMPLE_VALID`; every monthly archive was parsed, checksum-verified, and had zero duplicate funding timestamps. All observed Tardis next-event timestamps matched the archive `calc_time` values within the 15-second acceptance tolerance. Maximum local timestamp gaps in the sampled Tardis days were approximately 4.0–5.0 seconds; the CSV does not include disconnect markers, so this is not a packet-loss certification.

### Pre-event estimate versus archive rate

| Date | BTC exact matches | BTC mean absolute difference | ETH exact matches | ETH mean absolute difference |
|---|---:|---:|---:|---:|
| 2025-06-01 | 1/3 | 1.70e-7 | 1/3 | 3.17e-7 |
| 2025-10-01 | 1/3 | 1.83e-7 | 1/3 | 2.77e-7 |
| 2026-02-01 | 0/3 | 4.67e-7 | 0/3 | 8.60e-7 |

Rate differences are diagnostic only; they are not evidence of archive errors because the Tardis values are pre-event estimates rather than final settled rates.

## Reproducible runs and artifacts

| Sample | Research run | Artifact | Artifact SHA-256 |
|---|---|---|---|
| 2025-06-01 | [45008489597](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008489597) | [14749075739](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008489597/artifacts/14749075739) | `5027b97f7f144ebde888489bd0fc2cb30e397a02c0c8df46b688fd8084e77609` |
| 2025-10-01 | [45008491165](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008491165) | [14748732441](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008491165/artifacts/14748732441) | `6bb663afb830f89dae2e5c49929db44f8e12c6d443f9cde76d1ab1017ce1bb88` |
| 2026-02-01 | [45008493356](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008493356) | [14748722540](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008493356/artifacts/14748722540) | `62cea8b45fd7c23992bc253db46a06a970406961dfda67c9365fbea7c8aad05c` |

Artifacts expire after 30 days. The sample manifests explicitly record `settled_funding_rate_available=false` and `settlement_population_complete=false`.

## Queue-guardian reliability improvement

The five-minute scheduled trigger was empirically sparse: only **1 scheduled guardian run appeared among the latest 100 Actions runs** (the remaining guardian runs in that sample were issue-comment-triggered). To reduce dependence on the unreliable cron, `.github/workflows/queue-guardian.yml` now also triggers after completion of the specific ETH/BTC research workflow, with a fail-closed gate requiring workflow ID `425839329`, `issue_comment` origin, default branch, same repository and verified owner actor. Accepted workflow-run events execute live enforcement; they do not silently become dry runs.

End-to-end verification:

- Harmless dispatch smoke [45008338267](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008338267) completed successfully.
- Guardian [45008356294](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008356294) triggered from `workflow_run` and artifact [14748412102](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008356294/artifacts/14748412102) verified `LIVE_ENFORCEMENT`, 182/182 runs enumerated completely, no actions/errors.
- Guardians after the three samples ([45008517849](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008517849), [45008547335](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008547335), [45008562887](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008562887)) also succeeded in live mode, enumerating 190, 191 and 192 runs respectively, with no queue actions/errors.
- CI [45008182369](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008182369) passed 108 tests and synthetic smoke after the guardian change; [45008363615](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008363615) passed 109 tests after probe commands were added; [45008382261](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45008382261) passed 109 tests and synthetic smoke after date-mapping regression tests were added. The first workflow revision's stale assertion failure was corrected; the subsequent runs passed.

## Remaining blockers

1. Direct Binance funding REST requests are still unavailable from the prior hosted-runner route (HTTP 451); the web reader cannot retrieve the API endpoint. No evasion/proxy was attempted.
2. [Binance Public Data issue #517](https://github.com/binance/binance-public-data/issues/517) remains open without an official response; the last follow-up was 2026-11-19. It requests historical settlement retention/completeness and effective schedule semantics for a broad USD-M population.
3. Related [issue #495](https://github.com/binance/binance-public-data/issues/495) documents the LITUSDT ticker-incarnation problem: old Litentry funding archives have 417 post-delisting rows while REST queries for the old contract returned empty, and the ticker was reused for Lighter. This is a concrete identity/retention warning, not evidence that ETH/BTC archives are defective.

## Next action

Continue investigating authoritative historical schedule/settlement semantics and a lawful, independent full-history source. Preserve the funding rejection gate and original experiment **INCONCLUSIVE** status; do not run a perpetual backtest until the complete event population is accepted.
