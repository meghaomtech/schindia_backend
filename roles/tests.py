"""
API tests for the roles app (roles CRUD, people, permissions matrix, member management).

Same approach as the other apps' suites: SimpleTestCase (settings.DATABASES is a dummy
backend), dynamo_backend.services and django's send_mail mocked at the point they're
imported into roles.views, and force_authenticate() instead of real JWTs.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
ROLE_ID = "33333333-3333-3333-3333-333333333333"
USER_ID = "55555555-5555-5555-5555-555555555555"
OTHER_USER_ID = "66666666-6666-6666-6666-666666666666"

ADMIN_KEYS = {'people.manage', 'roles.manage'}


class FakeUser:
    def __init__(self, user_id=USER_ID, status="approved", role="staff"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = status
        self.role = role


class RolesAPITestCase(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = FakeUser()
        self.client.force_authenticate(user=self.user)


def admin_role(role_id=ROLE_ID, centre_id=CENTRE_ID, members=None):
    return {
        'id': role_id,
        'centre_id': centre_id,
        'name': 'Admin',
        'members': members or [],
        'permissions': [
            {'key': 'people.manage', 'visible': True, 'edit': True},
            {'key': 'roles.manage', 'visible': True, 'edit': True},
        ],
    }


def basic_role(role_id=ROLE_ID, centre_id=CENTRE_ID, members=None):
    return {
        'id': role_id,
        'centre_id': centre_id,
        'name': 'Teacher',
        'members': members or [],
        'permissions': [{'key': 'children.view_info', 'visible': True, 'edit': False}],
    }


# =============================================================================
# Permissions
# =============================================================================

class RolesPermissionsTests(SimpleTestCase):
    ENDPOINTS = [
        ("get", f"/api/v1/centres/{CENTRE_ID}/roles/"),
        ("get", f"/api/v1/roles/{ROLE_ID}/"),
        ("post", f"/api/v1/centres/{CENTRE_ID}/roles/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/people/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/permissions-matrix/"),
    ]

    def test_unauthenticated_requests_are_rejected(self):
        client = APIClient()
        for method, url in self.ENDPOINTS:
            with self.subTest(method=method, url=url):
                resp = getattr(client, method)(url)
                self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unapproved_user_requests_are_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=FakeUser(status="pending"))
        for method, url in self.ENDPOINTS:
            with self.subTest(method=method, url=url):
                resp = getattr(client, method)(url)
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# RoleViewSet: list / retrieve
# =============================================================================

@patch('roles.views.roles_db')
class RoleListRetrieveTests(RolesAPITestCase):
    def test_list_without_centre_returns_empty(self, mock_roles_db):
        resp = self.client.get('/api/v1/roles/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
        mock_roles_db.list_roles.assert_not_called()

    def test_list_roles_for_centre(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = [admin_role()]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/roles/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_roles_db.list_roles.assert_called_once_with(CENTRE_ID)

    def test_retrieve_not_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = None

        resp = self.client.get(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_scope_mismatch_is_404(self, mock_roles_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_roles_db.get_role.return_value = admin_role(centre_id=other_centre)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = admin_role()

        resp = self.client.get(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# =============================================================================
# RoleViewSet: create
# =============================================================================

@patch('roles.views.roles_db')
class RoleCreateTests(RolesAPITestCase):
    def test_create_without_centre_is_rejected(self, mock_roles_db):
        resp = self.client.post('/api/v1/roles/', {"name": "Teacher"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_roles_db.create_role.assert_not_called()

    def test_create_missing_name(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = []

        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/roles/', {"name": "  "}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("required", resp.data["name"][0])

    def test_create_name_too_long(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = []

        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/roles/', {"name": "x" * 51}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blocked_at_8_roles(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = [basic_role(role_id=str(i)) for i in range(8)]

        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/roles/', {"name": "New Role"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Maximum 8 roles", resp.data["name"][0])
        mock_roles_db.create_role.assert_not_called()

    def test_create_duplicate_name_case_insensitive(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = [basic_role()]

        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/roles/', {"name": "teacher"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", resp.data["name"][0])
        mock_roles_db.create_role.assert_not_called()

    def test_create_success_strips_centre_from_body(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = []
        mock_roles_db.create_role.return_value = {"id": ROLE_ID, "name": "New Role"}

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/roles/', {"name": "  New Role  ", "centre": CENTRE_ID}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent_data = mock_roles_db.create_role.call_args[0][1]
        self.assertEqual(sent_data["name"], "New Role")
        self.assertNotIn("centre", sent_data)


# =============================================================================
# RoleViewSet: partial_update
# =============================================================================

@patch('roles.views.roles_db')
class RoleUpdateTests(RolesAPITestCase):
    def test_update_not_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = None

        resp = self.client.patch(f'/api/v1/roles/{ROLE_ID}/', {"name": "New"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_scope_mismatch_is_404(self, mock_roles_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_roles_db.get_role.return_value = basic_role(centre_id=other_centre)

        resp = self.client.patch(f'/api/v1/centres/{CENTRE_ID}/roles/{ROLE_ID}/', {"name": "New"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_roles_db.update_role.assert_not_called()

    def test_rename_too_long(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()

        resp = self.client.patch(f'/api/v1/roles/{ROLE_ID}/', {"name": "x" * 51}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rename_duplicate(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [
            basic_role(), admin_role(role_id="other-role"),
        ]

        resp = self.client.patch(f'/api/v1/roles/{ROLE_ID}/', {"name": "admin"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_roles_db.update_role.assert_not_called()

    def test_update_without_rename_skips_duplicate_check(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.update_role.return_value = {"id": ROLE_ID, "description": "Updated"}

        resp = self.client.patch(f'/api/v1/roles/{ROLE_ID}/', {"description": "Updated"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_roles_db.list_roles.assert_not_called()
        mock_roles_db.update_role.assert_called_once_with(ROLE_ID, {"description": "Updated"})

    def test_update_success_with_rename(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [basic_role()]
        mock_roles_db.update_role.return_value = {"id": ROLE_ID, "name": "Senior Teacher"}

        resp = self.client.patch(f'/api/v1/roles/{ROLE_ID}/', {"name": "Senior Teacher"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_roles_db.update_role.assert_called_once_with(ROLE_ID, {"name": "Senior Teacher"})


# =============================================================================
# RoleViewSet: destroy
# =============================================================================

@patch('roles.views.roles_db')
class RoleDestroyTests(RolesAPITestCase):
    def test_destroy_not_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = None

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_scope_mismatch_is_404(self, mock_roles_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_roles_db.get_role.return_value = basic_role(centre_id=other_centre)

        resp = self.client.delete(f'/api/v1/centres/{CENTRE_ID}/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_roles_db.delete_role.assert_not_called()

    def test_destroy_blocked_by_active_members(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role(members=[{"user_id": USER_ID}])

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active members", resp.data["detail"])
        mock_roles_db.delete_role.assert_not_called()

    def test_destroy_blocked_as_last_admin_role(self, mock_roles_db):
        mock_roles_db.get_role.return_value = admin_role()
        mock_roles_db.list_roles.return_value = [admin_role(), basic_role(role_id="other-role")]

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last role with full admin permissions", resp.data["detail"])
        mock_roles_db.delete_role.assert_not_called()

    def test_destroy_admin_role_allowed_when_another_admin_role_exists(self, mock_roles_db):
        other_admin = admin_role(role_id="other-admin-role")
        mock_roles_db.get_role.return_value = admin_role()
        mock_roles_db.list_roles.return_value = [admin_role(), other_admin]

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_roles_db.delete_role.assert_called_once_with(ROLE_ID)

    def test_destroy_non_admin_role_success(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_roles_db.delete_role.assert_called_once_with(ROLE_ID)


# =============================================================================
# centre_people
# =============================================================================

@patch('roles.views.roles_db')
class CentrePeopleTests(RolesAPITestCase):
    def test_empty_when_no_roles(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = []

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/people/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"total": 0, "role_counts": {}, "people": []})

    def test_flattens_members_across_roles(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = [
            {
                "id": "role-1", "name": "Admin",
                "members": [{"user_id": USER_ID, "name": "Jane", "email": "jane@example.com"}],
            },
            {
                "id": "role-2", "name": "Teacher",
                "members": [{"user_id": OTHER_USER_ID, "name": "Bob", "email": "bob@example.com"}],
            },
        ]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/people/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], 2)
        self.assertEqual(resp.data["role_counts"], {"Admin": 1, "Teacher": 1})

    def test_user_in_multiple_roles_is_deduped_with_combined_roles_list(self, mock_roles_db):
        mock_roles_db.list_roles.return_value = [
            {"id": "role-1", "name": "Admin", "members": [{"user_id": USER_ID, "name": "Jane", "email": "j@x.com"}]},
            {"id": "role-2", "name": "Teacher", "members": [{"user_id": USER_ID, "name": "Jane", "email": "j@x.com"}]},
        ]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/people/')

        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(sorted(resp.data["people"][0]["roles"]), ["Admin", "Teacher"])


# =============================================================================
# permissions_matrix
# =============================================================================

@patch('roles.views.roles_db')
@patch('roles.views.centres_db')
class PermissionsMatrixTests(RolesAPITestCase):
    def test_centre_not_found(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_builds_matrix_with_role_flags(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_roles_db.list_roles.return_value = [admin_role()]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["roles"][0]["id"], ROLE_ID)
        self.assertEqual(resp.data["roles"][0]["member_count"], 0)
        # 'Children' module should include the people.manage-independent key row
        self.assertIn("Children", resp.data["matrix"])
        first_row = resp.data["matrix"]["Children"][0]
        self.assertIn(ROLE_ID, first_row["roles"])


# =============================================================================
# save_permissions_matrix
# =============================================================================

@patch('roles.views.roles_db')
@patch('roles.views.centres_db')
class SavePermissionsMatrixTests(RolesAPITestCase):
    def test_rejects_when_no_role_retains_admin_permissions(self, mock_centres_db, mock_roles_db):
        payload = {ROLE_ID: {"people.manage": {"visible": False, "edit": False}}}

        resp = self.client.put(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_centres_db.get_centre.assert_not_called()

    def test_centre_not_found(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = None
        payload = {ROLE_ID: {"people.manage": {"visible": True}, "roles.manage": {"visible": True}}}

        resp = self.client.put(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_skips_roles_not_belonging_to_centre(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_roles_db.get_role.return_value = basic_role(centre_id=other_centre)
        payload = {
            ROLE_ID: {
                "people.manage": {"visible": True, "edit": True},
                "roles.manage": {"visible": True, "edit": True},
            }
        }

        resp = self.client.put(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["skipped_role_ids"], [ROLE_ID])
        mock_roles_db.update_permission.assert_not_called()

    def test_saves_permissions_for_valid_roles(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_roles_db.get_role.return_value = admin_role()
        payload = {
            ROLE_ID: {
                "people.manage": {"visible": True, "edit": True},
                "roles.manage": {"visible": True, "edit": True},
                "children.view_info": {"visible": True, "edit": False},
            }
        }

        resp = self.client.put(f'/api/v1/centres/{CENTRE_ID}/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("skipped_role_ids", resp.data)
        self.assertEqual(mock_roles_db.update_permission.call_count, 3)


# =============================================================================
# update_permission
# =============================================================================

@patch('roles.views.roles_db')
class UpdatePermissionTests(RolesAPITestCase):
    def test_role_not_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = None

        resp = self.client.patch(
            f'/api/v1/roles/{ROLE_ID}/permissions/children.view_info/', {"visible": True}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_success(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.update_permission.return_value = {"key": "children.view_info", "visible": True, "edit": True}

        resp = self.client.patch(
            f'/api/v1/roles/{ROLE_ID}/permissions/children.view_info/', {"visible": True, "edit": True}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_roles_db.update_permission.assert_called_once_with(
            ROLE_ID, "children.view_info", {"visible": True, "edit": True}
        )


# =============================================================================
# add_member
# =============================================================================

@patch('roles.views.send_mail')
@patch('roles.views.auth_db')
@patch('roles.views.roles_db')
class AddMemberTests(RolesAPITestCase):
    def test_role_not_found(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = None

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/', {"user": USER_ID}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_user_id(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role()

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_roles_db.add_member.assert_not_called()

    def test_looks_up_name_and_email_when_not_provided(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [basic_role()]
        mock_auth_db.get_user_by_id.return_value = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
        mock_roles_db.add_member.return_value = {"id": "member-1", "user_id": USER_ID}

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/', {"user": USER_ID}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_roles_db.add_member.assert_called_once_with(ROLE_ID, USER_ID, name="Jane Doe", email="jane@example.com")

    def test_rejects_user_already_in_another_role_at_same_centre(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [
            basic_role(role_id="other-role", members=[{"user_id": USER_ID}]),
        ]

        resp = self.client.post(
            f'/api/v1/roles/{ROLE_ID}/members/', {"user": USER_ID, "name": "Jane", "email": "j@x.com"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists at this centre", resp.data["detail"])
        mock_roles_db.add_member.assert_not_called()

    def test_rejects_when_already_a_member_of_this_role(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [basic_role()]
        mock_roles_db.add_member.return_value = None

        resp = self.client.post(
            f'/api/v1/roles/{ROLE_ID}/members/', {"user": USER_ID, "name": "Jane", "email": "j@x.com"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists in this role", resp.data["detail"])

    def test_success_sends_onboarding_email(self, mock_roles_db, mock_auth_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role()
        mock_roles_db.list_roles.return_value = [basic_role()]
        mock_roles_db.add_member.return_value = {"id": "member-1", "user_id": USER_ID}

        resp = self.client.post(
            f'/api/v1/roles/{ROLE_ID}/members/', {"user": USER_ID, "name": "Jane", "email": "j@x.com"}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_send_mail.assert_called_once()


# =============================================================================
# resend_invite
# =============================================================================

@patch('roles.views.send_mail')
@patch('roles.views.roles_db')
class ResendInviteTests(RolesAPITestCase):
    def test_role_not_found(self, mock_roles_db, mock_send_mail):
        mock_roles_db.get_role.return_value = None

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/resend-invite/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_not_found(self, mock_roles_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role(members=[])

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/resend-invite/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_success(self, mock_roles_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role(
            members=[{"user_id": USER_ID, "name": "Jane", "email": "j@x.com"}]
        )

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/resend-invite/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()

    def test_email_failure_returns_500(self, mock_roles_db, mock_send_mail):
        mock_roles_db.get_role.return_value = basic_role(
            members=[{"user_id": USER_ID, "name": "Jane", "email": "j@x.com"}]
        )
        mock_send_mail.side_effect = Exception("SMTP down")

        resp = self.client.post(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/resend-invite/')

        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# remove_member
# =============================================================================

@patch('roles.views.roles_db')
class RemoveMemberTests(RolesAPITestCase):
    def test_role_not_found(self, mock_roles_db):
        mock_roles_db.get_role.return_value = None

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_blocked_when_removing_last_admin(self, mock_roles_db):
        mock_roles_db.get_role.return_value = admin_role(members=[{"user_id": USER_ID}])
        mock_roles_db.list_roles.return_value = [admin_role(members=[{"user_id": USER_ID}])]

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last person with admin permissions", resp.data["detail"])
        mock_roles_db.remove_member.assert_not_called()

    def test_allowed_when_another_admin_remains(self, mock_roles_db):
        mock_roles_db.get_role.return_value = admin_role(members=[{"user_id": USER_ID}, {"user_id": OTHER_USER_ID}])
        mock_roles_db.list_roles.return_value = [
            admin_role(members=[{"user_id": USER_ID}, {"user_id": OTHER_USER_ID}]),
        ]
        mock_roles_db.remove_member.return_value = True

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_admin_role_member_removed_freely(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role(members=[{"user_id": USER_ID}])
        mock_roles_db.remove_member.return_value = True

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_roles_db.remove_member.assert_called_once_with(ROLE_ID, USER_ID)

    def test_member_not_found_returns_404(self, mock_roles_db):
        mock_roles_db.get_role.return_value = basic_role(members=[])
        mock_roles_db.remove_member.return_value = False

        resp = self.client.delete(f'/api/v1/roles/{ROLE_ID}/members/{USER_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
