from __future__ import annotations

import datetime as dt
import json
import math
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import btc_cross_venue_funding_dispersion_source_preflight as model


def stamp_ms(day: dt.date, hour: int) -> int:
    stamp = dt.datetime.combine(day, dt.time(hour), tzinfo=dt.timezone.utc)
    return int(stamp.timestamp() * 1000)


def mexc_row(day: dt.date, hour: int, rate: float = 0.0001) -> dict:
    return {
        "symbol": "BTC_USDT",
        "funding_rate": rate,
        "settle_time_ms": stamp_ms(day, hour),
        "settle_time_utc": dt.datetime.fromtimestamp(stamp_ms(day, hour) / 1000, dt.timezone.utc).isoformat(),
        "settle_date": day,
        "settle_hour": hour,
        "collect_cycle_hours": 8,
    }


def binance_row(day: dt.date, hour: int, rate: float = 0.0002) -> dict:
    return {
        "symbol": "BTCUSDT",
        "funding_rate": rate,
        "settle_time_ms": stamp_ms(day, hour),
        "settle_time_utc": dt.datetime.fromtimestamp(stamp_ms(day, hour) / 1000, dt.timezone.utc).isoformat(),
        "settle_date": day,
        "settle_hour": hour,
    }


def raw_binance_row(day: dt.date, hour: int, rate: str = "0.0002") -> dict:
    return {"symbol": "BTCUSDT", "fundingRate": rate, "fundingTime": stamp_ms(day, hour)}


def three_slot_rows(start: dt.date, days: int, factory, rate: float) -> list[dict]:
    return [
        factory(start + dt.timedelta(days=offset), hour, rate + offset * 0.000001)
        for offset in range(days)
        for hour in model.SLOT_HOURS
    ]


