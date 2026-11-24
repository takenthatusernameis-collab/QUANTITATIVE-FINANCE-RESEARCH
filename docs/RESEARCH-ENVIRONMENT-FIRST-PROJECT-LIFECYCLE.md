# Evidence-First Quantitative Research Project Lifecycle

**Status: MANDATORY for every new quantitative hypothesis, model, data-enabling project and research-factory improvement.**

## Governing rule

**The available evidence and operating environment determine which hypotheses are eligible. Agents must not choose an attractive model first and then bend data, infrastructure, permissions, compute or research assumptions around it.**

The repository must first establish what information is realistically accessible, authorized, sufficiently complete, semantically valid, reproducible and economically usable. Only then may an agent design and select a hypothesis that fits the verified evidence envelope.

The factory has no global asset whitelist. Apply the mandatory [Asset-Universe Discovery and Scope Policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md): dynamic discovery is the default for asset-level research, while prior project symbols and narrow capture datasets must never silently constrain the next project's opportunity space.

A source advertised by a provider, an endpoint that once returned HTTP 200, a small sample, a test fixture or an assumed permission is not proof of full research feasibility. Keep observed facts separate from claims, assumptions and unknowns.

## Required lifecycle and stage gates

### Stage 0 — Inherit the objective, constraints and prior-task feedback

Before proposing a new project:

1. Read the current active queue, previous task report, relevant empirical conclusions and current repository state.
2. Complete the two-axis retrospective in [Project Retrospective and Admin-Agent Calibration](PROJECT-RETROSPECTIVE-AND-ADMIN-CALIBRATION.md).
3. Carry forward both research/performance feedback and technical-delivery feedback. If the preceding task did not measure trading performance, record why and use its research/evidence yield instead; never invent a performance metric.
4. Record which previous assumptions were confirmed, falsified or left unresolved, and what the repository-admin agents will change or deliberately retain as a result.

A new project is not ready if either feedback axis or its evidence references are missing.

### Stage 1 — Build the realistic information-and-environment inventory

Do this before designing a new model. Inspect the actual connected tools, GitHub permissions, available runners, network routes, public APIs, files, data archives, storage, compute limits and prior run evidence. Use official documentation and a bounded representative probe where the actual behavior matters.

For every relevant dimension, classify the evidence as:

- **VERIFIED:** directly tested or inspected over the required scope, with a durable evidence reference.
- **SAMPLE_ONLY:** a bounded sample passed; full-history, universe-wide or production behavior is not established.
- **CLAIMED_UNVERIFIED:** documentation, vendor marketing or an endpoint description claims support, but the required behavior has not been verified.
- **UNAVAILABLE / RESTRICTED:** access, rights, coverage or technical limits currently prevent use.
- **UNKNOWN:** not yet investigated or evidence is ambiguous.
- **NOT_APPLICABLE:** genuinely irrelevant to the proposed research question, with a written rationale.

The standard environment inventory must cover:

| Dimension | Required questions |
|---|---|
| Authorization and data rights | Is access lawful, permitted and within existing credentials/permissions? Is any owner-only approval or purchase required? |
| Actual source access | Has the exact source, instrument, endpoint, runner and representative time range been tested from the intended execution environment? |
| Product identity and coverage | Do the instruments/products exist for the entire requested sample? Are inception, delistings, contract changes and historical retention known? |
| Point-in-time population | Can the universe, market-cap ranks, constituents and delisted assets be reconstructed without survivorship or look-ahead bias? Is this not applicable for a fixed, predeclared instrument pair? |
| Timestamp and market semantics | Are timezone, bar boundary, event time, settlement time, units, contract type, quote currency and schema understood and tested? |
| Data quality and controls | Are known-active positive controls, meaningful negative controls, missingness, duplicates, corrections, outliers and gap treatment established? |
| Economic/execution inputs | Are actual fees, spreads, slippage, funding, borrow, liquidity, contract multipliers, lot sizes and minimum notional available where relevant? |
| Compute and operational limits | Can the intended job fit runner time, memory, API rate limits, pagination, concurrency and retry constraints? |
| Storage and recovery | Can raw/derived evidence, manifests, hashes, checkpoints and outputs be retained for the required holdout period and recovered after failure? |
| Provenance and reproducibility | Can the source, query parameters, code SHA, environment/dependencies, transformations, random seeds and artifact hashes be recorded? |
| Workflow permissions and autonomy | Can the project be dispatched, monitored, resumed and reported through the actual authorized integration without routine manual action? |

Use [templates/PROJECT-INTAKE-TEMPLATE.json](../templates/PROJECT-INTAKE-TEMPLATE.json) and the tested [project-readiness policy](../research/project_readiness.py). The intake must include [Asset-Universe Discovery and Scope Policy](ASSET-UNIVERSE-DISCOVERY-AND-SCOPE-POLICY.md).

### Stage 2 — Decide whether the environment is ready for hypothesis design

A new hypothesis may depend only on dimensions classified **VERIFIED** with evidence references. A dimension marked SAMPLE_ONLY or CLAIMED_UNVERIFIED may support a bounded data-enablement pilot, but not a full-history performance claim. UNAVAILABLE, RESTRICTED and UNKNOWN dimensions are blockers whenever the proposed hypothesis requires them.

NOT_APPLICABLE is acceptable only with a reason. It must never be used to hide a missing requirement.

If one or more required dimensions are not verified:

