from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import RootAccessRequest

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status', 'requested_at']
        read_only_fields = ['id', 'role', 'status', 'requested_at']

    def get_name(self, obj):
        return obj.get_full_name()


class RegisterSerializer(serializers.Serializer):
    """
    For POST /api/auth/register/
    Creates user with status=approved and returns JWT immediately.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RequestAccessSerializer(serializers.Serializer):
    """
    For POST /api/auth/request-access/
    Creates user with status=pending. No token returned.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RequestRootAccessSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if RootAccessRequest.objects.filter(email=value, status='pending').exists():
            raise serializers.ValidationError("A root access request for this email is already pending.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AccessRequestSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status', 'requested_at']
        read_only_fields = ['id', 'name', 'email', 'role', 'requested_at']

    def get_name(self, obj):
        return obj.get_full_name()
