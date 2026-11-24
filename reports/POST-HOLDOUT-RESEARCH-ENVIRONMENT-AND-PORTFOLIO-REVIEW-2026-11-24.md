# Post-Holdout Research Environment and Portfolio Review — 2026-11-24

**Project ID:** `post-holdout-environment-review`  
**Status:** COMPLETE — one substantive cycle used of two maximum  
**Activation:** 2026-11-24T10:27:16Z  
**Completion date:** 2026-11-24  
**Scope:** predecessor retrospective, environment inventory, portfolio selection and repository-admin calibration. No strategy implementation or holdout evaluation.

## Executive decision

**No new strategy hypothesis is ready for implementation from the currently verified evidence envelope.** The repository has a strong, reproducible Binance Spot historical-price path for the specific ETHUSDT/BTCUSDT pair, but it does not yet have a verified point-in-time multi-asset universe, delisted-product history, broad-symbol archive coverage or measured execution costs. The two completed ETH/BTC Spot hypotheses are closed NO-GO experiments, and the separate USD-M funding-aware study remains INCONCLUSIVE.

The highest-value successor is a bounded, public-data-only **Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit**. It will establish whether current catalogue metadata and historical archives can support a defensible, dynamically discovered research universe, including historical listing/delisting limitations. It is an environment-enabling task, not a strategy. No model is selected in advance.

## 1. Predecessor feedback — research and evidence

### Holdout-validation result

The predecessor, [final November 24 holdout validation report](PROSPECTIVE-BINANCE-SPOT-HOLDOUT-SCHEDULED-VALIDATION-2026-11-24.md), is COMPLETE / RECOVERED.

- The scheduled 2026-11-24 04:23 UTC event did not create a run. The first authorized agent wake-up used the existing exact-owner PR #2 command and completed capture in [run 45373419544](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373419544), completing at 10:18:08 UTC. Due-time-to-capture latency was 5h 54m 48s.
- The manifest records **562 closed hourly observations each** for ETHUSDT and BTCUSDT, from 2026-11-01 00:00 UTC through the 2026-11-24 09:00 UTC bar. Both series report zero missing hours, duplicate timestamps, overlap corrections and source errors.
- The current ZIP is Release asset 786684218 (65,817 bytes; SHA-256 `22bd362b7c0db51c7a3302f5b09c1a4a2327a4d9553b8ac7259f2a343c5caade`). Its JSON sidecar is asset 786684257 (5,211 bytes; SHA-256 `57cb7b1d297c15a33aa80784a0b72e010988e3da99a0e65171174ce02e19d284`). The original ZIP 784136576 was preserved; its sidecar was backfilled as asset 786684146.
- Same-slot replay [run 45373703705](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45373703705) independently verified and reused the same ZIP/sidecar IDs with `idempotent_slot_reuse=true`; no duplicate snapshot was published.
- The Release currently has four assets. Release metadata is still `immutable=false`: append-only behavior is a workflow policy, not platform-enforced write-once storage. The separate Actions manifest artifacts expire after 30 days.
- The capture manifest sets `research_evaluation_authorized=false`. This review used only the report, manifest facts and Release metadata; it did not download or inspect the protected raw holdout, evaluate signals or run a strategy.

**Research/evidence interpretation:** the predecessor produced a valid prospective data-preservation and recovery result. It did **not** measure strategy returns, validate an investment edge or promote any model. The 562-row capture is a narrow two-symbol, one-hour operational snapshot—not a multi-asset or long-horizon holdout.

### Carry-forward empirical conclusions

- [Binance Spot ETH/BTC mean-reversion](ETH-BTC-SPOT-EMPIRICAL-RESULT-2026-11-22.md): **NO-GO** for both frozen variants. Do not retune on the same OOS sample.
- [ETH/BTC Spot relative-momentum rotation](ETH-BTC-SPOT-MOMENTUM-EMPIRICAL-RESULT-2026-11-23.md): **NO-GO**. At 10 bps per one-way leg, net CAGR was 1.34% versus BTC buy-and-hold at 11.26%; Sharpe was 0.024 versus 0.213; maximum drawdown was -77.98% versus -67.38%. All six frozen promotion criteria failed. The 7-day paired bootstrap excess-CAGR 95% interval was -28.04% to +11.24%; the 20-bps/leg case lost money. Do not tune or add filters against that OOS sample.
- [Original USD-M funding-aware study](ETH-BTC-FUNDING-DATA-ARCHITECTURE-PIVOT-2026-11-23.md): **INCONCLUSIVE**. Funding inputs remain provisional/unaccepted; no perpetual backtest or venue merge is permitted.

These outcomes reduce the case for more ETH/BTC strategy variants. They do not establish that all other assets or hypotheses are unprofitable.

## 2. Predecessor feedback — technical delivery

