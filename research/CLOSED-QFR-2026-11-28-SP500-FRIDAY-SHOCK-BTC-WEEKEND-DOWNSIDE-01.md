# Closure — QFR-2026-11-28-SP500-FRIDAY-SHOCK-BTC-WEEKEND-DOWNSIDE-01

**Disposition: CLOSED — INCONCLUSIVE/INFEASIBLE (source feasibility).**  
**Closure timestamp:** 2026-11-28T10:15:17Z.  
**Research-performance conclusion:** NONE. No model was fitted and no backtest was run.

## Frozen hypothesis and timebox

A negative Friday S&P 500 close-to-close return may add information about BTC downside semivariance during the following Saturday 12:00–Sunday 12:00 UTC window beyond BTC's prior 24h/168h downside risk, 168h realized variance and prior 24h absolute return.

The frozen source design used FRED daily SP500 and checksum-verified Binance Vision BTCUSDT Spot 1h UTC archives. The HIGH-difficulty timebox allowed at most eight substantive cycles, with implementation deadline 2026-11-30T07:46:26Z and final conclusion deadline 2026-12-08T07:46:26Z. The attempt closed early after the frozen source gate remained materially failed following the authorized same-source daily-archive recovery. No deadline extension or clock reset occurred.

## Verified source evidence

### FRED SP500
- 2,331 positive, finite, unique daily observations, 2017-08-18 through 2026-11-25.
- Source coverage and freshness gates passed.
- FRED provides daily observation dates but not historical intraday first-publication timestamps or vintages for this series. The 15–16 hour post-close embargo does not certify exact historical availability.

### Binance BTCUSDT hourly archives
- Required window: 81,204 UTC hours.
- Primary monthly/latest-month daily archives: 81,033 observed hours; 171 affected/missing hours (0.21058%); maximum consecutive affected run 75 hours.
- The 44 malformed primary-archive rows were confirmed to affect 44 distinct in-window UTC hours; no rounding, interpolation or synthetic candle insertion was used.
- Gap-specific, checksum-verified official Binance daily archives recovered 43 exact missing hours.
- Final post-recovery coverage remained at 129 affected/missing hours (0.158859%) and a maximum consecutive gap of 33 hours.
- One exact-close conflict remained at **2020-12-21T13:00:00Z**: monthly archive close **22,646.53**, daily archive close **22,681.32**. Both files and CHECKSUM sidecars were verified. The conflicting hour was removed from trusted coverage; neither value was selected, averaged or overwritten.
- Final source-only run [#46126649110](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46126649110); manifest [artifact 15255678201](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46126649110/artifacts/15255678201).

## Frozen gate and result

The preregistered limits were no more than 24 missing/affected hours, no more than 0.05% effective missingness, no more than four consecutive affected hours, and no conflicting overlapping closes.

The final source gate failed all three coverage limits (129, 0.158859%, 33) and the conflicting-close gate (one conflict). Event feasibility passed with 91 eligible validation forecasts and 246 eligible test forecasts after 104 matured weekly training events. Sample sufficiency cannot override source integrity.

The final run's deterministic parser/timestamp/archive/event-feasibility tests passed. After closure, the workflow was retired (push trigger removed and job disabled), and both the Python `run_preflight()` function and CLI entrypoint were given a fail-closed guard. Parser tests remain available without source retrieval. The networked source step produced a diagnostic manifest and failed the unchanged data acceptance gate. No raw market observations were committed. No model fit, empirical backtest, performance metric, or strategy decision exists.

## Recovery disposition

The official daily-archive gap-specific recovery was a materially different invocation of the same official Binance Vision source and recovered 43 hours. It did not bring the source within limits and revealed a conflicting close. Stop this route; do not repeat it unchanged.

Do not relax the frozen thresholds, choose one conflicting archive close, average closes, round timestamps, interpolate or synthesize missing candles, treat event sufficiency as source validity, or call the result a performance NO-GO.

Any materially different source/market construction must be separately justified and preregistered with a new identity and timebox before implementation. A venue-only substitution does not automatically create a materially distinct research hypothesis or qualify for the daily research KPI.

## Daily KPI and next action

The 2026-11-28 daily real-data backtest minimum was already met by the separate MEXC funding-dispersion / BTC realized-variance backtest [#46085887442](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085887442). This source-only preflight and closure do not count as another backtest.

Close this identity permanently. The next agent should select a materially distinct mechanism, check prior registry/literature and data feasibility, then freeze a difficulty-adjusted timebox before any substantive implementation.
