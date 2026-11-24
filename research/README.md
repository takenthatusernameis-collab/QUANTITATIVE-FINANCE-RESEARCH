# ETH/BTC quantitative research pipeline


**Repository-wide operating rules:** follow the [General Antifragile Autonomous Operating Mindset](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md), [Adaptive Execution Standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md), and [Repository Hygiene preflight](../docs/REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md). The single current task pointer is [tasks/ACTIVE-QUEUE.md](../tasks/ACTIVE-QUEUE.md).

## New-project intake (mandatory before hypothesis design)

The research factory is evidence-first and has no global asset whitelist. Review research/performance and technical-delivery feedback from the previous task, calibrate repository-admin decisions, and inventory actual accessible sources before designing a model. The existing `run_eth_btc.py` pipeline and Spot holdout tooling are pair-/capture-specific implementations, not the factory's complete research universe. Do not carry their ETHUSDT/BTCUSDT symbols into unrelated hypotheses. Required evidence covers authorized access, product/history coverage, point-in-time population, market/time semantics, quality controls, execution costs, compute/API limits, storage, provenance and workflow permissions.

Only VERIFIED required dimensions may support a new hypothesis. Sample-only or claimed source support is a bounded pilot, not model readiness. If the environment is insufficient, scope a bounded environment-enabling project rather than bending the data/infrastructure around a favored model.

- [Evidence-First Project Lifecycle](../docs/RESEARCH-ENVIRONMENT-FIRST-PROJECT-LIFECYCLE.md)
- [Project Retrospective and Admin-Agent Calibration](../docs/PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md)
- [Asset-Universe Discovery and Scope Policy](../docs/ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md)
- [Project intake template](../templates/PROJECT-INTAKE-TEMPLATE.json)
- Deterministic gate: `project_readiness.py`

## Run

From the repository root, install the dependencies and run:

```bash
python -m pip install -r research/requirements.txt
python research/run_eth_btc.py --start 2020-01-01 --end 2026-10-31 --market both
```

The script downloads monthly 1-hour Binance Spot and USDⓈ-M perpetual klines for `ETHUSDT` and `BTCUSDT`. USD-M funding history is ingested from monthly Binance Vision `fundingRate` ZIP archives with `.CHECKSUM` verification, schema and UTC-month validation, per-month provenance, and consolidated row-count/hash manifests. The archive route is deliberately fail-closed: the downloader preserves the data and manifest but rejects empirical use until the complete payable-settlement population and event semantics are independently established. Monthly archives are cached under `data/cache/`; consolidated input CSVs and per-archive SHA-256/checksum/timestamp-unit manifests are written under `data/raw/`. The run writes data-quality JSON with sample bounds, gaps and source hashes. Generated outputs go to `reports/generated/`. Raw data are not intended to be committed.

Use `--market spot`, `--market um`, or `--market both`. `--self-test` runs a synthetic plumbing test only; it is not evidence of strategy performance.

## Autonomous execution, failover and incident handling

Routine safe research work is agent-initiated: deterministic tests, synthetic checks, historical data audits, lawful data retrieval, parser repair, provider comparison, research code, historical backtests after their acceptance gates pass, artifact inspection, reporting and task handoff. Do not wait for a routine user click or confirmation. Genuine security, legal, permission and live-financial boundaries remain enforced.

Treat the first implementation route as replaceable. Diagnose the exact failure, preserve the request/error/source/schema/timestamps and hashes, test at least three materially different options where applicable, and stop an unchanged non-transient route after two independent identical failures. Use positive controls and provenance. A new data source, time resolution or model is a separate experiment with its own frozen hypothesis and acceptance criteria; never combine its outputs as if they belonged to the original study.

### GitHub Actions queue enforcement

