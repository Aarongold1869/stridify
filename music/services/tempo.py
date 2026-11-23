from decimal import Decimal, ROUND_HALF_UP

from music.choices import SyncRatio


def calculate_target_bpm(
    cadence_spm: Decimal,
    ratio: SyncRatio = SyncRatio.ONE_TO_ONE,
) -> Decimal:

    if cadence_spm <= 0:
        raise ValueError("Cadence must be positive.")

    ratio_value = Decimal(ratio.value)

    return (cadence_spm * ratio_value).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def get_tempo_targets(
    cadence_spm: Decimal,
) -> dict[SyncRatio, Decimal]:
    """
    Generate target BPM values for every supported
    synchronization ratio.
    """

    return {
        ratio: calculate_target_bpm(cadence_spm, ratio)
        for ratio in SyncRatio
    }