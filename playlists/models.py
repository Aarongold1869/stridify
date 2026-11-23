from music.choices import SyncRatio

from django.db import models
from django.conf import settings
from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)


class Playlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="running_playlists",
    )

    name = models.CharField(max_length=255)

    target_pace_seconds = models.PositiveIntegerField()

    target_cadence_spm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    target_bpm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    duration_minutes = models.PositiveIntegerField(
        default=60,
    )

    algorithm_version = models.CharField(
        max_length=20,
        default="1.0",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    tracks = models.ManyToManyField(
        "music.Track",
        through="PlaylistTrack",
        related_name="playlists",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class PlaylistTrack(models.Model):

    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name="playlist_tracks",
    )

    track = models.ForeignKey(
        "music.Track",
        on_delete=models.CASCADE,
        related_name="playlist_entries",
    )

    position = models.PositiveIntegerField()

    match_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    sync_ratio = models.CharField(
        max_length=5,
        choices=SyncRatio.choices,
    )

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["playlist", "track"],
                name="unique_track_in_playlist",
            ),
            models.UniqueConstraint(
                fields=["playlist", "position"],
                name="unique_playlist_position",
            ),
        ]