- The scheduled workflow [queue-guardian.yml](../.github/workflows/queue-guardian.yml) scans the repository's explicitly allowlisted safe workflows every five minutes. The deterministic policy cancels workflow-run-level queued/pending runs older than 15 minutes unless an earlier run in the exact same concurrency group is currently in progress.
- The exception is only for an earlier active same-group predecessor. A merely queued predecessor, a different workflow/group, an individual queued job within an in-progress workflow, or an environment approval wait does not qualify.
- Each cancelled run receives a durable queue-incident issue with status `QUEUE_CANCELLED / RETRY_REQUIRED`. If cancellation cannot be confirmed, the original is recorded `CANCELLATION_BLOCKED / ORPHANED_POSSIBLE_EXECUTION` and the next agent must launch exactly one materially different, independently isolated alternative as `ALTERNATIVE_ATTEMPT_ACTIVE`.
- Check open issues with the title prefix `[QFR queue guardian]` at the start of each agent cycle. Handle cancellation-blocked issues before creating new overlapping work. Keep run IDs and attempt lineage in the task record.
- The harmless command `/qfr-queue-guardian-dry-run` on control PR #2 executes the scanner without cancellation or issue creation. The scheduled workflow is the live enforcement path; it requires only `actions: write`, `contents: read` and `issues: write` for the repository.
- Research-test CI is serialized with a bounded queue. The queue guardian only handles the two paths explicitly mapped in `research/queue_guardian.py`; unknown workflows are never cancelled until deliberately reviewed and allowlisted.

### Alternative-attempt isolation

An alternative attempt must have its own attempt key, execution route, worktree/branch where appropriate, cache key, manifests, artifact namespace and output paths. Keep all attempts read-only with respect to trading venues/accounts and prevent shared mutable writes. If a full alternative run cannot be isolated safely, immediately advance an independent non-mutating slice such as a provider positive-control probe, parser fixture, deterministic test or separately specified model audit. Do not spawn endless retries: diagnose each new failure before selecting the next distinct approach.

Queue or infrastructure failures are not empirical strategy failures. Never fabricate market observations, forward-fill missing prices, substitute zero funding, weaken data gates, or use synthetic smoke results as evidence of a trading edge. No live orders, capital deployment, live credentials or strategy promotion.

### Independent Bybit funding-history sample

The allowlisted control-PR command `/qfr-probe-bybit-funding-history` runs a read-only public API availability check for exactly `BTCUSDT` and `ETHUSDT`. It samples 2020-01-01, 2022-01-01 and run-time UTC, at most 200 rows per request (six requests total, three bounded attempts per request). Raw response caches stay on the ephemeral runner; only hashed compact manifests are uploaded. This is an independent Bybit venue pilot, not Binance evidence, full-history acceptance, or a backtest. The official endpoint documents endTime-only sampling and a 200-record maximum: [Bybit funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate).

### Bybit pilot result — 2026-11-22

All six public API requests (BTCUSDT and ETHUSDT × 2020-01-01, 2022-01-01, run-time UTC) returned **HTTP 403 Forbidden** from the hosted GitHub runner. Because 403 is treated as a permanent failure, the probe made no retries. Artifact [14750381483](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45012785615/artifacts/14750381483) contains compact per-symbol manifests only; raw response caches were not uploaded. This proves the route is blocked in this runner context, not that Bybit data is universally inaccessible or retention is known. No funding data accepted and no backtest performed. Do not repeat the same probe; move to a distinct provider route.

## Research design

- Signal: completed-bar close; execution: next bar open; PnL: open-to-open.
- Fixed spread: `log(ETHUSDT) - log(BTCUSDT)`.
- Dynamic spread: `log(ETHUSDT) - alpha - beta*log(BTCUSDT)`, with trailing 30-day OLS parameters refreshed once daily from prior observations.
- Entry/exit/stop: absolute z-score 2.0 / 0.5 / 4.0; maximum holding period seven days.
- Walk-forward: 730 calendar days of trailing training data followed by non-overlapping 90-day test folds. No parameter optimization is performed; thresholds are pre-specified.
- Position sizing: spread-hedge neutrality, not dollar neutrality. The two leg weights are normalized to 1x gross exposure using the estimated log-price hedge ratio. A close signal is shifted one bar and executed at the next bar open.
- Costs: fees, slippage and spread are configurable per leg per side; 1.0x, 1.5x and 2.0x cost cases are reported. USDⓈ-M funding is charged at observed settlement timestamps. Spot borrow can be configured with `--spot-borrow-bps-per-day`.
- Daily robustness resamples OHLC data and uses next-day-open execution. It is price-only: funding is not applied to the daily robustness run. Sharpe and Sortino use a 0% risk-free hurdle; annualization is 8,760 hourly or 365 daily periods.

