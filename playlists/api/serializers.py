from rest_framework import serializers
from playlists.models import Playlist, PlaylistTrack
from music.api.serializers import TrackSerializer


class PlaylistTrackSerializer(serializers.ModelSerializer):
    track = TrackSerializer(read_only=True)
    track_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = PlaylistTrack
        fields = ('id', 'track', 'track_id', 'position', 'sync_ratio', 'match_score')
        read_only_fields = ('id', 'position', 'match_score')


class PlaylistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    playlist_tracks = PlaylistTrackSerializer(many=True, read_only=True)
    track_count = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    pace_display = serializers.SerializerMethodField()
    cadence_display = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = (
            'id', 'name', 'user', 'target_pace_seconds', 'pace_display',
            'target_cadence_spm', 'cadence_display', 'target_bpm',
            'duration_minutes', 'track_count', 'algorithm_version',
            'playlist_tracks', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

    def get_track_count(self, obj):
        return obj.playlist_tracks.count()

    def get_duration_minutes(self, obj):
        total_seconds = sum(pt.track.duration_seconds for pt in obj.playlist_tracks.all())
        return round(total_seconds / 60, 1)

    def get_pace_display(self, obj):
        if obj.target_pace_seconds:
            minutes = obj.target_pace_seconds // 60
            seconds = obj.target_pace_seconds % 60
            return f"{minutes}:{seconds:02d}/mile"
        return None

    def get_cadence_display(self, obj):
        if obj.target_cadence_spm:
            return f"{obj.target_cadence_spm} SPM"
        return None


class PlaylistCreateSerializer(serializers.Serializer):
    playlist_name = serializers.CharField(max_length=255)
    duration_minutes = serializers.IntegerField(min_value=15, max_value=180)
    target_energy = serializers.DecimalField(
        max_digits=3, decimal_places=2, required=False, allow_null=True
    )

    def validate_duration_minutes(self, value):
        if value not in [15, 30, 45, 60, 75, 90, 120, 180]:
            raise serializers.ValidationError(
                "Duration should be in common intervals (15, 30, 45, 60, 75, 90, 120, 180)"
            )
        return value
