# Ethereum validator queue / ETH downside — source-only preflight

- **Candidate:** QFR-2026-11-28-ETH-VALIDATOR-QUEUE-ASYMMETRY-DOWNSIDE-01
- **Status:** PASS
- **Run:** 46104132708, attempt 1
- **Retrieved:** 2026-11-28T03:46:26.095129+00:00
- **Model fit:** False
- **Backtest:** False
- **Raw observations saved:** False

## Source feasibility

- CryptoKeyhole metric: `eth.ValidatorQueueWait`; state `delayed`; daily components: Entry Wait (eth.ValidatorQueueWait.entry, 2187 final values), Exit Wait (eth.ValidatorQueueWait.exit, 2187 final values), Consolidation Wait (eth.ValidatorQueueWait.cons, 569 final values)
- Entry/exit feature coverage: 100.000% / 100.000%.
- Binance ETHUSDT daily rows: 2166 across 71 monthly and 5 daily archives; 76 SHA-256 sidecars verified.
- Forecast schedule: validation 183 / 183; test 111 / 111.
- Test regime coverage: 21 pre-Pectra and 90 post-Pectra origins.
- Training history: 60–100 matured prior events; observed 63–100.

## Methodology and limitations

- Queue waits are computed as queue divided by churn limit, in days of 225 epochs.
- Entry queue definition and churn calculation change at Pectra (2025-05-07); preserve a regime indicator and report pre/post results separately.
- Exit queue includes voluntary exits, slashings and execution-layer exit requests; it is not a direct measure of ETH sales.
- Execution-layer-requested partial withdrawals share exit churn but are absent from daily history; consolidation is a separate queue.
- The free chart is current-vintage, not point-in-time. A two-day lag does not remove historical revision risk.
- The source preflight is not a preregistration, model fit, empirical backtest or trading authorization.

## Provenance

- CryptoKeyhole OpenAPI SHA-256: `2a3e84f5f996f6a6fb97719d0ac2600c45ffc60d593be02ef1b385e4b05a5d45`.
- CryptoKeyhole catalog SHA-256: `0c8388b45f0c21b5e6c67016a447fe7befe5ad51acde3ca197fea4e5c6a487f3`.
- CryptoKeyhole series SHA-256: `7119a0522e4c0cccc7384233b85eeb1732029f85ba4e8f4a03f14b72ba1d1cd1`.
- Binance canonical daily-close SHA-256: `4150b21985ddfccdadf81f0a484666a9fff0c7db79263fae61f1da92881a9810`.

## Durable artifacts

- Machine-readable manifest: `reports/generated/eth-validator-queue-source-preflight/46104132708-attempt-1/preflight.json`.
- Source documentation: https://cryptokeyhole.com/charts/eth/?metric=eth.ValidatorQueueWait and https://cryptokeyhole.com/data-access/.
