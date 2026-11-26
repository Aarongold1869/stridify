from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction

from music.choices import SyncRatio
from music.models import Track, TrackProviderMapping
from runners.models import RunnerProfile, UserGenrePreference
from runners.services.cadence import (
    resolve_runner_cadence,
    get_tempo_targets_for_cadence,
    CadenceResult,
    CadenceToTempoResult,
)
from playlists.models import Playlist, PlaylistTrack
from playlists.services.recommendation import (
    recommend_tracks,
    RecommendationQuery,
    TrackScore,
)


SECONDS_PER_MINUTE = 60
KM_PER_MILE = Decimal("1.60934")


def _format_pace_for_display(pace_seconds: int) -> str:
    """Convert pace in seconds/km to min:sec/mile format.

    Example: 300 seconds/km -> 8:03/mile
    """
    # Convert km to miles
    pace_seconds_per_mile = Decimal(pace_seconds) * KM_PER_MILE
    minutes = int(pace_seconds_per_mile) // 60
    seconds = int(pace_seconds_per_mile) % 60
    return f"{minutes}:{seconds:02d}/mile"


def _generate_playlist_name(duration_minutes: int, pace_seconds: int) -> str:
    """Generate a user-friendly playlist name.

    Example: "30min Run - Pace 8:03/mile"
    """
    pace_str = _format_pace_for_display(pace_seconds)
    return f"{duration_minutes}min Run - Pace {pace_str}"


@dataclass
class PlaylistGenerationRequest:
    user: User
    playlist_name: str
    duration_minutes: int = 60
    target_energy: Optional[Decimal] = None
    algorithm_version: str = "1.0"


@dataclass
class PlaylistGenerationResult:
    playlist: Playlist
    tracks_selected: int
    total_duration_seconds: int
    cadence_spm: Decimal
    sync_ratio_distribution: dict[str, int]


def estimate_num_tracks_needed(
    target_duration_minutes: int,
    average_track_duration_seconds: int = 240,
) -> int:
    """
    Estimate how many tracks are needed to fill target duration.

    Default average track length is 4 minutes (240 seconds).
    """

    target_seconds = target_duration_minutes * SECONDS_PER_MINUTE
    num_tracks = int(target_seconds / average_track_duration_seconds)

    return max(1, num_tracks)


def _generate_recommendations_for_sync_ratio(
    user: User,
    target_bpm: Decimal,
    sync_ratio: SyncRatio,
    num_tracks: int,
    target_energy: Optional[Decimal] = None,
) -> list[TrackScore]:
    """
    Generate recommendations for a specific sync ratio.
    """

    query = RecommendationQuery(
        user=user,
        target_bpm=target_bpm,
        sync_ratio=sync_ratio,
        num_tracks=num_tracks,
        target_energy=target_energy,
    )

    return recommend_tracks(query)


def _select_and_order_tracks(
    recommendations_by_ratio: dict[SyncRatio, list[TrackScore]],
    target_duration_minutes: int,
) -> list[TrackScore]:
    """
    Select tracks from recommendations across all sync ratios,
    ordered for good flow.

    Strategy:
    1. Interleave recommendations across sync ratios (variety)
    2. Respect target duration
    3. Use scoring as tiebreaker
    """

    target_seconds = target_duration_minutes * SECONDS_PER_MINUTE
    selected_tracks: list[TrackScore] = []
    total_duration = 0

    # Create iterators for each sync ratio
    sync_ratio_iterators = {
        ratio: iter(recs) for ratio, recs in recommendations_by_ratio.items()
    }

    # Interleave recommendations to create variety
    active_ratios = list(sync_ratio_iterators.keys())
    ratio_index = 0

    while active_ratios and total_duration < target_seconds:
        ratio = active_ratios[ratio_index % len(active_ratios)]

        try:
            track_score = next(sync_ratio_iterators[ratio])
            selected_tracks.append(track_score)
            total_duration += track_score.track.duration_seconds
        except StopIteration:
            active_ratios.remove(ratio)
            if active_ratios:
                ratio_index = ratio_index % len(active_ratios)
            continue

        ratio_index += 1

    return selected_tracks


def _create_playlist_records(
    user: User,
    playlist_name: str,
    target_pace_seconds: int,
    cadence_spm: Decimal,
    selected_tracks: list[TrackScore],
    algorithm_version: str = "1.0",
) -> Playlist:
    """
    Create Playlist and PlaylistTrack records in database.
    """

    if not selected_tracks:
        raise ValueError("No tracks selected for playlist.")

    # Calculate average target BPM (from primary sync ratio)
    primary_target_bpm = None
    for track_score in selected_tracks:
        if track_score.sync_ratio == SyncRatio.ONE_TO_ONE:
            primary_target_bpm = track_score.track.bpm
            break

    if primary_target_bpm is None:
        primary_target_bpm = selected_tracks[0].track.bpm

    with transaction.atomic():
        playlist = Playlist.objects.create(
            user=user,
            name=playlist_name,
            target_pace_seconds=target_pace_seconds,
            target_cadence_spm=cadence_spm,
            target_bpm=primary_target_bpm,
            duration_minutes=sum(t.track.duration_seconds for t in selected_tracks) // SECONDS_PER_MINUTE,
            algorithm_version=algorithm_version,
        )

        playlist_tracks = [
            PlaylistTrack(
                playlist=playlist,
                track=track_score.track,
                position=position + 1,
                match_score=track_score.overall_score,
                sync_ratio=track_score.sync_ratio,
            )
            for position, track_score in enumerate(selected_tracks)
        ]

        PlaylistTrack.objects.bulk_create(playlist_tracks)

    return playlist


