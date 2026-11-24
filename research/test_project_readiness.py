import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_readiness import (
    DIFFICULTY_DIMENSIONS, ENVIRONMENT_DIMENSIONS, assess_project_difficulty,
    evaluate_asset_universe_policy, evaluate_environment_assessment,
    evaluate_hypothesis_environment_fit, evaluate_predecessor_feedback,
    evaluate_project_intake,
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
            "asset_universe_policy": {
                "mode": "dynamic_discovery",
                "target_scope": "All eligible assets from relevant authorized sources",
                "discovery_method": "Enumerate instrument catalogues and apply frozen filters",
                "inclusion_criteria": ["Point-in-time listed instrument", "Meets liquidity threshold"],
                "exclusion_criteria": ["Restricted source", "Unverifiable instrument history"],
                "point_in_time_membership": "Reconstruct membership at each decision time, including delistings",
                "expansion_rule": "Include every newly discovered candidate passing the same rules; no inherited ticker whitelist",
                "max_asset_count": None,
                "cap_rationale": None,
            },
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

    def test_claimed_environment_is_classified_but_not_verified_for_hypothesis_use(self):
        assessment = complete_environment({"actual_source_access": "claimed_unverified"})
        result = evaluate_environment_assessment(assessment)
        self.assertTrue(result["assessment_valid"])
        self.assertTrue(result["ready_for_hypothesis_design"])
        self.assertIn("actual_source_access", result["unverified_dimensions"])
        fit = evaluate_hypothesis_environment_fit(assessment, ["actual_source_access"])
        self.assertFalse(fit["allowed"])

    def test_verified_dimension_requires_evidence(self):
        assessment = complete_environment()
        assessment["dimensions"]["actual_source_access"].pop("evidence_refs")
        self.assertFalse(evaluate_environment_assessment(assessment)["assessment_valid"])

    def test_hypothesis_requires_verified_required_dimensions(self):
        assessment = complete_environment({"historical_coverage_and_product_inception": "sample_only"})
        result = evaluate_hypothesis_environment_fit(assessment, ["historical_coverage_and_product_inception"])
        self.assertFalse(result["allowed"])

    def test_unresolved_unrequired_dimension_does_not_block_hypothesis_fit(self):
        assessment = complete_environment({"compute_runtime_and_api_limits": "unknown"})
        result = evaluate_hypothesis_environment_fit(assessment, ["actual_source_access"])
        self.assertTrue(result["allowed"], result["blockers"])

    def test_unresolved_required_dimension_blocks_hypothesis_fit(self):
        assessment = complete_environment({"compute_runtime_and_api_limits": "unknown"})
        result = evaluate_hypothesis_environment_fit(assessment, ["compute_runtime_and_api_limits"])
        self.assertFalse(result["allowed"])


    def test_dynamic_universe_is_open_ended_without_an_arbitrary_asset_cap(self):
        policy = {
            "mode": "dynamic_discovery",
            "target_scope": "All eligible assets from relevant authorized sources",
            "discovery_method": "Enumerate source catalogues and apply frozen filters",
            "inclusion_criteria": ["Point-in-time listing", "Observed liquidity"],
            "exclusion_criteria": ["Restricted source", "Unverifiable history"],
            "point_in_time_membership": "Reconstruct membership at each decision time",
            "expansion_rule": "Include every candidate satisfying the same frozen rules",
        }
        result = evaluate_asset_universe_policy(policy)
        self.assertTrue(result["valid"], result["blockers"])

    def test_fixed_universe_requires_research_specific_justification(self):
        policy = {
            "mode": "fixed_universe",
            "target_scope": "One predeclared relative-value pair",
            "inclusion_criteria": ["The two legs required by the hypothesis"],
            "exclusion_criteria": ["Other instruments do not represent this exact pair relationship"],
            "point_in_time_membership": "Both legs must exist throughout each evaluated interval",
        }
        self.assertFalse(evaluate_asset_universe_policy(policy)["valid"])
        policy["fixed_scope_rationale"] = "The estimand is specifically this two-leg relative-value relationship."
        self.assertTrue(evaluate_asset_universe_policy(policy)["valid"])

    def test_dynamic_asset_count_cap_requires_rationale(self):
        policy = {
            "mode": "dynamic_discovery",
            "target_scope": "All eligible assets from relevant sources",
            "discovery_method": "Enumerate source catalogues",
            "inclusion_criteria": ["Point-in-time listed"],
            "exclusion_criteria": ["Unverifiable source"],
            "point_in_time_membership": "Historical reconstruction",
            "expansion_rule": "Expand to all candidates passing the filters",
            "max_asset_count": 50,
        }
        self.assertFalse(evaluate_asset_universe_policy(policy)["valid"])
        policy["cap_rationale"] = "A measured runner memory limit bounds this pilot; it is not the final universe."
        self.assertTrue(evaluate_asset_universe_policy(policy)["valid"])

    def test_seed_assets_must_be_declared_non_exhaustive(self):
        policy = {
            "mode": "dynamic_discovery",
            "target_scope": "All qualifying assets from relevant authorized sources",
            "discovery_method": "Enumerate source catalogues",
            "inclusion_criteria": ["Point-in-time listing"],
            "exclusion_criteria": ["Unverifiable history"],
            "point_in_time_membership": "Historical reconstruction",
            "expansion_rule": "Expand to all candidates passing the filters",
            "seed_assets": ["EXAMPLE1", "EXAMPLE2"],
            "seed_assets_non_exhaustive": False,
        }
        self.assertFalse(evaluate_asset_universe_policy(policy)["valid"])
        policy["seed_assets_non_exhaustive"] = True
        self.assertTrue(evaluate_asset_universe_policy(policy)["valid"])

    def test_not_applicable_universe_requires_rationale(self):
        self.assertFalse(evaluate_asset_universe_policy({"mode": "not_applicable"})["valid"])
        self.assertTrue(evaluate_asset_universe_policy({
            "mode": "not_applicable",
            "rationale": "This research concerns a non-asset aggregate risk index.",
        })["valid"])

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
