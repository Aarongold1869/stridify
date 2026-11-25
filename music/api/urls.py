from django.urls import path, include
from rest_framework.routers import DefaultRouter
from music.api.views import GenreViewSet, TrackViewSet

router = DefaultRouter()
router.register(r'genres', GenreViewSet, basename='genre')
router.register(r'tracks', TrackViewSet, basename='track')

urlpatterns = [
    path('', include(router.urls)),
]
