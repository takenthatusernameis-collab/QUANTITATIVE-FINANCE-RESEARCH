# Ethereum validator queue — Git-history vintage and cross-source concordance audit

- **Candidate:** QFR-2026-11-28-ETH-VALIDATOR-QUEUE-ASYMMETRY-DOWNSIDE-01
- **Status:** COMPLETE_COMMIT_HISTORY_AUDIT
- **Run:** 46109045788, attempt 1
- **Retrieved:** 2026-11-28T04:50:11.159625+00:00
- **Model fit:** False
- **Backtest:** False
- **Raw observations saved:** False

## Git-history version audit and unverified timestamp proxy

- ValidatorQueue.com: 1243 daily first-read rows, 2023-05-21 through 2026-10-25.
- Missing calendar days: 11 across 5 gaps.
- Git history: 1237 commits; 1234 share the row's UTC date.
- Frozen schedule under Git committer-time proxy (not verified publication time): 37 validation and 107 test origins.
- Proxy 100/100 split minima: validation False; test True.
- Public first-publication time: UNVERIFIED; PIT-accepted validation/test origin counts are not established.

## Cross-source concordance

- Common dates before known-bug exclusion: 1243.
- Known Pectra bug dates excluded: 15.
- Clean paired dates: 1228 (2023-05-21 to 2026-10-25).

| Regime | n | Entry Pearson | Exit Pearson | Log-asymmetry Pearson | Log-asymmetry MAE |
|---|---:|---:|---:|---:|---:|
| Pre-Pectra | 714 | 0.9985 | 0.7132 | 0.9798 | 0.171672 |
| Post-Pectra | 514 | 0.9983 | 0.9839 | 0.9782 | 0.243024 |
| All clean | 1228 | 0.9985 | 0.9865 | 0.9791 | 0.201538 |

## Archive reconstruction assessment

- Public Nimbus .era files are large (roughly 0.48–0.94 GB in the sampled 2025–26 listing).
- Full-file reconstruction across roughly 1,923 eras is a terabyte-scale retrieval; no files were downloaded.
- Selective range reads may reduce the cost but remain unverified. A valid reconstruction still needs state-root anchoring, slot alignment and deterministic replay.

## Decision boundary

- This is source validation only; it is not a preregistration, model fit, backtest, strategy result or trading authorization.
- Git committer timestamps are mutable metadata, not server-side first-publication times; the proxy schedule cannot establish point-in-time availability.
- Even under the unverified timestamp proxy, the frozen validation split fails its 100-origin minimum if fewer than 100 origins remain.
- Any current-vintage exploratory association requires a separate hypothesis identity, preregistration and timebox before model fitting.

## Provenance

- CryptoKeyhole chart: https://cryptokeyhole.com/charts/eth/?metric=eth.ValidatorQueueWait
- ValidatorQueue repository: https://github.com/etheralpha/validatorqueue-com
- Nimbus archive index: https://mainnet.era.nimbus.team/
- Era format: https://github.com/eth-clients/e2store-format-specs/blob/main/formats/era.md
- Machine-readable manifest: reports/generated/eth-validator-queue-pit-concordance/46109045788-attempt-1/pit_concordance.json.
