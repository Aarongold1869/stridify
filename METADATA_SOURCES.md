# Music Streaming Services: Track Metadata Available

## Overview

Different streaming services provide varying levels of track metadata. For Stridify's needs (BPM, genre, energy for playlist generation), **Spotify is by far the best source**.

---

## Metadata Comparison by Service

### **Spotify API** ⭐ Best for Stridify
**Cost:** Free tier (rate-limited), Premium for higher limits  
**Coverage:** ~100M tracks

#### Available Metadata:
✅ **Audio Features** (via `/audio-features` endpoint):
- **BPM (Tempo)** — Yes, explicit BPM value (0-240)
- **Energy** — Yes (0-1 scale) - intensity and activity
- **Danceability** — Yes (0-1) - rhythm regularity
- **Valence** — Yes (0-1) - musical positiveness
- **Acousticness** — Yes (0-1) - acoustic vs electronic
- **Instrumentalness** — Yes (0-1) - absence of vocals
- **Liveness** — Yes (0-1) - audience presence
- **Speechiness** — Yes (0-1) - spoken words presence
- **Mode** — Major/minor key
- **Time Signature** — 3/4, 4/4, etc.
- **Key** — Pitch class (0-11)

✅ **Track Metadata:**
- Title, artist, album
- Release date
- Duration
- ISRC (International Standard Recording Code)
- Genres (at artist level)
- Popularity score (0-100)
- Explicit flag
- Preview URL (30-second clip)

❌ **Not Available:**
- Genre at track level (only artist/album genres)
- More granular mood/era classification

#### Example Response:
```json
{
  "acousticness": 0.00242,
  "analysis_url": "https://api.spotify.com/v1/audio_analysis/...",
  "danceability": 0.585,
  "duration_ms": 237973,
  "energy": 0.842,
  "id": "11dFghVhatMKQ6ibJ8V3iq",
  "instrumentalness": 0.00686,
  "key": 9,
  "liveness": 0.0867,
  "loudness": -5.599,
  "mode": 0,
  "speechiness": 0.0556,
  "tempo": 130.039,
  "time_signature": 4,
  "track_href": "https://api.spotify.com/v1/tracks/11dFghVhatMKQ6ibJ8V3iq",
  "type": "audio_features",
  "uri": "spotify:track:11dFghVhatMKQ6ibJ8V3iq",
  "valence": 0.418
}
```

---

### **Apple Music API**
**Cost:** Free (requires developer account)  
**Coverage:** ~100M tracks (similar to Spotify)

#### Available Metadata:
✅ **Track Data:**
- Title, artist, album
- Release date
- Duration
- Genres
- Rating/explicit flag

⚠️ **Limited Audio Features:**
- Some metadata via Shazam integration
- Not designed for detailed audio analysis

❌ **Not Available:**
- BPM/Tempo
- Energy levels
- Danceability
- Other acoustic analysis
- Audio features endpoints

---

### **YouTube Music API**
**Cost:** Free (requires API key)  
**Coverage:** Largest catalog but poorest metadata

#### Available Metadata:
✅ **Basic Data:**
- Title, artist
- Duration
- Thumbnail/artwork

❌ **Audio Features:**
- BPM — No
- Energy — No
- Genre — Limited
- Audio analysis — No

**Verdict:** Only useful for music discovery, not for audio-analysis-based playlist generation.

---

### **Alternative/Supplementary Sources**

#### **MusicBrainz + AcousticBrainz**
**Cost:** Free & open source  
**Coverage:** ~30M tracks (less comprehensive)

✅ **Available:**
- BPM (via AcousticBrainz)
- Genre (community-tagged)
- ISRC matching to other DBs
- Low-Level audio features (timbral, spectral)

❌ **Limitations:**
- Lower coverage than commercial APIs
- Variable data quality (community-maintained)
- Slower/less reliable for real-time lookup
- Harder to match tracks across catalogs

#### **Last.fm API**
**Cost:** Free

✅ **Available:**
- Genre tags (crowd-sourced)
- Listener/tag counts

❌ **Not Available:**
- BPM
- Energy/danceability
- Official metadata

#### **Genius API**
**Cost:** Free

✅ **Available:**
- Lyrics
- Artist/song metadata

❌ **Not Available:**
- BPM
- Audio features
- Streaming availability

#### **Beatport API** (EDM-specific)
**Cost:** Paid  
**Coverage:** EDM music only

✅ **Available:**
- BPM (accurate for EDM)
- Genre (detailed EDM subgenres)
- Key

