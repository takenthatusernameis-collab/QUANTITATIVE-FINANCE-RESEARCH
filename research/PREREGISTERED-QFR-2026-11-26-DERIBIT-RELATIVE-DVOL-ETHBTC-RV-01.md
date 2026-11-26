# Preregistration — relative Deribit DVOL pricing and ETH/BTC realized volatility

- **Hypothesis ID:** QFR-2026-11-26-DERIBIT-RELATIVE-DVOL-ETHBTC-RV-01
- **Registered:** 2026-11-26T13:35:00Z, before implementation and empirical-result inspection.
- **Initial status:** PREREGISTERED.
- **Difficulty:** MEDIUM.
- **Difficulty rationale:** the Deribit public DVOL endpoint is documented, but its BTC/ETH history, pagination and numeric scale require live verification. The study also requires two synchronized Coinbase price series, strict cross-venue time alignment, a new relative-volatility target, walk-forward tests, an admission-gated workflow and evidence persistence. Existing repository helpers cover CSV parsing, standardized OLS and block bootstrap, reducing but not eliminating implementation work.
- **Timebox start:** 2026-11-26T13:35:00Z.
- **Maximum substantive cycles:** 4 total.
- **Hard implementation deadline:** 2026-11-29T13:35:00Z.
- **Hard final research-conclusion deadline:** 2026-12-01T13:35:00Z.
- **Expiry rule:** the earlier of four substantive cycles or the five-calendar-day limit governs. If source acceptance, implementation or the complete frozen backtest remains unresolved at its applicable deadline, close INCONCLUSIVE/INFEASIBLE with the exact blocker. No automatic extension, silent clock reset, relaxed coverage, weakened sample size or same-ID retuning. A materially changed source, feature, lag, target, market or model requires a new identity and preregistration.

## Research question and falsifiable claim

Does the latest strictly prior common-date log ratio of Deribit ETH DVOL to BTC DVOL add chronological out-of-sample information about the next seven daily observations' relative realized volatility, beyond each asset's own recent realized volatility?

The target is the log ratio of annualized next-seven-observation ETH realized volatility to BTC realized volatility. The proposed feature is the log ratio of ETH DVOL to BTC DVOL, measured on the latest common Deribit daily-candle date strictly earlier than the Coinbase signal date.

The mechanism is **cross-asset options-implied relative risk pricing**. If the options market prices ETH's forward volatility differently from BTC's, that relative price may contain information about subsequent relative realized volatility not already present in each asset's recent realized volatility. This is a risk-forecasting hypothesis, not a directional ETH/BTC return forecast.

## Novelty and literature boundary

This is materially distinct from the repository's macro, CFTC positioning, and VXN/VIX screens. The signal comes from the relative pricing of two cryptocurrency options markets and the target is relative ETH/BTC realized volatility, rather than a single-asset return or volatility level. It is not a parameter variation of the earlier BTC macro or CFTC experiments.

- Chevallier and Sanhaji (2023), “Jump-Robust Realized-GARCH-MIDAS-X Estimators for Bitcoin and Ethereum Volatility Indices,” *Stats* 6(4), 1339–1370, DOI https://doi.org/10.3390/stats6040082. Their study finds that 30-day implied-volatility indices can improve separate BTC and ETH realized-volatility forecasts. This study does not claim that result is new; it tests a relative ETH/BTC DVOL feature against a joint cross-asset baseline.
- Hoang and Baur (2020), “Forecasting bitcoin volatility: evidence from the options market,” *Journal of Futures Markets* 40(10), 1584–1602, DOI https://doi.org/10.1002/fut.22144. Their results differ by forecast horizon and motivate explicit reporting of the 30-day implied versus seven-day realized horizon mismatch.
- Deribit introduced its BTC DVOL index on 2021-03-31 and describes it as a 30-day annualized implied-volatility measure: https://insights.deribit.com/exchange-updates/deribit-launches-volatility-index/.
- The 2023 Chevallier and Sanhaji study reports Deribit BTC and ETH volatility indices available from 2023-03-26. This defines the conservative common-history start, not an assumption of complete API retention.
- Deribit's official public API documents BTC and ETH currency parameters, millisecond start/end timestamps, daily resolution 1D, OHLC candle arrays and a continuation cursor: https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data.

No first-in-literature claim is made.

## Data feasibility and source-acceptance gates

### Deribit BTC and ETH DVOL

