# Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit

**Project ID:** `BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24`  
**Status:** ACTIVE — activated 2026-11-24; the exact start, expiry and cycle counter are frozen in the canonical active queue.  
**Priority:** P2 — environment-enabling prerequisite for any broader asset-level research.  
**Project kind:** `environment_enabling`; this is not a strategy hypothesis or backtest.

## Rationale and predecessor evidence

The [Post-Holdout Research Environment and Portfolio Review](../reports/POST-HOLDOUT-RESEARCH-ENVIRONMENT-AND-PORTFOLIO-REVIEW-2026-11-24.md) found a verified Binance Spot price-data path for ETHUSDT/BTCUSDT, but no verified point-in-time multi-asset universe, delisted-symbol inventory or broad-symbol archive coverage. A one-symbol public `exchangeInfo` sample succeeded for BTCUSDT. Binance documents that `exchangeInfo` returns current symbol/trading information and that the public market-data-only base host is `data-api.binance.vision`; neither fact establishes historical universe membership.

This task tests whether a broader, dynamically discovered universe can be evidenced before any strategy is selected. It must not assume that the result will be positive.

## Frozen difficulty and timebox policy

- **Difficulty:** MEDIUM.
- **Five-dimension score:** data novelty 2; methodology 2; integration 2; statistical validation 1; compute/operations 1; **total 8 / MEDIUM**.
- **Rationale:** new full-catalogue and historical archive discovery is required; point-in-time/delisted membership needs explicit methodology; a bounded metadata/archive probe and manifest integration are moderate engineering work; no strategy statistics are produced; request and download budgets keep compute modest.
- **Budget:** maximum 4 substantive cycles and 5 elapsed calendar days from activation; the earlier limit controls.
- **Absolute deadline:** **2026-12-02 17:30 UTC**. On activation, set `started_at_utc` and `expires_at_utc` exactly, with expiry no later than five days after start and no later than the absolute deadline.
- **Terminal rule:** if complete universe/archive evidence is not obtained by expiry, close as INCONCLUSIVE/INFEASIBLE with the exact missing dimension. Expiry is not a strategy NO-GO.
- **No clock reset:** agent handoffs, ordinary CI/runner delays and route changes do not reset the budget.



## Activation record — 2026-11-24

- **workstream_id:** `BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24`
- **started_at_utc:** `2026-11-24T12:28:44Z`
- **expires_at_utc:** `2026-11-29T12:28:44Z`
- **max_cycles / cycles_used:** 4 / 0 at activation.
- **Activation authority:** canonical [active queue](ACTIVE-QUEUE.md); this task's MEDIUM score and five-day ceiling remain unchanged.
- **No strategy, holdout evaluation, paid data, credentials, or trading authorization is created by activation.**

## Objective

Determine whether Binance Spot's public catalogue and historical archive surfaces can support a defensible, dynamically discovered, point-in-time asset universe for future research, including current instrument identity, historical archive presence, product inception and delisted-symbol limitations.

Do not choose a trading model in this task. Do not inherit ETHUSDT/BTCUSDT as the research universe; they are positive controls only and any seed assets must remain explicitly non-exhaustive.

## Required sequence

1. Reconstruct live repository state and inspect this task's predecessor report, source code, current API documentation and any already-active runs/artifacts. Do not duplicate a completed probe.
2. Fetch the complete current Spot symbol catalogue from the public market-data-only `exchangeInfo` endpoint. Record exact request parameters, retrieval time, response hash, counts, statuses, base/quote identifiers, permissions and symbol filters. Do not use a hand-written ticker allowlist or top-N truncation.
3. Verify whether the official public archive surface can enumerate monthly Spot kline objects and whether its listing/index route has complete, paginated coverage. Determine whether delisted symbols can be discovered from an authoritative route; do not infer that current `exchangeInfo` contains delisted products.
4. Only after full catalogue enumeration, choose a deterministic, documented, **non-exhaustive** sample across available quote assets/status/history strata. Include BTCUSDT and ETHUSDT as positive controls and at least one non-seed symbol selected from the returned catalogue. Preserve the sampling algorithm and the full catalogue separately.
5. Run bounded monthly 1h archive checks for the selected sample, including a recent complete month and a historical month. Use a pre-listing negative control only when independent inception evidence exists. Verify file identity, schema, UTC timestamps, checksums, row counts, duplicates, gaps and known-active positive controls.
6. Use a nonexistent-symbol or known-absent archive as a negative control. Confirm that missing/invalid data fail closed rather than becoming zero returns, synthetic candles or silently excluded assets.
7. Keep raw market data ephemeral. Upload/commit only compact manifests, exact request metadata, checksums, summaries and screenshots if required. Do not commit raw ZIP/CSV files.
8. Classify each dimension as VERIFIED, SAMPLE_ONLY, CLAIMED_UNVERIFIED, UNAVAILABLE/RESTRICTED, UNKNOWN or NOT_APPLICABLE. Explicitly distinguish current catalogue completeness from historical point-in-time universe completeness.
9. Recommend a future research opportunity only if every required data/universe dimension is VERIFIED. Otherwise report the exact blocker and do not start a strategy implementation.

## Hard resource and safety limits

- Public, read-only data only; no API keys, account endpoints, paid datasets, purchases, credentials, permissions or external services.
- Maximum 50 metadata/API requests and 12 archive objects in the bounded pilot; stop earlier if response headers or documented limits require it.
- Maximum 250 MB downloaded across all sample archives. Record actual bytes and elapsed time.
- Respect IP-based rate limits and `Retry-After`; back off on HTTP 429 and stop on HTTP 418/403/451. No proxies, region changes, alternate identities or access-control workarounds.
- No venue merge, funding research, protected holdout access, strategy backtest, signal/performance inspection, live order or capital deployment.
- The sample is explicitly non-exhaustive. It must not be used to claim universe-wide historical completeness or justify a permanent top-N universe.

## Acceptance criteria

- [ ] Complete current Spot catalogue response is retained by SHA-256 with exact request/time and symbol counts.
- [ ] Every catalogue symbol has a normalized identity/status/quote/permission record or a documented parse failure.
- [ ] Archive-listing/index semantics and pagination are verified, or the exact limitation is recorded.
- [ ] Delisted-symbol and historical membership coverage are VERIFIED or explicitly UNKNOWN/UNAVAILABLE; current symbols are not treated as historical constituents.
- [ ] Deterministic sample selection is reproducible, non-exhaustive and not an arbitrary fixed ticker list.
- [ ] Positive and negative controls behave as expected; sampled archive checksums/schema/coverage pass or are explicitly rejected.
- [ ] No raw data are committed or uploaded; provenance and manifest hashes are retained.
- [ ] The final report distinguishes VERIFIED from SAMPLE_ONLY and states whether any broader hypothesis is actually ready.
- [ ] Any later hypothesis receives its own identity, preregistration, independent holdout and difficulty/timebox before implementation.

## Stop conditions

Stop the affected route immediately on an authorization restriction, HTTP 403/418/451, unexpected request volume, unbounded archive listing, incomplete pagination, schema ambiguity or any indication that the 250 MB / 12-object / 50-request budget would be exceeded. Do not retry an unchanged permanent failure or bypass the restriction.

If point-in-time universe or historical archive completeness cannot be established within the frozen timebox, close INCONCLUSIVE/INFEASIBLE and preserve the exact blocker. Do not force a strategy selection merely to keep the research queue occupied.
