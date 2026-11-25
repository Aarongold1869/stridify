# Stridify Architecture: Web vs API Separation

## Project Structure

```
Stridify/
├── runners/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── serializers.py      # DRF serializers (REST endpoints)
│   │   ├── views.py            # DRF viewsets (REST endpoints)
│   │   └── urls.py             # API routing
│   ├── views.py                # Django web views (templates)
│   ├── serializers.py          # (placeholder - redirects to api/)
│   ├── models.py
│   ├── admin.py
│   └── ...
│
├── music/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── views.py                # Django web views
│   ├── serializers.py          # (placeholder)
│   ├── models.py
│   ├── admin.py
│   └── ...
│
├── playlists/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── views.py                # Django web views
│   ├── serializers.py          # (placeholder)
│   ├── models.py
│   ├── admin.py
│   └── ...
│
├── api/
│   ├── __init__.py
│   └── urls.py                 # Main API router (includes all app apis)
│
└── Stridify/
    ├── urls.py                 # Main URL config
    └── settings.py
```

## URL Structure

### API Routes
```
/api/v1/
├── auth/register/register/     (POST) - User registration
├── profiles/                   (GET/POST/PATCH) - Runner profiles
├── genre-preferences/          (GET/POST/DELETE) - Genre preferences
├── genres/                     (GET) - Browse genres
├── tracks/                     (GET) - Search tracks
└── playlists/                  (GET/POST)
    ├── generate/               (POST) - Generate playlist
    └── {id}/sync_ratio_stats/  (GET) - Playlist stats
```

### Web Routes (Future)
```
/                              - Home page
/dashboard/                    - User dashboard
/profile/                      - Profile management
/playlists/                    - Browse playlists
/playlists/{id}/               - Playlist detail
/music/                        - Music discovery
```

## Implementation Pattern

### API Structure (Mobile/REST Clients)
```python
# runners/api/views.py
from rest_framework import viewsets

class RunnerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RunnerProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    # ... REST logic
```

```python
# runners/api/serializers.py
from rest_framework import serializers

class RunnerProfileSerializer(serializers.ModelSerializer):
    # ... serializer fields
```

```python
# runners/api/urls.py
router = DefaultRouter()
router.register(r'profiles', RunnerProfileViewSet, basename='runner-profile')
urlpatterns = [path('', include(router.urls))]
```

### Web Structure (Browser/Template Clients)
```python
# runners/views.py (future)
from django.views.generic import TemplateView

class ProfileDetailView(TemplateView):
    template_name = 'runners/profile_detail.html'
    # ... web view logic
```

```html
<!-- templates/runners/profile_detail.html -->
{% extends 'base.html' %}
{% block content %}
  <!-- Template content -->
{% endblock %}
```

## Separation Benefits

| Concern | Web Views | API Views |
|---------|-----------|-----------|
| **Client Type** | Browser (HTML/Template) | Mobile/Frontend (JSON) |
| **Response Format** | HTML pages | JSON |
| **Authentication** | Sessions/Cookies | Token-based |
| **Template Logic** | Business logic in template context | Serializer logic |
| **Error Handling** | HTTP redirects/status pages | JSON error responses |
| **Response Size** | Minimal (HTML only) | Complete data (JSON) |
| **Caching** | Page-level (Cache headers) | API-level (Redis/CDN) |

## Routing Strategy

**Main URLs** (`Stridify/urls.py`):
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),        # All REST APIs
    path('', include('web.urls')),                # All web routes (future)
]
```

**API URLs** (`api/urls.py`):
```python
urlpatterns = [
    path('', include('runners.api.urls')),
    path('', include('music.api.urls')),
    path('', include('playlists.api.urls')),
]
```

**App-Specific API** (`runners/api/urls.py`):
```python
router = DefaultRouter()
router.register(r'profiles', RunnerProfileViewSet)
router.register(r'auth/register', RegisterView)
router.register(r'genre-preferences', UserGenrePreferenceViewSet)

urlpatterns = [path('', include(router.urls))]
```

## Migration Path

### Phase 1 (Current) ✅
- API viewsets in `app/api/views.py`
- API serializers in `app/api/serializers.py`
- Web placeholder files in `app/views.py`
- All tests passing (99/99)

### Phase 2 (Next)
- Create `web/urls.py` for web routes
- Create `app/web_views.py` or `app/views.py` with Django CBVs
- Create `templates/` directories with HTML templates
- Build form handling for web interface

### Phase 3 (Future)
- Integrate with Spotify/Apple Music
- Add real-time features (WebSockets)
- Performance optimizations (caching, CDN)

## Testing Strategy

- **API Tests**: Test serializers, viewsets, authentication
- **Web Tests**: Test template rendering, form submission
- **Integration Tests**: API + Database interactions
- **End-to-End Tests**: Full workflows (register → generate playlist)

## Development Workflow

### For API (Mobile/Frontend Dev)
```bash
# Start server
python manage.py runserver

# Test API endpoints
curl http://localhost:8000/api/v1/playlists/

# Run API-focused tests
python manage.py test runners.tests.api_tests
```

### For Web (Backend/Template Dev)
```bash
# Start server
python manage.py runserver

# Test web routes
http://localhost:8000/dashboard/

# Run web-focused tests (future)
python manage.py test runners.tests.web_tests
```

## Notes

- Root level `serializers.py` and `views.py` are now placeholders (redirecting to API)
- All API functionality is preserved and tested
- Structure allows independent development of web UI without affecting API
- Both web and API can share the same models, services, and business logic
- Admin interface remains at `/admin/` and uses models directly
