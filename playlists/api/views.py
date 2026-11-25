from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from collections import Counter
from playlists.models import Playlist
from playlists.api.serializers import PlaylistSerializer, PlaylistCreateSerializer
from playlists.services.generator import PlaylistGenerationRequest, generate_playlist
from music.services.spotify_service import SpotifyService
from runners.models import SpotifyAuth


class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Playlist.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        serializer = PlaylistCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            runner_profile = request.user.runner_profile
        except Exception:
            return Response(
                {'error': 'Runner profile not found. Please set up your profile first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            gen_request = PlaylistGenerationRequest(
                user=request.user,
                playlist_name=serializer.validated_data['playlist_name'],
                duration_minutes=serializer.validated_data['duration_minutes'],
                target_energy=serializer.validated_data.get('target_energy'),
            )

            result = generate_playlist(gen_request)

            return Response(
                PlaylistSerializer(result.playlist).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def sync_ratio_stats(self, request, pk=None):
        playlist = self.get_object()
        ratios = Counter(
            pt.sync_ratio for pt in playlist.playlist_tracks.all()
        )

        return Response({
            'playlist': playlist.name,
            'sync_ratios': dict(ratios),
            'total_tracks': playlist.playlist_tracks.count()
        })

    @action(detail=True, methods=['post'])
    def export_spotify(self, request, pk=None):
        """Export playlist to Spotify"""
        playlist = self.get_object()

        try:
            spotify_auth = request.user.spotify_auth
        except SpotifyAuth.DoesNotExist:
            return Response(
                {'error': 'Not connected to Spotify. Please authenticate first.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            if spotify_auth.is_expired:
                spotify_auth.refresh_access_token(SpotifyService().get_oauth_handler())

            # Get track URIs
            track_uris = []
            for entry in playlist.playlist_tracks.all():
                mapping = entry.track.provider_mappings.filter(provider='spotify').first()
                if mapping:
                    track_uris.append(f"spotify:track:{mapping.provider_track_id}")

            if not track_uris:
                return Response(
                    {'error': 'No Spotify tracks found in playlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create playlist on Spotify
            service = SpotifyService(spotify_auth.access_token)
            result = service.create_playlist(
                spotify_auth.access_token,
                playlist.name,
                track_uris,
                is_public=False
            )

            if not result:
                return Response(
                    {'error': 'Failed to create Spotify playlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'message': 'Playlist exported to Spotify',
                'spotify': result
            })

        except Exception as e:
            return Response(
                {'error': f'Export failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