## Spot event-time integration status

`research/event_time.py` is integrated into the production Spot walk-forward path in `research/run_eth_btc.py`. When the synchronized Spot hourly index is irregular and its provenance gate passes, the pipeline routes to `walk_forward_event_time`; it does not synthesize candles, forward-fill prices, or assign a one-hour return to a multi-hour elapsed interval. The integrated path uses calendar-time rolling features, next-observed-open execution, actual elapsed holding and borrow costs, event-time benchmarks, fold-end liquidation, and continuous-time annualization. Daily Spot aggregation uses the regular daily engine while every UTC day is represented and switches to event-time accounting only when the daily index is itself irregular.

The Spot gate remains fail-closed: both symbols must have synchronized gap inventories, checksum-verified monthly kline and daily aggregate-trade provenance, successful same-day positive controls, and exact source-to-CSV manifest binding. This acceptance applies only to Spot price observations; it does not accept USDⓈ-M funding or permit combined/perpetual research. The default Spot borrow charge remains an illustrative assumption unless historical borrow evidence is independently verified.

The event-time path writes `<market>_<interval>_oos_returns.csv` and `<market>_<interval>_pooled_oos_summary.csv`. The pooled file reports all-fold 1.0x, 1.5x and 2.0x cost point estimates. The primary 1.0x case also receives 95% percentile intervals from a fold-stratified moving-block bootstrap using seven-calendar-day blocks and 1,000 replications; blocks are sampled by elapsed time and never cross fold boundaries. The 1.5x and 2.0x rows are point estimates only. The seven-day block is aligned with the strategy's maximum holding horizon, but alternative block-length sensitivity and verified historical Spot borrow costs remain necessary before strong inference.

Deterministic integration tests cover the irregular Spot walk-forward outputs, benchmarks, continuous-time metrics, pooled OOS aggregation, deterministic calendar-time bootstrap, diagnostics labeling, no-trade evidence, and fail-closed manifest checks. These tests validate implementation behavior, not full-history strategy performance. The original strict hourly representation remains incomplete, and the empirical result remains **INCONCLUSIVE** until the authorized Spot-only run completes and its real-data artifacts and out-of-sample outputs are reviewed.

## Preregistered Spot relative-momentum rotation

The frozen experiment is implemented in `research/spot_momentum.py` and is intentionally separate from the earlier mean-reversion study. Run from the repository root:

```bash
python research/spot_momentum.py --start 2020-01-01 --end 2026-10-31 --data-dir data --output-dir reports/generated/spot-momentum
```

The runner downloads only Binance Spot ETHUSDT/BTCUSDT monthly hourly archives, verifies their checksum/provenance, reconciles missing hours against official daily aggregate-trade archives and positive controls, then fails closed unless the existing Spot event-time gate accepts the exact source files. It does not download or read funding data.

The signal is the daily UTC-close ETH/BTC ratio versus its 200-valid-daily-observation SMA. A signal is known at the next UTC midnight and executes at the first observed hourly open at or after that time. The last observed close in a UTC day is used only when no more than one hour stale at midnight; otherwise no new signal is generated. No missing price is forward-filled or synthesized. The target is 100% ETH above the SMA and 100% BTC otherwise.