| Area | Observed evidence | Operating interpretation |
|---|---|---|
| Scheduled capture | The 04:23 UTC GitHub cron did not fire; first-agent fallback captured at 10:17:48 UTC. | GitHub cron is best-effort, not a delivery SLA. |
| Recovery/idempotency | Successful capture run 45373419544; same-slot replay 45373703705 reused exact assets. | The direct-agent fallback and stable slot check are verified for this slot. |
| Queue guardian | Event-driven handoffs 45373479882, 45373736534 and 45373756502 succeeded. | Completion-triggered handoffs worked; the five-minute scheduled heartbeat is not thereby proven reliable. |
| CI | Main CI 45375425738 passed 324 deterministic tests and the synthetic plumbing smoke test. The review-activation branch CI [45376533993](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45376533993) also passed 324 tests in 14.153 seconds and the synthetic smoke test. | Software and plumbing are validated; this is not market-data or strategy evidence. |
| Artifacts | Release ZIP and sidecar hashes, asset IDs and manifest were verified. Actions manifest artifacts have 30-day expiry. | Recovery is possible for this slot, but external write-once durability is not established. |
| Automation | External authenticated scheduler, dedicated dispatch credential and independent watchdog remain UNCONFIGURED / DEGRADED. | Do not describe the capture system as independently scheduled or DELIVERY_VERIFIED. |
| Live repository state | No open queue-guardian issues, no queued or in-progress runs, and no active research run were found at this checkpoint. PR #2 remains the open draft control surface. | No orphaned incident or active run required recovery before this review. |

The exact first-agent recovery command remains a tightly gated owner command on PR #2. No actor allowlist or workflow permission was broadened. The connected GitHub tool path has no direct workflow-dispatch POST action; no scheduler token, app credential or watchdog was created.

## 3. Environment inventory

Status definitions follow the mandatory [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md): VERIFIED, SAMPLE_ONLY, CLAIMED_UNVERIFIED, UNAVAILABLE / RESTRICTED, UNKNOWN and NOT_APPLICABLE. A VERIFIED status below is always limited to the stated scope; it must not be generalized to every symbol, venue or market.

| Required dimension | Status | Verified evidence and limitation |
|---|---|---|
| Legal and authorized access | **VERIFIED — public read-only scope only** | Binance documents public market-data endpoints as security type `NONE`; no API key is required for those endpoints. The review used public metadata only. This does not authorize private account data, trading, paid data, credentials or any live action. |
| Actual source access | **SAMPLE_ONLY for the wider universe** | Binance Spot monthly archives and aggregate-trade gap controls were successfully used from GitHub-hosted runners for ETHUSDT/BTCUSDT. A current one-symbol request to `https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT` returned BTCUSDT with status TRADING, base BTC and quote USDT. This is one metadata sample, not a full catalogue or an all-symbol runner test. A separate `api.binance.com` ticker request returned HTTP 451 through this browsing proxy; that result is specific to this access path and was not bypassed. |
| Historical coverage and product inception | **SAMPLE_ONLY** | For each of ETHUSDT and BTCUSDT, 82/82 monthly 1h archives for 2020-01-01 through 2026-10-31 were checksum-verified; 59,873 observed rows versus 59,904 expected, with all 31 missing hours independently classified as no-trade intervals using daily aggregate-trade archives and positive controls. This proves the exact pair/window, not the inception or archive coverage of the full symbol universe. |
| Point-in-time universe and delistings | **UNKNOWN** | The public `exchangeInfo` endpoint documents current trading rules and symbol information. No accepted historical catalogue, point-in-time membership history or complete delisted-symbol inventory is present. Current symbols cannot be substituted for historical constituents. |
| Timestamp, schema and market semantics | **VERIFIED for the accepted Spot pair** | Binance Spot klines have open-time identity, millisecond timestamps and a documented 12-field schema; the repository uses UTC bars and aggregate-trade evidence to classify no-trade gaps without synthesizing candles. Funding settlement timestamps and population remain unresolved; Spot evidence does not certify perpetual funding. |
| Data quality and controls | **VERIFIED for the accepted Spot pair; SAMPLE_ONLY beyond it** | The 82/82 monthly archive checksums, 15/15 daily aggregate-trade archive controls and exact gap reconciliation passed for both symbols. The prospective snapshot reports zero gaps, duplicates, overlap corrections or source errors. No equivalent universe-wide controls have been run. |
| Cost and execution economics | **SAMPLE_ONLY** | Spot momentum reports 5–50 bps/leg cost scenarios, with 10 bps as its baseline; these are assumptions, not verified account fee tiers or historical fills. Historical bid/ask depth, queue position, market impact, partial fills, taxes and actual account-specific fees are not available as accepted inputs. Historical Spot borrow is unverified for short strategies. |
| Compute, runtime and API limits | **SAMPLE_ONLY** | Hosted CI uses Ubuntu runners and Python 3.11; the latest review-branch run completed 324 tests in 14.153 seconds plus a synthetic smoke test. CI is capped at 20 minutes; the trusted cache warmer is capped at 30 minutes. Binance documents `exchangeInfo` request weight 20, klines weight 2 and a maximum kline limit of 1,000. The sampled response reported IP request-weight limits; limits are IP-scoped, HTTP 429 requires backoff, and repeated violations can cause HTTP 418 bans. No all-symbol load test has been performed. |
| Storage, retention and recovery | **SAMPLE_ONLY** | `/data/` and `/reports/generated/` are Git-ignored. Raw market data are not committed. The holdout ZIP/sidecar Release assets and same-slot recovery were verified, while Actions artifacts expire after 30 days. Release metadata is not immutable and no independent object store or WORM retention has been verified. |
| Provenance and reproducibility | **SAMPLE_ONLY** | Pair-specific archive manifests bind source files to SHA-256 checksums, run IDs and code commits; deterministic tests and CI pass. However, `research/requirements.txt` specifies minimum dependency versions rather than an exact lock, and there is no broad-universe data manifest or independently retained raw dataset for this review. |
| Workflow permissions and automation | **SAMPLE_ONLY** | CI is `contents: read`; the holdout capture uses `contents: write` behind exact default-branch/actor/command checks; the queue guardian has scoped Actions/issues/PR write permissions. The PR-comment route and event-driven handoffs have worked. The scheduled capture missed its due event, and the external scheduler, GitHub App dispatch credential and independent watchdog remain UNCONFIGURED / DEGRADED. |

