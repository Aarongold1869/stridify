# Playlists Services

This directory contains the recommendation engine and playlist generation workflow.

## Services

### Recommendation Engine (`recommendation.py`)

Scores and ranks tracks based on BPM match (50%), genre preference (25%), energy (15%), and artist diversity (10%).

**Primary function:** `recommend_tracks(query) → list[TrackScore]`

**See:** [`README.md`](README.md) for full documentation.

### Playlist Generator (`generator.py`)

Orchestrates end-to-end playlist creation: runner profile → cadence → tempo targets → recommendations → playlist.

**Primary function:** `generate_playlist(request) → PlaylistGenerationResult`

**See:** [`GENERATOR.md`](GENERATOR.md) for full documentation.

## Quick Start

```python
from decimal import Decimal
from playlists.services.generator import (
    PlaylistGenerationRequest,
    generate_playlist,
)

# Generate a 60-minute playlist for a runner
request = PlaylistGenerationRequest(
    user=request.user,
    playlist_name="Morning Run",
    duration_minutes=60,
    target_energy=Decimal("0.75"),
)

result = generate_playlist(request)
print(f"Created playlist with {result.tracks_selected} tracks")
```

## Architecture

```
Runner Profile (pace, cadence, genres)
    ↓
Cadence Calculation (resolve from profile)
    ↓
Tempo Targets (all BPM for all sync ratios)
    ↓
Recommendations (scored tracks per sync ratio)
    ↓
Selection & Ordering (interleaved, respects duration)
    ↓
Playlist Records (Playlist + PlaylistTrack in DB)
```

## Tests

Run all playlists tests:

```bash
python manage.py test playlists
```

Specific test classes:

```bash
python manage.py test playlists.tests.BpmMatchScoreTests
python manage.py test playlists.tests.PlaylistGenerationTests
```

