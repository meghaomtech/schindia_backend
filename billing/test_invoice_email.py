"""
Who an invoice actually reaches.

The bug: recipients were resolved only from a child's parent contacts, so an
invoice raised without a linked child — the ordinary case from a centre's own
Invoices tab — silently sent to nobody, while the bill-payer address printed
on the document was ignored. Nothing surfaced that at the till either.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from billing.notifications import invoice_recipients

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
CHILD_ID = "55555555-5555-5555-5555-555555555555"


def child_with(*contacts):
    return {'id': CHILD_ID, 'centre_id': CENTRE_ID, 'first_name': 'Alice',
            'last_name': 'A', 'contacts': list(contacts)}


def contact(email, invite_as='Parent'):
    return {'name': 'P', 'email': email, 'invite_as': invite_as}


class InvoiceRecipientTests(SimpleTestCase):
    def test_prefers_the_childs_parent_contacts(self):
        child = child_with(contact('mum@example.com'), contact('dad@example.com'))
        self.assertEqual(
            invoice_recipients({'email': 'reception@example.com'}, child),
            ['mum@example.com', 'dad@example.com'],
        )

    def test_ignores_contacts_who_are_not_parents(self):
        child = child_with(contact('teacher@example.com', invite_as='Staff'))
        # Falls through to the bill payer rather than emailing a colleague.
        self.assertEqual(
            invoice_recipients({'email': 'payer@example.com'}, child),
            ['payer@example.com'],
        )

    def test_falls_back_to_the_bill_payer_when_there_is_no_child(self):
        # An invoice raised before enrolment has no contacts to resolve.
        self.assertEqual(
            invoice_recipients({'email': 'payer@example.com'}, None),
            ['payer@example.com'],
        )

    def test_falls_back_when_the_child_has_no_contacts(self):
        self.assertEqual(
            invoice_recipients({'email': 'payer@example.com'}, child_with()),
            ['payer@example.com'],
        )

    def test_has_nobody_when_there_is_no_contact_and_no_bill_payer(self):
        self.assertEqual(invoice_recipients({}, None), [])
        self.assertEqual(invoice_recipients({'email': '   '}, None), [])


@patch("billing.notifications.centres_db")
@patch("billing.notifications.children_db")
@patch("billing.notifications.send_mail")
class SendInvoiceEmailTests(SimpleTestCase):
    def _invoice(self, **over):
        base = {'id': 'inv-1', 'number': 'BA260001', 'centre_id': CENTRE_ID,
                'child_id': None, 'email': 'payer@example.com',
                'student_name': 'Walk-in', 'total_amount': '2360',
                'due_date': '2026-09-30'}
        base.update(over)
        return base

    def test_emails_the_bill_payer_for_a_childless_invoice(self, mail, kids, centres):
        from billing.notifications import send_invoice_email
        kids.get_child.return_value = None
        centres.get_centre.return_value = {'name': 'Sunshine'}

        result = send_invoice_email(self._invoice())

        self.assertTrue(result['sent'])
        self.assertEqual(mail.call_args.kwargs['recipient_list'], ['payer@example.com'])

    def test_names_the_student_when_there_is_no_child_record(self, mail, kids, centres):
        from billing.notifications import send_invoice_email
        kids.get_child.return_value = None
        centres.get_centre.return_value = {'name': 'Sunshine'}

        send_invoice_email(self._invoice())

        self.assertIn('Walk-in', mail.call_args.kwargs['subject'])

    def test_reports_when_there_is_nobody_to_send_to(self, mail, kids, centres):
        from billing.notifications import send_invoice_email
        kids.get_child.return_value = None

        result = send_invoice_email(self._invoice(email=''))

        self.assertFalse(result['sent'])
        self.assertEqual(result['reason'], 'no_contacts')
        mail.assert_not_called()

    def test_reports_a_send_failure_rather_than_claiming_success(self, mail, kids, centres):
        from billing.notifications import send_invoice_email
        kids.get_child.return_value = None
        centres.get_centre.return_value = {'name': 'Sunshine'}
        mail.side_effect = Exception('MessageRejected: not verified')

        result = send_invoice_email(self._invoice())

        self.assertFalse(result['sent'])
        self.assertEqual(result['reason'], 'all_failed')


class FakeUser:
    def __init__(self):
        self.id = "33333333-3333-3333-3333-333333333333"
        self.pk = self.id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"
        self.email = "front.desk@shichida.local"


@patch("billing.views.get_user_access")
@patch("billing.views.children_db")
@patch("billing.views.billing_db")
@patch("billing.views.send_invoice_email")
class CreateReportsDeliveryTests(SimpleTestCase):
    """Raising an invoice says whether it actually reached anyone."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _wire(self, db, access):
        a = MagicMock()
        a.can_access_centre.side_effect = lambda c: str(c) == CENTRE_ID
        access.return_value = a
        db.allocate_invoice_number.return_value = "BA260001"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-1")

    def _post(self):
        return self.client.post("/api/v1/invoices/", {
            "centreId": CENTRE_ID, "sessionFeeAmount": 2000, "gstPercent": 18,
        }, format="json")

    def test_says_who_it_reached(self, send, db, kids, access):
        self._wire(db, access)
        send.return_value = {'sent': True, 'reason': None,
                             'results': [{'email': 'payer@example.com', 'status': 'sent'}]}

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['email_delivery']['sent'])
        self.assertEqual(res.data['email_delivery']['recipients'], ['payer@example.com'])

    def test_still_saves_the_invoice_when_the_email_fails(self, send, db, kids, access):
        # The bill is owed whether or not it was delivered. Failing the save
        # would lose a real invoice over a mail problem.
        self._wire(db, access)
        send.return_value = {'sent': False, 'reason': 'no_contacts', 'results': []}

        res = self._post()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.data['email_delivery']['sent'])
        self.assertEqual(res.data['email_delivery']['reason'], 'no_contacts')