class CrossVenueFundingDispersionSourcePreflightTests(unittest.TestCase):
    def test_binance_parser_accepts_documented_ascending_funding_rows(self):
        day = dt.date(2026, 1, 2)
        payload = [
            raw_binance_row(day, 0, "0.0001"),
            raw_binance_row(day, 8, "-0.0002"),
            raw_binance_row(day, 16, "0.0003"),
        ]
        parsed = model.parse_binance_funding_page(
            json.dumps(payload).encode(),
            stamp_ms(day, 0),
            stamp_ms(day, 16),
        )
        self.assertEqual([row["settle_hour"] for row in parsed], [0, 8, 16])
        self.assertAlmostEqual(parsed[1]["funding_rate"], -0.0002)

    def test_binance_parser_rejects_wrong_symbol_nonfinite_rate_and_off_grid_time(self):
        day = dt.date(2026, 1, 2)
        wrong_symbol = raw_binance_row(day, 0)
        wrong_symbol["symbol"] = "ETHUSDT"
        with self.assertRaisesRegex(ValueError, "unexpected symbol"):
            model.parse_binance_funding_page(json.dumps([wrong_symbol]).encode(), 0, 2**63 - 1)
        bad_rate = raw_binance_row(day, 0, "NaN")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            model.parse_binance_funding_page(json.dumps([bad_rate]).encode(), 0, 2**63 - 1)
        off_grid = raw_binance_row(day, 1)
        with self.assertRaisesRegex(ValueError, "off the frozen"):
            model.parse_binance_funding_page(json.dumps([off_grid]).encode(), 0, 2**63 - 1)

    def test_binance_parser_rejects_duplicates_unsorted_and_out_of_window_rows(self):
        day = dt.date(2026, 1, 2)
        first = raw_binance_row(day, 0)
        duplicate = raw_binance_row(day, 0, "0.0003")
        with self.assertRaisesRegex(ValueError, "strictly ascending"):
            model.parse_binance_funding_page(json.dumps([first, duplicate]).encode(), 0, 2**63 - 1)
        later = raw_binance_row(day, 8)
        with self.assertRaisesRegex(ValueError, "strictly ascending"):
            model.parse_binance_funding_page(json.dumps([later, first]).encode(), 0, 2**63 - 1)
        with self.assertRaisesRegex(ValueError, "outside"):
            model.parse_binance_funding_page(json.dumps([first]).encode(), stamp_ms(day, 8), stamp_ms(day, 16))

    def test_binance_funding_pagination_advances_by_last_timestamp_plus_one_ms(self):
        start = dt.date(2026, 1, 2)
        all_rows = [
            raw_binance_row(start - dt.timedelta(days=1), 16),
            raw_binance_row(start, 0),
            raw_binance_row(start, 8),
            raw_binance_row(start, 16),
            raw_binance_row(start + dt.timedelta(days=1), 0),
        ]
        requested = []

        def fake_fetch(url, timeout=25):
            query = parse_qs(urlsplit(url).query)
            cursor = int(query["startTime"][0])
            end = int(query["endTime"][0])
            requested.append(cursor)
            rows = [
                row for row in all_rows
                if cursor <= int(row["fundingTime"]) <= end
            ][:3]
            return json.dumps(rows).encode()

        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", start),
            patch.object(model, "PAGE_SIZE", 3),
            patch.object(model, "MAX_PAGES", 3),
            patch.object(model.base, "fetch_bytes", side_effect=fake_fetch),
        ):
            rows, source = model.fetch_binance_funding_history()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(source["retrieved_pages"]), 2)
        self.assertEqual(requested[1], rows[2]["settle_time_ms"] + 1)
        self.assertEqual(source["cadence"]["missing_eight_hour_intervals"], 0)

    def test_eight_hour_validator_allows_counted_missing_slots_but_rejects_sub_eight_hour_cadence(self):
        start = dt.date(2026, 1, 2)
        rows = [
            binance_row(start - dt.timedelta(days=1), 16),
            binance_row(start, 0),
            binance_row(start, 16),
            binance_row(start + dt.timedelta(days=1), 0),
        ]
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", start),
        ):
            result = model.validate_eight_hour_history(rows, "Binance")
        self.assertEqual(result["missing_eight_hour_intervals"], 1)
        bad = rows[:2] + [binance_row(start, 8), binance_row(start, 16), rows[-1]]
        bad.insert(2, {
            **binance_row(start, 0),
            "settle_time_ms": stamp_ms(start, 1),
        })
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", start),
        ):
            with self.assertRaisesRegex(ValueError, "off the common 8-hour grid"):
                model.validate_eight_hour_history(bad, "Binance")

    def test_mexc_history_requires_eight_hour_collect_cycle_and_exact_boundaries(self):
        start = dt.date(2026, 1, 2)
        end = start + dt.timedelta(days=1)
        rows = [
            mexc_row(start - dt.timedelta(days=1), 16),
            *three_slot_rows(start, 2, mexc_row, 0.0001),
            mexc_row(end + dt.timedelta(days=1), 0),
        ]
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
        ):
            selected, coverage = model.validate_mexc_history(rows)
        self.assertEqual(len(selected), 8)
        self.assertEqual(coverage["non_eight_hour_intervals"], 0)
        wrong = [dict(row) for row in selected]
        wrong[1]["collect_cycle_hours"] = 4
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
        ):
            with self.assertRaisesRegex(ValueError, "non-eight-hour collectCycle"):
                model.validate_eight_hour_history(wrong, "MEXC")

    def test_match_uses_only_exact_common_three_slot_days(self):
        start = dt.date(2026, 1, 1)
        end = start + dt.timedelta(days=3)
        m_rows = three_slot_rows(start, 4, mexc_row, 0.0001)
        b_rows = three_slot_rows(start, 4, binance_row, 0.0002)
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "MIN_MATCHED_DAYS", 4),
            patch.object(model, "MAX_INCOMPLETE_SHARE", 0.0),
            patch.object(model, "MAX_MISSING_RUN", 0),
        ):
            matched, coverage = model.match_funding_days(m_rows, b_rows)
        self.assertEqual(coverage["matched_days"], 4)
        self.assertAlmostEqual(matched[start]["mean_abs_funding_spread_bps"], 1.0)

    def test_missing_settlement_is_not_forward_filled_or_counted_as_a_match(self):
        start = dt.date(2026, 1, 1)
        end = start + dt.timedelta(days=3)
        m_rows = three_slot_rows(start, 4, mexc_row, 0.0001)
        b_rows = three_slot_rows(start, 4, binance_row, 0.0002)
        missing_day = start + dt.timedelta(days=1)
        b_rows = [
            row for row in b_rows
            if not (row["settle_date"] == missing_day and row["settle_hour"] == 8)
        ]
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "MIN_MATCHED_DAYS", 3),
            patch.object(model, "MAX_INCOMPLETE_SHARE", 0.25),
            patch.object(model, "MAX_MISSING_RUN", 1),
        ):
            matched, coverage = model.match_funding_days(m_rows, b_rows)
        self.assertNotIn(missing_day, matched)
        self.assertEqual(coverage["missing_dates"], [missing_day.isoformat()])
        self.assertEqual(coverage["matched_days"], 3)

    def test_match_fails_when_incomplete_share_or_missing_run_exceeds_frozen_gate(self):
        start = dt.date(2026, 1, 1)
        end = start + dt.timedelta(days=4)
        m_rows = three_slot_rows(start, 5, mexc_row, 0.0001)
        b_rows = three_slot_rows(start, 5, binance_row, 0.0002)
        b_rows = [row for row in b_rows if row["settle_date"] != start + dt.timedelta(days=2)]
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "MIN_MATCHED_DAYS", 4),
            patch.object(model, "MAX_INCOMPLETE_SHARE", 0.10),
            patch.object(model, "MAX_MISSING_RUN", 0),
        ):
            with self.assertRaisesRegex(ValueError, "coverage fails"):
                model.match_funding_days(m_rows, b_rows)

    def test_event_builder_uses_next_session_only_and_frozen_spread_feature(self):
        start = dt.date(2026, 1, 6)
        price_start = start - dt.timedelta(days=5)
        prices = {}
        close = 100.0
        for offset in range(10):
            day = price_start + dt.timedelta(days=offset)
            close *= math.exp(-0.01 if offset == 6 else 0.002)
            prices[day] = close
        matched = {
            start + dt.timedelta(days=offset): {"mean_abs_funding_spread_bps": 1.0 + offset}
            for offset in range(4)
        }
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", start + dt.timedelta(days=3)),
            patch.object(model, "PRICE_START_DATE", price_start),
            patch.object(model, "PRICE_END_DATE", start + dt.timedelta(days=4)),
        ):
            events, metadata = model.build_events(matched, prices)
        self.assertEqual(len(events), 4)
        first = events[0]
        self.assertEqual(first["signal_date"], start)
        self.assertEqual(first["target_start_date"], start + dt.timedelta(days=1))
        self.assertEqual(first["target_end_date"], start + dt.timedelta(days=1))
        expected_return = math.log(prices[start + dt.timedelta(days=1)] / prices[start])
        self.assertAlmostEqual(
            first["target_downside_loss_pct2"],
            max(-expected_return, 0.0) ** 2 * 10_000,
        )
        self.assertEqual(first["mean_abs_funding_spread_bps"], 1.0)
        self.assertEqual(metadata["accepted_events"], 4)

    def test_source_preflight_is_explicitly_source_only_and_never_fits_a_model(self):
        start = dt.date(2026, 1, 2)
        end = start + dt.timedelta(days=3)
        boundary_before = start - dt.timedelta(days=1)
        boundary_after = end + dt.timedelta(days=1)
        m_rows = [mexc_row(boundary_before, 16)]
        b_rows = [binance_row(boundary_before, 16)]
        for offset in range(4):
            day = start + dt.timedelta(days=offset)
            m_rows.extend(mexc_row(day, hour) for hour in model.SLOT_HOURS)
            b_rows.extend(binance_row(day, hour) for hour in model.SLOT_HOURS)
        m_rows.append(mexc_row(boundary_after, 0))
        b_rows.append(binance_row(boundary_after, 0))
        price_start = start - dt.timedelta(days=5)
        price_end = end + dt.timedelta(days=1)
        prices = {}
        close = 100.0
        for offset in range((price_end - price_start).days + 1):
            day = price_start + dt.timedelta(days=offset)
            close *= 1.001
            prices[day] = close
        mexc_source = {"page_manifest_sha256": "a" * 64}
        binance_source = {"page_manifest_sha256": "b" * 64}
        spot_source = {"archive_manifest_sha256": "c" * 64}
        with (
            patch.object(model, "START_DATE", start),
            patch.object(model, "END_DATE", end),
            patch.object(model, "PRICE_START_DATE", price_start),
            patch.object(model, "PRICE_END_DATE", price_end),
            patch.object(model, "MIN_MATCHED_DAYS", 4),
            patch.object(model, "MAX_INCOMPLETE_SHARE", 0.0),
            patch.object(model, "MAX_MISSING_RUN", 0),
            patch.object(model, "MIN_ACCEPTED_EVENTS", 1),
            patch.object(model.mexc, "fetch_funding_history", return_value=(m_rows, mexc_source)),
            patch.object(model, "fetch_binance_funding_history", return_value=(b_rows, binance_source)),
            patch.object(model.mexc, "fetch_binance_prices", return_value=(prices, spot_source)),
            patch.object(model.base, "fit_ols_predict", side_effect=AssertionError("model fit must not run")),
        ):
            result = model.run_source_preflight()
        self.assertTrue(result["source_preflight_only"])
        self.assertFalse(result["completed_backtest"])
        self.assertFalse(result["model_fit_executed"])
        self.assertEqual(result["accepted_event_count"], 4)
        self.assertNotIn("validation", result)
        self.assertNotIn("test", result)


if __name__ == "__main__":
    unittest.main()