### Source and provider disposition

| Source/route | Status | Decision |
|---|---|---|
| Binance Spot monthly klines + daily aggregate trades | **VERIFIED for ETHUSDT/BTCUSDT only** | Reusable pair-specific price evidence; do not infer broad-universe or delisted coverage. |
| Binance Spot `exchangeInfo` | **SAMPLE_ONLY** | One BTCUSDT metadata sample succeeded. The endpoint is a current catalogue, not a historical point-in-time universe. |
| Binance USD-M funding archives/API | **PROVISIONAL_NOT_ACCEPTED** | Existing archives are 8h-only despite conditional 1h/4h funding intervals; the direct funding REST route returned HTTP 451 in the prior runner probe. No perpetual backtest. |
| Market History funding | **CLAIMED_UNVERIFIED / owner authorization absent** | Vendor claims full Binance history; no keyless sample. The $5 minimum purchase and API key are not authorized. |
| Bybit funding API | **UNAVAILABLE / RESTRICTED in the tested runner** | The bounded public probe returned HTTP 403; do not repeat the same route or bypass. |
| Bitget funding download | **UNAVAILABLE / RESTRICTED in the tested browser context** | A Restricted IP modal was observed; do not change region or bypass. |
| OKX funding archive UI | **SAMPLE_ONLY** | Funding download modal was reached, but no instrument/date was selected and no data were downloaded. |
| Kraken PI funding | **SAMPLE_ONLY / not accepted** | A bounded API census returned 34,256 rows and identified nine out-of-cap observations; five two-hour intervals per response had unresolved settlement interpretation, history began 2025-11-19 09:00 UTC, and timestamp-to-accrual semantics/full event completeness remain unresolved. |
| Coinbase Exchange Spot | **SAMPLE_ONLY** | Used only for bounded Kraken PI price plausibility checks; not a complete cross-venue research dataset. |

Provider details and exact evidence are retained in the linked [funding architecture decision](ETH-BTC-FUNDING-DATA-ARCHITECTURE-PIVOT-2026-11-23.md), [Kraken price validation](ETH-BTC-KRAKEN-PI-PRICE-VALIDATION-2026-11-23.md) and [Kraken semantics/completeness task](../tasks/KRAKEN-PI-API-SEMANTICS-AND-SETTLEMENT-COMPLETENESS.md).

### Public API documentation and bounded probe

The one-symbol metadata probe confirms that the public market-data-only host can return current symbol identity and trading filters for BTCUSDT. Binance's official documentation states that `exchangeInfo` returns current trading rules and symbol information, while `/api/v3/klines` is keyed by open time, supports a maximum 1,000 rows per request and has documented request weight. The general API documentation recommends `data-api.binance.vision` for public market data and describes IP-based limits, 429 backoff and 418 bans.

