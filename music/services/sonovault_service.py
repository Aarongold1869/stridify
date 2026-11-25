from sonovault import SonoVault
from decimal import Decimal
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SonoVaultService:
    """Service for enriching track metadata via SonoVault API."""

    _client = None

    @classmethod
    def get_client(cls):
        """Get or create SonoVault client."""
        if cls._client is None:
            if not settings.SONOVAULT_API_KEY:
                raise ValueError("SONOVAULT_API_KEY not configured in settings")
            cls._client = SonoVault(api_key=settings.SONOVAULT_API_KEY)
        return cls._client

    @classmethod
    def get_track_by_isrc(cls, isrc: str) -> dict | None:
        """
        Look up track metadata by ISRC code.

        Args:
            isrc: ISRC code (e.g., "USRC17607839")

        Returns:
            Dict with track metadata including BPM, or None if not found
        """
        if not isrc:
            return None

        try:
            client = cls.get_client()
            result = client.tracks.by_isrc(isrc)

            if result:
                # Result can be a dict or list
                track = result[0] if isinstance(result, list) else result

                # Extract artist name from various possible locations
                artist_name = None
                if track.get('artist'):
                    artist_name = track['artist'].get('name')
                elif track.get('artists') and len(track['artists']) > 0:
                    artist_name = track['artists'][0].get('name')

                bpm = None
                if track.get('bpm'):
                    bpm = Decimal(str(track['bpm']))

                return {
                    'title': track.get('title'),
                    'artist': artist_name,
                    'bpm': bpm,
                    'key': track.get('key_musical'),
                    'isrc': track.get('isrc'),
                    'source': 'sonovault'
                }
            return None

        except Exception as e:
            logger.warning(f"SonoVault ISRC lookup failed for {isrc}: {e}")
            return None

    @classmethod
    def get_track_bpm(cls, isrc: str) -> Decimal | None:
        """
        Get BPM for a track by ISRC.

        Args:
            isrc: ISRC code

        Returns:
            BPM as Decimal, or None if not found
        """
        track = cls.get_track_by_isrc(isrc)
        if track and track.get('bpm'):
            return track['bpm']
        return None

    @classmethod
    def batch_lookup_isrc(cls, isrcs: list) -> dict:
        """
        Batch lookup multiple ISRC codes.

        Args:
            isrcs: List of ISRC codes (max 100)

        Returns:
            Dict mapping ISRC → track data
        """
        if not isrcs:
            return {}

        # Limit to 100 per API request
        isrcs = isrcs[:100]

        results = {}

        try:
            client = cls.get_client()

            for isrc in isrcs:
                track = cls.get_track_by_isrc(isrc)
                if track:
                    results[isrc] = track

        except Exception as e:
            logger.warning(f"SonoVault batch lookup failed: {e}")

        return results
