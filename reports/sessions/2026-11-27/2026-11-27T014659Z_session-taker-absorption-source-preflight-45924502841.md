# Taker-flow/price-response source preflight — 2026-11-27

**Status: PASS — source feasibility only; no model/backtest executed.**

- Hypothesis: QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01
- Workflow run: [45925248340](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45924502841)
- Source-preflight code commit: 6f91629a1f3b5003da516ae1829de1fadf8a0530
- Retrieval time: 2026-11-27T01:54:42Z
- Official source: Binance Vision BTCUSDT Spot 1d UTC monthly/daily klines and .CHECKSUM sidecars.
- Verified archives: **136**
- Verified observations: **3,388**
- Complete coverage: **2017-08-17 to 2026-11-25**
- Missing dates: **0**
- Zero-volume dates: **0**
- Finite taker-flow observations: **3,388**
- Taker imbalance range: **-0.650991 to +0.621599**; median **-0.008361**
- Archive-manifest SHA-256: 978b00dda884620e6e19cfb32f42bbf93df1f1a19d5d0a906951e23762440bbe

The latest requested date, 2026-11-26, returned HTTP 404. The bounded publication-lag probe then verified the 2026-11-25 daily archive and its checksum. The selected research sample is therefore frozen through November 25, not extended by assumption.

The parser validated the 12-column daily kline schema, OHLC relationships, base/quote volume bounds, integer trade counts, complete UTC candles and both millisecond and microsecond timestamp encodings. Boundary-month rows outside the requested sample are clipped before coverage reconciliation.

**Interpretation:** source feasibility is established for this sample and field definition. The source is venue-specific and the daily flow/price interaction is only a proxy for passive-liquidity absorption. No empirical forecast result exists yet.
