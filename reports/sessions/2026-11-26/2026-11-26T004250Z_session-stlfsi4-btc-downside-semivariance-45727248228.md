# Research session — STLFSI4 and BTC downside semivariance (2026-11-26T00:42:50.558131+00:00)

- **Hypothesis:** QFR-2026-11-26-STLFSI4-BTC-DOWNSIDE-SEMIVARIANCE-01
- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE — bounded source/execution failure: RuntimeError: Binance public-data endpoints failed: https://data-api.binance.vision: ValueError: BTCUSDT candle is not aligned to a full UTC day | https://api.binance.com: RuntimeError: Non-retryable HTTP 451 for https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT
- **Daily KPI:** 2026-11-25 minimum was already MET by earlier experiments; this run on 2026-11-26 did not complete a valid backtest.
- **GitHub run:** 45727248228, attempt 1
- **Triggering commit:** ef686c4b2e651c24ef853d4bcf64e9063736c2ea

## Blocker

- RuntimeError: Binance public-data endpoints failed: https://data-api.binance.vision: ValueError: BTCUSDT candle is not aligned to a full UTC day | https://api.binance.com: RuntimeError: Non-retryable HTTP 451 for https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT
- No valid empirical backtest completed; this run does not count toward the daily minimum.

