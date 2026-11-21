# Pending Research Task: ETH/BTC Market-Neutral Mean Reversion

**Status:** Executed — INCONCLUSIVE (2026-11-21)  
**Priority:** High  
**Type:** Empirical quantitative research  
**Scope:** Research and backtesting only; do not deploy capital or place live orders.

## 1. Objective

Determine whether an ETH/BTC relative-value mean-reversion strategy can deliver a durable, risk-adjusted return after realistic trading costs, and whether its behaviour changes as the ETH/BTC market matures and volatility declines.

Do not assume that ETH and BTC are cointegrated, that the spread is stationary, or that lower volatility improves profitability. Test those propositions out of sample.

## 2. Hypotheses to test

1. ETH and BTC prices may exhibit a sufficiently stable long-run relationship to support a market-neutral spread strategy.
2. A dynamically estimated hedge ratio may improve neutrality or robustness relative to a fixed 1:1 ETH/BTC ratio.
3. Lower-volatility regimes may reduce spread excursions and gross opportunity, while potentially improving signal stability; the net effect after fees, slippage and funding is unknown.
4. Any apparent edge may decay after realistic costs, parameter selection, or regime changes.

Report evidence for and against each hypothesis.

## 3. Data requirements

- Obtain synchronized ETH and BTC spot and, where available, perpetual-futures data.
- Prefer hourly observations for the primary study; include daily data as a robustness check.
- Include OHLCV, timestamps, exchange trading fees, bid/ask or spread proxies, and perpetual funding rates. Include borrow costs if the implementation requires borrowing.
- Use at least one sufficiently long history spanning materially different volatility and market regimes. Document venue, instruments, timezone, missing observations, survivorship/data-quality issues and the exact sample period.
- Do not fabricate missing data. If full cost or funding history is unavailable, disclose the limitation and run conservative cost sensitivities.

## 4. Research and strategy specification

### A. Relationship diagnostics

- Test log-price relationships using Engle–Granger and, where appropriate, Johansen cointegration tests.
- Test spread stationarity using ADF and KPSS; report p-values, test assumptions and rolling-window stability.
- Compare a fixed unit hedge ratio (log ETH minus log BTC) with a rolling or expanding-window estimated hedge ratio.
- Estimate spread half-life and examine structural breaks, parameter drift and periods in which the relationship ceases to be stationary.
- Avoid using full-sample estimates to generate historical signals.

### B. Trading rules

Build a transparent baseline z-score strategy on the training-window spread:
- Enter when the absolute spread z-score crosses a pre-specified threshold.
- Exit on mean reversion to a pre-specified level; define stop-loss, maximum holding period and handling of failed convergence.
- Size both legs to target market neutrality and state whether neutrality means dollar neutrality, beta neutrality or spread-hedge neutrality.
- Evaluate both long-spread and short-spread trades, including borrow/funding feasibility.
- Select parameters only on training data. Freeze them for each subsequent out-of-sample test window.

Compare at minimum:
1. Fixed 1:1 ETH/BTC spread.
2. Dynamically estimated hedge-ratio spread.
3. A no-trade benchmark.

### C. Volatility and market-maturity analysis

- Define volatility regimes using information available at the time (for example, trailing realized volatility quantiles).
- Compare gross and net returns, trade frequency, spread half-life, drawdowns and cost burden across regimes.
- Test whether falling volatility reduces opportunity or improves risk-adjusted performance after costs.
- Discuss market capitalization/liquidity growth only where supported by measured data; do not treat market-cap growth as proof of stronger cointegration.

## 5. Validation and implementation realism

- Use chronological train/validation/test splits and rolling walk-forward evaluation. Prevent look-ahead, survivorship and parameter-selection leakage.
- Report results by test fold and regime, not just as one aggregate backtest.
- Deduct commissions, bid/ask spread, slippage and funding/borrow costs on every applicable leg. Include conservative cost scenarios at 1.0x, 1.5x and 2.0x estimated costs.
- Model simultaneous leg execution, position sizing, leverage, collateral and liquidation/margin constraints where relevant. Do not assume fills at candle close without justification.
- Stress test sudden spread divergence, volatility spikes, funding shocks, exchange outages and prolonged non-convergence.
- If multiple venues are used, keep venue-specific results separate before any aggregate.

## 6. Benchmarks and metrics

Compare on a clearly stated, comparable capital and exposure basis against:
- BTC buy-and-hold;
- ETH buy-and-hold;
- a static 50/50 ETH-BTC portfolio; and
- passive long ETH/BTC relative performance.

Report gross and net CAGR, annualized volatility, Sharpe, Sortino, maximum drawdown, Calmar, turnover, exposure, average holding period, trade count, win rate, profit factor, tail losses and capital utilization. State the risk-free-rate assumption and annualization convention. Include confidence intervals or bootstrap uncertainty where feasible.

## 7. Deliverables

1. Reproducible research code with a clear environment/dependency file and documented data inputs.
2. A concise research report explaining methodology, assumptions, results, limitations and a clear **GO / NO-GO / INCONCLUSIVE** conclusion.
3. Charts for the price relationship, spread and rolling z-score, hedge ratio, rolling performance, drawdowns, volatility-regime results and cost sensitivity.
4. A machine-readable summary of out-of-sample results by fold, strategy variant and regime.
5. A short section identifying what additional data or tests would most change the conclusion.

## 8. Acceptance criteria

The task is complete only when:
- the spread and hedge-ratio construction are mathematically documented;
- all reported strategy performance is out of sample and net of stated costs;
- results are reproducible from the committed code and documented inputs;
- both favourable and unfavourable regimes are analysed;
- the report distinguishes statistical evidence of cointegration from evidence of a tradable net edge; and
- the final conclusion is supported by the reported diagnostics and sensitivity tests.

Do not declare success solely because a full-sample backtest is profitable, a cointegration test is significant, or a single Sharpe ratio is high. If the data are insufficient to support a reliable conclusion, classify the result as **INCONCLUSIVE** rather than filling gaps with assumptions.

## Execution record — 2026-11-21

- Outcome: **INCONCLUSIVE**. No empirical market statistics are claimed because raw historical data and funding history could not be retrieved in this execution environment.
- Added: `research/run_eth_btc.py`, `research/requirements.txt`, and `research/README.md`.
- Report: `reports/ETH-BTC-MEAN-REVERSION-2026-11-21.md`.
- Validation: syntax check, synthetic self-test and synthetic daily integration run passed. These checks validate plumbing only, not strategy performance.
- Follow-up: `tasks/ETH-BTC-FULL-DATA-EXECUTION.md` requests the network-enabled empirical run and final conclusion.
