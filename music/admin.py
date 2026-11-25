from django.contrib import admin
from music.models import Genre, Track, TrackProviderMapping


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "track_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    def track_count(self, obj):
        return obj.tracks.count()
    track_count.short_description = "Tracks"


class TrackProviderMappingInline(admin.TabularInline):
    model = TrackProviderMapping
    extra = 1
    fields = ("provider", "provider_track_id", "provider_url")


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "artist",
        "bpm",
        "energy",
        "duration_minutes",
        "genre_list",
        "created_at",
    )
    list_filter = ("bpm", "energy", "created_at", "genres")
    search_fields = ("title", "artist", "album", "isrc")
    readonly_fields = ("created_at", "updated_at", "isrc")
    filter_horizontal = ("genres",)
    inlines = [TrackProviderMappingInline]
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Track Information",
            {
                "fields": ("title", "artist", "album", "isrc"),
            },
        ),
        (
            "Audio Properties",
            {
                "fields": ("duration_seconds", "bpm", "energy"),
            },
        ),
        (
            "Classification",
            {
                "fields": ("genres",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def duration_minutes(self, obj):
        minutes = obj.duration_seconds / 60
        return f"{minutes:.1f} min"
    duration_minutes.short_description = "Duration"

    def genre_list(self, obj):
        return ", ".join([g.name for g in obj.genres.all()]) or "—"
    genre_list.short_description = "Genres"


@admin.register(TrackProviderMapping)
class TrackProviderMappingAdmin(admin.ModelAdmin):
    list_display = ("track", "provider", "provider_track_id", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("track__title", "track__artist", "provider_track_id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Mapping",
            {
                "fields": ("track", "provider", "provider_track_id", "provider_url"),
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
