from django.contrib import admin
from runners.models import RunnerProfile, UserGenrePreference


@admin.register(RunnerProfile)
class RunnerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "height_display",
        "leg_length_display",
        "target_pace_display",
        "measured_cadence_display",
        "created_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "User",
            {
                "fields": ("user",),
            },
        ),
        (
            "Physical Dimensions",
            {
                "fields": ("height_inches", "leg_length_inches"),
            },
        ),
        (
            "Running Profile",
            {
                "fields": ("target_pace_seconds", "measured_cadence_spm", "step_length_inches", "cadence_observed_pace_seconds"),
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

    def height_display(self, obj):
        if obj.height_inches:
            feet = int(obj.height_inches // 12)
            inches = int(obj.height_inches % 12)
            return f"{feet}'{inches}\" ({obj.height_inches}\")"
        return "—"
    height_display.short_description = "Height"

    def leg_length_display(self, obj):
        if obj.leg_length_inches:
            return f"{obj.leg_length_inches}\""
        return "—"
    leg_length_display.short_description = "Leg Length"

    def target_pace_display(self, obj):
        if obj.target_pace_seconds:
            minutes = obj.target_pace_seconds // 60
            seconds = obj.target_pace_seconds % 60
            return f"{minutes}:{seconds:02d}/mile"
        return "—"
    target_pace_display.short_description = "Target Pace"

    def measured_cadence_display(self, obj):
        if obj.measured_cadence_spm:
            return f"{obj.measured_cadence_spm} SPM"
        return "—"
    measured_cadence_display.short_description = "Measured Cadence"


@admin.register(UserGenrePreference)
class UserGenrePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "genre", "preference_weight", "preference_bar")
    list_filter = ("genre", "preference_weight")
    search_fields = ("user__username", "genre__name")
    ordering = ("-preference_weight", "user__username")

    fieldsets = (
        (
            "Preference",
            {
                "fields": ("user", "genre", "preference_weight"),
            },
        ),
    )

    def preference_bar(self, obj):
        # Visual representation of preference weight (0-5 scale)
        filled = int(obj.preference_weight)
        empty = 5 - filled
        return "█" * filled + "░" * empty
    preference_bar.short_description = "Weight"
