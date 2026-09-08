"""
Archiving a child.

Archiving takes a child off the active roll and nothing else. The record, its
contacts, bookings and invoices stay exactly where they are — a centre asked
in two years what a family was billed still has to be able to answer, and a
delete dressed up as an archive cannot.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from dynamo_backend.services.children_service import is_archived
from roles.access import UserAccess

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
OTHER_CENTRE_ID = "99999999-9999-9999-9999-999999999999"
CHILD_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "55555555-5555-5555-5555-555555555555"
USER_EMAIL = "manager@shichida.local"

ARCHIVE_URL = f"/api/v1/children/{CHILD_ID}/archive/"
UNARCHIVE_URL = f"/api/v1/children/{CHILD_ID}/unarchive/"


class FakeUser:
    def __init__(self):
        self.id = USER_ID
        self.pk = USER_ID
        self.email = USER_EMAIL
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"


def child(**over):
    base = {
        'id': CHILD_ID, 'system_id': 'CHD-001', 'centre_id': CENTRE_ID,
        'first_name': 'Aarav', 'last_name': 'Sharma', 'gender': 'Male',
        'date_of_birth': '2022-04-01', 'start_date': '2026-01-10',
        'contacts': [{'invite_as': 'Parent', 'email': 'riya@example.com'}],
    }
    base.update(over)
    return base


def scoped_access(**permissions):
    access = UserAccess(unrestricted=False)
    access.centres[CENTRE_ID] = {
        'data_scope': 'own', 'role_names': ['Manager'],
        'permissions': {k: {'visible': True, 'edit': v}
                        for k, v in permissions.items()},
    }
    return access


class IsArchivedTests(SimpleTestCase):
    def test_a_child_stored_before_archiving_existed_reads_as_active(self):
        # No `archived` attribute at all must mean active, not neither.
        self.assertFalse(is_archived({'id': CHILD_ID}))

    def test_reads_the_flag_when_it_is_there(self):
        self.assertTrue(is_archived({'archived': True}))
        self.assertFalse(is_archived({'archived': False}))

    def test_nothing_is_not_archived(self):
        self.assertFalse(is_archived(None))


@patch('children.views.get_user_access')
@patch('children.views.children_db')
class ArchiveChildTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def test_archives_the_child_and_says_who_did_it(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = child()
        db.archive_child.return_value = child(archived=True)

        res = self.client.post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.archive_child.assert_called_once_with(CHILD_ID, archived_by=USER_EMAIL)

    def test_never_deletes_anything(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = child()
        db.archive_child.return_value = child(archived=True)

        self.client.post(ARCHIVE_URL)

        db.delete_child.assert_not_called()
        db.delete_contact.assert_not_called()
        db.delete_enrolment.assert_not_called()

    def test_archiving_an_already_archived_child_changes_nothing(self, db, access):
        # A repeated click must not write a second archive date over the real one.
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = child(archived=True, archived_at='2026-01-01T00:00:00')

        res = self.client.post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.archive_child.assert_not_called()

    def test_an_unknown_child_is_not_found(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = None

        res = self.client.post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        db.archive_child.assert_not_called()

    def test_another_centres_child_cannot_be_archived(self, db, access):
        # The id comes from the URL and is never trusted on its own.
        db.get_child.return_value = child(centre_id=OTHER_CENTRE_ID)
        access.return_value = scoped_access(**{'children.register_status': True})

        res = self.client.post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        db.archive_child.assert_not_called()

    def test_a_member_without_the_status_permission_is_refused(self, db, access):
        db.get_child.return_value = child()
        access.return_value = scoped_access(**{'children.view_info': True})

        res = self.client.post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        db.archive_child.assert_not_called()

    def test_an_anonymous_caller_is_refused(self, db, access):
        res = APIClient().post(ARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        db.archive_child.assert_not_called()


@patch('children.views.get_user_access')
@patch('children.views.children_db')
class UnarchiveChildTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def test_restores_an_archived_child(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = child(archived=True)
        db.unarchive_child.return_value = child(archived=False)

        res = self.client.post(UNARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.unarchive_child.assert_called_once_with(CHILD_ID)

    def test_unarchiving_an_active_child_changes_nothing(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.get_child.return_value = child()

        res = self.client.post(UNARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.unarchive_child.assert_not_called()

    def test_another_centres_child_cannot_be_restored(self, db, access):
        db.get_child.return_value = child(centre_id=OTHER_CENTRE_ID)
        access.return_value = scoped_access(**{'children.register_status': True})

        res = self.client.post(UNARCHIVE_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        db.unarchive_child.assert_not_called()


@patch('children.views.get_user_access')
@patch('children.views.children_db')
class ChildListArchiveFilterTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _list(self, query=''):
        return self.client.get(f'/api/v1/children/?centre={CENTRE_ID}{query}')

    def test_the_default_list_is_the_active_roll(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.list_children.return_value = [child()]

        res = self._list()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.list_children.assert_called_once_with(CENTRE_ID, archived=False)

    def test_archived_children_are_asked_for_explicitly(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.list_children.return_value = [child(archived=True)]

        self._list('&status=archived')

        db.list_children.assert_called_once_with(CENTRE_ID, archived=True)

    def test_everything_can_still_be_asked_for(self, db, access):
        access.return_value = UserAccess(unrestricted=True)
        db.list_children.return_value = []

        self._list('&status=all')

        db.list_children.assert_called_once_with(CENTRE_ID, archived=None)

    def test_an_unknown_status_is_rejected_rather_than_guessed_at(self, db, access):
        access.return_value = UserAccess(unrestricted=True)

        res = self._list('&status=deleted')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        db.list_children.assert_not_called()

    def test_the_filter_still_runs_behind_the_centre_scope_check(self, db, access):
        access.return_value = UserAccess(unrestricted=False)

        res = self._list('&status=archived')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        db.list_children.assert_not_called()


class ListChildrenFilterTests(SimpleTestCase):
    """The service-level filter the API leans on."""

    def _service(self, rows):
        from dynamo_backend.services.children_service import ChildrenDynamoService
        service = ChildrenDynamoService()
        service.children = _StubTable(rows)
        service.contacts = _StubContacts()
        return service

    def test_active_leaves_out_archived_children(self):
        service = self._service([child(), child(id='b', archived=True)])
        self.assertEqual([c['id'] for c in service.list_children(CENTRE_ID, archived=False)],
                         [CHILD_ID])

    def test_archived_shows_only_archived_children(self):
        service = self._service([child(), child(id='b', archived=True)])
        self.assertEqual([c['id'] for c in service.list_children(CENTRE_ID, archived=True)],
                         ['b'])

    def test_no_filter_returns_everything(self):
        # Callers reaching children on their way to invoices or the timetable
        # need the whole set — an archived child's invoices still exist.
        service = self._service([child(), child(id='b', archived=True)])
        self.assertEqual(len(service.list_children(CENTRE_ID)), 2)


class _StubTable:
    def __init__(self, rows):
        self.rows = rows

    def query_by_index(self, _index, _key, value):
        return [dict(r) for r in self.rows if r.get('centre_id') == value]

    def list_all(self):
        return [dict(r) for r in self.rows]


class _StubContacts:
    def query_by_index(self, _index, _key, _value):
        return []
