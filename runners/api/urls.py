from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from runners.api.views import (
    LoginView, RegisterView, UserViewSet, RunnerProfileViewSet,
    UserGenrePreferenceViewSet, SpotifyAuthViewSet
)

router = DefaultRouter()
router.register(r'auth/register', RegisterView, basename='auth-register')
router.register(r'auth/spotify', SpotifyAuthViewSet, basename='spotify-auth')
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', RunnerProfileViewSet, basename='runner-profile')
router.register(r'genre-preferences', UserGenrePreferenceViewSet, basename='genre-preference')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

