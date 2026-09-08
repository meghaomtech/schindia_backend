"""
Moving a child between centres.

Four things have to hold, and every test here is one of them.

The child does not move when the request is made — only when a Global Admin
approves. A centre that could move its own children would make the approval
step decorative.

Only a Global Admin decides: root, or a holder of the Super Admin global
role. Not a centre member, not a Centre Manager, and not an ordinary portal
admin either — the request goes to the organisation's administrators alone.

An approval is all-or-nothing. If any part of it fails, the child is back at
the centre they started at, their invoices are back on them, and the request
is back to pending for someone to try again.

A rejection changes nothing at all — not the centre, and not one invoice.

Nothing here touches DynamoDB: every service is patched where it is looked
up, including the global_access lookups behind the Global Admin rule.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from dynamo_backend.services.move_requests_service import (
    APPROVED, MoveRequestConflict, MoveRequestsUnavailable, PENDING, PROCESSING,
    REJECTED,
)
from notifications.tokens import make_move_action_token
from roles.access import UserAccess

FROM_CENTRE = "22222222-2222-2222-2222-222222222222"
TO_CENTRE = "88888888-8888-8888-8888-888888888888"
OTHER_CENTRE = "99999999-9999-9999-9999-999999999999"
CHILD_ID = "11111111-1111-1111-1111-111111111111"
REQUEST_ID = "44444444-4444-4444-4444-444444444444"
USER_ID = "55555555-5555-5555-5555-555555555555"
USER_EMAIL = "manager@shichida.local"
ADMIN_EMAIL = "admin@shichida.local"
SUPER_ADMIN_ROLE_ID = "66666666-6666-6666-6666-666666666666"
CENTRE_MANAGER_ROLE_ID = "77777777-7777-7777-7777-777777777777"

REQUEST_URL = f"/api/v1/children/{CHILD_ID}/move-requests/"
PREVIEW_URL = f"/api/v1/children/{CHILD_ID}/move-preview/"
QUEUE_URL = "/api/v1/move-requests/"
APPROVE_URL = f"/api/v1/move-requests/{REQUEST_ID}/approve/"
REJECT_URL = f"/api/v1/move-requests/{REQUEST_ID}/reject/"
EMAIL_ACTION_URL = "/api/v1/move-requests/email-action/"


class FakeUser:
    def __init__(self, email=USER_EMAIL, role="staff"):
        self.id = USER_ID
        self.pk = USER_ID
        self.email = email
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = role


def child(**over):
    base = {'id': CHILD_ID, 'system_id': 'CHD-001', 'centre_id': FROM_CENTRE,
            'first_name': 'Aarav', 'last_name': 'Sharma', 'contacts': []}
    base.update(over)
    return base


def move_request(**over):
    base = {
        'id': REQUEST_ID, 'child_id': CHILD_ID,
        'from_centre_id': FROM_CENTRE, 'to_centre_id': TO_CENTRE,
        'requested_by': USER_EMAIL, 'requested_by_id': USER_ID,
        'status': PENDING, 'requested_at': '2026-09-04T09:00:00', 'reason': '',
    }
    base.update(over)
    return base


def centre(centre_id, name):
    return {'id': centre_id, 'name': name}


def requesting_access():
    """A centre member allowed to ask for a move, but not to decide one."""
    access = UserAccess(unrestricted=False)
    access.centres[FROM_CENTRE] = {
        'data_scope': 'own', 'role_names': ['Manager'],
        'permissions': {
            'children.view_info': {'visible': True, 'edit': True},
            'children.transfer_sites': {'visible': True, 'edit': True},
        },
    }
    return access


# ── The Global Admin rule, as global_access sees it ─────────────────

SUPER_ADMIN_ROLE = {'id': SUPER_ADMIN_ROLE_ID, 'kind': 'super_admin', 'name': 'Super Admin'}
CENTRE_MANAGER_ROLE = {'id': CENTRE_MANAGER_ROLE_ID, 'kind': 'centre_manager',
                       'name': 'Centre Manager'}


def person(email, role_id, centre_id=None):
    return {
        'id': 'p-' + email, 'name': email, 'email': email,
        'roles': [{'assignment_id': 'a-1', 'role_id': role_id, 'centre_id': centre_id}],
    }


def nobody_is_super_admin(cap_db):
    cap_db.list_roles.return_value = [SUPER_ADMIN_ROLE, CENTRE_MANAGER_ROLE]
    cap_db.list_people.return_value = []


def super_admin_is(cap_db, email):
    cap_db.list_roles.return_value = [SUPER_ADMIN_ROLE, CENTRE_MANAGER_ROLE]
    cap_db.list_people.return_value = [person(email, SUPER_ADMIN_ROLE_ID)]


@patch('children.move_requests.send_move_request_email')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.get_user_access')
class CreateMoveRequestTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _wire(self, access, requests, kids, centres, existing=None):
        access.return_value = requesting_access()
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))
        requests.pending_for_child.return_value = existing
        requests.create_request.return_value = move_request()

    def _post(self, **body):
        payload = {'toCentreId': TO_CENTRE}
        payload.update(body)
        return self.client.post(REQUEST_URL, payload, format='json')

    def test_creates_a_pending_request(self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        mail.return_value = {'sent': True, 'reason': None, 'results': []}

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()['status'], PENDING)
        requests.create_request.assert_called_once()

    def test_the_child_does_not_move(self, access, requests, kids, centres, mail):
        # The whole point of the workflow. Anything written to the child here
        # would make approval a formality after the fact.
        self._wire(access, requests, kids, centres)
        mail.return_value = {'sent': True, 'reason': None, 'results': []}

        self._post()

        kids.update_child.assert_not_called()

    def test_no_invoice_is_touched_when_a_request_is_merely_raised(
            self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        mail.return_value = {'sent': True, 'reason': None, 'results': []}

        with patch('children.move_requests.clear_child_invoices_for_move') as clear:
            self._post()

        clear.assert_not_called()

    def test_the_global_admins_are_emailed(self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        mail.return_value = {'sent': True, 'reason': None, 'results': []}

        res = self._post()

        mail.assert_called_once()
        self.assertTrue(res.json()['adminNotified']['sent'])

    def test_says_so_when_no_admin_could_be_notified(
            self, access, requests, kids, centres, mail):
        # The request stands either way, but a queue nobody has been pointed
        # at is a child waiting indefinitely.
        self._wire(access, requests, kids, centres)
        mail.return_value = {'sent': False, 'reason': 'no_admins', 'results': []}

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.json()['adminNotified']['sent'])
        self.assertEqual(res.json()['adminNotified']['reason'], 'no_admins')

    def test_the_destination_is_required(self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)

        res = self.client.post(REQUEST_URL, {}, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        requests.create_request.assert_not_called()

    def test_a_child_cannot_be_moved_to_the_centre_they_are_already_at(
            self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)

        res = self._post(toCentreId=FROM_CENTRE)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        requests.create_request.assert_not_called()

    def test_a_destination_that_does_not_exist_is_rejected(
            self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        centres.get_centre.side_effect = lambda cid: (
            centre(FROM_CENTRE, 'Indiranagar') if str(cid) == FROM_CENTRE else None)

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        requests.create_request.assert_not_called()

    def test_an_archived_child_is_not_moved(self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        kids.get_child.return_value = child(archived=True)

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        requests.create_request.assert_not_called()

    def test_a_second_request_while_one_is_open_is_a_conflict(
            self, access, requests, kids, centres, mail):
        # Two open requests would have two admins deciding the same move
        # against different destinations.
        self._wire(access, requests, kids, centres, existing=move_request())

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        requests.create_request.assert_not_called()

    def test_another_centres_child_cannot_be_moved(
            self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        kids.get_child.return_value = child(centre_id=OTHER_CENTRE)

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        requests.create_request.assert_not_called()

    def test_a_member_without_transfer_permission_is_refused(
            self, access, requests, kids, centres, mail):
        self._wire(access, requests, kids, centres)
        limited = UserAccess(unrestricted=False)
        limited.centres[FROM_CENTRE] = {
            'data_scope': 'own', 'role_names': ['Teacher'],
            'permissions': {'children.view_info': {'visible': True, 'edit': True}},
        }
        access.return_value = limited

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        requests.create_request.assert_not_called()

    def test_an_anonymous_caller_is_refused(self, access, requests, kids, centres, mail):
        res = APIClient().post(REQUEST_URL, {'toCentreId': TO_CENTRE}, format='json')

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


@patch('children.move_requests.send_move_decision_email')
@patch('children.move_requests.clear_child_invoices_for_move')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.get_user_access')
class ApproveMoveRequestTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        # Root is a Global Admin by role alone — no lookup behind it.
        self.client.force_authenticate(user=FakeUser(email=ADMIN_EMAIL, role='root'))

    def _wire(self, access, requests, kids, centres, request_row=None, child_row=None):
        access.return_value = UserAccess(unrestricted=True)
        requests.get.return_value = request_row if request_row is not None else move_request()
        requests.claim_for_decision.return_value = move_request(status=PROCESSING)
        requests.mark_decided.return_value = move_request(
            status=APPROVED, decided_by=ADMIN_EMAIL)
        kids.get_child.return_value = child_row if child_row is not None else child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))

    def test_the_child_moves_to_the_destination_centre(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.return_value = []

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        kids.update_child.assert_called_once_with(CHILD_ID, {'centre_id': TO_CENTRE})

    def test_the_request_is_marked_approved_with_who_decided_it(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.return_value = []

        self.client.post(APPROVE_URL, {'note': 'Family relocated'}, format='json')

        requests.mark_decided.assert_called_once_with(
            REQUEST_ID, APPROVED, decided_by=ADMIN_EMAIL, decided_by_id=USER_ID,
            note='Family relocated')

    def test_the_old_centres_invoices_come_off_the_child(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.return_value = ['inv-1', 'inv-2']

        res = self.client.post(APPROVE_URL)

        clear.assert_called_once_with(CHILD_ID, FROM_CENTRE, REQUEST_ID)
        self.assertEqual(res.json()['invoicesCleared'], ['inv-1', 'inv-2'])

    def test_the_requesting_centre_is_told(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.return_value = []

        self.client.post(APPROVE_URL)

        self.assertTrue(mail.call_args.kwargs['approved'])

    # ── Only one approval can win ────────────────────────────────────

    def test_a_second_approval_is_refused(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        requests.claim_for_decision.side_effect = MoveRequestConflict('decided')

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        kids.update_child.assert_not_called()
        clear.assert_not_called()

    def test_a_request_that_no_longer_exists_is_not_found(
            self, access, requests, kids, centres, clear, mail):
        access.return_value = UserAccess(unrestricted=True)
        requests.get.return_value = None

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        kids.update_child.assert_not_called()

    def test_a_stale_request_for_a_child_who_has_already_left_is_refused(
            self, access, requests, kids, centres, clear, mail):
        # Approving a move away from a centre the child has already left
        # would send them somewhere nobody asked for.
        self._wire(access, requests, kids, centres, child_row=child(centre_id=OTHER_CENTRE))

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        requests.claim_for_decision.assert_not_called()
        kids.update_child.assert_not_called()

    def test_a_request_whose_child_is_gone_is_refused(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        kids.get_child.return_value = None

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        requests.claim_for_decision.assert_not_called()

    def test_a_destination_that_has_since_closed_is_refused(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        centres.get_centre.side_effect = lambda cid: (
            centre(FROM_CENTRE, 'Indiranagar') if str(cid) == FROM_CENTRE else None)

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        requests.claim_for_decision.assert_not_called()

    # ── All-or-nothing ───────────────────────────────────────────────

    def test_a_failure_clearing_invoices_puts_the_child_back(
            self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.side_effect = RuntimeError('dynamo threw')

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(kids.update_child.call_args_list[-1][0],
                         (CHILD_ID, {'centre_id': FROM_CENTRE}))
        requests.release_claim.assert_called_once_with(REQUEST_ID)
        requests.mark_decided.assert_not_called()

    @patch('children.move_requests.reattach_child_invoices')
    def test_a_failure_after_clearing_puts_the_invoices_back_too(
            self, reattach, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        clear.return_value = ['inv-1', 'inv-2']
        requests.mark_decided.side_effect = RuntimeError('dynamo threw')

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        reattach.assert_called_once_with(CHILD_ID, ['inv-1', 'inv-2'])
        self.assertEqual(kids.update_child.call_args_list[-1][0],
                         (CHILD_ID, {'centre_id': FROM_CENTRE}))
        requests.release_claim.assert_called_once_with(REQUEST_ID)

    # ── Only a Global Admin decides ──────────────────────────────────

    @patch('global_access.capabilities.global_access_db')
    def test_a_centre_member_cannot_approve_even_with_transfer_permission(
            self, cap_db, access, requests, kids, centres, clear, mail):
        nobody_is_super_admin(cap_db)
        self.client.force_authenticate(user=FakeUser())
        access.return_value = requesting_access()

        res = self.client.post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        requests.get.assert_not_called()
        kids.update_child.assert_not_called()

    def test_an_anonymous_caller_is_refused(
            self, access, requests, kids, centres, clear, mail):
        res = APIClient().post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


@patch('children.move_requests.send_move_decision_email')
@patch('children.move_requests.clear_child_invoices_for_move')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.get_user_access')
class RejectMoveRequestTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser(email=ADMIN_EMAIL, role='root'))

    def _wire(self, access, requests, kids, centres):
        access.return_value = UserAccess(unrestricted=True)
        requests.get.return_value = move_request()
        requests.claim_for_decision.return_value = move_request(status=PROCESSING)
        requests.mark_decided.return_value = move_request(
            status=REJECTED, decided_by=ADMIN_EMAIL)
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))

    def test_marks_the_request_rejected(self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)

        res = self.client.post(REJECT_URL, {'note': 'Fees outstanding'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        requests.mark_decided.assert_called_once_with(
            REQUEST_ID, REJECTED, decided_by=ADMIN_EMAIL, decided_by_id=USER_ID,
            note='Fees outstanding')

    def test_the_child_stays_where_they_are(self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)

        self.client.post(REJECT_URL)

        kids.update_child.assert_not_called()

    def test_no_invoice_is_touched(self, access, requests, kids, centres, clear, mail):
        # A rejection is the absence of a change, not a different one.
        self._wire(access, requests, kids, centres)

        self.client.post(REJECT_URL)

        clear.assert_not_called()

    def test_a_second_rejection_is_refused(self, access, requests, kids, centres, clear, mail):
        self._wire(access, requests, kids, centres)
        requests.claim_for_decision.side_effect = MoveRequestConflict('decided')

        res = self.client.post(REJECT_URL)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        requests.mark_decided.assert_not_called()

    @patch('global_access.capabilities.global_access_db')
    def test_a_centre_member_cannot_reject(
            self, cap_db, access, requests, kids, centres, clear, mail):
        nobody_is_super_admin(cap_db)
        self.client.force_authenticate(user=FakeUser())
        access.return_value = requesting_access()

        res = self.client.post(REJECT_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        requests.mark_decided.assert_not_called()


@patch('children.move_requests.send_move_decision_email')
@patch('children.move_requests.clear_child_invoices_for_move')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('global_access.capabilities.global_access_db')
class WhoMayDecideTests(SimpleTestCase):
    """
    Who the approve, reject and queue endpoints let through.

    Being able to see every centre is not the same as being allowed to move
    a child between two of them. Every approved portal user is `admin` and
    unrestricted; only root and the holders of the Super Admin global role
    are Global Admins, and the decision is theirs alone.
    """

    def _wire(self, cap_db, requests, kids, centres, clear):
        requests.get.return_value = move_request()
        requests.list_by_status.return_value = []
        requests.claim_for_decision.return_value = move_request(status=PROCESSING)
        requests.mark_decided.return_value = move_request(status=APPROVED)
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))
        clear.return_value = []

    def _as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _every_decision(self, client):
        return [
            client.post(APPROVE_URL).status_code,
            client.post(REJECT_URL).status_code,
            client.get(QUEUE_URL).status_code,
        ]

    def test_root_may_decide(self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        nobody_is_super_admin(cap_db)

        codes = self._every_decision(self._as(FakeUser(email=ADMIN_EMAIL, role='root')))

        self.assertNotIn(status.HTTP_403_FORBIDDEN, codes)
        # Root never needs the directory looked up.
        cap_db.list_people.assert_not_called()

    def test_a_super_admin_may_decide(self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        super_admin_is(cap_db, ADMIN_EMAIL)

        codes = self._every_decision(self._as(FakeUser(email=ADMIN_EMAIL, role='admin')))

        self.assertNotIn(status.HTTP_403_FORBIDDEN, codes)

    def test_the_address_match_ignores_case_and_spacing(
            self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        super_admin_is(cap_db, ' Admin@Shichida.LOCAL ')

        res = self._as(FakeUser(email=ADMIN_EMAIL, role='admin')).post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_an_ordinary_portal_admin_may_not(
            self, cap_db, requests, kids, centres, clear, mail):
        # `admin` is every approved portal user — a centre owner, say. They
        # are unrestricted, and that is exactly why this must not be enough.
        self._wire(cap_db, requests, kids, centres, clear)
        nobody_is_super_admin(cap_db)

        codes = self._every_decision(self._as(FakeUser(email=ADMIN_EMAIL, role='admin')))

        self.assertEqual(codes, [status.HTTP_403_FORBIDDEN] * 3)
        kids.update_child.assert_not_called()
        requests.mark_decided.assert_not_called()

    def test_a_centre_manager_may_not(self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        cap_db.list_roles.return_value = [SUPER_ADMIN_ROLE, CENTRE_MANAGER_ROLE]
        cap_db.list_people.return_value = [person(ADMIN_EMAIL, CENTRE_MANAGER_ROLE_ID)]

        codes = self._every_decision(self._as(FakeUser(email=ADMIN_EMAIL, role='admin')))

        self.assertEqual(codes, [status.HTTP_403_FORBIDDEN] * 3)
        kids.update_child.assert_not_called()

    def test_super_admin_scoped_to_one_centre_is_not_global(
            self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        cap_db.list_roles.return_value = [SUPER_ADMIN_ROLE]
        cap_db.list_people.return_value = [
            person(ADMIN_EMAIL, SUPER_ADMIN_ROLE_ID, centre_id=FROM_CENTRE)]

        res = self._as(FakeUser(email=ADMIN_EMAIL, role='admin')).post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_a_role_named_global_admin_counts_without_a_kind(
            self, cap_db, requests, kids, centres, clear, mail):
        # An environment whose Super Admin role predates the seed command
        # carries no `kind`; the name is the fallback.
        self._wire(cap_db, requests, kids, centres, clear)
        cap_db.list_roles.return_value = [{'id': 'r-x', 'name': 'Global Admin'}]
        cap_db.list_people.return_value = [person(ADMIN_EMAIL, 'r-x')]

        res = self._as(FakeUser(email=ADMIN_EMAIL, role='admin')).post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_a_failed_lookup_is_a_denial(self, cap_db, requests, kids, centres, clear, mail):
        self._wire(cap_db, requests, kids, centres, clear)
        cap_db.list_roles.side_effect = RuntimeError('dynamo down')

        res = self._as(FakeUser(email=ADMIN_EMAIL, role='admin')).post(APPROVE_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        kids.update_child.assert_not_called()


@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.get_user_access')
class MoveRequestQueueTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser(email=ADMIN_EMAIL, role='root'))

    def _wire(self, access, requests, kids, centres):
        access.return_value = UserAccess(unrestricted=True)
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))

    def test_the_queue_defaults_to_what_is_still_outstanding(
            self, access, requests, kids, centres):
        self._wire(access, requests, kids, centres)
        requests.list_by_status.side_effect = lambda s: (
            [move_request()] if s == PENDING else [])

        res = self.client.get(QUEUE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # A request being decided right now is still outstanding.
        self.assertEqual(
            [c[0][0] for c in requests.list_by_status.call_args_list],
            [PENDING, PROCESSING])

    def test_names_the_child_and_both_centres(self, access, requests, kids, centres):
        self._wire(access, requests, kids, centres)
        requests.list_by_status.side_effect = lambda s: (
            [move_request()] if s == PENDING else [])

        row = self.client.get(QUEUE_URL).json()[0]

        self.assertEqual(row['childName'], 'Aarav Sharma')
        self.assertEqual(row['fromCentreName'], 'Indiranagar')
        self.assertEqual(row['toCentreName'], 'Koramangala')

    def test_everything_can_be_asked_for(self, access, requests, kids, centres):
        self._wire(access, requests, kids, centres)
        requests.list_all.return_value = [move_request(status=APPROVED)]

        res = self.client.get(f'{QUEUE_URL}?status=all')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        requests.list_all.assert_called_once()

    def test_an_unknown_status_is_rejected(self, access, requests, kids, centres):
        self._wire(access, requests, kids, centres)

        res = self.client.get(f'{QUEUE_URL}?status=maybe')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('global_access.capabilities.global_access_db')
    def test_a_centre_member_cannot_read_the_admin_queue(
            self, cap_db, access, requests, kids, centres):
        nobody_is_super_admin(cap_db)
        self.client.force_authenticate(user=FakeUser())
        access.return_value = requesting_access()

        res = self.client.get(QUEUE_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


# ── Deciding from the email ─────────────────────────────────────────


def token_for(email=ADMIN_EMAIL, request_id=REQUEST_ID):
    return make_move_action_token(request_id, email)


@patch('children.move_requests.auth_db')
@patch('global_access.capabilities.auth_db')
@patch('global_access.capabilities.global_access_db')
@patch('children.move_requests.old_centre_invoices')
@patch('children.move_requests.send_move_decision_email')
@patch('children.move_requests.clear_child_invoices_for_move')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
class EmailActionTests(SimpleTestCase):
    """
    The Approve / Reject buttons in the email.

    There is no session. The signed token in the link is the whole
    credential, so what it must prove is: this site issued it, recently,
    for this request, to an address that is a Global Admin right now. GET
    only describes the request — that is what a mail scanner fetches — and
    only a POST with an explicit action decides anything.
    """

    def setUp(self):
        # Deliberately not authenticated: the link works from any browser.
        self.client = APIClient()

    def _wire(self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth,
              auth, request_row=None):
        requests.get.return_value = request_row if request_row is not None else move_request()
        requests.claim_for_decision.return_value = move_request(status=PROCESSING)
        requests.mark_decided.side_effect = lambda pk, st, **kw: move_request(
            status=st, decided_by=kw.get('decided_by'), decision_note=kw.get('note'))
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))
        clear.return_value = []
        invoices.return_value = [{'id': 'inv-1'}, {'id': 'inv-2'}]
        # The recipient is root in auth_db; nobody holds Super Admin.
        cap_auth.list_by_role.return_value = [
            {'id': USER_ID, 'email': ADMIN_EMAIL, 'status': 'approved', 'role': 'root'}]
        nobody_is_super_admin(cap_db)
        auth.get_user_by_email.return_value = {'id': USER_ID, 'email': ADMIN_EMAIL}

    # ── GET: what the link is about ──────────────────────────────────

    def test_get_describes_the_move_without_deciding_it(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        res = self.client.get(EMAIL_ACTION_URL, {'token': token_for()})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertEqual(body['childName'], 'Aarav Sharma')
        self.assertEqual(body['fromCentreName'], 'Indiranagar')
        self.assertEqual(body['toCentreName'], 'Koramangala')
        self.assertEqual(body['status'], PENDING)
        self.assertEqual(body['deciderEmail'], ADMIN_EMAIL)
        self.assertEqual(body['invoiceCount'], 2)
        # A scanner following the link changes nothing.
        requests.claim_for_decision.assert_not_called()
        requests.mark_decided.assert_not_called()
        kids.update_child.assert_not_called()

    def test_get_reports_a_decision_already_made(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth,
                   request_row=move_request(status=APPROVED, decided_by='other@shichida.local',
                                            decided_at='2026-09-05T10:00:00'))

        body = self.client.get(EMAIL_ACTION_URL, {'token': token_for()}).json()

        self.assertEqual(body['status'], APPROVED)
        self.assertEqual(body['decidedBy'], 'other@shichida.local')

    # ── The token ────────────────────────────────────────────────────

    def test_a_missing_token_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        res = self.client.get(EMAIL_ACTION_URL)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['reason'], 'missing_token')

    def test_a_tampered_token_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        forged = token_for()[:-4] + 'AAAA'

        res = self.client.post(EMAIL_ACTION_URL, {'token': forged, 'action': 'approve'},
                               format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['reason'], 'invalid')
        kids.update_child.assert_not_called()

    def test_a_token_signed_for_another_purpose_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        from django.core import signing
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        other = signing.dumps({'move_request_id': REQUEST_ID, 'email': ADMIN_EMAIL},
                              salt='something-else')

        res = self.client.get(EMAIL_ACTION_URL, {'token': other})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['reason'], 'invalid')

    def test_an_expired_token_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        with patch('notifications.tokens.MOVE_ACTION_MAX_AGE', -1):
            res = self.client.post(EMAIL_ACTION_URL,
                                   {'token': token_for(), 'action': 'approve'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_410_GONE)
        self.assertEqual(res.json()['reason'], 'expired')
        kids.update_child.assert_not_called()

    def test_a_token_for_someone_who_is_not_a_global_admin_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        # Checked when the link is used, not when it was sent: a Super Admin
        # removed from the role after the email went out cannot still decide.
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        cap_auth.list_by_role.return_value = []

        res = self.client.post(EMAIL_ACTION_URL,
                               {'token': token_for(), 'action': 'approve'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.json()['reason'], 'not_global_admin')
        kids.update_child.assert_not_called()

    def test_a_centre_managers_token_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        cap_auth.list_by_role.return_value = []
        cap_db.list_people.return_value = [person(USER_EMAIL, CENTRE_MANAGER_ROLE_ID)]

        res = self.client.post(EMAIL_ACTION_URL,
                               {'token': token_for(email=USER_EMAIL), 'action': 'approve'},
                               format='json')

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_a_super_admins_token_is_accepted(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        cap_auth.list_by_role.return_value = []
        super_admin_is(cap_db, 'super@shichida.local')

        res = self.client.get(EMAIL_ACTION_URL, {'token': token_for(email='super@shichida.local')})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_a_token_for_a_request_that_is_gone_is_not_found(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        requests.get.return_value = None

        res = self.client.get(EMAIL_ACTION_URL, {'token': token_for()})

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_stale_authorization_header_does_not_break_the_link(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        # The admin's browser may still hold an expired portal token. The
        # link must not turn into a 401 because of it.
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        res = self.client.get(EMAIL_ACTION_URL, {'token': token_for()},
                              HTTP_AUTHORIZATION='Bearer not.a.real.token')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # ── POST: the decision ───────────────────────────────────────────

    def test_approving_from_the_email_moves_the_child(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        clear.return_value = ['inv-1', 'inv-2']

        res = self.client.post(EMAIL_ACTION_URL,
                               {'token': token_for(), 'action': 'approve',
                                'note': 'Confirmed by phone'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        kids.update_child.assert_called_once_with(CHILD_ID, {'centre_id': TO_CENTRE})
        clear.assert_called_once_with(CHILD_ID, FROM_CENTRE, REQUEST_ID)
        self.assertEqual(res.json()['invoicesCleared'], ['inv-1', 'inv-2'])
        self.assertEqual(res.json()['moveRequest']['status'], APPROVED)

    def test_the_decision_is_recorded_against_the_recipient_as_from_email(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        self.client.post(EMAIL_ACTION_URL,
                         {'token': token_for(), 'action': 'approve', 'note': 'ok'},
                         format='json')

        requests.mark_decided.assert_called_once_with(
            REQUEST_ID, APPROVED, decided_by=f'{ADMIN_EMAIL} (Email)',
            decided_by_id=USER_ID, note='ok')

    def test_a_recipient_without_a_portal_login_is_still_recorded(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        auth.get_user_by_email.return_value = None

        self.client.post(EMAIL_ACTION_URL, {'token': token_for(), 'action': 'approve'},
                         format='json')

        self.assertEqual(requests.mark_decided.call_args.kwargs['decided_by'],
                         f'{ADMIN_EMAIL} (Email)')
        self.assertEqual(requests.mark_decided.call_args.kwargs['decided_by_id'], '')

    def test_the_requesting_centre_is_told_of_an_email_approval(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        self.client.post(EMAIL_ACTION_URL, {'token': token_for(), 'action': 'approve'},
                         format='json')

        self.assertTrue(mail.call_args.kwargs['approved'])

    def test_rejecting_from_the_email_changes_nothing(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        res = self.client.post(EMAIL_ACTION_URL,
                               {'token': token_for(), 'action': 'reject',
                                'note': 'Fees outstanding'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['moveRequest']['status'], REJECTED)
        kids.update_child.assert_not_called()
        clear.assert_not_called()
        requests.mark_decided.assert_called_once_with(
            REQUEST_ID, REJECTED, decided_by=f'{ADMIN_EMAIL} (Email)',
            decided_by_id=USER_ID, note='Fees outstanding')
        self.assertFalse(mail.call_args.kwargs['approved'])

    def test_an_unknown_action_is_refused(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)

        res = self.client.post(EMAIL_ACTION_URL, {'token': token_for(), 'action': 'maybe'},
                               format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        requests.claim_for_decision.assert_not_called()

    def test_a_request_already_decided_is_a_conflict(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        # Two admins each got an email; the second to click is told, not
        # silently ignored, and the child is not moved twice.
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        requests.claim_for_decision.side_effect = MoveRequestConflict('decided')

        res = self.client.post(EMAIL_ACTION_URL, {'token': token_for(), 'action': 'approve'},
                               format='json')

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        kids.update_child.assert_not_called()

    def test_a_failure_partway_is_rolled_back_for_email_approvals_too(
            self, requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth):
        self._wire(requests, kids, centres, clear, mail, invoices, cap_db, cap_auth, auth)
        clear.side_effect = RuntimeError('dynamo threw')

        res = self.client.post(EMAIL_ACTION_URL, {'token': token_for(), 'action': 'approve'},
                               format='json')

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(kids.update_child.call_args_list[-1][0],
                         (CHILD_ID, {'centre_id': FROM_CENTRE}))
        requests.release_claim.assert_called_once_with(REQUEST_ID)


@patch('children.move_requests.old_centre_invoices')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.get_user_access')
class MovePreviewTests(SimpleTestCase):
    """What a move would affect, before anyone commits to asking for one."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def test_lists_the_invoices_that_would_come_off_the_child(
            self, access, kids, requests, centres, invoices):
        access.return_value = requesting_access()
        kids.get_child.return_value = child()
        requests.pending_for_child.return_value = None
        invoices.return_value = [{'id': 'inv-1', 'number': 'BA260001',
                                  'total_amount': '5900'}]

        res = self.client.get(PREVIEW_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['invoiceCount'], 1)
        self.assertEqual(res.json()['invoices'][0]['number'], 'BA260001')

    def test_previewing_changes_nothing(self, access, kids, requests, centres, invoices):
        access.return_value = requesting_access()
        kids.get_child.return_value = child()
        requests.pending_for_child.return_value = None
        invoices.return_value = []

        self.client.get(PREVIEW_URL)

        kids.update_child.assert_not_called()
        requests.create_request.assert_not_called()

    def test_another_centres_child_cannot_be_previewed(
            self, access, kids, requests, centres, invoices):
        access.return_value = requesting_access()
        kids.get_child.return_value = child(centre_id=OTHER_CENTRE)

        res = self.client.get(PREVIEW_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


@patch('children.move_requests.old_centre_invoices')
@patch('children.move_requests.centres_db')
@patch('children.move_requests.children_db')
@patch('children.move_requests.move_requests_db')
@patch('children.move_requests.get_user_access')
class UnprovisionedEnvironmentTests(SimpleTestCase):
    """
    What happens before anyone has run create_dynamo_tables.

    The move-requests table is new, so an environment upgraded without it
    answered every one of these with a bare 500 whose body said only "Server
    Error". An environment missing a table is not a broken request, and the
    person hitting it should be told which command fixes it.
    """

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser(email=ADMIN_EMAIL, role='root'))

    def _missing(self, requests):
        requests.get.side_effect = MoveRequestsUnavailable('no table')
        requests.list_all.side_effect = MoveRequestsUnavailable('no table')
        requests.list_by_status.side_effect = MoveRequestsUnavailable('no table')
        requests.list_for_child.side_effect = MoveRequestsUnavailable('no table')
        requests.pending_for_child.side_effect = MoveRequestsUnavailable('no table')
        requests.create_request.side_effect = MoveRequestsUnavailable('no table')

    def test_the_admin_queue_says_what_to_run(
            self, access, requests, kids, centres, invoices):
        access.return_value = UserAccess(unrestricted=True)
        self._missing(requests)

        res = self.client.get(QUEUE_URL)

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('create_dynamo_tables', res.json()['detail'])

    def test_raising_a_request_says_what_to_run(
            self, access, requests, kids, centres, invoices):
        access.return_value = requesting_access()
        self.client.force_authenticate(user=FakeUser())
        self._missing(requests)
        kids.get_child.return_value = child()
        centres.get_centre.side_effect = lambda cid: {
            FROM_CENTRE: centre(FROM_CENTRE, 'Indiranagar'),
            TO_CENTRE: centre(TO_CENTRE, 'Koramangala'),
        }.get(str(cid))

        res = self.client.post(REQUEST_URL, {'toCentreId': TO_CENTRE}, format='json')

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res.json()['reason'], 'not_provisioned')

    def test_deciding_says_what_to_run(self, access, requests, kids, centres, invoices):
        access.return_value = UserAccess(unrestricted=True)
        self._missing(requests)

        for url in (APPROVE_URL, REJECT_URL):
            with self.subTest(url=url):
                res = self.client.post(url)
                self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch('global_access.capabilities.auth_db')
    @patch('global_access.capabilities.global_access_db')
    def test_the_email_link_says_what_to_run(
            self, cap_db, cap_auth, access, requests, kids, centres, invoices):
        cap_auth.list_by_role.return_value = [
            {'email': ADMIN_EMAIL, 'status': 'approved', 'role': 'root'}]
        nobody_is_super_admin(cap_db)
        self._missing(requests)

        res = APIClient().get(EMAIL_ACTION_URL, {'token': token_for()})

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_the_preview_still_opens(self, access, requests, kids, centres, invoices):
        # This is the one the centre hits just by opening Transfer Center. The
        # invoice figures are true whether or not the table exists, so the
        # dialog opens and reports what it could not determine.
        access.return_value = requesting_access()
        self.client.force_authenticate(user=FakeUser())
        self._missing(requests)
        kids.get_child.return_value = child()
        invoices.return_value = [{'id': 'i1', 'number': 'BA260001',
                                  'total_amount': '5900'}]

        res = self.client.get(PREVIEW_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['invoiceCount'], 1)
        self.assertIsNone(res.json()['pendingRequest'])
        self.assertFalse(res.json()['moveRequestsAvailable'])
