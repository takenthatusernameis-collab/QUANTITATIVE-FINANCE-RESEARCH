# Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit

**Project ID:** `BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24`  
**Status:** CLOSED — INCONCLUSIVE; final substantive wake-up completed 2026-11-24 14:53 UTC; 4 of 4 cycles used. The cycle cap was reached; no extension or expiry reset was granted.  
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
- **max_cycles / cycles_used:** 4 / 4 at final closure (2026-11-24 14:53 UTC). The fourth cycle was limited to independent source review and terminal disposition; workflow-run count is not used as a substitute for agent-cycle count.
- **Activation authority:** canonical [active queue](ACTIVE-QUEUE.md); this task's MEDIUM score and five-day ceiling remain unchanged.
- **No strategy, holdout evaluation, paid data, credentials, or trading authorization is created by activation.**


## Autonomous execution interface

- **Workflow:** `.github/workflows/binance-spot-universe-audit.yml`.
- **Exact command:** `/qfr-audit-binance-spot-universe` on open control PR #2, posted by the verified actor `takenthatusernameis-collab`.
- **Security:** `issue_comment: created`; exact PR, open state, actor and whole command; checkout of the event's default-branch `GITHUB_SHA`; `GITHUB_REF` verification; `persist-credentials: false`; `contents: read` only; no secrets or PR-head code.
- **Queue group:** `binance-spot-universe-audit-main`, explicitly allowlisted in `research/queue_guardian.py`.
- **Artifact:** `binance-spot-universe-audit-<run_id>`; only `manifest.json`, normalized `catalogue.json` and an archive-prefix index if one is actually obtained. Raw response bodies and ZIP/CSV market data remain ephemeral.

## Initial runner probe evidence — 2026-11-24

Run [45395322993](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45395322993) proved that the GitHub-hosted runner can retrieve the **complete current** public Spot `exchangeInfo` catalogue:

- HTTP 200 from `https://data-api.binance.vision/api/v3/exchangeInfo`; retrieved at 2026-11-24 12:37:44.598995 UTC.
- Raw response SHA-256: `84885194a788fcf6095bddda2420cd98fc384c97e907e167e29ad9ffa07464e5`; 18,152,734 decoded response bytes; `X-MBX-USED-WEIGHT-1M: 20`.
- 3,751/3,751 symbols normalized with zero parse errors; 1,376 `TRADING`, 2,375 `BREAK`; 50 quote assets; `isSpotTradingAllowed`: 3,711 true and 40 false. `BREAK` is a current status value, not proof of a delisting date or complete historical universe.
- The same run's single ListObjectsV2 prefix request returned HTTP 200, `text/html`, 2,712 bytes, rather than an XML `ListBucketResult`. Pagination and archive symbol-directory enumeration are therefore **not verified**. The affected listing/index route is stopped; do not repeat it or probe alternate directory-index paths without a separately justified route.
- The first implementation failed because the XML parser exception was not caught. The uploaded artifact [14920004516](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45395322993/artifacts/14920004516) has digest `sha256:8386d14ba23f79bc7e418f5ff0de2b9f514b9b00df0416f8694da3fe4bb390d7`; it contains the manifest and normalized catalogue only. No archive object was downloaded and no klines inception query was made in that run.
- The parser now converts non-XML index responses into a recorded schema limitation, and the runner audit skips that known failed index route. The direct documented monthly-object route was tested in run [45396976562](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562); see the second-wake-up checkpoint report below.
- CI run [45397358320](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45397358320) covers the current code on commit c67b6d and passed 346 deterministic tests plus the synthetic smoke test.


## Second-wake-up checkpoint — 2026-11-24 12:53:20 UTC

Full evidence and exact classifications: [Binance Spot Dynamic-Universe and Historical-Coverage Audit checkpoint](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md).