def generate_playlist(
    request: PlaylistGenerationRequest,
) -> PlaylistGenerationResult:
    """
    Generate a complete running playlist end-to-end.

    Orchestrates:
    1. Fetch runner profile
    2. Calculate cadence from profile
    3. Get tempo targets for all sync ratios
    4. Generate recommendations for each sync ratio
    5. Select and order tracks intelligently
    6. Create Playlist and PlaylistTrack records

    Returns PlaylistGenerationResult with playlist and metadata.
    """

    if request.duration_minutes <= 0:
        raise ValueError("Playlist duration must be positive.")

    try:
        runner_profile = RunnerProfile.objects.get(user=request.user)
    except RunnerProfile.DoesNotExist:
        raise ValueError(
            f"Runner profile not found for user {request.user.username}. "
            "User must set up their profile before generating playlists."
        )

    if runner_profile.target_pace_seconds is None:
        raise ValueError("Runner profile must have target_pace_seconds set.")

    # Step 1: Resolve cadence from runner profile
    cadence_result = resolve_runner_cadence(
        target_pace_seconds=runner_profile.target_pace_seconds,
        measured_step_length_inches=runner_profile.measured_step_length_inches,
        height_inches=runner_profile.height_inches,
        leg_length_inches=runner_profile.leg_length_inches,
    )

    # Step 2: Get all tempo targets for all sync ratios
    tempo_result = get_tempo_targets_for_cadence(
        cadence_spm=cadence_result.cadence_spm,
    )

    # Step 3: Estimate how many tracks we need
    num_tracks_needed = estimate_num_tracks_needed(
        target_duration_minutes=request.duration_minutes,
    )

    # Step 4: Generate recommendations for each sync ratio
    recommendations_by_ratio: dict[SyncRatio, list[TrackScore]] = {}

    for sync_ratio, target_bpm in tempo_result.tempo_targets.items():
        recommendations = _generate_recommendations_for_sync_ratio(
            user=request.user,
            target_bpm=target_bpm,
            sync_ratio=sync_ratio,
            num_tracks=num_tracks_needed,
            target_energy=request.target_energy,
        )

        if recommendations:
            recommendations_by_ratio[sync_ratio] = recommendations

    if not recommendations_by_ratio:
        track_count = Track.objects.count()
        pref_count = UserGenrePreference.objects.filter(user=request.user).count()

        raise ValueError(
            f"No recommendations found for any sync ratio. "
            f"Cadence: {cadence_result.cadence_spm} SPM, "
            f"Tempo targets: {tempo_result.tempo_targets}, "
            f"DB: {track_count} tracks, {pref_count} user preferences."
        )

    # Step 5: Select and order tracks across all sync ratios
    selected_tracks = _select_and_order_tracks(
        recommendations_by_ratio=recommendations_by_ratio,
        target_duration_minutes=request.duration_minutes,
    )

    if not selected_tracks:
        raise ValueError("No tracks selected for playlist after filtering.")

    # Filter to only include tracks with Spotify provider mappings
    spotify_track_ids = set(
        TrackProviderMapping.objects.filter(provider='spotify').values_list(
            'track_id', flat=True
        )
    )
    selected_tracks_with_spotify = [
        ts for ts in selected_tracks if ts.track.id in spotify_track_ids
    ]

    if not selected_tracks_with_spotify:
        raise ValueError(
            "No selected tracks have Spotify provider mappings. "
            "Ensure tracks are synced from Spotify before generating playlists."
        )

    # Generate user-friendly playlist name
    friendly_name = _generate_playlist_name(
        duration_minutes=request.duration_minutes,
        pace_seconds=runner_profile.target_pace_seconds,
    )

    # Step 6: Create database records
    playlist = _create_playlist_records(
        user=request.user,
        playlist_name=friendly_name,
        target_pace_seconds=runner_profile.target_pace_seconds,
        cadence_spm=cadence_result.cadence_spm,
        selected_tracks=selected_tracks_with_spotify,
        algorithm_version=request.algorithm_version,
    )

    # Step 7: Calculate result metrics
    sync_ratio_counts = {}
    for track_score in selected_tracks_with_spotify:
        ratio_name = track_score.sync_ratio.label
        sync_ratio_counts[ratio_name] = sync_ratio_counts.get(ratio_name, 0) + 1

    total_duration_seconds = sum(
        t.track.duration_seconds for t in selected_tracks_with_spotify
    )

    return PlaylistGenerationResult(
        playlist=playlist,
        tracks_selected=len(selected_tracks_with_spotify),
        total_duration_seconds=total_duration_seconds,
        cadence_spm=cadence_result.cadence_spm,
        sync_ratio_distribution=sync_ratio_counts,
    )
