# Authentication & Authorization Guide

## Overview

Stridify uses JWT (JSON Web Tokens) for stateless, scalable authentication with token refresh capabilities. All sensitive endpoints require authentication.

---

## Authentication Methods

### 1. JWT Token Authentication (Recommended)
Stateless, scalable, mobile-friendly. Best for apps and microservices.

**Token Types:**
- **Access Token** (short-lived, 1 hour) — Use for API requests
- **Refresh Token** (long-lived, 7 days) — Use to get new access tokens

---

## Authentication Endpoints

### Register New User
**POST** `/api/v1/auth/register/register/`

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
    "id": 1,
    "username": "newuser",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": ""
  },
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Password Requirements:**
- Minimum 8 characters
- Must contain uppercase, lowercase, numbers
- Cannot be entirely numeric
- Cannot match username or email

---

### Login (Get Tokens)
**POST** `/api/v1/auth/login/`

Request:
```json
{
  "username": "newuser",
  "password": "SecurePassword123!"
}
```

Response (200 OK):
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Token Lifetime:**
- Access: 1 hour
- Refresh: 7 days

---

### Refresh Access Token
**POST** `/api/v1/auth/refresh/`

**When to use:** When access token expires (401 Unauthorized)

Request:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response (200 OK):
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Note:** Tokens are automatically rotated on refresh for security.

---

### Get Current User Info
**GET** `/api/v1/users/me/`

**Requires:** Authentication (Bearer token)

Response:
```json
{
  "id": 1,
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": ""
}
```

---

### Change Password
**POST** `/api/v1/users/change_password/`

**Requires:** Authentication

Request:
```json
{
  "old_password": "SecurePassword123!",
  "new_password": "NewPassword456!",
  "new_password2": "NewPassword456!"
}
```

Response (200 OK):
```json
{
  "message": "Password changed successfully"
}
```

---

### Request Password Reset
**POST** `/api/v1/users/request_password_reset/`

**Permission:** Anyone (unauthenticated)

Request:
```json
{
  "email": "user@example.com"
}
```

Response (200 OK):
```json
{
  "message": "If a user with this email exists, a reset link will be sent"
}
```

**Note:** Actual email sending not yet implemented. Currently validates email exists.

---

## Using Tokens

### Bearer Token Header
All authenticated requests must include:
```
Authorization: Bearer <access_token>
```

### Example Request
```bash
curl -X GET http://localhost:8000/api/v1/profiles/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token in Response Header
Some endpoints may return tokens in response headers for convenience.

---

## Security Features

### Token Rotation
- Tokens auto-rotate on refresh for added security
- Old tokens are automatically blacklisted
- Each login/refresh generates new tokens

### Password Validation
- Minimum 8 characters
- Must be sufficiently complex
- Cannot reuse common passwords
- Must differ from username/email

### Rate Limiting
- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour
- Prevents brute force attacks

### User Isolation
- Users can only access their own data
- Cannot view/modify other users' profiles, playlists, preferences
- Admin endpoints (future) for data management

---

## Common Workflows

### 1. Register & Create Profile
```bash
# Register and get tokens
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "first_name": "Alice",
    "password": "SecurePass123!",
    "password2": "SecurePass123!"
  }')

ACCESS=$(echo $RESPONSE | jq -r '.access')

# Create runner profile
curl -X POST http://localhost:8000/api/v1/profiles/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "height_inches": "66",
    "leg_length_inches": "31",
    "target_pace_seconds": "600"
  }'
```

### 2. Login & Generate Playlist
```bash
# Login
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!"
  }')

ACCESS=$(echo $LOGIN_RESPONSE | jq -r '.access')

# Generate playlist
curl -X POST http://localhost:8000/api/v1/playlists/generate/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_name": "Morning Run",
    "duration_minutes": 30
  }'
```

### 3. Handle Token Expiration
```bash
# Initial request
curl -s -X GET http://localhost:8000/api/v1/profiles/ \
  -H "Authorization: Bearer $ACCESS" \
  # Returns 401 when token expired

# Refresh and retry
NEW_ACCESS=$(curl -s -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH\"}" | jq -r '.access')

# Retry with new token
curl -s -X GET http://localhost:8000/api/v1/profiles/ \
  -H "Authorization: Bearer $NEW_ACCESS"
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid token",
  "code": "token_not_valid"
}
```
**Action:** Refresh token using refresh endpoint or login again.

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action"
}
```
**Action:** Verify you have access to this resource.

### 429 Too Many Requests
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```
**Action:** Wait before making more requests.

### 400 Bad Request (Validation Error)
```json
{
  "password": ["This field may not be blank."],
  "email": ["Enter a valid email address."]
}
```
**Action:** Fix validation errors and retry.

---

## Token Structure

### Access Token Payload
```json
{
  "token_type": "access",
  "exp": 1795574140,
  "iat": 1795570541,
  "jti": "4c99140...",
  "user_id": "9",
  "username": "jwtuser",
  "email": "jwt@example.com"
}
```

### Refresh Token Payload
```json
{
  "token_type": "refresh",
  "exp": 1796175340,
  "iat": 1795570540,
  "jti": "73c94571...",
  "user_id": "9",
  "username": "jwtuser",
  "email": "jwt@example.com"
}
```

---

## Best Practices

### For Frontend
1. ✅ Store tokens in secure storage (not localStorage for sensitive apps)
2. ✅ Always include `Authorization: Bearer <token>` header
3. ✅ Implement token refresh logic (refresh before 401)
4. ✅ Clear tokens on logout
5. ❌ Never expose refresh tokens in network logs

### For Mobile Apps
1. ✅ Use secure storage (Keychain, Keystore)
2. ✅ Implement automatic token refresh
3. ✅ Handle offline scenarios gracefully
4. ✅ Clear tokens on user logout/uninstall

### For Backend
1. ✅ Rotate tokens on refresh
2. ✅ Blacklist old tokens (automatic)
3. ✅ Use HTTPS only in production
4. ✅ Validate token claims server-side
5. ✅ Implement rate limiting

---

## Future Enhancements

- [ ] Email-based password reset with token links
- [ ] Two-factor authentication (2FA)
- [ ] Social login (Google, Apple, Spotify OAuth)
- [ ] API key authentication for server-to-server
- [ ] Session management (logout all devices)
- [ ] User account deletion/GDPR compliance
- [ ] Login activity logging and alerts

---

## Migration from Token Auth

If upgrading from simple Token authentication:

1. **User can keep existing Token auth working** (still supported)
2. **Recommend JWT for new clients** (access + refresh model)
3. **No data migration needed** (database schemas unchanged)
4. **Gradual migration path** (old and new auth coexist)

```bash
# Old Token Auth (still works)
Authorization: Token abc123def456...

# New JWT Auth (recommended)
Authorization: Bearer eyJhbGciOiJIUzI1NiI...
```