- [Binance Spot REST — exchange information](https://developers.binance.info/en/docs/catalog/core-trading-spot-trading/api/rest-api/general)
- [Binance Spot REST — market endpoints and klines](https://developers.binance.info/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
- [Binance Spot REST — general limits and public market-data host](https://developers.binance.info/en/docs/products/spot/rest-api)

The public probe was deliberately limited to one symbol. No catalogue-wide response, historical archive listing, new market-data download or protected holdout access occurred in this review.

## 4. Candidate generation and portfolio decision

Candidates were considered only after the environment inventory above.

| Candidate | Feasibility and decision | Priority |
|---|---|---|
| **Binance Spot dynamic-universe and historical-coverage feasibility audit** | Uses an already demonstrated public data route and addresses the largest gap preventing broader research: current catalogue enumeration, archive discovery, inception and delisted-product coverage. It can be performed without credentials, purchases, strategy code or protected holdout access. **Select as the next environment-enabling task.** | **1 — READY** |
| Independent external scheduler / watchdog | The operational need is real, but a dedicated authorized GitHub App/dispatch credential and independent watchdog are not provisioned. This is owner-authorization dependent; do not create credentials or permissions speculatively. Continue the existing first-agent fallback. | 2 — BLOCKED / owner prerequisite |
| Funding-aware perpetual research | Funding completeness and timestamp semantics remain unaccepted; the strongest historical vendor route requires an unauthorized purchase/key. Do not backtest or spend. | 3 — NOT READY |
| Cross-sectional crypto momentum or rotation | Requires a point-in-time universe, delisted history and broad-symbol archive coverage that are not verified. Do not start a model before the selected environment audit. | DEFER |
| Another ETH/BTC Spot strategy | Two distinct Spot hypotheses have concluded NO-GO on their frozen OOS evidence. A new idea would require a genuinely distinct hypothesis and independent future holdout; the existing OOS samples are not tuning data. | REJECT for current portfolio cycle |
| Cross-venue basis / funding arbitrage | Venue identity, event semantics, complete funding, historical depth and executable costs are not accepted. | NOT READY |

**Portfolio decision:** no strategy is currently justified. The next project is an environment-enabling feasibility audit, not a promise that a cross-sectional strategy will follow. If point-in-time universe or archive completeness cannot be established, preserve the blocker and do not force a model.

## 5. Repository-admin calibration

### Decision 1 — change scheduler reliability priors

- **Prior assumption to retire:** a configured GitHub Actions cron/guardian schedule could be treated as a dependable due-time trigger.
- **Evidence:** the November 24 04:23 UTC capture schedule created no run; the first authorized wake-up recovered the slot 5h 54m 48s after due time. Same-slot replay was idempotent, but that does not prove scheduled delivery.
- **Revised rule:** classify external scheduling as UNCONFIGURED / DEGRADED until a real end-to-end test proves an independently authorized dispatch, durable per-slot ledger and independent watchdog. Keep GitHub cron opportunistic; use first-agent direct recovery after the due time.
- **Expected effect:** fewer false claims of autonomous delivery and less time lost waiting for a missing schedule event.
- **Validation metric:** for each due slot, record (a) scheduled-delivery success within five minutes / total due slots and (b) due-to-successful-fallback latency. The current observation is one missed scheduled slot and one successful fallback; it is a small sample, not a stable reliability estimate.

### Decision 2 — tighten source-feasibility classification

- **Prior risk:** a public endpoint description or one successful symbol response could be mistaken for broad-universe feasibility.
- **Evidence:** one BTCUSDT `exchangeInfo` response confirms current metadata only; the historical pair pipeline proves only ETHUSDT/BTCUSDT coverage; no point-in-time or delisted-symbol universe has been accepted.
- **Revised rule:** mark a source/dimension VERIFIED only for the exact scope and execution environment tested. Require complete catalogue enumeration, positive/negative controls and historical archive coverage evidence before marking a dynamic universe VERIFIED.
- **Expected effect:** prevent premature model selection and avoid wasting implementation cycles on unavailable historical membership.
- **Validation metric:** source-feasibility false-positive rate = required source dimensions marked VERIFIED that fail their first bounded full-scope acceptance probe / all VERIFIED source dimensions subsequently probed. Report the numerator and denominator; do not invent a baseline.

## 6. Successor handoff

The canonical next task is [Binance Spot Dynamic-Universe and Historical-Coverage Feasibility Audit](../tasks/BINANCE-SPOT-DYNAMIC-UNIVERSE-AND-HISTORICAL-COVERAGE-AUDIT.md).

It is an environment-enabling project with a frozen **MEDIUM** difficulty assessment (score 8), maximum four substantive cycles and five elapsed calendar days, with an absolute deadline of 2026-12-02 17:30 UTC. Its exact start and expiry must be frozen in the queue before its first substantive action. It must dynamically enumerate the full current catalogue, investigate archive/delisted-symbol discovery, use only a deterministic non-exhaustive sample for bounded archive checks, and stop without strategy implementation if point-in-time coverage remains unverified.

No new model, paid dataset, credential, permission, venue merge, live trading or capital deployment is authorized by this review.
