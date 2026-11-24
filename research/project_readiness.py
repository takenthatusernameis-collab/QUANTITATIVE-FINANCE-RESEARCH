"""Evidence-first project intake and difficulty-based timebox rules.

Dependency-free deterministic gates for project selection. They do not judge
market performance or replace scientific review: they ensure hypotheses fit
verified environment dimensions and inherit feedback from the previous task.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

ENVIRONMENT_DIMENSIONS = (
    "legal_and_authorized_access",
    "actual_source_access",
    "historical_coverage_and_product_inception",
    "point_in_time_universe_and_delisting_coverage",
    "timestamp_schema_and_market_semantics",
    "data_quality_and_control_design",
    "cost_and_execution_economics",
    "compute_runtime_and_api_limits",
    "storage_retention_and_artifact_recovery",
    "provenance_and_reproducibility",
    "workflow_permissions_and_automation",
)
ENVIRONMENT_STATUSES = {
    "verified", "sample_only", "claimed_unverified", "unavailable",
    "restricted", "unknown", "not_applicable",
}
DIFFICULTY_DIMENSIONS = (
    "data_novelty", "methodological_complexity", "integration_burden",
    "statistical_validation_burden", "compute_operational_burden",
)
TIMEBOXES = {
    "LOW": {"max_cycles": 2, "max_elapsed_days": 2},
    "MEDIUM": {"max_cycles": 4, "max_elapsed_days": 5},
    "HIGH": {"max_cycles": 8, "max_elapsed_days": 10},
}
PROJECT_KINDS = {"hypothesis_research", "environment_enabling", "meta_process_improvement"}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) > 0
        and all(_nonempty(item) for item in value)
    )


def evaluate_environment_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Require an explicit classification for every environment dimension."""
    blockers: list[str] = []
    if not _nonempty(assessment.get("assessment_id")):
        blockers.append("assessment_id is missing")
    if not _nonempty(assessment.get("assessed_at_utc")):
        blockers.append("assessed_at_utc is missing")
    dimensions = assessment.get("dimensions")
    if not isinstance(dimensions, Mapping):
        dimensions = {}
        blockers.append("dimensions must be a mapping")

    normalized: dict[str, str] = {}
    for name in ENVIRONMENT_DIMENSIONS:
        entry = dimensions.get(name)
        if not isinstance(entry, Mapping):
            blockers.append(f"{name}: classification is missing")
            continue
        status = str(entry.get("status", "")).strip().lower()
        if status not in ENVIRONMENT_STATUSES:
            blockers.append(f"{name}: invalid or missing status")
            continue
        normalized[name] = status
        if status == "verified" and not _string_list(entry.get("evidence_refs")):
            blockers.append(f"{name}: VERIFIED requires evidence_refs")
        elif status == "not_applicable" and not _nonempty(entry.get("rationale")):
            blockers.append(f"{name}: NOT_APPLICABLE requires a rationale")

    classification_complete = len(normalized) == len(ENVIRONMENT_DIMENSIONS)
    readiness_blockers = list(blockers)
    for name, status in normalized.items():
        if status not in {"verified", "not_applicable"}:
            readiness_blockers.append(f"{name}: {status} is not sufficient for hypothesis design")
    return {
        "assessment_valid": not blockers,
        "classification_complete": classification_complete,
        "ready_for_hypothesis_design": classification_complete and not readiness_blockers,
        "statuses": normalized,
        "blockers": blockers,
        "readiness_blockers": readiness_blockers,
    }


def evaluate_hypothesis_environment_fit(
    assessment: Mapping[str, Any], required_dimensions: Sequence[str]
) -> dict[str, Any]:
    """Require all dimensions used by a hypothesis to be VERIFIED."""
    env = evaluate_environment_assessment(assessment)
    blockers = list(env["readiness_blockers"])
    if not isinstance(required_dimensions, Sequence) or isinstance(required_dimensions, (str, bytes)):
        required_dimensions = ()
    required = list(required_dimensions)
    if not required:
        blockers.append("hypothesis must declare required_environment_dimensions")
    for name in required:
        if name not in ENVIRONMENT_DIMENSIONS:
            blockers.append(f"unknown environment dimension: {name}")
        elif env["statuses"].get(name) != "verified":
            blockers.append(f"hypothesis dependency is not VERIFIED: {name}")
    return {
        "allowed": not blockers,
        "required_dimensions": required,
        "environment_ready": bool(env["ready_for_hypothesis_design"]),
        "blockers": blockers,
    }


def assess_project_difficulty(ratings: Mapping[str, Any]) -> dict[str, Any]:
    """Convert evidence-backed 1–3 complexity ratings into a default timebox."""
    blockers: list[str] = []
    scores: dict[str, int] = {}
    for dimension in DIFFICULTY_DIMENSIONS:
        item = ratings.get(dimension)
        if not isinstance(item, Mapping):
            blockers.append(f"{dimension}: rating and rationale are required")
            continue
        score = item.get("score")
        rationale = item.get("rationale")
        if isinstance(score, bool) or not isinstance(score, int) or score not in {1, 2, 3}:
            blockers.append(f"{dimension}: score must be integer 1, 2 or 3")
            continue
        if not _nonempty(rationale):
            blockers.append(f"{dimension}: rationale is required")
            continue
        scores[dimension] = score
    if blockers:
        return {"valid": False, "blockers": blockers, "scores": scores}
    total = sum(scores.values())
    tier = "LOW" if total <= 7 else "MEDIUM" if total <= 11 else "HIGH"
    return {
        "valid": True, "scores": scores, "total_score": total, "tier": tier,
        **TIMEBOXES[tier], "blockers": [],
    }


