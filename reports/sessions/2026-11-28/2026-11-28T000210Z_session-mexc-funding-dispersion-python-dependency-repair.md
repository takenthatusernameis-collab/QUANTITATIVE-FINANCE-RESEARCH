# Python 3.11 dependency-pin correction

- **Recorded UTC:** 2026-11-28T00:02:10Z
- **Hypothesis:** QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01
- **Failed model run:** [#46085556820](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085556820)
- **Failed admission-guard run:** [#46085556822](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/46085556822)

The workflow logs showed the pinned NumPy 2.5.5 release requires Python >=3.12, while the repository workflows deliberately use Python 3.11. No model tests, MEXC refetch or backtest ran in that attempt.

Changed the research dependency pin to NumPy 2.4.6, which is available for the configured Python 3.11 runtime. The next admitted run must install it successfully before deterministic tests or source retrieval.
