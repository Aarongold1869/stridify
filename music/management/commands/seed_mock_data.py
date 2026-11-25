from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from music.models import Genre, Track
from runners.models import RunnerProfile, UserGenrePreference


class Command(BaseCommand):
    help = "Seed the database with mock data for testing and demonstration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            User.objects.filter(username__startswith="runner_").delete()
            Track.objects.all().delete()
            Genre.objects.all().delete()

        self.stdout.write("Creating genres...")
        genres_data = [
            ("Rock", "rock"),
            ("Alternative", "alternative"),
            ("Electronic", "electronic"),
            ("Hip-hop", "hip-hop"),
            ("Pop", "pop"),
            ("Indie", "indie"),
            ("Funk", "funk"),
            ("Dance", "dance"),
            ("Reggae", "reggae"),
            ("Jazz", "jazz"),
        ]

        genres = {}
        for name, slug in genres_data:
            genre, created = Genre.objects.get_or_create(
                name=name,
                defaults={"slug": slug},
            )
            genres[name] = genre

        self.stdout.write(f"[OK] Created {len(genres)} genres")

        # Track data: (title, artist, bpm, energy, genres, duration_seconds)
        self.stdout.write("Creating tracks...")
        tracks_data = [
            # Rock tracks (high BPM, varied energy)
            ("Bleed It Out", "Linkin Park", 170, Decimal("0.95"), ["Rock"], 180),
            ("In the End", "Linkin Park", 160, Decimal("0.85"), ["Rock"], 216),
            ("Numb", "Linkin Park", 158, Decimal("0.82"), ["Rock"], 192),
            ("Break My Soul", "Beyoncé", 164, Decimal("0.88"), ["Electronic", "Pop"], 180),
            ("Levitating", "Dua Lipa", 162, Decimal("0.85"), ["Pop", "Dance"], 203),
            ("Uptown Funk", "Mark Ronson ft. Bruno Mars", 160, Decimal("0.80"), ["Funk", "Pop"], 269),
            ("Blinding Lights", "The Weeknd", 171, Decimal("0.73"), ["Electronic", "Pop"], 200),
            ("Don't Start Now", "Dua Lipa", 160, Decimal("0.84"), ["Funk", "Dance"], 183),
            ("Good as Hell", "Lizzo", 165, Decimal("0.90"), ["Pop"], 161),
            ("Walking on Sunshine", "Katrina & The Waves", 158, Decimal("0.88"), ["Pop"], 212),
            # Alternative tracks (160-180 BPM)
            ("Wonderwall", "Oasis", 162, Decimal("0.72"), ["Alternative", "Rock"], 258),
            ("Creep", "Radiohead", 92, Decimal("0.60"), ["Alternative"], 238),
            ("Fake Plastic Trees", "Radiohead", 102, Decimal("0.58"), ["Alternative"], 307),
            ("Paranoid Android", "Radiohead", 132, Decimal("0.75"), ["Alternative"], 358),
            ("The Middle", "Jimmy Eat World", 164, Decimal("0.78"), ["Alternative"], 177),
            # Indie/Upbeat tracks
            ("Take Me Out", "Franz Ferdinand", 169, Decimal("0.84"), ["Indie", "Rock"], 254),
            ("Sex on Fire", "Kings of Leon", 165, Decimal("0.82"), ["Indie", "Rock"], 230),
            ("Mr. Brightside", "The Killers", 158, Decimal("0.76"), ["Indie", "Rock"], 223),
            ("Somebody Told Me", "The Killers", 174, Decimal("0.80"), ["Indie", "Rock"], 203),
            ("Nude", "Radiohead", 158, Decimal("0.69"), ["Alternative", "Indie"], 288),
            # Electronic/Dance tracks
            ("Get Lucky", "Daft Punk ft. Pharrell", 160, Decimal("0.84"), ["Electronic", "Dance"], 369),
            ("One More Time", "Daft Punk", 160, Decimal("0.88"), ["Electronic", "Dance"], 325),
            ("Around the World", "Daft Punk", 160, Decimal("0.75"), ["Electronic"], 384),
            ("Titanium", "David Guetta ft. Sia", 128, Decimal("0.82"), ["Electronic", "Pop"], 244),
            ("Animals", "Martin Garrix", 128, Decimal("0.80"), ["Electronic", "Dance"], 243),
            # Hip-hop tracks (varied BPM)
            ("Lose Yourself", "Eminem", 171, Decimal("0.90"), ["Hip-hop"], 326),
            ("In Da Club", "50 Cent", 180, Decimal("0.92"), ["Hip-hop"], 236),
            ("Mo Money Mo Problems", "Biggie", 164, Decimal("0.85"), ["Hip-hop"], 282),
            ("Nuthin' but a 'G' Thang", "Dr. Dre", 94, Decimal("0.68"), ["Hip-hop"], 320),
            ("Still D.R.E.", "Dr. Dre", 110, Decimal("0.72"), ["Hip-hop"], 299),
            # Funk/Upbeat
            ("Superstition", "Stevie Wonder", 108, Decimal("0.75"), ["Funk"], 304),
            ("Sir Duke", "Stevie Wonder", 160, Decimal("0.88"), ["Funk"], 296),
            ("Le Freak", "Chic", 100, Decimal("0.78"), ["Funk"], 282),
            # Reggae/Slow
            ("No Woman No Cry", "Bob Marley", 76, Decimal("0.60"), ["Reggae"], 268),
            ("Is This Love", "Bob Marley", 76, Decimal("0.65"), ["Reggae"], 282),
            ("Redemption Song", "Bob Marley", 98, Decimal("0.55"), ["Reggae"], 229),
            # Jazz/Mellow
            ("Take Five", "Dave Brubeck", 85, Decimal("0.50"), ["Jazz"], 342),
            ("Kind of Blue", "Miles Davis", 72, Decimal("0.48"), ["Jazz"], 540),
            ("Autumn Leaves", "Bill Evans", 90, Decimal("0.52"), ["Jazz"], 298),
            # More running-friendly tracks
            ("The Night They Drove Old Dixie Down", "The Band", 160, Decimal("0.70"), ["Rock"], 338),
            ("Born to Run", "Bruce Springsteen", 162, Decimal("0.86"), ["Rock"], 330),
            ("Born to Be Wild", "Steppenwolf", 162, Decimal("0.84"), ["Rock"], 346),
        ]

        created_count = 0
        for title, artist, bpm, energy, genre_names, duration in tracks_data:
            track, created = Track.objects.get_or_create(
                title=title,
                artist=artist,
                defaults={
                    "bpm": Decimal(str(bpm)),
                    "energy": energy,
                    "duration_seconds": duration,
                    "album": "Mock Album",
                },
            )
            if created:
                created_count += 1
                for genre_name in genre_names:
                    if genre_name in genres:
                        track.genres.add(genres[genre_name])

        self.stdout.write(f"[OK] Created {created_count} tracks")

        # Create test users and profiles
        self.stdout.write("Creating test users and runner profiles...")
        users_data = [
            {
                "username": "runner_alice",
                "email": "alice@example.com",
                "first_name": "Alice",
                "height_inches": Decimal("68"),
                "leg_length_inches": Decimal("32"),
                "measured_cadence_spm": Decimal("160"),
                "target_pace_seconds": 600,  # 10:00/mile
                "genre_preferences": {"Rock": 5, "Alternative": 4, "Indie": 3},
            },
            {
                "username": "runner_bob",
                "email": "bob@example.com",
                "first_name": "Bob",
                "height_inches": Decimal("72"),
                "leg_length_inches": Decimal("34"),
                "measured_cadence_spm": Decimal("170"),
                "target_pace_seconds": 540,  # 9:00/mile
                "genre_preferences": {"Hip-hop": 5, "Electronic": 4, "Funk": 3},
            },
            {
                "username": "runner_charlie",
                "email": "charlie@example.com",
                "first_name": "Charlie",
                "height_inches": Decimal("64"),
                "leg_length_inches": Decimal("30"),
                "measured_cadence_spm": Decimal("175"),
                "target_pace_seconds": 480,  # 8:00/mile
                "genre_preferences": {"Electronic": 5, "Dance": 4, "Pop": 3},
            },
            {
                "username": "runner_diana",
                "email": "diana@example.com",
                "first_name": "Diana",
                "height_inches": Decimal("66"),
                "leg_length_inches": Decimal("31"),
                "target_pace_seconds": 660,  # 11:00/mile
                # No measured cadence - will use height-based estimation
                "genre_preferences": {"Pop": 5, "Indie": 4, "Rock": 2},
            },
        ]

        users_created = 0
        profiles_created = 0

        for user_data in users_data:
            username = user_data["username"]
            email = user_data["email"]
            first_name = user_data["first_name"]

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                },
            )
            if created:
                users_created += 1

            profile, created = RunnerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "height_inches": user_data.get("height_inches"),
                    "leg_length_inches": user_data.get("leg_length_inches"),
                    "measured_cadence_spm": user_data.get("measured_cadence_spm"),
                    "target_pace_seconds": user_data["target_pace_seconds"],
                },
            )
            if created:
                profiles_created += 1

            # Create genre preferences
            for genre_name, weight in user_data.get("genre_preferences", {}).items():
                if genre_name in genres:
                    UserGenrePreference.objects.get_or_create(
                        user=user,
                        genre=genres[genre_name],
                        defaults={"preference_weight": Decimal(str(weight))},
                    )

        self.stdout.write(f"[OK] Created {users_created} test users")
        self.stdout.write(f"[OK] Created {profiles_created} runner profiles")

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("[OK] MOCK DATA SEEDING COMPLETE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Genres: {Genre.objects.count()}")
        self.stdout.write(f"Tracks: {Track.objects.count()}")
        self.stdout.write(f"Users: {User.objects.filter(username__startswith='runner_').count()}")
        self.stdout.write(f"Runner Profiles: {RunnerProfile.objects.count()}")
        self.stdout.write(f"Genre Preferences: {UserGenrePreference.objects.count()}")
        self.stdout.write("\nTest Users:")
        for user in User.objects.filter(username__startswith="runner_"):
            profile = user.runner_profile
            prefs = UserGenrePreference.objects.filter(user=user)
            genres_list = ", ".join([p.genre.name for p in prefs])
            self.stdout.write(
                f"  - {user.username}: {profile.target_pace_seconds // 60}:{profile.target_pace_seconds % 60:02d}/mile "
                f"({profile.measured_cadence_spm or 'height-based'} SPM) | {genres_list}"
            )
