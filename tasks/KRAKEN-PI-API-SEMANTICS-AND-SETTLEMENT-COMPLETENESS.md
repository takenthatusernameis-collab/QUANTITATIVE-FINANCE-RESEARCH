# Resolve Kraken PI cap exceptions, API timestamp semantics, and settlement-population completeness

**Status:** PENDING — 2026-11-23 05:10 UTC  
**Priority:** P1 data-integrity / research-acceptance blocker  
**Research gate:** all four Kraken funding series remain PROVISIONAL_NOT_ACCEPTED; no backtest or cross-venue merge.

## Objective

Resolve the remaining reasons the Kraken PF/PI funding histories cannot be accepted: effective-dated PI funding-cap terms for the nine exceptions, the public API timestamp-to-accrual mapping, and completeness of the payable funding-event population. Reconcile the exact PI delisting settlement reference where possible.

This is a data-validity task, not permission to accept unexplained rows, alter rates, run a strategy backtest, use credentials, purchase data, or merge venue histories.

## Evidence to reuse — do not repeat

- Completed PI exception plausibility/terms diagnostic: [report](../reports/ETH-BTC-KRAKEN-PI-PRICE-VALIDATION-2026-11-23.md), [run 45116028859](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859), manifest artifact [14791133228](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45116028859/artifacts/14791133228).
- Code/test correction: [8420754](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/8420754d5edb927b420c6ea5f4fd19ca0dbf4700). CI [45115907842](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45115907842) passed 209 deterministic tests and synthetic smoke.
- Nine exceptions: one PI_XBTUSD row and eight PI_ETHUSD rows, dated 2026-08-20, 2026-10-29 and 2026-10-30. All nine are arithmetically consistent under the inverse formula and all nine implied levels fall inside bounded three-hour Coinbase spot envelopes. This is plausibility only; every exception remains above the published ±0.25% hourly cap.
- Current inverse specification, dated 29 September 2026, states ±0.25% per hour, n=24, and next-period rate calculation over the preceding/current one-hour window. No PI-specific cap change appears in the public parameters changelog, whose latest dated entry is 4 September 2025. A PF_OGNUSD-specific override proves overrides can exist but does not imply PI inherited one.
- Official PI delisting evidence: inverse specification says settlement at 16:00 UTC against CME CF reference rates; the delisting page lists PI_ETHUSD at $2,235.76 for 15:00–16:00 London and describes a time-segmented volume-weighted TWAP. CME CF's ETHUSD_RR methodology uses a one-hour 15:00–16:00 London window and twelve five-minute partitions. The high-level descriptions are compatible, but the exact historical reference-rate value and Kraken deviation safeguards have not been independently reconstructed.
- API/archive coverage: PI archive has 38,225 rows per symbol from 2018-08-31 16:00 through 2026-02-01 00:00 UTC; API has 8,283 rows per symbol from 2025-11-19 09:00 through 2026-10-30 16:00 UTC. The shared range contains 1,767 exact timestamp/rate matches per symbol. The API and archive each have residual intervals; five two-hour gaps are common across all four instruments. Exact evidence is in [the API-tail quality report](../reports/ETH-BTC-KRAKEN-API-TAIL-QUALITY-2026-11-23.md).
- The official API reference documents ascending timestamp order and a required symbol but no cursor, since/limit, retention, refresh, or timestamp-to-accrual semantics.

## Adaptive execution plan

1. **Effective-dated PI cap terms.** Search authoritative Kraken contract pages, dated parameter changes, archived snapshots, and instrument-specific configuration records for the cap applicable to PI_XBTUSD and PI_ETHUSD on 2026-08-20, 2026-10-29 and 2026-10-30. Distinguish UI symbol PI_BTCUSD from API symbol PI_XBTUSD. Do not infer a cap from observed rates, a different instrument's override, or a current page alone. If no public historical source exists, state the exact owner/external confirmation required and leave the nine rows unaccepted.
2. **API timestamp mapping.** Find an authoritative definition of the historical-funding API timestamp or a reproducible public example that identifies whether timestamp T denotes the accrual-period start, period end, rate-setting boundary, or another event. Reconcile it with the contract's documented rule that the next period's rate is calculated over the current one-hour period. Do not choose the mapping that makes the October 30 final row look convenient. If the API schema remains silent, keep the mapping unresolved.
3. **Delisting reference reconciliation.** Seek the exact 2026-10-30 CME CF ETHUSD_RR value from an official, accessible source and compare it with Kraken's published $2,235.76 settlement. Confirm the 15:00–16:00 London observation, five-minute partitions and any deviation safeguards. The public methodology supports the broad window/partition structure; do not claim exact Kraken implementation without evidence.
4. **Payable-event population completeness.** Establish the public API's historical coverage, retention, refresh and pagination behavior, and reconcile every unexplained interval against an independent authoritative source. Do not treat an incident overlap as proof that funding did not settle. Do not assume the API/archive union is complete merely because the overlap matches exactly.
5. **Bound the external prerequisite.** Use public, no-auth sources first. Do not use account credentials, paid Market History access, private account logs, or contact Kraken on the owner's behalf without explicit authorization. Complete all independent work before declaring an external prerequisite.
6. **Fail over without contaminating the study.** If Kraken's cap/timestamp/population evidence cannot be made authoritative, record the Kraken route as UNRESOLVED/UNACCEPTED and continue a separate MEXC-first, Bitget-second funding-provider pilot under the shared adaptive policy. Keep every venue's data and event semantics separate.
7. **Verify and hand off.** Add deterministic tests for any established timestamp/cap rule, run hosted CI, update the canonical queue, README and report, and preserve the exact evidence. Do not repeat the completed Coinbase windows or re-download the same Kraken archive unchanged.

## Acceptance criteria

- The effective PI cap is documented for each exception date from an authoritative dated source, or the nine rows remain explicitly rejected/unaccepted with the missing source identified.
- API timestamp-to-accrual semantics are supported by authoritative documentation or a reproducible exact-event mapping; otherwise the gate remains closed.
- The PI_ETHUSD 2026-10-30 settlement reference and methodology are reconciled to an official source, or the unresolved component is precisely identified.
- The complete payable settlement-event population is independently supported; unexplained gaps, truncation and retention boundaries are not silently accepted.
- No rate clipping, interpolation, synthetic funding, zero insertion, raw-data commit, credentials, paid data, access-restriction bypass, trading or cross-venue merge.
- Deterministic regression tests and hosted CI pass for any new implementation; README, report and active queue are updated.

**Until every required data-validity gate passes, keep all four Kraken series PROVISIONAL_NOT_ACCEPTED and do not run a Kraken or Binance perpetual backtest.**
