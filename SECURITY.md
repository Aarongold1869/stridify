# Stridify Security Best Practices

## Spotify Token Security

### ✅ What We Do (Secure)

1. **No Disk Caching**
   ```python
   # In music/services/spotify_service.py
   sp_oauth = SpotifyOAuth(
       client_id=...,
       client_secret=...,
       redirect_uri=...,
       cache_path=False  # ← PREVENTS .cache file creation
   )
   ```

2. **Database Storage**
   - Tokens stored in `SpotifyAuth` model
   - Never written to disk
   - Encrypted in production database

3. **Token Flow Security**
   ```
   Spotify OAuth → Python Memory → Database
   (Tokens never touch disk)
   ```

### ❌ What We DON'T Do (Insecure)

- ❌ Cache tokens to `.cache` file
- ❌ Write tokens to environment files
- ❌ Hardcode tokens in settings
- ❌ Log tokens to files
- ❌ Commit credentials to Git

---

## Environment Variables

### ✅ Secure Pattern
```bash
# .env (not in Git, in .gitignore)
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret

# settings.py
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
```

### ❌ Insecure Pattern
```python
# NEVER do this:
SPOTIFY_CLIENT_ID = '27167a1165...'  # Hardcoded in code
SPOTIFY_CLIENT_SECRET = 'f8743eeab7...'  # Visible in Git history
```

---

## .gitignore Coverage

Protected files:
```
.env              # Environment variables
.env.local        # Local overrides
.cache            # Spotipy disk cache
.cache/           # Cache directory
credentials.json  # API credentials
secrets.json      # Secret keys
__pycache__/      # Python bytecode
*.pyc             # Compiled Python
db.sqlite3        # Local database
*.log             # Application logs
```

---

## Token Lifecycle

### On First OAuth
```
1. User clicks "Connect Spotify"
2. Redirected to Spotify login
3. User authorizes app
4. Spotify returns authorization code (safe)
5. Code → SpotifyOAuth.get_access_token() (in memory)
6. Access token + refresh token extracted
7. Tokens stored in SpotifyAuth model (database)
8. .cache file is NEVER created (cache_path=False)
9. Access token returned to frontend via API
```

### On Token Refresh
```
1. Access token expires
2. Refresh token used to get new token (from database)
3. New tokens stored in database
4. No disk files created
```

### On Token Expiration
```
1. Database check: is_expired property
2. If expired: refresh_access_token() called
3. New tokens fetched and stored
4. All in-memory, never to disk
```

---

## Security Checklist

- ✅ `cache_path=False` in SpotifyOAuth
- ✅ Tokens stored in database, not disk
- ✅ `.cache` ignored in .gitignore
- ✅ `.env` file ignored in .gitignore
- ✅ No hardcoded secrets in code
- ✅ Environment variables for config
- ✅ Access tokens in Bearer headers only
- ✅ Refresh tokens never sent to frontend
- ✅ All comments document security measures

---

## Testing Security

```bash
# After connecting to Spotify:
# 1. No .cache file should exist
ls -la | grep cache  # Should show nothing

# 2. Check git won't track it
git status | grep cache  # Should show nothing

# 3. Verify token in database
python manage.py shell
>>> from runners.models import SpotifyAuth
>>> auth = SpotifyAuth.objects.first()
>>> print(auth.access_token)  # Shows token in DB ✅
```

---

## Production Considerations

For production deployment:

1. **Database Encryption**
   ```python
   # Use Django-encrypted-model-fields or similar
   access_token = EncryptedTextField()
   refresh_token = EncryptedTextField()
   ```

2. **Secrets Management**
   ```bash
   # Use environment secrets (AWS Secrets Manager, etc.)
   export SPOTIFY_CLIENT_SECRET=$(aws secretsmanager get-secret-value ...)
   ```

3. **Token Rotation**
   ```python
   # Implement auto-refresh before expiry
   if spotify_auth.is_expired:
       spotify_auth.refresh_access_token(sp_oauth)
   ```

4. **Audit Logging**
   ```python
   # Log token usage (not values)
   logger.info(f"User {user.id} accessed Spotify API")
   ```

5. **HTTPS Only**
   - All Spotify API calls via HTTPS
   - Bearer tokens in Authorization headers only
   - Never in URLs or query parameters

---

## References

- [Spotipy Documentation](https://spotipy.readthedocs.io/)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [Django Secrets Management](https://docs.djangoproject.com/en/5.2/topics/settings/#security-considerations)
