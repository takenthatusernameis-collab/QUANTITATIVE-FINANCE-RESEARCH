# ETH/BTC funding-data architecture pivot after independent source failures

**Status:** COMPLETED — 2026-11-23 09:25 UTC (decision reached; owner authorization remains external)  
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

## One-cycle decision — 2026-11-23

Report: [ETH/BTC funding-data architecture pivot](../reports/ETH-BTC-FUNDING-DATA-ARCHITECTURE-PIVOT-2026-11-23.md).

**Primary route:** Market History's paid historical Binance-perpetual funding dataset. Official docs claim complete event rows from inception, delisted contracts included, interval metadata (1h/4h/8h), nightly updates, and monthly row-by-row validation. Funding requests are paginated by cursor. The minimum one-time purchase is 1M bars for $5, with purchased bars never expiring. The docs contain no keyless funding sample, and exact BTCUSDT/ETHUSDT funding coverage cannot be independently sample-verified. No key or purchase is authorized.

**Fallback:** Prospective event capture only if an official source is legally/regionally available to an authorized runner; it cannot backfill the original 2020–2026 study. The previous direct Binance funding REST route returned HTTP 451; do not retry or evade. If it is unavailable, the next feasible research is a separate spot-only hypothesis using accepted spot data.

**Rejected as substitutes:** Binance Vision's 8h-only archive is not a complete settlement population; MEXC (~540 days), Bitget (90 days), Bybit (403), OKX (no symbol records in the prior probe), and Kraken (different venue, provisional) do not satisfy the original full-history Binance gate. Do not repeat those probes or merge venues.

Decision complete: the original funding-aware study remains INCONCLUSIVE pending owner authorization for the $5 minimum purchase and a subsequent bounded sample-validation gate. The next task is a preregistered, separate spot-only ETH/BTC momentum experiment.

## Acceptance criteria — completed for the architecture decision

- Four materially different routes compared with coverage, cost, permission and limitations: **PASS**.
- Primary route and fallback selected: **PASS** (Market History; prospective capture only if legally/regionally accessible).
- No new free sample, purchase or key was used: **PASS**. Sample validation is an external prerequisite, not an architecture-task requirement.
- Prospective capture is identified as future-only and cannot backfill: **PASS**.
- README/report/queue and one canonical task pointer updated: **PASS**.

**Stop condition reached:** no additional provider search. The original funding-aware study remains INCONCLUSIVE until owner authorization and complete independent validation.
