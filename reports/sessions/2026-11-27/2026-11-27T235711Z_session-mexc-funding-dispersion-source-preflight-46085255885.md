# MEXC funding-dispersion source preflight — 2026-11-27T23:57:11.979615+00:00

- **Hypothesis:** QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01
- **Status:** PASS
- **Model fit/backtest:** NOT RUN
- **GitHub run:** 46085255885, attempt 1
- **Source commit:** aa76af09051a7b5b7482eafa3a0b86896a378569

## Contract
{
  "base_coin": "BTC",
  "contract_size": "0.0001",
  "future_type": 1,
  "quote_coin": "USDT",
  "settle_coin": "USDT",
  "state": 0,
  "symbol": "BTC_USDT"
}

## Funding coverage
{
  "complete_days": 530,
  "first_settlement": "2025-06-15T00:00:00+00:00",
  "incomplete_days": 0,
  "incomplete_share": 0.0,
  "last_settlement": "2026-11-26T16:00:00+00:00",
  "latest_complete_date": "2026-11-26",
  "sample_end": "2026-11-26",
  "sample_start": "2025-06-15",
  "settlements": 1590
}

## Hourly kline coverage
{
  "coverage": 1.0,
  "end_exclusive": "2026-11-27T17:00:00+00:00",
  "expected_hours": 12929,
  "first_bar": "2025-06-07T00:00:00+00:00",
  "last_bar_start": "2026-11-27T16:00:00+00:00",
  "longest_missing_run_hours": 0,
  "missing_hours": 0,
  "returned_hours": 12929,
  "start": "2025-06-07T00:00:00+00:00"
}

## Event coverage
{
  "complete_event_windows": 530,
  "first_complete": "2025-06-15",
  "last_complete": "2026-11-26",
  "test_events_before_model_warmup": 330,
  "validation_events_before_model_warmup": 61,
  "warmup_events": 139
}

## Provenance
{
  "contract": {
    "host": "https://api.mexc.com",
    "route_attempts": [],
    "sha256": "0fb167f37e8bfa0b9b8a875c04c85a5d690ed5429d93d4a64661ff28367600e9",
    "url": "https://api.mexc.com/api/v1/contract/detail/country?symbol=BTC_USDT"
  },
  "funding": {
    "canonical_sha256": "427f4b141673a6e43108d7033c91494af554c507527e8e51330ac95c0fbafd2f",
    "host": "https://api.mexc.com",
    "pages": [
      {
        "page": 1,
        "rows": 1000,
        "sha256": "5fd177a631494b588de29376c775f5776614b49a2a5a2427fd3916c83e096cc3",
        "url": "https://api.mexc.com/api/v1/contract/funding_rate/history?symbol=BTC_USDT&page_num=1&page_size=1000"
      },
      {
        "page": 2,
        "rows": 618,
        "sha256": "8c5a8b0c093135ec868b10671dee3273174295211861f774e496590713773dfc",
        "url": "https://api.mexc.com/api/v1/contract/funding_rate/history?symbol=BTC_USDT&page_num=2&page_size=1000"
      }
    ],
    "route_attempts": []
  },
  "hourly_klines": {
    "canonical_sha256": "b3fc8ef0cd1f695c18499e191294214914eee96d846b70b71c7c83c541c8468e",
    "host": "https://api.mexc.com",
    "route_attempts": [],
    "segments": [
      {
        "accepted_bars": 1800,
        "end_exclusive": "2025-08-21T00:00:00+00:00",
        "response_sha256": "4e9e1a8e1737ef1870fac4d768a6c87719cf8af4f6197ab02feeed7bfff49fe2",
        "start": "2025-06-07T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1749254400&end=1755734400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2025-11-04T00:00:00+00:00",
        "response_sha256": "40f410fe399951c08aa8656f5d810ca26a54f6256899b8b63c6e69051246e385",
        "start": "2025-08-21T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1755734400&end=1762214400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2026-01-18T00:00:00+00:00",
        "response_sha256": "4dba92b452235289e50fd98d8aa67bbaf96c1526fdd2bee7b3eb938f3f5d52d0",
        "start": "2025-11-04T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1762214400&end=1768694400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2026-04-03T00:00:00+00:00",
        "response_sha256": "2db10bf4ac0baee0a36b061d7b706eb5fea4a39e2d8279ddc4e4328677583d7d",
        "start": "2026-01-18T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1768694400&end=1775174400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2026-06-17T00:00:00+00:00",
        "response_sha256": "273565a6129fee1683a107cbc8b84ba6f53eab6013a3837c0ffb52bfb79cedb6",
        "start": "2026-04-03T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1775174400&end=1781654400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2026-08-31T00:00:00+00:00",
        "response_sha256": "b1907b39b8e31944322c55feae7a90a10ea191972a1861d5028b80ede6764551",
        "start": "2026-06-17T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1781654400&end=1788134400"
      },
      {
        "accepted_bars": 1800,
        "end_exclusive": "2026-11-14T00:00:00+00:00",
        "response_sha256": "7a922f003a523b3bbb63e911d0fc889a4487a40fa0ccfb65b2d19245b974fd9b",
        "start": "2026-08-31T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1788134400&end=1794614400"
      },
      {
        "accepted_bars": 329,
        "end_exclusive": "2026-11-27T17:00:00+00:00",
        "response_sha256": "ea2b37f3b447efd9913a3e1ddaae8bd9fdacf8a4d543807cde5f56a4031e926c",
        "start": "2026-11-14T00:00:00+00:00",
        "url": "https://api.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=1794614400&end=1795798800"
      }
    ]
  }
}

## Error
None

No raw observations, correlations, model fits, forecast metrics or performance results were generated.
