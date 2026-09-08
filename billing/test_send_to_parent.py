"""
Sending an invoice to a parent, and previewing one without sending it.

The rule these are all really about: an invoice is marked sent because a
parent received it, not because somebody pressed a button. So the history is
written after the email leaves and never before — not when the PDF will not
render, not when the mail server refuses it, and not twice for one click.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from roles.access import UserAccess

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
OTHER_CENTRE_ID = "99999999-9999-9999-9999-999999999999"
CHILD_ID = "11111111-1111-1111-1111-111111111111"
INVOICE_ID = "33333333-3333-3333-3333-333333333333"
USER_ID = "55555555-5555-5555-5555-555555555555"
USER_EMAIL = "front.desk@shichida.local"

SEND_URL = f"/api/v1/invoices/{INVOICE_ID}/send-to-parent/"
PDF_URL = f"/api/v1/invoices/{INVOICE_ID}/pdf/"


class FakeUser:
    def __init__(self):
        self.id = USER_ID
        self.pk = USER_ID
        self.email = USER_EMAIL
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"


def invoice(**over):
    base = {
        'id': INVOICE_ID, 'number': 'BA260007', 'centre_id': CENTRE_ID,
        'child_id': CHILD_ID, 'email': 'payer@example.com',
        'student_name': 'Aarav Sharma', 'parent_name': 'Riya Sharma',
        'registration_fee': 5000, 'gst_percent': 18, 'gst_mode': 'excluding',
        'extra_items': [], 'deductions': [], 'total_amount': '5900',
        'invoice_date': '2026-09-04', 'due_date': '2026-09-30',
    }
    base.update(over)
    return base


def child(*emails):
    return {
        'id': CHILD_ID, 'centre_id': CENTRE_ID,
        'first_name': 'Aarav', 'last_name': 'Sharma',
        'contacts': [{'invite_as': 'Parent', 'email': e, 'name': 'Riya'}
                     for e in emails],
    }


def sent_entry(email='parent@example.com', ago_seconds=0):
    when = datetime.utcnow() - timedelta(seconds=ago_seconds)
    return {'channel': 'email', 'target': email, 'sent_at': when.isoformat(),
            'sent_by': USER_EMAIL}


@patch('billing.notifications.centres_db')
@patch('billing.notifications.children_db')
@patch('billing.views.invoice_email_context')
@patch('billing.views.invoice_recipients')
@patch('billing.views.send_invoice_email')
@patch('billing.views.get_user_access')
@patch('billing.views.billing_db')
class SendToParentTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _wire(self, db, access, recipients, context, inv=None):
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = inv if inv is not None else invoice()
        db.update_invoice.side_effect = lambda _id, updates: dict(
            db.get_invoice.return_value, **updates)
        db.list_ledger.return_value = []
        context.return_value = (child('parent@example.com'), {'name': 'Sunshine'})
        recipients.return_value = ['parent@example.com']

    def _delivered(self, email='parent@example.com'):
        return {'sent': True, 'reason': None,
                'results': [{'email': email, 'status': 'sent', 'error': None}]}

    # ── The happy path ───────────────────────────────────────────────

    def test_sends_and_records_the_delivery(self, db, access, send, recipients,
                                            context, kids, centres):
        self._wire(db, access, recipients, context)
        send.return_value = self._delivered()

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['sentTo'], ['parent@example.com'])
        db.add_sent_to.assert_called_once_with(
            INVOICE_ID, 'email', 'parent@example.com', sent_by=USER_EMAIL)

    def test_moves_the_invoice_to_sent_and_stamps_when(self, db, access, send,
                                                       recipients, context, kids, centres):
        self._wire(db, access, recipients, context)
        send.return_value = self._delivered()

        self.client.post(SEND_URL)

        updates = db.update_invoice.call_args[0][1]
        self.assertEqual(updates['status'], 'Sent')
        self.assertIn('sent_at', updates)

    def test_a_paid_invoice_is_not_reopened_by_sending_a_copy(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context, inv=invoice(status='Paid'))
        send.return_value = self._delivered()

        self.client.post(SEND_URL)

        self.assertNotIn('status', db.update_invoice.call_args[0][1])

    # ── Nothing is recorded when nothing was delivered ───────────────

    def test_a_pdf_failure_sends_nothing_and_records_nothing(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context)
        send.return_value = {'sent': False, 'reason': 'pdf_failed',
                             'error': 'boom', 'results': []}

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.json()['reason'], 'pdf_failed')
        db.add_sent_to.assert_not_called()
        db.update_invoice.assert_not_called()

    def test_a_mail_failure_is_reported_rather_than_claimed_as_sent(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context)
        send.return_value = {
            'sent': False, 'reason': 'all_failed',
            'results': [{'email': 'parent@example.com', 'status': 'failed',
                         'error': 'MessageRejected'}],
        }

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('MessageRejected', res.json()['errors'][0])
        db.add_sent_to.assert_not_called()
        db.update_invoice.assert_not_called()

    def test_refuses_when_there_is_no_parent_email(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context)
        recipients.return_value = []

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()['reason'], 'no_contacts')
        send.assert_not_called()
        db.add_sent_to.assert_not_called()

    def test_refuses_to_send_a_cancelled_invoice(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context,
                   inv=invoice(cancelled_at='2026-09-01T00:00:00'))

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        send.assert_not_called()

    # ── Duplicate protection ─────────────────────────────────────────

    def test_a_second_click_moments_later_does_not_send_again(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context,
                   inv=invoice(sent_to=[sent_entry(ago_seconds=2)]))

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()['duplicate'])
        send.assert_not_called()
        db.add_sent_to.assert_not_called()

    def test_a_deliberate_resend_later_is_allowed(
            self, db, access, send, recipients, context, kids, centres):
        # Chasing an unpaid invoice next week is a normal thing to do; only
        # a double-click is a duplicate.
        self._wire(db, access, recipients, context,
                   inv=invoice(sent_to=[sent_entry(ago_seconds=3600)]))
        send.return_value = self._delivered()

        res = self.client.post(SEND_URL)

        self.assertFalse(res.json()['duplicate'])
        send.assert_called_once()

    def test_a_recent_send_to_a_different_address_is_not_a_duplicate(
            self, db, access, send, recipients, context, kids, centres):
        self._wire(db, access, recipients, context,
                   inv=invoice(sent_to=[sent_entry('someone.else@example.com', 2)]))
        send.return_value = self._delivered()

        self.client.post(SEND_URL)

        send.assert_called_once()

    def test_an_untimed_legacy_delivery_does_not_block_sending(
            self, db, access, send, recipients, context, kids, centres):
        # Rows written before sends were timestamped say nothing about
        # whether this click is a repeat of the last one.
        self._wire(db, access, recipients, context, inv=invoice(
            sent_to=[{'channel': 'email', 'target': 'parent@example.com'}]))
        send.return_value = self._delivered()

        self.client.post(SEND_URL)

        send.assert_called_once()

    # ── Authorisation ────────────────────────────────────────────────

    def test_an_unknown_invoice_is_not_found(
            self, db, access, send, recipients, context, kids, centres):
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = None

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        send.assert_not_called()

    def test_another_centres_invoice_reads_as_not_found(
            self, db, access, send, recipients, context, kids, centres):
        # 404 rather than 403: a forbidden would confirm the invoice exists.
        db.get_invoice.return_value = invoice(centre_id=OTHER_CENTRE_ID)
        scoped = UserAccess(unrestricted=False)
        scoped.centres[CENTRE_ID] = {'data_scope': 'own', 'role_names': [],
                                     'permissions': {}}
        access.return_value = scoped

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        send.assert_not_called()

    def test_a_member_without_manage_invoices_is_refused(
            self, db, access, send, recipients, context, kids, centres):
        db.get_invoice.return_value = invoice()
        scoped = UserAccess(unrestricted=False)
        scoped.centres[CENTRE_ID] = {
            'data_scope': 'own', 'role_names': ['Front desk'],
            'permissions': {'finance.view_invoices': {'visible': True, 'edit': True}},
        }
        access.return_value = scoped

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        send.assert_not_called()

    def test_an_anonymous_caller_is_refused(
            self, db, access, send, recipients, context, kids, centres):
        res = APIClient().post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        send.assert_not_called()


@patch('billing.views.invoice_email_context')
@patch('billing.views.get_user_access')
@patch('billing.views.billing_db')
class InvoicePreviewPdfTests(SimpleTestCase):
    """
    Previewing must not send. That is the whole point of the endpoint being
    a GET that touches nothing.
    """

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def test_returns_the_invoice_as_a_pdf(self, db, access, context):
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = invoice()
        context.return_value = (child('parent@example.com'), {'name': 'Sunshine'})

        res = self.client.get(PDF_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn('Invoice-BA260007.pdf', res['Content-Disposition'])
        self.assertTrue(res.content.startswith(b'%PDF-'))

    def test_previewing_changes_nothing_about_the_invoice(self, db, access, context):
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = invoice()
        context.return_value = (None, None)

        self.client.get(PDF_URL)

        db.update_invoice.assert_not_called()
        db.add_sent_to.assert_not_called()

    @patch('billing.views.build_invoice_pdf')
    def test_a_render_failure_is_a_500_not_a_broken_download(
            self, build, db, access, context):
        from billing.pdf_generator import InvoicePdfError
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = invoice()
        context.return_value = (None, None)
        build.side_effect = InvoicePdfError('boom')

        res = self.client.get(PDF_URL)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_another_centres_invoice_cannot_be_previewed(self, db, access, context):
        db.get_invoice.return_value = invoice(centre_id=OTHER_CENTRE_ID)
        access.return_value = UserAccess(unrestricted=False)

        res = self.client.get(PDF_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class SendPathIntegrationTests(SimpleTestCase):
    """
    The real send_invoice_email, with only the mail transport and the database
    stubbed — so this proves the wiring produces an actual PDF attachment
    rather than that some function was called.
    """

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    @patch('billing.notifications.deliver_invoice_email')
    @patch('billing.notifications.centres_db')
    @patch('billing.notifications.children_db')
    @patch('billing.views.get_user_access')
    @patch('billing.views.billing_db')
    def test_the_parent_is_emailed_the_invoice_as_a_pdf_attachment(
            self, db, access, kids, centres, deliver):
        access.return_value = UserAccess(unrestricted=True)
        db.get_invoice.return_value = invoice()
        db.update_invoice.side_effect = lambda _id, updates: dict(invoice(), **updates)
        db.list_ledger.return_value = []
        kids.get_child.return_value = child('parent@example.com')
        centres.get_centre.return_value = {'name': 'Sunshine'}

        res = self.client.post(SEND_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        subject, message, recipient, attachment = deliver.call_args[0]
        self.assertEqual(recipient, 'parent@example.com')
        self.assertEqual(attachment[0], 'Invoice-BA260007.pdf')
        self.assertTrue(attachment[1].startswith(b'%PDF-'))
        self.assertEqual(attachment[2], 'application/pdf')

        # The essentials are in the message too — a parent should not have to
        # open an attachment to know which bill this is.
        self.assertIn('BA260007', message)
        self.assertIn('Aarav', subject)
        self.assertIn('Sunshine', subject)
        self.assertIn('Invoice-BA260007.pdf', message)
        self.assertIn('30 September 2026', message)
