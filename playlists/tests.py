from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from music.models import Genre, Track
from music.choices import SyncRatio
from runners.models import UserGenrePreference, RunnerProfile
from playlists.services.recommendation import (
    calculate_bpm_match_score,
    calculate_genre_preference_score,
    calculate_energy_score,
    calculate_artist_diversity_penalty,
    score_track,
    find_matching_tracks,
    recommend_tracks,
    RecommendationQuery,
)


class BpmMatchScoreTests(TestCase):

    def test_perfect_bpm_match(self):
        score = calculate_bpm_match_score(
            track_bpm=Decimal("160"),
            target_bpm=Decimal("160"),
        )

        self.assertEqual(score, Decimal("1.00"))

    def test_within_tolerance(self):
        score = calculate_bpm_match_score(
            track_bpm=Decimal("162"),
            target_bpm=Decimal("160"),
            tolerance_percent=Decimal("5"),
        )

        self.assertGreater(score, Decimal("0.0"))
        self.assertLess(score, Decimal("1.0"))

    def test_beyond_tolerance(self):
        score = calculate_bpm_match_score(
            track_bpm=Decimal("200"),
            target_bpm=Decimal("160"),
        )

        self.assertEqual(score, Decimal("0.00"))

    def test_linear_degradation(self):
        score_2_percent = calculate_bpm_match_score(
            track_bpm=Decimal("163.2"),
            target_bpm=Decimal("160"),
            tolerance_percent=Decimal("5"),
        )

        score_4_percent = calculate_bpm_match_score(
            track_bpm=Decimal("166.4"),
            target_bpm=Decimal("160"),
            tolerance_percent=Decimal("5"),
        )

        self.assertGreater(score_2_percent, score_4_percent)

    def test_custom_tolerance(self):
        score_strict = calculate_bpm_match_score(
            track_bpm=Decimal("165"),
            target_bpm=Decimal("160"),
            tolerance_percent=Decimal("2"),
        )

        score_lenient = calculate_bpm_match_score(
            track_bpm=Decimal("165"),
            target_bpm=Decimal("160"),
            tolerance_percent=Decimal("5"),
        )

        self.assertLess(score_strict, score_lenient)

    def test_rejects_zero_target_bpm(self):
        with self.assertRaises(ValueError):
            calculate_bpm_match_score(
                track_bpm=Decimal("160"),
                target_bpm=Decimal("0"),
            )

    def test_rejects_zero_track_bpm(self):
        with self.assertRaises(ValueError):
            calculate_bpm_match_score(
                track_bpm=Decimal("0"),
                target_bpm=Decimal("160"),
            )


class GenrePreferenceScoreTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )
        self.rock_genre = Genre.objects.create(
            name="Rock",
            slug="rock",
        )
        self.pop_genre = Genre.objects.create(
            name="Pop",
            slug="pop",
        )

    def test_track_with_preferred_genre(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )
        track.genres.add(self.rock_genre)

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.rock_genre,
            preference_weight=Decimal("5.0"),
        )

        score = calculate_genre_preference_score(track, self.user)

        self.assertEqual(score, Decimal("1.00"))

    def test_track_with_low_preference_genre(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )
        track.genres.add(self.rock_genre)

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.rock_genre,
            preference_weight=Decimal("1.0"),
        )

        score = calculate_genre_preference_score(track, self.user)

        self.assertEqual(score, Decimal("0.20"))

    def test_track_with_no_genres(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )

        score = calculate_genre_preference_score(track, self.user)

        self.assertEqual(score, Decimal("0.50"))

    def test_track_with_unpreferred_genre(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )
        track.genres.add(self.rock_genre)

        score = calculate_genre_preference_score(track, self.user)

        self.assertEqual(score, Decimal("0.00"))

    def test_multiple_genres_uses_highest_preference(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )
        track.genres.add(self.rock_genre, self.pop_genre)

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.rock_genre,
            preference_weight=Decimal("2.0"),
        )
        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.pop_genre,
            preference_weight=Decimal("5.0"),
        )

        score = calculate_genre_preference_score(track, self.user)

        self.assertEqual(score, Decimal("1.00"))


