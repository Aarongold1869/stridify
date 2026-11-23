from decimal import Decimal

from django.test import SimpleTestCase

from music.choices import SyncRatio
from music.services.tempo import (
    calculate_target_bpm,
    get_tempo_targets,
)


class CalculateTargetBpmTests(SimpleTestCase):

    def test_half_time_ratio(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160"),
            ratio=SyncRatio.HALF_TIME,
        )

        self.assertEqual(result, Decimal("80.0"))

    def test_one_to_one_ratio(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160"),
            ratio=SyncRatio.ONE_TO_ONE,
        )

        self.assertEqual(result, Decimal("160.0"))

    def test_double_time_ratio(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160"),
            ratio=SyncRatio.DOUBLE_TIME,
        )

        self.assertEqual(result, Decimal("320.0"))

    def test_default_ratio_is_one_to_one(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160"),
        )

        self.assertEqual(result, Decimal("160.0"))

    def test_rounds_to_one_decimal_place(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160.05"),
        )

        self.assertEqual(result, Decimal("160.1"))

    def test_rounds_half_up_for_half_time(self):
        result = calculate_target_bpm(
            cadence_spm=Decimal("160.1"),
            ratio=SyncRatio.HALF_TIME,
        )

        self.assertEqual(result, Decimal("80.1"))

    def test_rejects_zero_cadence(self):
        with self.assertRaises(ValueError):
            calculate_target_bpm(Decimal("0"))

    def test_rejects_negative_cadence(self):
        with self.assertRaises(ValueError):
            calculate_target_bpm(Decimal("-160"))


class GetTempoTargetsTests(SimpleTestCase):

    def test_returns_all_supported_ratios(self):
        result = get_tempo_targets(Decimal("160"))

        self.assertEqual(
            set(result.keys()),
            set(SyncRatio),
        )

    def test_returns_expected_bpm_for_each_ratio(self):
        result = get_tempo_targets(Decimal("160"))

        self.assertEqual(
            result,
            {
                SyncRatio.HALF_TIME: Decimal("80.0"),
                SyncRatio.ONE_TO_ONE: Decimal("160.0"),
                SyncRatio.DOUBLE_TIME: Decimal("320.0"),
            },
        )

    def test_rejects_invalid_cadence(self):
        with self.assertRaises(ValueError):
            get_tempo_targets(Decimal("0"))