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


    def test_paired_squared_loss_bootstrap_is_reproducible_and_favors_augmented(self):
        rows = []
        for i in range(46):
            target = float((i % 9) - 4)
            baseline_error = 2.0 + (i % 3) * 0.1
            augmented_error = 1.0 + (i % 2) * 0.1
            rows.append({
                "record_date": dt.date(2023, 1, 1) + dt.timedelta(days=i * 14),
                "cusip": f"C{i:03d}",
                "target_bp": target,
                "baseline_prediction_bp": target + baseline_error,
                "augmented_prediction_bp": target + augmented_error,
            })
        first = qfr.bootstrap_paired_squared_loss_difference(rows, reps=200)
        second = qfr.bootstrap_paired_squared_loss_difference(list(reversed(rows)), reps=200)
        self.assertEqual(first, second)
        self.assertEqual(first["observations"], 46)
        self.assertGreater(first["observed_mean_baseline_minus_augmented_squared_loss_bp2"], 0)
        self.assertGreater(first["ci_95_low_bp2"], 0)
        self.assertEqual(first["bootstrap_fraction_positive"], 1.0)

    def test_paired_squared_loss_bootstrap_negative_difference_favors_baseline(self):
        rows = []
        for i in range(40):
            target = float(i % 7)
            rows.append({
                "record_date": dt.date(2023, 1, 1) + dt.timedelta(days=i * 14),
                "cusip": f"N{i:03d}",
                "target_bp": target,
                "baseline_prediction_bp": target + 1.0,
                "augmented_prediction_bp": target + 2.0,
            })
        result = qfr.bootstrap_paired_squared_loss_difference(rows, reps=100)
        self.assertEqual(result["observed_mean_baseline_minus_augmented_squared_loss_bp2"], -3.0)
        self.assertLess(result["ci_95_high_bp2"], 0)

    def test_paired_squared_loss_bootstrap_rejects_short_or_invalid_samples(self):
        rows = []
        for i in range(29):
            target = float(i % 5)
            rows.append({
                "record_date": dt.date(2023, 1, 1) + dt.timedelta(days=i * 14),
                "cusip": f"S{i:03d}",
                "target_bp": target,
                "baseline_prediction_bp": target + 1.0,
                "augmented_prediction_bp": target + 0.5,
            })
        self.assertIsNone(qfr.bootstrap_paired_squared_loss_difference(rows, reps=100))
        rows.append({
            "record_date": dt.date(2024, 3, 1),
            "cusip": "INVALID",
            "target_bp": 1.0,
            "baseline_prediction_bp": float("nan"),
            "augmented_prediction_bp": 0.5,
        })
        self.assertIsNone(qfr.bootstrap_paired_squared_loss_difference(rows, reps=100))

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



    def _updated_auction_sample(self):
        api_fields = {
            "bid_to_cover_ratio": "2.46",
            "offering_amt": "42000000000",
            "prim_deal_comp_par_awarded": "4080513500",
            "dir_bid_comp_par_awarded": "12109950200",
            "indir_bid_comp_par_awarded": "25566955000",
            "subtot_comp_inside_awrd": "41757418700",
            "subtot_comp_outside_awrd": "0",
            "grand_total_par_awarded": "50519618200",
            "prim_deal_comp_par_recog": "57556000000",
            "dir_bid_comp_par_recog": "16167600000",
            "indir_bid_comp_par_recog": "29336438000",
            "subtot_comp_inside_recog": "103060038000",
            "subtot_comp_outside_recog": "0",
            "grand_total_par_recog": "111822237500",
        }
        xml_values = [
            ("CUSIP", "91282CRX1"),
            ("SecurityType", "Note"),
            ("SecurityDescription", "10-Year Note"),
            ("CompetitiveAuctionCloseDate", "2026-11-10"),
            ("InflationProtected", "N"),
            ("FloatingRate", "N"),
            ("Reopening", "N"),
            ("BidToCoverRatio", "2.46"),
            ("OfferingAmount", "42000000000"),
            ("PrimaryDealersCompetitiveParAwarded", "4080513500"),
            ("DirectBiddersCompetitiveParAwarded", "12109950200"),
            ("IndirectBiddersCompetitiveParAwarded", "25566955000"),
            ("SubtotalCompetitiveParAwardedInsideOfOfferingAmount", "41757418700"),
            ("SubtotalCompetitiveParAwardedOutsideOfOfferingAmount", "0"),
            ("GrandTotalParAwarded", "50519618200"),
            ("PrimaryDealersCompetitiveParRecognized", "57556000000"),
            ("DirectBiddersCompetitiveParRecognized", "16167600000"),
            ("IndirectBiddersCompetitiveParRecognized", "29336438000"),
            ("SubtotalCompetitiveParRecognizedInsideOfOfferingAmount", "103060038000"),
            ("SubtotalCompetitiveParRecognizedOutsideOfOfferingAmount", "0"),
            ("GrandTotalParRecognized", "111822237500"),
        ]
        return {
            "record_date": "2026-11-16",
            "cusip": "91282CRX1",
            "security_type": "Note",
            "security_desc": "10-Year Note",
            "comp_auction_close_date": "2026-11-10",
            "inflation_protected": "No",
            "floating_rate": "No",
            "reopening": "No",
            "result_fields": api_fields,
            "result_xml": {
                "status": "PARSED",
                "candidate_values": [{"name": name, "value": value} for name, value in xml_values],
            },
        }

    def test_updated_auction_awarded_fields_reconcile_to_official_xml(self):
        result = qfr.reconcile_updated_auction_sample(self._updated_auction_sample())
        self.assertEqual(result["status"], "RECONCILED_SAMPLE_ONLY")
        crosswalk = result["legacy_crosswalk"]
        self.assertEqual(crosswalk["comp_accepted"], 41757418700.0)
        self.assertEqual(crosswalk["primary_dealer_accepted"], 4080513500.0)
        self.assertAlmostEqual(crosswalk["dealer_share"], 4080513500 / 41757418700, places=12)
        self.assertEqual(result["award_identity"]["difference"], 0.0)
        self.assertEqual(
            result["recognized_amounts_not_used_for_award_share"]["primary_dealer_competitive_recognized"],
            57556000000.0,
        )

    def test_updated_auction_api_xml_amount_mismatch_fails_closed(self):
        sample = self._updated_auction_sample()
        sample["result_fields"]["prim_deal_comp_par_awarded"] = "4080513502"
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("prim_deal_comp_par_awarded", result["reason"])

    def test_updated_auction_award_identity_mismatch_fails_closed(self):
        sample = self._updated_auction_sample()
        sample["result_fields"]["subtot_comp_inside_awrd"] = "41757418800"
        for item in sample["result_xml"]["candidate_values"]:
            if item["name"] == "SubtotalCompetitiveParAwardedInsideOfOfferingAmount":
                item["value"] = "41757418800"
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("do not sum", result["reason"])

    def test_updated_auction_crosswalk_requires_complete_result_xml(self):
        sample = self._updated_auction_sample()
        sample["result_xml"]["candidate_values"] = []
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "INCOMPLETE")


    def test_updated_auction_boolean_fields_accept_api_no_and_xml_n(self):
        sample = self._updated_auction_sample()
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "RECONCILED_SAMPLE_ONLY")
        checks = {item["api_field"]: item for item in result["field_checks"]}
        for field in ("inflation_protected", "floating_rate", "reopening"):
            self.assertTrue(checks[field]["matched"])
            self.assertEqual(checks[field]["api_value"], "No")
            self.assertEqual(checks[field]["xml_value"], "N")
        sample["floating_rate"] = "Yes"
        mismatch = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(mismatch["status"], "MISMATCH")
        self.assertIn("floating_rate", mismatch["reason"])


    def test_updated_ten_year_note_classifier_uses_original_term_and_security_type(self):
        self.assertTrue(qfr.is_updated_ten_year_note({
            "security_type": "Note",
            "original_security_term": "10-Year",
            "security_desc": "9-Year 11-Month Note",
        }))
        self.assertFalse(qfr.is_updated_ten_year_note({
            "security_type": "Note",
            "original_security_term": "5-Year",
            "security_desc": "5-Year Note",
        }))
        self.assertFalse(qfr.is_updated_ten_year_note({
            "security_type": "Bill",
            "original_security_term": "10-Year",
            "security_desc": "10-Year Bill",
        }))

    def test_updated_api_xml_crosswalk_checks_record_date_order(self):
        sample = self._updated_auction_sample()
        sample["record_date"] = "2026-11-09"
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("precedes", result["reason"])

    def test_updated_api_population_reconciles_every_nominal_ten_year_row_and_legacy_overlap(self):
        base = self._updated_auction_sample()

        def make_row(cusip, auction_date, record_date, xml_name, inflation="No", floating="No", term="10-Year"):
            xml_values = [
                {"name": item["name"], "value": item["value"]}
                for item in base["result_xml"]["candidate_values"]
            ]
            for item in xml_values:
                if item["name"] == "CUSIP":
                    item["value"] = cusip
                elif item["name"] == "CompetitiveAuctionCloseDate":
                    item["value"] = auction_date
            xml_body = (
                "<AuctionResult>"
                + "".join(f"<{item['name']}>{item['value']}</{item['name']}>" for item in xml_values)
                + "</AuctionResult>"
            ).encode("utf-8")
            row = {
                "record_date": record_date,
                "cusip": cusip,
                "security_type": "Note",
                "security_desc": "10-Year Note" if term == "10-Year" else "5-Year Note",
                "comp_auction_close_date": auction_date,
                "original_security_term": term,
                "inflation_protected": inflation,
                "floating_rate": floating,
                "reopening": "No",
                "xml_filenm_comp_results": xml_name,
                **base["result_fields"],
            }
            return row, xml_body

        first, first_xml = make_row("91282CRX0", "2026-10-07", "2026-10-08", "R_20261007.xml")
        second, second_xml = make_row("91282CRX1", "2026-11-10", "2026-11-16", "R_20261110.xml")
        tips, _ = make_row("TIPS-CUSIP", "2026-10-15", "2026-10-16", "R_TIPS.xml", inflation="Yes")
        five_year, _ = make_row("FIVE-CUSIP", "2026-10-20", "2026-10-21", "R_5Y.xml", term="5-Year")
        payload = {
            "data": [first, second, tips, five_year],
            "meta": {"total-pages": "1", "total-count": "4"},
        }
        legacy = [{
            "cusip": "91282CRX0",
            "auction_date": dt.date(2026, 10, 7),
            "record_date": dt.date(2026, 10, 8),
            "bid_to_cover": 2.46,
            "comp_accepted": 41757418700.0,
            "primary_dealer_accepted": 4080513500.0,
            "direct_bidder_accepted": 12109950200.0,
            "indirect_bidder_accepted": 25566955000.0,
        }]
        with patch.object(
            qfr,
            "fetch_bytes",
            side_effect=[qfr.json.dumps(payload).encode("utf-8"), first_xml, second_xml],
        ) as fetch:
            probe = qfr.fetch_updated_auction_probe(
                dt.date(2026, 11, 24), legacy_auctions=legacy
            )
        self.assertTrue(probe["page_complete"])
        self.assertEqual(probe["candidate_population"]["ten_year_note_rows"], 3)
        self.assertEqual(probe["candidate_population"]["nominal_fixed_rows"], 2)
        self.assertEqual(probe["candidate_population"]["excluded_tips_or_floating"], 1)
        self.assertEqual(probe["candidate_population"]["reconciled_rows"], 2)
        self.assertEqual(probe["candidate_population"]["status"], "RECONCILED_SAMPLE_ONLY")
        self.assertEqual(probe["legacy_overlap"]["status"], "VERIFIED")
        self.assertEqual(probe["legacy_overlap"]["matched_rows"], 1)
        self.assertEqual(probe["legacy_overlap"]["no_legacy_match_rows"], 1)
        self.assertEqual(probe["target_matches"], 1)
        self.assertEqual(probe["target_sample"]["cusip"], "91282CRX1")
        self.assertEqual(fetch.call_count, 3)


    def test_updated_auction_legacy_xml_schema_and_billions_offering_amount_reconcile(self):
        sample = {
            "record_date": "2026-10-15",
            "cusip": "91282CRF0",
            "security_type": "Note",
            "security_desc": "9-Year 10-Month Note",
            "comp_auction_close_date": "2026-10-07",
            "inflation_protected": "No",
            "floating_rate": "No",
            "reopening": "Yes",
            "result_fields": {
                "bid_to_cover_ratio": "2.77",
                "offering_amt": "39000000000",
                "prim_deal_comp_par_awarded": "984000000",
                "dir_bid_comp_par_awarded": "6618200000",
                "indir_bid_comp_par_awarded": "31063238000",
                "subtot_comp_inside_awrd": "38665438000",
                "subtot_comp_outside_awrd": "null",
                "grand_total_par_awarded": "39926321900",
                "prim_deal_comp_par_recog": "52876000000",
                "dir_bid_comp_par_recog": "14852200000",
                "indir_bid_comp_par_recog": "40006206000",
                "subtot_comp_inside_recog": "107734406000",
                "subtot_comp_outside_recog": "null",
                "grand_total_par_recog": "108995289900",
            },
            "result_xml": {
                "status": "PARSED",
                "candidate_values": [
                    {"name": "SecurityTermWeekYear", "value": "9-YEAR"},
                    {"name": "SecurityTermDayMonth", "value": "10-MONTH"},
                    {"name": "SecurityType", "value": "NOTE"},
                    {"name": "CUSIP", "value": "91282CRF0"},
                    {"name": "AuctionDate", "value": "2026-10-07"},
                    {"name": "OfferingAmount", "value": "39.000"},
                    {"name": "InflationIndexSecurity", "value": "N"},
                    {"name": "FloatingRate", "value": "N"},
                    {"name": "ReOpeningIndicator", "value": "Y"},
                    {"name": "BidToCoverRatio", "value": "2.77"},
                    {"name": "PrimaryDealerAccepted", "value": "984000000"},
                    {"name": "DirectBidderAccepted", "value": "6618200000"},
                    {"name": "IndirectBidderAccepted", "value": "31063238000"},
                    {"name": "CompetitiveAccepted", "value": "38665438000"},
                    {"name": "TotalAccepted", "value": "39926321900"},
                    {"name": "PrimaryDealerTendered", "value": "52876000000"},
                    {"name": "DirectBidderTendered", "value": "14852200000"},
                    {"name": "IndirectBidderTendered", "value": "40006206000"},
                    {"name": "CompetitiveTendered", "value": "107734406000"},
                    {"name": "TotalTendered", "value": "108995289900"},
                ],
            },
        }
        result = qfr.reconcile_updated_auction_sample(sample)
        self.assertEqual(result["status"], "RECONCILED_SAMPLE_ONLY")
        self.assertEqual(result["schema_variant"], "LEGACY_AUCTION_RESULT_XML")
        self.assertEqual(result["legacy_crosswalk"]["comp_accepted"], 38665438000.0)
        self.assertAlmostEqual(
            result["legacy_crosswalk"]["dealer_share"],
            984000000 / 38665438000,
            places=12,
        )
        self.assertEqual(
            result["award_identity"]["denominator_source"],
            "official XML CompetitiveAccepted; legacy API outside-award split unavailable",
        )
        self.assertEqual(
            result["optional_absent_fields"],
            ["subtot_comp_outside_awrd", "subtot_comp_outside_recog"],
        )
        checks = {item["api_field"]: item for item in result["field_checks"]}
        self.assertEqual(checks["offering_amt"]["xml_scale_factor"], 1_000_000_000.0)
        self.assertEqual(checks["comp_auction_close_date"]["xml_field"], "AuctionDate")
        self.assertEqual(checks["reopening"]["xml_field"], "ReOpeningIndicator")
        self.assertEqual(checks["security_desc"]["xml_field"], "SecurityTermWeekYear+SecurityTermDayMonth")

        legacy = [{
            "cusip": "91282CRF0",
            "auction_date": dt.date(2026, 10, 7),
            "record_date": dt.date(2026, 10, 15),
            "bid_to_cover": 2.77,
            "comp_accepted": 38665438000.0,
            "primary_dealer_accepted": 984000000.0,
            "direct_bidder_accepted": 6618200000.0,
            "indirect_bidder_accepted": 31063238000.0,
        }]
        sample["reconciliation"] = result
        overlap = qfr.compare_updated_auction_sample_to_legacy(sample, legacy)
        self.assertEqual(overlap["status"], "MATCH")


if __name__ == "__main__":
    unittest.main()
