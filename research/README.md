# ETH/BTC mean-reversion research pipeline

## Run

From the repository root, install the dependencies and run:

```bash
python -m pip install -r research/requirements.txt
python research/run_eth_btc.py --start 2020-01-01 --end 2026-10-31 --market both
```

The script downloads monthly 1-hour Binance Spot and USDⓈ-M perpetual klines for `ETHUSDT` and `BTCUSDT`. It separately paginates settled USDⓈ-M funding events for both contracts. Monthly archives are cached under `data/cache/`; consolidated input CSVs and per-archive SHA-256/checksum/timestamp-unit manifests are written under `data/raw/`. Funding CSVs also receive row-count/hash manifests. The run writes data-quality JSON with sample bounds, gaps and source hashes. Generated outputs go to `reports/generated/`. Raw data are not intended to be committed.

Use `--market spot`, `--market um`, or `--market both`. `--self-test` runs a synthetic plumbing test only; it is not evidence of strategy performance.

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
3. USDⓈ-M perps are used as two separate linear contracts, not as an ETHBTC perpetual. Funding intervals can change; the pipeline uses each actual funding event timestamp rather than assuming a fixed 8-hour schedule.
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
