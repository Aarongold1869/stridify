from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from collections import Counter
from playlists.models import Playlist
from playlists.api.serializers import PlaylistSerializer, PlaylistCreateSerializer
from playlists.services.generator import PlaylistGenerationRequest, generate_playlist


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
