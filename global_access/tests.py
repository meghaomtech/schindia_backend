"""
API tests for the global_access app (global roles & permissions, and the
people holding them).

Same approach as the other apps' suites: SimpleTestCase (settings.DATABASES is a dummy
backend), dynamo_backend.services mocked at the point it's imported into
global_access.views, and force_authenticate() instead of real JWTs. Like catalogue,
these views sit behind IsAuthenticated + IsApprovedUser only — no roles.access
enforcement layer to mock.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

ROLE_ID = "33333333-3333-3333-3333-333333333333"
OTHER_ROLE_ID = "44444444-4444-4444-4444-444444444444"
PERSON_ID = "55555555-5555-5555-5555-555555555555"
ASSIGNMENT_ID = "66666666-6666-6666-6666-666666666666"


class FakeUser:
    def __init__(self, user_id="77777777-7777-7777-7777-777777777777", status="approved", role="staff"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = status
        self.role = role


class GlobalAccessAPITestCase(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = FakeUser()
        self.client.force_authenticate(user=self.user)


def custom_role(role_id=ROLE_ID, name='Regional Head', permissions=None, member_count=0):
    return {
        'id': role_id, 'name': name, 'description': '', 'kind': None,
        'permissions': permissions or [], 'member_count': member_count,
    }


def protected_role(kind='super_admin', role_id=ROLE_ID, name='Super Admin', permissions=None, member_count=0):
    return {
        'id': role_id, 'name': name, 'description': '', 'kind': kind,
        'permissions': permissions or [], 'member_count': member_count,
    }


# =============================================================================
# Permissions
# =============================================================================

class GlobalAccessPermissionsTests(SimpleTestCase):
    ENDPOINTS = [
        ("get", "/api/v1/global/roles/"),
        ("get", f"/api/v1/global/roles/{ROLE_ID}/"),
        ("post", "/api/v1/global/roles/"),
        ("get", "/api/v1/global/people/"),
        ("post", "/api/v1/global/people/add/"),
        ("get", "/api/v1/global/permissions-matrix/"),
        ("put", "/api/v1/global/permissions-matrix/save/"),
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
# GlobalRoleViewSet: list / retrieve
# =============================================================================

@patch('global_access.views.global_access_db')
class GlobalRoleListRetrieveTests(GlobalAccessAPITestCase):
    def test_list(self, mock_db):
        mock_db.list_roles.return_value = [protected_role(), custom_role()]

        resp = self.client.get('/api/v1/global/roles/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_retrieve_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.get(f'/api/v1/global/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_found(self, mock_db):
        mock_db.get_role.return_value = custom_role()

        resp = self.client.get(f'/api/v1/global/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'Regional Head')


# =============================================================================
# GlobalRoleViewSet: create
# =============================================================================

@patch('global_access.views.global_access_db')
class GlobalRoleCreateTests(GlobalAccessAPITestCase):
    def test_missing_name(self, mock_db):
        resp = self.client.post('/api/v1/global/roles/', {'name': '  '}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', resp.data)
        mock_db.create_role.assert_not_called()

    def test_name_too_long(self, mock_db):
        resp = self.client.post('/api/v1/global/roles/', {'name': 'x' * 51}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.create_role.assert_not_called()

    def test_duplicate_name_case_insensitive_rejected(self, mock_db):
        mock_db.list_roles.return_value = [protected_role(name='Super Admin')]

        resp = self.client.post('/api/v1/global/roles/', {'name': 'super admin'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', resp.data['name'][0])
        mock_db.create_role.assert_not_called()

    def test_kind_cannot_be_set_via_the_api(self, mock_db):
        """`kind` is what marks a role protected — only the seed command may set it."""
        mock_db.list_roles.return_value = []
        mock_db.create_role.return_value = custom_role()

        resp = self.client.post(
            '/api/v1/global/roles/', {'name': 'Fake Admin', 'kind': 'super_admin'}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent = mock_db.create_role.call_args[0][0]
        self.assertNotIn('kind', sent)

    def test_success_trims_name(self, mock_db):
        mock_db.list_roles.return_value = []
        mock_db.create_role.return_value = custom_role()

        resp = self.client.post('/api/v1/global/roles/', {'name': '  Regional Head  '}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent = mock_db.create_role.call_args[0][0]
        self.assertEqual(sent['name'], 'Regional Head')


# =============================================================================
# GlobalRoleViewSet: partial_update
# =============================================================================

@patch('global_access.views.global_access_db')
class GlobalRoleUpdateTests(GlobalAccessAPITestCase):
    def test_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.patch(f'/api/v1/global/roles/{ROLE_ID}/', {'name': 'New'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_db.update_role.assert_not_called()

    def test_rename_too_long(self, mock_db):
        mock_db.get_role.return_value = custom_role()

        resp = self.client.patch(f'/api/v1/global/roles/{ROLE_ID}/', {'name': 'x' * 51}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.update_role.assert_not_called()

    def test_rename_duplicate_rejected(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.list_roles.return_value = [custom_role(), protected_role(name='Affiliate', role_id=OTHER_ROLE_ID)]

        resp = self.client.patch(f'/api/v1/global/roles/{ROLE_ID}/', {'name': 'affiliate'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.update_role.assert_not_called()

    def test_update_without_rename_skips_duplicate_check(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.update_role.return_value = {**custom_role(), 'description': 'Updated'}

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/', {'description': 'Updated'}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.list_roles.assert_not_called()

    def test_kind_cannot_be_changed_via_the_api(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.update_role.return_value = custom_role()

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/', {'kind': 'super_admin'}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sent = mock_db.update_role.call_args[0][1]
        self.assertNotIn('kind', sent)

    def test_success(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.list_roles.return_value = [custom_role()]
        mock_db.update_role.return_value = {**custom_role(), 'name': 'District Head'}

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/', {'name': 'District Head'}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.update_role.assert_called_once_with(ROLE_ID, {'name': 'District Head'})


# =============================================================================
# GlobalRoleViewSet: destroy
# =============================================================================

@patch('global_access.views.global_access_db')
class GlobalRoleDestroyTests(GlobalAccessAPITestCase):
    def test_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.delete(f'/api/v1/global/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_protected_role_cannot_be_deleted(self, mock_db):
        for kind in ('super_admin', 'centre_manager', 'affiliate'):
            with self.subTest(kind=kind):
                mock_db.get_role.return_value = protected_role(kind=kind)

                resp = self.client.delete(f'/api/v1/global/roles/{ROLE_ID}/')

                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('built-in role', resp.data['detail'])
        mock_db.delete_role.assert_not_called()

    def test_custom_role_deleted_freely(self, mock_db):
        mock_db.get_role.return_value = custom_role()

        resp = self.client.delete(f'/api/v1/global/roles/{ROLE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.delete_role.assert_called_once_with(ROLE_ID)


# =============================================================================
# global_people
# =============================================================================

@patch('global_access.views.global_access_db')
class GlobalPeopleTests(GlobalAccessAPITestCase):
    def test_empty(self, mock_db):
        mock_db.list_people.return_value = []
        mock_db.list_roles.return_value = []

        resp = self.client.get('/api/v1/global/people/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {'total': 0, 'role_counts': {}, 'people': []})

    def test_attaches_permission_count_per_role_membership(self, mock_db):
        mock_db.list_people.return_value = [
            {'id': PERSON_ID, 'name': 'Helen Brooks', 'email': 'helen@example.com',
             'roles': [{'assignment_id': ASSIGNMENT_ID, 'role_id': ROLE_ID, 'role_name': 'Centre Manager'}]},
        ]
        mock_db.list_roles.return_value = [
            custom_role(permissions=[
                {'key': 'view_all_centres', 'visible': True, 'edit': False},
                {'key': 'edit_any_centre', 'visible': True, 'edit': True},
                {'key': 'archive_centres', 'visible': False, 'edit': False},
            ], member_count=1),
        ]

        resp = self.client.get('/api/v1/global/people/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total'], 1)
        self.assertEqual(resp.data['people'][0]['roles'][0]['permission_count'], 2)
        self.assertEqual(resp.data['role_counts']['Regional Head'], 1)


# =============================================================================
# add_person
# =============================================================================

@patch('global_access.views.global_access_db')
class AddPersonTests(GlobalAccessAPITestCase):
    VALID_PAYLOAD = {'name': 'Helen Brooks', 'email': 'helen@example.com', 'role_id': ROLE_ID}

    def test_missing_name(self, mock_db):
        payload = {**self.VALID_PAYLOAD, 'name': ''}

        resp = self.client.post('/api/v1/global/people/add/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', resp.data)
        mock_db.add_person.assert_not_called()

    def test_missing_email(self, mock_db):
        payload = {**self.VALID_PAYLOAD, 'email': ''}

        resp = self.client.post('/api/v1/global/people/add/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data)

    def test_missing_role(self, mock_db):
        payload = {'name': 'Helen Brooks', 'email': 'helen@example.com'}

        resp = self.client.post('/api/v1/global/people/add/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role_id', resp.data)
        mock_db.get_role.assert_not_called()

    def test_role_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.post('/api/v1/global/people/add/', self.VALID_PAYLOAD, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_db.add_person.assert_not_called()

    def test_success_defaults_member_type_to_person(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.add_person.return_value = {'id': PERSON_ID, **self.VALID_PAYLOAD}

        resp = self.client.post('/api/v1/global/people/add/', self.VALID_PAYLOAD, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_db.add_person.assert_called_once_with(
            'Helen Brooks', 'helen@example.com', ROLE_ID, member_type='person'
        )

    def test_success_organisation_member_type(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.add_person.return_value = {'id': PERSON_ID}
        payload = {**self.VALID_PAYLOAD, 'name': 'Acme Corporate Tie-up', 'member_type': 'organisation'}

        resp = self.client.post('/api/v1/global/people/add/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_db.add_person.assert_called_once_with(
            'Acme Corporate Tie-up', 'helen@example.com', ROLE_ID, member_type='organisation'
        )


# =============================================================================
# assign_role
# =============================================================================

@patch('global_access.views.global_access_db')
class AssignRoleTests(GlobalAccessAPITestCase):
    def test_missing_role_id(self, mock_db):
        resp = self.client.post(f'/api/v1/global/people/{PERSON_ID}/roles/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.assign_role.assert_not_called()

    def test_role_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.post(
            f'/api/v1/global/people/{PERSON_ID}/roles/', {'role_id': ROLE_ID}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_db.assign_role.assert_not_called()

    def test_already_holds_role(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.assign_role.return_value = None

        resp = self.client.post(
            f'/api/v1/global/people/{PERSON_ID}/roles/', {'role_id': ROLE_ID}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already holds', resp.data['detail'])

    def test_success(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.assign_role.return_value = {'id': ASSIGNMENT_ID, 'person_id': PERSON_ID, 'role_id': ROLE_ID}

        resp = self.client.post(
            f'/api/v1/global/people/{PERSON_ID}/roles/', {'role_id': ROLE_ID}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_db.assign_role.assert_called_once_with(PERSON_ID, ROLE_ID)


# =============================================================================
# remove_assignment / remove_person
# =============================================================================

@patch('global_access.views.global_access_db')
class RemoveAssignmentTests(GlobalAccessAPITestCase):
    def test_not_found(self, mock_db):
        mock_db.remove_assignment.return_value = False

        resp = self.client.delete(f'/api/v1/global/assignments/{ASSIGNMENT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_success(self, mock_db):
        mock_db.remove_assignment.return_value = True

        resp = self.client.delete(f'/api/v1/global/assignments/{ASSIGNMENT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.remove_assignment.assert_called_once_with(ASSIGNMENT_ID)


@patch('global_access.views.global_access_db')
class RemovePersonTests(GlobalAccessAPITestCase):
    def test_success(self, mock_db):
        resp = self.client.delete(f'/api/v1/global/people/{PERSON_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.remove_person.assert_called_once_with(PERSON_ID)


# =============================================================================
# permissions_matrix
# =============================================================================

@patch('global_access.views.global_access_db')
class PermissionsMatrixTests(GlobalAccessAPITestCase):
    def test_builds_matrix_grouped_by_category(self, mock_db):
        mock_db.list_roles.return_value = [
            protected_role(permissions=[{'key': 'view_all_centres', 'visible': True, 'edit': True}]),
        ]

        resp = self.client.get('/api/v1/global/permissions-matrix/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('Centres', resp.data['matrix'])
        self.assertIn('Global roles & people', resp.data['matrix'])
        first_row = resp.data['matrix']['Centres'][0]
        self.assertEqual(first_row['key'], 'view_all_centres')
        self.assertEqual(first_row['roles'][ROLE_ID], {'visible': True, 'edit': True})

    def test_unset_permission_defaults_to_false(self, mock_db):
        mock_db.list_roles.return_value = [custom_role(permissions=[])]

        resp = self.client.get('/api/v1/global/permissions-matrix/')

        first_row = resp.data['matrix']['Centres'][0]
        self.assertEqual(first_row['roles'][ROLE_ID], {'visible': False, 'edit': False})

    def test_roles_summary_includes_kind_and_member_count(self, mock_db):
        mock_db.list_roles.return_value = [protected_role(member_count=1)]

        resp = self.client.get('/api/v1/global/permissions-matrix/')

        self.assertEqual(resp.data['roles'][0], {
            'id': ROLE_ID, 'name': 'Super Admin', 'kind': 'super_admin', 'member_count': 1,
        })


# =============================================================================
# save_permissions_matrix
# =============================================================================

@patch('global_access.views.global_access_db')
class SavePermissionsMatrixTests(GlobalAccessAPITestCase):
    def test_unknown_role_id_is_skipped(self, mock_db):
        mock_db.get_role.return_value = None
        payload = {ROLE_ID: {'view_all_centres': {'visible': True, 'edit': False}}}

        resp = self.client.put('/api/v1/global/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['skipped_role_ids'], [ROLE_ID])
        mock_db.update_permission.assert_not_called()

    def test_super_admin_role_is_never_editable_via_the_matrix(self, mock_db):
        mock_db.get_role.return_value = protected_role(kind='super_admin')
        payload = {ROLE_ID: {'view_all_centres': {'visible': False, 'edit': False}}}

        resp = self.client.put('/api/v1/global/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn('skipped_role_ids', resp.data)
        mock_db.update_permission.assert_not_called()

    def test_saves_permissions_for_editable_roles(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        payload = {
            ROLE_ID: {
                'view_all_centres': {'visible': True, 'edit': False},
                'edit_any_centre': {'visible': True, 'edit': True},
            }
        }

        resp = self.client.put('/api/v1/global/permissions-matrix/save/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn('skipped_role_ids', resp.data)
        self.assertEqual(mock_db.update_permission.call_count, 2)
        mock_db.update_permission.assert_any_call(ROLE_ID, 'view_all_centres', {'visible': True, 'edit': False})
        mock_db.update_permission.assert_any_call(ROLE_ID, 'edit_any_centre', {'visible': True, 'edit': True})


# =============================================================================
# update_permission
# =============================================================================

@patch('global_access.views.global_access_db')
class UpdatePermissionTests(GlobalAccessAPITestCase):
    def test_role_not_found(self, mock_db):
        mock_db.get_role.return_value = None

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/permissions/view_all_centres/', {'visible': True}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_db.update_permission.assert_not_called()

    def test_super_admin_is_rejected(self, mock_db):
        mock_db.get_role.return_value = protected_role(kind='super_admin')

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/permissions/view_all_centres/', {'visible': False}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.update_permission.assert_not_called()

    def test_success(self, mock_db):
        mock_db.get_role.return_value = custom_role()
        mock_db.update_permission.return_value = {'key': 'view_all_centres', 'visible': True, 'edit': True}

        resp = self.client.patch(
            f'/api/v1/global/roles/{ROLE_ID}/permissions/view_all_centres/',
            {'visible': True, 'edit': True}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.update_permission.assert_called_once_with(
            ROLE_ID, 'view_all_centres', {'visible': True, 'edit': True}
        )
