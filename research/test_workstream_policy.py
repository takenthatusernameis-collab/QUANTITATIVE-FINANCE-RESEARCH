import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workstream_policy import (
    assess_workstream_timebox,
    evaluate_parallel_workstream_admission,
)


def difficulty(score=1):
    dimensions = (
        "data_novelty", "methodological_complexity", "integration_burden",
        "statistical_validation_burden", "compute_operational_burden",
    )
    return {
        name: {"score": score, "rationale": "Evidence-backed bounded workstream estimate."}
        for name in dimensions
    }


def workstream(identifier, **overrides):
    result = {
        "workstream_id": identifier,
        "objective": f"Complete isolated work for {identifier}.",
        "independence_rationale": "No dependency on another active workstream; isolated outputs.",
        "dependencies": [],
        "write_scope": [f"research/{identifier}"],
        "exclusive_resource_keys": [f"runner:{identifier}"],
        "confirmatory_holdout_ids": [],
        "difficulty_assessment": difficulty(1),
        "started_at_utc": "2026-01-01T00:00:00Z",
        "expires_at_utc": "2026-01-02T00:00:00Z",
        "max_cycles": 2,
        "cycles_used": 0,
    }
    result.update(overrides)
    return result


class WorkstreamPolicyTests(unittest.TestCase):
    def test_low_workstream_gets_its_own_difficulty_timebox(self):
        result = assess_workstream_timebox(
            workstream("low-a"), now_utc="2026-01-01T12:00:00Z"
        )
        self.assertTrue(result["valid"], result["blockers"])
        self.assertEqual(result["difficulty_tier"], "LOW")
        self.assertEqual(result["tier_max_cycles"], 2)
        self.assertEqual(result["tier_max_elapsed_days"], 2)
        self.assertFalse(result["expired"])

    def test_medium_and_high_workstreams_have_distinct_ceilings(self):
        medium = workstream(
            "medium-a", difficulty_assessment=difficulty(2),
            expires_at_utc="2026-01-06T00:00:00Z", max_cycles=4,
        )
        high = workstream(
            "high-a", difficulty_assessment=difficulty(3),
            expires_at_utc="2026-01-11T00:00:00Z", max_cycles=8,
        )
        medium_result = assess_workstream_timebox(medium, now_utc="2026-01-01T12:00:00Z")
        high_result = assess_workstream_timebox(high, now_utc="2026-01-01T12:00:00Z")
        self.assertEqual(medium_result["tier_max_elapsed_days"], 5)
        self.assertEqual(medium_result["tier_max_cycles"], 4)
        self.assertEqual(high_result["tier_max_elapsed_days"], 10)
        self.assertEqual(high_result["tier_max_cycles"], 8)

    def test_expiry_or_cycle_exhaustion_stops_only_that_workstream(self):
        time_expired = assess_workstream_timebox(
            workstream("expired-a"), now_utc="2026-01-02T00:00:00Z"
        )
        cycle_expired = assess_workstream_timebox(
            workstream("cycles-a", cycles_used=2), now_utc="2026-01-01T12:00:00Z"
        )
        self.assertTrue(time_expired["expired"])
        self.assertTrue(time_expired["time_expired"])
        self.assertTrue(cycle_expired["expired"])
        self.assertTrue(cycle_expired["cycle_budget_exhausted"])

    def test_workstream_cannot_exceed_its_tier_time_ceiling(self):
        result = assess_workstream_timebox(
            workstream("too-long", expires_at_utc="2026-01-03T00:00:00Z"),
            now_utc="2026-01-01T12:00:00Z",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("tier ceiling" in item for item in result["blockers"]))

    def test_workstream_cannot_exceed_its_tier_cycle_ceiling(self):
        result = assess_workstream_timebox(
            workstream("too-many", max_cycles=3),
            now_utc="2026-01-01T12:00:00Z",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("tier ceiling" in item for item in result["blockers"]))

    def test_timestamps_must_be_timezone_aware_utc(self):
        result = assess_workstream_timebox(
            workstream("naive", started_at_utc="2026-01-01T00:00:00"),
            now_utc="2026-01-01T12:00:00Z",
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "started_at_utc must be an explicit timezone-aware UTC timestamp",
            result["blockers"],
        )

    def test_independent_workstreams_can_run_in_parallel(self):
        candidate = workstream("candidate")
        active = [dict(workstream("existing"), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertTrue(result["admitted"], result["blockers"])
        self.assertEqual(result["compared_active_workstreams"], ["existing"])

    def test_unfinished_dependency_blocks_parallel_admission(self):
        candidate = workstream("candidate", dependencies=["existing"])
        active = [dict(workstream("existing"), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertFalse(result["admitted"])
        self.assertTrue(any("dependency existing is still active" in item for item in result["blockers"]))

    def test_completed_dependency_does_not_block_parallel_admission(self):
        candidate = workstream("candidate", dependencies=["source-audit"])
        result = evaluate_parallel_workstream_admission(
            candidate, [], completed_workstream_ids=["source-audit"],
            now_utc="2026-01-01T12:00:00Z",
        )
        self.assertTrue(result["admitted"], result["blockers"])

    def test_overlapping_write_scopes_block_parallel_admission(self):
        candidate = workstream("candidate", write_scope=["reports/shared/new"])
        active = [dict(workstream("existing", write_scope=["reports/shared"]), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertFalse(result["admitted"])
        self.assertTrue(any("write_scope overlaps" in item for item in result["blockers"]))

    def test_shared_exclusive_resource_blocks_parallel_admission(self):
        candidate = workstream("candidate", exclusive_resource_keys=["runner:shared"])
        active = [dict(workstream("existing", exclusive_resource_keys=["runner:shared"]), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertFalse(result["admitted"])
        self.assertTrue(any("exclusive resources" in item for item in result["blockers"]))

    def test_shared_confirmatory_holdout_blocks_parallel_admission(self):
        candidate = workstream("candidate", confirmatory_holdout_ids=["holdout-2026-a"])
        active = [dict(workstream("existing", confirmatory_holdout_ids=["holdout-2026-a"]), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertFalse(result["admitted"])
        self.assertTrue(any("confirmatory holdouts" in item for item in result["blockers"]))

    def test_shared_holdout_requires_joint_preregistration_and_multiplicity_control(self):
        candidate = workstream(
            "candidate", confirmatory_holdout_ids=["holdout-2026-a"],
            joint_evaluation_id="family-01", multiplicity_control_ref="tasks/family-01.md",
        )
        active = [dict(
            workstream("existing", confirmatory_holdout_ids=["holdout-2026-a"]),
            status="active", joint_evaluation_id="family-01",
            multiplicity_control_ref="tasks/family-01.md",
        )]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertTrue(result["admitted"], result["blockers"])

    def test_duplicate_workstream_identity_is_rejected(self):
        candidate = workstream("existing")
        active = [dict(workstream("existing"), status="active")]
        result = evaluate_parallel_workstream_admission(
            candidate, active, now_utc="2026-01-01T12:00:00Z"
        )
        self.assertFalse(result["admitted"])
        self.assertTrue(any("workstream_id must be unique" in item for item in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
