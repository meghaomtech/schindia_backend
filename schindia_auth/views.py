from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import (
    SetupRootSerializer,
    SignupSerializer,
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
@permission_classes([AllowAny])
def setup_root(request):
    """One-time root admin creation. Returns 403 if root already exists."""
    if User.objects.filter(role='root').exists():
        return Response(
            {'detail': 'Root user already exists.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = SetupRootSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = User.objects.create_user(
        username=serializer.validated_data['email'],
        email=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
        first_name=serializer.validated_data['first_name'],
        last_name=serializer.validated_data['last_name'],
        role='root',
        status='approved',
    )

    return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """Request admin access. Creates user with pending status."""
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    User.objects.create_user(
        username=serializer.validated_data['email'],
        email=serializer.validated_data['email'],
        password=serializer.validated_data['password'],
        first_name=serializer.validated_data['first_name'],
        last_name=serializer.validated_data['last_name'],
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
