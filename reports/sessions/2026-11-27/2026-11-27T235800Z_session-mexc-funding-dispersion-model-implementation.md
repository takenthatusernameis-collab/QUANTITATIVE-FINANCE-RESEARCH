# MEXC funding-dispersion source feasibility passed; model implementation admitted

- **Recorded UTC:** 2026-11-27T23:58:00Z
- **Hypothesis:** QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01
- **Source-preflight run:** [#46085255885](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085255885)
- **Admission guard run:** [#46085255945](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085255945)
- **Accepted source manifest:** [preflight.json](../reports/generated/mexc-funding-dispersion-source-preflight/46085255885-attempt-1/preflight.json)

## Cycle 1 result — PASS

- Exact enabled BTC_USDT USDT perpetual verified on the documented MEXC REST host `api.mexc.com`.
- Funding history: 1,590 settlements, 530 complete UTC dates, zero incomplete candidate dates; latest complete date 2026-11-26.
- Hourly contract candles: 12,929 of 12,929 expected bars, 100% coverage, zero missing hours, zero duplicate bars.
- Complete event windows: 530; 139 pre-validation warm-up events, 61 validation candidates and 330 test candidates.
- Canonical funding hash: `427f4b141673a6e43108d7033c91494af554c507527e8e51330ac95c0fbafd2f`.
- Canonical hourly-close hash: `b3fc8ef0cd1f695c18499e191294214914eee96d846b70b71c7c83c541c8468e`.
- All deterministic source-preflight tests passed after one code repair. The initial test failure occurred before any MEXC request and produced no empirical result.

## Cycle 2 — implementation

The frozen model and deterministic tests are now admitted. The implementation will re-fetch MEXC data and require exact equality with the accepted canonical hashes before fitting anything. It uses one baseline, one added feature, a 120-event rolling window and the preregistered validation/test split. No parameter tuning or alternate features are allowed.

## Cycle 3 — backtest

The model workflow will run the single preregistered walk-forward backtest after its deterministic tests. No backtest result is claimed until the workflow and persisted forecast rows are inspected.

## Daily KPI

The 2026-11-27 UTC minimum was already met by earlier distinct real-data backtests. This additional study does not change that count. The source preflight itself does not count as a backtest.

## Boundaries

Forecast-only research. No live trading, capital deployment, private endpoints or raw observation persistence.