The model is long-only, unlevered and Spot-only. All-in transaction-cost scenarios are 5, 10, 15, 20, 25 and 50 bps per one-way leg; a full ETH-to-BTC rotation pays both legs. Benchmarks are BTC buy-and-hold, ETH buy-and-hold, 50/50 buy-and-hold and 50/50 monthly rebalanced. Outputs include net OOS metrics, turnover, time allocation, recovery periods, equity/cost charts, exact source SHA-256 values and paired 3/7/14-day block-bootstrap confidence intervals for excess CAGR versus BTC. The bootstrap uses 1,000 replications per block length and fixed deterministic seeds.

The runner is connected to the default-branch-only control workflow using the exact command `/qfr-run-eth-btc-spot-momentum` on open control PR #2. The workflow uploads reports and manifests only, never raw market CSVs. Passing CI or synthetic tests is not evidence of profitability; a GO remains research-only.

## Important caveats

1. The default fee, slippage and spread values are scenario assumptions, not verified current account rates. Replace them with venue- and account-specific values.
2. Spot short-leg results are theoretical unless margin borrowing is available and its actual borrow costs are entered.
3. USDⓈ-M perps are used as two separate linear contracts, not as an ETHBTC perpetual. Funding intervals can change; when a validated event series is accepted, the pipeline uses each event timestamp rather than assuming a fixed 8-hour schedule. The current Binance Vision archive source remains provisional and is rejected by the empirical gate until settlement-population semantics are independently verified.
4. The pipeline uses 1x gross exposure and does not simulate exchange liquidation engines, order-book queue position, partial fills or outages. It includes illustrative one-bar shock scenarios, not a full margin simulator.
5. Hourly OHLCV is not a historical order book. The spread/slippage inputs are proxies, not measured historical bid/ask execution costs.
6. Inspect data-quality JSON and CSV outputs before interpreting statistics. Do not treat a significant cointegration test as evidence of a profitable net trading edge.

## Pre-dispatch metric/reporting audit (CI validated)

The metric audit corrections were merged in `305bf5c70a14d8a8167dbbd4a22ec95f775402f7`; CI run `44929403565` passed all 17 deterministic tests and the synthetic smoke test. The full-data study remains separate and unverified.

- Sortino uses the root-mean-square downside deviation relative to the 0% minimum acceptable return, computed over all observations (including zero downside for non-negative returns).
- Maximum drawdown includes initial NAV = 1.0 in the peak path, so a loss on the first realized bar is captured.
- Average gross exposure is calculated from the weights held during the return interval, aligned with the lagged weights used for PnL.
- Funding stress is reported only for USDⓈ-M results. The hypothetical scenario assumes both contracts receive a +10 bp funding rate at each of three settlements (+0.30% per leg in total); it is not observed funding data.
- The Sharpe percentile bootstrap remains at 150 replications. Its 95% interval is explicitly marked **exploratory**, with limited quantile precision; this count was retained rather than silently treated as high-precision inference.


## Irregular Spot observations and event-time backtests

The Spot pipeline may contain missing hourly candles only when both ETHUSDT and BTCUSDT have synchronized, provenance-complete gap inventories and every missing hour is classified as confirmed_no_trade_interval using checksum-verified daily aggregate-trade archives plus same-day positive controls. validate_spot_event_time_evidence binds the exact price CSV checksum to both manifests and fails closed on any mismatch, trade evidence, unverified archive, unsynchronized gap or missing manifest. It never creates candles or forward-fills prices.

When the validated Spot hourly grid is irregular, walk_forward_event_time uses calendar-time rolling features, next-observed-open execution, actual elapsed holding and borrow costs, event-time benchmarks, and continuous-time annualization. Daily Spot bars also use this engine if an entire UTC day is absent. Equal-spacing ADF/KPSS/cointegration lag diagnostics are skipped and labelled for irregular samples. The output metric columns continuous_time_sharpe and continuous_time_sortino are intentionally distinct from the regular-period Sharpe/Sortino fields; do not compare them as if they were calculated by the same estimator.

This event-time acceptance applies only to Spot price observations. It does not establish USD-M funding completeness or permit a combined/perpetual backtest. The default Spot short-borrow charge remains an illustrative assumption unless a feasible historical borrow source is independently verified.
