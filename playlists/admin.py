from django.contrib import admin
from playlists.models import Playlist, PlaylistTrack


class PlaylistTrackInline(admin.TabularInline):
    model = PlaylistTrack
    extra = 0
    fields = ("position", "track", "sync_ratio", "match_score")
    readonly_fields = ("match_score",)
    ordering = ("position",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("track")


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "target_pace_display",
        "target_cadence_display",
        "duration_minutes",
        "track_count",
        "algorithm_version",
        "created_at",
    )
    list_filter = ("algorithm_version", "created_at", "user")
    search_fields = ("name", "user__username")
    readonly_fields = ("created_at", "target_cadence_spm", "target_bpm")
    inlines = [PlaylistTrackInline]
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Playlist Information",
            {
                "fields": ("name", "user"),
            },
        ),
        (
            "Running Parameters",
            {
                "fields": ("target_pace_seconds", "target_cadence_spm", "target_bpm"),
            },
        ),
        (
            "Configuration",
            {
                "fields": ("duration_minutes", "algorithm_version"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def target_pace_display(self, obj):
        minutes = obj.target_pace_seconds // 60
        seconds = obj.target_pace_seconds % 60
        return f"{minutes}:{seconds:02d}/mile"
    target_pace_display.short_description = "Target Pace"

    def target_cadence_display(self, obj):
        return f"{obj.target_cadence_spm} SPM"
    target_cadence_display.short_description = "Target Cadence"

    def track_count(self, obj):
        return obj.playlist_tracks.count()
    track_count.short_description = "Tracks"


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = (
        "playlist",
        "position",
        "track",
        "sync_ratio",
        "match_score",
        "bpm_info",
    )
    list_filter = ("sync_ratio", "playlist__user", "playlist__created_at")
    search_fields = ("playlist__name", "track__title", "track__artist")
    readonly_fields = ("match_score",)
    ordering = ("playlist", "position")

    fieldsets = (
        (
            "Playlist Track",
            {
                "fields": ("playlist", "track", "position"),
            },
        ),
        (
            "Recommendation Details",
            {
                "fields": ("sync_ratio", "match_score"),
            },
        ),
    )

    def bpm_info(self, obj):
        track = obj.track
        return f"{track.bpm} BPM ({obj.sync_ratio})"
    bpm_info.short_description = "BPM & Sync Ratio"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("playlist", "track")
