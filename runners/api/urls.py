from django.urls import path, include
from rest_framework.routers import DefaultRouter
from runners.api.views import RegisterView, RunnerProfileViewSet, UserGenrePreferenceViewSet

router = DefaultRouter()
router.register(r'auth/register', RegisterView, basename='auth-register')
router.register(r'profiles', RunnerProfileViewSet, basename='runner-profile')
router.register(r'genre-preferences', UserGenrePreferenceViewSet, basename='genre-preference')

urlpatterns = [
    path('', include(router.urls)),
]
