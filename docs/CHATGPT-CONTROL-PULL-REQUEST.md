# ChatGPT control pull request

This open pull request is a deliberately narrow event surface for the repository's ChatGPT-connected agent.

The default-branch workflow accepts only exact, whole-body commands posted by the verified connected GitHub actor to this exact pull request:

- `/qfr-control-smoke` — harmless dispatch-path smoke test; no checkout, research, or data retrieval.
- `/qfr-run-eth-btc-data-audit` — runs the pre-existing data audit only, including official-source reconciliation of all currently missing ETHUSDT Spot hours. It does not start strategy backtests.

Security properties:

- The workflow gate must verify `issue_comment: created`, this exact PR number, an open pull request, the exact authenticated actor, and exact full comment-body equality.
- The workflow must execute only files checked out from the repository default branch. It must never checkout, import, execute, or trust this PR's head or PR-supplied code or data.
- The event is a PR-conversation `issue_comment` event; do not use `pull_request_target`.
- All jobs retain least-privilege read-only repository permissions.
- Do not merge this control PR as part of dispatch. Keep it open as the stable control surface.
- The empirical workflow must retain its data-quality gates. This control surface does not authorize live trading, capital deployment, or strategy promotion.

Any command outside this exact allowlist, from another actor or target, or posted in another event must be ignored by the research job.
