# ETH/BTC Funding Web-Download Probe — 2026-11-22

## Summary

- **Bitget:** page reached (HTTP 200), but an IP-region restriction blocked interactive access. No self-declaration or workaround was attempted.
- **OKX:** official historical-data page reached anonymously. The funding-rate Download control was found, but not clicked. The exact archive scope/schema remains unverified.
- **No raw data downloaded, no data accepted, and no perpetual backtest run.**

## Bitget

The anonymous Playwright page title was `Funding rate | Bitget Unified trading account`. Its visible body showed a `Restricted IP` dialog stating that the runner's IP was detected as United States and the exchange's products/services were not intended for US users. The page also displayed a self-declaration checkbox and disabled Continue button. The probe did not click, attest, or bypass; the first attempt to click the funding-history tab timed out against the modal.

The probe code now explicitly classifies this restriction and stops before interacting with the tab. Regression tests passed. This code change was **not** live-rerun from the same restricted runner.

## OKX

The page [https://www.okx.com/historical-data](https://www.okx.com/historical-data) returned HTTP 200 and redirected to `/en-us/historical-data`. The anonymous rendered page showed five Download controls, including the Funding rate category. It advertises perpetual funding history from **March 2022 onwards**. The Funding button was identified but not clicked; no file was downloaded. `networkidle` timed out, but the page rendered and the DOM snapshot was captured.

The screenshot shows the top of the page (Trade history and Candlestick cards); the manifest contains the page text and all visible interactive controls, including five Download buttons. The probe was deliberately read-only.

## API cross-check

The official OKX API docs describe `GET /api/v5/public/funding-rate-history`:

- up to three months of history per request;
- maximum 400 records;
- `before` and `after` for pagination;
- `fundingTime` settlement timestamp;
- `fundingRate` forecast and `realizedRate` actual settlement.

The endpoint is recent-history only, so the downloadable archive is the only candidate for the full March 2022+ range. The public API sample could not be retrieved through the web reader, and no runner API request was made.

## Workflow and tests

- Probe run: [45021709395](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021709395), success.
- Artifact: [14753937981](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021709395/artifacts/14753937981), SHA-256 `4d85dbba73b3fae65770d9d3635a4557cab51768e8127b19cf7047200684cce4`.
- CI after classifier and OKX command changes: [45021446714](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021446714) and [45021633877](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45021633877), both passed.
- Playwright 1.56.0 could not install system dependencies on the runner's Ubuntu 26.04 image. Upgrading to 1.65.0 fixed browser installation; the probe then ran successfully.

## Next bounded task

Inspect the **specific OKX Funding card Download button** in a headless browser. Click only that button, immediately cancel if a direct download event starts, and inspect a modal if one opens; do not submit a full-history download or download raw data. Record its selectors, parameters, symbol/date scope, and estimated file size if visible. Keep OKX a separate venue study from 2022+, not a Binance substitute.

**Research status:** INCONCLUSIVE. This UI discovery does not establish file coverage, data completeness, or a trading edge.
