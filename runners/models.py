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

    cadence_observed_pace_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
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


class SpotifyAuth(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spotify_auth",
    )

    spotify_user_id = models.CharField(
        max_length=255,
        unique=True,
    )

    access_token = models.TextField()

    refresh_token = models.TextField()

    token_expires_at = models.DateTimeField()

    scope = models.CharField(
        max_length=500,
        default="playlist-modify-public playlist-modify-private",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spotify Authorization"

    def __str__(self):
        return f"{self.user} - Spotify"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.token_expires_at

    def refresh_access_token(self, sp_oauth):
        """Refresh access token using refresh token"""
        token_info = sp_oauth.refresh_access_token(self.refresh_token)

        from django.utils import timezone
        from datetime import timedelta

        self.access_token = token_info['access_token']
        if 'refresh_token' in token_info:
            self.refresh_token = token_info['refresh_token']
        self.token_expires_at = timezone.now() + timedelta(seconds=token_info['expires_in'])
        self.save()

        return self.access_token
