from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from runners.models import RunnerProfile, UserGenrePreference
from runners.api.serializers import (
    UserSerializer, RegisterSerializer, RunnerProfileSerializer,
    RunnerProfileCreateUpdateSerializer, UserGenrePreferenceSerializer
)


class RegisterView(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
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
