"""Deterministic, evidence-driven fallback selection for research workstreams.

This module selects a next action from caller-supplied, already-verified state. It
never fetches data, dispatches jobs, relaxes scientific gates, or authorizes trading.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ProviderCandidate:
    provider: str
    route: str
    condition_key: str


@dataclass(frozen=True)
class ProviderFailure:
    provider: str
    route: str
    condition_key: str
    transient: bool = False


@dataclass(frozen=True)
class DecisionState:
    invariants_pass: bool = True
    verified_output_exists: bool = False
    concurrent_owner_exists: bool = False
    deadline_expired: bool = False
    direct_execution_authorized: bool = True
    market_type: str = "spot"
    funding_accepted: bool = True
    provider_candidates: Tuple[ProviderCandidate, ...] = ()
    provider_failures: Tuple[ProviderFailure, ...] = ()
    architecture_candidates: Tuple[str, ...] = ()
    attempted_architectures: Tuple[str, ...] = ()
    timeframe_candidates: Tuple[str, ...] = ()
    attempted_timeframes: Tuple[str, ...] = ()
    model_candidates: Tuple[str, ...] = ()
    attempted_models: Tuple[str, ...] = ()
    independent_work_available: bool = False


@dataclass(frozen=True)
class Decision:
    action: str
    candidate: Optional[str]
    reason: str
    continue_independent_work: bool


def _decision(state: DecisionState, action: str, candidate: Optional[str], reason: str) -> Decision:
    return Decision(action, candidate, reason, state.independent_work_available)


def choose_next_action(state: DecisionState) -> Decision:
    """Return the highest-priority safe next action for one research workstream.

    Provider order is supplied by the research-specific preregistration. After two
    distinct providers have non-transient failures, the selector moves to data
    architectures instead of trying an unbounded list of similar vendors.
    """
    if not state.invariants_pass:
        return _decision(state, "BLOCK_INVARIANT", None,
                         "A scientific, security, legal, authorization, or data-integrity invariant failed.")

    if state.verified_output_exists:
        return _decision(state, "REUSE_VERIFIED_OUTPUT", None,
                         "A valid output already exists; do not duplicate acquisition, execution, or persistence.")

    if state.concurrent_owner_exists:
        return _decision(state, "RECONCILE_CONCURRENT_OWNER", None,
                         "A concurrent execution owns this task identity; inspect its output before any retry.")

    if state.market_type.lower() == "perpetual" and not state.funding_accepted:
        return _decision(state, "BLOCK_PERPETUAL", None,
                         "Perpetual-futures evaluation is blocked until final funding settlements pass acceptance; independent spot work may continue.")

    if state.deadline_expired:
        if state.direct_execution_authorized:
            return _decision(state, "DIRECT_AGENT_RECOVERY", None,
                             "The deadline passed without a valid output; the first authorized agent should execute recovery directly.")
        return _decision(state, "BLOCK_EXTERNAL_PREREQUISITE", None,
                         "Direct recovery is not authorized; preserve the blocker and continue independent work if available.")

    non_transient_providers = {failure.provider for failure in state.provider_failures if not failure.transient}
    if len(non_transient_providers) < 2:
        route_failures = Counter(
            (failure.provider, failure.route)
            for failure in state.provider_failures
            if not failure.transient
        )
        attempted_conditions = {
            (failure.provider, failure.route, failure.condition_key)
            for failure in state.provider_failures
        }
        for candidate in state.provider_candidates:
            signature = (candidate.provider, candidate.route, candidate.condition_key)
            if signature in attempted_conditions:
                continue
            if route_failures[(candidate.provider, candidate.route)] >= 2:
                continue
            return _decision(
                state,
                "TRY_PROVIDER",
                f"{candidate.provider}:{candidate.route}:{candidate.condition_key}",
                "Test the next research-specific provider route with a materially distinct invocation; preserve its own acceptance gates.",
            )

    for candidate in state.architecture_candidates:
        if candidate not in state.attempted_architectures:
            return _decision(state, "TRY_DATA_ARCHITECTURE", candidate,
                             "Provider routes are exhausted or two distinct providers failed; change the data representation materially.")

    for candidate in state.timeframe_candidates:
        if candidate not in state.attempted_timeframes:
            return _decision(state, "TRY_TIMEFRAME", candidate,
                             "Data architectures are exhausted; test a scientifically defensible frequency under a new frozen specification.")

    for candidate in state.model_candidates:
        if candidate not in state.attempted_models:
            return _decision(state, "TRY_MODEL", candidate,
                             "Source and timeframe alternatives are exhausted; test a materially different model under a new identity.")

    return _decision(state, "REPLACE_HYPOTHESIS", None,
                     "Distinct provider, data-architecture, timeframe, and model alternatives are exhausted; close this formulation as INCONCLUSIVE/INFEASIBLE and select a separate hypothesis.")
