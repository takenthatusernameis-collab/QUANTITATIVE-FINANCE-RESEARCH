"""Admission and independent expiry rules for concurrent research workstreams.

This module complements project_readiness.py. It does not replace the evidence,
authorization, preregistration, or scientific-validity gates.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any

from project_readiness import assess_project_difficulty


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object, field: str, blockers: list[str]) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        blockers.append(f"{field} must be a list (an empty list is allowed)")
        return []
    items = list(value)
    if any(not _nonempty(item) for item in items):
        blockers.append(f"{field} must contain only non-empty strings")
        return []
    if len(items) != len(set(items)):
        blockers.append(f"{field} must not contain duplicates")
    return items


def _parse_utc(value: object) -> datetime | None:
    if not _nonempty(value):
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None
    return parsed.astimezone(timezone.utc)


def assess_workstream_timebox(
    workstream: Mapping[str, Any], now_utc: str | None = None
) -> dict[str, Any]:
    """Validate one workstream's own start, expiry, cycle cap and difficulty tier.

    Expiry is not a research conclusion. It means the workstream must stop and
    publish the strongest defensible GO/NO-GO/INCONCLUSIVE/INFEASIBLE outcome.
    """
    blockers: list[str] = []
    difficulty = workstream.get("difficulty_assessment")
    difficulty_result = (
        assess_project_difficulty(difficulty)
        if isinstance(difficulty, Mapping)
        else {"valid": False, "blockers": ["difficulty_assessment is required"]}
    )
    if not difficulty_result["valid"]:
        blockers.extend(difficulty_result["blockers"])

    started = _parse_utc(workstream.get("started_at_utc"))
    expires = _parse_utc(workstream.get("expires_at_utc"))
    now = _parse_utc(now_utc) if now_utc is not None else datetime.now(timezone.utc)
    if started is None:
        blockers.append("started_at_utc must be an explicit timezone-aware UTC timestamp")
    if expires is None:
        blockers.append("expires_at_utc must be an explicit timezone-aware UTC timestamp")
    if now is None:
        blockers.append("now_utc must be an explicit timezone-aware UTC timestamp")

    max_cycles = workstream.get("max_cycles")
    if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or max_cycles < 1:
        blockers.append("max_cycles must be a positive integer")
    cycles_used = workstream.get("cycles_used")
    if isinstance(cycles_used, bool) or not isinstance(cycles_used, int) or cycles_used < 0:
        blockers.append("cycles_used must be a non-negative integer")

    if difficulty_result["valid"] and isinstance(max_cycles, int) and not isinstance(max_cycles, bool):
        if max_cycles > difficulty_result["max_cycles"]:
            blockers.append(
                f"max_cycles exceeds the {difficulty_result['tier']} tier ceiling "
                f"of {difficulty_result['max_cycles']}"
            )
    if isinstance(max_cycles, int) and not isinstance(max_cycles, bool):
        if isinstance(cycles_used, int) and not isinstance(cycles_used, bool) and cycles_used > max_cycles:
            blockers.append("cycles_used cannot exceed max_cycles")

    if started is not None and expires is not None and difficulty_result["valid"]:
        if expires <= started:
            blockers.append("expires_at_utc must be later than started_at_utc")
        elif expires > started + timedelta(days=difficulty_result["max_elapsed_days"]):
            blockers.append(
                f"expires_at_utc exceeds the {difficulty_result['tier']} tier ceiling "
                f"of {difficulty_result['max_elapsed_days']} calendar days"
            )

    valid = not blockers
    time_expired = bool(valid and now is not None and expires is not None and now >= expires)
    cycle_budget_exhausted = bool(
        valid and isinstance(cycles_used, int) and isinstance(max_cycles, int)
        and cycles_used >= max_cycles
    )
    return {
        "valid": valid,
        "difficulty_tier": difficulty_result.get("tier"),
        "tier_max_elapsed_days": difficulty_result.get("max_elapsed_days"),
        "tier_max_cycles": difficulty_result.get("max_cycles"),
        "max_cycles": max_cycles if isinstance(max_cycles, int) and not isinstance(max_cycles, bool) else None,
        "cycles_used": cycles_used if isinstance(cycles_used, int) and not isinstance(cycles_used, bool) else None,
        "time_expired": time_expired,
        "cycle_budget_exhausted": cycle_budget_exhausted,
        "expired": time_expired or cycle_budget_exhausted,
        "remaining_cycles": (
            max(0, max_cycles - cycles_used)
            if isinstance(max_cycles, int) and not isinstance(max_cycles, bool)
            and isinstance(cycles_used, int) and not isinstance(cycles_used, bool)
            else None
        ),
        "blockers": blockers,
    }


def _normalized_scope(value: str) -> PurePosixPath | None:
    path = PurePosixPath(value.strip())
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return None
    return path


def _scopes_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left == right or left in right.parents or right in left.parents


def _joint_holdout_exception(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    joint_id = left.get("joint_evaluation_id")
    adjustment = left.get("multiplicity_control_ref")
    return (
        _nonempty(joint_id)
        and _nonempty(adjustment)
        and joint_id == right.get("joint_evaluation_id")
        and adjustment == right.get("multiplicity_control_ref")
    )


def evaluate_parallel_workstream_admission(
    workstream: Mapping[str, Any],
    active_workstreams: Sequence[Mapping[str, Any]],
    completed_workstream_ids: Sequence[str] = (),
    now_utc: str | None = None,
) -> dict[str, Any]:
    """Admit a workstream only when its dependencies and mutable/evaluation scopes are isolated.

    Shared immutable, provenance-preserving read-only data is allowed. Write
    paths, explicitly exclusive resources and confirmatory holdouts are not
    silently shared between concurrently active workstreams.
    """
    blockers: list[str] = []
    if not isinstance(workstream, Mapping):
        return {"admitted": False, "blockers": ["workstream must be a mapping"]}

    for field in ("workstream_id", "objective", "independence_rationale"):
        if not _nonempty(workstream.get(field)):
            blockers.append(f"{field} is required")

    dependencies = _string_list(workstream.get("dependencies"), "dependencies", blockers)
    write_scope_raw = _string_list(workstream.get("write_scope"), "write_scope", blockers)
    resources = _string_list(
        workstream.get("exclusive_resource_keys"), "exclusive_resource_keys", blockers
    )
    holdouts = _string_list(
        workstream.get("confirmatory_holdout_ids"), "confirmatory_holdout_ids", blockers
    )

    completed = set(_string_list(
        completed_workstream_ids, "completed_workstream_ids", blockers
    ))
    active_ids: set[str] = set()
    active_items: list[Mapping[str, Any]] = []
    if not isinstance(active_workstreams, Sequence) or isinstance(active_workstreams, (str, bytes)):
        blockers.append("active_workstreams must be a list")
    else:
        for index, item in enumerate(active_workstreams):
            if not isinstance(item, Mapping):
                blockers.append(f"active_workstreams[{index}] must be a mapping")
                continue
            status = item.get("status")
            if status not in {"active", "blocked"}:
                continue
            identifier = item.get("workstream_id")
            if not _nonempty(identifier):
                blockers.append(f"active_workstreams[{index}].workstream_id is required")
                continue
            active_ids.add(identifier)
            active_items.append(item)

    identifier = workstream.get("workstream_id")
    if _nonempty(identifier) and (identifier in active_ids or identifier in completed):
        blockers.append("workstream_id must be unique across active and completed workstreams")

    for dependency in dependencies:
        if dependency in active_ids:
            blockers.append(f"dependency {dependency} is still active; dependent work cannot run in parallel")
        elif dependency not in completed:
            blockers.append(f"dependency {dependency} is not recorded as completed")

    candidate_scopes: list[PurePosixPath] = []
    for raw in write_scope_raw:
        normalized = _normalized_scope(raw)
        if normalized is None:
            blockers.append(f"write_scope must use safe repository-relative paths: {raw}")
        else:
            candidate_scopes.append(normalized)

    holdout_set = set(holdouts)
    resource_set = set(resources)
    for item in active_items:
        other_id = item["workstream_id"]
        other_resources = _string_list(
            item.get("exclusive_resource_keys"), f"{other_id}.exclusive_resource_keys", blockers
        )
        collisions = resource_set.intersection(other_resources)
        if collisions:
            blockers.append(
                f"exclusive resources already held by {other_id}: {sorted(collisions)}"
            )

        other_scopes_raw = _string_list(
            item.get("write_scope"), f"{other_id}.write_scope", blockers
        )
        other_scopes: list[PurePosixPath] = []
        for raw in other_scopes_raw:
            normalized = _normalized_scope(raw)
            if normalized is None:
                blockers.append(f"{other_id}.write_scope contains an unsafe path: {raw}")
            else:
                other_scopes.append(normalized)
        overlaps = [
            f"{left} <-> {right}"
            for left in candidate_scopes
            for right in other_scopes
            if _scopes_overlap(left, right)
        ]
        if overlaps:
            blockers.append(f"write_scope overlaps active workstream {other_id}: {overlaps}")

        other_holdouts = _string_list(
            item.get("confirmatory_holdout_ids"), f"{other_id}.confirmatory_holdout_ids", blockers
        )
        shared_holdouts = holdout_set.intersection(other_holdouts)
        if shared_holdouts and not _joint_holdout_exception(workstream, item):
            blockers.append(
                f"confirmatory holdouts already assigned to {other_id}: {sorted(shared_holdouts)}"
            )

    timebox = assess_workstream_timebox(workstream, now_utc=now_utc)
    blockers.extend(timebox["blockers"])
    if timebox["expired"]:
        blockers.append("workstream timebox is already expired or its cycle budget is exhausted")

    return {
        "admitted": not blockers,
        "workstream_id": identifier if _nonempty(identifier) else None,
        "timebox": timebox,
        "compared_active_workstreams": sorted(active_ids),
        "blockers": blockers,
    }
