# ETH/BTC funding-data architecture pivot after independent source failures

**Status:** PENDING — 2026-11-23  
**Priority:** P2 unblock existing research / P4 architecture replacement  
**Time budget:** One research cycle. Produce a decision, not an open-ended provider hunt.  
**Research gate:** The original Binance USD-M funding dataset remains PROVISIONAL_NOT_ACCEPTED; no perpetual backtest or venue merge.

## Objective

Find a materially different, safe and reproducible architecture to obtain or build a complete, event-level ETHUSDT/BTCUSDT funding dataset for the original study. Existing routes have failed on coverage, semantics or access. Preserve venue/instrument identity; do not force a substitute.

## Current evidence (reuse; do not repeat)

- Binance Vision monthly funding archive: 7,488 rows per symbol, 8-hour cadence only, 2020-01-01 through 2026-10-31; official checksums passed, but conditional 1h/4h settlement intervals make event-population completeness unverified.
- Binance public funding REST: `fapi.binance.com/fapi/v1/fundingRate` returned HTTP 451 on prior hosted-runner requests. Do not retry or evade.
- MEXC public funding-history pilot: 1,620 rows each, about 540 days (starts 2025-05-31); not full-history coverage.
- Bitget funding API: 90-day window; full-history download not documented/verified. Hosted browser encountered a Restricted IP dialog; no bypass.
- Bybit public API pilot: all six bounded requests returned HTTP 403 from the hosted runner; no retry for 403.
- Kraken: public API/archive is a different venue and remains provisional. Nine PI cap anomalies and five common two-hour gaps unresolved; do not merge with Binance.
- Tardis: one no-key sample day (2026-10-01) corroborated Kraken PI timestamp semantics; gap dates all returned HTTP 401. No repeat without new authorization.
- Market History is the cost-first commercial candidate, claims full Binance event history including delisted contracts and variable 1h/4h/8h intervals, with a $5 minimum one-time purchase. No key or purchase authorized. Vendor claims are not acceptance evidence.
- Spot-only ETH/BTC mean-reversion study already returned NO-GO for both tested variants; that result does not reject all possible spot strategies.

## One-cycle architecture options

Evaluate no more than these four materially different routes and rank by probability of obtaining trustworthy event coverage, time-to-proof, cost, permissions, source provenance and future maintainability.

1. **Commercial complete-history dataset (primary candidate):** Market History $5 one-time minimum. Assess the exact schema, historical event coverage, delisted-contract handling, interval fields, checksums/source methodology, and a small BTC/ETH sample if publicly available. Do not create a key or buy without explicit owner authorization.
2. **Prospective first-party event capture:** Design a low-cost collector using official Binance public funding/settlement data from now forward. Define event identity, UTC timestamp semantics, interval/cadence changes, idempotency, checksums, checkpointing, gap alerts, duplicate and completeness controls. Clearly state it cannot backfill 2020–2026.
3. **Restricted-coverage archive sensitivity:** Decide whether the existing 8-hour-only Binance dataset can support a separately defined 8-hour-only sensitivity experiment. It cannot satisfy the original complete-event gate or be presented as a full funding-aware result. Do not run a backtest in this task.
4. **Separate-venue dataset:** Reuse existing MEXC/Bitget evidence only. If feasible, formulate a separate venue-specific question; never combine or substitute its funding rates for Binance.

Do not add more providers unless the one-cycle screen finds a genuinely new route with a clear reason. No paid access, credentialed access, access-restriction bypass, raw-data commit, backtest, or live trading.

## Acceptance criteria

- A concise comparison of the four architectures with sourced coverage, cost, permission, data semantics and hard limitations.
- Select one primary route and one fallback, or conclude that the original study is INCONCLUSIVE/INFEASIBLE pending the exact owner authorization.
- Any new free sample is bounded, one-time and materially different from already failed routes; validate both symbols, interval semantics, positive/negative controls, completeness and provenance before acceptance.
- Prospective collection may be designed or tested with synthetic fixtures only; never imply it fills historical gaps.
- Keep one canonical task pointer; update README and report; no redundant probe or provider retry.

**Stop condition:** End the cycle after the decision and precise prerequisite/handoff. Do not keep searching indefinitely. The original empirical gate remains closed until complete, independently validated payable funding events are available.
