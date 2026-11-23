# Cadence Calculation Service

The cadence service converts a runner's physical characteristics and target pace into running cadence (steps per minute), then generates all available musical tempo targets.

## Overview

**Running cadence** is steps per minute (SPM). This service calculates cadence from a runner's target pace and step length, then maps that cadence to musical BPM using different synchronization ratios.

### Core Formula

```
Cadence (SPM) = (Distance per minute) / Step length
Distance per minute = (63,360 inches/mile × 60 seconds/minute) / pace (seconds/mile)
```

### Example

- Target pace: 10:00/mile (600 seconds)
- Step length: 39.6 inches
- Distance per minute: 6,336 inches
- Cadence: 6,336 / 39.6 = **160 SPM**

## Functions

### `calculate_cadence(pace_seconds, step_length_inches) → Decimal`

Basic cadence calculation from pace and step length.

```python
from decimal import Decimal
from runners.services.cadence import calculate_cadence

cadence = calculate_cadence(
    pace_seconds=600,         # 10:00/mile
    step_length_inches=Decimal("39.6"),
)
# → Decimal("160.0")
```

### `estimate_step_length_from_leg_length(leg_length_inches) → Decimal`

Estimates step length using biomechanical ratio (~0.43 of leg length).

```python
from decimal import Decimal
from runners.services.cadence import estimate_step_length_from_leg_length

step_length = estimate_step_length_from_leg_length(
    leg_length_inches=Decimal("30"),
)
# → Decimal("12.9")
```

### `derive_step_length(observed_pace_seconds, measured_cadence_spm) → Decimal`

Reverse-calculates step length from an observed pace and measured cadence.

Useful when you know someone's actual running cadence (from a wearable) and want to determine their effective step length.

```python
from decimal import Decimal
from runners.services.cadence import derive_step_length

step_length = derive_step_length(
    observed_pace_seconds=600,
    measured_cadence_spm=Decimal("160"),
)
# → Decimal("39.60")
```

### `resolve_runner_cadence(...) → CadenceResult`

**Primary function** that orchestrates the cadence calculation using a priority chain.

#### Priority Chain

1. **Measured cadence** (from wearable) — most accurate
2. **Measured step length** — from calibration or manual measurement
3. **Leg length** — estimated using biomechanical ratio
4. Error if none provided

#### Example: Using measured cadence

```python
from decimal import Decimal
from runners.services.cadence import resolve_runner_cadence

result = resolve_runner_cadence(
    target_pace_seconds=600,
    measured_cadence_spm=Decimal("110"),
)

print(result.cadence_spm)      # Decimal("110")
print(result.step_length_inches) # Decimal("57.60")
print(result.source)           # "measured"
```

#### Example: Estimating from leg length

```python
result = resolve_runner_cadence(
    target_pace_seconds=600,
    leg_length_inches=Decimal("30"),
)

print(result.cadence_spm)      # Decimal("409.3")
print(result.step_length_inches) # Decimal("12.9")
print(result.source)           # "estimated_from_leg_length"
```

### `get_tempo_targets_for_cadence(cadence_spm) → CadenceToTempoResult`

Generates all available musical tempo targets for a given cadence.

```python
from decimal import Decimal
from runners.services.cadence import get_tempo_targets_for_cadence

result = get_tempo_targets_for_cadence(
    cadence_spm=Decimal("160"),
)

# result.cadence_spm → Decimal("160")
# result.tempo_targets →
#   {
#       SyncRatio.HALF_TIME: Decimal("80.0"),    # 1 beat per 2 steps
#       SyncRatio.ONE_TO_ONE: Decimal("160.0"),  # 1 beat per step
#       SyncRatio.DOUBLE_TIME: Decimal("320.0"), # 2 beats per step
#   }
```

## Full Workflow Example

```python
from decimal import Decimal
from runners.services.cadence import (
    resolve_runner_cadence,
    get_tempo_targets_for_cadence,
)

# Step 1: Resolve the runner's cadence
cadence_result = resolve_runner_cadence(
    target_pace_seconds=600,
    leg_length_inches=Decimal("30"),
)

# Step 2: Get all available musical tempos
tempo_result = get_tempo_targets_for_cadence(
    cadence_spm=cadence_result.cadence_spm,
)

print(f"Target cadence: {cadence_result.cadence_spm} SPM")
print(f"Available BPMs:")
for ratio, bpm in tempo_result.tempo_targets.items():
    print(f"  {ratio.label}: {bpm} BPM")
```

## Integration with RunnerProfile

The service is designed to work with the `RunnerProfile` model:

```python
from runners.models import RunnerProfile
from runners.services.cadence import resolve_runner_cadence, get_tempo_targets_for_cadence

profile = RunnerProfile.objects.get(user=user)

cadence_result = resolve_runner_cadence(
    target_pace_seconds=profile.target_pace_seconds,
    measured_cadence_spm=profile.measured_cadence_spm,
    measured_step_length_inches=profile.step_length_inches,
    leg_length_inches=profile.leg_length_inches,
)

tempo_result = get_tempo_targets_for_cadence(
    cadence_spm=cadence_result.cadence_spm,
)
```

## Data Classes

### `CadenceResult`

```python
@dataclass(frozen=True)
class CadenceResult:
    target_pace_seconds: int        # Input pace in seconds/mile
    cadence_spm: Decimal            # Calculated cadence in steps/minute
    step_length_inches: Decimal     # Step length used in calculation
    source: str                     # "measured", "measured_step_length", or "estimated_from_leg_length"
```

### `CadenceToTempoResult`

```python
@dataclass(frozen=True)
class CadenceToTempoResult:
    cadence_spm: Decimal                        # The input cadence
    tempo_targets: dict[SyncRatio, Decimal]     # Map of sync ratios to target BPMs
```

## Tests

Comprehensive test coverage in `runners/tests.py`:

- `CadenceCalculationTests` — basic calculations
- `EstimateStepLengthTests` — leg length estimation
- `ResolveRunnerCadenceTests` — priority chain handling
- `CadenceToTempoTargetsTests` — tempo target generation
- `EndToEndCadenceWorkflowTests` — full integration

Run tests:

```bash
python manage.py test runners
```

## Constants

- `INCHES_PER_MILE = Decimal("63360")`
- `SECONDS_PER_MINUTE = Decimal("60")`
- `LEG_LENGTH_TO_STEP_RATIO = Decimal("0.43")` — biomechanical ratio for step estimation
