# Stridify REST API Documentation

## Base URL
```
http://localhost:8000/api/v1/
```

## Authentication
All endpoints (except registration and public endpoints) require a Bearer token:
```
Authorization: Token <your-token>
```

---

## Endpoints

### 1. Authentication

#### Register New User
**POST** `/auth/register/register/`

Request:
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "password": "SecurePassword123!",
  "password2": "SecurePassword123!"
}
```

Response (201 Created):
```json
{
  "user": {
    "id": 8,
    "username": "newuser",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": ""
  },
  "token": "0d727fcdbffa72cad76372078798b74bcbe6faac"
}
```

---

### 2. Runner Profile Management

#### Create/Update Runner Profile
**POST** `/profiles/`

Request:
```json
{
  "height_inches": "70",
  "leg_length_inches": "33",
  "target_pace_seconds": "600",
  "measured_cadence_spm": null
}
```

Response (201 Created):
```json
{
  "id": 5,
  "user": {...},
  "height_inches": "70.00",
  "height_display": "5'10\"",
  "leg_length_inches": "33.00",
  "target_pace_seconds": 600,
  "pace_display": "10:00/mile",
  "measured_cadence_spm": null,
  "cadence_spm": 145.7,
  "created_at": "2026-11-25T01:24:17.034036Z"
}
```

#### List Runner Profile
**GET** `/profiles/`

#### Retrieve Profile Details
**GET** `/profiles/{id}/`

#### Update Profile
**PATCH** `/profiles/{id}/`

---

### 3. Genre Preferences

#### Add Genre Preference
**POST** `/genre-preferences/`

Request:
```json
{
  "genre_id": 2,
  "preference_weight": "5"
}
```

Response (201 Created):
```json
{
  "id": 13,
  "genre": {
    "id": 2,
    "name": "Alternative",
    "slug": "alternative",
    "track_count": 6
  },
  "preference_weight": "5.00"
}
```

#### List Your Preferences
**GET** `/genre-preferences/`

#### Update Preference
**PATCH** `/genre-preferences/{id}/`

#### Delete Preference
**DELETE** `/genre-preferences/{id}/`

---

### 4. Music Browse

#### List All Genres
**GET** `/genres/`

**Query Parameters:**
- None (supports pagination via `page` parameter)

Response:
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Rock",
      "slug": "rock",
      "track_count": 11
    },
    ...
  ]
}
```

#### List All Tracks
**GET** `/tracks/`

**Query Parameters:**
- `bpm_min`: Minimum BPM (e.g., `?bpm_min=160`)
- `bpm_max`: Maximum BPM (e.g., `?bpm_max=175`)
- `energy_min`: Minimum energy (0-1) (e.g., `?energy_min=0.5`)
- `energy_max`: Maximum energy (0-1) (e.g., `?energy_max=0.9`)
- `genres`: Genre IDs (comma-separated) (e.g., `?genres=1,2`)
- `search`: Search in title/artist/album (e.g., `?search=blinding`)
- `page`: Pagination (e.g., `?page=2`)

**Example:**
```
GET /tracks/?bpm_min=160&bpm_max=175&search=weekend
```

Response:
```json
{
  "count": 22,
  "next": "http://localhost:8000/api/v1/tracks/?page=2",
  "previous": null,
  "results": [
    {
      "id": 7,
      "title": "Blinding Lights",
      "artist": "The Weeknd",
      "bpm": "171.00",
      "energy": "0.730",
      "genre_names": ["Electronic", "Pop"]
    },
    ...
  ]
}
```

---

### 5. Playlist Management

#### List Your Playlists
**GET** `/playlists/`

Response:
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "name": "Alice - Mixed 45min Run",
      "user": "runner_alice",
      "target_pace_seconds": 600,
      "pace_display": "10:00/mile",
      "target_cadence_spm": "160.00",
      "cadence_display": "160.00 SPM",
      "target_bpm": "160.00",
      "duration_minutes": 43.3,
      "track_count": 10,
      "algorithm_version": "1.0",
      "playlist_tracks": [...],
      "created_at": "2026-11-25T01:05:28Z"
    },
    ...
  ]
}
```

#### Retrieve Playlist Details
**GET** `/playlists/{id}/`

#### Generate New Playlist
**POST** `/playlists/generate/`

Request:
```json
{
  "playlist_name": "Evening Run",
  "duration_minutes": 45,
  "target_energy": "0.75"
}
```

Response (201 Created):
```json
{
  "id": 10,
  "name": "Evening Run",
  "user": "runner_alice",
  "target_cadence_spm": "160.00",
  "cadence_display": "160.00 SPM",
  "target_bpm": "160.00",
  "duration_minutes": 43.3,
  "track_count": 10,
  "playlist_tracks": [
    {
      "id": 43,
      "track": {...},
      "position": 1,
      "sync_ratio": "1.0",
      "match_score": "0.90"
    },
    ...
  ],
  "created_at": "2026-11-25T01:24:45Z"
}
```

**Parameters:**
- `playlist_name` (required): Name for the playlist
- `duration_minutes` (required): Duration in minutes (15, 30, 45, 60, 75, 90, 120, 180)
- `target_energy` (optional): Target energy level (0-1 scale)

#### Get Playlist Sync Ratio Stats
**GET** `/playlists/{id}/sync_ratio_stats/`

Response:
```json
{
  "playlist": "Evening Run",
  "sync_ratios": {
    "1.0": 7,
    "0.5": 2,
    "2.0": 1
  },
  "total_tracks": 10
}
```

---

## Common Use Cases

### 1. Complete Registration & Profile Setup
```bash
# 1. Register
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "first_name": "Jane",
    "password": "Password123!",
    "password2": "Password123!"
  }' | jq -r '.token')

# 2. Create runner profile
curl -X POST http://localhost:8000/api/v1/profiles/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "height_inches": "66",
    "leg_length_inches": "31",
    "target_pace_seconds": "660"
  }'

# 3. Add genre preferences
curl -X POST http://localhost:8000/api/v1/genre-preferences/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"genre_id": 2, "preference_weight": "5"}'
```

### 2. Generate a Playlist
```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8000/api/v1/playlists/generate/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_name": "Morning Run",
    "duration_minutes": 30,
    "target_energy": "0.80"
  }'
```

### 3. Search Tracks by BPM
```bash
# Find all tracks between 160-170 BPM
curl "http://localhost:8000/api/v1/tracks/?bpm_min=160&bpm_max=170"
```

### 4. Search Tracks by Genre
```bash
# Find all Rock (id=1) and Alternative (id=2) tracks
curl "http://localhost:8000/api/v1/tracks/?genres=1,2"
```

---

## Error Responses

All errors follow this format:
```json
{
  "error": "Error message describing what went wrong"
}
```

or for validation errors:
```json
{
  "field_name": ["Error message for this field"],
  "other_field": ["Another error"]
}
```

---

## Status Codes

- `200 OK`: Success
- `201 Created`: Resource created successfully
- `400 Bad Request`: Validation error or missing required fields
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: You don't have permission to access this resource
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Notes

- All timestamps are in UTC (ISO 8601 format)
- Pagination defaults to 20 items per page
- BPM and energy values are returned as strings (Decimal types for precision)
- Cadence is automatically calculated from your runner profile (height + pace)
- Playlists are generated with track interleaving across sync ratios (1:2, 1:1, 2:1) for variety
