from django.core.management.base import BaseCommand
from django.conf import settings
from music.models import Track, TrackProviderMapping
from music.services.spotify_service import SpotifyService


class Command(BaseCommand):
    help = "Fetch and update audio features from Spotify for tracks in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of tracks to process'
        )
        parser.add_argument(
            '--unmapped-only',
            action='store_true',
            help='Only process tracks without Spotify mappings'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        unmapped_only = options['unmapped_only']

        # Initialize Spotify service
        service = SpotifyService()
        self.stdout.write("Initializing Spotify service...")

        # Get tracks to process
        if unmapped_only:
            # Only tracks without Spotify mappings
            tracks_without_mapping = Track.objects.filter(
                provider_mappings__provider='spotify'
            ).exclude(id__in=TrackProviderMapping.objects.filter(
                provider='spotify'
            ).values('track_id'))
            tracks = tracks_without_mapping[:limit]
            self.stdout.write(f"Found {len(tracks)} tracks without Spotify mapping")
        else:
            tracks = Track.objects.all()[:limit]
            self.stdout.write(f"Processing {len(tracks)} tracks...")

        updated_count = 0
        created_count = 0
        error_count = 0

        for track in tracks:
            self.stdout.write(f"\nProcessing: {track.artist} - {track.title}")

            # Search for track on Spotify
            query = f"{track.artist} {track.title}"
            spotify_track = service.search_track(query)

            if not spotify_track:
                self.stdout.write(f"  [ERROR] Not found on Spotify")
                error_count += 1
                continue

            # Sync to database
            synced_track, created = service.sync_track_to_db(spotify_track)

            if created:
                self.stdout.write(f"  [CREATED] BPM: {synced_track.bpm}, Energy: {synced_track.energy}")
                created_count += 1
            else:
                self.stdout.write(f"  [UPDATED] BPM: {synced_track.bpm}, Energy: {synced_track.energy}")
                updated_count += 1

        # Print summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write("[OK] SPOTIFY SYNC COMPLETE")
        self.stdout.write(f"{'=' * 70}")
        self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Errors: {error_count}")
        self.stdout.write(f"Total: {updated_count + created_count}")
