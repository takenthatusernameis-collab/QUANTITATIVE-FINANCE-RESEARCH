import csv
import datetime as dt
import io
import unittest

import h8_ci_credit_impulse_source_preflight as preflight


def synthetic_panel(vintages, *, age_days=4, missing_lag=False, irregular_gap=False):
    maps = {}
    all_dates = set()
    for vintage in vintages:
        vintage_date = dt.date.fromisoformat(vintage)
        latest = vintage_date - dt.timedelta(days=age_days)
        offsets = [0, 7, 14, 21, 28]
        if irregular_gap:
            offsets = [0, 7, 14, 28, 35]
        if missing_lag:
            offsets = [0, 7, 14, 21]
        values = {}
        for index, offset in enumerate(offsets):
            observation_date = latest - dt.timedelta(days=offset)
            values[observation_date] = 1000.0 - 10.0 * index
            all_dates.add(observation_date)
        maps[vintage] = values

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ["observation_date"]
        + [f"{preflight.SERIES_ID}_{value.replace('-', '')}" for value in vintages]
    )
    for observation_date in sorted(all_dates):
        row = [observation_date.isoformat()]
        for vintage in vintages:
            value = maps[vintage].get(observation_date)
            row.append("" if value is None else f"{value:.4f}")
        writer.writerow(row)
    return output.getvalue().encode("utf-8"), maps


class H8CICreditImpulseSourcePreflightTests(unittest.TestCase):
    def test_build_url_uses_exact_sunday_vintages_without_api_key(self):
        url = preflight.build_url(("2024-01-07", "2026-11-22"))
        self.assertIn("id=TOTCI%2CTOTCI", url)
        self.assertIn("vintage_date=2024-01-07%2C2026-11-22", url)
        self.assertNotIn("api_key", url)

    def test_build_url_rejects_non_sunday_duplicate_and_more_than_twelve(self):
        with self.assertRaises(ValueError):
            preflight.build_url(("2024-01-05",))
        with self.assertRaises(ValueError):
            preflight.build_url(("2024-01-07", "2024-01-07"))
        with self.assertRaises(ValueError):
            preflight.build_url(tuple("2024-01-07" for _ in range(13)))

    def test_parser_preserves_vintage_columns_and_missing_cells(self):
        vintages = ("2024-01-07",)
        raw, maps = synthetic_panel(vintages)
        raw = raw.replace(b"2023-12-13,970.0000", b"2023-12-13,.")
        panel = preflight.parse_vintage_csv(raw, vintages)
        self.assertNotIn(dt.date(2023, 12, 13), panel[vintages[0]])
        self.assertEqual(len(panel[vintages[0]]), 4)
        self.assertEqual(maps[vintages[0]][dt.date(2023, 12, 13)], 970.0)

    def test_parser_rejects_wrong_header_duplicate_dates_and_invalid_values(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages)
        with self.assertRaises(ValueError):
            preflight.parse_vintage_csv(raw.replace(b"observation_date", b"date"), vintages)

        duplicate = (
            b"observation_date,TOTCI_20240107\n"
            b"2024-01-03,1000\n"
            b"2024-01-03,990\n"
        )
        with self.assertRaises(ValueError):
            preflight.parse_vintage_csv(duplicate, vintages)

        invalid = b"observation_date,TOTCI_20240107\n2024-01-03,nan\n"
        with self.assertRaises(ValueError):
            preflight.parse_vintage_csv(invalid, vintages)

    def test_summary_accepts_weekly_wednesday_asof_vintage_and_four_interval_change(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages)
        panel = preflight.parse_vintage_csv(raw, vintages)
        summary = preflight.summarize_vintages(panel, vintages)[0]
        self.assertEqual(summary["latest_observation_date"], "2024-01-03")
        self.assertEqual(summary["latest_observation_age_days"], 4)
        self.assertEqual(summary["fourth_prior_observation_date"], "2023-12-06")
        self.assertEqual(summary["four_observation_span_days"], 28)
        self.assertGreater(summary["four_observation_log_change_pct"], 0)

    def test_summary_rejects_future_observation_dates(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages)
        text = raw.decode("utf-8")
        text += "2024-01-10,1010.0\n"
        panel = preflight.parse_vintage_csv(text.encode("utf-8"), vintages)
        with self.assertRaises(ValueError):
            preflight.summarize_vintages(panel, vintages)

    def test_summary_rejects_stale_observation(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages, age_days=15)
        panel = preflight.parse_vintage_csv(raw, vintages)
        with self.assertRaises(ValueError):
            preflight.summarize_vintages(panel, vintages)

    def test_summary_rejects_missing_fourth_prior_observation(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages, missing_lag=True)
        panel = preflight.parse_vintage_csv(raw, vintages)
        with self.assertRaises(ValueError):
            preflight.summarize_vintages(panel, vintages)

    def test_summary_rejects_irregular_weekly_observation_spacing(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages, irregular_gap=True)
        panel = preflight.parse_vintage_csv(raw, vintages)
        with self.assertRaises(ValueError):
            preflight.summarize_vintages(panel, vintages)

    def test_latest_vintage_history_minimum_is_enforced(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages)
        panel = preflight.parse_vintage_csv(raw, vintages)
        with self.assertRaises(ValueError):
            preflight.summarize_vintages(panel, vintages, min_history_rows=6)
        self.assertEqual(
            preflight.summarize_vintages(panel, vintages, min_history_rows=5)[0][
                "observations_since_2017_08_16"
            ],
            5,
        )

    def test_revision_statistics_use_only_common_observation_dates(self):
        observation_date = dt.date(2020, 3, 11)
        panel = {
            "2020-03-15": {observation_date: 100.0},
            "2026-11-22": {observation_date: 101.0},
        }
        stats = preflight.revision_stats(panel)
        self.assertEqual(stats["common_observations"], 1)
        self.assertEqual(stats["changed_observations"], 1)

    def test_canonical_hash_is_independent_of_mapping_insertion_order(self):
        vintages = ("2024-01-07",)
        raw, _ = synthetic_panel(vintages)
        panel = preflight.parse_vintage_csv(raw, vintages)
        reversed_panel = {
            vintage: dict(reversed(list(values.items())))
            for vintage, values in panel.items()
        }
        self.assertEqual(
            preflight.canonical_sha256(panel),
            preflight.canonical_sha256(reversed_panel),
        )


if __name__ == "__main__":
    unittest.main()
