"""Contract-aware Kraken perpetual funding-rate and payout semantics.

API fundingRate is the absolute rate; relativeFundingRate is the relative
hourly rate. They are not interchangeable. Positive rates debit longs and
credit shorts. This module uses Decimal for reproducible financial examples.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

ContractFamily = Literal["linear", "inverse"]
PositionSide = Literal["long", "short"]

INVERSE_METHOD_CUTOVER = datetime(2022, 9, 29, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FundingSpec:
    family: ContractFamily
    period_hours: Decimal
    multiplier: Decimal
    max_hourly_rate: Decimal | None
    settlement_currency: str
    position_unit: str
    regime: str
    cap_evidence: str


CURRENT_SPECS = {
    "linear": FundingSpec(
        family="linear",
        period_hours=Decimal("1"),
        multiplier=Decimal("8"),
        max_hourly_rate=Decimal("0.005"),
        settlement_currency="USD",
        position_unit="base-asset units (PF contractSize=1)",
        regime="current_hourly_linear",
        cap_evidence="Kraken Linear Multi-M contract specifications",
    ),
    "inverse": FundingSpec(
        family="inverse",
        period_hours=Decimal("1"),
        multiplier=Decimal("24"),
        max_hourly_rate=Decimal("0.0025"),
        settlement_currency="base asset (BTC or ETH)",
        position_unit="USD-notional contracts (PI contractSize=1 USD)",
        regime="current_hourly_inverse",
        cap_evidence="Kraken Inverse Coin-M contract specifications",
    ),
}

INVERSE_PRE_CUTOVER = FundingSpec(
    family="inverse",
    period_hours=Decimal("4"),
    multiplier=Decimal("8"),
    max_hourly_rate=Decimal("0.001"),
    settlement_currency="base asset (BTC or ETH)",
    position_unit="USD-notional contracts (PI contractSize=1 USD)",
    regime="pre_2022-09-29_4h_inverse",
    cap_evidence="Kraken inverse pre-2022-09-29 methodology",
)

# The historical source says the 4h -> 1h schedule change applied to all
# perpetuals, and the PF archive cadence is consistent with that boundary.
# The cited historical page is inverse-specific, however, so a PF pre-cutover
# cap is intentionally left unknown rather than copied from PI.
LINEAR_PRE_CUTOVER = FundingSpec(
    family="linear",
    period_hours=Decimal("4"),
    multiplier=Decimal("8"),
    max_hourly_rate=None,
    settlement_currency="USD",
    position_unit="base-asset units (PF contractSize=1)",
    regime="pre_2022-09-29_4h_linear_cap_unverified",
    cap_evidence="4h cadence supported; PF-specific historical cap not established",
)


def _decimal(name: str, value: object) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite decimal")
    return result


def _utc_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("effective_at must be an ISO-8601 timestamp") from exc
    if value.tzinfo is None:
        raise ValueError("effective_at must be timezone-aware")
    return value.astimezone(timezone.utc)


def funding_spec(
    family: ContractFamily,
    effective_at: datetime | str | None = None,
) -> FundingSpec:
    """Return the documented schedule applicable at a rate's effective time.

    For pre-cutover PF data the 4-hour cadence is supported by the archive and
    platform-wide wording in Kraken's historical methodology page, but the
    historical PF cap is not asserted because that page is inverse-specific.
    """
    if family not in CURRENT_SPECS:
        raise ValueError("family must be 'linear' or 'inverse'")
    timestamp = _utc_datetime(effective_at)
    if timestamp is not None and timestamp < INVERSE_METHOD_CUTOVER:
        return INVERSE_PRE_CUTOVER if family == "inverse" else LINEAR_PRE_CUTOVER
    return CURRENT_SPECS[family]


def _validate_period(spec: FundingSpec, elapsed_hours: object) -> Decimal:
    elapsed = _decimal("elapsed_hours", elapsed_hours)
    if elapsed < 0 or elapsed > spec.period_hours:
        raise ValueError(
            f"elapsed_hours must be between 0 and {spec.period_hours} "
            f"for {spec.regime}"
        )
    return elapsed


def absolute_rate_from_relative(
    family: ContractFamily,
    relative_rate: object,
    spot_price: object,
) -> Decimal:
    """Convert the relative hourly rate to the absolute rate per contract unit.

    Linear: USD per base-asset unit per hour = relative_rate * spot_price.
    Inverse: base-asset units per USD contract per hour = relative_rate / spot_price.
    """
    rate = _decimal("relative_rate", relative_rate)
    spot = _decimal("spot_price", spot_price)
    if spot <= 0:
        raise ValueError("spot_price must be positive")
    if family == "linear":
        return rate * spot
    if family == "inverse":
        return rate / spot
    raise ValueError("family must be 'linear' or 'inverse'")


def relative_rate_from_absolute(
    family: ContractFamily,
    absolute_rate: object,
    spot_price: object,
) -> Decimal:
    """Invert absolute_rate_from_relative."""
    absolute = _decimal("absolute_rate", absolute_rate)
    spot = _decimal("spot_price", spot_price)
    if spot <= 0:
        raise ValueError("spot_price must be positive")
    if family == "linear":
        return absolute / spot
    if family == "inverse":
        return absolute * spot
    raise ValueError("family must be 'linear' or 'inverse'")


def hourly_rate_from_average_premium(
    family: ContractFamily,
    average_premium: object,
    effective_at: datetime | str | None = None,
) -> Decimal:
    """Apply the documented multiplier once and the applicable hourly cap.

    Do not call this on Kraken's already-computed relativeFundingRate API
    field: that field is already the hourly relative rate.
    """
    spec = funding_spec(family, effective_at)
    premium = _decimal("average_premium", average_premium)
    hourly = premium / spec.multiplier
    if spec.max_hourly_rate is not None:
        cap = spec.max_hourly_rate
        hourly = max(-cap, min(cap, hourly))
    return hourly


def funding_payout(
    family: ContractFamily,
    side: PositionSide,
    position_units: object,
    relative_rate: object,
    spot_price: object,
    elapsed_hours: object = 1,
    effective_at: datetime | str | None = None,
) -> Decimal:
    """Return signed funding cashflow in the contract's settlement currency.

    position_units is base-asset units for PF linear contracts and USD
    notional contract units for PI inverse contracts. Positive output is a
    credit to the position holder; negative output is a debit.
    """
    if side not in ("long", "short"):
        raise ValueError("side must be 'long' or 'short'")
    spec = funding_spec(family, effective_at)
    quantity = _decimal("position_units", position_units)
    rate = _decimal("relative_rate", relative_rate)
    spot = _decimal("spot_price", spot_price)
    if quantity <= 0:
        raise ValueError("position_units must be positive")
    if spot <= 0:
        raise ValueError("spot_price must be positive")
    elapsed = _validate_period(spec, elapsed_hours)
    side_sign = Decimal("1") if side == "long" else Decimal("-1")
    if family == "linear":
        unit_payout = rate * spot
    else:
        unit_payout = rate / spot
    return -side_sign * quantity * unit_payout * elapsed


def funding_payout_from_absolute(
    family: ContractFamily,
    side: PositionSide,
    position_units: object,
    absolute_rate: object,
    elapsed_hours: object = 1,
    effective_at: datetime | str | None = None,
) -> Decimal:
    """Apply an absolute rate directly; result uses the family settlement currency."""
    if side not in ("long", "short"):
        raise ValueError("side must be 'long' or 'short'")
    spec = funding_spec(family, effective_at)
    quantity = _decimal("position_units", position_units)
    rate = _decimal("absolute_rate", absolute_rate)
    if quantity <= 0:
        raise ValueError("position_units must be positive")
    elapsed = _validate_period(spec, elapsed_hours)
    side_sign = Decimal("1") if side == "long" else Decimal("-1")
    return -side_sign * quantity * rate * elapsed