def evaluate_predecessor_feedback(feedback: Mapping[str, Any]) -> dict[str, Any]:
    """Require research/performance and technical feedback plus admin calibration."""
    blockers: list[str] = []
    if not _nonempty(feedback.get("previous_task_id")):
        blockers.append("previous_task_id is required")
    research = feedback.get("research_feedback")
    if not isinstance(research, Mapping):
        blockers.append("research_feedback is required")
    else:
        if not _nonempty(research.get("summary")):
            blockers.append("research_feedback.summary is required")
        if not _string_list(research.get("evidence_refs")):
            blockers.append("research_feedback.evidence_refs are required")
        metrics = research.get("performance_metrics")
        reason = research.get("not_measured_reason")
        if not isinstance(metrics, Mapping) or (not metrics and not _nonempty(reason)):
            blockers.append("research_feedback requires performance_metrics or not_measured_reason")

    technical = feedback.get("technical_feedback")
    if not isinstance(technical, Mapping):
        blockers.append("technical_feedback is required")
    else:
        if not _nonempty(technical.get("summary")):
            blockers.append("technical_feedback.summary is required")
        if not _string_list(technical.get("evidence_refs")):
            blockers.append("technical_feedback.evidence_refs are required")
        metrics = technical.get("metrics")
        if not isinstance(metrics, Mapping) or not metrics:
            blockers.append("technical_feedback.metrics must contain observed measures")

    decisions = feedback.get("admin_calibration")
    if not isinstance(decisions, Sequence) or isinstance(decisions, (str, bytes)) or not decisions:
        blockers.append("at least one admin_calibration decision is required")
    else:
        for index, decision in enumerate(decisions):
            if not isinstance(decision, Mapping):
                blockers.append(f"admin_calibration[{index}] must be a mapping")
                continue
            for field in ("decision", "rationale", "expected_effect", "validation_metric"):
                if not _nonempty(decision.get(field)):
                    blockers.append(f"admin_calibration[{index}].{field} is required")
            if not _string_list(decision.get("evidence_refs")):
                blockers.append(f"admin_calibration[{index}].evidence_refs are required")
    return {"valid": not blockers, "blockers": blockers}


def evaluate_project_intake(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Gate a new hypothesis or a bounded project that improves its environment."""
    blockers: list[str] = []
    for field in ("project_id", "project_kind", "objective"):
        if not _nonempty(manifest.get(field)):
            blockers.append(f"{field} is required")
    kind = str(manifest.get("project_kind", "")).strip().lower()
    if kind not in PROJECT_KINDS:
        blockers.append(f"project_kind must be one of {sorted(PROJECT_KINDS)}")

    environment = manifest.get("environment_assessment")
    if not isinstance(environment, Mapping):
        env_result = {"assessment_valid": False, "ready_for_hypothesis_design": False,
                      "statuses": {}, "blockers": ["environment_assessment is required"],
                      "readiness_blockers": ["environment_assessment is required"]}
        blockers.append("environment_assessment is required")
    else:
        env_result = evaluate_environment_assessment(environment)
        if not env_result["assessment_valid"]:
            blockers.extend(env_result["blockers"])

    feedback = manifest.get("previous_task_feedback")
    feedback_result = (
        evaluate_predecessor_feedback(feedback) if isinstance(feedback, Mapping)
        else {"valid": False, "blockers": ["previous_task_feedback is required"]}
    )
    if not feedback_result["valid"]:
        blockers.extend(feedback_result["blockers"])

    difficulty = manifest.get("difficulty_assessment")
    difficulty_result = (
        assess_project_difficulty(difficulty) if isinstance(difficulty, Mapping)
        else {"valid": False, "blockers": ["difficulty_assessment is required"]}
    )
    if not difficulty_result["valid"]:
        blockers.extend(difficulty_result["blockers"])

    if kind == "hypothesis_research":
        hypothesis = manifest.get("hypothesis")
        if not isinstance(hypothesis, Mapping):
            blockers.append("hypothesis specification is required")
        else:
            required_fields = (
                "research_question", "primary_metric", "baseline", "cost_model",
                "holdout_policy", "acceptance_criteria", "stop_conditions", "preregistration_path",
            )
            for field in required_fields:
                value = hypothesis.get(field)
                if not (_nonempty(value) or _string_list(value)):
                    blockers.append(f"hypothesis.{field} is required")
            fit = evaluate_hypothesis_environment_fit(
                environment if isinstance(environment, Mapping) else {},
                hypothesis.get("required_environment_dimensions", ()),
            )
            blockers.extend(fit["blockers"])
    elif kind in {"environment_enabling", "meta_process_improvement"}:
        if not _string_list(manifest.get("target_dimensions")):
            blockers.append("target_dimensions are required for enabling projects")
        if not _string_list(manifest.get("acceptance_criteria")):
            blockers.append("acceptance_criteria are required for enabling projects")

    return {
        "ready": not blockers, "project_kind": kind, "environment": env_result,
        "predecessor_feedback": feedback_result, "difficulty": difficulty_result,
        "blockers": blockers,
    }
