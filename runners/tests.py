from decimal import Decimal

from django.test import TestCase
from django.test import SimpleTestCase


from runners.services.cadence import (
    calculate_cadence,
    derive_step_length,
    calculate_target_cadence,
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
