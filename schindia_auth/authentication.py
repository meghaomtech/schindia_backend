"""
Custom JWT authentication backed entirely by DynamoDB.

The standard SimpleJWT authentication does User.objects.get(id=token['user_id']),
which would hit SQLite — this class fetches from DynamoDB instead, and checks
the DynamoDB blacklist table so tokens revoked on logout are rejected immediately.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings


class DynamoAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        from dynamo_backend.services import auth_db, blacklist_db

        jti = validated_token.get('jti')
        if jti and blacklist_db.is_blacklisted(jti):
            raise AuthenticationFailed('Token has been revoked.')

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


class DynamoAwareTokenRefreshSerializer(TokenRefreshSerializer):
    """Same fix as DynamoAwareJWTAuthentication, applied to token refresh.

    The stock TokenRefreshSerializer does
    get_user_model().objects.get(id=user_id) to re-check the user is still
    active, which hits Django's ORM (auth.User, integer AutoField id) with
    our DynamoDB UUID and raises ValueError: Field 'id' expected a number.
    """

    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        if user_id:
            from dynamo_backend.services import auth_db

            user = auth_db.get_user_by_id(str(user_id))
            if not user or not user.get('is_active', True):
                raise AuthenticationFailed(
                    'No active account found for the given token.',
                    code='no_active_account',
                )

        return {'access': str(refresh.access_token)}
