"""
The move-request email: who gets it, and what they can do from it.

Who: Global Admins only — root, and holders of the Super Admin global role.
Not centre managers, not centre-scoped staff, and not the ordinary `admin`
portal users who run a centre. The recipients are resolved from the same
rule the approve endpoint enforces, so nobody is told about a move they
cannot decide, and nobody who can decide is left out.

What: an Approve and a Reject link, each carrying a token signed for that
recipient and that request, pointing at a confirmation page rather than at
the API — a mail scanner following the link must not be able to decide.

Everything DynamoDB-shaped is patched where it is looked up, so no network
call is made and no real email is sent.
"""
import html
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlparse

from django.core import signing
from django.test import SimpleTestCase, override_settings

from notifications import mailer
from notifications.tokens import MOVE_ACTION_SALT, read_move_action_token

CENTRE_A = "22222222-2222-2222-2222-222222222222"
CENTRE_B = "88888888-8888-8888-8888-888888888888"
REQUEST_ID = "44444444-4444-4444-4444-444444444444"
SUPER_ADMIN_ROLE_ID = "66666666-6666-6666-6666-666666666666"
CENTRE_MANAGER_ROLE_ID = "77777777-7777-7777-7777-777777777777"
AFFILIATE_ROLE_ID = "99999999-9999-9999-9999-999999999999"

SUPER_ADMIN_ROLE = {'id': SUPER_ADMIN_ROLE_ID, 'kind': 'super_admin', 'name': 'Super Admin'}
CENTRE_MANAGER_ROLE = {'id': CENTRE_MANAGER_ROLE_ID, 'kind': 'centre_manager',
                       'name': 'Centre Manager'}
AFFILIATE_ROLE = {'id': AFFILIATE_ROLE_ID, 'kind': 'affiliate', 'name': 'Affiliate'}
ALL_ROLES = [SUPER_ADMIN_ROLE, CENTRE_MANAGER_ROLE, AFFILIATE_ROLE]


def person(email, *assignments):
    return {
        'id': 'p-' + email, 'name': email, 'email': email,
        'roles': [
            {'assignment_id': f'a-{i}', 'role_id': role_id, 'centre_id': centre_id}
            for i, (role_id, centre_id) in enumerate(assignments)
        ],
    }


def root_user(email, status='approved'):
    return {'id': 'u-' + email, 'email': email, 'role': 'root', 'status': status}


def move_request(**over):
    base = {
        'id': REQUEST_ID, 'child_id': 'kid-1', 'from_centre_id': CENTRE_A,
        'to_centre_id': CENTRE_B, 'requested_by': 'manager@shichida.local',
        'requested_at': '2026-09-04T09:00:00', 'reason': 'Family relocating',
        'status': 'pending',
    }
    base.update(over)
    return base


CHILD = {'id': 'kid-1', 'system_id': 'CHD-001', 'first_name': 'Aarav', 'last_name': 'Sharma'}
FROM_CENTRE = {'id': CENTRE_A, 'name': 'Indiranagar'}
TO_CENTRE = {'id': CENTRE_B, 'name': 'Koramangala'}


# =============================================================================
# get_global_admin_emails
# =============================================================================

