from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from music.choices import SyncRatio
from music.services.tempo import get_tempo_targets


INCHES_PER_MILE = Decimal("63360")
SECONDS_PER_MINUTE = Decimal("60")
LEG_LENGTH_TO_STEP_RATIO = Decimal("0.43")


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


def estimate_step_length_from_leg_length(
    leg_length_inches: Decimal,
) -> Decimal:
    """
    Estimate step length from leg length using
    biomechanical ratio (~0.43 of leg length).

    This is an initial estimate; measured values
    are more accurate.
    """

    if leg_length_inches <= 0:
        raise ValueError("Leg length must be greater than zero.")

    estimated_step_length = (
        leg_length_inches * LEG_LENGTH_TO_STEP_RATIO
    )

    return estimated_step_length.quantize(
        Decimal("0.1"),
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


def resolve_runner_cadence(
    target_pace_seconds: int,
    measured_cadence_spm: Optional[Decimal] = None,
    measured_step_length_inches: Optional[Decimal] = None,
    leg_length_inches: Optional[Decimal] = None,
) -> CadenceResult:
    """
    Resolve a runner's target cadence using priority chain:

    1. If measured cadence provided, use it directly.
    2. Else if measured step length provided, calculate cadence from it.
    3. Else if leg length provided, estimate step length, then calculate.
    4. Else raise error (insufficient data).

    Returns CadenceResult with source indicating which path was taken.
    """

    if target_pace_seconds <= 0:
        raise ValueError("Target pace must be greater than zero.")

    if measured_cadence_spm is not None:
        if measured_cadence_spm <= 0:
            raise ValueError("Measured cadence must be greater than zero.")

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=measured_cadence_spm,
            step_length_inches=derive_step_length(
                target_pace_seconds,
                measured_cadence_spm,
            ),
            source="measured",
        )

    if measured_step_length_inches is not None:
        if measured_step_length_inches <= 0:
            raise ValueError("Step length must be greater than zero.")

        cadence = calculate_cadence(
            target_pace_seconds,
            measured_step_length_inches,
        )

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=cadence,
            step_length_inches=measured_step_length_inches,
            source="measured_step_length",
        )

    if leg_length_inches is not None:
        if leg_length_inches <= 0:
            raise ValueError("Leg length must be greater than zero.")

        estimated_step_length = estimate_step_length_from_leg_length(
            leg_length_inches
        )

        cadence = calculate_cadence(
            target_pace_seconds,
            estimated_step_length,
        )

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=cadence,
            step_length_inches=estimated_step_length,
            source="estimated_from_leg_length",
        )

    raise ValueError(
        "Must provide either measured cadence, measured step length, or leg length."
    )


@dataclass(frozen=True)
class CadenceToTempoResult:
    cadence_spm: Decimal
    tempo_targets: dict[SyncRatio, Decimal]


def get_tempo_targets_for_cadence(
    cadence_spm: Decimal,
) -> CadenceToTempoResult:
    """
    Given a running cadence, generate all available
    musical tempo targets using different synchronization ratios.

    Returns a result containing the cadence and a dict mapping
    each SyncRatio to its corresponding target BPM.
    """

    if cadence_spm <= 0:
        raise ValueError("Cadence must be greater than zero.")

    targets = get_tempo_targets(cadence_spm)

    return CadenceToTempoResult(
        cadence_spm=cadence_spm,
        tempo_targets=targets,
    )
