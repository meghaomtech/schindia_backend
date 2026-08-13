"""Unit tests for roles.access: the shared resolver behind all permission
enforcement (view enforcement in every app's views.py, and the /api/auth/me/
response) — see roles/access.py.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from .access import get_user_access

CENTRE_A = "22222222-2222-2222-2222-222222222222"
CENTRE_B = "33333333-3333-3333-3333-333333333333"
USER_ID = "55555555-5555-5555-5555-555555555555"
OTHER_USER_ID = "66666666-6666-6666-6666-666666666666"


class FakeUser:
    # Default role is a generic per-centre custom role (e.g. "Teacher"),
    # not one of the global unrestricted roles ('root'/'admin') — most tests
    # in this file want the scoped path exercised.
    def __init__(self, user_id=USER_ID, role="staff"):
        self.id = user_id
        self.role = role


class GetUserAccessTests(SimpleTestCase):
    def test_root_user_bypasses_everything(self):
        access = get_user_access(FakeUser(role="root"))

        self.assertTrue(access.unrestricted)
        self.assertIsNone(access.accessible_centre_ids())
        self.assertTrue(access.can_access_centre("any-centre-not-in-db"))
        self.assertTrue(access.can_view("any-centre", "children.view_info"))
        self.assertTrue(access.can_edit("any-centre", "children.view_info"))

    def test_admin_user_also_bypasses_everything(self):
        # 'admin' means "approved portal user" (e.g. a centre owner/operator),
        # not just system-level 'root' — both see every centre. Only custom
        # per-centre roles (Teacher, Manager, etc.) are scoped.
        access = get_user_access(FakeUser(role="admin"))

        self.assertTrue(access.unrestricted)
        self.assertIsNone(access.accessible_centre_ids())
        self.assertTrue(access.can_access_centre("any-centre-not-in-db"))

    @patch('dynamo_backend.services.centres_db')
    @patch('dynamo_backend.services.roles_db')
    def test_non_member_has_no_access(self, mock_roles_db, mock_centres_db):
        mock_centres_db.list_centres.return_value = [{"id": CENTRE_A, "name": "Centre A"}]
        mock_roles_db.list_roles.return_value = [{
            "id": "role-1", "name": "Teacher", "data_scope": "own", "centre_id": CENTRE_A,
            "members": [{"user_id": OTHER_USER_ID}],
            "permissions": [{"key": "children.view_info", "visible": True, "edit": False}],
        }]

        access = get_user_access(FakeUser())

        self.assertFalse(access.unrestricted)
        self.assertEqual(access.accessible_centre_ids(), set())
        self.assertFalse(access.can_access_centre(CENTRE_A))
        self.assertFalse(access.can_view(CENTRE_A, "children.view_info"))

    @patch('dynamo_backend.services.centres_db')
    @patch('dynamo_backend.services.roles_db')
    def test_member_sees_only_their_centre_with_role_flags(self, mock_roles_db, mock_centres_db):
        mock_centres_db.list_centres.return_value = [
            {"id": CENTRE_A, "name": "Centre A", "system_id": "SC-001"},
            {"id": CENTRE_B, "name": "Centre B", "system_id": "SC-002"},
        ]

        def list_roles(centre_id):
            if centre_id == CENTRE_A:
                return [{
                    "id": "role-1", "name": "Teacher", "data_scope": "own", "centre_id": CENTRE_A,
                    "members": [{"user_id": USER_ID}],
                    "permissions": [
                        {"key": "children.view_info", "visible": True, "edit": False},
                        {"key": "children.manage_notes", "visible": True, "edit": True},
                    ],
                }]
            return [{
                "id": "role-2", "name": "Admin", "data_scope": "all", "centre_id": CENTRE_B,
                "members": [{"user_id": OTHER_USER_ID}],
                "permissions": [{"key": "children.view_info", "visible": True, "edit": True}],
            }]

        mock_roles_db.list_roles.side_effect = list_roles

        access = get_user_access(FakeUser())

        self.assertEqual(access.accessible_centre_ids(), {CENTRE_A})
        self.assertTrue(access.can_access_centre(CENTRE_A))
        self.assertFalse(access.can_access_centre(CENTRE_B))

        # visible but not editable
        self.assertTrue(access.can_view(CENTRE_A, "children.view_info"))
        self.assertFalse(access.can_edit(CENTRE_A, "children.view_info"))

        # visible and editable
        self.assertTrue(access.can_view(CENTRE_A, "children.manage_notes"))
        self.assertTrue(access.can_edit(CENTRE_A, "children.manage_notes"))

        # key never granted at all
        self.assertFalse(access.can_view(CENTRE_A, "admin.configure_centre_settings"))

    @patch('dynamo_backend.services.centres_db')
    @patch('dynamo_backend.services.roles_db')
    def test_memoizes_on_request(self, mock_roles_db, mock_centres_db):
        mock_centres_db.list_centres.return_value = []

        class FakeRequest:
            pass

        request = FakeRequest()
        user = FakeUser()

        first = get_user_access(user, request)
        second = get_user_access(user, request)

        self.assertIs(first, second)
        mock_centres_db.list_centres.assert_called_once()
