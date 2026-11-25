from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from runners.models import RunnerProfile, UserGenrePreference
from runners.api.serializers import (
    UserSerializer, RegisterSerializer, RunnerProfileSerializer,
    RunnerProfileCreateUpdateSerializer, UserGenrePreferenceSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer
)


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

