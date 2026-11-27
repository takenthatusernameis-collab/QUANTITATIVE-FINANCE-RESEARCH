# Research session — Treasury/ON RRP drain and BTC downside semivariance (2026-11-27T224315Z)

- **Hypothesis:** QFR-2026-11-27-TREASURY-RRP-DRAIN-BTC-DOWNSIDE-01
- **Status:** INCONCLUSIVE
- **Disposition:** INCONCLUSIVE/INFEASIBLE — bounded source/execution failure: RuntimeError: Both public Binance exchangeInfo endpoints failed: [{"error": "ValueError: expected exactly one BTCUSDT symbol, got 3756", "response_bytes": 18178232, "response_prefix_hex": "7b2274696d657a6f6e65223a22555443222c227365727665", "url": "https://data-api.binance.vision/api/v3/exchangeInfo"}, {"error": "RuntimeError: Non-retryable HTTP 451 for https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT", "response_bytes": 0, "response_prefix_hex": "", "url": "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT"}]
- **Daily KPI:** The 2026-11-27 minimum was already met by distinct real-data screens; this failed source/execution attempt does not count.
- **GitHub run:** 46078321167, attempt 1
- **Triggering commit:** beb4892ff91154f5411b50f2dc3e72529f812104

## Authenticated dispatch provenance

- Source comment: 7229558801
- Control PR: 15
- Authorized actor: takenthatusernameis-collab

## Execution blocker

- RuntimeError: Both public Binance exchangeInfo endpoints failed: [{"error": "ValueError: expected exactly one BTCUSDT symbol, got 3756", "response_bytes": 18178232, "response_prefix_hex": "7b2274696d657a6f6e65223a22555443222c227365727665", "url": "https://data-api.binance.vision/api/v3/exchangeInfo"}, {"error": "RuntimeError: Non-retryable HTTP 451 for https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT", "response_bytes": 0, "response_prefix_hex": "", "url": "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT"}]
- No valid real-data backtest completed in this run; the previously met 2026-11-27 KPI remains independent.


## Final source diagnosis and timebox closure

- The separate FRED WDTGAL and RRPONTSYD CSV requests were retrieved and parsed. Exact common Wednesday observations were constructed, but the coverage gate was not reached.
- The primary Binance data-api exchangeInfo request omitted the required symbol=BTCUSDT query parameter and returned all 3,756 symbols. The fallback filtered endpoint at api.binance.com returned HTTP 451.
- BTC archive ingestion, BTC coverage acceptance, event construction and the forecast model were not reached. There are no validation/test metrics and no performance conclusion.
- This is an implementation failure, not evidence that the Treasury/ON RRP predictor works or fails. The frozen two-cycle budget is exhausted; the hypothesis is closed INCONCLUSIVE/INFEASIBLE. No third attempt is authorized under this hypothesis ID.