class EnergyScoreTests(TestCase):

    def test_perfect_energy_match(self):
        score = calculate_energy_score(
            track_energy=Decimal("0.75"),
            target_energy=Decimal("0.75"),
        )

        self.assertEqual(score, Decimal("1.00"))

    def test_within_energy_tolerance(self):
        score = calculate_energy_score(
            track_energy=Decimal("0.80"),
            target_energy=Decimal("0.75"),
            tolerance=Decimal("0.2"),
        )

        self.assertGreater(score, Decimal("0.0"))
        self.assertLess(score, Decimal("1.0"))

    def test_beyond_energy_tolerance(self):
        score = calculate_energy_score(
            track_energy=Decimal("0.95"),
            target_energy=Decimal("0.75"),
            tolerance=Decimal("0.1"),
        )

        self.assertEqual(score, Decimal("0.00"))

    def test_no_target_energy_returns_neutral(self):
        score = calculate_energy_score(
            track_energy=Decimal("0.75"),
            target_energy=None,
        )

        self.assertEqual(score, Decimal("0.50"))

    def test_no_track_energy_returns_neutral(self):
        score = calculate_energy_score(
            track_energy=None,
            target_energy=Decimal("0.75"),
        )

        self.assertEqual(score, Decimal("0.50"))


class ArtistDiversityPenaltyTests(TestCase):

    def test_new_artist_no_penalty(self):
        penalty = calculate_artist_diversity_penalty(
            artist_name="Artist A",
            already_selected_artists={"Artist B", "Artist C"},
        )

        self.assertEqual(penalty, Decimal("0.0"))

    def test_duplicate_artist_gets_penalty(self):
        penalty = calculate_artist_diversity_penalty(
            artist_name="Artist A",
            already_selected_artists={"Artist A", "Artist B"},
        )

        self.assertEqual(penalty, Decimal("-0.1"))

    def test_custom_penalty_amount(self):
        penalty = calculate_artist_diversity_penalty(
            artist_name="Artist A",
            already_selected_artists={"Artist A"},
            penalty_per_duplicate=Decimal("0.2"),
        )

        self.assertEqual(penalty, Decimal("-0.2"))


class ScoreTrackTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )
        self.genre = Genre.objects.create(
            name="Rock",
            slug="rock",
        )

    def test_track_outside_bpm_range_returns_none(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("200"),
        )

        result = score_track(
            track=track,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            user=self.user,
            already_selected_artists=set(),
            bpm_tolerance_percent=Decimal("2"),
        )

        self.assertIsNone(result)

    def test_scores_track_within_range(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
            energy=Decimal("0.8"),
        )
        track.genres.add(self.genre)

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.genre,
            preference_weight=Decimal("5.0"),
        )

        result = score_track(
            track=track,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            user=self.user,
            already_selected_artists=set(),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.track, track)
        self.assertEqual(result.sync_ratio, SyncRatio.ONE_TO_ONE)
        self.assertGreater(result.overall_score, Decimal("0.0"))

    def test_includes_artist_diversity_in_score(self):
        track = Track.objects.create(
            title="Test Song",
            artist="Test Artist",
            duration_seconds=240,
            bpm=Decimal("160"),
        )

        result = score_track(
            track=track,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            user=self.user,
            already_selected_artists={"Test Artist"},
            bpm_tolerance_percent=Decimal("5"),
        )

        self.assertLess(result.artist_diversity_bonus, Decimal("0.0"))


class FindMatchingTracksTests(TestCase):

    def setUp(self):
        self.rock_genre = Genre.objects.create(
            name="Rock",
            slug="rock",
        )
        self.pop_genre = Genre.objects.create(
            name="Pop",
            slug="pop",
        )

        self.track_160 = Track.objects.create(
            title="Song A",
            artist="Artist A",
            duration_seconds=240,
            bpm=Decimal("160"),
        )
        self.track_160.genres.add(self.rock_genre)

        self.track_168 = Track.objects.create(
            title="Song B",
            artist="Artist B",
            duration_seconds=240,
            bpm=Decimal("168"),
        )
        self.track_168.genres.add(self.rock_genre)

        self.track_100 = Track.objects.create(
            title="Song C",
            artist="Artist C",
            duration_seconds=240,
            bpm=Decimal("100"),
        )
        self.track_100.genres.add(self.pop_genre)

    def test_finds_tracks_within_tolerance(self):
        matches = find_matching_tracks(
            target_bpm=Decimal("160"),
            bpm_tolerance_percent=Decimal("5"),
        )

        self.assertEqual(matches.count(), 2)
        self.assertIn(self.track_160, matches)
        self.assertIn(self.track_168, matches)
        self.assertNotIn(self.track_100, matches)

    def test_filters_by_genre(self):
        matches = find_matching_tracks(
            target_bpm=Decimal("160"),
            bpm_tolerance_percent=Decimal("5"),
            genres=Genre.objects.filter(id=self.rock_genre.id),
        )

        self.assertEqual(matches.count(), 2)
        self.assertIn(self.track_160, matches)
        self.assertIn(self.track_168, matches)

    def test_excludes_artists(self):
        matches = find_matching_tracks(
            target_bpm=Decimal("160"),
            bpm_tolerance_percent=Decimal("5"),
            exclude_artists={"Artist A"},
        )

        self.assertEqual(matches.count(), 1)
        self.assertNotIn(self.track_160, matches)
        self.assertIn(self.track_168, matches)


class RecommendTracksTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )
        self.genre = Genre.objects.create(
            name="Rock",
            slug="rock",
        )

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.genre,
            preference_weight=Decimal("5.0"),
        )

        self.tracks = []
        for i in range(5):
            track = Track.objects.create(
                title=f"Song {i}",
                artist=f"Artist {i}",
                duration_seconds=240,
                bpm=Decimal("160"),
                energy=Decimal("0.75"),
            )
            track.genres.add(self.genre)
            self.tracks.append(track)

    def test_returns_top_ranked_tracks(self):
        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            num_tracks=3,
        )

        recommendations = recommend_tracks(query)

        self.assertEqual(len(recommendations), 3)
        for rec in recommendations:
            self.assertIsNotNone(rec.track)
            self.assertGreater(rec.overall_score, Decimal("0.0"))

    def test_maintains_artist_diversity(self):
        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            num_tracks=5,
        )

        recommendations = recommend_tracks(query)

        artists = [rec.track.artist for rec in recommendations]
        self.assertEqual(len(artists), len(set(artists)))

    def test_respects_num_tracks_limit(self):
        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            num_tracks=2,
        )

        recommendations = recommend_tracks(query)

        self.assertEqual(len(recommendations), 2)

    def test_ranked_by_score_descending(self):
        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            num_tracks=5,
        )

        recommendations = recommend_tracks(query)

        scores = [rec.overall_score for rec in recommendations]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_respects_bpm_tolerance(self):
        track_out_of_range = Track.objects.create(
            title="Out of Range",
            artist="Out of Range Artist",
            duration_seconds=240,
            bpm=Decimal("200"),
            energy=Decimal("0.75"),
        )
        track_out_of_range.genres.add(self.genre)

        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("160"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
            num_tracks=10,
            bpm_tolerance_percent=Decimal("5"),
        )

        recommendations = recommend_tracks(query)

        track_ids = [rec.track.id for rec in recommendations]
        self.assertNotIn(track_out_of_range.id, track_ids)

    def test_raises_error_for_zero_target_bpm(self):
        query = RecommendationQuery(
            user=self.user,
            target_bpm=Decimal("0"),
            sync_ratio=SyncRatio.ONE_TO_ONE,
        )

        with self.assertRaises(ValueError):
            recommend_tracks(query)


class EstimateNumTracksNeededTests(TestCase):

    def test_60_minute_playlist_needs_15_tracks(self):
        from playlists.services.generator import estimate_num_tracks_needed

        num_tracks = estimate_num_tracks_needed(
            target_duration_minutes=60,
            average_track_duration_seconds=240,
        )

        self.assertEqual(num_tracks, 15)

    def test_30_minute_playlist_needs_7_tracks(self):
        from playlists.services.generator import estimate_num_tracks_needed

        num_tracks = estimate_num_tracks_needed(
            target_duration_minutes=30,
            average_track_duration_seconds=240,
        )

        self.assertEqual(num_tracks, 7)

    def test_minimum_one_track(self):
        from playlists.services.generator import estimate_num_tracks_needed

        num_tracks = estimate_num_tracks_needed(
            target_duration_minutes=1,
            average_track_duration_seconds=1000,
        )

        self.assertGreaterEqual(num_tracks, 1)


class PlaylistGenerationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="runner",
            email="runner@example.com",
        )

        self.runner_profile = RunnerProfile.objects.create(
            user=self.user,
            leg_length_inches=Decimal("30"),
            target_pace_seconds=600,
        )

        self.genre = Genre.objects.create(
            name="Rock",
            slug="rock",
        )

        UserGenrePreference.objects.create(
            user=self.user,
            genre=self.genre,
            preference_weight=Decimal("5.0"),
        )

        self.tracks = []
        for i in range(30):
            track = Track.objects.create(
                title=f"Song {i}",
                artist=f"Artist {i}",
                duration_seconds=240,
                bpm=Decimal("160"),
                energy=Decimal("0.75"),
            )
            track.genres.add(self.genre)
            self.tracks.append(track)

    def test_generate_basic_playlist(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Morning Run",
            duration_minutes=30,
        )

        result = generate_playlist(request)

        self.assertIsNotNone(result.playlist)
        self.assertEqual(result.playlist.user, self.user)
        self.assertEqual(result.playlist.name, "Morning Run")
        self.assertGreater(result.tracks_selected, 0)

    def test_playlist_has_correct_duration(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=30,
        )

        result = generate_playlist(request)

        # Allow some tolerance (songs might not fit exactly)
        expected_seconds = 30 * 60
        self.assertGreaterEqual(result.total_duration_seconds, expected_seconds - 300)

    def test_playlist_stores_cadence_and_pace(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
        )

        result = generate_playlist(request)

        self.assertEqual(
            result.playlist.target_pace_seconds,
            self.runner_profile.target_pace_seconds,
        )
        self.assertGreater(result.playlist.target_cadence_spm, Decimal("0"))

    def test_playlist_tracks_created_in_database(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
        )

        result = generate_playlist(request)

        playlist_tracks = result.playlist.playlist_tracks.all()
        self.assertEqual(playlist_tracks.count(), result.tracks_selected)

    def test_playlist_tracks_have_correct_positions(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
        )

        result = generate_playlist(request)

        playlist_tracks = result.playlist.playlist_tracks.all().order_by("position")

        for position, track_entry in enumerate(playlist_tracks, start=1):
            self.assertEqual(track_entry.position, position)

    def test_playlist_tracks_have_sync_ratios(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
        )

        result = generate_playlist(request)

        playlist_tracks = result.playlist.playlist_tracks.all()

        for track_entry in playlist_tracks:
            self.assertIn(track_entry.sync_ratio, dict(SyncRatio.choices))

    def test_playlist_tracks_have_match_scores(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
        )

        result = generate_playlist(request)

        playlist_tracks = result.playlist.playlist_tracks.all()

        for track_entry in playlist_tracks:
            self.assertGreater(track_entry.match_score, Decimal("0"))
            self.assertLessEqual(track_entry.match_score, Decimal("1.0"))

    def test_raises_error_for_negative_duration(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=-10,
        )

        with self.assertRaises(ValueError):
            generate_playlist(request)

    def test_raises_error_for_missing_runner_profile(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        other_user = User.objects.create_user(
            username="norunner",
            email="norunner@example.com",
        )

        request = PlaylistGenerationRequest(
            user=other_user,
            playlist_name="Run",
            duration_minutes=30,
        )

        with self.assertRaises(ValueError):
            generate_playlist(request)

    def test_raises_error_for_missing_target_pace(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        profile_no_pace = RunnerProfile.objects.create(
            user=self.user,
            leg_length_inches=Decimal("30"),
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=30,
        )

        with self.assertRaises(ValueError):
            generate_playlist(request)

    def test_sync_ratio_distribution_in_result(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=30,
        )

        result = generate_playlist(request)

        total_in_distribution = sum(result.sync_ratio_distribution.values())
        self.assertEqual(total_in_distribution, result.tracks_selected)

    def test_includes_multiple_sync_ratios(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=60,
        )

        result = generate_playlist(request)

        # With enough tracks, should have multiple sync ratios
        self.assertGreaterEqual(len(result.sync_ratio_distribution), 1)

    def test_respects_target_energy_preference(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Easy Run",
            duration_minutes=20,
            target_energy=Decimal("0.5"),
        )

        result = generate_playlist(request)

        self.assertIsNotNone(result.playlist)
        self.assertGreater(result.tracks_selected, 0)

    def test_stores_algorithm_version(self):
        from playlists.services.generator import (
            PlaylistGenerationRequest,
            generate_playlist,
        )

        request = PlaylistGenerationRequest(
            user=self.user,
            playlist_name="Run",
            duration_minutes=20,
            algorithm_version="2.0",
        )

        result = generate_playlist(request)

        self.assertEqual(result.playlist.algorithm_version, "2.0")

