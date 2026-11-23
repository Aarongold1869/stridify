from decimal import Decimal

from django.test import SimpleTestCase

from music.choices import SyncRatio
from runners.services.cadence import (
    calculate_cadence,
    derive_step_length,
    calculate_target_cadence,
    estimate_step_length_from_leg_length,
    resolve_runner_cadence,
    get_tempo_targets_for_cadence,
)


class CadenceCalculationTests(SimpleTestCase):

    def test_calculate_cadence(self):
        result = calculate_cadence(
            pace_seconds=600,
            step_length_inches=Decimal("39.6"),
        )

        self.assertEqual(result, Decimal("160.0"))

    def test_derive_step_length(self):
        result = derive_step_length(
            observed_pace_seconds=600,
            measured_cadence_spm=Decimal("160"),
        )

        self.assertEqual(result, Decimal("39.60"))

    def test_calculate_target_cadence(self):
        result = calculate_target_cadence(
            target_pace_seconds=540,
            step_length_inches=Decimal("39.6"),
        )

        self.assertEqual(
            result.cadence_spm,
            Decimal("177.8"),
        )

    def test_invalid_pace(self):
        with self.assertRaises(ValueError):
            calculate_cadence(
                pace_seconds=0,
                step_length_inches=Decimal("40"),
            )

    def test_invalid_step_length(self):
        with self.assertRaises(ValueError):
            calculate_cadence(
                pace_seconds=600,
                step_length_inches=Decimal("0"),
            )


class EstimateStepLengthTests(SimpleTestCase):

    def test_estimate_step_length_from_leg_length(self):
        result = estimate_step_length_from_leg_length(
            leg_length_inches=Decimal("30"),
        )

        self.assertEqual(result, Decimal("12.9"))

    def test_estimate_step_length_from_longer_leg(self):
        result = estimate_step_length_from_leg_length(
            leg_length_inches=Decimal("36"),
        )

        self.assertEqual(result, Decimal("15.5"))

    def test_rejects_zero_leg_length(self):
        with self.assertRaises(ValueError):
            estimate_step_length_from_leg_length(
                leg_length_inches=Decimal("0"),
            )

    def test_rejects_negative_leg_length(self):
        with self.assertRaises(ValueError):
            estimate_step_length_from_leg_length(
                leg_length_inches=Decimal("-30"),
            )


class ResolveRunnerCadenceTests(SimpleTestCase):

    def test_uses_measured_cadence_when_provided(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_cadence_spm=Decimal("110"),
        )

        self.assertEqual(result.cadence_spm, Decimal("110"))
        self.assertEqual(result.source, "measured")

    def test_derives_step_length_from_measured_cadence(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_cadence_spm=Decimal("160"),
        )

        self.assertEqual(result.step_length_inches, Decimal("39.60"))

    def test_uses_measured_step_length_when_cadence_missing(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_step_length_inches=Decimal("39.6"),
        )

        self.assertEqual(result.cadence_spm, Decimal("160.0"))
        self.assertEqual(result.source, "measured_step_length")

    def test_estimates_from_leg_length_when_no_measured_data(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            leg_length_inches=Decimal("30"),
        )

        self.assertEqual(result.step_length_inches, Decimal("12.9"))
        self.assertEqual(result.source, "estimated_from_leg_length")
        self.assertEqual(result.cadence_spm, Decimal("409.3"))

    def test_prefers_measured_cadence_over_step_length(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_cadence_spm=Decimal("160"),
            measured_step_length_inches=Decimal("50"),
        )

        self.assertEqual(result.cadence_spm, Decimal("160"))
        self.assertEqual(result.source, "measured")

    def test_prefers_measured_step_length_over_leg_length(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_step_length_inches=Decimal("39.6"),
            leg_length_inches=Decimal("30"),
        )

        self.assertEqual(result.cadence_spm, Decimal("160.0"))
        self.assertEqual(result.source, "measured_step_length")

    def test_raises_error_when_no_data_provided(self):
        with self.assertRaises(ValueError):
            resolve_runner_cadence(
                target_pace_seconds=600,
            )

    def test_raises_error_for_invalid_target_pace(self):
        with self.assertRaises(ValueError):
            resolve_runner_cadence(
                target_pace_seconds=0,
                measured_cadence_spm=Decimal("160"),
            )

    def test_raises_error_for_zero_measured_cadence(self):
        with self.assertRaises(ValueError):
            resolve_runner_cadence(
                target_pace_seconds=600,
                measured_cadence_spm=Decimal("0"),
            )

    def test_raises_error_for_zero_step_length(self):
        with self.assertRaises(ValueError):
            resolve_runner_cadence(
                target_pace_seconds=600,
                measured_step_length_inches=Decimal("0"),
            )

    def test_raises_error_for_zero_leg_length(self):
        with self.assertRaises(ValueError):
            resolve_runner_cadence(
                target_pace_seconds=600,
                leg_length_inches=Decimal("0"),
            )


class CadenceToTempoTargetsTests(SimpleTestCase):

    def test_returns_all_sync_ratios(self):
        result = get_tempo_targets_for_cadence(
            cadence_spm=Decimal("160"),
        )

        self.assertEqual(
            set(result.tempo_targets.keys()),
            {SyncRatio.HALF_TIME, SyncRatio.ONE_TO_ONE, SyncRatio.DOUBLE_TIME},
        )

    def test_returns_correct_bpm_targets(self):
        result = get_tempo_targets_for_cadence(
            cadence_spm=Decimal("160"),
        )

        self.assertEqual(
            result.tempo_targets,
            {
                SyncRatio.HALF_TIME: Decimal("80.0"),
                SyncRatio.ONE_TO_ONE: Decimal("160.0"),
                SyncRatio.DOUBLE_TIME: Decimal("320.0"),
            },
        )

    def test_stores_original_cadence(self):
        result = get_tempo_targets_for_cadence(
            cadence_spm=Decimal("110"),
        )

        self.assertEqual(result.cadence_spm, Decimal("110"))

    def test_raises_error_for_zero_cadence(self):
        with self.assertRaises(ValueError):
            get_tempo_targets_for_cadence(Decimal("0"))

    def test_raises_error_for_negative_cadence(self):
        with self.assertRaises(ValueError):
            get_tempo_targets_for_cadence(Decimal("-160"))


class EndToEndCadenceWorkflowTests(SimpleTestCase):

    def test_resolve_cadence_then_get_tempo_targets(self):
        cadence_result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_cadence_spm=Decimal("110"),
        )

        tempo_result = get_tempo_targets_for_cadence(
            cadence_spm=cadence_result.cadence_spm,
        )

        self.assertEqual(tempo_result.cadence_spm, Decimal("110"))
        self.assertEqual(
            tempo_result.tempo_targets[SyncRatio.ONE_TO_ONE],
            Decimal("110.0"),
        )

    def test_full_workflow_from_leg_length_to_bpm_targets(self):
        cadence_result = resolve_runner_cadence(
            target_pace_seconds=600,
            leg_length_inches=Decimal("30"),
        )

        tempo_result = get_tempo_targets_for_cadence(
            cadence_spm=cadence_result.cadence_spm,
        )

        self.assertEqual(tempo_result.cadence_spm, Decimal("409.3"))
        self.assertIn(SyncRatio.ONE_TO_ONE, tempo_result.tempo_targets)
        self.assertIn(SyncRatio.HALF_TIME, tempo_result.tempo_targets)
        self.assertIn(SyncRatio.DOUBLE_TIME, tempo_result.tempo_targets)
