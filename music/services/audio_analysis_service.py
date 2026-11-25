import os
import tempfile
import requests
import librosa
import numpy as np
from pathlib import Path
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AudioAnalysisService:
    """Extract tempo/BPM from audio files using librosa."""

    CACHE_DIR = Path(tempfile.gettempdir()) / "stridify_audio_cache"

    @classmethod
    def _ensure_cache_dir(cls):
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _get_cache_path(cls, preview_url: str) -> Path:
        """Generate cache path from preview URL hash."""
        import hashlib
        url_hash = hashlib.md5(preview_url.encode()).hexdigest()
        return cls.CACHE_DIR / f"{url_hash}.bpm"

    @classmethod
    def extract_tempo_from_preview(cls, preview_url: str) -> Decimal | None:
        """
        Download Spotify preview MP3 and extract tempo using librosa.
        Results are cached to avoid re-downloading.

        Args:
            preview_url: Spotify preview URL (30-second MP3)

        Returns:
            BPM as Decimal, or None if extraction fails
        """
        if not preview_url:
            return None

        cls._ensure_cache_dir()
        cache_path = cls._get_cache_path(preview_url)

        # Check cache first
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    bpm_str = f.read().strip()
                    if bpm_str == "FAILED":
                        return None
                    return Decimal(bpm_str)
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")

        # Download and analyze
        try:
            logger.info(f"Downloading preview: {preview_url[:50]}...")
            response = requests.get(preview_url, timeout=10)
            response.raise_for_status()

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            try:
                # Load audio and extract tempo
                y, sr = librosa.load(tmp_path, sr=None)
                onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                tempo = librosa.feature.tempo(onset_env=onset_env, sr=sr)[0]

                bpm = Decimal(str(round(float(tempo), 1)))
                logger.info(f"Extracted BPM: {bpm}")

                # Cache result
                with open(cache_path, 'w') as f:
                    f.write(str(bpm))

                return bpm

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download preview: {e}")
            with open(cache_path, 'w') as f:
                f.write("FAILED")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract tempo: {e}")
            with open(cache_path, 'w') as f:
                f.write("FAILED")
            return None

    @classmethod
    def get_tempo_for_track(cls, track_data: dict) -> Decimal | None:
        """
        Extract tempo from Spotify track preview URL.

        Args:
            track_data: Spotify track object containing preview_url

        Returns:
            BPM as Decimal, or None if unavailable
        """
        preview_url = track_data.get('preview_url')
        if not preview_url:
            logger.debug(f"No preview URL for track: {track_data.get('name')}")
            return None

        return cls.extract_tempo_from_preview(preview_url)
