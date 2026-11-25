# Spotify Integration Guide

## Overview

Stridify integrates with Spotify to:
- Authenticate users via Spotify OAuth
- Fetch audio features (BPM, energy, danceability) for accurate playlist generation
- Create and export playlists directly to users' Spotify accounts
- Sync user's saved tracks to build a personalized track database

---

## Setup: Spotify Developer App

### 1. Register at Spotify Developer Dashboard

1. Go to [developer.spotify.com](https://developer.spotify.com)
2. Sign in with your Spotify account (create one if needed)
3. Create a new app:
   - Name: "Stridify" (or your preference)
   - Accept terms and click "Create"
4. You'll receive:
   - **Client ID**
   - **Client Secret** (keep this secret!)

### 2. Configure Redirect URI

1. In your app settings, add Redirect URIs:
   - Development: `http://localhost:8000/api/v1/auth/spotify/callback/`
   - Production: `https://your-domain.com/api/v1/auth/spotify/callback/`

### 3. Set Environment Variables

Update `Stridify/settings.py` with your credentials:

```python
SPOTIFY_CLIENT_ID = 'your_client_id_here'
SPOTIFY_CLIENT_SECRET = 'your_client_secret_here'
SPOTIFY_REDIRECT_URI = 'http://localhost:8000/api/v1/auth/spotify/callback/'
```

**For production**, use environment variables:
```bash
export SPOTIFY_CLIENT_ID='xxxxx'
export SPOTIFY_CLIENT_SECRET='xxxxx'
export SPOTIFY_REDIRECT_URI='https://your-domain.com/api/v1/auth/spotify/callback/'
```

Then in settings:
```python
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
```

---

## API Endpoints

### Spotify Authentication

#### 1. Get Spotify Login URL
**GET** `/api/v1/auth/spotify/login/`

**Requires:** Authentication

Response:
```json
{
  "auth_url": "https://accounts.spotify.com/authorize?client_id=..."
}
```

**Flow:**
1. Frontend calls this endpoint
2. User clicks returned auth_url
3. Spotify redirects to callback URL with authorization code

#### 2. OAuth Callback
**GET** `/api/v1/auth/spotify/callback/?code=xxxxx`

**Requires:** Authentication

Response (200 OK):
```json
{
  "message": "Successfully connected to Spotify",
  "spotify_user": {
    "id": "spotify_user_123",
    "display_name": "John Doe",
    "email": "john@spotify.com"
  }
}
```

**What happens:**
- Exchange code for access/refresh tokens
- Store tokens in SpotifyAuth model
- User now connected to Spotify

#### 3. Check Connection Status
**GET** `/api/v1/auth/spotify/status/`

**Requires:** Authentication

Response:
```json
{
  "connected": true,
  "data": {
    "spotify_user_id": "spotify_user_123",
    "is_expired": false,
    "created_at": "2026-11-25T12:00:00Z",
    "updated_at": "2026-11-25T12:00:00Z"
  }
}
```

#### 4. Disconnect Spotify
**POST** `/api/v1/auth/spotify/disconnect/`

**Requires:** Authentication

Response (200 OK):
```json
{
  "message": "Spotify account disconnected"
}
```

---

### Music Library Sync

#### Sync User's Saved Tracks
**POST** `/api/v1/auth/spotify/sync_library/`

**Requires:** Authentication + Spotify connection

Response (200 OK):
```json
{
  "synced_count": 42,
  "new_count": 10,
  "tracks": [
    {
      "title": "Blinding Lights",
      "artist": "The Weeknd",
      "bpm": 171.0,
      "created": false
    },
    ...
  ]
}
```

**What happens:**
1. Fetches user's 50 most recent saved tracks from Spotify
2. For each track:
   - Extracts audio features (BPM, energy, etc.)
   - Stores in Stridify Track table
   - Creates SpotifyTrackMapping
3. Returns summary of synced tracks

---

## Data Models

### SpotifyAuth
Stores user's Spotify OAuth credentials:

```python
class SpotifyAuth(models.Model):
    user = OneToOneField(User)
    spotify_user_id = CharField()          # Spotify's unique user ID
    access_token = TextField()              # Short-lived (1 hour)
    refresh_token = TextField()             # Long-lived (doesn't expire)
    token_expires_at = DateTimeField()      # When access_token expires
    scope = CharField()                     # OAuth scopes granted
    created_at = DateTimeField()
    updated_at = DateTimeField()
```

### TrackProviderMapping
Links Stridify tracks to Spotify IDs:

```python
class TrackProviderMapping(models.Model):
    track = ForeignKey(Track)
    provider = CharField(choices=['spotify', 'apple_music'])
    provider_track_id = CharField()         # Spotify's track ID
    provider_url = URLField()               # Link to Spotify
    created_at = DateTimeField()
```

---

## Workflow: Complete Integration

### 1. User Registration & Spotify Connection
```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePass123!",
    "password2": "SecurePass123!"
  }'
# Returns: { access, refresh, user }

# Get Spotify login URL
curl http://localhost:8000/api/v1/auth/spotify/login/ \
  -H "Authorization: Bearer <access_token>"
# Returns: { auth_url: "https://accounts.spotify.com/authorize?..." }

# User clicks auth_url → Spotify → Redirect to callback
# Browser redirects to: /api/v1/auth/spotify/callback/?code=xxxxx
# Returns: { message, spotify_user }
```

### 2. Sync Music Library
```bash
curl -X POST http://localhost:8000/api/v1/auth/spotify/sync_library/ \
  -H "Authorization: Bearer <access_token>"
# Returns: { synced_count, new_count, tracks[] }
```

### 3. Generate Playlist with Real Data
```bash
curl -X POST http://localhost:8000/api/v1/playlists/generate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_name": "Morning Run",
    "duration_minutes": 30
  }'
# Playlist generated using real Spotify audio features!
```

### 4. Export to Spotify (Future)
```bash
curl -X POST http://localhost:8000/api/v1/playlists/123/export_to_spotify/ \
  -H "Authorization: Bearer <access_token>"
# Creates playlist in user's Spotify account
```

---

## Management Commands

### Sync Audio Features from Spotify

Fetch and store audio features for existing tracks:

```bash
# Process 50 tracks
python manage.py sync_spotify_audio_features

# Process 100 tracks
python manage.py sync_spotify_audio_features --limit=100

# Only process tracks without Spotify mapping
python manage.py sync_spotify_audio_features --unmapped-only
```

Output:
```
Processing: Blinding Lights
  [CREATED] BPM: 171.0, Energy: 0.84

Processing: In the End
  [UPDATED] BPM: 160.0, Energy: 0.85

========================
[OK] SPOTIFY SYNC COMPLETE
========================
Updated: 15
Created: 25
Errors: 2
Total: 40
```

---

## Token Management

### Access Token Lifetime
- **Access Token:** 1 hour (auto-refresh recommended)
- **Refresh Token:** Indefinite (don't expire, but can be revoked)

### Auto-Refresh
When making Spotify API calls, tokens are automatically refreshed if expired:

```python
if spotify_auth.is_expired:
    spotify_auth.refresh_access_token(sp_oauth)
```

---

## Security Best Practices

✅ **DO:**
- Store `refresh_token` securely (database is OK if encrypted)
- Keep `client_secret` out of frontend code
- Use HTTPS in production
- Rotate tokens regularly
- Revoke access if user disconnects

❌ **DON'T:**
- Expose `client_secret` in frontend
- Log access tokens
- Hardcode credentials
- Trust user input (validate Spotify IDs)

---

## Spotify API Quotas & Limits

- **Rate Limiting:** 429 Too Many Requests
- **Search Requests:** Unlimited (included in rate limit)
- **Audio Features:** Included in rate limit
- **Playlist Creation:** No limit per se, but rate-limited

---

## Error Handling

### Common Errors

**401 Unauthorized**
```json
{"error": "Invalid or expired token"}
```
→ Call refresh endpoint or re-authenticate

**404 Not Found**
```json
{"error": "Track not found on Spotify"}
```
→ Spotify doesn't have this track in their catalog

**429 Too Many Requests**
```json
{"error": "Rate limit exceeded"}
```
→ Wait before making more requests

**403 Forbidden**
```json
{"error": "Insufficient permissions"}
```
→ User may need to re-authenticate with broader scopes

---

## Testing

```bash
# Run tests
python manage.py test

# Test Spotify connection
python manage.py shell
>>> from runners.models import SpotifyAuth
>>> from music.services.spotify_service import SpotifyService
>>> auth = SpotifyAuth.objects.first()
>>> service = SpotifyService(auth.access_token)
>>> track = service.search_track("Blinding Lights The Weeknd")
>>> print(track['name'], track['id'])
```

---

## Future Enhancements

- [ ] Export playlists to Spotify
- [ ] Real-time playlist sync to Spotify
- [ ] Apple Music integration
- [ ] YouTube Music integration
- [ ] Playlist collaboration
- [ ] User-generated recommendations
- [ ] Spotify recommendation engine
- [ ] Save/liked tracks sync automation
- [ ] Spotify follow/playlist follower tracking

---

## Troubleshooting

### "Invalid Client ID"
→ Check settings.py has correct `SPOTIFY_CLIENT_ID`

### "Redirect URI mismatch"
→ Redirect URI in app settings must exactly match settings.py

### "Unauthorized client"
→ Client Secret incorrect or not provided

### "Track not found"
→ Spotify may not have this track; try with artist + title search

### "Token expired"
→ Call refresh endpoint to get new access token

### "User not connected to Spotify"
→ Call `/auth/spotify/login/` first to get auth URL
