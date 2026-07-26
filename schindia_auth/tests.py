"""
API tests for the schindia_auth app (access requests, OTP login, JWT lifecycle,
password reset, notification preferences, root-access admin endpoints).

Same approach as the other apps' suites: SimpleTestCase (settings.DATABASES is a dummy
backend), dynamo_backend.services and django's send_mail mocked at the point they're
imported into schindia_auth.views, and force_authenticate() with a lightweight fake user
instead of real JWTs — except where we exercise the actual JWT issuance/parsing itself
(otp_verify, logout), which needs no database and runs for real against SIMPLE_JWT.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

USER_ID = "55555555-5555-5555-5555-555555555555"
OTHER_USER_ID = "66666666-6666-6666-6666-666666666666"
REQUEST_ID = "77777777-7777-7777-7777-777777777777"

VALID_PASSWORD = "SuperSecure123!"


class FakeUser:
    """Stand-in for schindia_auth.authentication.DynamoUser."""

    def __init__(self, user_id=USER_ID, status="approved", role="admin", notification_preference="all"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.email = "jane@example.com"
        self.first_name = "Jane"
        self.last_name = "Doe"
        self.role = role
        self.status = status
        self.notification_preference = notification_preference
        self.requested_at = "2026-01-01T00:00:00"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class AuthAPITestCase(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()


def approved_user(**overrides):
    user = {
        "id": USER_ID, "email": "jane@example.com", "first_name": "Jane", "last_name": "Doe",
        "role": "admin", "status": "approved", "email_verified": False,
    }
    user.update(overrides)
    return user


# =============================================================================
# request_access
# =============================================================================

@patch('schindia_auth.views.auth_db')
class RequestAccessTests(AuthAPITestCase):
    def test_missing_fields(self, mock_auth_db):
        resp = self.client.post('/api/auth/request-access/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ("name", "email", "password"):
            self.assertIn(field, resp.data)
        mock_auth_db.create_user.assert_not_called()

    def test_weak_password_rejected(self, mock_auth_db):
        mock_auth_db.get_user_by_email.return_value = None

        resp = self.client.post(
            '/api/auth/request-access/',
            {"name": "Jane Doe", "email": "jane@example.com", "password": "1234"},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.data)
        mock_auth_db.create_user.assert_not_called()

    def test_existing_pending_user_returns_409(self, mock_auth_db):
        mock_auth_db.get_user_by_email.return_value = approved_user(status="pending")

        resp = self.client.post(
            '/api/auth/request-access/',
            {"name": "Jane Doe", "email": "jane@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already pending", resp.data["detail"])

    def test_existing_approved_user_returns_409(self, mock_auth_db):
        mock_auth_db.get_user_by_email.return_value = approved_user(status="approved")

        resp = self.client.post(
            '/api/auth/request-access/',
            {"name": "Jane Doe", "email": "jane@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("log in instead", resp.data["detail"])

    def test_existing_rejected_user_returns_409(self, mock_auth_db):
        mock_auth_db.get_user_by_email.return_value = approved_user(status="rejected")

        resp = self.client.post(
            '/api/auth/request-access/',
            {"name": "Jane Doe", "email": "jane@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("previous request", resp.data["detail"])

    def test_success_splits_name_and_creates_pending_admin(self, mock_auth_db):
        mock_auth_db.get_user_by_email.return_value = None
        mock_auth_db.create_user.return_value = {"id": USER_ID}

        resp = self.client.post(
            '/api/auth/request-access/',
            {"name": "Jane Middle Doe", "email": "JANE@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, {"status": "pending"})
        mock_auth_db.create_user.assert_called_once_with(
            email="jane@example.com",
            password=VALID_PASSWORD,
            first_name="Jane",
            last_name="Middle Doe",
            role="admin",
            status="pending",
        )


# =============================================================================
# request_root_access
# =============================================================================

@patch('schindia_auth.views.root_access_db')
@patch('schindia_auth.views.auth_db')
class RequestRootAccessTests(AuthAPITestCase):
    def test_existing_user_returns_409(self, mock_auth_db, mock_root_access_db):
        mock_auth_db.get_user_by_email.return_value = approved_user(status="approved")

        resp = self.client.post(
            '/api/auth/request-root-access/',
            {"name": "Root User", "email": "root@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        mock_root_access_db.create_request.assert_not_called()

    def test_existing_pending_request_returns_409(self, mock_auth_db, mock_root_access_db):
        mock_auth_db.get_user_by_email.return_value = None
        mock_root_access_db.get_by_email.return_value = {"status": "pending"}

        resp = self.client.post(
            '/api/auth/request-root-access/',
            {"name": "Root User", "email": "root@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        mock_root_access_db.create_request.assert_not_called()

    def test_success(self, mock_auth_db, mock_root_access_db):
        mock_auth_db.get_user_by_email.return_value = None
        mock_root_access_db.get_by_email.return_value = None
        mock_root_access_db.create_request.return_value = {"id": REQUEST_ID}

        resp = self.client.post(
            '/api/auth/request-root-access/',
            {"name": "Root User", "email": "root@example.com", "password": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        call_kwargs = mock_root_access_db.create_request.call_args.kwargs
        self.assertEqual(call_kwargs["email"], "root@example.com")
        self.assertNotEqual(call_kwargs["password_hash"], VALID_PASSWORD)  # stored hashed, not plaintext


# =============================================================================
# otp_request (routed as /api/auth/login/)
# =============================================================================

@patch('schindia_auth.views.send_mail')
@patch('schindia_auth.views.otp_db')
@patch('schindia_auth.views.auth_db')
class OtpRequestTests(AuthAPITestCase):
    def test_missing_email_or_password(self, mock_auth_db, mock_otp_db, mock_send_mail):
        resp = self.client.post('/api/auth/login/', {"email": "jane@example.com"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_returns_generic_response(self, mock_auth_db, mock_otp_db, mock_send_mail):
        mock_auth_db.get_user_by_email.return_value = None

        resp = self.client.post(
            '/api/auth/login/', {"email": "ghost@example.com", "password": "whatever"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("If this email is registered", resp.data["detail"])
        mock_otp_db.generate.assert_not_called()

    def test_wrong_password_returns_401(self, mock_auth_db, mock_otp_db, mock_send_mail):
        mock_auth_db.get_user_by_email.return_value = approved_user()
        mock_auth_db.verify_password.return_value = False

        resp = self.client.post(
            '/api/auth/login/', {"email": "jane@example.com", "password": "wrong"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_otp_db.generate.assert_not_called()

    def test_locked_email_returns_429(self, mock_auth_db, mock_otp_db, mock_send_mail):
        mock_auth_db.get_user_by_email.return_value = approved_user()
        mock_auth_db.verify_password.return_value = True
        mock_otp_db.is_email_locked.return_value = True

        resp = self.client.post(
            '/api/auth/login/', {"email": "jane@example.com", "password": VALID_PASSWORD}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_cooldown_blocks_rapid_resend(self, mock_auth_db, mock_otp_db, mock_send_mail):
        from datetime import datetime
        mock_auth_db.get_user_by_email.return_value = approved_user()
        mock_auth_db.verify_password.return_value = True
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.get_latest_unused.return_value = {"created_at": datetime.utcnow().isoformat()}

        resp = self.client.post(
            '/api/auth/login/', {"email": "jane@example.com", "password": VALID_PASSWORD}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        mock_otp_db.generate.assert_not_called()

    def test_success_generates_and_emails_otp(self, mock_auth_db, mock_otp_db, mock_send_mail):
        mock_auth_db.get_user_by_email.return_value = approved_user()
        mock_auth_db.verify_password.return_value = True
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.get_latest_unused.return_value = None
        mock_otp_db.generate.return_value = {"_plaintext_code": "123456"}

        resp = self.client.post(
            '/api/auth/login/', {"email": "jane@example.com", "password": VALID_PASSWORD}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()
        self.assertIn("123456", mock_send_mail.call_args.kwargs["message"])


# =============================================================================
# otp_verify (routed as /api/auth/login/verify/)
# =============================================================================

@patch('schindia_auth.views.auth_db')
@patch('schindia_auth.views.otp_db')
class OtpVerifyTests(AuthAPITestCase):
    def test_missing_email_or_code(self, mock_otp_db, mock_auth_db):
        resp = self.client.post('/api/auth/login/verify/', {"email": "jane@example.com"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_otp_found(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = None

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_locked_email(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = True

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_expired_otp_marks_used_and_401s(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = True

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_otp_db.mark_used.assert_called_once_with("otp-1")

    def test_wrong_code_returns_attempts_remaining(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = False
        mock_otp_db.register_failed_attempt.return_value = {"attempts": 1}

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "000000"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp.data["attempts_remaining"], 2)

    def test_wrong_code_locks_out_after_3_attempts(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = False
        mock_otp_db.register_failed_attempt.return_value = {"attempts": 3}

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "000000"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_pending_user_forbidden(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user(status="pending")

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejected_user_forbidden(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user(status="rejected")

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_not_found_after_otp_success(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = None

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_success_returns_tokens_and_marks_email_verified(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user(email_verified=False)

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "jane@example.com")
        mock_otp_db.mark_used.assert_called_once_with("otp-1")
        mock_auth_db.update_user.assert_called_once_with(USER_ID, {"email_verified": True})

    def test_success_skips_email_verified_update_if_already_verified(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user(email_verified=True)

        resp = self.client.post(
            '/api/auth/login/verify/', {"email": "jane@example.com", "code": "123456"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_auth_db.update_user.assert_not_called()


# =============================================================================
# logout_view
# =============================================================================

@patch('schindia_auth.views.blacklist_db')
class LogoutViewTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=FakeUser())

    def test_requires_authentication(self, mock_blacklist_db):
        client = APIClient()
        resp = client.post('/api/auth/logout/')

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_no_tokens_still_succeeds(self, mock_blacklist_db):
        resp = self.client.post('/api/auth/logout/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_blacklist_db.add.assert_not_called()

    def test_logout_blacklists_provided_refresh_token(self, mock_blacklist_db):
        refresh = RefreshToken()
        refresh['user_id'] = USER_ID

        resp = self.client.post('/api/auth/logout/', {"refresh": str(refresh)}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_blacklist_db.add.assert_any_call(refresh['jti'], refresh['exp'])

    def test_logout_blacklists_bearer_access_token_from_header(self, mock_blacklist_db):
        access = RefreshToken().access_token

        resp = self.client.post(
            '/api/auth/logout/', {}, format='json', HTTP_AUTHORIZATION=f'Bearer {access}'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_blacklist_db.add.assert_any_call(access['jti'], access['exp'])

    def test_logout_with_garbage_refresh_token_returns_400(self, mock_blacklist_db):
        resp = self.client.post('/api/auth/logout/', {"refresh": "not-a-real-token"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# me
# =============================================================================

class MeViewTests(AuthAPITestCase):
    def test_requires_authentication(self):
        resp = self.client.get('/api/auth/me/')

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('schindia_auth.views.auth_db')
    def test_user_not_found_in_db(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser())
        mock_auth_db.get_user_by_id.return_value = None

        resp = self.client.get('/api/auth/me/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch('dynamo_backend.services.centres_db')
    @patch('dynamo_backend.services.roles_db')
    @patch('schindia_auth.views.auth_db')
    def test_success_returns_serialized_user(self, mock_auth_db, mock_roles_db, mock_centres_db):
        self.client.force_authenticate(user=FakeUser())
        mock_auth_db.get_user_by_id.return_value = approved_user()
        mock_centres_db.list_centres.return_value = []

        resp = self.client.get('/api/auth/me/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "jane@example.com")
        self.assertEqual(resp.data["name"], "Jane Doe")
        self.assertEqual(resp.data["permissions"], {})
        self.assertEqual(resp.data["centres"], [])

    @patch('dynamo_backend.services.centres_db')
    @patch('dynamo_backend.services.roles_db')
    @patch('schindia_auth.views.auth_db')
    def test_success_includes_permissions_and_centres_from_role_membership(
        self, mock_auth_db, mock_roles_db, mock_centres_db
    ):
        self.client.force_authenticate(user=FakeUser())
        mock_auth_db.get_user_by_id.return_value = approved_user()
        mock_centres_db.list_centres.return_value = [{"id": "centre-1", "name": "Centre A", "system_id": "SC-001"}]
        mock_roles_db.list_roles.return_value = [{
            "id": "role-1", "name": "Admin", "data_scope": "all",
            "members": [{"user_id": USER_ID}],
            "permissions": [{"key": "people.manage", "visible": True}],
        }]

        resp = self.client.get('/api/auth/me/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("centre-1", resp.data["permissions"])
        self.assertEqual(resp.data["permissions"]["centre-1"]["permissions"], ["people.manage"])
        self.assertEqual(resp.data["centres"], [{"id": "centre-1", "name": "Centre A", "system_id": "SC-001"}])


# =============================================================================
# Access request management (root only)
# =============================================================================

@patch('schindia_auth.views.auth_db')
class AccessRequestsListTests(AuthAPITestCase):
    def test_non_root_user_forbidden(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser(role="admin"))

        resp = self.client.get('/api/auth/access-requests/')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_root_user_success(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser(role="root"))
        mock_auth_db.list_access_requests.return_value = [approved_user(status="pending")]

        resp = self.client.get('/api/auth/access-requests/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data[0]["email"], "jane@example.com")


@patch('schindia_auth.views.send_mail')
@patch('schindia_auth.views.auth_db')
class ApproveRejectRequestTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=FakeUser(role="root"))

    def test_approve_not_found(self, mock_auth_db, mock_send_mail):
        mock_auth_db.get_user_by_id.return_value = None

        resp = self.client.patch(f'/api/auth/access-requests/{USER_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_approve_success_sends_email(self, mock_auth_db, mock_send_mail):
        mock_auth_db.get_user_by_id.return_value = approved_user(status="pending")
        mock_auth_db.update_user.return_value = approved_user(status="approved")

        resp = self.client.patch(f'/api/auth/access-requests/{USER_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "approved")
        mock_send_mail.assert_called_once()

    def test_reject_not_found(self, mock_auth_db, mock_send_mail):
        mock_auth_db.get_user_by_id.return_value = None

        resp = self.client.patch(f'/api/auth/access-requests/{USER_ID}/reject/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_success(self, mock_auth_db, mock_send_mail):
        mock_auth_db.get_user_by_id.return_value = approved_user(status="pending")
        mock_auth_db.update_user.return_value = approved_user(status="rejected")

        resp = self.client.patch(f'/api/auth/access-requests/{USER_ID}/reject/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "rejected")
        mock_send_mail.assert_not_called()


# =============================================================================
# Root access request management (root only)
# =============================================================================

@patch('schindia_auth.views.root_access_db')
class RootAccessRequestsListTests(AuthAPITestCase):
    def test_non_root_user_forbidden(self, mock_root_access_db):
        self.client.force_authenticate(user=FakeUser(role="admin"))

        resp = self.client.get('/api/auth/root-access-requests/')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_root_user_success(self, mock_root_access_db):
        self.client.force_authenticate(user=FakeUser(role="root"))
        mock_root_access_db.list_requests.return_value = [{"id": REQUEST_ID, "name": "Root", "email": "r@x.com"}]

        resp = self.client.get('/api/auth/root-access-requests/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data[0]["id"], REQUEST_ID)


@patch('schindia_auth.views.send_mail')
@patch('schindia_auth.views.auth_db')
@patch('schindia_auth.views.root_access_db')
class ApproveRejectRootAccessRequestTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=FakeUser(role="root"))

    def test_approve_not_found(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = None

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_approve_already_reviewed(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = {"id": REQUEST_ID, "status": "approved"}

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_rejects_if_user_already_exists(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = {"id": REQUEST_ID, "status": "pending", "email": "root@example.com"}
        mock_auth_db.get_user_by_email.return_value = approved_user()

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        mock_auth_db.create_user_with_hashed_password.assert_not_called()

    def test_approve_success_creates_root_user(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = {
            "id": REQUEST_ID, "status": "pending", "email": "root@example.com",
            "name": "Root User", "password": "hashed-pw",
        }
        mock_auth_db.get_user_by_email.return_value = None
        mock_auth_db.create_user_with_hashed_password.return_value = {"id": OTHER_USER_ID}
        mock_root_access_db.approve.return_value = {
            "id": REQUEST_ID, "name": "Root User", "email": "root@example.com", "status": "approved",
        }

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/approve/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["user_id"], OTHER_USER_ID)
        mock_auth_db.create_user_with_hashed_password.assert_called_once_with(
            email="root@example.com", password_hash="hashed-pw",
            first_name="Root", last_name="User", role="root", status="approved",
        )
        mock_send_mail.assert_called_once()

    def test_reject_not_found(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = None

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/reject/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_success(self, mock_root_access_db, mock_auth_db, mock_send_mail):
        mock_root_access_db.get.return_value = {"id": REQUEST_ID, "status": "pending"}
        mock_root_access_db.reject.return_value = {"id": REQUEST_ID, "status": "rejected"}

        resp = self.client.patch(f'/api/auth/root-access-requests/{REQUEST_ID}/reject/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "rejected")


# =============================================================================
# forgot_password / reset_password
# =============================================================================

@patch('schindia_auth.views.send_mail')
@patch('schindia_auth.views.otp_db')
@patch('schindia_auth.views.auth_db')
class ForgotPasswordTests(AuthAPITestCase):
    def test_missing_email(self, mock_auth_db, mock_otp_db, mock_send_mail):
        resp = self.client.post('/api/auth/forgot-password/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_returns_generic_response_without_generating_otp(
        self, mock_auth_db, mock_otp_db, mock_send_mail
    ):
        mock_auth_db.get_user_by_email.return_value = None

        resp = self.client.post('/api/auth/forgot-password/', {"email": "ghost@example.com"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_otp_db.generate.assert_not_called()

    def test_known_email_sends_reset_code(self, mock_auth_db, mock_otp_db, mock_send_mail):
        mock_auth_db.get_user_by_email.return_value = approved_user()
        mock_otp_db.generate.return_value = {"_plaintext_code": "654321"}

        resp = self.client.post('/api/auth/forgot-password/', {"email": "jane@example.com"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()
        self.assertIn("654321", mock_send_mail.call_args.kwargs["message"])


@patch('schindia_auth.views.auth_db')
@patch('schindia_auth.views.otp_db')
class ResetPasswordTests(AuthAPITestCase):
    def test_missing_fields(self, mock_otp_db, mock_auth_db):
        resp = self.client.post('/api/auth/reset-password/', {"email": "jane@example.com"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self, mock_otp_db, mock_auth_db):
        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": "short"},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_otp_found(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = None

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_locked_email(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = True

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_expired_otp(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = True

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_otp_db.mark_used.assert_called_once_with("otp-1")

    def test_wrong_code(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = False

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "000000", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_otp_db.register_failed_attempt.assert_called_once()

    def test_user_not_found(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = None

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unapproved_account_forbidden(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user(status="pending")

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_success_updates_hashed_password(self, mock_otp_db, mock_auth_db):
        mock_otp_db.get_latest_unused.return_value = {"id": "otp-1"}
        mock_otp_db.is_email_locked.return_value = False
        mock_otp_db.is_expired.return_value = False
        mock_otp_db.verify_code.return_value = True
        mock_auth_db.get_user_by_email.return_value = approved_user()

        resp = self.client.post(
            '/api/auth/reset-password/',
            {"email": "jane@example.com", "code": "123456", "newPassword": VALID_PASSWORD},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_otp_db.mark_used.assert_called_once_with("otp-1")
        update_args = mock_auth_db.update_user.call_args[0]
        self.assertEqual(update_args[0], USER_ID)
        self.assertNotEqual(update_args[1]["password"], VALID_PASSWORD)  # stored hashed


# =============================================================================
# notification_preferences
# =============================================================================

@patch('schindia_auth.views.auth_db')
class NotificationPreferencesTests(AuthAPITestCase):
    def test_requires_authentication(self, mock_auth_db):
        resp = self.client.get('/api/auth/notification-preferences/')

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_returns_current_preference(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser(notification_preference="milestones"))

        resp = self.client.get('/api/auth/notification-preferences/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"preference": "milestones"})

    def test_patch_invalid_preference(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser())

        resp = self.client.patch('/api/auth/notification-preferences/', {"preference": "bogus"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_auth_db.update_user.assert_not_called()

    def test_patch_success(self, mock_auth_db):
        self.client.force_authenticate(user=FakeUser())

        resp = self.client.patch('/api/auth/notification-preferences/', {"preference": "none"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"preference": "none"})
        mock_auth_db.update_user.assert_called_once_with(USER_ID, {"notification_preference": "none"})
