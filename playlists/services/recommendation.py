from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet, Prefetch

from music.choices import SyncRatio
from music.models import Track, Genre, TrackProviderMapping
from runners.models import UserGenrePreference, SpotifyAuth
from music.services.spotify_service import SpotifyService


WEIGHTS = {
    "bpm_match": Decimal("0.50"),
    "genre_preference": Decimal("0.25"),
    "energy": Decimal("0.15"),
    "artist_diversity": Decimal("0.10"),
}

BPM_TOLERANCE_PERCENT = Decimal("5")


@dataclass(frozen=True)
class TrackScore:
    track: Track
    overall_score: Decimal
    bpm_match_score: Decimal
    genre_score: Decimal
    energy_score: Decimal
    artist_diversity_bonus: Decimal
    sync_ratio: SyncRatio


@dataclass
class RecommendationQuery:
    user: User
    target_bpm: Decimal
    sync_ratio: SyncRatio
    num_tracks: int = 20
    bpm_tolerance_percent: Decimal = BPM_TOLERANCE_PERCENT
    exclude_artists: set[str] = field(default_factory=set)
    target_energy: Optional[Decimal] = None
    energy_tolerance: Optional[Decimal] = None


def calculate_bpm_match_score(
    track_bpm: Decimal,
    target_bpm: Decimal,
    tolerance_percent: Decimal = BPM_TOLERANCE_PERCENT,
) -> Decimal:
    """
    Score how close track BPM is to target BPM.

    Returns 1.0 for perfect match, decreasing linearly to 0.0
    at tolerance_percent deviation.
    """

    if target_bpm <= 0:
        raise ValueError("Target BPM must be positive.")

    if track_bpm <= 0:
        raise ValueError("Track BPM must be positive.")

    deviation_percent = abs(track_bpm - target_bpm) / target_bpm * 100

    if deviation_percent > tolerance_percent:
        return Decimal("0.0")

    score = (tolerance_percent - deviation_percent) / tolerance_percent

    return max(Decimal("0.0"), score).quantize(
        Decimal("0.01"),
    )


def calculate_genre_preference_score(
    track: Track,
    user: User,
) -> Decimal:
    """
    Score based on how much the user prefers the track's genres.

    If track has multiple genres, uses the highest preference.
    """

    track_genres = track.genres.all()

    if not track_genres.exists():
        return Decimal("0.5")

    user_prefs = UserGenrePreference.objects.filter(
        user=user,
        genre__in=track_genres,
    )

    if not user_prefs.exists():
        return Decimal("0.0")

    max_preference_weight = user_prefs.order_by(
        "-preference_weight"
    ).first().preference_weight

    normalized_score = max_preference_weight / 5

    return normalized_score.quantize(
        Decimal("0.01"),
    )


def calculate_energy_score(
    track_energy: Optional[Decimal],
    target_energy: Optional[Decimal] = None,
    tolerance: Decimal = Decimal("0.2"),
) -> Decimal:
    """
    Score based on track energy level.

    If no target_energy specified, returns neutral score (0.5).
    If track has no energy data, returns 0.5 (neutral).
    """

    if track_energy is None:
        return Decimal("0.5")

    if target_energy is None:
        return Decimal("0.5")

    deviation = abs(track_energy - target_energy)

    if deviation > tolerance:
        return Decimal("0.0")

    score = (tolerance - deviation) / tolerance

    return max(Decimal("0.0"), score).quantize(
        Decimal("0.01"),
    )


def calculate_artist_diversity_penalty(
    artist_name: str,
    already_selected_artists: set[str],
    penalty_per_duplicate: Decimal = Decimal("0.1"),
) -> Decimal:
    """
    Penalize selecting the same artist multiple times.

    Returns bonus (0.0 for new artist, negative for duplicates).
    """

    if artist_name not in already_selected_artists:
        return Decimal("0.0")

    return -penalty_per_duplicate


