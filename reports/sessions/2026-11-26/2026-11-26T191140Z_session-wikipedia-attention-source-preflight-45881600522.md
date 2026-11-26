# Session report — Wikipedia Bitcoin-attention source feasibility

- **Session timestamp:** 2026-11-26T19:11:40Z
- **Repository:** `takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH`
- **Branch:** `main`
- **Starting commit:** `c343f96de48e9a9c466caa9e6b941a111ecd7189`
- **Final implementation commit:** `6fda17a264c79442003f86433b2e4bf37618e01d`
- **Documentation/evidence commit:** pending this report commit
- **Hypothesis:** `QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01`
- **Disposition:** `FEASIBILITY_CHECKED`; no backtest yet.

## Work completed

1. Reconciled the live default branch, current hypothesis registry, recent Actions runs and the latest wake-up report. The current main branch has no `tasks/ACTIVE-QUEUE.md`; the README is the authoritative wake-up contract.
2. Confirmed that the November 26 daily real-data-backtest minimum had already been exceeded by separate studies, including CFTC BTC positioning, Deribit relative DVOL, MEXC BTC funding, EPU and DeFiLlama stablecoin supply. No extra backtest was run merely to inflate activity.
3. Screened for a materially different information mechanism. Public attention is distinct from the current macro, positioning, funding, volatility and stablecoin-supply predictors. The literature boundary is explicit: Wikipedia attention has already been studied against next-day realised skewness; this candidate instead tests five-session BTC downside semivariance beyond a frozen risk-and-momentum baseline.
4. Registered the candidate and a LOW, two-cycle timebox before executing the source preflight. The timebox is frozen: start 2026-11-26T19:02:30Z; implementation deadline 2026-11-27T19:02:30Z; final conclusion deadline 2026-11-28T19:02:30Z. No deadline reset is permitted.
5. Added a read-only Wikimedia/Binance source preflight, eight deterministic parser/coverage tests and a dedicated least-privilege workflow. The workflow uses the immutable triggering commit, `contents: read`, sequential requests and a descriptive Wikimedia User-Agent. It does not run a backtest or save raw observations.
6. The first run exposed two genuine integration defects: Wikimedia's response identifies the project as `en.wikipedia` although the request path is `en.wikipedia.org`; and the repository admission regression suite initially classified the new source-preflight workflow as a research workflow. Both were corrected in an ordinary unmarked repair commit. A new regression explicitly excludes and checks the read-only preflight workflow.
7. The corrected source preflight and repository admission suite then passed.

## Source evidence

[Wikimedia source-preflight run #45881600522](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881600522) completed successfully.

| Check | Result |
|---|---:|
| Wikimedia request chunks | 38, sequential |
| Daily observations | 3,381 |
| First / last date | 2017-08-17 / 2026-11-18 |
| Omitted calendar dates | 0 |
| Maximum consecutive omission | 0 |
| Minimum / maximum views | 2,176 / 344,686 |
| Binance BTCUSDT status | TRADING |
| Binance Spot allowed | Yes |
| Raw observations saved | No |
| Backtest executed | No |

- Combined SHA-256 for the 38 Wikimedia responses: `b1bc21a94749fa1775ed5a3482e8076734bcfff58a729a75da29c1f6d4023b60`.
- Binance exchangeInfo response SHA-256: `3f9e1acedee1a539f106bb591b97828d28d13a264a8f4a1959b22649bea11e41`.
- The source preflight proves current endpoint reachability, response semantics and requested historical coverage. It does not prove historical point-in-time publication availability or absence of revisions.

## CI and recovery evidence

- [Corrected source preflight #45881600522](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881600522): success; 8 source-preflight tests passed.
- [Admission regression #45881600462](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881600462): success; 100 tests passed across the configured suites.
- Initial source-preflight attempt [#45881214470](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881214470) failed closed on the response-project identifier mismatch; no backtest ran.
- Initial admission regression [#45881214510](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45881214510) exposed the missing non-research-workflow exclusion. The repair was committed without the research-admission prefix, so no research backtest was retriggered.

## Repository changes

- `research/PREREGISTERED-QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01.md`: frozen specification and source-preflight evidence.
- `research/wikipedia_attention_source_preflight.py`: read-only source retrieval, schema validation, coverage validation and response digests.
- `research/test_wikipedia_attention_source_preflight.py`: 8 deterministic tests.
- `.github/workflows/wikipedia-attention-source-preflight.yml`: least-privilege source-only workflow.
- `research/test_workflow_admission.py`: explicit source-preflight exclusion and regression coverage.
- `research/HYPOTHESIS-REGISTRY.md`: new `FEASIBILITY_CHECKED` entry.
- `README.md`: removed the completed one-shot instruction line so it does not recur as an ambiguous wake-up command.

## Next bounded action

The next substantive cycle is to implement the already-frozen feature and walk-forward model, run the complete deterministic and workflow-admission suites, and admit one atomic real-data backtest only after those gates pass. Preserve the fixed 104-event training window, validation/test split, non-overlapping six-day event schedule and decision rule. If the second cycle cannot finish by 2026-11-28T19:02:30Z, close `INCONCLUSIVE`; do not extend the timebox.

No live trading, paid data, private exchange credentials, raw-data Git commits or research-parameter changes were made.
