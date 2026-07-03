from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import (
    RegisterSerializer,
    RequestAccessSerializer,
    LoginSerializer,
    UserSerializer,
    AccessRequestSerializer,
)
from .permissions import IsRootUser

User = get_user_model()


def get_tokens_for_user(user):
    """Generate JWT tokens and user info."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': str(user.id),
            'name': user.get_full_name(),
            'email': user.email,
            'role': user.role,
        }
    }


@api_view(['POST'])
@permission_classes([IsRootUser])
def register(request):
    """
    Invite a new admin user (root only).
    Creates user with role=admin, status=approved.
    Returns the created user — no JWT issued (user must log in themselves).
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Parse name into first/last
    name = serializer.validated_data['name']
    parts = name.strip().split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    user = User.objects.create_user(
        username=serializer.validated_data['email'],
        email=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
        first_name=first_name,
        last_name=last_name,
        role='admin',
        status='approved',
    )

    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_access(request):
    """
    Request admin access (pending approval).
    Creates user with role=admin, status=pending.
    Does NOT return a token — user must wait for root approval.
    """
    serializer = RequestAccessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Parse name into first/last
    name = serializer.validated_data['name']
    parts = name.strip().split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    User.objects.create_user(
        username=serializer.validated_data['email'],
        email=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
        first_name=first_name,
        last_name=last_name,
        role='admin',
        status='pending',
    )

    return Response({'status': 'pending'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login with email/password. Returns JWT if approved."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if user.status == 'pending':
        return Response(
            {'detail': 'Your account is pending approval.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if user.status == 'rejected':
        return Response(
            {'detail': 'Your account has been rejected.'},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response(get_tokens_for_user(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Blacklist the refresh token."""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out successfully.'})
    except Exception:
        return Response(
            {'detail': 'Invalid token.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Get current user info."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change the current user's password.
    Blacklists all existing refresh tokens so old JWTs cannot be reused.
    """
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            {'detail': 'Both old_password and new_password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not request.user.check_password(old_password):
        return Response(
            {'detail': 'Current password is incorrect.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

    try:
        validate_password(new_password, request.user)
    except ValidationError as e:
        return Response(
            {'detail': e.messages},
            status=status.HTTP_400_BAD_REQUEST
        )

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])

    # Blacklist all outstanding refresh tokens for this user so old JWTs
    # cannot be used after a password change.
    outstanding_tokens = OutstandingToken.objects.filter(user=request.user)
    for token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(token=token)

    return Response({'detail': 'Password changed successfully. Please log in again.'})


@api_view(['GET'])
@permission_classes([IsRootUser])
def access_requests_list(request):
    """List all access requests (pending, approved, rejected)."""
    users = User.objects.filter(role='admin').order_by('-requested_at')
    serializer = AccessRequestSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def approve_request(request, pk):
    """Approve a pending access request."""
    try:
        user = User.objects.get(pk=pk, role='admin')
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    user.status = 'approved'
    user.save(update_fields=['status'])
    serializer = AccessRequestSerializer(user)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def reject_request(request, pk):
    """Reject a pending access request."""
    try:
        user = User.objects.get(pk=pk, role='admin')
    except User.DoesNotExist:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    user.status = 'rejected'
    user.save(update_fields=['status'])
    serializer = AccessRequestSerializer(user)
    return Response(serializer.data)