- Current exchangeInfo snapshot: 3,751/3,751 unique symbols normalized, zero parse errors; 1,376 TRADING, 2,375 BREAK, 50 quote assets, 3,711 spot-allowed and 40 not spot-allowed. Raw response SHA-256: 1547b62532d008d7e2ca92a64d3f60be23d32552a675a96b82f67f515d2b5d53.
- Run [45396976562](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562), artifact [14920684215](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562/artifacts/14920684215), contains only manifest.json and normalized catalogue.json. The normalized catalogue SHA-256 is 86cfc7b96303d1b8c3397469ca4524328109425fb89b24c75e7ca7d572ceda47; artifact SHA-256 is f6749853ea829a013490e9af394d6b24e39a51e96433cbcfee7ed9070dcd5e66.
- Direct monthly object checks used 5 metadata/API requests, 11 unique archive objects, 16 HTTP requests total and 155,377 downloaded archive bytes. BTCUSDT 2026-10, ETHUSDT 2026-10, USDTAED 2026-10 and BTCUSDT 2020-01 passed 744-row monthly checks and checksum validation. USDCAED 2026-10 was explicitly rejected as a complete month: four rows, 740 missing hours and one close-time alignment error; its first-kline query was 2026-10-28 08:00 UTC. QFRNOTREALUSDT returned the expected 404. No pre-listing archive negative-control request was made.
- A non-exhaustive cross-check of 106 pair symbols sampled from 17 official pair-removal notices (2023–2026) found 105 current catalogue records in BREAK and one, ACMTRY, in TRADING after its 2025 relisting. An additional 20 current catalogue records associated with tokens named in 2018/2019 token-delisting notices were all present in BREAK. This is SAMPLE_ONLY evidence of retention, not a complete historical symbol inventory.
- The official announcement category is a possible event source, but complete historical pagination and listing/removal/relisting coverage are not verified. The current catalogue has no point-in-time lifecycle dates. The archive prefix-list request remains unusable in the tested form (HTTP 200 HTML rather than XML); direct object URLs are verified only for the bounded sample.
- Latest main CI [45397358320](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45397358320) passed 346 deterministic tests in 15.555 seconds and the synthetic pipeline smoke test on commit c67b6d686475c5bbc96c43516bcd248d442d020e. This is engineering evidence, not data or strategy acceptance.
- Current classification: current catalogue VERIFIED; direct archive objects SAMPLE_ONLY; sampled delisted-pair presence SAMPLE_ONLY; complete delisted inventory UNKNOWN; point-in-time membership and universe-wide archive completeness UNKNOWN. No strategy is admitted.

**Next action at the second checkpoint (completed at the third checkpoint):** inspect the official Binance announcement categories and reconcile a bounded older event sample. The third-checkpoint report records the result and the scope deviation; do not repeat the archive sample or call undocumented endpoints.
## Third wake-up checkpoint — 2026-11-24 13:31 UTC

Full findings are in the [third-checkpoint report](../reports/BINANCE-SPOT-DYNAMIC-UNIVERSE-AUDIT-2026-11-24.md).

- The visible New Cryptocurrency Listing and Delisting category pages expose 231 and 45 pages respectively, but their first pages mix Spot, Futures, token, Margin, bStocks/stock-options and Alpha items. The inspection surface did not permit verification of page 2 or the oldest page; no official completeness guarantee was found.
- A bounded sample of 18 pair records from four 2022 listing/removal notices and the ACM/TRY removal/reopening sequence was reconciled against the retained 2026-11-24 catalogue: all 18 records are present; 15 are BREAK and 3 are TRADING. This remains SAMPLE_ONLY and does not establish a complete lifecycle ledger.
- Undocumented public BAPI list endpoints were inadvertently opened during route discovery. Its response is excluded from evidence and no further use is permitted. The accepted event evidence is from individual official announcement pages.
- The single pre-listing archive URL attempt was inaccessible through the inspection surface and yielded no HTTP status or bytes; it is not a verified negative control and must not be retried in this task.
- Current catalogue remains VERIFIED for its snapshot; direct archive objects and sampled lifecycle records remain SAMPLE_ONLY; complete historical membership, announcement-history completeness and universe-wide archive coverage remain UNKNOWN.
- Latest main CI [45404093861](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404093861) passed 346 deterministic tests in 15.485 seconds and the synthetic smoke test on commit `1459356eeb93c017920d6ab016249493b4ccb67b`.
- Workstream remains ACTIVE / MEDIUM / cycle 3 of 4. No strategy is admitted.

**Next action:** use the final cycle for an independent evidence review and, only if supported visible UI navigation is available, verify older announcement pages. Otherwise close INCONCLUSIVE/INFEASIBLE with the exact missing dimensions. Do not use undocumented endpoints, repeat archive probes, or start a strategy.


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


## Acceptance criteria — final disposition 2026-11-24 14:53 UTC

- [x] Complete current Spot catalogue response retained by SHA-256 with exact request/time and symbol counts.
- [x] Every returned catalogue symbol normalized with identity/status/quote/permission fields or a documented parse failure; 3,751/3,751 normalized with zero parse errors.
- [x] Archive-listing/index semantics and pagination investigated; the tested prefix route's HTML/schema failure and lack of verified supported pagination are explicitly recorded.
- [x] Delisted-symbol and historical membership coverage explicitly classified: sampled presence is SAMPLE_ONLY; complete lifecycle and point-in-time membership remain UNKNOWN.
- [x] Deterministic, non-exhaustive sample selection and its limitations are documented.
- [x] Positive and negative controls behaved as expected; sampled archive checksums/schema/coverage were accepted or explicitly rejected. No pre-listing negative-control result is claimed.
- [x] No raw market data committed or uploaded; provenance, hashes and compact catalogue artifact retained.
- [x] Final report distinguishes VERIFIED from SAMPLE_ONLY/UNKNOWN and concludes that no broader universe or strategy is ready.
- [x] Any future hypothesis remains subject to its own identity, preregistration, independent holdout and mandatory difficulty/timebox gate.

## Stop conditions

