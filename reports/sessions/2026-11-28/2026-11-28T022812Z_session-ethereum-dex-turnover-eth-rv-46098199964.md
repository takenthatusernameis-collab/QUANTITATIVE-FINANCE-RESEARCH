# Ethereum DEX turnover / ETH realized variance — 2026-11-28T02:28:12.524243+00:00

- **Hypothesis:** QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01
- **Status:** COMPLETED
- **Decision:** INCONCLUSIVE
- **GitHub run:** 46098199964, attempt 1
- **Source commit:** 024f91ba2e8ec039bc53d9ccd1b3540c3fb4d350
- **Completed real-data backtest:** True

## Frozen method

- Forecast origin: daily 00:00 UTC.
- DEX input: exact daily dates t-8 through t-2; seven-day aggregate Ethereum DEX notional volume divided by mean Ethereum DeFi TVL.
- Baseline: log1p trailing 24-hour RV in bp^2, log1p trailing 168-hour RV in bp^2, and absolute trailing 24-hour cumulative log return in bp.
- Augmented model: baseline plus log1p of the frozen seven-day DEX-turnover ratio.
- Target: log1p of next-24-hour ETHUSDT Spot realized variance in bp^2.
- Standardized rolling OLS; at most 252 strictly matured prior daily events, minimum 180; fixed ridge stabilization 1e-8.
- Validation: 2023-01-01 through 2024-12-31. Test: 2025-01-01 through 2026-10-31.
- Paired test-loss circular block bootstrap: 2,000 replications, seven daily events per block, seed 20261128.

## Source provenance