def score_track(
    track: Track,
    target_bpm: Decimal,
    sync_ratio: SyncRatio,
    user: User,
    already_selected_artists: set[str],
    bpm_tolerance_percent: Decimal = BPM_TOLERANCE_PERCENT,
    target_energy: Optional[Decimal] = None,
) -> Optional[TrackScore]:
    """
    Calculate composite score for a track.

    Returns None if track is outside acceptable BPM range.
    """

    bpm_match = calculate_bpm_match_score(
        track_bpm=track.bpm,
        target_bpm=target_bpm,
        tolerance_percent=bpm_tolerance_percent,
    )

    if bpm_match == 0:
        return None

    genre_score = calculate_genre_preference_score(track, user)
    energy_score = calculate_energy_score(track.energy, target_energy)
    artist_diversity = calculate_artist_diversity_penalty(
        track.artist,
        already_selected_artists,
    )

    overall_score = (
        bpm_match * WEIGHTS["bpm_match"]
        + genre_score * WEIGHTS["genre_preference"]
        + energy_score * WEIGHTS["energy"]
        + artist_diversity * WEIGHTS["artist_diversity"]
    )

    return TrackScore(
        track=track,
        overall_score=overall_score.quantize(Decimal("0.01")),
        bpm_match_score=bpm_match,
        genre_score=genre_score,
        energy_score=energy_score,
        artist_diversity_bonus=artist_diversity,
        sync_ratio=sync_ratio,
    )


def find_matching_tracks(
    target_bpm: Decimal,
    bpm_tolerance_percent: Decimal = BPM_TOLERANCE_PERCENT,
    genres: Optional[QuerySet[Genre]] = None,
    exclude_artists: Optional[set[str]] = None,
) -> QuerySet[Track]:
    """
    Find all tracks within BPM tolerance of target.

    Optionally filter by genre and exclude specific artists.
    """

    tolerance = target_bpm * bpm_tolerance_percent / 100

    min_bpm = target_bpm - tolerance
    max_bpm = target_bpm + tolerance

    query = Track.objects.filter(
        bpm__gte=min_bpm,
        bpm__lte=max_bpm,
    ).select_related().prefetch_related("genres")

    if genres is not None and genres.exists():
        query = query.filter(genres__in=genres).distinct()

    if exclude_artists:
        query = query.exclude(artist__in=exclude_artists)

    return query


def search_and_sync_spotify_tracks(
    target_bpm: Decimal,
    bpm_tolerance_percent: Decimal = BPM_TOLERANCE_PERCENT,
    genres: Optional[QuerySet[Genre]] = None,
    limit: int = 20,
    access_token: Optional[str] = None,
) -> list[Track]:
    """
    Search Spotify for tracks matching BPM and genres, then sync to database.

    Returns list of newly synced tracks with Spotify IDs and audio features.
    Handles errors gracefully — if Spotify search fails, returns empty list.
    """
    try:
        service = SpotifyService(access_token=access_token)

        # Build genre-based search query (Spotify doesn't support tempo in search)
        genre_names = []
        if genres and genres.exists():
            genre_names = [g.name.lower() for g in genres[:3]]

        # Construct search query with genre keywords
        search_query = " ".join(genre_names) if genre_names else "pop rock"

        tolerance = target_bpm * bpm_tolerance_percent / 100
        min_bpm = target_bpm - tolerance
        max_bpm = target_bpm + tolerance

        synced_tracks = []

        # Search Spotify - will get back tracks we then filter by audio features
        results = service.sp.search(q=search_query, type="track", limit=20)

        if results["tracks"]["items"]:
            for spotify_track in results["tracks"]["items"]:
                # Get audio features to check BPM
                features = service.get_track_audio_features(spotify_track["id"])

                if features and min_bpm <= features["bpm"] <= max_bpm:
                    track, created = service.sync_track_to_db(spotify_track)
                    if track:
                        synced_tracks.append(track)

                    if len(synced_tracks) >= limit:
                        break

        return synced_tracks

    except Exception as e:
        print(f"[Warning] Spotify search failed: {e}")
        return []


