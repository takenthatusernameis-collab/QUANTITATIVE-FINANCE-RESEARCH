import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_readiness import (
    DIFFICULTY_DIMENSIONS, ENVIRONMENT_DIMENSIONS, assess_project_difficulty,
    evaluate_environment_assessment, evaluate_hypothesis_environment_fit,
    evaluate_predecessor_feedback, evaluate_project_intake,
)


def complete_environment(statuses=None):
    statuses = statuses or {}
    dimensions = {}
    for name in ENVIRONMENT_DIMENSIONS:
        status = statuses.get(name, "verified")
        entry = {"status": status}
        if status == "verified":
            entry["evidence_refs"] = [f"reports/evidence-{name}.md"]
        elif status == "not_applicable":
            entry["rationale"] = "Not required for this fixed, predeclared research scope."
        dimensions[name] = entry
    return {"assessment_id": "env-test-001", "assessed_at_utc": "2026-11-24T00:00:00Z",
            "dimensions": dimensions}


def difficulty(score=1):
    return {name: {"score": score, "rationale": "Bounded test rating with current evidence."}
            for name in DIFFICULTY_DIMENSIONS}


def predecessor_feedback():
    return {
        "previous_task_id": "tasks/previous-task.md",
        "research_feedback": {
            "summary": "No strategy performance was measured; capture evidence was measured.",
            "evidence_refs": ["reports/previous-result.md"], "performance_metrics": {},
            "not_measured_reason": "Predecessor was a data-infrastructure task, not a strategy test.",
        },
        "technical_feedback": {
            "summary": "CI and workflow delivery were inspected.",
            "evidence_refs": ["reports/previous-ci.md"],
            "metrics": {"tests_passed": 10, "manual_interventions": 0, "runtime_seconds": 42},
        },
        "admin_calibration": [{
            "decision": "change", "rationale": "Storage effort was underestimated.",
            "evidence_refs": ["reports/previous-result.md"],
            "expected_effect": "Improve storage feasibility forecasts.",
            "validation_metric": "planned_vs_actual_storage_rework",
        }],
    }


def valid_manifest():
    return {
        "project_id": "test-project-001", "project_kind": "hypothesis_research",
        "objective": "Test a falsifiable market hypothesis with accepted data.",
        "environment_assessment": complete_environment({
            "point_in_time_universe_and_delisting_coverage": "not_applicable",
        }),
        "previous_task_feedback": predecessor_feedback(), "difficulty_assessment": difficulty(1),
        "hypothesis": {
            "research_question": "Does a predeclared signal predict next-period returns?",
            "required_environment_dimensions": [
                "legal_and_authorized_access", "actual_source_access",
                "historical_coverage_and_product_inception",
                "timestamp_schema_and_market_semantics", "data_quality_and_control_design",
                "provenance_and_reproducibility",
            ],
            "primary_metric": "net_excess_sharpe", "baseline": "buy_and_hold",
            "cost_model": "frozen_all_in_costs", "holdout_policy": "untouched chronological holdout",
            "acceptance_criteria": ["positive net excess Sharpe with interval excluding zero"],
            "stop_conditions": ["any required data dimension is not verified"],
            "preregistration_path": "tasks/TEST-PREREGISTRATION.md",
        },
    }


class ProjectReadinessTests(unittest.TestCase):
    def test_complete_environment_is_ready(self):
        result = evaluate_environment_assessment(complete_environment())
        self.assertTrue(result["assessment_valid"])
        self.assertTrue(result["ready_for_hypothesis_design"])

    def test_not_applicable_requires_rationale(self):
        assessment = complete_environment({"point_in_time_universe_and_delisting_coverage": "not_applicable"})
        assessment["dimensions"]["point_in_time_universe_and_delisting_coverage"].pop("rationale")
        self.assertFalse(evaluate_environment_assessment(assessment)["assessment_valid"])

    def test_claimed_or_unknown_environment_blocks_hypothesis_design(self):
        assessment = complete_environment({"actual_source_access": "claimed_unverified"})
        result = evaluate_environment_assessment(assessment)
        self.assertTrue(result["assessment_valid"])
        self.assertFalse(result["ready_for_hypothesis_design"])

    def test_verified_dimension_requires_evidence(self):
        assessment = complete_environment()
        assessment["dimensions"]["actual_source_access"].pop("evidence_refs")
        self.assertFalse(evaluate_environment_assessment(assessment)["assessment_valid"])

    def test_hypothesis_requires_verified_required_dimensions(self):
        assessment = complete_environment({"historical_coverage_and_product_inception": "sample_only"})
        result = evaluate_hypothesis_environment_fit(assessment, ["historical_coverage_and_product_inception"])
        self.assertFalse(result["allowed"])

    def test_any_unresolved_environment_dimension_blocks_hypothesis(self):
        assessment = complete_environment({"compute_runtime_and_api_limits": "unknown"})
        result = evaluate_hypothesis_environment_fit(assessment, ["actual_source_access"])
        self.assertFalse(result["allowed"])

    def test_difficulty_maps_to_timebox(self):
        self.assertEqual(assess_project_difficulty(difficulty(1))["tier"], "LOW")
        self.assertEqual(assess_project_difficulty(difficulty(2))["tier"], "MEDIUM")
        high = assess_project_difficulty(difficulty(3))
        self.assertEqual(high["tier"], "HIGH")
        self.assertEqual(high["max_cycles"], 8)
        self.assertEqual(high["max_elapsed_days"], 10)

    def test_difficulty_requires_rationale(self):
        ratings = difficulty()
        ratings["compute_operational_burden"]["rationale"] = ""
        self.assertFalse(assess_project_difficulty(ratings)["valid"])

    def test_feedback_requires_both_axes_and_admin_calibration(self):
        feedback = predecessor_feedback()
        feedback.pop("technical_feedback")
        result = evaluate_predecessor_feedback(feedback)
        self.assertFalse(result["valid"])
        self.assertTrue(any("technical_feedback" in item for item in result["blockers"]))

    def test_infrastructure_project_can_resolve_unknown_environment(self):
        manifest = {
            "project_id": "enable-data-001", "project_kind": "environment_enabling",
            "objective": "Verify historical coverage of a public source.",
            "environment_assessment": complete_environment({"actual_source_access": "unknown"}),
            "previous_task_feedback": predecessor_feedback(), "difficulty_assessment": difficulty(1),
            "target_dimensions": ["actual_source_access", "historical_coverage_and_product_inception"],
            "acceptance_criteria": ["known-active control passes", "coverage limits documented"],
        }
        self.assertTrue(evaluate_project_intake(manifest)["ready"])

    def test_hypothesis_intake_passes_only_with_complete_prerequisites(self):
        result = evaluate_project_intake(valid_manifest())
        self.assertTrue(result["ready"], result["blockers"])

    def test_hypothesis_intake_fails_when_data_are_sample_only(self):
        manifest = valid_manifest()
        manifest["environment_assessment"] = complete_environment({"actual_source_access": "sample_only"})
        result = evaluate_project_intake(manifest)
        self.assertFalse(result["ready"])

    def test_project_cannot_skip_predecessor_feedback(self):
        manifest = valid_manifest()
        manifest["previous_task_feedback"] = {}
        result = evaluate_project_intake(manifest)
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
