"""
Custom JWT authentication that supports DynamoDB users.

When use_dynamo() is True, the standard SimpleJWT authentication will fail
because it tries User.objects.get(id=token['user_id']) and the user only
exists in DynamoDB. This class overrides get_user() to fetch from DDB instead.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from dynamo_backend.router import use_dynamo


class DynamoAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        if not use_dynamo():
            return super().get_user(validated_token)

        from dynamo_backend.services import auth_db

        user_id = validated_token.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token contained no recognizable user identification.')

        user = auth_db.get_user_by_id(str(user_id))
        if not user:
            raise AuthenticationFailed('User not found.')

        if not user.get('is_active', True):
            raise AuthenticationFailed('User is inactive.')

        if user.get('status') != 'approved':
            raise AuthenticationFailed('User account is not approved.')

        # Return a simple object that DRF can use as request.user
        return DynamoUser(user)


class DynamoUser:
    """Lightweight user object for DynamoDB users, compatible with DRF permissions."""

    def __init__(self, data: dict):
        self._data = data
        self.id = data['id']
        self.pk = data['id']
        self.email = data['email']
        self.username = data.get('username', data['email'])
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.role = data.get('role', '')
        self.status = data.get('status', '')
        self.notification_preference = data.get('notification_preference', 'all')
        self.email_verified = data.get('email_verified', False)
        self.is_active = data.get('is_active', False)
        self.is_staff = False
        self.is_superuser = False
        self.is_authenticated = True
        self.is_anonymous = False
        self.requested_at = data.get('requested_at')

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.email