- Do not invent a model that assumes they will become available.
- Prefer an independent, bounded data-enabling project if it has a realistic path to resolve the gap.
- Continue unrelated workstreams that do not depend on the missing evidence.
- If no safe, cost-effective route exists, preserve the limitation and move to a different research question that fits the verified environment.

A provider or infrastructure upgrade is its own project, with explicit evidence, cost, deadline and acceptance criteria. It is not an unlimited precondition that can expand to accommodate a favored strategy.

### Stage 3 — Generate hypotheses from the verified evidence envelope

Only after Stages 0–2 pass may agents generate hypotheses.

Each candidate must state the observed market phenomenon and falsifiable mechanism; exact instruments, universe, venue, market type, quote currency and required fields; why the verified environment can measure them; expected information gain; primary benchmark and null; realistic costs; minimum viable sample and independent holdout; leakage, survivorship, multiple-testing and regime risks; compute/storage needs; and explicit rejection/stop conditions. Include an `asset_universe_policy`: dynamic discovery by default, or a documented reason why a fixed set is intrinsic to the hypothesis. Do not carry over the previous task's tickers or asset-count limits.

Do not rank a candidate highly because of an attractive backtest, theoretical return or novelty when required evidence is unavailable. No empirical result may be inspected before preregistration and holdout rules are frozen.

### Stage 4 — Rank only feasible candidates

Apply hard feasibility and authorization gates first. A high score cannot compensate for a failed hard gate.

Rank eligible candidates by expected decision value and information gain; evidence readiness and probability of valid conclusion; economic rationale and strategic relevance; robustness and falsifiability; expected net benefit after costs and risk; implementation/validation/compute burden; elapsed time and maintenance; reproducibility; and the lessons inherited from previous research and technical outcomes.

Record rejected candidates and the precise reason. Do not silently discard inconvenient evidence or select a candidate merely to keep the pipeline busy.

If no hypothesis passes, select a bounded environment-enabling project or explicitly conclude that no new model is currently justified.

### Stage 5 — Assess difficulty and freeze the timebox

Difficulty is assessed **after** environment feasibility and candidate scope are known, but **before** implementation or inspection of model-performance results.

Rate each dimension LOW (1), MEDIUM (2) or HIGH (3), with a written rationale: data novelty and evidence acquisition; methodological/model complexity; integration/software-engineering burden; statistical validation, robustness and independent-holdout burden; and compute/runtime/operational burden.

| Total score | Tier | Maximum substantive cycles | Maximum elapsed calendar time |
|---:|---|---:|---:|
| 5–7 | LOW | 2 | 2 days |
| 8–11 | MEDIUM | 4 | 5 days |
| 12–15 | HIGH | 8 | 10 days |

The earlier of the cycle limit or calendar deadline controls. The timebox includes ordinary acquisition, implementation, CI queues, analysis and reporting. Deadlines do not authorize weaker scientific standards. Do not inflate difficulty to obtain more time, reset a clock after an ordinary handoff, or extend an experiment silently. Any material change in hypothesis, data construction, venue, timeframe or inference creates a distinct project identity and requires a new preregistration.

### Stage 6 — Execute, validate and conclude

Use immutable or content-addressed inputs, deterministic tests, explicit schemas, source manifests, run IDs, code commit SHAs, environment/dependency records, logs, checkpoint/recovery evidence and hashed artifacts.

Separate these outcomes:

- **Engineering pass:** code, tests or orchestration behaved as intended.
- **Data acceptance:** inputs satisfy the preregistered evidence requirements.
- **Empirical conclusion:** frozen research criteria were evaluated on valid data and the independent sample.

Never use one outcome as evidence for another. A passing smoke test is not data acceptance; a successful download is not market-data completeness; a completed backtest is not a GO.

At expiry, conclude GO/NO-GO only if valid empirical evidence exists. Otherwise use INCONCLUSIVE/INFEASIBLE and name the exact blocker. Preserve failed and null results.

### Stage 7 — Retrospective and next-project handoff

Before choosing the next project, complete the two-axis retrospective. Update the repository-admin decision rubric using the previous project's actual research/performance and technical-delivery evidence. Commit one canonical successor task, its acceptance criteria, agent responsibilities, difficulty rationale and deadline.

## Quantitative-finance-specific acceptance reminders

- Spot, dated futures, perpetual swaps, options and other instruments are distinct evidence domains.
- Funding rates must be distinguished from estimates, timestamps, accrual windows and final payable settlements.
- Universe studies require point-in-time constituents and delisted assets, not just today's survivors.
- Cross-sectional rankings require historical ranks/market capitalizations and point-in-time liquidity filters.
- Execution models require historically valid fees, spreads, depth/impact, funding/borrow and exchange constraints.
- Missing market observations are not zero returns. Never forward-fill or synthesize an observation to make a model executable.
- Holdout data must remain independent. A frozen NO-GO sample is not a tuning set for a replacement idea.

## References

[The Turing Way](https://book.the-turing-way.org/), [FAIR research software guidance](https://fair-software.eu/), [MLflow dataset tracking](https://mlflow.org/docs/latest/ml/dataset/), [MLflow experiment tracking](https://mlflow.org/docs/latest/ml/tracking/), [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions), and [OpenSSF Scorecard](https://scorecard.dev/). These are design references, not dependencies; prefer transparent, low-cost repository-native mechanisms.
