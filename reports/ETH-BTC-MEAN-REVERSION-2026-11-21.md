# ETH/BTC market-neutral mean-reversion — execution report

**Execution date:** 2026-11-21  
**Conclusion:** **INCONCLUSIVE — empirical run blocked by data access**  
**Scope:** Research only; no live trading or capital deployment

## Executive finding

The pending research task was reviewed and a reproducible research pipeline was added. The pipeline passed a Python syntax check and a synthetic plumbing self-test. A synthetic daily integration run also exercised the walk-forward loop, diagnostics, CSV exports, charts and stress-scenario output. However, this execution environment could not retrieve the historical market-data files needed for a valid empirical run. Therefore, no cointegration p-values, half-life estimates, out-of-sample returns, Sharpe/Sortino ratios, drawdowns, trade counts, funding contributions or cost-adjusted results are reported here.

This is not a NO-GO result for the strategy. It is an **INCONCLUSIVE** result because the data prerequisite was not satisfied. No synthetic or guessed prices were substituted for market observations. Synthetic outputs were kept outside the repository and are not research evidence.

## Data-access investigation

The intended sample is 2020-01-01 through 2026-10-31, using synchronized hourly Binance Spot and USDⓈ-M perpetual ETHUSDT and BTCUSDT bars, plus settled funding events. The last complete month is used to avoid partial-month archives.

The official [Binance Public Data repository](https://github.com/binance/binance-public-data) documents downloadable daily/monthly market-data archives, including 1-hour klines, and notes a spot timestamp-unit change from milliseconds to microseconds beginning 2025-01-01. The [Binance Spot REST documentation](https://developers.binance.com/en/docs/products/spot/rest-api) describes chronological pagination for public market data. The USDⓈ-M [funding-rate history endpoint](https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) exposes `fundingTime` and `fundingRate`, accepts time bounds, returns ascending records, and caps each request at 1,000 events.

Attempts to acquire the archive from this run failed because outbound DNS/network access from the execution container was unavailable. The web reader could not open the binary archive. A public GitHub repository lists a 1,145,319-byte `Binance_ETHBTC_1h.csv`, but the connected GitHub file reader returned an empty body for that large file and the raw-file fetch was rejected as too large. Consequently, no usable raw price file or funding history was available for computation.

## Research specification implemented

The added pipeline is `research/run_eth_btc.py`; dependencies are in `research/requirements.txt`; operating instructions and caveats are in `research/README.md`. It records per-archive SHA-256 values, whether Binance checksum sidecars were verified, row counts and timestamp units, plus consolidated CSV hashes and funding CSV hashes in data-quality manifests.

- **Price relationship:** fixed spread `log(ETHUSDT) - log(BTCUSDT)`; dynamic spread `log(ETHUSDT) - alpha - beta*log(BTCUSDT)`, with trailing 30-day OLS parameters refreshed once daily using only prior observations.
- **Diagnostics:** Engle–Granger, ADF, KPSS, Johansen trace, Zivot–Andrews, AR(1)-based half-life and rolling 180-day cointegration windows.
- **Trading rule:** pre-specified entry/exit/stop z-scores of 2.0 / 0.5 / 4.0; seven-day maximum holding period; no parameter optimization. Signal is generated at the completed-bar close, execution is at the next bar open, and returns are open-to-open.
- **Walk-forward:** trailing 730-day training windows and non-overlapping 90-day out-of-sample folds. Positions are reset at each test fold and liquidated at the final test open.
- **Hedge construction:** spread-hedge neutrality, not dollar neutrality. Leg weights are normalized to 1x gross exposure using the estimated log-price hedge ratio. The dynamic-beta strategy can therefore carry non-zero net dollar exposure.
- **Costs:** configurable per-leg, per-side fees, slippage and spread assumptions, with 1.0x / 1.5x / 2.0x sensitivities. USDⓈ-M funding is charged at observed settlement timestamps. Optional spot borrow cost is configurable; the default is zero and must not be mistaken for a borrow quote.
- **Benchmarks:** BTC buy-and-hold, ETH buy-and-hold, 50/50 ETH-BTC, passive long ETH/short BTC, and no-trade, on a 1x gross-exposure basis with entry and exit costs.
- **Risk outputs:** CAGR, annualized volatility, Sharpe, block-bootstrap Sharpe interval, Sortino, maximum drawdown, Calmar, turnover, exposure, time in market, trade count, win rate, profit factor, holding period and 1% hourly/daily tail return.
- **Regimes and stress:** trailing 30-day relative-volatility terciles, 1.0x / 1.5x / 2.0x cost sensitivity and illustrative instantaneous spread-divergence/funding shocks.
- **Daily robustness:** daily resampling is included, but the daily run is price-only and does not apply funding. It must not replace the hourly funding-aware perpetual result.

## Implementation checks completed

- `python -m py_compile research/run_eth_btc.py` — passed.
- `python research/run_eth_btc.py --self-test` — passed. The self-test uses generated synthetic prices only to check feature generation, the position state machine, turnover/cost arithmetic and finite PnL outputs. It does not validate strategy performance or statistical hypotheses.
- A synthetic daily integration run exercised the walk-forward loop, statistical diagnostics, CSV exports, charts and stress-scenario output. It produced the expected artifact set. Those synthetic outputs were kept outside the repository and are not research evidence.

## Material limitations still open

1. No real market data were loaded, so none of the hypotheses has been empirically tested.
2. No historical order-book/bid-ask series was available. The pipeline's default spread and slippage are scenario inputs, not measured fills.
3. Default fee inputs (Spot 10 bps, USDⓈ-M 5 bps, slippage 2 bps, spread 1 bp per leg per side) are illustrative assumptions, not a verified account fee schedule. Replace them with current venue/account-specific values before relying on net results.
4. Spot shorting requires margin borrow; no historical borrow-rate series was acquired. Spot short-spread results are theoretical unless actual borrow feasibility and costs are supplied.
5. The futures implementation uses separate ETHUSDT and BTCUSDT USDⓈ-M contracts, not an ETHBTC perpetual. Funding is applied at observed timestamps, but the backtest does not model mark-price liquidation, exchange outages, partial fills, order-book queue position or portfolio margin. Exposure is capped at 1x gross with no leverage.
6. The daily robustness run omits funding and is not a fully costed perpetual backtest.

## What would change the conclusion

The decisive next step is to run the committed pipeline in a network-enabled environment, verify all archive checksums and hourly continuity, obtain account-specific fee/borrow inputs and a defensible spread/slippage proxy, and inspect the resulting out-of-sample fold/regime tables. A tradable edge would require stable out-of-sample diagnostics and positive net performance after those costs, not merely a significant full-sample cointegration test.

**Status:** The research task was executed as far as the available data access permitted and is recorded as **INCONCLUSIVE**. The follow-up task requests the missing network-enabled empirical run.
