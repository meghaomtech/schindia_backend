"""
API tests for the global_access app (global roles & permissions, and the
people holding them).

Same approach as the other apps' suites: SimpleTestCase (settings.DATABASES is a dummy
backend), dynamo_backend.services mocked at the point it's imported into
global_access.views, and force_authenticate() instead of real JWTs. Like catalogue,
these views sit behind IsAuthenticated + IsApprovedUser only — no roles.access
enforcement layer to mock.
"""
import io
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
        # 'admin' is unrestricted, so the capability check passes.
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = {'id': PERSON_ID, 'name': 'A', 'email': 'a@b.c'}

        resp = self.client.delete(f'/api/v1/global/people/{PERSON_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.remove_person.assert_called_once_with(PERSON_ID)

    def test_deleting_needs_the_staff_capability(self, mock_db):
        # Deleting a staff record used to be open to any approved user.
        mock_db.get_person.return_value = {'id': PERSON_ID, 'name': 'A', 'email': 'a@b.c'}

        resp = self.client.delete(f'/api/v1/global/people/{PERSON_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        mock_db.remove_person.assert_not_called()

    def test_unknown_person_is_not_found(self, mock_db):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = None

        resp = self.client.delete(f'/api/v1/global/people/{PERSON_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_db.remove_person.assert_not_called()


@patch('global_access.views.default_storage')
@patch('global_access.views.global_access_db')
class StaffDocumentTests(GlobalAccessAPITestCase):
    """
    GET /api/v1/global/people/<id>/documents/<index>/

    Aadhaar cards and passports. Addressed by position on the person's own
    record so a storage key can never arrive from the caller.
    """

    def _person(self):
        return {
            'id': PERSON_ID, 'name': 'Priya', 'email': 'p@x.com',
            'documents': [
                {'name': 'Aadhaar card', 'key': 'staff-documents/abc/aadhaar.pdf',
                 'content_type': 'application/pdf'},
            ],
        }

    def test_opens_the_document_recorded_against_that_person(self, mock_db, storage):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()
        storage.open.return_value = io.BytesIO(b'%PDF-1.4 fake')

        resp = self.client.get(f'/api/v1/global/people/{PERSON_ID}/documents/0/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # The key came off the record, not the request.
        storage.open.assert_called_once_with('staff-documents/abc/aadhaar.pdf')
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_needs_the_identity_documents_capability(self, mock_db, storage):
        # The same capability that decides whether documents are even listed.
        mock_db.get_person.return_value = self._person()

        resp = self.client.get(f'/api/v1/global/people/{PERSON_ID}/documents/0/')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        storage.open.assert_not_called()

    def test_an_index_beyond_their_documents_is_not_found(self, mock_db, storage):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()

        resp = self.client.get(f'/api/v1/global/people/{PERSON_ID}/documents/7/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        storage.open.assert_not_called()

    def test_unknown_person_is_not_found(self, mock_db, storage):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = None

        resp = self.client.get(f'/api/v1/global/people/{PERSON_ID}/documents/0/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        storage.open.assert_not_called()

    def test_a_missing_file_reports_not_found_rather_than_a_500(self, mock_db, storage):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()
        storage.open.side_effect = FileNotFoundError('gone')

        resp = self.client.get(f'/api/v1/global/people/{PERSON_ID}/documents/0/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@patch('global_access.views.global_access_db')
class PersonDetailTests(GlobalAccessAPITestCase):
    """
    GET / PATCH /api/v1/global/people/<id>/

    Opening a person shows what was saved when they were onboarded, and
    correcting it respects the same field rules as creating them.
    """

    URL = f'/api/v1/global/people/{PERSON_ID}/'

    def _person(self, **over):
        base = {
            'id': PERSON_ID, 'name': 'Anshal Aggarwal', 'email': 'anshal570@gmail.com',
            'job_title': 'Teacher', 'phone': '9876543210',
            'aadhaar_number': '123412341234', 'pan': 'ABCDE1234F',
            'bank_details': {'bank_name': 'HDFC'},
        }
        base.update(over)
        return base

    def test_returns_the_saved_record(self, mock_db):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()

        resp = self.client.get(self.URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['job_title'], 'Teacher')
        self.assertEqual(resp.data['phone'], '9876543210')

    def test_hides_regulated_fields_from_a_caller_without_the_capability(self, mock_db):
        # The same rule the directory listing applies — opening one person
        # must not become a way around it.
        mock_db.get_person.return_value = self._person()

        resp = self.client.get(self.URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn('aadhaar_number', resp.data)
        self.assertNotIn('bank_details', resp.data)

    def test_patches_only_the_fields_sent(self, mock_db):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()
        mock_db.update_person.return_value = self._person(phone='9000000000')

        resp = self.client.patch(self.URL, {'phone': '9000000000'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_db.update_person.call_args[0][1], {'phone': '9000000000'})

    def test_editing_needs_the_staff_capability(self, mock_db):
        mock_db.get_person.return_value = self._person()

        resp = self.client.patch(self.URL, {'phone': '9000000000'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        mock_db.update_person.assert_not_called()

    def test_validates_the_same_way_as_onboarding(self, mock_db):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()

        for field, bad in (('phone', '123'), ('aadhaar_number', '99'), ('pan', 'nope')):
            with self.subTest(field=field):
                resp = self.client.patch(self.URL, {field: bad}, format='json')
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                mock_db.update_person.assert_not_called()

    def test_an_empty_patch_is_rejected(self, mock_db):
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()

        resp = self.client.patch(self.URL, {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_db.update_person.assert_not_called()

    def test_a_start_date_is_stored_as_a_string(self, mock_db):
        # A validated DateField will not serialise into DynamoDB as-is.
        self.client.force_authenticate(user=FakeUser(role='admin'))
        mock_db.get_person.return_value = self._person()
        mock_db.update_person.return_value = self._person()

        self.client.patch(self.URL, {'start_date': '2026-09-01'}, format='json')

        self.assertEqual(mock_db.update_person.call_args[0][1]['start_date'], '2026-09-01')


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


# =============================================================================
# Onboard staff wizard
# =============================================================================

CENTRE_ID = "88888888-8888-8888-8888-888888888888"


def _profile(**overrides):
    data = {'name': 'Anshal Aggarwal', 'email': 'anshal570@gmail.com'}
    data.update(overrides)
    return data


def _payload(profile=None, assignment=None, send_invite=False):
    return {
        'profile': profile or _profile(),
        'assignment': assignment or {'role_id': ROLE_ID, 'centre_id': CENTRE_ID},
        'send_invite': send_invite,
    }


def centre_role(role_id='r-teacher-c1', name='Teacher', centre_id=CENTRE_ID, permissions=None):
    """A role from the roles app — always scoped to exactly one centre."""
    return {'id': role_id, 'name': name, 'centre_id': centre_id, 'permissions': permissions or []}


@patch("global_access.views.auth_db")
@patch("global_access.views.roles_db")
@patch("global_access.views.global_access_db")
class OnboardStaffTests(SimpleTestCase):
    """
    POST /api/v1/global/people/onboard/

    Which table a role lives in *is* its scope: global_access roles are
    organisation-wide, roles-app roles belong to one centre.
    """

    URL = "/api/v1/global/people/onboard/"

    def setUp(self):
        self.client = APIClient()
        # 'admin' is unrestricted, so capability checks pass — the denial
        # case below authenticates as 'staff' instead.
        self.client.force_authenticate(user=FakeUser(role="admin"))

    def _global(self, db, roles, people=None):
        db.get_role.return_value = custom_role()
        roles.get_role.return_value = None
        db.list_people.return_value = people or []
        db.add_person.return_value = {'id': PERSON_ID, **_profile(), 'roles': []}

    def _centre(self, db, roles, people=None, role=None):
        db.get_role.return_value = None
        roles.get_role.return_value = role or centre_role()
        db.list_people.return_value = people or []
        db.add_person.return_value = {'id': PERSON_ID, **_profile(), 'roles': []}

    def test_a_centre_role_creates_membership_in_the_roles_app(self, db, roles, auth):
        """
        Centre roles are onboarded through here too — it is what backs Add
        person on a centre's Roles tab.

        The directory row alone grants nothing at a centre: the per-centre
        permission checks read membership from the roles app, so both have to
        be written.
        """
        self._centre(db, roles)
        roles.list_roles.return_value = []
        auth.get_user_by_email.return_value = None
        auth.create_user.return_value = {'id': 'login-1'}

        res = self.client.post(self.URL, _payload(
            assignment={'role_id': 'r-teacher-c1', 'centre_id': CENTRE_ID}), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        db.add_person.assert_called_once()
        # Membership must key on the *login* user, not the directory person —
        # that is what roles.access matches against.
        self.assertEqual(roles.add_member.call_args[0][1], 'login-1')

    def test_a_centre_role_finds_its_own_centre(self, db, roles, auth):
        # Omitting centre_id must not skip the one-role-per-centre check: the
        # role itself says which centre it belongs to.
        self._centre(db, roles)
        roles.list_roles.return_value = []
        auth.get_user_by_email.return_value = None
        auth.create_user.return_value = {'id': 'login-1'}

        self.client.post(self.URL, _payload(
            assignment={'role_id': 'r-teacher-c1'}), format="json")

        roles.list_roles.assert_called_once_with(CENTRE_ID)

    def test_the_same_person_cannot_hold_two_roles_at_one_centre(self, db, roles, auth):
        self._centre(db, roles)
        auth.get_user_by_email.return_value = {'id': 'login-1'}
        roles.list_roles.return_value = [
            centre_role(role_id='r-manager-c1', name='Manager') | {
                'members': [{'user_id': 'login-1'}]
            }
        ]

        res = self.client.post(self.URL, _payload(
            assignment={'role_id': 'r-teacher-c1', 'centre_id': CENTRE_ID}), format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        roles.add_member.assert_not_called()

    def test_global_role_rejects_a_centre(self, db, roles, auth):
        self._global(db, roles)
        res = self.client.post(self.URL, _payload(
            assignment={'role_id': ROLE_ID, 'centre_id': CENTRE_ID}), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_global_role_without_a_centre_succeeds(self, db, roles, auth):
        self._global(db, roles)
        res = self.client.post(self.URL, _payload(
            assignment={'role_id': ROLE_ID}), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(db.add_person.call_args[1]['centre_id'])
        # Global roles carry no centre membership.
        roles.add_member.assert_not_called()

    def test_unknown_role_is_a_404(self, db, roles, auth):
        db.get_role.return_value = None
        roles.get_role.return_value = None
        db.list_people.return_value = []
        res = self.client.post(self.URL, _payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_an_existing_person_gains_the_role_rather_than_a_second_record(self, db, roles, auth):
        """
        One person, many roles.

        Someone already in the directory being given another role is an
        ordinary thing — a teacher who also runs a centre — so a known email
        adds the assignment instead of refusing, and does not create a
        duplicate directory row. Matching ignores case.
        """
        self._global(db, roles, people=[{'id': 'x', 'email': 'ANSHAL570@gmail.com', 'roles': []}])
        db.assign_role.return_value = {'id': ASSIGNMENT_ID}
        db.update_person.return_value = {'id': 'x'}

        res = self.client.post(self.URL, _payload(
            assignment={'role_id': ROLE_ID}), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        db.add_person.assert_not_called()
        db.assign_role.assert_called_once()

    def test_the_same_global_role_twice_is_refused(self, db, roles, auth):
        # assign_role returns None when that role is already held at that scope.
        self._global(db, roles, people=[{'id': 'x', 'email': 'anshal570@gmail.com', 'roles': []}])
        db.assign_role.return_value = None
        db.update_person.return_value = {'id': 'x'}

        res = self.client.post(self.URL, _payload(
            assignment={'role_id': ROLE_ID}), format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.json())

    def test_invalid_pan_and_aadhaar_are_rejected(self, db, roles, auth):
        self._global(db, roles)
        for field, value in (('pan', 'NOTAPAN'), ('aadhaarNumber', '123')):
            res = self.client.post(self.URL, _payload(
                profile=_profile(**{field: value}),
                assignment={'role_id': ROLE_ID}), format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, field)

    def test_missing_name_uses_the_wizard_wording(self, db, roles, auth):
        self._global(db, roles)
        res = self.client.post(self.URL, _payload(
            profile={'name': '   ', 'email': 'a@b.com'},
            assignment={'role_id': ROLE_ID}), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("global_access.capabilities.global_access_db")
    def test_staff_without_capability_cannot_onboard(self, cap_db, db, roles, auth):
        self._global(db, roles)
        cap_db.list_people.return_value = []
        cap_db.list_roles.return_value = []
        self.client.force_authenticate(user=FakeUser(role="staff"))
        res = self.client.post(self.URL, _payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("global_access.views.send_staff_invite_email")
    def test_the_invite_names_the_centre_role_that_was_assigned(self, invite, db, roles, auth):
        # Assigning Teacher and being told you are a "staff member" is what
        # this guards: the global lookup is None for a centre role, so passing
        # it to the invite fell through to that wording.
        self._centre(db, roles)
        invite.return_value = {'sent': True, 'reason': None, 'results': []}

        self.client.post(self.URL, _payload(
            assignment={'role_id': 'r-teacher-c1', 'centre_id': CENTRE_ID}, send_invite=True), format="json")

        invite.assert_called_once()
        _person, sent_role, sent_centre = invite.call_args[0]
        self.assertEqual((sent_role or {}).get('name'), 'Teacher')
        self.assertEqual(sent_centre, CENTRE_ID)

    @patch("global_access.views.send_staff_invite_email")
    def test_the_invite_still_names_a_global_role(self, invite, db, roles, auth):
        self._global(db, roles)
        invite.return_value = {'sent': True, 'reason': None, 'results': []}

        self.client.post(self.URL, _payload(assignment={'role_id': ROLE_ID}, send_invite=True), format="json")

        _person, sent_role, sent_centre = invite.call_args[0]
        self.assertEqual((sent_role or {}).get('name'), 'Regional Head')
        # Organisation-wide, so there is no centre to name.
        self.assertIsNone(sent_centre)


class StaffFieldVisibilityTests(SimpleTestCase):
    """Regulated fields must never leave the API without the capability."""

    URL = "/api/v1/global/people/"

    PERSON = {
        'id': PERSON_ID, 'name': 'Priya Nair', 'email': 'priya@shichida.local',
        'aadhaar_number': '123456789012', 'pan': 'ABCDE1234F',
        'documents': [{'name': 'Aadhaar card', 'key': 'k'}],
        'bank_details': {'account_number': '123456789'},
        'roles': [],
    }

    @patch("global_access.capabilities.global_access_db")
    @patch("global_access.views.global_access_db")
    def test_identity_and_bank_stripped_without_capability(self, db, cap_db):
        db.list_people.return_value = [dict(self.PERSON)]
        db.list_roles.return_value = []
        cap_db.list_people.return_value = []
        cap_db.list_roles.return_value = []

        client = APIClient()
        client.force_authenticate(user=FakeUser(role="staff"))
        person = client.get(self.URL).json()['people'][0]

        # Responses go through djangorestframework_camel_case, so assertions
        # must use camelCase — snake_case keys would pass vacuously.
        for field in ('aadhaarNumber', 'pan', 'documents', 'bankDetails'):
            self.assertNotIn(field, person)
        self.assertEqual(person['name'], 'Priya Nair')

    @patch("global_access.views.global_access_db")
    def test_unrestricted_user_sees_everything(self, db):
        db.list_people.return_value = [dict(self.PERSON)]
        db.list_roles.return_value = []

        client = APIClient()
        client.force_authenticate(user=FakeUser(role="admin"))
        person = client.get(self.URL).json()['people'][0]

        self.assertEqual(person['pan'], 'ABCDE1234F')
        self.assertIn('bankDetails', person)

    @patch("global_access.capabilities.global_access_db")
    @patch("global_access.views.global_access_db")
    def test_people_can_always_see_their_own_record(self, db, cap_db):
        db.list_people.return_value = [dict(self.PERSON)]
        db.list_roles.return_value = []
        cap_db.list_people.return_value = []
        cap_db.list_roles.return_value = []

        user = FakeUser(role="staff")
        user.email = 'priya@shichida.local'
        client = APIClient()
        client.force_authenticate(user=user)
        person = client.get(self.URL).json()['people'][0]

        self.assertEqual(person['pan'], 'ABCDE1234F')
        self.assertIn('bankDetails', person)


# =============================================================================
# Staff document upload
# =============================================================================

class StaffDocumentUploadTests(SimpleTestCase):
    """POST /api/v1/global/people/documents/upload/"""

    URL = "/api/v1/global/people/documents/upload/"

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser(role="admin"))

    def _file(self, name="aadhaar.pdf", content=b"%PDF-1.4 fake", content_type="application/pdf"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content, content_type=content_type)

    @patch("global_access.views.default_storage")
    def test_stores_the_file_and_returns_a_reference(self, storage):
        storage.save.return_value = "staff-documents/abc/aadhaar.pdf"
        res = self.client.post(self.URL, {'file': self._file(), 'name': 'Aadhaar card'})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        body = res.json()
        self.assertEqual(body['name'], 'Aadhaar card')
        self.assertEqual(body['key'], "staff-documents/abc/aadhaar.pdf")
        # Only the reference travels back — never the bytes.
        self.assertNotIn('content', body)

    @patch("global_access.views.default_storage")
    def test_rejects_a_disallowed_content_type(self, storage):
        res = self.client.post(self.URL, {
            'file': self._file('payload.exe', b'MZ', 'application/x-msdownload'),
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        storage.save.assert_not_called()

    @patch("global_access.views.default_storage")
    def test_rejects_a_file_over_the_size_limit(self, storage):
        from global_access.views import MAX_DOCUMENT_BYTES
        big = self._file('big.pdf', b'x' * (MAX_DOCUMENT_BYTES + 1))
        res = self.client.post(self.URL, {'file': big})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        storage.save.assert_not_called()

    def test_requires_a_file(self):
        res = self.client.post(self.URL, {})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("global_access.capabilities.global_access_db")
    def test_staff_without_the_identity_capability_are_refused(self, cap_db):
        cap_db.list_people.return_value = []
        cap_db.list_roles.return_value = []
        self.client.force_authenticate(user=FakeUser(role="staff"))
        res = self.client.post(self.URL, {'file': self._file()})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("global_access.views.default_storage")
    def test_storage_failure_is_reported_not_swallowed(self, storage):
        storage.save.side_effect = OSError("bucket unreachable")
        res = self.client.post(self.URL, {'file': self._file()})
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


# =============================================================================
# Centre-scoped assignments (service layer)
# =============================================================================

class CentreScopedAssignmentTests(SimpleTestCase):
    """
    The same role at two different centres is legitimate, so the duplicate
    guard must key on role *and* centre — not role alone.
    """

    def _service(self, existing):
        from dynamo_backend.services.global_access_service import GlobalAccessDynamoService
        svc = GlobalAccessDynamoService.__new__(GlobalAccessDynamoService)
        svc.assignments = type('Fake', (), {
            'create': staticmethod(lambda data: data),
            'query_by_index': staticmethod(lambda *a, **k: existing),
            'list_all': staticmethod(lambda: existing),
        })()
        return svc

    def test_same_role_at_a_different_centre_is_allowed(self):
        svc = self._service([{'role_id': 'r1', 'centre_id': 'c1'}])
        result = svc.assign_role('p1', 'r1', centre_id='c2')
        self.assertIsNotNone(result)
        self.assertEqual(result['centre_id'], 'c2')

    def test_same_role_at_the_same_centre_is_rejected(self):
        svc = self._service([{'role_id': 'r1', 'centre_id': 'c1'}])
        self.assertIsNone(svc.assign_role('p1', 'r1', centre_id='c1'))

    def test_duplicate_org_wide_role_is_rejected(self):
        svc = self._service([{'role_id': 'r1', 'centre_id': None}])
        self.assertIsNone(svc.assign_role('p1', 'r1'))

    def test_sub_centre_cascade_flag_is_persisted(self):
        svc = self._service([])
        result = svc.assign_role('p1', 'r1', centre_id='c1', include_sub_centres=True)
        self.assertTrue(result['include_sub_centres'])


# =============================================================================
# First login
# =============================================================================

@patch("global_access.views.auth_db")
@patch("global_access.views.roles_db")
@patch("global_access.views.global_access_db")
class OnboardCreatesLoginTests(SimpleTestCase):
    """
    A directory entry alone can't sign in — login looks the email up in the
    users table, and an unknown email gets the deliberately vague "if this
    email is registered" response. Onboarding must create the account.
    """

    URL = "/api/v1/global/people/onboard/"

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser(role="admin"))

    def _ready(self, db, roles):
        db.get_role.return_value = custom_role()
        roles.get_role.return_value = None
        db.list_people.return_value = []
        db.add_person.return_value = {'id': PERSON_ID, **_profile(), 'roles': []}

    def _post(self):
        return self.client.post(
            self.URL, _payload(assignment={'role_id': ROLE_ID}), format="json")

    def test_creates_an_approved_user(self, db, roles, auth):
        self._ready(db, roles)
        auth.get_user_by_email.return_value = None

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.json()['loginCreated'])
        kwargs = auth.create_user.call_args[1]
        self.assertEqual(kwargs['email'], 'anshal570@gmail.com')
        # Pending users are refused by IsApprovedUser, so they'd authenticate
        # and then be blocked everywhere.
        self.assertEqual(kwargs['status'], 'approved')
        self.assertEqual(kwargs['first_name'], 'Anshal')
        self.assertEqual(kwargs['last_name'], 'Aggarwal')

    def test_the_generated_password_is_random_and_never_returned(self, db, roles, auth):
        self._ready(db, roles)
        auth.get_user_by_email.return_value = None

        res = self._post()

        password = auth.create_user.call_args[1]['password']
        self.assertGreaterEqual(len(password), 32)
        # It must not reach the client, or it would sit in logs and history.
        self.assertNotIn(password, res.content.decode())

    def test_an_existing_login_is_left_alone(self, db, roles, auth):
        """Re-onboarding someone must not reset the password they already set."""
        self._ready(db, roles)
        auth.get_user_by_email.return_value = {'id': 'u1', 'email': 'anshal570@gmail.com'}

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.json()['loginCreated'])
        auth.create_user.assert_not_called()