Stop the affected route immediately on an authorization restriction, HTTP 403/418/451, unexpected request volume, unbounded archive listing, incomplete pagination, schema ambiguity or any indication that the 250 MB / 12-object / 50-request budget would be exceeded. Do not retry an unchanged permanent failure or bypass the restriction.

If point-in-time universe or historical archive completeness cannot be established within the frozen timebox, close INCONCLUSIVE/INFEASIBLE and preserve the exact blocker. Do not force a strategy selection merely to keep the research queue occupied.


## Final cycle and terminal disposition — 2026-11-24 14:53 UTC

**Decision: INCONCLUSIVE.** The audit established a complete current snapshot and several useful samples, but did not establish a complete historical Spot universe or archive-coverage contract. This is not proof that Binance has no internal or other historical records; it means no sufficiently complete, authorized and reproducible public evidence route was verified within the frozen four-cycle budget.

### Independent source review

- The official [New Cryptocurrency Listing category](https://www.binance.com/en/support/announcement/list/48) currently renders **231 pages**. Its visible first-page entries mix Spot trading-pair announcements with token listings, Futures products, bStocks and other products. Numeric pagination is visible, but the available read-only inspection surface exposes no clickable destination for page 2 or the oldest page. No unsupported page URL or undocumented endpoint was guessed.
- The official [Delisting category](https://www.binance.com/en/support/announcement/list/161) currently renders **45 pages**. Its visible first page mixes Spot pair removals with Margin, Futures, token and Binance Alpha removals. It is not a Spot-pair-only lifecycle feed.
- Binance's [delisting-information FAQ](https://www.binance.com/en/support/faq/detail/2068a768949b4ccab0cd7ac962465ddd), published 2022-10-27 and updated 2026-01-07, explains where users can find delisting announcements and how notifications work. It does not state a complete historical-retention guarantee or provide a point-in-time pair-membership ledger.
- The official [Binance Public Data README](https://github.com/binance/binance-public-data/blob/master/README.md) describes daily/monthly public archives and checksum files and points to a helper for obtaining current running symbols. It does not document a complete dated historical Spot symbol manifest, lifecycle event ledger or exhaustive archive-directory index.
- Upstream [binance/binance-public-data issue #479](https://github.com/binance/binance-public-data/issues/479), which asks for a historical Spot symbol manifest and archive-boundary guarantees, remains OPEN as of 2026-11-24 08:51:49 UTC. Its two visible comments are user follow-ups; no maintainer answer or authoritative completeness statement is present. This is supporting context, not proof that no private or unindexed source exists.

### Final evidence classification

| Dimension | Final classification | Basis |
|---|---|---|
| Current Spot catalogue | VERIFIED for the 2026-11-24 snapshot | 3,751/3,751 normalized; raw and normalized hashes retained |
| Direct monthly archive objects | SAMPLE_ONLY | Four accepted of five sampled files; one incomplete month explicitly rejected |
| Announcement-category pagination | SAMPLE_ONLY | 231 and 45 visible pages; mixed-product categories; older-page navigation and retention completeness unverified |
| Older pair lifecycle reconciliation | SAMPLE_ONLY | 18 selected pairs from 2022 events and ACM/TRY removal/reopening all present; 15 BREAK, 3 TRADING |
| Complete historical delisted-symbol inventory | UNKNOWN | No exhaustive authoritative pair-event ledger |
| Point-in-time listing/delisting/relisting membership | UNKNOWN | Current exchangeInfo status does not encode effective lifecycle dates |
| Universe-wide historical archive completeness | UNKNOWN | No complete symbol/month index or exhaustive symbol-month validation |

The prior archive sample was not repeated, the inaccessible pre-listing URL was not retried, undocumented BAPI endpoints were not used again, and no additional market-data downloads were made.

### Four-axis outcome and handoff

- **Engineering:** PASS for the bounded audit implementation and existing tests; latest main CI [45404411941](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404411941) completed successfully on b2d6d3271bbfa2cf2559fd4be68a7a2d919a233b. The preceding full run [45404093861](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45404093861) passed 346 deterministic tests and the synthetic pipeline smoke test.
- **Data:** PARTIAL; current catalogue is VERIFIED for its snapshot, while historical universe/archive dimensions remain SAMPLE_ONLY or UNKNOWN.
- **Empirical research:** NOT RUN / NOT APPLICABLE; no strategy or backtest was authorized by this audit.
- **Operations:** the audit's owner-authorized read-only workflow run [45396976562](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45396976562) completed successfully and its 496,162-byte catalogue artifact remains available with digest sha256:f6749853ea829a013490e9af394d6b24e39a51e96433cbcfee7ed9070dcd5e66. This does not establish factory-wide scheduler delivery.

**Closure:** cycle 4/4 reached; no extension. No broader Spot universe, strategy hypothesis or successor workstream is admitted. Reconsider only if materially new authoritative evidence or a separately authorized, documented source route becomes available.
