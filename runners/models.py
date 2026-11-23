from django.db import models

# Create your models here.

from django.conf import settings
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models


class RunnerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="runner_profile",
    )

    height_inches = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    leg_length_inches = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # User's preferred target pace in seconds per mile.
    target_pace_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    # Optional measured cadence from a wearable or manual input.
    measured_cadence_spm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    # Optional measured average step length.
    step_length_inches = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Runner Profile"

    def __str__(self):
        return f"{self.user} - Runner Profile"



class UserGenrePreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="genre_preferences",
    )

    genre = models.ForeignKey(
        "music.Genre",
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )

    # Allows users to eventually rank their genre preferences.
    preference_weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5),
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "genre"],
                name="unique_user_genre_preference",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.genre}"