❌ **Limitations:**
- EDM/dance music only
- Limited coverage outside electronic

---

## Recommendation for Stridify

### **Best Strategy: Spotify-First with Fallback**

```
┌─────────────────────────────────────────────────┐
│  User wants to export playlist to streaming    │
│  service (e.g., Spotify)                       │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │ Spotify API (Primary)    │
        │ ✅ BPM/Energy/Genres     │
        │ ✅ 100M+ track coverage   │
        │ ✅ Real-time data        │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼──────────────────┐
        │ Store in Stridify DB:          │
        │ - track_id (Spotify ID)        │
        │ - bpm, energy, genre           │
        │ - sync ratios to cache         │
        │ - last_updated timestamp       │
        └─────────────┬──────────────────┘
                      │
        ┌─────────────▼────────────────────┐
        │ User can:                        │
        │ - Generate playlists            │
        │ - Optimize by audio features    │
        │ - Export directly to Spotify    │
        └────────────────────────────────┘
```

### **Implementation Path**

**Phase 1 (Current):** ✅ Manual data entry  
- We seeded 42 tracks with estimated BPM/energy
- Good for MVP/testing

**Phase 2 (Recommended):** Spotify Integration  
- Connect user's Spotify account via OAuth
- Fetch audio features for songs in their library
- Store in `Track` table with `track_provider` mapping
- Use for playlist generation

**Phase 3 (Future):** Apple Music fallback  
- For users without Spotify
- Lower fidelity but covers more users

---

## Spotify API: Track Lookup Flow

### How to Get BPM & Audio Features

```python
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Authenticate
auth = SpotifyClientCredentials(
    client_id='your_client_id',
    client_secret='your_client_secret'
)
sp = spotipy.client.Spotify(auth_manager=auth)

# Search for track
results = sp.search(q='Blinding Lights The Weeknd', type='track', limit=1)
track = results['tracks']['items'][0]
track_id = track['id']

# Get audio features
features = sp.audio_features(track_id)[0]

print(f"BPM: {features['tempo']}")
print(f"Energy: {features['energy']}")
print(f"Genre: {track['artists'][0]['genres']}")
```

### Database Integration

Add to `Track` model:

```python
class Track(models.Model):
    # ... existing fields ...
    
    # Provider mappings
    spotify_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    apple_music_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata last fetched
    metadata_source = models.CharField(
        max_length=20, 
        choices=[('manual', 'Manual'), ('spotify', 'Spotify'), ('apple', 'Apple')],
        default='manual'
    )
    metadata_updated_at = models.DateTimeField(auto_now=True)
    
    # Confidence score for auto-fetched data
    bpm_confidence = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=1.0,  # 1.0 = manual, 0.9 = Spotify, 0.7 = fallback
        help_text="Confidence in BPM accuracy"
    )
```

---

## Comparison Table

| Feature | Spotify | Apple Music | YouTube Music | MusicBrainz | Beatport |
|---------|---------|-------------|---------------|-------------|----------|
| **BPM** | ✅ Yes | ❌ No | ❌ No | ⚠️ Limited | ✅ Yes |
| **Energy** | ✅ Yes | ❌ No | ❌ No | ❌ No | ⚠️ Limited |
| **Danceability** | ✅ Yes | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Genre** | ⚠️ Artist level | ✅ Track level | ⚠️ Limited | ✅ Tags | ✅ Detailed |
| **Coverage** | 100M+ | 100M+ | 150M+ | 30M | 10M (EDM) |
| **Cost** | Free/Paid | Free | Free | Free | Paid |
| **Real-time** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Slower | ✅ Yes |
| **Accuracy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Recommended Data Flow

### For MVP (Current)
✅ Manual entry → Store in DB → Use for playlists

### For Production
```
Spotify OAuth login
    ↓
Get user's liked songs
    ↓
Fetch audio features batch
    ↓
Store with track_provider mapping
    ↓
Use for playlist generation
    ↓
Export back to Spotify
```

---

## Next Steps

**To integrate Spotify:**

1. Register Stridify app at [developer.spotify.com](https://developer.spotify.com)
2. Install `spotipy` library
3. Add Spotify OAuth flow to registration
4. Create management command to bulk-fetch audio features
5. Add `TrackProviderMapping` model to link Stridify tracks to Spotify IDs
6. Update `generate_playlist()` to prefer provider data with fallback to manual

Would you like me to start implementing Spotify integration next?
