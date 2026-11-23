import unittest
from decimal import Decimal

from kraken_funding_semantics import (
    INVERSE_METHOD_CUTOVER,
    absolute_rate_from_relative,
    funding_payout,
    funding_payout_from_absolute,
    funding_spec,
    hourly_rate_from_average_premium,
    relative_rate_from_absolute,
)


class KrakenFundingSemanticsTests(unittest.TestCase):
    def test_linear_official_example_pays_short_about_25_usd(self):
        payout = funding_payout("linear", "short", 2, "0.0003378375", 37000, 1)
        # Kraken's example rounds 24.999975 USD to 25.0 USD.
        self.assertEqual(payout, Decimal("24.9999750000"))

    def test_inverse_official_example_pays_short_000085_btc(self):
        payout = funding_payout("inverse", "short", 100000, "0.0000595", 7000, 1)
        self.assertEqual(payout, Decimal("0.0008500000000000000000000000000"))

    def test_positive_rate_debits_long_and_credits_short(self):
        long = funding_payout("linear", "long", 2, "0.0004", 37000, 1)
        short = funding_payout("linear", "short", 2, "0.0004", 37000, 1)
        self.assertEqual(long, Decimal("-29.6000"))
        self.assertEqual(short, Decimal("29.6000"))

    def test_negative_rate_credits_long(self):
        payout = funding_payout("inverse", "long", 200000, "-0.0004", 7000, 1)
        self.assertEqual(payout, Decimal("0.01142857142857142857142857143"))

    def test_absolute_and_relative_payouts_are_equivalent_linear(self):
        relative = Decimal("0.0003378375")
        spot = Decimal("37000")
        absolute = absolute_rate_from_relative("linear", relative, spot)
        self.assertEqual(absolute, Decimal("12.4999875000"))
        self.assertEqual(
            funding_payout("linear", "short", 2, relative, spot, "0.5"),
            funding_payout_from_absolute("linear", "short", 2, absolute, "0.5"),
        )
        self.assertEqual(relative_rate_from_absolute("linear", absolute, spot), relative)

    def test_absolute_and_relative_payouts_are_equivalent_inverse(self):
        relative = Decimal("0.0000595")
        spot = Decimal("7000")
        absolute = absolute_rate_from_relative("inverse", relative, spot)
        self.assertEqual(
            funding_payout("inverse", "short", 100000, relative, spot, "0.5"),
            funding_payout_from_absolute("inverse", "short", 100000, absolute, "0.5"),
        )
        self.assertEqual(relative_rate_from_absolute("inverse", absolute, spot), relative)

    def test_current_specs_keep_family_multipliers_caps_and_units_distinct(self):
        linear = funding_spec("linear")
        inverse = funding_spec("inverse")
        self.assertEqual(linear.period_hours, Decimal("1"))
        self.assertEqual(linear.multiplier, Decimal("8"))
        self.assertEqual(linear.max_hourly_rate, Decimal("0.005"))
        self.assertEqual(linear.settlement_currency, "USD")
        self.assertEqual(inverse.period_hours, Decimal("1"))
        self.assertEqual(inverse.multiplier, Decimal("24"))
        self.assertEqual(inverse.max_hourly_rate, Decimal("0.0025"))
        self.assertIn("USD-notional", inverse.position_unit)

    def test_historical_inverse_regime_uses_four_hour_period_n8_and_01_percent_cap(self):
        spec = funding_spec("inverse", "2022-09-29T11:59:59Z")
        self.assertEqual(spec.period_hours, Decimal("4"))
        self.assertEqual(spec.multiplier, Decimal("8"))
        self.assertEqual(spec.max_hourly_rate, Decimal("0.001"))
        self.assertEqual(funding_spec("inverse", INVERSE_METHOD_CUTOVER).period_hours, Decimal("1"))

    def test_pre_cutover_linear_period_is_four_hours_but_cap_is_not_assumed(self):
        spec = funding_spec("linear", "2022-09-29T11:59:59Z")
        self.assertEqual(spec.period_hours, Decimal("4"))
        self.assertEqual(spec.multiplier, Decimal("8"))
        self.assertIsNone(spec.max_hourly_rate)

    def test_average_premium_multiplier_and_cap_are_applied_once(self):
        self.assertEqual(hourly_rate_from_average_premium("linear", "0.0027027"), Decimal("0.0003378375"))
        self.assertEqual(hourly_rate_from_average_premium("inverse", "0.001428"), Decimal("0.0000595"))
        self.assertEqual(hourly_rate_from_average_premium("linear", "0.08"), Decimal("0.005"))
        self.assertEqual(hourly_rate_from_average_premium("inverse", "0.12"), Decimal("0.0025"))

    def test_historical_inverse_rate_uses_old_multiplier_and_cap(self):
        self.assertEqual(
            hourly_rate_from_average_premium("inverse", "0.014", "2022-09-29T11:00:00Z"),
            Decimal("0.001"),
        )

    def test_elapsed_time_is_bounded_by_the_applicable_funding_period(self):
        self.assertEqual(funding_payout("linear", "short", 1, "0.001", 100, "0.5"), Decimal("0.0500"))
        self.assertEqual(
            funding_payout("inverse", "short", 1000, "0.001", 100, 4, "2022-09-29T11:00:00Z"),
            Decimal("0.04000"),
        )
        with self.assertRaisesRegex(ValueError, "elapsed_hours"):
            funding_payout("linear", "short", 1, "0.001", 100, 1.01)
        with self.assertRaisesRegex(ValueError, "elapsed_hours"):
            funding_payout("inverse", "short", 1, "0.001", 100, 4.01, "2022-09-29T11:00:00Z")

    def test_invalid_units_rates_and_sides_fail_closed(self):
        for kwargs in [
            {"family": "linear", "side": "long", "position_units": 0, "relative_rate": 0.001, "spot_price": 100, "elapsed_hours": 1},
            {"family": "inverse", "side": "short", "position_units": 1, "relative_rate": 0.001, "spot_price": 0, "elapsed_hours": 1},
            {"family": "linear", "side": "sideways", "position_units": 1, "relative_rate": 0.001, "spot_price": 100, "elapsed_hours": 1},
            {"family": "linear", "side": "long", "position_units": 1, "relative_rate": float("nan"), "spot_price": 100, "elapsed_hours": 1},
        ]:
            with self.assertRaises(ValueError):
                funding_payout(**kwargs)


if __name__ == "__main__":
    unittest.main()
