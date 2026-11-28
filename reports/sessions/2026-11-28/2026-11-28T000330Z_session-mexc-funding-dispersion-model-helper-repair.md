# MEXC BTC RV model helper-signature repair

- **Recorded UTC:** 2026-11-28T00:03:55.871Z
- **Hypothesis:** QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01
- **Failed run:** [#46085741045](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085741045)
- **Persisted failure evidence:** [manifest](../reports/generated/mexc-funding-dispersion-btc-rv/46085741045-attempt-1/manifest.json), [session report](../reports/sessions/2026-11-28/2026-11-28T000240Z_session-mexc-funding-dispersion-btc-rv-46085741045.md)

The model workflow installed NumPy, passed all deterministic model and repository admission tests, re-fetched MEXC funding and hourly candles, and matched both frozen canonical source hashes. It then stopped before fitting because the shared helper signature is fit_ols_predict(train, current, feature_names), not the assumed vector/keyword interface.

No model fit, forecast or backtest result was produced. The repair now passes named feature dictionaries and the explicit feature-name list to the existing shared standardized OLS helper. A deterministic test exercises this exact interface. The README result updater was also made robust to the already-updated source-feasibility status line.
