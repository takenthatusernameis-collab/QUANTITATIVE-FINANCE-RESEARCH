# Repository Hygiene and Context Compaction

**Status:** Mandatory preflight for every wake-up/session before substantive work.

## Objective

Keep the repository small, navigable, reviewable and reproducible. Remove disposable clutter and stale instructions so agents can identify the current task and the actual blocker quickly. Do not optimize for the smallest possible file count at the expense of evidence, provenance, reproducibility or useful history.

## Required order at every wake-up

1. Brainstorm and record a compact, context-aware adaptive antifragile session plan first. Identify the likely highest-leverage process bottleneck and independent work.
2. Inspect the complete repository tree and current working-tree state where available. Review open PRs, branches, active/pending workflow runs, queue-guardian issues, current task pointers and recent artifacts.
3. Perform the conservative cleanup below before the main research or engineering work.
4. Verify references and repository state after cleanup. Then execute the highest-priority process improvement and current objective.

Do not let cleanup become an excuse to defer safe work. Isolate any uncertain or owner-only deletion decision and continue with unrelated safe cleanup and engineering.

## File classes and cleanup rules

| Class | Examples | Rule |
|---|---|---|
| Source and tests | `research/*.py`, test fixtures, workflow definitions | Preserve; edit only for a verified improvement and validate. |
| Canonical policy | README, execution standard, dispatch runbook | Maintain one authoritative location; update in place rather than copy. |
| Active tasks | One canonical active task and a concise queue/index | Keep current, actionable and non-duplicative. |
| Superseded task plans | Old task files with obsolete manual-dispatch instructions | Mark superseded, link to the current task, and move to archive only when references can be updated safely. Preserve historical evidence. |
| Historical reports | Completed audits, negative results, empirical conclusions | Preserve; add a short supersession note when operational instructions are stale. Do not rewrite contemporaneous findings. |
| Reproducibility evidence | Hashes, checksums, source manifests, run IDs, test results | Preserve while the finding remains relevant. Consolidate duplicate summaries without losing provenance. |
| Generated artifacts | Raw CSVs, plots, model outputs, workflow logs, temporary downloads | Keep outside Git in supported caches/artifact storage. Retain compact report, manifest and hash. Do not create a tracked copy to ease transfer. |
| Disposable clutter | `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.DS_Store`, editor swap files, abandoned temporary files and test scratch outputs | Remove when confirmed disposable and not referenced by an active run. |
| Secrets or credentials | Tokens, private keys, account credentials | Never commit or copy. Treat discovery as a security incident; follow credential rotation/removal procedures rather than ordinary cleanup. |

## Safe cleanup procedure

- Inspect `git status --short`, the recursive tree, recent commits and active run/artifact references before making deletions.
- Remove only clearly disposable generated files, caches that are not needed for reproducibility, scratch files and redundant temporary outputs. Keep a verified reusable market-data cache outside version control when it materially reduces future acquisition cost and has a valid provenance manifest.
- Prefer updating one canonical task or report over creating another document that repeats the same state. Do not append routine session transcripts to the README.
- Maintain one canonical active-queue pointer in `tasks/ACTIVE-QUEUE.md`. The queue may list one primary critical-path assignment plus multiple admitted independent workstreams, each with its own task link, isolation record and expiry. Completed tasks should be marked completed; superseded task definitions should clearly point to their successor.
- Keep run logs and bulky outputs in GitHub Actions artifacts or an approved external store with documented retention. Keep a compact summary, source hashes and artifact IDs in Git.
- Archive rather than delete superseded research records when they contain unique decisions, failed approaches, source findings or reproducibility evidence.
- Before moving/renaming a file, search all repository references and update them in the same change. Do not break links.
- Remove a branch only after verifying it is merged or abandoned, has no open PR, is not used by an active run and is not referenced by an active task. Never force-push or delete an active user's work.
- Do not delete an active/queued run's inputs or outputs during cleanup.
- Do not clean by indiscriminately deleting all cache, data or report directories. Distinguish temporary clutter from verified reusable research inputs.

## Preventing repository bloat

- Do not create a new report for every agent cycle. Update the current execution section in the active task/README unless a materially new, reproducible result warrants a standalone report.
- Do not create duplicate task files for the same objective. Split tasks only where the workstreams have independent acceptance criteria and can progress independently.
- Avoid duplicated policy prose. Link to the canonical standard and add only short task-specific deltas.
- Use stable naming, concise status headers, run IDs, commit SHAs, artifact IDs and hashes.
- Keep generated plots, raw data, scratch exports, full logs and bulky model files outside Git.
- Delete or archive temporary files only after verifying no active workflow, task or report depends on them.

## Completion checks

Before moving to substantive work, verify:

- the current active task pointer is unambiguous;
- no stale manual-dispatch instructions are presented as current;
- no duplicate run/incident/alternative attempt is about to be created;
- no disposable scratch clutter remains in the tracked working tree;
- historical evidence, checksums, provenance and failed-run diagnostics are preserved;
- cross-links still resolve;
- the cleanup has not removed inputs needed by active runs.

Record a one-line cleanup result in the existing handoff. If no safe cleanup was needed, say so and proceed. The purpose is review clarity and lower future operating cost, not cosmetic churn.
