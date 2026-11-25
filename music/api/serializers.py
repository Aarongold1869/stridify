from rest_framework import serializers
from music.models import Genre, Track


class GenreSerializer(serializers.ModelSerializer):
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ('id', 'name', 'slug', 'track_count')

    def get_track_count(self, obj):
        return obj.tracks.count()


class TrackSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = (
            'id', 'title', 'artist', 'album', 'bpm', 'energy',
            'duration_seconds', 'duration_minutes', 'genres', 'created_at'
        )
        read_only_fields = ('created_at',)

    def get_duration_minutes(self, obj):
        return round(obj.duration_seconds / 60, 1)


class TrackListSerializer(serializers.ModelSerializer):
    genre_names = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = ('id', 'title', 'artist', 'bpm', 'energy', 'genre_names')

    def get_genre_names(self, obj):
        return [g.name for g in obj.genres.all()]
