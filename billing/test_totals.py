"""
What an invoice comes to.

The total is not cosmetic: every balance, ageing band and debtors row resolves
through it. An invoice stored without one reads as ₹0 owed, which means a bill
that was just raised presents as already settled and can never be paid,
chased, or shown as overdue.
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from billing.ledger import compute_balance
from billing.totals import compute_invoice_total

CENTRE_ID = "22222222-2222-2222-2222-222222222222"


def item(amount, quantity=1):
    return {'description': 'x', 'amount': amount, 'quantity': quantity}


class InvoiceTotalTests(SimpleTestCase):
    def test_adds_gst_on_top_when_amounts_exclude_it(self):
        total = compute_invoice_total({
            'session_fee_amount': 2000, 'gst_percent': 18, 'gst_mode': 'excluding',
        })
        self.assertEqual(total, Decimal('2360'))

    def test_works_gst_out_of_the_amount_when_it_is_included(self):
        # The amount entered is already the final bill; adding GST again would
        # overcharge the family.
        total = compute_invoice_total({
            'session_fee_amount': 2360, 'gst_percent': 18, 'gst_mode': 'including',
        })
        self.assertEqual(total, Decimal('2360'))

    def test_sums_fees_extras_and_subtracts_deductions(self):
        total = compute_invoice_total({
            'registration_fee': 1000,
            'session_fee_amount': 2000,
            'extra_items': [item(500), item(100, 3)],
            'deductions': [item(300)],
            'gst_percent': 0,
        })
        # 1000 + 2000 + 500 + 300 - 300
        self.assertEqual(total, Decimal('3500'))

    def test_multiplies_a_line_by_its_quantity(self):
        self.assertEqual(
            compute_invoice_total({'extra_items': [item(250, 4)], 'gst_percent': 0}),
            Decimal('1000'),
        )

    def test_treats_a_missing_quantity_as_one(self):
        # Dropping the line entirely would under-bill without anyone noticing.
        self.assertEqual(
            compute_invoice_total(
                {'extra_items': [{'description': 'x', 'amount': 700}], 'gst_percent': 0}),
            Decimal('700'),
        )

    def test_respects_an_explicit_zero_quantity(self):
        self.assertEqual(
            compute_invoice_total({'extra_items': [item(700, 0)], 'gst_percent': 0}),
            Decimal('0'),
        )

    def test_adds_the_balance_brought_forward(self):
        total = compute_invoice_total({
            'session_fee_amount': 1000, 'gst_percent': 0, 'debit_brought_forward': 250,
        })
        self.assertEqual(total, Decimal('1250'))

    def test_rounds_gst_half_up_like_the_printed_invoice(self):
        # The frontend prints Math.round(entered * pct / 100). If the server
        # rounded differently the document and the balance would disagree.
        total = compute_invoice_total({
            'session_fee_amount': 1005, 'gst_percent': 5, 'gst_mode': 'excluding',
        })
        # 1005 * 5% = 50.25 -> 50
        self.assertEqual(total, Decimal('1055'))

    def test_survives_missing_and_junk_fields(self):
        self.assertEqual(compute_invoice_total({}), Decimal('0'))
        self.assertEqual(
            compute_invoice_total({'session_fee_amount': '', 'gst_percent': None}),
            Decimal('0'),
        )
        self.assertEqual(
            compute_invoice_total({'session_fee_amount': 'abc', 'gst_percent': 18}),
            Decimal('0'),
        )

    def test_a_totalled_invoice_is_owed_not_settled(self):
        # The whole point: without a total this resolves to paid-in-full.
        data = {'session_fee_amount': 2000, 'gst_percent': 18, 'gst_mode': 'excluding'}
        invoice = {'total_amount': str(compute_invoice_total(data)), 'due_date': '2099-01-01'}
        balance = compute_balance(invoice, [])
        self.assertEqual(balance['outstanding'], Decimal('2360'))
        self.assertEqual(balance['status'], 'issued')

    def test_an_untotalled_invoice_is_what_the_bug_looked_like(self):
        # Documents the failure this fixes: no total -> nothing owed.
        balance = compute_balance({'due_date': '2099-01-01'}, [])
        self.assertEqual(balance['outstanding'], Decimal('0'))
        self.assertEqual(balance['status'], 'paid')


class FakeUser:
    def __init__(self):
        self.id = "33333333-3333-3333-3333-333333333333"
        self.pk = self.id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"
        self.email = "front.desk@shichida.local"


@patch("billing.views.send_invoice_email", MagicMock())
@patch("billing.views.get_user_access")
@patch("billing.views.children_db")
@patch("billing.views.billing_db")
class InvoiceCreateStoresTotalTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _access(self):
        a = MagicMock()
        a.can_access_centre.side_effect = lambda c: str(c) == CENTRE_ID
        a.can_view.return_value = True
        a.can_edit.return_value = True
        return a

    def test_stores_a_total_worked_out_from_the_lines(self, db, kids, access):
        access.return_value = self._access()
        db.allocate_invoice_number.return_value = "BA260001"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-1")

        res = self.client.post("/api/v1/invoices/", {
            "centreId": CENTRE_ID, "sessionFeeAmount": 2000,
            "gstPercent": 18, "gstMode": "excluding",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(db.create_invoice.call_args[0][0]["total_amount"], "2360")

    def test_leaves_an_item_based_invoice_total_alone(self, db, kids, access):
        # The older shape posts `items` and its own total. There are no fee
        # fields to recompute from, so overriding it would zero a real invoice.
        access.return_value = self._access()
        db.allocate_invoice_number.return_value = "BA260003"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-3")

        self.client.post("/api/v1/invoices/", {
            "centreId": CENTRE_ID, "totalAmount": 100,
            "items": [{"description": "Fee", "unitPrice": 100}],
        }, format="json")

        self.assertEqual(db.create_invoice.call_args[0][0]["total_amount"], 100)

    def test_ignores_a_total_asserted_by_the_client(self, db, kids, access):
        # The total decides what a family owes. Accepting it from the browser
        # would let the printed lines and the balance disagree.
        access.return_value = self._access()
        db.allocate_invoice_number.return_value = "BA260002"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-2")

        self.client.post("/api/v1/invoices/", {
            "centreId": CENTRE_ID, "sessionFeeAmount": 2000,
            "gstPercent": 18, "gstMode": "excluding", "totalAmount": "1",
        }, format="json")

        self.assertEqual(db.create_invoice.call_args[0][0]["total_amount"], "2360")
