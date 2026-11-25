from rest_framework import viewsets, permissions
from django.db.models import Q
from music.models import Genre, Track
from music.api.serializers import GenreSerializer, TrackSerializer, TrackListSerializer


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (permissions.AllowAny,)


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrackSerializer
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        if self.action == 'list':
            return TrackListSerializer
        return TrackSerializer

    def get_queryset(self):
        queryset = Track.objects.all()

        bpm_min = self.request.query_params.get('bpm_min')
        if bpm_min:
            queryset = queryset.filter(bpm__gte=int(bpm_min))

        bpm_max = self.request.query_params.get('bpm_max')
        if bpm_max:
            queryset = queryset.filter(bpm__lte=int(bpm_max))

        energy_min = self.request.query_params.get('energy_min')
        if energy_min:
            queryset = queryset.filter(energy__gte=float(energy_min))

        energy_max = self.request.query_params.get('energy_max')
        if energy_max:
            queryset = queryset.filter(energy__lte=float(energy_max))

        genres = self.request.query_params.getlist('genres')
        if genres:
            queryset = queryset.filter(genres__id__in=genres).distinct()

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(artist__icontains=search) |
                Q(album__icontains=search)
            )

        return queryset.distinct()
