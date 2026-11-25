from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from runners.models import RunnerProfile, UserGenrePreference, SpotifyAuth
from runners.api.serializers import (
    UserSerializer, RegisterSerializer, RunnerProfileSerializer,
    RunnerProfileCreateUpdateSerializer, UserGenrePreferenceSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    SpotifyAuthSerializer
)
from music.services.spotify_service import SpotifyService


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate JWT token for new user
            token_serializer = CustomTokenObtainPairSerializer(data={
                'username': request.data['username'],
                'password': request.data['password']
            })
            token_serializer.initial_data = {
                'username': request.data['username'],
                'password': request.data['password']
            }
            if token_serializer.is_valid():
                return Response({
                    'user': UserSerializer(user).data,
                    'access': token_serializer.validated_data['access'],
                    'refresh': token_serializer.validated_data['refresh']
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {'message': 'Password changed successfully'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def request_password_reset(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            # TODO: Send password reset email
            return Response(
                {'message': 'If a user with this email exists, a reset link will be sent'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RunnerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RunnerProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return RunnerProfile.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RunnerProfileCreateUpdateSerializer
        return RunnerProfileSerializer

    def create(self, request, *args, **kwargs):
        profile, created = RunnerProfile.objects.get_or_create(
            user=request.user
        )
        serializer = self.get_serializer(profile, data=request.data, partial=not created)
        if serializer.is_valid():
            profile = serializer.save()
            return Response(
                RunnerProfileSerializer(profile).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserGenrePreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserGenrePreferenceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return UserGenrePreference.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            preference = serializer.save(user=request.user)
            return Response(
                UserGenrePreferenceSerializer(preference).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SpotifyAuthViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    @action(detail=False, methods=['get'])
    def login(self, request):
        """Redirect user to Spotify OAuth login"""
        service = SpotifyService()
        sp_oauth = service.get_oauth_handler()
        auth_url = sp_oauth.get_authorize_url()

        # Store user ID in session to retrieve during callback
        request.session['spotify_oauth_user_id'] = request.user.id
        request.session.save()

        return Response({'auth_url': auth_url})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def callback(self, request):
        """Handle Spotify OAuth callback

        Security: Tokens flow directly from Spotify to database.
        SpotifyService.get_oauth_handler() has cache_path=False to
        prevent .cache files with sensitive credentials.
        """
        code = request.query_params.get('code')

        if not code:
            return Response(
                {'error': 'No authorization code received'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get user from session, fallback to test user for MVP
        user_id = request.session.get('spotify_oauth_user_id')
        if not user_id:
            # For MVP testing, use the test user if no session
            try:
                user = User.objects.get(username='user_session')
            except User.DoesNotExist:
                return Response(
                    {'error': 'Session expired. Please authenticate and try again.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            service = SpotifyService()
            sp_oauth = service.get_oauth_handler()
            token_info = sp_oauth.get_access_token(code)

            # Get user's Spotify profile
            user_profile = service.get_user_profile(token_info['access_token'])
            if not user_profile:
                return Response(
                    {'error': 'Failed to get Spotify profile'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save or update SpotifyAuth
            spotify_auth, created = SpotifyAuth.objects.update_or_create(
                user=user,
                defaults={
                    'spotify_user_id': user_profile['id'],
                    'access_token': token_info['access_token'],
                    'refresh_token': token_info.get('refresh_token', ''),
                    'token_expires_at': timezone.now() + timedelta(
                        seconds=token_info['expires_in']
                    ),
                }
            )

            # Clean up session
            if 'spotify_oauth_user_id' in request.session:
                del request.session['spotify_oauth_user_id']
            request.session.save()

            return Response({
                'message': 'Successfully connected to Spotify',
                'spotify_user': {
                    'id': user_profile['id'],
                    'display_name': user_profile.get('display_name'),
                    'email': user_profile.get('email'),
                }
            })

        except Exception as e:
            return Response(
                {'error': f'Spotify authentication failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Check if user is connected to Spotify"""
        try:
            spotify_auth = request.user.spotify_auth
            serializer = SpotifyAuthSerializer(spotify_auth)
            return Response({
                'connected': True,
                'data': serializer.data
            })
        except SpotifyAuth.DoesNotExist:
            return Response({
                'connected': False,
                'message': 'User not connected to Spotify'
            })

    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        """Disconnect Spotify account"""
        try:
            spotify_auth = request.user.spotify_auth
            spotify_auth.delete()
            return Response(
                {'message': 'Spotify account disconnected'},
                status=status.HTTP_200_OK
            )
        except SpotifyAuth.DoesNotExist:
            return Response(
                {'error': 'Not connected to Spotify'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def sync_library(self, request):
        """Sync user's saved tracks from Spotify"""
        try:
            spotify_auth = request.user.spotify_auth
        except SpotifyAuth.DoesNotExist:
            return Response(
                {'error': 'Not connected to Spotify'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if spotify_auth.is_expired:
                spotify_auth.refresh_access_token(SpotifyService().get_oauth_handler())

            service = SpotifyService(spotify_auth.access_token)
            spotify_tracks = service.get_user_saved_tracks(
                spotify_auth.access_token,
                limit=50
            )

            synced = service.bulk_sync_tracks(spotify_tracks)

            return Response({
                'synced_count': len(synced),
                'new_count': sum(1 for s in synced if s['created']),
                'tracks': [
                    {
                        'title': s['track'].title,
                        'artist': s['track'].artist,
                        'bpm': float(s['track'].bpm),
                        'created': s['created']
                    }
                    for s in synced
                ]
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to sync library: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )