from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from music.choices import SyncRatio
from music.services.tempo import get_tempo_targets


INCHES_PER_MILE = Decimal("63360")
SECONDS_PER_MINUTE = Decimal("60")
LEG_LENGTH_TO_STEP_RATIO = Decimal("0.43")

# Empirical stride length data: height_inches -> (min_stride, typical_stride, max_stride)
# Based on running biomechanics studies of recreational runners at moderate pace
# Stride = full gait cycle (both feet complete a step)
STRIDE_LENGTH_BY_HEIGHT = {
    60: (Decimal("31"), Decimal("35.5"), Decimal("40")),      # 5'0"
    64: (Decimal("33"), Decimal("38.0"), Decimal("43")),      # 5'4"
    68: (Decimal("35"), Decimal("41.5"), Decimal("48")),      # 5'8"
    72: (Decimal("37"), Decimal("45.5"), Decimal("54")),      # 6'0"
    74: (Decimal("39"), Decimal("48.5"), Decimal("58")),      # 6'2"
}


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


def estimate_stride_from_height(
    height_inches: Decimal,
) -> Decimal:
    """
    Estimate typical running stride length from height using
    empirical biomechanical data.

    Stride = distance covered in one complete gait cycle (both feet).
    Uses midpoint of typical range for recreational runners at
    moderate pace (~160-180 SPM).

    If height falls between data points, interpolates linearly.
    Uses empirical data from running biomechanics studies.
    """

    if height_inches <= 0:
        raise ValueError("Height must be greater than zero.")

    height_int = int(height_inches)

    # Exact match in table
    if height_int in STRIDE_LENGTH_BY_HEIGHT:
        _, typical_stride, _ = STRIDE_LENGTH_BY_HEIGHT[height_int]
        return typical_stride

    # Find surrounding data points for interpolation
    heights = sorted(STRIDE_LENGTH_BY_HEIGHT.keys())

    if height_int < heights[0]:
        # Below minimum height in data - use minimum
        _, typical_stride, _ = STRIDE_LENGTH_BY_HEIGHT[heights[0]]
        return typical_stride

    if height_int > heights[-1]:
        # Above maximum height in data - use maximum
        _, typical_stride, _ = STRIDE_LENGTH_BY_HEIGHT[heights[-1]]
        return typical_stride

    # Find surrounding points
    h1 = None
    h2 = None
    for i, h in enumerate(heights):
        if h < height_int:
            h1 = h
        if h > height_int and h2 is None:
            h2 = h
            break

    if h1 is None or h2 is None:
        _, typical_stride, _ = STRIDE_LENGTH_BY_HEIGHT[height_int]
        return typical_stride

    # Linear interpolation between two data points
    _, stride1, _ = STRIDE_LENGTH_BY_HEIGHT[h1]
    _, stride2, _ = STRIDE_LENGTH_BY_HEIGHT[h2]

    # Interpolate
    fraction = Decimal(height_int - h1) / Decimal(h2 - h1)
    interpolated = stride1 + (stride2 - stride1) * fraction

    return interpolated.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def estimate_step_length_from_leg_length(
    leg_length_inches: Decimal,
) -> Decimal:
    """
    Estimate step length from leg length using
    biomechanical ratio (~0.43 of leg length).

    This is a fallback estimate; height-based estimation or
    measured values are more accurate.
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
    height_inches: Optional[Decimal] = None,
    leg_length_inches: Optional[Decimal] = None,
) -> CadenceResult:
    """
    Resolve a runner's target cadence using priority chain:

    1. If measured stride length provided, calculate cadence from it.
    2. Else if height provided, estimate stride from empirical data, then calculate.
    3. Else if leg length provided, estimate step length, then calculate.
    4. Else raise error (insufficient data).

    Note: Cadence is pace-dependent, so measured values must include the pace
    at which they were recorded. If a measured stride length is provided but
    the target pace differs, we use the measured stride with the target pace
    (which assumes stride length is relatively constant across moderate paces).

    Returns CadenceResult with source indicating which path was taken.

    Note: target_pace_seconds is in seconds/km and must be converted to
    seconds/mile for the calculate_cadence function.
    """

    if target_pace_seconds <= 0:
        raise ValueError("Target pace must be greater than zero.")

    # Convert pace from seconds/km to seconds/mile
    # 1 mile = 1.60934 km
    KM_PER_MILE = Decimal("1.60934")
    pace_seconds_per_mile = Decimal(target_pace_seconds) * KM_PER_MILE

    # Priority 1: Use measured stride length if available
    if measured_step_length_inches is not None:
        if measured_step_length_inches <= 0:
            raise ValueError("Step length must be greater than zero.")

        cadence = calculate_cadence(
            int(pace_seconds_per_mile),
            measured_step_length_inches,
        )

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=cadence,
            step_length_inches=measured_step_length_inches,
            source="measured_step_length",
        )

    # Priority 2: Estimate from height
    if height_inches is not None:
        if height_inches <= 0:
            raise ValueError("Height must be greater than zero.")

        estimated_stride = estimate_stride_from_height(height_inches)

        cadence = calculate_cadence(
            int(pace_seconds_per_mile),
            estimated_stride,
        )

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=cadence,
            step_length_inches=estimated_stride,
            source="estimated_from_height",
        )

    # Priority 3: Estimate from leg length
    if leg_length_inches is not None:
        if leg_length_inches <= 0:
            raise ValueError("Leg length must be greater than zero.")

        estimated_step_length = estimate_step_length_from_leg_length(
            leg_length_inches
        )

        cadence = calculate_cadence(
            int(pace_seconds_per_mile),
            estimated_step_length,
        )

        return CadenceResult(
            target_pace_seconds=target_pace_seconds,
            cadence_spm=cadence,
            step_length_inches=estimated_step_length,
            source="estimated_from_leg_length",
        )

    raise ValueError(
        "Insufficient data to calculate cadence. "
        "Provide measured_step_length_inches, height_inches, or leg_length_inches."
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