@patch('global_access.capabilities.global_access_db')
@patch('global_access.capabilities.auth_db')
class GlobalAdminEmailsTests(SimpleTestCase):
    def test_super_admins_only(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = [root_user('root@shichida.local')]
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            person('super@shichida.local', (SUPER_ADMIN_ROLE_ID, None)),
            person('centremgr@shichida.local', (CENTRE_MANAGER_ROLE_ID, None)),
            person('affiliate@shichida.local', (AFFILIATE_ROLE_ID, None)),
        ]

        emails = mailer.get_global_admin_emails()

        self.assertEqual(emails, {'super@shichida.local'})

    def test_a_centre_manager_is_excluded_even_with_other_roles(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = []
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            person('centremgr@shichida.local',
                   (CENTRE_MANAGER_ROLE_ID, CENTRE_A), (AFFILIATE_ROLE_ID, None)),
        ]

        self.assertEqual(mailer.get_global_admin_emails(), set())

    def test_super_admin_scoped_to_a_centre_is_not_global(self, auth_db, cap_db):
        # Centre-level access, whatever the role is called.
        auth_db.list_by_role.return_value = []
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            person('scoped@shichida.local', (SUPER_ADMIN_ROLE_ID, CENTRE_A)),
        ]

        self.assertEqual(mailer.get_global_admin_emails(), set())

    def test_someone_holding_super_admin_and_centre_manager_counts(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = []
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            person('both@shichida.local',
                   (CENTRE_MANAGER_ROLE_ID, CENTRE_A), (SUPER_ADMIN_ROLE_ID, None)),
        ]

        self.assertEqual(mailer.get_global_admin_emails(), {'both@shichida.local'})

    def test_root_is_excluded(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = [
            root_user('pending@shichida.local', status='pending'),
            root_user('root@shichida.local'),
        ]
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = []

        self.assertEqual(mailer.get_global_admin_emails(), set())

    def test_addresses_are_normalised(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = [root_user(' Root@Shichida.LOCAL ')]
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            person('Super@Shichida.Local', (SUPER_ADMIN_ROLE_ID, None)),
        ]

        self.assertEqual(mailer.get_global_admin_emails(), {'super@shichida.local'})

    def test_a_role_named_global_admin_without_a_kind_counts(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = []
        cap_db.list_roles.return_value = [{'id': 'r-x', 'name': 'Global Admin'}]
        cap_db.list_people.return_value = [person('ga@shichida.local', ('r-x', None))]

        self.assertEqual(mailer.get_global_admin_emails(), {'ga@shichida.local'})

    def test_the_old_admin_portal_role_does_not_count(self, auth_db, cap_db):
        # `admin` is every approved portal user. They used to be told; they
        # must not be any more.
        auth_db.list_by_role.return_value = []
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = []

        mailer.get_global_admin_emails()

        for call in auth_db.list_by_role.call_args_list:
            self.assertNotEqual(call.args, ('admin',))

    def test_people_without_an_address_are_skipped(self, auth_db, cap_db):
        auth_db.list_by_role.return_value = [{'role': 'root', 'status': 'approved'}]
        cap_db.list_roles.return_value = ALL_ROLES
        cap_db.list_people.return_value = [
            {'id': 'p-1', 'name': 'No Email', 'email': None,
             'roles': [{'role_id': SUPER_ADMIN_ROLE_ID, 'centre_id': None}]},
        ]

        self.assertEqual(mailer.get_global_admin_emails(), set())


# =============================================================================
# send_move_request_email
# =============================================================================

def links_in(message):
    """Every child-moves action URL in a message body, keyed by action."""
    found = {}
    # The HTML body escapes & as &amp; inside href attributes, as it should.
    for word in html.unescape(message).replace('"', ' ').replace('>', ' ').split():
        if '/child-moves/action?' in word:
            parsed = urlparse(word)
            query = parse_qs(parsed.query)
            found[query['action'][0]] = {
                'url': word, 'path': parsed.path, 'token': unquote(query['token'][0]),
            }
    return found


@override_settings(FRONTEND_URL='https://portal.example.test/')
@patch('notifications.mailer.send_mail')
@patch('notifications.mailer.get_global_admin_emails')
class SendMoveRequestEmailTests(SimpleTestCase):
    def _send(self, admins, send_mail, emails=frozenset({'root@shichida.local'})):
        admins.return_value = set(emails)
        return mailer.send_move_request_email(move_request(), CHILD, FROM_CENTRE, TO_CENTRE)

    def test_goes_to_the_global_admins_only(self, admins, send_mail):
        self._send(admins, send_mail,
                   emails={'root@shichida.local', 'super@shichida.local'})

        recipients = {c.kwargs['recipient_list'][0] for c in send_mail.call_args_list}
        self.assertEqual(recipients, {'root@shichida.local', 'super@shichida.local'})
        for call in send_mail.call_args_list:
            self.assertEqual(len(call.kwargs['recipient_list']), 1)

    def test_reports_when_there_is_nobody_to_tell(self, admins, send_mail):
        result = self._send(admins, send_mail, emails=set())

        self.assertEqual(result, {'sent': False, 'reason': 'no_admins', 'results': []})
        send_mail.assert_not_called()

    def test_carries_approve_and_reject_links_to_the_confirmation_page(
            self, admins, send_mail):
        self._send(admins, send_mail)

        call = send_mail.call_args
        for body in (call.kwargs['message'], call.kwargs['html_message']):
            links = links_in(body)
            self.assertEqual(set(links), {'approve', 'reject'})
            for link in links.values():
                self.assertTrue(link['url'].startswith('https://portal.example.test/child-moves/action?'))
                self.assertEqual(link['path'], '/child-moves/action')

    def test_the_html_has_the_two_buttons(self, admins, send_mail):
        self._send(admins, send_mail)

        html = send_mail.call_args.kwargs['html_message']
        self.assertIn('Approve Transfer', html)
        self.assertIn('Reject Transfer', html)
        self.assertIn('#2e7d32', html)  # green
        self.assertIn('#c62828', html)  # red

    def test_the_token_names_the_request_and_the_recipient(self, admins, send_mail):
        self._send(admins, send_mail)

        links = links_in(send_mail.call_args.kwargs['message'])
        payload = read_move_action_token(links['approve']['token'])
        self.assertEqual(payload, {'move_request_id': REQUEST_ID,
                                   'email': 'root@shichida.local'})
        # Same token for both buttons: the action is chosen on the page.
        self.assertEqual(links['approve']['token'], links['reject']['token'])

    def test_each_recipient_gets_their_own_token(self, admins, send_mail):
        self._send(admins, send_mail,
                   emails={'root@shichida.local', 'super@shichida.local'})

        by_recipient = {
            c.kwargs['recipient_list'][0]: links_in(c.kwargs['message'])['approve']['token']
            for c in send_mail.call_args_list
        }
        self.assertNotEqual(by_recipient['root@shichida.local'],
                            by_recipient['super@shichida.local'])
        for email, token in by_recipient.items():
            self.assertEqual(read_move_action_token(token)['email'], email)

    def test_the_token_is_signed_for_this_purpose_only(self, admins, send_mail):
        self._send(admins, send_mail)

        token = links_in(send_mail.call_args.kwargs['message'])['approve']['token']
        with self.assertRaises(signing.BadSignature):
            signing.loads(token, salt='another-purpose')
        with self.assertRaises(signing.BadSignature):
            signing.loads(token[:-3] + 'xyz', salt=MOVE_ACTION_SALT)

    def test_describes_the_move(self, admins, send_mail):
        self._send(admins, send_mail)

        call = send_mail.call_args
        self.assertIn('Aarav Sharma', call.kwargs['subject'])
        self.assertIn('Koramangala', call.kwargs['subject'])
        for body in (call.kwargs['message'], call.kwargs['html_message']):
            self.assertIn('Aarav Sharma', body)
            self.assertIn('CHD-001', body)
            self.assertIn('Indiranagar', body)
            self.assertIn('Koramangala', body)
            self.assertIn('Family relocating', body)
            self.assertIn('manager@shichida.local', body)

    def test_user_supplied_text_is_escaped_in_the_html(self, admins, send_mail):
        admins.return_value = {'root@shichida.local'}
        mailer.send_move_request_email(
            move_request(reason='<script>alert(1)</script>'), CHILD, FROM_CENTRE, TO_CENTRE)

        html = send_mail.call_args.kwargs['html_message']
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_one_failed_recipient_does_not_block_the_rest(self, admins, send_mail):
        def flaky(**kwargs):
            if kwargs['recipient_list'] == ['root@shichida.local']:
                raise Exception('MessageRejected')
        send_mail.side_effect = flaky

        result = self._send(admins, send_mail,
                            emails={'root@shichida.local', 'super@shichida.local'})

        self.assertTrue(result['sent'])
        self.assertEqual(send_mail.call_count, 2)
        statuses = {r['email']: r['status'] for r in result['results']}
        self.assertEqual(statuses, {'root@shichida.local': 'failed',
                                    'super@shichida.local': 'sent'})

    def test_says_so_when_every_send_failed(self, admins, send_mail):
        send_mail.side_effect = Exception('SMTP down')

        result = self._send(admins, send_mail)

        self.assertFalse(result['sent'])
        self.assertEqual(result['reason'], 'all_failed')


# =============================================================================
# send_move_decision_email
# =============================================================================

@patch('notifications.mailer.send_mail')
@patch('notifications.mailer.get_global_admin_emails')
class SendMoveDecisionEmailTests(SimpleTestCase):
    def test_tells_the_global_admins_only(
            self, admins, send_mail):
        admins.return_value = {'root@shichida.local'}

        mailer.send_move_decision_email(
            move_request(status='approved', decided_by='root@shichida.local (Email)'),
            CHILD, FROM_CENTRE, TO_CENTRE, approved=True)

        recipients = {c.kwargs['recipient_list'][0] for c in send_mail.call_args_list}
        self.assertEqual(recipients, {'root@shichida.local'})
        message = send_mail.call_args.kwargs['message']
        self.assertIn('approved', message)
        self.assertIn('root@shichida.local (Email)', message)
