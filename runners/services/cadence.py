
# runners/services/cadence.py

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


INCHES_PER_MILE = Decimal("63360")
SECONDS_PER_MINUTE = Decimal("60")


@dataclass(frozen=True)
class CadenceResult:
    target_pace_seconds: int
    cadence_spm: Decimal
    step_length_inches: Decimal
    source: str


def calculate_cadence(
    pace_seconds: int,
    step_length_inches: Decimal,
) -> Decimal:
    """
    Calculate running cadence (steps per minute).

    pace_seconds:
        Running pace in seconds per mile.

    step_length_inches:
        Distance covered per individual step.
    """

    if pace_seconds <= 0:
        raise ValueError("Pace must be greater than zero.")

    if step_length_inches <= 0:
        raise ValueError("Step length must be greater than zero.")

    distance_per_minute = (
        INCHES_PER_MILE
        * SECONDS_PER_MINUTE
        / Decimal(pace_seconds)
    )

    cadence = distance_per_minute / step_length_inches

    return cadence.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def derive_step_length(
    observed_pace_seconds: int,
    measured_cadence_spm: Decimal,
) -> Decimal:
    """
    Derive effective step length from an observed
    running pace and measured cadence.
    """

    if observed_pace_seconds <= 0:
        raise ValueError("Pace must be greater than zero.")

    if measured_cadence_spm <= 0:
        raise ValueError("Cadence must be greater than zero.")

    distance_per_minute = (
        INCHES_PER_MILE
        * SECONDS_PER_MINUTE
        / Decimal(observed_pace_seconds)
    )

    return (
        distance_per_minute / measured_cadence_spm
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def calculate_target_cadence(
    target_pace_seconds: int,
    step_length_inches: Decimal,
    source: str = "calibrated",
) -> CadenceResult:

    cadence = calculate_cadence(
        pace_seconds=target_pace_seconds,
        step_length_inches=step_length_inches,
    )

    return CadenceResult(
        target_pace_seconds=target_pace_seconds,
        cadence_spm=cadence,
        step_length_inches=step_length_inches,
        source=source,
    )
