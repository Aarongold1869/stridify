from decimal import Decimal

from django.test import SimpleTestCase

from music.choices import SyncRatio
from runners.services.cadence import (
    calculate_cadence,
    derive_step_length,
    calculate_target_cadence,
    estimate_step_length_from_leg_length,
    estimate_stride_from_height,
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


class EstimateStrideFromHeightTests(SimpleTestCase):

    def test_stride_at_5_foot_0(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("60"),
        )

        self.assertEqual(result, Decimal("35.5"))

    def test_stride_at_5_foot_4(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("64"),
        )

        self.assertEqual(result, Decimal("38.0"))

    def test_stride_at_5_foot_8(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("68"),
        )

        self.assertEqual(result, Decimal("41.5"))

    def test_stride_at_6_foot_0(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("72"),
        )

        self.assertEqual(result, Decimal("45.5"))

    def test_stride_at_6_foot_2(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("74"),
        )

        self.assertEqual(result, Decimal("48.5"))

    def test_interpolates_between_data_points(self):
        # 5'6" = 66 inches (between 64 and 68)
        result = estimate_stride_from_height(
            height_inches=Decimal("66"),
        )

        # Should interpolate between 38.0 and 41.5
        # Fraction: (66 - 64) / (68 - 64) = 0.5
        # Result: 38.0 + (41.5 - 38.0) * 0.5 = 38.0 + 1.75 = 39.75
        self.assertEqual(result, Decimal("39.8"))

    def test_below_minimum_height_uses_minimum(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("55"),
        )

        # Should use minimum height data (60 inches)
        self.assertEqual(result, Decimal("35.5"))

    def test_above_maximum_height_uses_maximum(self):
        result = estimate_stride_from_height(
            height_inches=Decimal("78"),
        )

        # Should use maximum height data (74 inches)
        self.assertEqual(result, Decimal("48.5"))

    def test_rejects_zero_height(self):
        with self.assertRaises(ValueError):
            estimate_stride_from_height(
                height_inches=Decimal("0"),
            )

    def test_rejects_negative_height(self):
        with self.assertRaises(ValueError):
            estimate_stride_from_height(
                height_inches=Decimal("-70"),
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
        self.assertEqual(result.cadence_spm, Decimal("491.2"))

    def test_prefers_measured_cadence_over_step_length(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_cadence_spm=Decimal("160"),
            measured_step_length_inches=Decimal("50"),
        )

        self.assertEqual(result.cadence_spm, Decimal("160"))
        self.assertEqual(result.source, "measured")

    def test_prefers_measured_step_length_over_height(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            measured_step_length_inches=Decimal("39.6"),
            height_inches=Decimal("68"),
        )

        self.assertEqual(result.cadence_spm, Decimal("160.0"))
        self.assertEqual(result.source, "measured_step_length")

    def test_estimates_from_height_when_no_measured_data(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            height_inches=Decimal("68"),
        )

        self.assertEqual(result.step_length_inches, Decimal("41.5"))
        self.assertEqual(result.source, "estimated_from_height")
        # Cadence: 6336 / 41.5 = 152.65 SPM ≈ 152.7 SPM
        self.assertEqual(result.cadence_spm, Decimal("152.7"))

    def test_prefers_height_over_leg_length(self):
        result = resolve_runner_cadence(
            target_pace_seconds=600,
            height_inches=Decimal("68"),
            leg_length_inches=Decimal("30"),
        )

        self.assertEqual(result.source, "estimated_from_height")
        self.assertEqual(result.step_length_inches, Decimal("41.5"))

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

        self.assertEqual(tempo_result.cadence_spm, Decimal("491.2"))
        self.assertIn(SyncRatio.ONE_TO_ONE, tempo_result.tempo_targets)
        self.assertIn(SyncRatio.HALF_TIME, tempo_result.tempo_targets)
        self.assertIn(SyncRatio.DOUBLE_TIME, tempo_result.tempo_targets)
