from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User

from music.services.spotify_service import SpotifyService
from runners.models import SpotifyAuth


@dataclass
class LibrarySyncRequest:
    user: User
    batch_size: int = 50


@dataclass
class LibrarySyncResult:
    total_tracks_synced: int
    new_tracks: int
    existing_tracks: int
    failed_count: int
    batches_processed: int


def sync_user_library(request: LibrarySyncRequest) -> LibrarySyncResult:
    """
    Sync all of a user's saved/liked tracks from Spotify to database.

    Paginates through ALL saved tracks (not just first 50) and syncs with
    audio features, genres, and Spotify provider mappings.

    Returns summary of sync operation.
    """
    try:
        spotify_auth = SpotifyAuth.objects.get(user=request.user)
    except SpotifyAuth.DoesNotExist:
        raise ValueError(
            f"User {request.user.username} not connected to Spotify. "
            "Please authenticate first."
        )

    # Check if token expired and refresh if needed
    if spotify_auth.is_expired:
        service = SpotifyService()
        spotify_auth.refresh_access_token(service.get_oauth_handler())

    service = SpotifyService(spotify_auth.access_token)

    total_synced = 0
    new_count = 0
    existing_count = 0
    failed_count = 0
    batch_count = 0

    offset = 0
    batch_size = request.batch_size

    while True:
        # Fetch batch of saved tracks
        try:
            # Get user's saved tracks with pagination
            sp = __import__('spotipy').Spotify(auth=spotify_auth.access_token)
            results = sp.current_user_saved_tracks(limit=batch_size, offset=offset)

            if not results["items"]:
                break

            # Extract track objects from saved tracks response
            tracks = [item["track"] for item in results["items"]]

            # Sync batch
            synced = service.bulk_sync_tracks(tracks)

            for sync_result in synced:
                if sync_result:
                    total_synced += 1
                    if sync_result["created"]:
                        new_count += 1
                    else:
                        existing_count += 1
                else:
                    failed_count += 1

            batch_count += 1
            offset += batch_size

            print(
                f"[Info] Synced batch {batch_count}: {len(synced)} tracks "
                f"({new_count} new, {existing_count} existing)"
            )

        except Exception as e:
            print(f"[Warning] Error syncing batch {batch_count}: {e}")
            failed_count += len(tracks)
            break

    return LibrarySyncResult(
        total_tracks_synced=total_synced,
        new_tracks=new_count,
        existing_tracks=existing_count,
        failed_count=failed_count,
        batches_processed=batch_count,
    )
