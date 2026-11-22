# ETH/BTC OKX Funding Download-Button Probe — 2026-11-22

## Result

**The exact OKX Funding rate Download control opened a configuration modal. No direct download started.** The probe stopped in the modal, without selecting a symbol, changing the date range, confirming, or downloading raw data.

- Run: [45026416957](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45026416957) — success.
- Artifact: [14754934492](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45026416957/artifacts/14754934492), 383,523 bytes, SHA-256 `e1f37cc2d20863682d75ab43bb788d8f27514a02a3b4dff9e783c6a97351ef89`. Hash independently matched the downloaded ZIP. It contains only a manifest and before/after screenshots.
- CI: [45026341656](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45026341656) passed **144 deterministic tests** and the synthetic plumbing smoke test on commit `c5d79ac287b974569b8fed101f5b3b814e7167b0`.
- Guardian: [45026480037](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45026480037) reported no active research/test runs after the probe.

## Exact target and behavior

The page returned HTTP 200. The probe uniquely matched the Funding rate card, with five exact Download buttons on the page. The target was visible, enabled, and unobstructed. The target's DOM button index was 14; its card text was:

> Funding rate — Historical perpetual funding rates from March 2022 onwards. Download

Clicking that specific control opened the modal titled **Download funding rate data**. No download event fired.

## Modal snapshot

| Control / field | Observed state |
|---|---|
| Instrument | Perpetual |
| Symbol | Select; up to 4 symbols; none selected |
| Date grouping | Daily |
| Date range | 11/20/2026 → 11/20/2026 (default) |
| Confirm | Disabled |
| Field information | Available, not clicked |
| Table headings | Period, Instrument, Symbols, Export time, Size, Action |
| Table state | No records found, with no symbol selected |

The modal also notes that, if only the first file downloads, multiple file downloads may need to be allowed in browser settings. No cookie-consent button was clicked.

## Interpretation

This confirms only the download-modal entry point and the existence of bounded controls. It does **not** establish which symbols are available, selectable date limits, the export schema, actual file size, or completeness of the advertised March 2022+ history. The default date is a single day (two days before the probe date); it must not be mistaken for the full archive scope.

OKX remains an independent venue study from March 2022 onward and is not a replacement for Binance USD-M funding. The Binance funding gate remains `PROVISIONAL_NOT_ACCEPTED`; no perpetual backtest is authorized by this probe.

## Next bounded task

Inspect the modal's **Field information** control only. Capture the schema/field definitions and any units or caveats; do not select symbols, change the date, confirm, or download. After that, a separate bounded probe may inspect symbol options without selecting any instrument.
