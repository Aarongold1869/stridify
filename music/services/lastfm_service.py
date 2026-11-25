import requests
from decimal import Decimal
from django.conf import settings
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class LastFmService:
    """Service for enriching track metadata via Last.fm API."""

    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    CACHE_DIR = Path(settings.BASE_DIR) / ".lastfm_cache"

    @classmethod
    def _ensure_cache_dir(cls):
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _get_cache_key(cls, artist: str, title: str) -> str:
        """Generate cache filename from artist and title."""
        import hashlib
        key = f"{artist}|{title}".lower()
        return hashlib.md5(key.encode()).hexdigest()

    @classmethod
    def _get_cached_bpm(cls, artist: str, title: str) -> Decimal | None:
        """Check if track BPM is cached."""
        cls._ensure_cache_dir()
        cache_file = cls.CACHE_DIR / f"{cls._get_cache_key(artist, title)}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if data.get('bpm'):
                        return Decimal(str(data['bpm']))
                    return None
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")
        return None

    @classmethod
    def _cache_bpm(cls, artist: str, title: str, bpm: Decimal | None):
        """Cache BPM result."""
        cls._ensure_cache_dir()
        cache_file = cls.CACHE_DIR / f"{cls._get_cache_key(artist, title)}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump({'bpm': float(bpm) if bpm else None}, f)
        except Exception as e:
            logger.warning(f"Failed to cache BPM: {e}")

    @classmethod
    def get_track_bpm(cls, artist: str, title: str) -> Decimal | None:
        """
        Get BPM for a track from Last.fm.

        Args:
            artist: Artist name
            title: Track title

        Returns:
            BPM as Decimal, or None if not found
        """
        if not settings.LASTFM_API_KEY:
            logger.warning("Last.fm API key not configured")
            return None

        # Check cache first
        cached_bpm = cls._get_cached_bpm(artist, title)
        if cached_bpm is not None:
            return cached_bpm

        try:
            # Query Last.fm for track info
            params = {
                'method': 'track.getInfo',
                'artist': artist,
                'track': title,
                'api_key': settings.LASTFM_API_KEY,
                'format': 'json'
            }

            response = requests.get(cls.BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                logger.debug(f"Last.fm error: {data['error']}")
                cls._cache_bpm(artist, title, None)
                return None

            # Try to extract tempo from toptags (genre-based heuristic)
            track = data.get('track', {})
            toptags = track.get('toptags', {}).get('tag', [])

            if not isinstance(toptags, list):
                toptags = [toptags]

            # Genre-based BPM estimation (rough heuristic)
            bpm = cls._estimate_bpm_from_genres(toptags)

            if bpm:
                logger.debug(f"Estimated BPM from genres: {bpm}")
                cls._cache_bpm(artist, title, bpm)
                return bpm

            # No data found
            cls._cache_bpm(artist, title, None)
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Last.fm request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error processing Last.fm data: {e}")
            return None

    @classmethod
    def _estimate_bpm_from_genres(cls, tags: list) -> Decimal | None:
        """
        Estimate BPM from genre tags (very rough heuristic).
        This is not accurate but better than nothing.
        """
        # Genre-to-approximate-BPM mappings
        genre_bpm = {
            'slow': Decimal('70'),
            'ballad': Decimal('60'),
            'hip-hop': Decimal('90'),
            'hip hop': Decimal('90'),
            'rap': Decimal('90'),
            'reggae': Decimal('76'),
            'folk': Decimal('90'),
            'acoustic': Decimal('90'),
            'metal': Decimal('140'),
            'rock': Decimal('120'),
            'pop': Decimal('100'),
            'electronic': Decimal('120'),
            'edm': Decimal('128'),
            'dance': Decimal('128'),
            'house': Decimal('128'),
            'techno': Decimal('128'),
            'trance': Decimal('135'),
            'dnb': Decimal('180'),
            'drum and bass': Decimal('180'),
            'jazz': Decimal('100'),
            'classical': Decimal('80'),
            'punk': Decimal('180'),
        }

        if not tags:
            return None

        tag_names = [t.get('name', '').lower() for t in tags] if isinstance(tags, list) else []

        # Return BPM for first matching tag
        for tag in tag_names:
            for genre_key, bpm in genre_bpm.items():
                if genre_key in tag:
                    return bpm

        return None