- Endpoint: https://www.deribit.com/api/v2/public/get_volatility_index_data.
- Official method: HTTP GET public/get_volatility_index_data with the documented query parameters; the response uses a JSON-RPC 2.0 envelope.
- Required parameters: currency BTC or ETH; start_timestamp and end_timestamp in Unix milliseconds; resolution 1D.
- Required response: daily OHLC candle arrays with UTC-midnight timestamps and a continuation cursor used as the next request's end_timestamp.
- Retrieve both currencies from 2023-03-26 through the last fully completed UTC daily candle. Follow continuation cursors with strict backward-progress checks, bounded retries and a maximum of ten pages. Deduplicate identical boundary candles; reject conflicting duplicates, out-of-range timestamps, non-daily timestamps, invalid OHLC values or non-progressing cursors.
- Require at least 1,200 rows per currency, first date no later than 2023-04-02, latest date no more than two calendar days stale, no future dates and no daily gap greater than two days. Require at least 1,200 common BTC/ETH dates.
- Preserve exact request/response hashes, page cursors, row counts, date coverage and numeric-scale normalization. Do not commit raw API response bodies.
- The endpoint's raw numeric scale must be detected consistently for BTC and ETH. Normalize both series to percentage points only after validating that both have the same scale; reject ambiguous or inconsistent scales.

### Coinbase BTCUSD and ETHUSD

- FRED series CBBTCUSD and CBETHUSD: https://fred.stlouisfed.org/series/CBBTCUSD and https://fred.stlouisfed.org/series/CBETHUSD.
- Public CSV route: https://fred.stlouisfed.org/graph/fredgraph.csv?id=CBBTCUSD&cosd=2023-03-26 and the corresponding CBETHUSD route.
- Both series are daily, seven days per week, and represent Coinbase prices as of 5 p.m. Pacific Time. They are copyrighted; raw observations must not be committed or redistributed.
- Require at least 1,200 observations per series, first date no later than 2023-04-02, latest date no more than three calendar days stale, no future dates and no calendar gap greater than one day in the accepted common price calendar.
- Use the common BTC/ETH price-date intersection. Never forward-fill, interpolate, or bridge a missing daily return. Require at least 1,200 common daily observations.

## Frozen signal, feature and target

- **Signal date:** Coinbase BTCUSD and ETHUSD daily close on date t.
- **Options feature:** latest common BTC/ETH Deribit 1D DVOL candle whose UTC candle date is strictly earlier than t. The same date must be used for both currencies; maximum age is two calendar days.
- **Relative options feature:** log(ETH_DVOL[d] / BTC_DVOL[d]).
- **Baseline features:** log annualized trailing seven-observation BTC realized volatility; log annualized trailing thirty-observation BTC realized volatility; the same two features for ETH.
- **Augmented model:** baseline features plus the relative-DVOL log ratio. No other feature, threshold or interaction is permitted under this hypothesis ID.
- **Target:** log(annualized next-seven-observation ETH realized volatility / annualized next-seven-observation BTC realized volatility). Daily realized variance is the sum of squared close-to-close log returns; annualization uses 365 calendar days.
- **Event spacing:** seven common price observations. Target windows do not overlap. Because the preceding target ends on the next signal date, the frozen training-maturity rule excludes that immediately preceding event: every training target must end strictly before the current signal date.
- **Missingness:** every pre-history and target return must be present. Any incomplete event is skipped and counted; no imputation or calendar bridging.

## Walk-forward model and evaluation

- Baseline and augmented forecasts use the repository's standardized, ridge-stabilized OLS predictor. All feature scaling and coefficient estimation use training observations only.
- Rolling training window: 52 prior events whose target end is strictly earlier than the current signal date.
- Validation: signal dates 2024-04-01 through 2024-12-31.
- Test: signal dates 2025-01-01 onward.
- Minimum sample: at least 30 forecasts in both validation and test. If the frozen source start and warm-up do not yield this, close INCONCLUSIVE/INFEASIBLE; do not move the split or shorten the training window after inspecting results.
- Primary metric: RMSE in log-relative-realized-volatility space. MAE and out-of-sample R-squared versus the period mean are descriptive.
- Paired test squared-loss uncertainty: 2,000 deterministic circular-block bootstrap replications, block length four events, seed 20261126.

## Frozen decision rule

