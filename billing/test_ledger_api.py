"""
Ledger endpoints — recording money and corrections against an invoice.

The permission separation is the point: front desk take payments all day and
must not be able to cancel, write off or refund. These tests hold that line.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

INVOICE_ID = "11111111-1111-1111-1111-111111111111"
CENTRE_ID = "22222222-2222-2222-2222-222222222222"


class FakeUser:
    def __init__(self, user_id="33333333-3333-3333-3333-333333333333"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"
        self.email = "front.desk@shichida.local"


def access_allowing(*keys):
    """A UserAccess granting exactly `keys` at CENTRE_ID and nothing else."""
    access = MagicMock()
    access.can_access_centre.return_value = True
    access.can_edit.side_effect = lambda centre, key: key in keys
    access.can_view.side_effect = lambda centre, key: key in keys
    return access


def invoice(cancelled_at=None):
    return {
        'id': INVOICE_ID, 'centre_id': CENTRE_ID, 'child_id': None,
        'total': '1000', 'due_date': '2026-09-01', 'cancelled_at': cancelled_at,
    }


@patch("billing.views.get_user_access")
@patch("billing.views.billing_db")
class LedgerPermissionTests(SimpleTestCase):
    """Each act asks its own row."""

    CASES = [
        ("payments", 'finance.manage_bill_payer_payments'),
        ("credit-notes", 'finance.manage_bill_payer_credits'),
        ("write-offs", 'finance.write_off_invoices'),
        ("refunds", 'finance.refund_payments'),
    ]

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _url(self, seg):
        return f"/api/v1/invoices/{INVOICE_ID}/{seg}/"

    def test_each_act_requires_its_own_permission(self, db, access):
        db.get_invoice.return_value = invoice()
        db.list_ledger.return_value = []
        for seg, key in self.CASES:
            with self.subTest(act=seg):
                # Holding every *other* finance permission must not help.
                others = [k for _s, k in self.CASES if k != key]
                access.return_value = access_allowing(*others)
                res = self.client.post(self._url(seg), {'amount': '100', 'reason': 'other'}, format="json")
                self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
                db.add_ledger_entry.assert_not_called()

    def test_front_desk_can_take_a_payment_without_being_able_to_refund(self, db, access):
        db.get_invoice.return_value = invoice()
        db.list_ledger.return_value = []
        db.add_ledger_entry.return_value = {'id': 'e1'}
        access.return_value = access_allowing('finance.manage_bill_payer_payments')

        ok = self.client.post(self._url('payments'), {'amount': '250'}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

        denied = self.client.post(self._url('refunds'), {'amount': '250', 'reason': 'overpayment'}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelling_needs_its_own_permission(self, db, access):
        db.get_invoice.return_value = invoice()
        access.return_value = access_allowing('finance.manage_bill_payer_payments')
        res = self.client.post(self._url('cancel'), {'reason': 'duplicate'}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_an_invoice_at_an_inaccessible_centre_reads_as_not_found(self, db, access):
        """404, not 403 — otherwise the response confirms it exists."""
        db.get_invoice.return_value = invoice()
        a = access_allowing('finance.manage_bill_payer_payments')
        a.can_access_centre.return_value = False
        access.return_value = a
        res = self.client.post(self._url('payments'), {'amount': '100'}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


@patch("billing.views.get_user_access")
@patch("billing.views.billing_db")
class LedgerRecordingTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _post(self, seg, body):
        return self.client.post(f"/api/v1/invoices/{INVOICE_ID}/{seg}/", body, format="json")

    def test_a_payment_is_recorded_and_the_balance_comes_back(self, db, access):
        access.return_value = access_allowing('finance.manage_bill_payer_payments')
        db.get_invoice.return_value = invoice()
        db.add_ledger_entry.return_value = {'id': 'e1'}
        db.list_ledger.return_value = [{'kind': 'payment', 'amount': '400'}]

        res = self._post('payments', {'amount': '400', 'method': 'upi'})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # camelCase applies to keys, not values — the status stays snake_case.
        self.assertEqual(res.json()['balance']['status'], 'part_paid')
        self.assertEqual(db.add_ledger_entry.call_args[0][1], 'payment')

    def test_zero_and_negative_amounts_are_rejected(self, db, access):
        access.return_value = access_allowing('finance.manage_bill_payer_payments')
        db.get_invoice.return_value = invoice()
        for amount in ('0', '-50'):
            with self.subTest(amount=amount):
                res = self._post('payments', {'amount': amount})
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                db.add_ledger_entry.assert_not_called()

    def test_a_correction_requires_a_reason_from_the_list(self, db, access):
        access.return_value = access_allowing('finance.write_off_invoices')
        db.get_invoice.return_value = invoice()
        db.list_ledger.return_value = []

        missing = self._post('write-offs', {'amount': '100'})
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        freetext = self._post('write-offs', {'amount': '100', 'reason': 'because I said so'})
        self.assertEqual(freetext.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_refund_cannot_exceed_what_was_actually_received(self, db, access):
        access.return_value = access_allowing('finance.refund_payments')
        db.get_invoice.return_value = invoice()
        db.list_ledger.return_value = [{'kind': 'payment', 'amount': '300'}]

        res = self._post('refunds', {'amount': '500', 'reason': 'overpayment'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', res.json())
        db.add_ledger_entry.assert_not_called()

    def test_nothing_can_be_recorded_against_a_cancelled_invoice(self, db, access):
        access.return_value = access_allowing('finance.manage_bill_payer_payments')
        db.get_invoice.return_value = invoice(cancelled_at='2026-08-19T10:00:00')

        res = self._post('payments', {'amount': '100'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        db.add_ledger_entry.assert_not_called()

    def test_cancelling_voids_rather_than_deletes(self, db, access):
        access.return_value = access_allowing('finance.cancel_invoices')
        db.get_invoice.return_value = invoice()
        db.cancel_invoice.return_value = invoice(cancelled_at='2026-08-20T00:00:00')
        db.list_ledger.return_value = []

        res = self._post('cancel', {'reason': 'duplicate', 'note': 'raised twice'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        db.cancel_invoice.assert_called_once()
        db.delete_invoice.assert_not_called()
        self.assertEqual(res.json()['balance']['status'], 'void')

    def test_an_already_cancelled_invoice_cannot_be_cancelled_twice(self, db, access):
        access.return_value = access_allowing('finance.cancel_invoices')
        db.get_invoice.return_value = invoice(cancelled_at='2026-08-19T10:00:00')

        res = self._post('cancel', {'reason': 'duplicate'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        db.cancel_invoice.assert_not_called()
