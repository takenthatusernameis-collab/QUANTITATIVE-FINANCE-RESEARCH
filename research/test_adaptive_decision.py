import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adaptive_decision import (
    DEFAULT_PROVIDER_ORDER,
    FailureKind,
    ProviderOption,
    PRIORITY_HIERARCHY,
    RecoveryAction,
    build_experiment_id,
    decide_after_failure,
    dispatch_is_allowed,
    evaluate_research_scope_gate,
    evaluate_provider_evidence,
    evaluate_six_input_gate,
    hypothesis_replacement_allowed,
    independent_workstream_can_continue,
    rank_provider_options,
    validate_market_separation,
)


class AdaptiveDecisionTests(unittest.TestCase):
    def provider(self, name, **kwargs):
        defaults = dict(
            provider=name,
            expected_information_gain=0.5,
            probability_of_success=0.5,
            data_quality=0.5,
            historical_coverage=0.5,
            reproducibility=0.5,
            cost_efficiency=0.5,
        )
        defaults.update(kwargs)
        return ProviderOption(**defaults)

    def complete_evidence(self):
        return {
            "legal_authorized": True,
            "product_inception_verified": True,
            "historical_coverage_verified": True,
            "full_history_feasibility_verified": True,
            "positive_control_passed": True,
            "negative_control_passed": True,
            "timestamps_valid": True,
            "schema_valid": True,
            "ohlcv_valid": True,
            "duplicates_absent": True,
            "provenance_complete": True,
            "checksums_or_immutable_hashes_verified": True,
        }

    def experiment(self):
        return {
            "hypothesis_id": "ethbtc-mean-reversion-v1",
            "venue": "coinbase-exchange",
            "provider": "coinbase-exchange",
            "market_type": "spot",
            "data_construction": "synchronized_eth_usd_div_btc_usd",
            "quote_currency": "USD",
            "timeframe": "1h",
            "sample_start": "2020-01-01",
            "sample_end": "2026-10-31",
            "strategy_version": "v1",
            "cost_model_version": "fees-slippage-v1",
            "source_version": "manifest-sha256:abc",
        }

    def test_canonical_priority_hierarchy_is_complete_and_ordered(self):
        self.assertEqual(
            list(PRIORITY_HIERARCHY.values()),
            [
                "hard_invariants",
                "meta_process_optimization",
                "resolve_existing_work_and_highest_value_bottlenecks",
                "original_research_implementation_and_recovery",
                "independent_alternatives_and_replacement_architectures",
                "hypothesis_or_model_replacement",
                "local_optimization_and_cosmetic_improvements",
            ],
        )

    def test_provider_priority_breaks_equal_score_ties_in_declared_order(self):
        ranked = rank_provider_options([
            self.provider("kraken"),
            self.provider("coinbase_exchange"),
            self.provider("binance_official_recovery"),
        ])
        self.assertEqual(
            [item.provider for item in ranked],
            ["binance_official_recovery", "coinbase_exchange", "kraken"],
        )

    def test_provider_ranking_uses_evidence_score_and_excludes_unauthorized(self):
        options = [
            self.provider("binance_official_recovery", probability_of_success=0.2),
            self.provider("coinbase_exchange", probability_of_success=0.9, data_quality=0.9),
            self.provider("kraken", authorized=False, probability_of_success=1.0),
        ]
        ranked = rank_provider_options(options)
        self.assertEqual(ranked[0].provider, "coinbase_exchange")
        self.assertNotIn("kraken", [item.provider for item in ranked])
        self.assertEqual(DEFAULT_PROVIDER_ORDER[0], "binance_official_recovery")

    def test_provider_is_rejected_when_any_required_evidence_is_unknown(self):
        evidence = self.complete_evidence()
        evidence["positive_control_passed"] = None
        result = evaluate_provider_evidence(evidence)
        self.assertFalse(result["accepted"])
        self.assertIn("positive_control_passed", result["blockers"])

    def test_provider_is_rejected_when_full_history_is_not_feasible(self):
        evidence = self.complete_evidence()
        evidence["full_history_feasibility_verified"] = False
        result = evaluate_provider_evidence(evidence)
        self.assertFalse(result["accepted"])
        self.assertIn("full_history_feasibility_verified", result["blockers"])

    def test_funding_provider_requires_final_settlement_population_semantics(self):
        evidence = self.complete_evidence()
        evidence.update({
            "final_settlement_semantics_verified": True,
            "settlement_population_complete": False,
            "contract_incarnations_verified": True,
        })
        result = evaluate_provider_evidence(evidence, requires_funding=True)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["blockers"], ["settlement_population_complete"])

    def test_transient_failure_uses_bounded_retry(self):
        self.assertEqual(
            decide_after_failure(failure_kind=FailureKind.TRANSIENT),
            RecoveryAction.BOUNDED_RETRY,
        )

    def test_access_restriction_stops_route_without_evasion(self):
        self.assertEqual(
            decide_after_failure(
                failure_kind=FailureKind.ACCESS_RESTRICTED,
                same_route_non_transient_failures=1,
            ),
            RecoveryAction.STOP_RESTRICTED_ROUTE,
        )

    def test_second_identical_non_transient_failure_stops_exact_route(self):
        self.assertEqual(
            decide_after_failure(
                failure_kind=FailureKind.NON_TRANSIENT,
                same_route_non_transient_failures=2,
                distinct_provider_failures=1,
            ),
            RecoveryAction.STOP_ROUTE_AND_SWITCH,
        )

    def test_two_distinct_provider_failures_escalate_to_architecture(self):
        self.assertEqual(
            decide_after_failure(
                failure_kind=FailureKind.NON_TRANSIENT,
                distinct_provider_failures=2,
                architecture_search_exhausted=False,
            ),
            RecoveryAction.CHANGE_DATA_ARCHITECTURE,
        )

    def test_exhausted_architectures_replace_only_an_infeasible_hypothesis(self):
        self.assertEqual(
            decide_after_failure(
                failure_kind=FailureKind.SCIENTIFIC_INVALIDITY,
                distinct_provider_failures=2,
                architecture_search_exhausted=True,
                original_hypothesis_feasible=False,
            ),
            RecoveryAction.REPLACE_HYPOTHESIS,
        )

    def test_independent_workstream_continues_when_dependencies_do_not_overlap(self):
        self.assertTrue(independent_workstream_can_continue(
            blocked_requirements={"spot_ETHUSDT"},
            workstream_requirements={"us_equity_prices", "macro_calendar"},
        ))
        self.assertFalse(independent_workstream_can_continue(
            blocked_requirements={"funding_ETHUSDT"},
            workstream_requirements={"funding_ETHUSDT", "um_ETHUSDT"},
        ))

    def test_experiment_identity_changes_with_provider_or_data_construction(self):
        original = self.experiment()
        identity = build_experiment_id(original)
        changed_provider = dict(original, provider="kraken", venue="kraken")
        changed_construction = dict(original, data_construction="trade_level_ratio")
        changed_timeframe = dict(original, timeframe="15m")
        changed_source = dict(original, source_version="manifest-sha256:def")
        self.assertNotEqual(identity, build_experiment_id(changed_provider))
        self.assertNotEqual(identity, build_experiment_id(changed_construction))
        self.assertNotEqual(identity, build_experiment_id(changed_timeframe))
        self.assertNotEqual(identity, build_experiment_id(changed_source))
        self.assertEqual(identity, build_experiment_id(original))

    def test_spot_and_perpetual_research_are_separated(self):
        spot = validate_market_separation(
            strategy_market="spot", price_market="spot", uses_funding=False
        )
        self.assertTrue(spot["accepted"])
        spot_mislabeled = validate_market_separation(
            strategy_market="perpetual", price_market="spot", uses_funding=False
        )
        self.assertFalse(spot_mislabeled["accepted"])
        perp_unfunded = validate_market_separation(
            strategy_market="perpetual", price_market="perpetual", uses_funding=True
        )
        self.assertFalse(perp_unfunded["accepted"])

    def test_hypothesis_replacement_requires_exhaustion_and_new_preregistration(self):
        denied = hypothesis_replacement_allowed(
            original_status="INCONCLUSIVE",
            reasonable_alternatives_exhausted=False,
            original_hypothesis_id="h1",
            new_hypothesis_id="h2",
            preregistration_frozen=True,
            independent_acceptance_criteria=True,
            provenance_defined=True,
        )
        self.assertFalse(denied["allowed"])
        allowed = hypothesis_replacement_allowed(
            original_status="INCONCLUSIVE/INFEASIBLE",
            reasonable_alternatives_exhausted=True,
            original_hypothesis_id="h1",
            new_hypothesis_id="h2",
            preregistration_frozen=True,
            independent_acceptance_criteria=True,
            provenance_defined=True,
        )
        self.assertTrue(allowed["allowed"])

    def test_duplicate_active_dispatch_is_reused_but_terminal_attempt_is_not_blocking(self):
        active = [{"experiment_id": "exp-a", "status": "in_progress"}]
        self.assertFalse(dispatch_is_allowed("exp-a", active)["allowed"])
        self.assertTrue(dispatch_is_allowed("exp-b", active)["allowed"])
        terminal = [{"experiment_id": "exp-a", "status": "completed"}]
        self.assertTrue(dispatch_is_allowed("exp-a", terminal)["allowed"])

    def test_six_input_gate_fails_closed_on_missing_or_unaccepted_input(self):
        accepted = {
            "spot_ETHUSDT": True,
            "spot_BTCUSDT": True,
            "um_ETHUSDT": True,
            "um_BTCUSDT": True,
            "funding_ETHUSDT": True,
            "funding_BTCUSDT": True,
        }
        self.assertTrue(evaluate_six_input_gate(accepted, manifests_present=True)["allowed"])
        incomplete = dict(accepted, funding_ETHUSDT=False)
        blocked = evaluate_six_input_gate(
            incomplete, manifests_present=True, spot_gap_reconciliation_complete=True
        )
        self.assertFalse(blocked["allowed"])
        self.assertIn("funding_ETHUSDT", blocked["blockers"][0])
        self.assertFalse(evaluate_six_input_gate(
            accepted, manifests_present=False
        )["allowed"])
        self.assertFalse(evaluate_six_input_gate(
            accepted, manifests_present=True, spot_gap_reconciliation_complete=False
        )["allowed"])


    def test_spot_scope_does_not_depend_on_perpetual_funding(self):
        states = {
            "spot_ETHUSDT": True, "spot_BTCUSDT": True,
            "um_ETHUSDT": False, "um_BTCUSDT": False,
            "funding_ETHUSDT": False, "funding_BTCUSDT": False,
        }
        manifests = {
            "spot_ETHUSDT": True, "spot_BTCUSDT": True,
            "um_ETHUSDT": False, "um_BTCUSDT": False,
            "funding_ETHUSDT": False, "funding_BTCUSDT": False,
        }
        result = evaluate_research_scope_gate(
            states, manifests, market_scope="spot",
            spot_gap_reconciliation_complete=True,
            spot_time_policy_accepted=True,
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["required_inputs"], ["spot_ETHUSDT", "spot_BTCUSDT"])

    def test_perpetual_scope_does_not_depend_on_spot_inputs(self):
        states = {
            "spot_ETHUSDT": False, "spot_BTCUSDT": False,
            "um_ETHUSDT": True, "um_BTCUSDT": True,
            "funding_ETHUSDT": True, "funding_BTCUSDT": True,
        }
        manifests = {
            "spot_ETHUSDT": False, "spot_BTCUSDT": False,
            "um_ETHUSDT": True, "um_BTCUSDT": True,
            "funding_ETHUSDT": True, "funding_BTCUSDT": True,
        }
        result = evaluate_research_scope_gate(
            states, manifests, market_scope="perpetual"
        )
        self.assertTrue(result["allowed"])

    def test_spot_gaps_require_both_reconciliation_and_elapsed_time_policy(self):
        states = {"spot_ETHUSDT": False, "spot_BTCUSDT": False}
        manifests = {"spot_ETHUSDT": True, "spot_BTCUSDT": True}
        reconciled_but_no_time_policy = evaluate_research_scope_gate(
            states, manifests, market_scope="spot",
            spot_gap_reconciliation_complete=True,
        )
        self.assertFalse(reconciled_but_no_time_policy["allowed"])
        self.assertIn(
            "Spot event-time/elapsed-time policy is not accepted",
            reconciled_but_no_time_policy["blockers"],
        )
        accepted = evaluate_research_scope_gate(
            states, manifests, market_scope="spot",
            spot_gap_reconciliation_complete=True,
            spot_time_policy_accepted=True,
        )
        self.assertTrue(accepted["allowed"])
        self.assertFalse(evaluate_research_scope_gate(
            states, manifests, market_scope="spot",
            spot_gap_reconciliation_complete=False,
            spot_time_policy_accepted=True,
        )["allowed"])

    def test_combined_scope_requires_all_six_independently(self):
        states = {
            "spot_ETHUSDT": True, "spot_BTCUSDT": True,
            "um_ETHUSDT": True, "um_BTCUSDT": True,
            "funding_ETHUSDT": False, "funding_BTCUSDT": True,
        }
        manifests = {key: True for key in states}
        result = evaluate_research_scope_gate(
            states, manifests, market_scope="both",
            spot_gap_reconciliation_complete=True,
            spot_time_policy_accepted=True,
        )
        self.assertFalse(result["allowed"])
        self.assertTrue(any("funding_ETHUSDT" in item for item in result["blockers"]))

if __name__ == "__main__":
    unittest.main()
