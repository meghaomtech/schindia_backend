from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.Serializer):
    """Serializes a DynamoUser (request.user) into the API user shape."""

    def to_representation(self, instance):
        from roles.access import get_user_access
        from global_access.capabilities import get_global_capabilities, is_unrestricted
        access = get_user_access(instance)

        return {
            'id': instance.id,
            'name': instance.get_full_name(),
            'email': instance.email,
            'role': instance.role,
            'status': instance.status,
            'permissions': self.get_permissions(access),
            'centres': self.get_centres(access),
            # Org-wide capabilities, so the client can hide Global settings
            # for people who hold none. Enforcement still happens per
            # endpoint — this only drives what's worth showing.
            'global_capabilities': sorted(get_global_capabilities(instance)),
            'unrestricted': is_unrestricted(instance),
            'requested_at': instance.requested_at,
        }

    def get_permissions(self, access):
        """Return all permissions grouped by centre for permission-based routing (Req 24)."""
        result = {}
        for centre_id, centre_access in access.centres.items():
            result[centre_id] = {
                'roles': centre_access['role_names'],
                'data_scope': centre_access['data_scope'],
                'permissions': [
                    key for key, flags in centre_access['permissions'].items()
                    if flags.get('visible', True)
                ],
            }
        return result

    def get_centres(self, access):
        """Return list of centres the user has access to (Req 24.3)."""
        return [
            {
                'id': centre_id,
                'name': centre_access['name'],
                'system_id': centre_access['system_id'],
            }
            for centre_id, centre_access in access.centres.items()
        ]


class RequestAccessSerializer(serializers.Serializer):
    """
    For POST /api/auth/request-access/
    Creates user with status=pending. No token returned.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        return value.strip().lower()


class RequestRootAccessSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        return value.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