def recommend_tracks(
    query: RecommendationQuery,
) -> list[TrackScore]:
    """
    Generate ranked track recommendations for a playlist.

    Uses priority scoring: BPM match (50%), genre (25%),
    energy (15%), artist diversity (10%).

    If insufficient local tracks found, auto-searches Spotify and syncs new tracks.

    Returns top-scored tracks, ordered by score descending,
    with artist diversity considered.
    """

    if query.target_bpm <= 0:
        raise ValueError("Target BPM must be positive.")

    user_genres = UserGenrePreference.objects.filter(
        user=query.user
    ).values_list("genre", flat=True)

    # Check if synced Spotify tracks have genres assigned
    spotify_tracks_with_genres = TrackProviderMapping.objects.filter(
        provider='spotify',
        track__genres__isnull=False
    ).distinct().count()

    total_spotify_tracks = TrackProviderMapping.objects.filter(
        provider='spotify'
    ).distinct().count()

    # Only filter by genre if synced tracks actually have genre data
    # Otherwise use BPM-only matching (more reliable for synced libraries)
    genre_queryset = None
    if total_spotify_tracks > 0 and spotify_tracks_with_genres / total_spotify_tracks > 0.5:
        # At least 50% of synced tracks have genres, so filter
        genre_queryset = Genre.objects.filter(id__in=user_genres) if user_genres.exists() else None

    if genre_queryset and not genre_queryset.exists():
        genre_queryset = None

    candidate_tracks = find_matching_tracks(
        target_bpm=query.target_bpm,
        bpm_tolerance_percent=query.bpm_tolerance_percent,
        genres=genre_queryset if genre_queryset is not None and genre_queryset.exists() else None,
        exclude_artists=query.exclude_artists,
    )

    # Check if we have enough local tracks; if not, search Spotify
    threshold = query.num_tracks  # Need at least this many to avoid fallback
    if candidate_tracks.count() < threshold:
        print(f"[Info] Only {candidate_tracks.count()} local tracks for {query.target_bpm} BPM target. Searching Spotify...")

        # Try to get user's access token for authenticated search
        access_token = None
        try:
            spotify_auth = query.user.spotify_auth
            if not spotify_auth.is_expired:
                access_token = spotify_auth.access_token
        except:
            pass

        new_tracks = search_and_sync_spotify_tracks(
            target_bpm=query.target_bpm,
            bpm_tolerance_percent=query.bpm_tolerance_percent,
            genres=genre_queryset if genre_queryset is not None and genre_queryset.exists() else None,
            limit=20,
            access_token=access_token,
        )
        if new_tracks:
            print(f"[Info] Found and synced {len(new_tracks)} tracks from Spotify")
            # Requery to include newly synced tracks
            candidate_tracks = find_matching_tracks(
                target_bpm=query.target_bpm,
                bpm_tolerance_percent=query.bpm_tolerance_percent,
                genres=genre_queryset if genre_queryset is not None and genre_queryset.exists() else None,
                exclude_artists=query.exclude_artists,
            )

    scored_tracks = []
    selected_artists = set()

    for track in candidate_tracks:
        track_score = score_track(
            track=track,
            target_bpm=query.target_bpm,
            sync_ratio=query.sync_ratio,
            user=query.user,
            already_selected_artists=selected_artists,
            bpm_tolerance_percent=query.bpm_tolerance_percent,
            target_energy=query.target_energy,
        )

        if track_score is not None:
            scored_tracks.append(track_score)

    scored_tracks.sort(
        key=lambda x: x.overall_score,
        reverse=True,
    )

    recommendations = []
    for scored_track in scored_tracks:
        recommendations.append(scored_track)
        selected_artists.add(scored_track.track.artist)

        if len(recommendations) >= query.num_tracks:
            break

    return recommendations
