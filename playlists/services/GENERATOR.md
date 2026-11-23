# Playlist Generation Workflow

The playlist generator orchestrates the entire end-to-end workflow: from runner profile through cadence calculation, tempo targets, recommendations, and finally to playlist creation.

## Workflow Overview

```
RunnerProfile (target pace)
    ↓
resolve_runner_cadence() → CadenceResult (cadence SPM)
    ↓
get_tempo_targets_for_cadence() → CadenceToTempoResult (all BPM targets)
    ↓
recommend_tracks() for EACH sync ratio → list[TrackScore]
    ↓
select_and_order_tracks() → interleaved, ordered list
    ↓
create_playlist_records() → Playlist + PlaylistTrack entries
```

## Primary Function: `generate_playlist(request)`

Takes a `PlaylistGenerationRequest` and returns a fully-created `PlaylistGenerationResult`.

### Input: `PlaylistGenerationRequest`

```python
@dataclass
class PlaylistGenerationRequest:
    user: User                           # Runner creating the playlist
    playlist_name: str                   # Name for the playlist
    duration_minutes: int = 60           # Target playlist length
    target_energy: Optional[Decimal] = None  # Optional energy preference (0-1)
    algorithm_version: str = "1.0"       # Algorithm version for reproducibility
```

### Output: `PlaylistGenerationResult`

```python
@dataclass
class PlaylistGenerationResult:
    playlist: Playlist                               # Created playlist object
    tracks_selected: int                            # Number of tracks in playlist
    total_duration_seconds: int                     # Actual total duration
    cadence_spm: Decimal                            # Runner's cadence
    sync_ratio_distribution: dict[str, int]         # Tracks per sync ratio
```

### Workflow Steps

1. **Validate request** — ensure positive duration
2. **Fetch runner profile** — get runner's physical data and preferences
3. **Resolve cadence** — calculate SPM from pace + physical dimensions using priority chain
   - Measured cadence (from wearable) if available
   - Else measured step length
   - Else estimated from leg length
4. **Get tempo targets** — generate BPM for each sync ratio (1:1, 1:2, 2:1)
5. **Estimate track count** — calculate how many tracks needed to fill duration
6. **Generate recommendations** — for each sync ratio, get ranked recommendations
7. **Select and order tracks** — interleave across ratios for variety, respect duration
8. **Create database records** — persist Playlist and PlaylistTrack entries
9. **Return metrics** — cadence, distribution, duration for user feedback

## Supporting Functions

### `estimate_num_tracks_needed(target_duration_minutes, average_track_duration_seconds=240) → int`

Calculates how many tracks are needed.

Default assumes 4-minute average track.

```python
num_tracks = estimate_num_tracks_needed(60)  # 60 minutes
# → 15 tracks
```

### `_generate_recommendations_for_sync_ratio(...) → list[TrackScore]`

Internal function that generates recommendations for a single sync ratio.

Calls `recommend_tracks()` with appropriate BPM target.

### `_select_and_order_tracks(recommendations_by_ratio, target_duration_minutes) → list[TrackScore]`

**Key orchestration function** that selects final tracks and determines their order.

**Strategy:**

1. **Interleave across sync ratios** — creates variety by switching between sync ratios
2. **Respect duration target** — stops when playlist is long enough
3. **Use scoring as quality metric** — always takes next highest-scored track from active ratio

This prevents playlists where all tracks are half-time (or all double-time) and distributes quality across the duration.

### `_create_playlist_records(...) → Playlist`

Internal function that persists to database.

Creates:
- One `Playlist` record with metadata
- Multiple `PlaylistTrack` records (one per track) with position, score, sync ratio

Uses `transaction.atomic()` to ensure all-or-nothing consistency.

## Example Usage

```python
from decimal import Decimal
from playlists.services.generator import (
    PlaylistGenerationRequest,
    generate_playlist,
)

# Create playlist for a runner
request = PlaylistGenerationRequest(
    user=request.user,
    playlist_name="Morning Easy Run",
    duration_minutes=30,
    target_energy=Decimal("0.6"),  # Lower energy for easy run
)

result = generate_playlist(request)

print(f"Created playlist: {result.playlist.name}")
print(f"Tracks: {result.tracks_selected}")
print(f"Duration: {result.total_duration_seconds / 60} minutes")
print(f"Cadence: {result.cadence_spm} SPM")
print(f"Sync ratios used: {result.sync_ratio_distribution}")

# Access tracks
for track_entry in result.playlist.playlist_tracks.all():
    track = track_entry.track
    print(f"{track_entry.position}. {track.artist} - {track.title} "
          f"({track_entry.sync_ratio} @ {track_entry.match_score})")
```

## Error Handling

The generator raises `ValueError` for:

- **Negative/zero duration** — invalid playlist length
- **Missing runner profile** — user hasn't set up their profile
- **Missing target pace** — profile is incomplete
- **No recommendations** — no matching tracks in database or no user genre preferences
- **No tracks selected** — filtering resulted in empty playlist after all strategies

These errors provide actionable feedback to guide the user toward fixing the issue.

## Data Model Integration

### Playlist Record

Stores:
- User
- Name
- Target pace (seconds/mile) — input from profile
- Target cadence (SPM) — calculated from pace
- Target BPM — primary sync ratio BPM
- Duration (minutes) — sum of selected tracks
- Algorithm version — for reproducibility
- Created timestamp

### PlaylistTrack Records (through table)

Each track entry stores:
- Position in playlist (1-indexed, ordered)
- Match score from recommendation engine (0-1)
- Sync ratio used (which ratio this track was matched to)

Constraints ensure:
- Each track appears at most once in a playlist
- Each position is unique within a playlist

## Design Notes

1. **Multiple sync ratios** — a single playlist can have tracks from different sync ratios (1:1, 1:2, 2:1), expanding the pool of available songs
2. **Interleaving for variety** — alternating between sync ratios prevents boring long sequences of one type
3. **Duration respect** — playlist respects target duration while being pragmatic about song boundaries
4. **Atomic transactions** — either entire playlist is created or none is (no partial playlists)
5. **Cadence is primary** — cadence SPM is what matters; sync ratio is just one way to achieve synchronization
6. **Algorithm version** — recorded for reproducibility and future algorithm iterations

## Tests

Comprehensive test coverage (20+ tests) in `playlists/tests.py`:

- `EstimateNumTracksNeededTests` — duration estimation logic
- `PlaylistGenerationTests` — full end-to-end workflow
  - Basic playlist creation
  - Duration handling
  - Cadence/pace storage
  - Database record creation
  - Position ordering
  - Sync ratio assignment
  - Match score validation
  - Error cases (missing profile, invalid duration, etc.)
  - Distribution metrics
  - Energy preferences
  - Algorithm version tracking

Run tests:

```bash
python manage.py test playlists.tests.PlaylistGenerationTests
```

## Future Enhancements

1. **Playlist modes** — Easy Run, Tempo Run, Interval Training, Long Run, Race Day (each with different energy/variety strategies)
2. **Live adaptation** — adjust playlist based on runner's actual pace during workout
3. **Persistence across sessions** — save playlist preferences and reuse in future generation
4. **Sharing/discovery** — public playlists for inspiration
5. **AB/multi-variant testing** — experiment with different weighting schemes and ordering strategies
