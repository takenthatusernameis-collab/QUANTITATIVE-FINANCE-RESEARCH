# OKX Funding metadata and symbol search — 2026-11-22

## Scope and safety

Anonymous browser-only inspection of the OKX historical-data page and Funding rate download modal. No authentication, cookie consent, CAPTCHA bypass, network workaround, form submission, symbol selection, date changes, confirmation, or file download was performed. All probe manifests confirm `auth_used=false`, `form_submitted=false`, `file_saved=false`, and no download events.

## Field-information result

Successful field-information probe: [run 45027332926](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45027332926), artifact [14756192431](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45027332926/artifacts/14756192431), 454,504 bytes, ZIP SHA-256 `34955d35ae6e02a01acb87ce9fab4f09364af0dd58c53ebce0f0855458e352af`.

| Field | UI description |
|---|---|
| `instrument_name` | Full trading-instrument name |
| `funding_rate` | Realized funding rate at the most recent settlement |
| `funding_time` | Unix timestamp (milliseconds) of when that funding rate was last settled |

The field-information table does not state the rate's numeric scale, timestamp timezone beyond Unix milliseconds, or row/event granularity. A second field-info probe was redundantly dispatched and also succeeded: [run 45028315196](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45028315196), artifact [14757030788](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45028315196/artifacts/14757030788), 454,508 bytes, SHA-256 `11d9b4577780e22c066dc181669a6c8e4b8a8b30ab2ee200f43e905986781eb1`.

## Symbol-selector investigation

1. The first selector extraction failed with a `Page.evaluate` syntax error after the selector opened. [Run 45027919591](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45027919591), artifact [14756208624](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45027919591/artifacts/14756208624), 386,248 bytes, SHA-256 `12bcc2e5a240e08e1872fc2549af3e4eb108cd6fe6047793320a56073104313a`. Snapshot captured a combobox and “Select All”; no symbols were captured. Exact parser/selector incompatibility remains unisolated.
2. The collector was changed to bounded Playwright locators scoped to the modal, filtering visible text, deduplicating and limiting output to 100. Regression tests were added. CI [45028705707](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45028705707) passed deterministic tests and synthetic plumbing.
3. A successful re-probe opened the selector and captured only “All”; the generic combobox locator was ambiguous (4 matches). [Run 45028848038](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45028848038), artifact [14757310475](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45028848038/artifacts/14757310475), 449,917 bytes, SHA-256 `4e7da039f7d8367fa0f3dd06c712b5c26e9669d9090cb5f19fc15aa6a384ad0d`.
4. The search locator was narrowed to the observed `input[type="search"]` element. Only `ETH` and `BTC` were queried, with no option selected. Both searches returned **“No result found”** in the modal, and the table still showed **“No records found.”** [Final run 45029337953](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45029337953), artifact [14757585237](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45029337953/artifacts/14757585237), 575,844 bytes, ZIP SHA-256 `f32fbc998a9c327eb77315045078747df3297ce86736df815db83d4cd98b55ea`. CI [45029278204](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45029278204) passed deterministic tests and the synthetic smoke test on the final locator/test commit [33a7c74](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/33a7c7424fe75c816def7196dda1d111f131c4ef).

## Conclusion

The anonymous OKX funding-download UI does not currently expose ETH or BTC symbols through the tested search, so no bounded sample can be acquired from this route. This is not proof of global OKX data unavailability; the page may be region-limited or the selector may be incomplete. Do not repeat the UI probe, change regions, accept cookies, or bypass access controls.

OKX remains **UNACCEPTED / NO SAMPLE** for the independent funding-data pilot. It cannot substitute for Binance funding. The Binance funding-completeness gate remains closed and the ETH/BTC perpetual research conclusion remains INCONCLUSIVE. The next highest-value process task is the trusted default-branch archive-cache warm-up design, while funding-event acceptance remains separate.
