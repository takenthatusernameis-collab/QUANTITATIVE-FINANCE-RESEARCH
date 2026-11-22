# ETH/BTC mean-reversion research pipeline


**Repository-wide operating rules:** follow the [General Antifragile Autonomous Operating Mindset](../docs/GENERAL-ANTIFRAGILE-AUTONOMOUS-OPERATING-MINDSET.md), [Adaptive Execution Standard](../docs/ADAPTIVE-AUTONOMOUS-RESEARCH-EXECUTION.md), and [Repository Hygiene preflight](../docs/REPOSITORY-HYGIENE-AND-CONTEXT-COMPACTION.md). The single current task pointer is [tasks/ACTIVE-QUEUE.md](../tasks/ACTIVE-QUEUE.md).

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

## Research design

- Signal: completed-bar close; execution: next bar open; PnL: open-to-open.
- Fixed spread: `log(ETHUSDT) - log(BTCUSDT)`.
- Dynamic spread: `log(ETHUSDT) - alpha - beta*log(BTCUSDT)`, with trailing 30-day OLS parameters refreshed once daily from prior observations.
- Entry/exit/stop: absolute z-score 2.0 / 0.5 / 4.0; maximum holding period seven days.
- Walk-forward: 730 calendar days of trailing training data followed by non-overlapping 90-day test folds. No parameter optimization is performed; thresholds are pre-specified.
- Position sizing: spread-hedge neutrality, not dollar neutrality. The two leg weights are normalized to 1x gross exposure using the estimated log-price hedge ratio. A close signal is shifted one bar and executed at the next bar open.
- Costs: fees, slippage and spread are configurable per leg per side; 1.0x, 1.5x and 2.0x cost cases are reported. USDⓈ-M funding is charged at observed settlement timestamps. Spot borrow can be configured with `--spot-borrow-bps-per-day`.
- Daily robustness resamples OHLC data and uses next-day-open execution. It is price-only: funding is not applied to the daily robustness run. Sharpe and Sortino use a 0% risk-free hurdle; annualization is 8,760 hourly or 365 daily periods.

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
