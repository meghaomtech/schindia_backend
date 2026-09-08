"""
Unit tests for notifications/mailer.py.

Same approach as the other apps' suites: SimpleTestCase, dynamo_backend.services and
django's send_mail mocked at the point they're imported into notifications.mailer, so
no AWS/network calls happen and no real email is sent (Django's test runner also swaps
EMAIL_BACKEND for locmem, but these tests mock send_mail directly for precise assertions
on recipients/subject).
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from notifications import mailer

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
CHILD_ID = "11111111-1111-1111-1111-111111111111"
ROLE_ID = "33333333-3333-3333-3333-333333333333"


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


def child_with_contacts(contacts=None, centre_id=CENTRE_ID):
    return {
        'id': CHILD_ID,
        'first_name': 'Kid',
        'last_name': 'One',
        'centre_id': centre_id,
        'contacts': contacts if contacts is not None else [
            {'invite_as': 'Parent', 'email': 'parent@example.com', 'name': 'Pat Parent'},
        ],
    }


# =============================================================================
# get_centre_admin_emails
# =============================================================================

@patch('notifications.mailer.roles_db')
@patch('notifications.mailer.centres_db')
class CentreAdminEmailsTests(SimpleTestCase):
    def test_combines_manager_and_admin_role_members(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {
            'id': CENTRE_ID, 'manager': {'email': 'manager@example.com'},
        }
        mock_roles_db.list_roles.return_value = [
            admin_role(members=[{'email': 'admin1@example.com'}, {'email': 'admin2@example.com'}]),
            basic_role(members=[{'email': 'teacher@example.com'}]),
        ]

        emails = mailer.get_centre_admin_emails(CENTRE_ID)

        self.assertEqual(emails, {'manager@example.com', 'admin1@example.com', 'admin2@example.com'})

    def test_no_manager_and_no_admin_roles_returns_empty(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = [basic_role()]

        emails = mailer.get_centre_admin_emails(CENTRE_ID)

        self.assertEqual(emails, set())

    def test_centre_not_found_still_checks_admin_roles(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = None
        mock_roles_db.list_roles.return_value = [admin_role(members=[{'email': 'admin@example.com'}])]

        emails = mailer.get_centre_admin_emails(CENTRE_ID)

        self.assertEqual(emails, {'admin@example.com'})

    def test_members_without_email_are_skipped(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = [admin_role(members=[{'name': 'No Email'}])]

        emails = mailer.get_centre_admin_emails(CENTRE_ID)

        self.assertEqual(emails, set())


# =============================================================================
# send_enrolment_added_email / send_enrolment_removed_email
# =============================================================================

@patch('notifications.mailer.send_mail')
@patch('notifications.mailer.roles_db')
@patch('notifications.mailer.centres_db')
class EnrolmentEmailTests(SimpleTestCase):
    def _no_admins(self, mock_centres_db, mock_roles_db):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = []

    def test_added_email_goes_to_parent_only(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': {'email': 'manager@example.com'}}
        mock_roles_db.list_roles.return_value = []
        child = child_with_contacts()
        slot = {'day': 'mon', 'start_time': '10:00', 'room_id': 'room-1'}
        session = {'name': 'Morning Session'}
        centre = {'id': CENTRE_ID, 'name': 'Centre A'}
        room = {'name': 'Room 1'}

        mailer.send_enrolment_added_email(child, slot, session, centre, room=room)

        recipients = {c.kwargs['recipient_list'][0] for c in mock_send_mail.call_args_list}
        self.assertEqual(recipients, {'parent@example.com'})
        subject = mock_send_mail.call_args_list[0].kwargs['subject']
        self.assertIn('New session scheduled', subject)
        self.assertIn('Kid One', subject)
        message = mock_send_mail.call_args_list[0].kwargs['message']
        self.assertIn('Morning Session', message)
        self.assertIn('Room 1', message)
        self.assertIn('Centre A', message)

    def test_added_email_no_recipients_sends_nothing(self, mock_centres_db, mock_roles_db, mock_send_mail):
        self._no_admins(mock_centres_db, mock_roles_db)
        child = child_with_contacts(contacts=[])

        mailer.send_enrolment_added_email(child, None, None, {'id': CENTRE_ID, 'name': 'Centre A'})

        mock_send_mail.assert_not_called()

    def test_removed_email_reason_removed(self, mock_centres_db, mock_roles_db, mock_send_mail):
        self._no_admins(mock_centres_db, mock_roles_db)
        child = child_with_contacts()

        mailer.send_enrolment_removed_email(
            child, {'day': 'tue', 'start_time': '11:00'}, {'name': 'Afternoon'},
            {'id': CENTRE_ID, 'name': 'Centre A'}, reason='removed',
        )

        subject = mock_send_mail.call_args.kwargs['subject']
        message = mock_send_mail.call_args.kwargs['message']
        self.assertIn('Session removed', subject)
        self.assertIn('removed from a session', message)

    def test_removed_email_reason_rescheduled(self, mock_centres_db, mock_roles_db, mock_send_mail):
        self._no_admins(mock_centres_db, mock_roles_db)
        child = child_with_contacts()

        mailer.send_enrolment_removed_email(
            child, {'day': 'wed', 'start_time': '09:00'}, {'name': 'Morning'},
            {'id': CENTRE_ID, 'name': 'Centre A'}, reason='rescheduled',
        )

        subject = mock_send_mail.call_args.kwargs['subject']
        message = mock_send_mail.call_args.kwargs['message']
        self.assertIn('Session time changed', subject)
        self.assertIn('rescheduled', message)

    def test_only_parent_guardian_carer_contacts_are_used(self, mock_centres_db, mock_roles_db, mock_send_mail):
        self._no_admins(mock_centres_db, mock_roles_db)
        child = child_with_contacts(contacts=[
            {'invite_as': 'Emergency', 'email': 'emergency@example.com'},
            {'invite_as': 'Guardian', 'email': 'guardian@example.com'},
            {'invite_as': 'Carer', 'email': 'carer@example.com'},
            {'invite_as': 'Parent', 'email': None},  # missing email, excluded
        ])

        mailer.send_enrolment_added_email(child, None, None, {'id': CENTRE_ID, 'name': 'Centre A'})

        recipients = {c.kwargs['recipient_list'][0] for c in mock_send_mail.call_args_list}
        self.assertEqual(recipients, {'guardian@example.com', 'carer@example.com'})

    def test_send_failure_for_one_recipient_does_not_raise_or_block_others(
        self, mock_centres_db, mock_roles_db, mock_send_mail
    ):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': {'email': 'manager@example.com'}}
        mock_roles_db.list_roles.return_value = []
        mock_send_mail.side_effect = Exception('SMTP down')
        child = child_with_contacts()

        # Should not raise despite every send failing.
        mailer.send_enrolment_added_email(child, None, None, {'id': CENTRE_ID, 'name': 'Centre A'})

        self.assertEqual(mock_send_mail.call_count, 1)


# =============================================================================
# send_permission_updated_email
# =============================================================================

@patch('notifications.mailer.send_mail')
@patch('notifications.mailer.roles_db')
@patch('notifications.mailer.centres_db')
class PermissionUpdatedEmailTests(SimpleTestCase):
    def test_notifies_members_and_centre_admins(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': {'email': 'manager@example.com'}}
        mock_roles_db.list_roles.return_value = []
        role = basic_role(members=[{'email': 'member@example.com'}])

        mailer.send_permission_updated_email(role, [('children.view_info', {'visible': True, 'edit': False})])

        recipients = {c.kwargs['recipient_list'][0] for c in mock_send_mail.call_args_list}
        self.assertEqual(recipients, {'member@example.com', 'manager@example.com'})
        subject = mock_send_mail.call_args_list[0].kwargs['subject']
        self.assertIn('Permissions updated', subject)
        self.assertIn('Teacher', subject)
        message = mock_send_mail.call_args_list[0].kwargs['message']
        self.assertIn('View child information', message)  # resolved label, not raw key
        self.assertIn('view only', message)

    def test_edit_permission_reports_edit_access(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = []
        role = basic_role(members=[{'email': 'member@example.com'}])

        mailer.send_permission_updated_email(role, [('children.view_info', {'visible': True, 'edit': True})])

        message = mock_send_mail.call_args.kwargs['message']
        self.assertIn('View child information: edit', message)

    def test_revoked_permission_reports_no_access(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = []
        role = basic_role(members=[{'email': 'member@example.com'}])

        mailer.send_permission_updated_email(role, [('children.view_info', {'visible': False, 'edit': False})])

        message = mock_send_mail.call_args.kwargs['message']
        self.assertIn('View child information: no access', message)

    def test_no_recipients_sends_nothing(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'manager': None}
        mock_roles_db.list_roles.return_value = []
        role = basic_role(members=[])

        mailer.send_permission_updated_email(role, [('children.view_info', {'visible': True, 'edit': False})])

        mock_send_mail.assert_not_called()


# =============================================================================
# send_staff_invite_email
# =============================================================================

@patch('notifications.mailer.send_mail')
@patch('notifications.mailer.roles_db')
@patch('notifications.mailer.centres_db')
class SendStaffInviteEmailTests(SimpleTestCase):
    def test_email_sent_without_login_instructions(self, mock_centres_db, mock_roles_db, mock_send_mail):
        mock_centres_db.get_centre.return_value = {'id': CENTRE_ID, 'name': 'Centre A'}
        person = {'email': 'staff@example.com', 'name': 'John Doe'}
        role = basic_role(members=[])

        result = mailer.send_staff_invite_email(person, role, CENTRE_ID)

        self.assertTrue(result['sent'])
        self.assertIsNone(result['reason'])
        
        mock_send_mail.assert_called_once()
        subject = mock_send_mail.call_args.kwargs['subject']
        message = mock_send_mail.call_args.kwargs['message']
        
        # Verify subject and basic info
        self.assertEqual(subject, "You have been set up on Shichida India — Teacher at Centre A")
        self.assertIn("Hello John", message)
        self.assertIn("You have been set up on Shichida India as Teacher at Centre A.", message)
        
        # Verify login/OTP instructions are NOT present
        self.assertNotIn("Forgot your password?", message)
        self.assertNotIn("choose your own password", message)
        self.assertNotIn("sign in with your email and password", message)
        self.assertNotIn("one-time code", message)
        self.assertNotIn("areas of the portal", message)
