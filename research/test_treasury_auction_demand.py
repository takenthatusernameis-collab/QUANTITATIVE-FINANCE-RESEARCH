import datetime as dt
import unittest
from unittest.mock import patch

import treasury_auction_demand as qfr


class TreasuryAuctionDemandTests(unittest.TestCase):
    def test_parse_helpers_reject_missing_and_preserve_values(self):
        self.assertEqual(qfr.parse_date("2026-11-24T00:00:00"), dt.date(2026, 11, 24))
        self.assertEqual(qfr.parse_float("4.125"), 4.125)
        self.assertIsNone(qfr.parse_float("."))
        self.assertIsNone(qfr.parse_date("null"))

    def test_selects_only_nominal_fixed_rate_ten_year_notes(self):
        rows = [
            {
                "security_type": "Note",
                "original_security_term": "10-Year",
                "security_term": "9-Year 11-Month",
                "tips": False,
                "floating_rate": "No",
                "record_date": "2020-01-15",
                "auction_date": "2020-01-14",
                "cusip": "A",
                "bid_to_cover_ratio": "2.4",
                "comp_accepted": "100",
                "primary_dealer_accepted": "20",
                "direct_bidder_accepted": "20",
                "indirect_bidder_accepted": "60",
            },
            {
                "security_type": "Note",
                "original_security_term": "10-Year",
                "security_term": "10-Year",
                "tips": True,
                "floating_rate": "No",
                "record_date": "2020-01-15",
                "auction_date": "2020-01-14",
                "cusip": "B",
                "bid_to_cover_ratio": "2.4",
                "comp_accepted": "100",
                "primary_dealer_accepted": "20",
                "direct_bidder_accepted": "20",
                "indirect_bidder_accepted": "60",
            },
            {
                "security_type": "Note",
                "original_security_term": "10-Year",
                "security_term": "10-Year",
                "tips": False,
                "floating_rate": "Yes",
                "record_date": "2020-01-15",
                "auction_date": "2020-01-14",
                "cusip": "C",
                "bid_to_cover_ratio": "2.4",
                "comp_accepted": "100",
                "primary_dealer_accepted": "20",
                "direct_bidder_accepted": "20",
                "indirect_bidder_accepted": "60",
            },
            {
                "security_type": "Note",
                "original_security_term": "5-Year",
                "security_term": "5-Year",
                "tips": False,
                "floating_rate": "No",
                "record_date": "2020-01-15",
                "auction_date": "2020-01-14",
                "cusip": "D",
                "bid_to_cover_ratio": "2.4",
                "comp_accepted": "100",
                "primary_dealer_accepted": "20",
                "direct_bidder_accepted": "20",
                "indirect_bidder_accepted": "60",
            },
        ]
        selected, counts = qfr.select_ten_year_nominal_auctions(rows)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["cusip"], "A")
        self.assertAlmostEqual(selected[0]["dealer_share"], 0.20)
        self.assertEqual(counts["selected"], 1)

    def test_missing_record_date_uses_auction_date_conservatively(self):
        row = {
            "security_type": "Note",
            "original_security_term": "10-Year",
            "security_term": "10-Year",
            "tips": False,
            "floating_rate": "No",
            "auction_date": "2020-01-14",
            "cusip": "A",
            "bid_to_cover_ratio": "2.4",
            "comp_accepted": "100",
            "primary_dealer_accepted": "20",
            "direct_bidder_accepted": "20",
            "indirect_bidder_accepted": "60",
        }
        selected, counts = qfr.select_ten_year_nominal_auctions([row])
        self.assertEqual(selected[0]["record_date"], dt.date(2020, 1, 14))
        self.assertEqual(counts["record_date_fallback_to_auction_date"], 1)

    def test_weak_score_uses_only_prior_auctions(self):
        auctions = []
        for i in range(27):
            auctions.append({
                "dealer_share": 0.10 + i * 0.01,
                "bid_to_cover": 3.0 - i * 0.02,
            })
        qfr.add_weak_demand_scores(auctions, lookback=26)
        self.assertIsNone(auctions[0]["weak_score"])
        self.assertIsNotNone(auctions[26]["weak_score"])
        self.assertGreaterEqual(auctions[26]["weak_score"], 0.75)

    def test_target_starts_after_record_date_and_uses_five_observed_business_steps(self):
        dates = [dt.date(2019, 12, day) for day in [24, 25, 26, 27, 30]] + [dt.date(2020, 1, day) for day in [2, 3, 6, 7, 8, 9, 10, 13, 14]]
        yields = {date: 2.0 + index * 0.01 for index, date in enumerate(dates)}
        auction = {
            "cusip": "A",
            "auction_date": dt.date(2020, 1, 3),
            "record_date": dt.date(2020, 1, 6),
            "bid_to_cover": 2.4,
            "dealer_share": 0.2,
        }
        events, skipped = qfr.build_events([auction], yields)
        self.assertEqual(skipped["no_future_yield_window"], 0)
        self.assertEqual(events[0]["yield_start_date"], dt.date(2020, 1, 7))
        self.assertEqual(events[0]["yield_end_date"], dt.date(2020, 1, 14))
        self.assertAlmostEqual(events[0]["target_bp"], 5.0)

    def test_walk_forward_requires_prior_targets_to_be_completed_before_signal(self):
        events = []
        base = dt.date(2020, 1, 1)
        for i in range(60):
            record_date = base + dt.timedelta(days=i * 10)
            events.append({
                "record_date": record_date,
                "yield_end_date": record_date + dt.timedelta(days=5),
                "cusip": str(i),
                "bid_to_cover": 2.0 + (i % 5) * 0.1,
                "dealer_share": 0.2 + (i % 7) * 0.01,
                "pre_yield_5d_bp": (i % 9) - 4,
                "target_bp": (i % 11) - 5,
                "weak_score": 0.5,
                "weak_demand": False,
            })
        predictions = qfr.walk_forward_predictions(events)
        self.assertTrue(predictions)
        first = predictions[0]
        current = next(row for row in events if row["cusip"] == first["cusip"])
        eligible = [
            row for row in events
            if row["record_date"] < current["record_date"]
            and row["yield_end_date"] < current["record_date"]
        ]
        self.assertEqual(len(eligible), qfr.MODEL_WINDOW)

    def test_ols_recovers_linear_relationship(self):
        train = []
        for i in range(60):
            x1 = 1.5 + i * 0.02
            x2 = (i % 7) * 0.1
            x3 = (i % 5) - 2
            y = 2.0 + 3.0 * x1 - 1.5 * x2 + 0.25 * x3
            train.append({
                "x1": x1,
                "x2": x2,
                "x3": x3,
                "target_bp": y,
            })
        current = {"x1": 2.0, "x2": 0.3, "x3": 1.0}
        prediction = qfr.fit_ols_predict(train, current, ["x1", "x2", "x3"])
        expected = 2.0 + 3.0 * 2.0 - 1.5 * 0.3 + 0.25 * 1.0
        self.assertAlmostEqual(prediction, expected, places=5)

    def test_bootstrap_is_reproducible(self):
        rows = []
        for i in range(80):
            weak = i % 4 == 0
            rows.append({
                "weak_demand": weak,
                "target_bp": (2.0 if weak else -0.5) + (i % 5) * 0.01,
            })
        first = qfr.bootstrap_mean_difference(rows, reps=100)
        second = qfr.bootstrap_mean_difference(rows, reps=100)
        self.assertEqual(first, second)
        self.assertGreater(first["ci_95_high_bp"], first["ci_95_low_bp"])


    def _fred_csv_with_1000_rows(self):
        start = dt.date(2008, 1, 2)
        rows = ["observation_date,DGS10"]
        for offset in range(1000):
            rows.append(f"{(start + dt.timedelta(days=offset)).isoformat()},4.0")
        return ("\n".join(rows) + "\n").encode("utf-8")

    def test_treasury_all_pages_crosscheck_uses_zero_based_pagination(self):
        fred_body = self._fred_csv_with_1000_rows()
        page_zero = (
            b"<feed>"
            b"<entry><NEW_DATE>2008-01-02</NEW_DATE><BC_10YEAR>4.0</BC_10YEAR></entry>"
            b"<entry><NEW_DATE>2008-01-03</NEW_DATE><BC_10YEAR>4.0</BC_10YEAR></entry>"
            b"</feed>"
        )
        empty_page = b"<feed></feed>"
        with patch.object(qfr, "fetch_bytes", side_effect=[fred_body, page_zero, empty_page]) as fetch:
            values, meta = qfr.fetch_treasury_yields(dt.date(2010, 10, 1))
        self.assertEqual(len(values), 1000)
        self.assertEqual(meta["treasury_xml_crosscheck"]["status"], "VERIFIED")
        self.assertEqual(meta["treasury_xml_crosscheck"]["rows"], 2)
        self.assertIn("H.15 via FRED", meta["provider"])
        self.assertEqual(fetch.call_count, 3)
        self.assertIn("page=0", fetch.call_args_list[1].args[0])
        self.assertIn("page=1", fetch.call_args_list[2].args[0])

    def test_treasury_crosscheck_timeout_is_unavailable_not_zero_overlap(self):
        fred_body = self._fred_csv_with_1000_rows()
        with patch.object(qfr, "fetch_bytes", side_effect=[fred_body, TimeoutError("Treasury XML timeout")]):
            values, meta = qfr.fetch_treasury_yields(dt.date(2010, 10, 1))
        self.assertEqual(len(values), 1000)
        self.assertEqual(meta["treasury_xml_crosscheck"]["status"], "UNAVAILABLE")
        self.assertEqual(meta["treasury_xml_crosscheck"]["rows"], 0)
        self.assertIn("timeout", meta["treasury_xml_crosscheck"]["error"].lower())

    def test_updated_auction_probe_discovers_schema_and_result_xml(self):
        payload = {
            "data": [
                {
                    "record_date": "2026-11-16",
                    "cusip": "TESTCUSIP",
                    "security_type": "Note",
                    "security_desc": "10-Year Note",
                    "comp_auction_close_date": "2026-11-10",
                    "issue_date": "2026-11-16",
                    "maturity_date": "2036-11-15",
                    "original_security_term": "10-Year",
                    "security_term": "10-Year",
                    "inflation_protected": "No",
                    "floating_rate": "No",
                    "reopening": "No",
                    "bid_to_cover_ratio": "2.5",
                    "offering_amt": "1000",
                    "prim_deal_comp_par_awarded": "100",
                    "dir_bid_comp_par_awarded": "200",
                    "indir_bid_comp_par_awarded": "300",
                    "subtot_comp_inside_awrd": "600",
                    "xml_filenm_comp_results": "R_TEST.xml",
                    "pdf_filenm_comp_results": "R_TEST.pdf",
                },
                {
                    "record_date": "2026-11-24",
                    "cusip": "TESTCUSIP5",
                    "security_type": "Note",
                    "security_desc": "5-Year Note",
                    "comp_auction_close_date": "2026-11-24",
                },
            ],
            "meta": {"total-pages": "1", "total-count": "2"},
        }
        body = qfr.json.dumps(payload).encode("utf-8")
        xml_body = b"<AuctionResult><PrimaryDealerAccepted>100</PrimaryDealerAccepted><DirectBidderAccepted>200</DirectBidderAccepted><IndirectBidderAccepted>300</IndirectBidderAccepted></AuctionResult>"
        with patch.object(qfr, "fetch_bytes", side_effect=[body, xml_body]) as fetch:
            probe = qfr.fetch_updated_auction_probe(dt.date(2026, 11, 24))
        self.assertEqual(probe["status"], "SAMPLE_ONLY")
        self.assertEqual(probe["rows_returned"], 2)
        self.assertEqual(probe["target_matches"], 1)
        self.assertEqual(probe["target_sample"]["cusip"], "TESTCUSIP")
        self.assertIn("prim_deal_comp_par_awarded", probe["target_sample"]["result_fields"])
        self.assertIn("dir_bid_comp_par_awarded", probe["candidate_result_fields"])
        self.assertEqual(probe["target_sample"]["result_xml"]["status"], "PARSED")
        self.assertIn("PrimaryDealerAccepted", probe["target_sample"]["result_xml"]["tag_names"])
        self.assertEqual(fetch.call_count, 2)
        self.assertIn("page%5Bsize%5D=1000", fetch.call_args_list[0].args[0])

    def test_updated_auction_probe_requires_total_count_for_complete_page(self):
        payload = {
            "data": [{
                "record_date": "2026-11-16",
                "cusip": "TESTCUSIP",
                "security_type": "Note",
                "security_desc": "10-Year Note",
                "comp_auction_close_date": "2026-11-10",
            }],
            "meta": {"total-pages": "1"},
        }
        body = qfr.json.dumps(payload).encode("utf-8")
        with patch.object(qfr, "fetch_bytes", return_value=body):
            probe = qfr.fetch_updated_auction_probe(dt.date(2026, 11, 24))
        self.assertEqual(probe["status"], "PARTIAL")
        self.assertFalse(probe["page_complete"])

    def test_updated_target_window_is_incomplete_until_five_observations_are_available(self):
        probe = {"target_sample": {"record_date": "2026-11-16"}}
        yields = {
            dt.date(2026, 11, 17): 4.0,
            dt.date(2026, 11, 18): 4.1,
            dt.date(2026, 11, 19): 4.2,
            dt.date(2026, 11, 20): 4.3,
            dt.date(2026, 11, 23): 4.4,
        }
        qfr.attach_updated_target_window(probe, yields)
        self.assertEqual(probe["target_window"]["status"], "INCOMPLETE")
        self.assertEqual(probe["target_window"]["target_start"], "2026-11-17")
        self.assertEqual(probe["target_window"]["latest_yield_date"], "2026-11-23")


    def test_updated_auction_probe_fails_closed_when_endpoint_unavailable(self):
        with patch.object(qfr, "fetch_bytes", side_effect=RuntimeError("endpoint unavailable")):
            probe = qfr.fetch_updated_auction_probe(dt.date(2026, 11, 24))
        self.assertEqual(probe["status"], "UNAVAILABLE")
        self.assertEqual(probe["rows_returned"], 0)
        self.assertEqual(probe["target_matches"], 0)
        self.assertIn("endpoint unavailable", probe["error"])



if __name__ == "__main__":
    unittest.main()
