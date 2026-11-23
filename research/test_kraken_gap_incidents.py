import unittest

from kraken_gap_incidents import (
    ARCHIVE_GAPS, ARCHIVE_INCIDENTS, GAPS, INCIDENTS,
    audit_all_gaps, audit_archive_anomalies, correlate_gap,
)


class KrakenGapIncidentTests(unittest.TestCase):
    def test_all_five_gaps_are_common_to_all_four_exact_symbols(self):
        self.assertEqual(len(GAPS), 5)
        expected_symbols = {"PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"}
        for gap in GAPS:
            self.assertEqual(set(gap["symbols"]), expected_symbols)
            self.assertEqual(len(gap["symbols"]), 4)

    def test_four_gaps_overlap_relevant_connectivity_incidents(self):
        results = audit_all_gaps()
        self.assertEqual(
            [item["classification"] for item in results],
            [
                "UNEXPLAINED_NO_MATCHING_API_OR_DERIVATIVES_INCIDENT",
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
                "GENERAL_API_CONNECTIVITY_INCIDENT_OVERLAP",
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
            ],
        )

    def test_missing_hourly_event_times_are_exact(self):
        results = audit_all_gaps()
        self.assertEqual(
            [item["missing_expected_hourly_timestamps"] for item in results],
            [
                ["2025-12-04T09:00:00Z"],
                ["2026-02-04T12:00:00Z"],
                ["2026-02-13T18:00:00Z"],
                ["2026-05-09T06:00:00Z"],
                ["2026-10-30T03:00:00Z"],
            ],
        )

    def test_overlap_durations_match_source_incident_windows(self):
        results = audit_all_gaps()
        durations = [
            item["incident_matches"][0]["overlap_minutes"]
            if item["incident_matches"] else 0
            for item in results
        ]
        self.assertEqual(durations, [0, 84, 51, 67, 60])

    def test_december_unichain_incident_is_nearby_but_not_relevant_or_overlapping(self):
        result = correlate_gap(GAPS[0])
        self.assertEqual(result["incident_matches"], [])
        incident = next(item for item in INCIDENTS if item["id"] == "unichain-funding-2025-12-04")
        self.assertFalse(incident["api_affected"])
        self.assertFalse(incident["derivatives_affected"])
        self.assertEqual(incident["end_utc"], "2025-12-04T05:52:00Z")

    def test_may_incident_api_phase_is_not_confused_with_later_payment_issue(self):
        result = audit_all_gaps()[3]
        self.assertEqual(result["incident_matches"][0]["overlap_minutes"], 67)
        self.assertEqual(
            result["incident_matches"][0]["statuspage_overall_end_utc"],
            "2026-05-11T18:15:00Z",
        )
        self.assertFalse(result["incident_matches"][0]["derivatives_affected"])

    def test_february_4_incident_does_not_claim_api_scope(self):
        incident = next(item for item in INCIDENTS if item["id"] == "spot-futures-connectivity-2026-02-04")
        self.assertFalse(incident["api_affected"])
        self.assertTrue(incident["derivatives_affected"])

    def test_status_overlap_never_proves_funding_was_paused_or_settled(self):
        for result in audit_all_gaps():
            self.assertEqual(result["funding_settlement_status"], "UNVERIFIED")
            self.assertEqual(result["causal_claim"], "NOT_ESTABLISHED")
            self.assertFalse(result["scheduled_funding_pause_evidence"])

    def test_six_archive_anomalies_are_exact_and_common_to_all_four_symbols(self):
        results = audit_archive_anomalies()
        self.assertEqual(len(ARCHIVE_GAPS), 6)
        self.assertEqual(len(results), 6)
        expected_symbols = {"PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"}
        for gap, result in zip(ARCHIVE_GAPS, results):
            self.assertEqual(set(gap["symbols"]), expected_symbols)
            self.assertEqual(set(result["symbols"]), expected_symbols)
        self.assertEqual([item["archive_interval_hours"] for item in results], [2.0, 2.0, 3.0, 2.0, 2.0, 2.0])
        self.assertEqual(
            [item["missing_expected_hourly_timestamps"] for item in results],
            [
                ["2025-07-10T22:00:00Z"], ["2025-08-31T04:00:00Z"],
                ["2025-11-01T16:00:00Z", "2025-11-01T17:00:00Z"],
                ["2025-11-02T04:00:00Z"], ["2025-11-19T05:00:00Z"],
                ["2025-12-04T09:00:00Z"],
            ],
        )

    def test_archive_anomalies_correlate_only_with_exact_overlapping_incident_phases(self):
        results = audit_archive_anomalies()
        self.assertEqual(
            [item["classification"] for item in results],
            [
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
                "UNEXPLAINED_NO_MATCHING_API_OR_DERIVATIVES_INCIDENT",
                "UNEXPLAINED_NO_MATCHING_API_OR_DERIVATIVES_INCIDENT",
                "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP",
                "UNEXPLAINED_NO_MATCHING_API_OR_DERIVATIVES_INCIDENT",
            ],
        )
        self.assertEqual(
            [item["incident_matches"][0]["overlap_minutes"] if item["incident_matches"] else 0 for item in results],
            [93, 56, 0, 0, 120, 0],
        )
        self.assertTrue(results[0]["incident_matches"][0]["api_affected"])
        self.assertFalse(results[1]["incident_matches"][0]["api_affected"])
        self.assertFalse(results[4]["incident_matches"][0]["api_affected"])
        self.assertEqual(len(ARCHIVE_INCIDENTS), 3)

    def test_archive_incident_overlap_never_establishes_settlement_causality(self):
        for result in audit_archive_anomalies():
            self.assertEqual(result["funding_settlement_status"], "UNVERIFIED")
            self.assertEqual(result["causal_claim"], "NOT_ESTABLISHED")
            self.assertFalse(result["scheduled_funding_pause_evidence"])
            self.assertEqual(
                result["archive_anomaly_status"],
                "INCIDENT_OVERLAP_NOT_CAUSAL_PROOF" if result["incident_matches"]
                else "NO_MATCHING_RECORDED_INCIDENT_FOUND",
            )

    def test_invalid_gap_order_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "after"):
            correlate_gap({"start_utc": "2026-01-01T02:00:00Z", "end_utc": "2026-01-01T01:00:00Z"})


if __name__ == "__main__":
    unittest.main()
