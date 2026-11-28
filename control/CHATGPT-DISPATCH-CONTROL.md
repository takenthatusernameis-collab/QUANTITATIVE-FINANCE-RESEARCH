# ChatGPT-to-GitHub Actions control PR

**This is a dedicated command surface. Keep this pull request open and in draft; do not merge it.**

The actual `issue_comment` listener is committed on the repository default branch. GitHub runs that listener from the default branch. It checks the exact control PR number, the verified ChatGPT-connected actor, the event type, and the complete comment body.

The listener must never:
- check out, import, execute, or trust this PR's head branch;
- use `pull_request_target`;
- interpret arbitrary comment text as code, shell input, or workflow parameters;
- accept commands from any other issue or pull request.

## Exact allowlisted commands

- `/qfr-probe-dispatch-bridge` — dispatches a harmless no-op workflow to prove the connected comment-to-Actions path.
- `/qfr-run-initial-claims-btc-downside` — dispatches the single already-preregistered U.S. initial-claims/BTC downside forecast workflow after the probe succeeds.

Commands are exact full-body matches. No free-form inputs are accepted. Duplicate or unexpected commands must not be treated as authorization.
