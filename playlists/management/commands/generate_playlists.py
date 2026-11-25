from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from playlists.services.generator import PlaylistGenerationRequest, generate_playlist
from music.choices import SyncRatio


class Command(BaseCommand):
    help = "Generate sample playlists for all test runners"

    def handle(self, *args, **options):
        self.stdout.write("Generating playlists for test runners...\n")

        runners = User.objects.filter(username__startswith="runner_").order_by("username")

        playlist_configs = [
            {
                "name_template": "{} - Easy 30min Run",
                "duration": 30,
                "energy": Decimal("0.60"),
                "description": "Low-energy warm-up playlist",
            },
            {
                "name_template": "{} - Tempo 60min Run",
                "duration": 60,
                "energy": Decimal("0.80"),
                "description": "High-energy workout playlist",
            },
            {
                "name_template": "{} - Mixed 45min Run",
                "duration": 45,
                "energy": None,
                "description": "Varied energy playlist",
            },
        ]

        total_playlists = 0
        total_tracks = 0

        for runner in runners:
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"Generating playlists for: {runner.first_name} ({runner.username})")
            self.stdout.write(f"{'=' * 70}")

            profile = runner.runner_profile
            self.stdout.write(f"Target pace: {profile.target_pace_seconds // 60}:{profile.target_pace_seconds % 60:02d}/mile")
            if profile.measured_cadence_spm:
                self.stdout.write(f"Measured cadence: {profile.measured_cadence_spm} SPM")
            else:
                self.stdout.write(f"Height: {int(profile.height_inches // 12)}'{int(profile.height_inches % 12)}\"")
                self.stdout.write("(Will use height-based cadence estimation)")

            for config in playlist_configs:
                self.stdout.write(f"\n  Creating: {config['name_template'].format(runner.first_name)}")
                self.stdout.write(f"  Duration: {config['duration']} minutes | Energy: {config['energy'] or 'varied'}")

                try:
                    request = PlaylistGenerationRequest(
                        user=runner,
                        playlist_name=config["name_template"].format(runner.first_name),
                        duration_minutes=config["duration"],
                        target_energy=config["energy"],
                    )

                    result = generate_playlist(request)

                    self.stdout.write(f"  [OK] Playlist created successfully")
                    self.stdout.write(f"      Tracks: {result.tracks_selected}")
                    self.stdout.write(f"      Duration: {result.total_duration_seconds / 60:.1f} minutes")
                    self.stdout.write(f"      Cadence: {result.cadence_spm} SPM")
                    self.stdout.write(f"      Target BPM: {result.playlist.target_bpm}")

                    # Show sync ratio distribution
                    dist_parts = []
                    for ratio_label, count in sorted(result.sync_ratio_distribution.items()):
                        dist_parts.append(f"{ratio_label}: {count}")
                    self.stdout.write(f"      Sync ratios: {', '.join(dist_parts)}")

                    # Show first few tracks
                    self.stdout.write(f"      First tracks:")
                    for track_entry in result.playlist.playlist_tracks.all()[:3]:
                        track = track_entry.track
                        self.stdout.write(
                            f"        - {track.artist} - {track.title} ({track.bpm} BPM, {track_entry.sync_ratio})"
                        )
                    if result.tracks_selected > 3:
                        self.stdout.write(f"        ... and {result.tracks_selected - 3} more")

                    total_playlists += 1
                    total_tracks += result.tracks_selected

                except Exception as e:
                    self.stdout.write(f"  [ERROR] Failed to create playlist: {str(e)}")

        # Print summary
        self.stdout.write(f"\n\n{'=' * 70}")
        self.stdout.write("[OK] PLAYLIST GENERATION COMPLETE")
        self.stdout.write(f"{'=' * 70}")
        self.stdout.write(f"Playlists created: {total_playlists}")
        self.stdout.write(f"Total tracks: {total_tracks}")
        self.stdout.write(f"\nPlaylists are ready to view in the admin interface!")
        self.stdout.write(f"Visit: /admin/playlists/playlist/")
