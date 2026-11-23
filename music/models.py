from django.db import models

# Create your models here.

from django.db import models
from django.db.models import Q
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)


class Genre(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Track(models.Model):
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)

    album = models.CharField(
        max_length=255,
        blank=True,
    )

    isrc = models.CharField(
        max_length=12,
        null=True,
        blank=True,
        db_index=True,
    )

    duration_seconds = models.PositiveIntegerField()

    bpm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(400),
        ],
    )

    energy = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    genres = models.ManyToManyField(
        Genre,
        related_name="tracks",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["artist", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["isrc"],
                condition=Q(isrc__isnull=False) & ~Q(isrc=""),
                name="unique_track_isrc",
            )
        ]
        indexes = [
            models.Index(fields=["bpm"]),
            models.Index(fields=["artist", "title"]),
        ]

    def __str__(self):
        return f"{self.artist} - {self.title}"


class TrackProviderMapping(models.Model):

    class Provider(models.TextChoices):
        SPOTIFY = "spotify", "Spotify"
        APPLE_MUSIC = "apple_music", "Apple Music"
        PANDORA = "pandora", "Pandora"

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="provider_mappings",
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
    )

    provider_track_id = models.CharField(
        max_length=255,
    )

    provider_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_track_id"],
                name="unique_provider_track",
            ),
            models.UniqueConstraint(
                fields=["track", "provider"],
                name="unique_track_provider",
            ),
        ]

    def __str__(self):
        return f"{self.provider}: {self.provider_track_id}"
