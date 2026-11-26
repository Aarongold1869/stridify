import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from music.models import Track, Genre, TrackProviderMapping
from music.services.audio_analysis_service import AudioAnalysisService
from music.services.lastfm_service import LastFmService
from music.services.sonovault_service import SonoVaultService


class SpotifyService:
    """Service for Spotify API interactions"""

    def __init__(self, access_token=None):
        """Initialize Spotify client with optional access token"""
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = settings.SPOTIFY_REDIRECT_URI

        if access_token:
            self.sp = spotipy.Spotify(auth=access_token)
        else:
            # Client credentials flow for public data (no user auth required)
            credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.sp = spotipy.Spotify(client_credentials_manager=credentials_manager)

    def get_oauth_handler(self):
        """Get SpotifyOAuth handler for login flow

        IMPORTANT: cache_path=False disables disk caching to prevent
        .cache files from being created with sensitive tokens.
        Tokens are stored securely in SpotifyAuth model instead.
        """
        return SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=[
                'playlist-modify-public',
                'playlist-modify-private',
                'user-library-read',
            ],
            cache_path=False  # Disable disk caching - use database instead
        )

    def get_track_audio_features(self, track_id):
        """Fetch audio features for a track"""
        try:
            features = self.sp.audio_features(track_id)[0]
            if features is None:
                return None

            return {
                'bpm': Decimal(str(features['tempo'])),
                'energy': Decimal(str(features['energy'])),
                'danceability': Decimal(str(features['danceability'])),
                'valence': Decimal(str(features['valence'])),
                'acousticness': Decimal(str(features['acousticness'])),
                'instrumentalness': Decimal(str(features['instrumentalness'])),
                'liveness': Decimal(str(features['liveness'])),
                'speechiness': Decimal(str(features['speechiness'])),
                'mode': features['mode'],
                'key': features['key'],
                'time_signature': features['time_signature'],
            }
        except Exception as e:
            print(f"Error fetching audio features for {track_id}: {e}")
            return None

    def search_track(self, query, limit=1):
        """Search for a track on Spotify"""
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            if results['tracks']['items']:
                return results['tracks']['items'][0]
            return None
        except Exception as e:
            print(f"Error searching for track: {e}")
            return None

    def get_track(self, track_id):
        """Get track info by Spotify ID"""
        try:
            return self.sp.track(track_id)
        except Exception as e:
            print(f"Error fetching track {track_id}: {e}")
            return None

    def get_user_profile(self, access_token):
        """Get authenticated user's profile"""
        try:
            sp = spotipy.Spotify(auth=access_token)
            return sp.current_user()
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            return None

    def sync_track_to_db(self, spotify_track, skip_existing=True):
        """
        Sync a Spotify track to Stridify database

        Returns: (Track object, created: bool)
        """
        spotify_id = spotify_track['id']

        # Check if already synced
        existing_mapping = TrackProviderMapping.objects.filter(
            provider='spotify',
            provider_track_id=spotify_id
        ).first()

        if existing_mapping and skip_existing:
            return existing_mapping.track, False

        # Get audio features (optional - use defaults if unavailable)
        features = self.get_track_audio_features(spotify_id)
        bpm = features['bpm'] if features else None
        energy = features['energy'] if features else Decimal('0.5')

        # Fallback 1: SonoVault by ISRC (most reliable)
        isrc = spotify_track.get('external_ids', {}).get('isrc')
        if not bpm and isrc:
            bpm = SonoVaultService.get_track_bpm(isrc)

        # Fallback 2: audio analysis on preview URL
        if not bpm:
            bpm = AudioAnalysisService.get_tempo_for_track(spotify_track)

        # Fallback 3: Last.fm genre-based estimation
        if not bpm:
            artist = ', '.join([a['name'] for a in spotify_track['artists']])
            title = spotify_track['name']
            bpm = LastFmService.get_track_bpm(artist, title)

        # Final fallback to default
        if not bpm:
            bpm = Decimal('120')

        # Extract track info
        title = spotify_track['name']
        artist = ', '.join([a['name'] for a in spotify_track['artists']])
        album = spotify_track['album']['name']
        duration_seconds = spotify_track['duration_ms'] // 1000
        isrc = spotify_track.get('external_ids', {}).get('isrc')

        # Create or update track
        track, created = Track.objects.get_or_create(
            isrc=isrc,
            defaults={
                'title': title,
                'artist': artist,
                'album': album,
                'duration_seconds': duration_seconds,
                'bpm': bpm,
                'energy': energy,
            }
        )

        if not created:
            # Update BPM and energy from various sources
            track.bpm = bpm
            track.energy = energy
            track.save()

        # Create provider mapping
        mapping, mapping_created = TrackProviderMapping.objects.get_or_create(
            track=track,
            provider='spotify',
            defaults={
                'provider_track_id': spotify_id,
                'provider_url': spotify_track['external_urls']['spotify'],
            }
        )

        # Sync genres
        self._sync_genres(track, spotify_track)

        return track, created

    def _sync_genres(self, track, spotify_track):
        """Sync genres from Spotify track to Stridify"""
        # Get artist genres (Spotify doesn't provide track-level genres)
        artist_id = spotify_track['artists'][0]['id']
        try:
            artist = self.sp.artist(artist_id)
            spotify_genres = artist.get('genres', [])

            for genre_name in spotify_genres:
                # Normalize genre name
                genre_name = genre_name.strip().title()
                genre, _ = Genre.objects.get_or_create(
                    name=genre_name,
                    defaults={'slug': genre_name.lower().replace(' ', '-')}
                )
                track.genres.add(genre)
        except Exception as e:
            print(f"Error syncing genres for artist {artist_id}: {e}")

    def create_playlist(self, access_token, playlist_name, track_uris, is_public=False):
        """Create a Spotify playlist and add tracks"""
        try:
            import requests

            sp = spotipy.Spotify(auth=access_token)

            # Use the new /me/playlists endpoint instead of deprecated user_playlist_create
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'name': playlist_name,
                'public': is_public,
                'description': 'Generated by Stridify - Cadence-Based Playlists'
            }

            response = requests.post(
                'https://api.spotify.com/v1/me/playlists',
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            playlist = response.json()

            playlist_id = playlist['id']

            # Add tracks (Spotify limits to 100 tracks per request)
            for i in range(0, len(track_uris), 100):
                chunk = track_uris[i:i + 100]
                sp.playlist_add_items(playlist_id, chunk)

            return {
                'id': playlist_id,
                'url': playlist['external_urls']['spotify'],
                'name': playlist['name'],
                'tracks': len(track_uris)
            }
        except Exception as e:
            print(f"Error creating Spotify playlist: {e}")
            return None

    def get_user_saved_tracks(self, access_token, limit=50):
        """Get user's saved/liked tracks"""
        try:
            sp = spotipy.Spotify(auth=access_token)
            results = sp.current_user_saved_tracks(limit=limit)
            return [item['track'] for item in results['items']]
        except Exception as e:
            print(f"Error fetching user saved tracks: {e}")
            return []

    def bulk_sync_tracks(self, spotify_tracks):
        """Sync multiple tracks efficiently"""
        synced_tracks = []
        for spotify_track in spotify_tracks:
            track, created = self.sync_track_to_db(spotify_track)
            if track:
                synced_tracks.append({
                    'track': track,
                    'created': created,
                    'spotify_id': spotify_track['id']
                })
        return synced_tracks