- **BACKTESTED / PROMISING FORECAST SCREEN:** at least 30 validation and 30 test forecasts; augmented RMSE improves in both chronological periods; and the paired test squared-loss 95% lower confidence bound is strictly above zero.
- **REJECTED:** augmented RMSE fails to improve in both periods and the paired test squared-loss 95% upper confidence bound is strictly below zero.
- **INCONCLUSIVE:** every other outcome, including mixed RMSE, confidence intervals crossing zero, insufficient samples, stale sources, incomplete history, API schema/cadence changes or execution failure.
- A BACKTESTED result remains a forecast-only screen. It is not independent validation or a trading strategy.

## Limitations and safety

- Deribit DVOL is a 30-day forward implied-volatility index while the target is seven-day realized volatility. The horizon mismatch is explicit and is not interpreted as a perfectly matched variance-swap forecast.
- Deribit is one options venue; its index is not a consolidated global options surface.
- Coinbase daily prices are a single venue's 5 p.m. Pacific reference closes, not executable consolidated prices.
- The conservative strictly-prior UTC-date rule avoids same-date timing ambiguity but can add a lag to the options feature.
- FRED current-vintage observations are used; historical point-in-time revisions are not reconstructed.
- Daily close-to-close realized volatility does not capture intraday jumps or microstructure effects.
- No directional-return, causal, hedge, portfolio, executable P&L, transaction-cost, profitability or live-deployment claim is authorized.
- Do not assign CAGR, Sharpe, Sortino, Calmar or drawdown to this forecast-only result.

## Empirical disposition

- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — the frozen chronological and paired-loss criteria do not establish incremental predictive value or decisive inferiority
- **Completed real-data backtest:** True
- **Run:** 45834522305, attempt 1; source commit 363211845204dd130b5402b9d3aea794c0a0387d
- **Data coverage:** {"BTC_DVOL": {"first_date": "2023-03-26", "last_date": "2026-11-25", "maximum_calendar_gap_days": 1, "rows": 1341}, "CBBTCUSD": {"first_date": "2023-03-26", "last_date": "2026-11-25", "maximum_calendar_gap_days": 1, "rows": 1341}, "CBETHUSD": {"first_date": "2023-03-26", "last_date": "2026-11-25", "maximum_calendar_gap_days": 1, "rows": 1341}, "COMMON": {"dvol_first_date": "2023-03-26", "dvol_last_date": "2026-11-25", "dvol_rows": 1341, "price_first_date": "2023-03-26", "price_last_date": "2026-11-25", "price_rows": 1341}, "ETH_DVOL": {"first_date": "2023-03-26", "last_date": "2026-11-25", "maximum_calendar_gap_days": 1, "rows": 1341}}
- **Validation metrics:** {"augmented": {"mae_log_relative_rv": 0.26755141126745774, "n": 36, "oos_r2_vs_period_mean": -0.1816164755603884, "rmse_log_relative_rv": 0.32422469981225305}, "baseline": {"mae_log_relative_rv": 0.26504821445118926, "n": 36, "oos_r2_vs_period_mean": -0.20262302381766295, "rmse_log_relative_rv": 0.32709400538028977}, "n": 36}
- **Test metrics:** {"augmented": {"mae_log_relative_rv": 0.28227674311208756, "n": 98, "oos_r2_vs_period_mean": -0.2264157190791778, "rmse_log_relative_rv": 0.34670051596092216}, "baseline": {"mae_log_relative_rv": 0.27899681333710113, "n": 98, "oos_r2_vs_period_mean": -0.19178056324770876, "rmse_log_relative_rv": 0.3417698776633235}, "n": 98}
- **RMSE improvement:** validation=0.8772112973152084; test=-1.4426778425616
- **Paired test-loss bootstrap:** {"block_size_events": 4, "bootstrap_fraction_positive": 0.25, "ci95_high": 0.005559075506429804, "ci95_low": -0.013994571829600524, "mean_baseline_minus_augmented_squared_loss": -0.00339459848956659, "observations": 98, "reps": 2000}
- **Report:** [reports/sessions/2026-11-26/2026-11-26T135953Z_session-deribit-relative-dvol-ethbtc-rv-45834522305.md](../reports/sessions/2026-11-26/2026-11-26T135953Z_session-deribit-relative-dvol-ethbtc-rv-45834522305.md)
- **Manifest:** [reports/generated/deribit-relative-dvol-ethbtc-rv/45834522305-attempt-1/manifest.json](../reports/generated/deribit-relative-dvol-ethbtc-rv/45834522305-attempt-1/manifest.json)
