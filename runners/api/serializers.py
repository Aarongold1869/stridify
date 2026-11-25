from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from runners.models import RunnerProfile, UserGenrePreference
from runners.services.cadence import resolve_runner_cadence
from music.api.serializers import GenreSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'password', 'password2')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({"new_password": "Passwords don't match"})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class UserGenrePreferenceSerializer(serializers.ModelSerializer):
    genre = GenreSerializer(read_only=True)
    genre_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = UserGenrePreference
        fields = ('id', 'genre', 'genre_id', 'preference_weight')

    def create(self, validated_data):
        genre_id = validated_data.pop('genre_id', None)
        if genre_id:
            validated_data['genre_id'] = genre_id
        return super().create(validated_data)


class RunnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    cadence_spm = serializers.SerializerMethodField()
    height_display = serializers.SerializerMethodField()
    pace_display = serializers.SerializerMethodField()

    class Meta:
        model = RunnerProfile
        fields = (
            'id', 'user', 'height_inches', 'height_display', 'leg_length_inches',
            'target_pace_seconds', 'pace_display', 'measured_cadence_spm',
            'cadence_spm', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

    def get_cadence_spm(self, obj):
        result = resolve_runner_cadence(
            target_pace_seconds=obj.target_pace_seconds,
            measured_cadence_spm=obj.measured_cadence_spm,
            measured_step_length_inches=obj.step_length_inches,
            height_inches=obj.height_inches,
            leg_length_inches=obj.leg_length_inches,
        )
        return result.cadence_spm

    def get_height_display(self, obj):
        if obj.height_inches:
            feet = int(obj.height_inches // 12)
            inches = int(obj.height_inches % 12)
            return f"{feet}'{inches}\""
        return None

    def get_pace_display(self, obj):
        if obj.target_pace_seconds:
            minutes = obj.target_pace_seconds // 60
            seconds = obj.target_pace_seconds % 60
            return f"{minutes}:{seconds:02d}/mile"
        return None


class RunnerProfileCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunnerProfile
        fields = (
            'height_inches', 'leg_length_inches', 'target_pace_seconds',
            'measured_cadence_spm', 'step_length_inches', 'cadence_observed_pace_seconds'
        )
