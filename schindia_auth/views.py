from datetime import datetime

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail

import logging

from .serializers import (
    RequestAccessSerializer,
    RequestRootAccessSerializer,
    LoginSerializer,
    UserSerializer,
)
from .permissions import IsRootUser
from dynamo_backend.services import auth_db, otp_db, root_access_db, blacklist_db

logger = logging.getLogger(__name__)


def get_tokens_for_user_data(user_data):
    """Generate JWT tokens from a DynamoDB user dict."""
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


@api_view(['POST'])
@permission_classes([AllowAny])
def request_access(request):
    """Request admin access (pending approval)."""
    serializer = RequestAccessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name_parts = serializer.validated_data['name'].split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    existing = auth_db.get_user_by_email(serializer.validated_data['email'])
    if existing:
        user_status = existing.get('status', 'unknown')
        if user_status == 'pending':
            msg = 'An access request with this email is already pending approval.'
        elif user_status == 'approved':
            msg = 'An account with this email already exists. Please log in instead.'
        elif user_status == 'rejected':
            msg = 'A previous request with this email was rejected. Please contact the administrator.'
        else:
            msg = 'A user with this email already exists.'
        return Response(
            {'detail': msg},
            status=status.HTTP_409_CONFLICT
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


@api_view(['POST'])
@permission_classes([AllowAny])
def request_root_access(request):
    """Request root access (requires approval via the root-access-requests API)."""
    serializer = RequestRootAccessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']

    existing_user = auth_db.get_user_by_email(email)
    if existing_user:
        user_status = existing_user.get('status', 'unknown')
        if user_status == 'pending':
            msg = 'An access request with this email is already pending approval.'
        elif user_status == 'approved':
            msg = 'An account with this email already exists. Please log in instead.'
        elif user_status == 'rejected':
            msg = 'A previous request with this email was rejected. Please contact the administrator.'
        else:
            msg = 'A user with this email already exists.'
        return Response({'detail': msg}, status=status.HTTP_409_CONFLICT)

    existing_request = root_access_db.get_by_email(email)
    if existing_request and existing_request.get('status') == 'pending':
        return Response(
            {'detail': 'A root access request for this email is already pending.'},
            status=status.HTTP_409_CONFLICT
        )

    root_access_db.create_request(
        name=serializer.validated_data['name'],
        email=email,
        password_hash=make_password(serializer.validated_data['password']),
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

    return Response(get_tokens_for_user_data(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Blacklist the access token's jti so it's rejected immediately."""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            blacklist_db.add(token['jti'], token['exp'])

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(auth_header.split(' ', 1)[1])
            blacklist_db.add(access_token['jti'], access_token['exp'])

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
    user = auth_db.get_user_by_id(str(request.user.id))
    if not user:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsRootUser])
def access_requests_list(request):
    """List all access requests."""
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


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def approve_request(request, pk):
    """Approve a pending access request and send approval email."""
    user = auth_db.get_user_by_id(str(pk))
    if not user:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    updated = auth_db.update_user(str(pk), {'status': 'approved'})

    _send_access_approved_email(
        updated['email'],
        f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip()
    )

    return Response({
        'id': updated['id'],
        'name': f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip(),
        'email': updated['email'],
        'role': updated.get('role'),
        'status': updated.get('status'),
    })


def _send_access_approved_email(email, name):
    """Send email notifying user their access has been approved."""
    try:
        send_mail(
            subject='Access Approved — Shichida India Portal',
            message=(
                f"Hi {name},\n\n"
                f"Your access request has been approved! You can now log in to the "
                f"Shichida India Admin Portal.\n\n"
                f"To log in:\n"
                f"1. Go to the portal login page\n"
                f"2. Enter your email address\n"
                f"3. Click 'Send OTP'\n"
                f"4. Enter the 6-digit code sent to your email\n\n"
                f"Welcome aboard!\n\n"
                f"Best regards,\n"
                f"Shichida India Admin Portal"
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning(f"Failed to send approval email to {email}: {e}")


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def reject_request(request, pk):
    """Reject a pending access request."""
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


# =============================================================================
# Root Access Request Management (replaces the Django Admin approval workflow)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsRootUser])
def root_access_requests_list(request):
    """List all root access requests."""
    requests_ = root_access_db.list_requests()
    result = [
        {
            'id': r['id'],
            'name': r.get('name', ''),
            'email': r.get('email', ''),
            'status': r.get('status', 'pending'),
            'requested_at': r.get('requested_at'),
            'reviewed_at': r.get('reviewed_at'),
        }
        for r in requests_
    ]
    return Response(result)


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def approve_root_access_request(request, pk):
    """Approve a pending root access request — creates the approved root user."""
    req = root_access_db.get(pk)
    if not req:
        return Response({'detail': 'Root access request not found.'}, status=status.HTTP_404_NOT_FOUND)
    if req.get('status') != 'pending':
        return Response({'detail': 'Request has already been reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

    if auth_db.get_user_by_email(req['email']):
        return Response(
            {'detail': f"User with email {req['email']} already exists."},
            status=status.HTTP_409_CONFLICT,
        )

    name_parts = req.get('name', '').strip().split(' ', 1)
    user = auth_db.create_user_with_hashed_password(
        email=req['email'],
        password_hash=req['password'],  # already hashed
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else '',
        role='root',
        status='approved',
    )

    updated_request = root_access_db.approve(pk)
    _send_access_approved_email(req['email'], req.get('name', ''))

    return Response({
        'id': updated_request['id'],
        'name': updated_request.get('name'),
        'email': updated_request.get('email'),
        'status': updated_request.get('status'),
        'user_id': user['id'],
    })


@api_view(['PATCH'])
@permission_classes([IsRootUser])
def reject_root_access_request(request, pk):
    """Reject a pending root access request."""
    req = root_access_db.get(pk)
    if not req:
        return Response({'detail': 'Root access request not found.'}, status=status.HTTP_404_NOT_FOUND)
    updated = root_access_db.reject(pk)
    return Response({
        'id': updated['id'],
        'name': updated.get('name'),
        'email': updated.get('email'),
        'status': updated.get('status'),
    })


# =============================================================================
# OTP-Based Authentication (Req 21)
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def otp_request(request):
    """
    Request OTP for login (Req 21.1-2).
    Validates email + password first, then sends a 6-digit code to the email.
    Unknown emails get a generic response to prevent email enumeration (Req 21.10);
    a known email with a wrong password gets an explicit "Invalid credentials" error.
    """
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {'detail': 'Email and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generic response to prevent email enumeration
    generic_response = {'detail': 'If this email is registered, you will receive an OTP.'}

    user = auth_db.get_user_by_email(email)
    if not user:
        # Return generic message even if email not found
        return Response(generic_response)

    if not auth_db.verify_password(user, password):
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if email is locked (Req 21.7) — keyed on email, not per-row
    # Moved after user-existence check so 429 doesn't leak email registration status
    if otp_db.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Check cooldown (Req 21.9): don't send if last OTP was sent < 30 seconds ago
    recent_otp = otp_db.get_latest_unused(email)
    if recent_otp and recent_otp.get('created_at'):
        try:
            created_at = datetime.fromisoformat(recent_otp['created_at'])
            elapsed = (datetime.utcnow() - created_at).total_seconds()
        except ValueError:
            elapsed = None
        if elapsed is not None and elapsed < 30:
            return Response(
                {'detail': 'Please wait before requesting a new OTP.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    # Generate OTP
    otp = otp_db.generate(email)
    plaintext_code = otp.get('_plaintext_code')

    if not plaintext_code:
        logger.error(f"OTP generation failed — no plaintext code available for {email}")
        return Response(generic_response)

    # Send OTP email
    try:
        send_mail(
            subject='Your Shichida India Portal Login Code',
            message=(
                f"Your one-time login code is: {plaintext_code}\n\n"
                f"This code expires in 5 minutes.\n\n"
                f"If you did not request this code, please ignore this email."
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning(f"Failed to send OTP to {email}: {e}")

    return Response(generic_response)


@api_view(['POST'])
@permission_classes([AllowAny])
def otp_verify(request):
    """
    Verify OTP and authenticate (Req 21.5-7).
    Returns JWT tokens on success.
    """
    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()

    if not email or not code:
        return Response(
            {'detail': 'Email and code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp = otp_db.get_latest_unused(email)

    if not otp:
        return Response(
            {'detail': 'Invalid or expired OTP.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if otp_db.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again in 15 minutes.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if otp_db.is_expired(otp):
        otp_db.mark_used(otp['id'])
        return Response(
            {'detail': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not otp_db.verify_code(otp, code):
        updated_otp = otp_db.register_failed_attempt(otp)
        if updated_otp.get('attempts', 0) >= 3:
            return Response(
                {'detail': 'Too many failed attempts. Account locked for 15 minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response(
            {'detail': 'Invalid OTP.', 'attempts_remaining': 3 - updated_otp.get('attempts', 0)},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Success - mark OTP as used
    otp_db.mark_used(otp['id'])

    user_data = auth_db.get_user_by_email(email)
    if not user_data:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if user_data.get('status') == 'pending':
        return Response(
            {'detail': 'Your account is pending approval.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if user_data.get('status') == 'rejected':
        return Response(
            {'detail': 'Your account has been rejected.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Mark email as verified on successful OTP login
    if not user_data.get('email_verified'):
        auth_db.update_user(user_data['id'], {'email_verified': True})

    return Response(get_tokens_for_user_data(user_data))


# =============================================================================
# Forgot Password (Req 26.6)
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Send a password reset OTP to the user's email.
    Uses the same OTP mechanism but for password reset.
    """
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {'detail': 'Email address is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generic response to prevent email enumeration
    generic_response = {'detail': 'If this email is registered, you will receive a reset code.'}

    if not auth_db.get_user_by_email(email):
        return Response(generic_response)

    otp = otp_db.generate(email)
    plaintext_code = otp.get('_plaintext_code')

    try:
        send_mail(
            subject='Password Reset — Shichida India Portal',
            message=(
                f"Your password reset code is: {plaintext_code}\n\n"
                f"This code expires in 5 minutes.\n\n"
                f"If you did not request a password reset, please ignore this email."
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning(f"Failed to send reset OTP to {email}: {e}")

    return Response(generic_response)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Verify OTP and set new password.
    Body: { email, code, new_password }
    """
    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()
    new_password = request.data.get('new_password', '')

    if not email or not code or not new_password:
        return Response(
            {'detail': 'Email, code, and new_password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 8:
        return Response(
            {'detail': 'Password must be at least 8 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp = otp_db.get_latest_unused(email)

    if not otp:
        return Response(
            {'detail': 'Invalid or expired reset code.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if otp_db.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if otp_db.is_expired(otp):
        otp_db.mark_used(otp['id'])
        return Response(
            {'detail': 'Reset code has expired. Please request a new one.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not otp_db.verify_code(otp, code):
        otp_db.register_failed_attempt(otp)
        return Response(
            {'detail': 'Invalid reset code.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Success - mark OTP as used and update password
    otp_db.mark_used(otp['id'])

    user = auth_db.get_user_by_email(email)
    if not user:
        return Response(
            {'detail': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if user.get('status') != 'approved':
        return Response(
            {'detail': 'Account is not active. Cannot reset password.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    auth_db.update_user(user['id'], {'password': make_password(new_password)})

    return Response({'detail': 'Password reset successful. You can now log in.'})


# =============================================================================
# Notification Preferences (Req 25.4)
# =============================================================================

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """
    GET: Return current notification preference.
    PATCH: Update notification preference.
    Body for PATCH: { preference: 'all' | 'milestones' | 'none' }
    """
    if request.method == 'GET':
        pref = getattr(request.user, 'notification_preference', 'all')
        return Response({'preference': pref})

    # PATCH
    preference = request.data.get('preference', '').strip()
    valid_choices = ['all', 'milestones', 'none']
    if preference not in valid_choices:
        return Response(
            {'detail': f'Invalid preference. Must be one of: {", ".join(valid_choices)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    auth_db.update_user(str(request.user.id), {'notification_preference': preference})

    return Response({'preference': preference})
