from django.urls import path, include

urlpatterns = [
    path('', include('runners.api.urls')),
    path('', include('music.api.urls')),
    path('', include('playlists.api.urls')),
]

