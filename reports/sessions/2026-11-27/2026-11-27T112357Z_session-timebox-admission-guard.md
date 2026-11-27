# Wake-up session — timebox admission guard — 2026-11-27T112357Z

## Objective

Reconcile the current mainline and implement a durable guard against the exact admission failure found in the unadmitted BTC mining-difficulty draft: research code can appear without a matching preregistration and a complete, difficulty-adjusted timebox.

## Repository preflight — VERIFIED

- Main HEAD at inspection: `5cedee238650438783b9b853df5d38f8ffcaf3da`.
- The README is the self-contained wake-up contract; `tasks/ACTIVE-QUEUE.md` does not exist on main.
- No open pull requests or standalone open issues were found.
- No queued, waiting or in-progress Actions runs were present in the inspected recent run set.
- The unadmitted BTC mining-difficulty draft was already closed on main as **INCONCLUSIVE/INFEASIBLE — UNADMITTED**, with a fail-closed source guard and read-only validation. Do not reopen that identity.
- The 2026-11-27 daily real-data backtest minimum was already satisfied by `QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01`, successful run [45926394994](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994). Its frozen decision remains INCONCLUSIVE. This session did not duplicate the backtest.

## Demonstrated process bottleneck

The mining-difficulty recovery report established that substantive code had been created before a preregistration/timebox, and the module had no matching preregistration. The existing admission tests checked workflow gates and a special-case closure but did not generally verify that a research module had an admission artifact or that post-policy preregistrations contained the complete timebox contract.

The mainline timebox policy first appeared in the current README at commit [3debfd54](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/commit/3debfd54e3fc46674d507b0c166301a4410f6b51), committed at **2026-11-26T10:12:25Z**. Earlier preregistrations are historical records; they must not be retroactively backdated or rewritten to fabricate compliance.

## Changes committed

1. README now records the exact mainline policy cutover and the structural CI checks.
2. `research/test_workflow_admission.py` now verifies that every non-test research module with a literal `HYPOTHESIS_ID` has a matching preregistration or explicit closure. Closed modules must retain a fail-closed execution guard. The shared `treasury_auction_demand.py` engine is the only legacy shared-helper exemption.
3. The same guard checks every preregistration frozen at/after the cutover for a difficulty tier, rationale, exact UTC start, cycle cap, separate implementation/final deadlines and expiry rule. It also checks the cycle and calendar budgets against the tier limits.
4. The completed taker-absorption preregistration now explicitly records the LOW-difficulty rationale, timebox start equal to its already-frozen preregistration timestamp, and the expiry outcome rule. Its original two-cycle budget and both original deadlines are unchanged.
5. Added this timestamped session report.

This is a documentation/guard clarification, not a new experiment, timebox reset or retrospective change to the taker-absorption model.

## Additional source-feasibility screen

A possible Bitcoin on-chain fee-pressure predictor was screened but not admitted. The legacy Blockchain.com Charts API documentation describes a GET chart endpoint and a `sampled=false` option, but the current official Explorer API documentation exposes chart requests through x402 at **$0.005 per request**. Paid data/services are not authorized, and the legacy GET route was not verified as still free. No paid request, payment, raw-data retrieval or hypothesis admission was attempted. Sources: [legacy Charts API documentation](https://www.blockchain.com/explorer/api/charts_api) and [current x402 API reference](https://www.blockchain.com/explorer/docs/x402).

## DAILY KPI

**SATISFIED** for 2026-11-27 by the previously completed BTC taker-absorption real-data backtest. No duplicate empirical run was launched.

## VERIFIED / UNVERIFIED

**Verified**
- Mainline state, README policy cutover and the prior closed mining-difficulty draft.
- Existing daily KPI evidence and its INCONCLUSIVE disposition.
- The new guard and preregistration clarifications are committed atomically.

**Pending verification**
- GitHub Actions execution of the updated admission-guard regression suite.
- The legacy Blockchain.com GET endpoint's current unauthenticated/free availability; it was deliberately not invoked.

## Research versus operations

No new empirical backtest was produced or claimed. Work was limited to a demonstrated governance repair and a bounded source-documentation screen. No paid service, credentials, raw market observations, live orders or capital deployment were used.

## Next

Continue with a materially distinct, public and free source-feasible research hypothesis. The on-chain fee-pressure candidate remains unadmitted until a no-cost route is verified. Preserve the existing daily KPI result and do not reopen closed hypotheses.
