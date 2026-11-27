# Unadmitted draft closure — BTC mining difficulty cuts and downside semivariance

**Hypothesis ID:** `QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01`  
**Status:** `CLOSED — INCONCLUSIVE/INFEASIBLE (UNADMITTED)`  
**This document is a closure record, NOT a preregistration.**

## Reason for closure

The draft was substantively implemented before the mandatory preregistration and difficulty-adjusted timebox existed for this hypothesis. The first implementation commit was `16f39873e7b4f55e045c3f5d36939d34dd8e6425` at **2026-11-27T06:00:26Z**. Further implementation, persistence and regression-test commits followed through `fd648669846b637bef2b9c46ef1baf08375191b2` at **2026-11-27T06:01:46Z**.

No frozen preregistration, exact UTC timebox start, implementation deadline, final conclusion deadline, or empirical acceptance contract existed before substantive implementation. The repository's mandatory timebox rule cannot be satisfied retroactively. Assigning a backdated deadline now would misrepresent compliance, so this identity is closed rather than admitted after the fact.

## Verified technical state at recovery

- The research module was stored as one JSON-quoted string containing escaped newlines, not as executable multiline Python source. Its staged tests could not import it in that form.
- The branch had no preregistration file and no dedicated research workflow.
- No GitHub Actions run existed for `agent/btc-mining-difficulty-20261127`; no open PR or issue owned the draft; its last commit was at 06:01:46Z, nearly five hours before this recovery inspection.
- No reproducible source manifest, accepted source-coverage record, empirical result, or backtest output for this identity is present in the repository. This is absence of verifiable evidence, not proof that a local/manual attempt never occurred.
- The proposed sources were Firsthand Bitcoin's public difficulty-adjustment series, Mempool's recent difficulty-adjustment endpoint as a consistency check, and checksummed Binance Vision BTCUSDT Spot daily archives. None is promoted as accepted for this closed identity.

## Recovery actions

The malformed source serialization was normalized into ordinary Python text solely so deterministic tests could import the draft. A hard-coded fail-closed guard now raises before the first source request. A regression test asserts that `run_research()` stops before calling the network fetch helper.

The unused empirical persistence helper and its tests were removed. A read-only validation workflow runs compilation and deterministic tests only. It must not retrieve market data, fit the model, or create an empirical disposition.

These repairs do **not** cure the original admission violation and do not authorize a backtest.

## Disposition and future work

This is **INCONCLUSIVE/INFEASIBLE due to admission nonconformance**, not a performance NO-GO and not a finding about whether difficulty cuts predict BTC downside semivariance.

Do not reopen or empirically execute this hypothesis ID. If the mining-network mechanism remains worth investigating, first formulate a materially revised hypothesis (for example, a separately specified independently reconstructed event series or a different falsifiable target), assign a new ID, review prior work and source feasibility, and freeze its exact timebox and acceptance criteria **before writing substantive model code**.

No raw observations, credentials, paid data, live orders, or capital deployment were used in this recovery.
