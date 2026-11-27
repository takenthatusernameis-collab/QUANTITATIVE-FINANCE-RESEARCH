import unittest

from decision_hierarchy import (
    DecisionState,
    ProviderCandidate,
    ProviderFailure,
    choose_next_action,
)


class DecisionHierarchyTests(unittest.TestCase):
    def test_hard_invariants_precede_every_fallback(self):
        result = choose_next_action(DecisionState(
            invariants_pass=False,
            provider_candidates=(ProviderCandidate("A", "api", "v1"),),
            architecture_candidates=("cross_quote",),
        ))
        self.assertEqual(result.action, "BLOCK_INVARIANT")

    def test_existing_verified_output_prevents_duplicate_work(self):
        result = choose_next_action(DecisionState(
            verified_output_exists=True,
            concurrent_owner_exists=True,
            provider_candidates=(ProviderCandidate("A", "api", "v1"),),
        ))
        self.assertEqual(result.action, "REUSE_VERIFIED_OUTPUT")

    def test_concurrent_owner_is_reconciled_before_retry(self):
        result = choose_next_action(DecisionState(concurrent_owner_exists=True))
        self.assertEqual(result.action, "RECONCILE_CONCURRENT_OWNER")

    def test_expired_task_uses_direct_agent_recovery(self):
        result = choose_next_action(DecisionState(deadline_expired=True))
        self.assertEqual(result.action, "DIRECT_AGENT_RECOVERY")

    def test_recovery_fails_closed_without_authorization(self):
        result = choose_next_action(DecisionState(
            deadline_expired=True, direct_execution_authorized=False,
            independent_work_available=True,
        ))
        self.assertEqual(result.action, "BLOCK_EXTERNAL_PREREQUISITE")
        self.assertTrue(result.continue_independent_work)

    def test_unaccepted_funding_blocks_perpetual_but_not_parallel_spot_work(self):
        result = choose_next_action(DecisionState(
            market_type="perpetual", funding_accepted=False,
            independent_work_available=True,
            provider_candidates=(ProviderCandidate("MEXC", "history_api", "probe-2"),),
        ))
        self.assertEqual(result.action, "BLOCK_PERPETUAL")
        self.assertTrue(result.continue_independent_work)

    def test_provider_order_is_research_specific_and_preserved(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("MEXC", "funding_api", "pilot"),
                ProviderCandidate("Coinbase", "hourly_candles", "pilot"),
            )
        ))
        self.assertEqual(result.action, "TRY_PROVIDER")
        self.assertTrue(result.candidate.startswith("MEXC:"))

    def test_one_provider_failure_advances_to_next_provider(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("A", "api", "v1"),
                ProviderCandidate("B", "archive", "v1"),
            ),
            provider_failures=(ProviderFailure("A", "api", "v1"),),
        ))
        self.assertEqual(result.action, "TRY_PROVIDER")
        self.assertTrue(result.candidate.startswith("B:"))

    def test_same_failed_condition_is_not_repeated(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("A", "api", "same-condition"),
                ProviderCandidate("B", "archive", "new-route"),
            ),
            provider_failures=(ProviderFailure("A", "api", "same-condition", transient=True),),
        ))
        self.assertTrue(result.candidate.startswith("B:"))

    def test_changed_condition_can_be_tested_once_after_failure(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("A", "api", "changed-pagination"),
                ProviderCandidate("B", "archive", "pilot"),
            ),
            provider_failures=(ProviderFailure("A", "api", "original-pagination"),),
        ))
        self.assertTrue(result.candidate.startswith("A:"))

    def test_two_identical_non_transient_route_failures_exhaust_that_route(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("A", "api", "new-variant"),
                ProviderCandidate("B", "archive", "pilot"),
            ),
            provider_failures=(
                ProviderFailure("A", "api", "variant-1", failure_code="HTTP_403"),
                ProviderFailure("A", "api", "variant-2", failure_code="HTTP_403"),
            ),
        ))
        self.assertTrue(result.candidate.startswith("B:"))

    def test_two_distinct_provider_failures_advance_to_data_architecture(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(ProviderCandidate("C", "api", "pilot"),),
            provider_failures=(
                ProviderFailure("A", "api", "v1"),
                ProviderFailure("B", "archive", "v1"),
            ),
            architecture_candidates=("same_venue_cross_quote", "raw_trades"),
        ))
        self.assertEqual(result.action, "TRY_DATA_ARCHITECTURE")
        self.assertEqual(result.candidate, "same_venue_cross_quote")

    def test_transient_failures_do_not_count_as_two_provider_failures(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(ProviderCandidate("C", "api", "pilot"),),
            provider_failures=(
                ProviderFailure("A", "api", "timeout", transient=True),
                ProviderFailure("B", "archive", "timeout", transient=True),
            ),
            architecture_candidates=("raw_trades",),
        ))
        self.assertEqual(result.action, "TRY_PROVIDER")
        self.assertTrue(result.candidate.startswith("C:"))

    def test_exhausted_providers_advance_to_architecture(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(ProviderCandidate("A", "api", "v1"),),
            provider_failures=(ProviderFailure("A", "api", "v1"),),
            architecture_candidates=("raw_trades",),
        ))
        self.assertEqual(result.action, "TRY_DATA_ARCHITECTURE")

    def test_architecture_exhaustion_advances_to_timeframe(self):
        result = choose_next_action(DecisionState(
            architecture_candidates=("cross_quote",),
            attempted_architectures=("cross_quote",),
            timeframe_candidates=("4h", "1d"),
        ))
        self.assertEqual(result.action, "TRY_TIMEFRAME")
        self.assertEqual(result.candidate, "4h")

    def test_timeframe_exhaustion_advances_to_model(self):
        result = choose_next_action(DecisionState(
            timeframe_candidates=("4h",), attempted_timeframes=("4h",),
            model_candidates=("state_space", "quantile_regression"),
        ))
        self.assertEqual(result.action, "TRY_MODEL")
        self.assertEqual(result.candidate, "state_space")

    def test_all_distinct_alternatives_exhausted_replace_hypothesis(self):
        result = choose_next_action(DecisionState(
            architecture_candidates=("cross_quote",), attempted_architectures=("cross_quote",),
            timeframe_candidates=("4h",), attempted_timeframes=("4h",),
            model_candidates=("state_space",), attempted_models=("state_space",),
        ))
        self.assertEqual(result.action, "REPLACE_HYPOTHESIS")
        self.assertIn("INCONCLUSIVE/INFEASIBLE", result.reason)

    def test_spot_research_is_not_blocked_by_unaccepted_funding(self):
        result = choose_next_action(DecisionState(market_type="spot", funding_accepted=False))
        self.assertNotEqual(result.action, "BLOCK_PERPETUAL")


    def test_different_failure_classes_do_not_trigger_identical_failure_stop(self):
        result = choose_next_action(DecisionState(
            provider_candidates=(
                ProviderCandidate("A", "api", "third-diagnosis"),
                ProviderCandidate("B", "archive", "pilot"),
            ),
            provider_failures=(
                ProviderFailure("A", "api", "first-diagnosis", failure_code="HTTP_403"),
                ProviderFailure("A", "api", "second-diagnosis", failure_code="CHECKSUM_MISMATCH"),
            ),
        ))
        self.assertEqual(result.action, "TRY_PROVIDER")
        self.assertTrue(result.candidate.startswith("A:"))



if __name__ == "__main__":
    unittest.main()
