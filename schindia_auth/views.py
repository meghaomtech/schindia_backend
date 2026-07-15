from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

import logging

from .serializers import (
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
logger = logging.getLogger(__name__)


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
        if user:
            verify_result = auth_db.verify_password(user, password)
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
        if not user:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Use UserSerializer with the DynamoUser object — it handles both paths
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


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
    """Approve a pending access request and send approval email."""
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_id(str(pk))
        if not user:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        updated = auth_db.update_user(str(pk), {'status': 'approved'})

        # Send approval email
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
    else:
        try:
            user = User.objects.get(pk=pk, role='admin')
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.status = 'approved'
        user.save(update_fields=['status'])

        # Send approval email
        _send_access_approved_email(user.email, user.get_full_name())

        serializer = AccessRequestSerializer(user)
        return Response(serializer.data)


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


# =============================================================================
# OTP-Based Authentication (Req 21)
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def otp_request(request):
    """
    Request OTP for login (Req 21.1-2).
    Sends a 6-digit code to the submitted email.
    Returns generic message to prevent email enumeration (Req 21.10).
    """
    from .models import OTPToken

    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {'detail': 'Email address is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generic response to prevent email enumeration
    generic_response = {'detail': 'If this email is registered, you will receive an OTP.'}

    # Check if user exists first (but always return generic message if not)
    user_exists = False
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_email(email)
        user_exists = user is not None
    else:
        user_exists = User.objects.filter(email=email).exists()

    if not user_exists:
        # Return generic message even if email not found
        return Response(generic_response)

    # Check if email is locked (Req 21.7) — keyed on email, not per-row
    # Moved after user-existence check so 429 doesn't leak email registration status
    if OTPToken.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Check cooldown (Req 21.9): don't send if last OTP was sent < 30 seconds ago
    recent_otp = OTPToken.objects.filter(email=email).order_by('-created_at').first()
    if recent_otp and not recent_otp.is_used:
        elapsed = (timezone.now() - recent_otp.created_at).total_seconds()
        if elapsed < 30:
            return Response(
                {'detail': 'Please wait before requesting a new OTP.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    # Generate OTP
    otp = OTPToken.generate(email)
    plaintext_code = otp.code  # Grab plaintext before any potential refresh

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
    from .models import OTPToken
    from datetime import timedelta

    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()

    if not email or not code:
        return Response(
            {'detail': 'Email and code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find the most recent unused OTP for this email
    otp = OTPToken.objects.filter(
        email=email,
        is_used=False,
    ).order_by('-created_at').first()

    if not otp:
        return Response(
            {'detail': 'Invalid or expired OTP.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if email is locked (keyed on email, not per-row)
    if OTPToken.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again in 15 minutes.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Check expiry (Req 21.4)
    if otp.is_expired:
        otp.is_used = True
        otp.save()
        return Response(
            {'detail': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Verify code (hashed comparison)
    if not otp.verify_code(code):
        from django.db.models import F
        OTPToken.objects.filter(pk=otp.pk).update(attempts=F('attempts') + 1)
        otp.refresh_from_db()
        # Lock after 3 failed attempts (Req 21.7)
        if otp.attempts >= 3:
            otp.locked_until = timezone.now() + timedelta(minutes=15)
            otp.is_used = True
            otp.save()
            return Response(
                {'detail': 'Too many failed attempts. Account locked for 15 minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response(
            {'detail': 'Invalid OTP.', 'attempts_remaining': 3 - otp.attempts},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Success - mark OTP as used and set email_verified
    otp.is_used = True
    otp.save()

    # Get user and generate tokens
    if use_dynamo():
        from dynamo_backend.services import auth_db
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
    else:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.status == 'pending':
            return Response(
                {'detail': 'Your account is pending approval.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.status == 'rejected':
            return Response(
                {'detail': 'Your account has been rejected.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Mark email as verified on successful OTP login
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        return Response(get_tokens_for_user_data(user))


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
    from .models import OTPToken

    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {'detail': 'Email address is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generic response to prevent email enumeration
    generic_response = {'detail': 'If this email is registered, you will receive a reset code.'}

    # Check if user exists
    user_exists = False
    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_email(email)
        user_exists = user is not None
    else:
        user_exists = User.objects.filter(email=email).exists()

    if not user_exists:
        return Response(generic_response)

    # Generate OTP
    otp = OTPToken.generate(email)
    plaintext_code = otp.code

    # Send reset email
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
    from .models import OTPToken
    from datetime import timedelta
    from django.contrib.auth.hashers import make_password

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

    # Verify OTP
    otp = OTPToken.objects.filter(
        email=email, is_used=False,
    ).order_by('-created_at').first()

    if not otp:
        return Response(
            {'detail': 'Invalid or expired reset code.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if OTPToken.is_email_locked(email):
        return Response(
            {'detail': 'Too many failed attempts. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if otp.is_expired:
        otp.is_used = True
        otp.save()
        return Response(
            {'detail': 'Reset code has expired. Please request a new one.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not otp.verify_code(code):
        from django.db.models import F
        OTPToken.objects.filter(pk=otp.pk).update(attempts=F('attempts') + 1)
        otp.refresh_from_db()
        if otp.attempts >= 3:
            otp.locked_until = timezone.now() + timedelta(minutes=15)
            otp.is_used = True
            otp.save()
        return Response(
            {'detail': 'Invalid reset code.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Success - mark OTP as used and update password
    otp.is_used = True
    otp.save()

    if use_dynamo():
        from dynamo_backend.services import auth_db
        user = auth_db.get_user_by_email(email)
        if not user:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user.get('status') not in ('approved',):
            return Response(
                {'detail': 'Account is not active. Cannot reset password.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        auth_db.update_user(user['id'], {'password': make_password(new_password)})
    else:
        try:
            user = User.objects.get(email=email)
            if user.status not in ('approved',):
                return Response(
                    {'detail': 'Account is not active. Cannot reset password.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            pass

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

    if use_dynamo():
        from dynamo_backend.services import auth_db
        auth_db.update_user(str(request.user.id), {'notification_preference': preference})
    else:
        request.user.notification_preference = preference
        request.user.save(update_fields=['notification_preference'])

    return Response({'preference': preference})
