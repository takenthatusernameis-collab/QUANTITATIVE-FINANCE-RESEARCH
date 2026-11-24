# Parallel Research Workstreams and Per-Workstream Expiry Policy

**Status: MANDATORY factory-wide execution policy.**

## Decision

The factory should run independent workstreams in parallel whenever doing so increases useful research throughput without violating dependency order, scientific independence, authorization, data integrity or actual resource limits. A single active task must not become an artificial factory-wide serialization rule.

Parallelism is conditional, not a mandate to launch more work. Resolve existing active work first, avoid duplicate experiments, and keep the highest-priority critical-path assignment protected. A queued successor that depends on the active assignment remains queued. Independent work may proceed beside it only after passing this policy's admission checks.

The active queue remains the single canonical index. It may list one primary critical-path workstream and additional independently admitted active workstreams. Every newly activated workstream has its own identity, scope, evidence, start time, cycle counter and hard expiry. Work already active when this policy is adopted retains its previously frozen cycle budget and hard deadline; do not retroactively reset its clock or invent an unrecorded start time. Before admitting a new concurrent workstream, add isolation metadata for every existing active workstream to the canonical queue so the validator can compare paths, resources and holdouts.

## 1. Independence and admission checks

Before starting a workstream alongside another active or blocked workstream, the coordinator must record its workstream_id, objective, independence rationale, dependencies, write scope, exclusive-resource claims and confirmatory-holdout identifiers. Run evaluate_parallel_workstream_admission from research/workstream_policy.py against the current active queue.

Admission requires all of the following:

1. **No unfinished dependency.** Every declared dependency must be recorded as completed. A workstream cannot run in parallel with a task whose output it needs.
2. **No duplicate experiment or dispatch.** Reuse an existing run or continue its authorized recovery instead of creating a second copy. Materially distinct hypotheses or specifications require distinct preregistered identities.
3. **Disjoint write scopes.** Concurrent workstreams must not write to the same repository path or nested path. Use isolated work directories or branches where appropriate; serialize integration and commits to main with expected-head/lease protection.
4. **Exclusive resources are reserved.** A runner, mutable store, API credential/rate-limit budget or other resource marked exclusive cannot be claimed by two concurrent workstreams. Shared read-only immutable inputs are allowed when provenance and checksums are retained.
5. **Confirmatory holdouts stay independent.** Do not expose the same confirmatory holdout to concurrent, separately optimized experiments. The only exception is a single jointly preregistered evaluation family with an explicit multiplicity-control method and the same joint_evaluation_id and multiplicity_control_ref recorded on every member.
6. **Real resource capacity is sufficient.** Respect observed runner, memory, storage, network, API, rate-limit and provider constraints. Do not use an arbitrary global concurrency count; schedule against measured capacity and per-resource limits. Reduce concurrency when contention degrades the critical-path task or makes evidence collection unreliable.

The validator deliberately permits separate workstreams to read the same immutable, provenance-preserving source data. It blocks overlapping write paths, conflicting exclusive resource keys, active dependencies and uncoordinated confirmatory holdout reuse. The coordinator remains responsible for assessing shared compute/network capacity and any domain-specific risks the validator cannot infer.

## 2. Separate clock and budget for every workstream

Every workstream receives a difficulty assessment and its own implementation start, maximum cycle count and exact UTC expiry. One workstream's elapsed time, cycles, blocker or expiry does not reset or consume another independent workstream's budget.

Use the same evidence-backed difficulty assessment and ceilings as the model timebox policy:

| Difficulty | Maximum substantive cycles | Maximum elapsed calendar time |
|---|---:|---:|
| LOW | 2 | 2 days |
| MEDIUM | 4 | 5 days |
| HIGH | 8 | 10 days |

The smaller of the declared workstream budget and its tier ceiling applies. The exact expiry may be earlier than the tier ceiling. The earlier of the cycle limit and timestamp expiry controls.

Required fields for every active workstream:

- workstream_id: stable identity, not recycled for a materially new task.
- difficulty_assessment: the five evidence-backed 1–3 ratings and rationales used by assess_project_difficulty.
- started_at_utc and expires_at_utc: explicit timezone-aware UTC timestamps.
- max_cycles and cycles_used: positive cycle budget and observed consumption.
- dependencies: completed workstream IDs only for a parallel admission.
- write_scope, exclusive_resource_keys, confirmatory_holdout_ids: explicit isolation declarations; use empty lists when not applicable.
- independence_rationale: why the objective can progress without an unfinished workstream.

Call assess_workstream_timebox in research/workstream_policy.py to verify the time and cycle budget. It rejects timezone-naive timestamps, an expiry beyond the difficulty ceiling, a cycle cap above the tier ceiling and cycle-count overruns. It reports time expiry and cycle exhaustion separately.

The clock starts when substantive work begins, not while a task is merely queued. Once started, it continues through handoffs, debugging, data acquisition, CI/runner queues and blocked periods; changing agents or execution routes does not reset it. A material change in scope creates a separately identified workstream with its own prerequisites and budget—it does not extend the old one.

## 3. Expiry and terminal handling

At the earlier of expiry or cycle exhaustion, stop substantive work on that workstream and publish the strongest defensible handoff:

- **GO / NO-GO** only when valid empirical evidence supports the frozen criteria.
- **INCONCLUSIVE / INFEASIBLE** when required evidence, implementation, execution or validation is unresolved.
- **ENGINEERING PASS** and **DATA ACCEPTANCE** remain separate from empirical conclusions.

An expired timebox is not evidence that a strategy is unprofitable. Never call it NO-GO merely because time ran out, weaken gates, quietly roll over the clock or continue under the same identity. A genuinely new research question, data construction or materially changed specification requires a distinct preregistration and expiry.

Expiry applies only to the affected workstream. Other admitted workstreams continue when they remain independent, authorized and within resource capacity; do not cancel unrelated work simply because one stream closes.

## 4. Queue, priority and integration

- Keep one canonical active-queue file, but do not impose a one-active-workstream ceiling.
- Mark one critical-path assignment as primary when required to protect a scheduled capture, holdout validation, release, or other deadline-sensitive dependency.
- List every additional active workstream with its own task link, status, difficulty, start, expiry, cycle usage, dependencies and resource/isolation notes.
- Keep dependency-gated successors queued until their prerequisites close. This policy does not waive predecessor feedback, evidence-first project intake, preregistration or holdout gates.
- Use distinct work directories/branches for concurrent code changes. Integrate and push to main through serialized, expected-head updates; never perform blind concurrent writes to the same branch or path.
- A workstream may continue while another is blocked only if it does not rely on the blocked output, share a conflicting resource or expose a confirmatory holdout.
- Do not let parallel work starve the highest-priority assignment or exceed observed infrastructure/provider limits.

## 5. Current activation

The existing **First Scheduled Holdout Run Validation** remains the primary active workstream, with its existing scope, deadline and acceptance criteria unchanged. The queued **Post-Holdout Research Environment and Portfolio Review** remains dependency-gated and must not be started early.

This policy enables future independent workstreams; it does not itself create or dispatch a new research experiment. No additional parallel workstream is currently admitted by this policy until a concrete task passes the admission checks and has its own frozen timebox.
