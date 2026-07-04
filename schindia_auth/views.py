from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone

from .serializers import (
    RegisterSerializer,
    RequestAccessSerializer,
    RequestRootAccessSerializer,
    LoginSerializer,
    UserSerializer,
    AccessRequestSerializer,
)
from .models import RootAccessRequest
from .permissions import IsRootUser
from dynamo_backend.router import use_dynamo

User = get_user_model()


def get_tokens_for_user_data(user_data):
    """Generate JWT tokens from user dict (DynamoDB) or model instance."""
    if isinstance(user_data, dict):
        refresh = RefreshToken()
        refresh['user_id'] = user_data['id']
        refresh['email'] = user_data['email']
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user_data['id'],
                'name': user_data.get('name', f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()),
                'email': user_data['email'],
                'role': user_data.get('role', 'admin'),
            }
        }
    else:
        refresh = RefreshToken.for_user(user_data)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user_data.id),
                'name': user_data.get_full_name(),
                'email': user_data.email,
                'role': user_data.role,
            }
        }


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user with immediate approval (returns JWT)."""
    if use_dynamo():
        from dynamo_backend.services import auth_db

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        existing = auth_db.get_user_by_email(serializer.validated_data['email'])
        if existing:
            return Response(
                {'email': ['A user with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = auth_db.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            role='admin',
            status='approved',
        )
        return Response(get_tokens_for_user_data(user), status=status.HTTP_201_CREATED)
    else:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=serializer.validated_data['email'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            role='admin',
            status='approved',
        )
        return Response(get_tokens_for_user_data(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_access(request):
    """Request admin access (pending approval)."""
    if use_dynamo():
        from dynamo_backend.services import auth_db

        serializer = RequestAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        existing = auth_db.get_user_by_email(serializer.validated_data['email'])
        if existing:
            return Response(
                {'email': ['A user with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        auth_db.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            role='admin',
            status='pending',
        )
        return Response({'status': 'pending'}, status=status.HTTP_201_CREATED)
    else:
        serializer = RequestAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

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
def request_root_access(request):
    """Request root access (requires admin approval from Django admin)."""
    if use_dynamo():
        from dynamo_backend.services import auth_db

        serializer = RequestRootAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        existing = auth_db.get_user_by_email(serializer.validated_data['email'])
        if existing:
            return Response(
                {'email': ['A user with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        auth_db.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            role='root',
            status='pending',
        )
        return Response({'status': 'pending'}, status=status.HTTP_201_CREATED)
    else:
        serializer = RequestRootAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name_parts = serializer.validated_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create the root access request record
        RootAccessRequest.objects.create(
            name=serializer.validated_data['name'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        return Response({'status': 'pending'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login with email/password."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    if use_dynamo():
        from dynamo_backend.services import auth_db

        user = auth_db.get_user_by_email(email)
        if not user or not auth_db.verify_password(user, password):
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.get('status') == 'pending':
            return Response(
                {'detail': 'Your account is pending approval.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if user.get('status') == 'rejected':
            return Response(
                {'detail': 'Your account has been rejected.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Ensure user exists in SQLite for JWT token validation
        django_user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'role': user.get('role', 'admin'),
                'status': 'approved',
            }
        )
        if not created:
            # Update fields in case they changed
            django_user.role = user.get('role', django_user.role)
            django_user.status = 'approved'
            django_user.save(update_fields=['role', 'status'])

        return Response(get_tokens_for_user_data(django_user))
    else:
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

        return Response(get_tokens_for_user_data(user))


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
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_id(str(request.user.id))
        if user:
            return Response({
                'id': user['id'],
                'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'email': user['email'],
                'role': user.get('role', 'admin'),
                'status': user.get('status', 'approved'),
                'requested_at': user.get('requested_at'),
            })
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change the current user's password."""
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')

    if not old_password or not new_password:
        return Response(
            {'detail': 'old_password and new_password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if use_dynamo():
        from dynamo_backend.services import auth_db
        from django.contrib.auth.hashers import make_password

        user = auth_db.get_user_by_id(str(request.user.id))
        if not user or not auth_db.verify_password(user, old_password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        auth_db.update_user(str(request.user.id), {'password': make_password(new_password)})
        return Response({'detail': 'Password changed successfully.'})
    else:
        if not request.user.check_password(old_password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({'detail': 'Password changed successfully.'})


@api_view(['GET'])
@permission_classes([IsRootUser])
def access_requests_list(request):
    """List all access requests."""
    if use_dynamo():
        from dynamo_backend.services import auth_db
        users = auth_db.list_access_requests()
        result = []
        for u in users:
            result.append({
                'id': u['id'],
                'name': f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                'email': u['email'],
                'role': u.get('role', 'admin'),
                'status': u.get('status', 'pending'),
                'requested_at': u.get('requested_at'),
            })
        return Response(result)
    else:
        users = User.objects.filter(role='admin').order_by('-requested_at')
        serializer = AccessRequestSerializer(users, many=True)
        return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def approve_request(request, pk):
    """Approve a pending access request."""
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_id(str(pk))
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        updated = auth_db.update_user(str(pk), {'status': 'approved'})
        return Response({
            'id': updated['id'],
            'name': f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip(),
            'email': updated['email'],
            'role': updated.get('role'),
            'status': updated.get('status'),
        })
    else:
        try:
            user = User.objects.get(pk=pk, role='admin')
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.status = 'approved'
        user.save(update_fields=['status'])
        serializer = AccessRequestSerializer(user)
        return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def reject_request(request, pk):
    """Reject a pending access request."""
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_id(str(pk))
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        updated = auth_db.update_user(str(pk), {'status': 'rejected'})
        return Response({
            'id': updated['id'],
            'name': f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip(),
            'email': updated['email'],
            'role': updated.get('role'),
            'status': updated.get('status'),
        })
    else:
        try:
            user = User.objects.get(pk=pk, role='admin')
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.status = 'rejected'
        user.save(update_fields=['status'])
        serializer = AccessRequestSerializer(user)
        return Response(serializer.data)