{
  "binance_market": {
    "base_asset": "ETH",
    "endpoint": "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=ETHUSDT",
    "quote_asset": "USDT",
    "response_sha256_refetched": "d75edb355605e42b996fe63a21e7b09265ad3dfd7accfe4a0c08b5bc64276b07",
    "spot_trading_allowed": true,
    "status": "TRADING",
    "symbol": "ETHUSDT"
  },
  "dex": {
    "canonical_daily_sha256": "8fdf8625a388b619d4426791f14a78bbb6bb3820ee535aa60cbd82a67c8e0696",
    "endpoint": "https://api.llama.fi/overview/dexs/ethereum?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume",
    "first_date": "2021-01-01",
    "last_date": "2026-10-29",
    "maximum_gap_days": 1,
    "maximum_value": 11078329937.0,
    "minimum_required_last_date": "2026-10-29",
    "minimum_value": 317420815.0,
    "response_sha256_at_preflight": "5f501c5c28c67f20b898b1780e395f11d9a265e90299bd85f5c870e62a566d19",
    "response_sha256_refetched": "5f501c5c28c67f20b898b1780e395f11d9a265e90299bd85f5c870e62a566d19",
    "rows_in_frozen_window": 2128
  },
  "hourly_klines": {
    "canonical_close_sha256": "64b2b592fe094ed576ec8582fe788d146293afabc2274bbb83650d0cd34c5a6c",
    "coverage_ratio": 0.9997261345852895,
    "daily_gap_repair_archive_count": 7,
    "daily_gap_repairs": [
      {
        "daily_missing_hours": [
          "2021-02-11T04:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 23,
        "period": "2021-02-11"
      },
      {
        "daily_missing_hours": [
          "2021-03-06T02:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 23,
        "period": "2021-03-06"
      },
      {
        "daily_missing_hours": [
          "2021-04-20T02:00:00+00:00",
          "2021-04-20T03:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 22,
        "period": "2021-04-20"
      },
      {
        "daily_missing_hours": [
          "2021-04-25T05:00:00+00:00",
          "2021-04-25T06:00:00+00:00",
          "2021-04-25T07:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 21,
        "period": "2021-04-25"
      },
      {
        "daily_missing_hours": [
          "2021-08-13T02:00:00+00:00",
          "2021-08-13T03:00:00+00:00",
          "2021-08-13T04:00:00+00:00",
          "2021-08-13T05:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 20,
        "period": "2021-08-13"
      },
      {
        "daily_missing_hours": [
          "2021-09-29T07:00:00+00:00",
          "2021-09-29T08:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 22,
        "period": "2021-09-29"
      },
      {
        "daily_missing_hours": [
          "2023-03-24T13:00:00+00:00"
        ],
        "filled_hour_count": 0,
        "filled_hours": [],
        "overlap_match_count": 23,
        "period": "2023-03-24"
      }
    ],
    "expected_hourly_rows": 51120,
    "first_timestamp": "2021-01-01T00:00:00+00:00",
    "interval": "1h UTC",
    "last_timestamp": "2026-10-31T23:00:00+00:00",
    "maximum_allowed_consecutive_missing_hours": 4,
    "maximum_allowed_missing_fraction": 0.001,
    "maximum_allowed_missing_hours": 24,
    "maximum_consecutive_missing_hours": 4,
    "missing_dates": [
      "2021-02-11",
      "2021-03-06",
      "2021-04-20",
      "2021-04-25",
      "2021-08-13",
      "2021-09-29",
      "2023-03-24"
    ],
    "missing_fraction": 0.0002738654147104851,
    "missing_hours": 14,
    "missing_timestamps": [
      "2021-02-11T04:00:00+00:00",
      "2021-03-06T02:00:00+00:00",
      "2021-04-20T02:00:00+00:00",
      "2021-04-20T03:00:00+00:00",
      "2021-04-25T05:00:00+00:00",
      "2021-04-25T06:00:00+00:00",
      "2021-04-25T07:00:00+00:00",
      "2021-08-13T02:00:00+00:00",
      "2021-08-13T03:00:00+00:00",
      "2021-08-13T04:00:00+00:00",
      "2021-08-13T05:00:00+00:00",
      "2021-09-29T07:00:00+00:00",
      "2021-09-29T08:00:00+00:00",
      "2023-03-24T13:00:00+00:00"
    ],
    "monthly_archive_count": 70,
    "observed_hourly_rows": 51106,
    "outside_hours": 0,
    "symbol": "ETHUSDT",
    "timestamp_units_observed": [
      "microseconds",
      "milliseconds"
    ]
  },
  "preflight_artifact_id": 15243896011,
  "preflight_artifact_zip_sha256": "5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49",
  "preflight_manifest_path": "reports/generated/ethereum-dex-turnover-eth-rv-source-preflight/46097000508-attempt-1/preflight.json",
  "preflight_manifest_sha256": "1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6",
  "preflight_run_id": "46097000508",
  "preflight_source_commit_sha": "aa59537e1a7938bddd8b4fd0b64bad4c73f271be",
  "tvl": {
    "canonical_daily_sha256": "0d21055246d26652c684847a5c85ff1abbe7ab4e3010a1e6e8ca8f2e77cac7fe",
    "endpoint": "https://api.llama.fi/v2/historicalChainTvl/Ethereum",
    "first_date": "2021-01-01",
    "last_date": "2026-10-29",
    "maximum_gap_days": 1,
    "maximum_value": 107261486399.0,
    "minimum_required_last_date": "2026-10-29",
    "minimum_value": 14717115471.0,
    "response_sha256_at_preflight": "6377494b5cc6fe5f07f86a6b6404f2056a4ce75cd1caf735fa5146d79ee4adaf",
    "response_sha256_refetched": "c9a69ed6bf251237981676412606bde94103507ab94f1e92450a9f23539bcda4",
    "rows_in_frozen_window": 2128
  }
}

## Event construction and exclusions

{
  "accepted_daily_events": 2069,
  "exact_adjacent_hourly_returns": 51098,
  "forecast_minimum_per_split": 300,
  "hourly_close_rows": 51106,
  "skipped_forecast_origins": {},
  "skipped_origins": {
    "incomplete_pre_rv168_returns": 40,
    "incomplete_pre_rv24_returns": 7,
    "incomplete_target_returns": 6
  }
}

## Validation metrics

{
  "augmented_mae": 0.6926959877660221,
  "augmented_rmse": 0.8915358482251184,
  "baseline_mae": 0.6871993969368533,
  "baseline_rmse": 0.8876825295028358,
  "mae_improvement_pct": -0.7998538493586527,
  "n": 723,
  "rmse_improvement_pct": -0.43408747995083335
}

## Test metrics

{
  "augmented_mae": 0.6748363222000544,
  "augmented_rmse": 0.8807983157207282,
  "baseline_mae": 0.6715679236133826,
  "baseline_rmse": 0.8795060704337156,
  "mae_improvement_pct": -0.4866817594691173,
  "n": 669,
  "rmse_improvement_pct": -0.1469285239128933
}

## Paired test-loss bootstrap

{
  "block_size_daily_events": 7,
  "bootstrap_fraction_positive": 0.305,
  "ci95_lower": -0.011202103506137949,
  "ci95_upper": 0.006070043616085962,
  "mean_baseline_minus_augmented_squared_loss": -0.0022747450467157683,
  "observations": 669,
  "reps": 2000,
  "seed": 20261128
}

## Error / blocker

None

## Literature screen and interpretation

- Hansen, Kim and Kimbrough (2024), Journal of Financial Econometrics 22(1), 224–251, DOI 10.1093/jjfinec/nbac034, document volume/volatility periodicities and report that price discovery predominantly occurs on CEXs while DEX price adjustment can be sluggish.
- Alexander, Chen, Deng and Fu (2025), Price Discovery and Efficiency in Uniswap Liquidity Pools, DOI 10.1002/fut.22593, find that informed traders tend to prefer centralized venues during volatile periods and that DEX speculative activity rises during uncertainty.
- Luo et al. (2024), Piercing the Veil of TVL, arXiv:2404.11745, document TVL double-counting and valuation sensitivity. The denominator here is a public aggregate proxy, not unique deployable capital.
- These studies motivate a narrow predictive test; they do not establish that the exact lagged chain-wide turnover ratio predicts ETH CEX realized variance. DEX activity may respond to volatility rather than lead it.

## Limitations

- DeFiLlama historical values are current-vintage and may be revised; the two-day lag is conservative but does not prove historical point-in-time publication.
- Aggregate Ethereum DEX volume is not ETH-specific flow and can include activity in other assets and protocols.
- TVL may double-count wrapped, leveraged or composable positions; turnover/TVL is a proxy, not true unique-capital turnover.
- ETHUSDT is one centralized venue; no cross-venue replication, causal identification, trading P&L, execution costs or economic value is established.
- Missing hourly bars and every return/window affected by them remain excluded; no price or return is filled or interpolated.

Forecast-only study. No strategy P&L, live orders, capital deployment or trading authorization.
