"""Deterministic decision rules for adaptive, evidence-preserving research execution.

The general operating mindset is authoritative; this module supplies reusable,
machine-checkable gates for decisions that can be expressed as structured evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Mapping, Sequence

PRIORITY_HIERARCHY = {
    0: "hard_invariants",
    1: "meta_process_optimization",
    2: "resolve_existing_work_and_highest_value_bottlenecks",
    3: "original_research_implementation_and_recovery",
    4: "independent_alternatives_and_replacement_architectures",
    5: "hypothesis_or_model_replacement",
    6: "local_optimization_and_cosmetic_polish",
}

DEFAULT_PROVIDER_ORDER = (
    "binance_official_recovery",
    "coinbase_exchange",
    "kraken",
    "additional_authorized_exchange",
    "raw_trade_reconstruction",
    "cross_provider_comparison",
)

DEFAULT_ARCHITECTURE_ORDER = (
    "synchronized_same_venue_eth_usd_over_btc_usd",
    "quote_currency_fx_adjusted_cross_rate",
    "checksum_verified_trade_level_reconstruction",
    "event_time_or_irregular_time_representation",
    "independently_justified_alternative_timeframe",
)

REQUIRED_SIX_INPUTS = (
    "spot_ETHUSDT",
    "spot_BTCUSDT",
    "um_ETHUSDT",
    "um_BTCUSDT",
    "funding_ETHUSDT",
    "funding_BTCUSDT",
)

REQUIRED_INPUTS_BY_SCOPE = {
    "spot": ("spot_ETHUSDT", "spot_BTCUSDT"),
    "perpetual": ("um_ETHUSDT", "um_BTCUSDT", "funding_ETHUSDT", "funding_BTCUSDT"),
    "both": REQUIRED_SIX_INPUTS,
}

_PROVIDER_WEIGHTS = {
    "expected_information_gain": 0.20,
    "probability_of_success": 0.15,
    "data_quality": 0.20,
    "historical_coverage": 0.20,
    "reproducibility": 0.15,
    "cost_efficiency": 0.10,
}


class FailureKind(str, Enum):
    TRANSIENT = "transient"
    NON_TRANSIENT = "non_transient"
    ACCESS_RESTRICTED = "access_restricted"
    SCIENTIFIC_INVALIDITY = "scientific_invalidity"


class RecoveryAction(str, Enum):
    BOUNDED_RETRY = "bounded_retry"
    STOP_RESTRICTED_ROUTE = "stop_restricted_route"
    TRY_MATERIALLY_DIFFERENT_ROUTE = "try_materially_different_route"
    STOP_ROUTE_AND_SWITCH = "stop_route_and_switch"
    CHANGE_DATA_ARCHITECTURE = "change_data_architecture"
    REPLACE_HYPOTHESIS = "replace_hypothesis"
    REASSESS_RESEARCH_DESIGN = "reassess_research_design"


@dataclass(frozen=True)
class ProviderOption:
    provider: str
    expected_information_gain: float
    probability_of_success: float
    data_quality: float
    historical_coverage: float
    reproducibility: float
    cost_efficiency: float
    authorized: bool = True

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        for name, value in self.__dict__.items():
            if name in {"provider", "authorized"}:
                continue
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def score(self) -> float:
        """Weighted pilot-priority score; acceptance gates remain separate."""
        return sum(getattr(self, name) * weight for name, weight in _PROVIDER_WEIGHTS.items())


def rank_provider_options(options: Iterable[ProviderOption]) -> list[ProviderOption]:
    """Rank authorized pilot candidates by research value, not fixed provider loyalty.

    The documented provider sequence is a tie-breaker. Authorization is a hard
    filter and cannot be compensated for by a high score.
    """
    priority = {name: index for index, name in enumerate(DEFAULT_PROVIDER_ORDER)}
    eligible = [option for option in options if option.authorized]
    return sorted(
        eligible,
        key=lambda option: (
            -option.score,
            priority.get(option.provider, len(priority)),
            option.provider,
        ),
    )


_COMMON_PROVIDER_GATES = (
    "legal_authorized",
    "product_inception_verified",
    "historical_coverage_verified",
    "positive_control_passed",
    "negative_control_passed",
    "timestamps_valid",
    "schema_valid",
    "ohlcv_valid",
    "duplicates_absent",
    "provenance_complete",
    "checksums_or_immutable_hashes_verified",
)
_FUNDING_GATES = (
    "final_settlement_semantics_verified",
    "settlement_population_complete",
    "contract_incarnations_verified",
)


def evaluate_provider_evidence(
    evidence: Mapping[str, bool | None], *, requires_funding: bool = False
) -> dict[str, object]:
    """Fail-closed provider acceptance with explicit, inspectable blockers."""
    required = _COMMON_PROVIDER_GATES + (_FUNDING_GATES if requires_funding else ())
    blockers = [key for key in required if evidence.get(key) is not True]
    return {
        "accepted": not blockers,
        "required_gates": list(required),
        "blockers": blockers,
        "status": "ACCEPTED" if not blockers else "REJECTED_OR_PROVISIONAL",
    }


def decide_after_failure(
    *,
    failure_kind: FailureKind,
    same_route_non_transient_failures: int = 0,
    distinct_provider_failures: int = 0,
    architecture_search_exhausted: bool = False,
    original_hypothesis_feasible: bool = True,
) -> RecoveryAction:
    """Apply bounded retry, route stop, architecture escalation and hypothesis rules."""
    if same_route_non_transient_failures < 0 or distinct_provider_failures < 0:
        raise ValueError("failure counts cannot be negative")
    if failure_kind is FailureKind.ACCESS_RESTRICTED:
        return RecoveryAction.STOP_RESTRICTED_ROUTE
    if failure_kind is FailureKind.TRANSIENT:
        return RecoveryAction.BOUNDED_RETRY
    if distinct_provider_failures >= 2:
        if not architecture_search_exhausted:
            return RecoveryAction.CHANGE_DATA_ARCHITECTURE
        if not original_hypothesis_feasible:
            return RecoveryAction.REPLACE_HYPOTHESIS
        return RecoveryAction.REASSESS_RESEARCH_DESIGN
    if same_route_non_transient_failures >= 2:
        return RecoveryAction.STOP_ROUTE_AND_SWITCH
    if architecture_search_exhausted and not original_hypothesis_feasible:
        return RecoveryAction.REPLACE_HYPOTHESIS
    return RecoveryAction.TRY_MATERIALLY_DIFFERENT_ROUTE


def independent_workstream_can_continue(
    *, blocked_requirements: Iterable[str], workstream_requirements: Iterable[str]
) -> bool:
    """A workstream may proceed when it has no dependency on the blocked inputs."""
    return not set(blocked_requirements).intersection(workstream_requirements)


def build_experiment_id(specification: Mapping[str, str]) -> str:
    """Create a stable identity that changes with venue, construction, market or spec."""
    required = (
        "hypothesis_id",
        "venue",
        "provider",
        "market_type",
        "data_construction",
        "quote_currency",
        "timeframe",
        "sample_start",
        "sample_end",
        "strategy_version",
        "cost_model_version",
        "source_version",
    )
    missing = [key for key in required if not str(specification.get(key, "")).strip()]
    if missing:
        raise ValueError(f"experiment specification missing: {', '.join(missing)}")
    canonical = {key: str(specification[key]).strip() for key in required}
    digest = sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"exp-{digest[:20]}"


def validate_market_separation(
    *,
    strategy_market: str,
    price_market: str,
    uses_funding: bool = False,
    final_funding_accepted: bool = False,
) -> dict[str, object]:
    """Prevent spot evidence from being represented as perpetual-strategy evidence."""
    market = strategy_market.lower()
    price = price_market.lower()
    blockers: list[str] = []
    if market not in {"spot", "perpetual"}:
        blockers.append("strategy_market must be spot or perpetual")
    if price != market:
        blockers.append("price market must match the strategy market construction")
    if market == "spot" and uses_funding:
        blockers.append("spot-only research cannot include perpetual funding")
    if market == "perpetual":
        if not uses_funding:
            blockers.append("perpetual research must model funding")
        if not final_funding_accepted:
            blockers.append("final settled funding history is not accepted")
    return {"accepted": not blockers, "blockers": blockers}


def hypothesis_replacement_allowed(
    *,
    original_status: str,
    reasonable_alternatives_exhausted: bool,
    original_hypothesis_id: str,
    new_hypothesis_id: str,
    preregistration_frozen: bool,
    independent_acceptance_criteria: bool,
    provenance_defined: bool,
) -> dict[str, object]:
    """Require a separately registered experiment before replacing an infeasible idea."""
    blockers: list[str] = []
    if original_status.upper() not in {
        "INCONCLUSIVE",
        "INFEASIBLE",
        "INCONCLUSIVE/INFEASIBLE",
    }:
        blockers.append("original hypothesis must be formally INCONCLUSIVE/INFEASIBLE")
    if not reasonable_alternatives_exhausted:
        blockers.append("reasonable, materially different alternatives are not exhausted")
    if not new_hypothesis_id.strip() or new_hypothesis_id == original_hypothesis_id:
        blockers.append("replacement requires a distinct non-empty hypothesis identity")
    if not preregistration_frozen:
        blockers.append("replacement preregistration is not frozen")
    if not independent_acceptance_criteria:
        blockers.append("replacement requires independent acceptance criteria")
    if not provenance_defined:
        blockers.append("replacement requires its own data provenance specification")
    return {"allowed": not blockers, "blockers": blockers}


def dispatch_is_allowed(
    experiment_id: str, active_attempts: Sequence[Mapping[str, str]]
) -> dict[str, object]:
    """Prevent duplicate queued, pending or in-progress dispatch for one experiment."""
    if not experiment_id.strip():
        raise ValueError("experiment_id must be non-empty")
    active_states = {"queued", "pending", "in_progress"}
    duplicates = [
        attempt
        for attempt in active_attempts
        if attempt.get("experiment_id") == experiment_id
        and attempt.get("status", "").lower() in active_states
    ]
    return {
        "allowed": not duplicates,
        "decision": "DISPATCH" if not duplicates else "REUSE_EXISTING_ATTEMPT",
        "matching_attempts": [dict(item) for item in duplicates],
    }


def evaluate_six_input_gate(
    input_states: Mapping[str, bool],
    *,
    manifests_present: bool,
    spot_gap_reconciliation_complete: bool | None = None,
) -> dict[str, object]:
    """Shared fail-closed gate used by the ETH/BTC audit and empirical workflow."""
    missing = [name for name in REQUIRED_SIX_INPUTS if name not in input_states]
    rejected = [name for name in REQUIRED_SIX_INPUTS if input_states.get(name) is not True]
    blockers: list[str] = []
    if missing:
        blockers.append(f"missing input status: {', '.join(missing)}")
    if rejected:
        blockers.append(f"unaccepted inputs: {', '.join(rejected)}")
    if not manifests_present:
        blockers.append("all six provenance manifests are not present")
    if spot_gap_reconciliation_complete is False:
        blockers.append("Spot missing-observation reconciliation is incomplete")
    return {
        "allowed": not blockers,
        "status": "PASS" if not blockers else "INCOMPLETE",
        "required_inputs": list(REQUIRED_SIX_INPUTS),
        "accepted_inputs": [
            name for name in REQUIRED_SIX_INPUTS if input_states.get(name) is True
        ],
        "blockers": blockers,
    }

def evaluate_research_scope_gate(
    input_states: Mapping[str, bool],
    manifest_states: Mapping[str, bool],
    *,
    market_scope: str,
    spot_gap_reconciliation_complete: bool | None = None,
    spot_time_policy_accepted: bool = False,
) -> dict[str, object]:
    """Gate spot and perpetual research independently without weakening either.

    A Spot series with known no-trade gaps is accepted only after the gap evidence
    and its elapsed-time/event-time treatment are both accepted. A perpetual
    experiment always requires both USD-M prices and accepted final funding
    histories. Combined research requires both market scopes.
    """
    scope = market_scope.lower()
    if scope == "um":
        scope = "perpetual"
    if scope not in REQUIRED_INPUTS_BY_SCOPE:
        raise ValueError("market_scope must be spot, perpetual/um, or both")

    required = REQUIRED_INPUTS_BY_SCOPE[scope]
    blockers: list[str] = []
    missing_status = [name for name in required if name not in input_states]
    rejected = [
        name for name in required
        if name in input_states and input_states.get(name) is not True
    ]
    missing_manifests = [name for name in required if manifest_states.get(name) is not True]

    if missing_status:
        blockers.append(f"missing input status: {', '.join(missing_status)}")
    if missing_manifests:
        blockers.append(f"missing required manifests: {', '.join(missing_manifests)}")

    spot_inputs = ("spot_ETHUSDT", "spot_BTCUSDT")
    if scope in {"spot", "both"}:
        spot_complete = all(input_states.get(name) is True for name in spot_inputs)
        if not spot_complete:
            if spot_gap_reconciliation_complete is not True:
                blockers.append("Spot hourly gaps are not fully reconciled")
            if not spot_time_policy_accepted:
                blockers.append("Spot event-time/elapsed-time policy is not accepted")
        if spot_complete:
            rejected = [name for name in rejected if name not in spot_inputs]

    if rejected:
        blockers.append(f"unaccepted inputs: {', '.join(rejected)}")

    return {
        "allowed": not blockers,
        "status": "PASS" if not blockers else "INCOMPLETE",
        "market_scope": scope,
        "required_inputs": list(required),
        "accepted_inputs": [name for name in required if input_states.get(name) is True],
        "spot_gap_reconciliation_complete": spot_gap_reconciliation_complete,
        "spot_time_policy_accepted": bool(spot_time_policy_accepted),
        "blockers": blockers,
    }

