"""
Settlement rules — the calculation every screen resolves through.

These are pure-function tests: no DynamoDB, no HTTP. If two screens ever
disagree about what a family owes, the bug is either here or in a caller
that computed its own total instead of asking.
"""
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from billing.ledger import (
    CREDIT_NOTE, PAYMENT, REFUND, WRITE_OFF,
    ISSUED, OVERDUE, PAID, PART_PAID, VOID, WRITTEN_OFF,
    ageing_bucket, compute_balance,
)

TODAY = date(2026, 8, 20)


def invoice(total='1000', due_date='2026-09-01', cancelled_at=None):
    return {'total': total, 'due_date': due_date, 'cancelled_at': cancelled_at}


def entry(kind, amount):
    return {'kind': kind, 'amount': amount}


class ComputeBalanceTests(SimpleTestCase):
    def test_an_untouched_invoice_is_issued_and_wholly_outstanding(self):
        b = compute_balance(invoice(), [], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('1000'))
        self.assertEqual(b['status'], ISSUED)

    def test_a_part_payment_leaves_the_remainder_outstanding(self):
        b = compute_balance(invoice(), [entry(PAYMENT, '400')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('600'))
        self.assertEqual(b['status'], PART_PAID)

    def test_paying_in_full_settles_it(self):
        b = compute_balance(invoice(), [entry(PAYMENT, '1000')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('0'))
        self.assertEqual(b['status'], PAID)

    def test_credit_notes_reduce_what_is_owed(self):
        b = compute_balance(invoice(), [entry(CREDIT_NOTE, '250')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('750'))

    def test_a_refunded_payment_does_not_read_as_part_settled(self):
        """The money did not stay, so the family still owes the full amount."""
        b = compute_balance(
            invoice(), [entry(PAYMENT, '1000'), entry(REFUND, '1000')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('1000'))
        self.assertNotEqual(b['status'], PAID)

    def test_a_forgiven_invoice_is_written_off_not_paid(self):
        """Reporting must tell "never arrived" apart from "received"."""
        b = compute_balance(invoice(), [entry(WRITE_OFF, '1000')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('0'))
        self.assertEqual(b['status'], WRITTEN_OFF)

    def test_part_paid_then_forgiven_reads_as_paid_not_written_off(self):
        """Money did arrive, so this isn't a pure write-off."""
        b = compute_balance(
            invoice(), [entry(PAYMENT, '400'), entry(WRITE_OFF, '600')], today=TODAY)
        self.assertEqual(b['status'], PAID)

    def test_a_cancelled_invoice_is_owed_by_nobody(self):
        b = compute_balance(
            invoice(cancelled_at='2026-08-19T10:00:00'), [], today=TODAY)
        self.assertEqual(b['status'], VOID)

    def test_cancellation_wins_even_when_money_is_outstanding(self):
        b = compute_balance(
            invoice(total='5000', cancelled_at='2026-08-19T10:00:00'),
            [entry(PAYMENT, '100')], today=TODAY)
        self.assertEqual(b['status'], VOID)

    def test_past_due_with_money_outstanding_is_overdue(self):
        b = compute_balance(invoice(due_date='2026-08-01'), [], today=TODAY)
        self.assertEqual(b['status'], OVERDUE)

    def test_past_due_but_settled_is_not_overdue(self):
        b = compute_balance(
            invoice(due_date='2026-08-01'), [entry(PAYMENT, '1000')], today=TODAY)
        self.assertEqual(b['status'], PAID)

    def test_overpayment_never_reports_a_negative_balance(self):
        b = compute_balance(invoice(), [entry(PAYMENT, '1500')], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('0'))

    def test_money_is_exact_to_the_paisa(self):
        """Float arithmetic here loses paise; the ledger must not."""
        b = compute_balance(
            invoice(total='0.30'), [entry(PAYMENT, '0.10'), entry(PAYMENT, '0.20')],
            today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('0'))
        self.assertEqual(b['status'], PAID)

    def test_a_malformed_due_date_does_not_mask_the_real_status(self):
        b = compute_balance(invoice(due_date='not-a-date'), [], today=TODAY)
        self.assertEqual(b['status'], ISSUED)

    def test_a_missing_total_is_treated_as_zero_not_a_crash(self):
        b = compute_balance({'total': None, 'due_date': None}, [], today=TODAY)
        self.assertEqual(b['outstanding'], Decimal('0'))


class AgeingBucketTests(SimpleTestCase):
    def test_settled_invoices_are_never_in_a_bucket(self):
        self.assertIsNone(ageing_bucket(invoice(due_date='2020-01-01'), Decimal('0'), TODAY))

    def test_not_yet_due_is_current(self):
        self.assertEqual(
            ageing_bucket(invoice(due_date='2026-09-01'), Decimal('100'), TODAY), 'current')

    def test_bands_run_by_days_past_due(self):
        cases = [('2026-08-10', '0-30'), ('2026-07-10', '31-60'),
                 ('2026-06-10', '61-90'), ('2026-01-10', '90+')]
        for due, expected in cases:
            with self.subTest(due=due):
                self.assertEqual(
                    ageing_bucket(invoice(due_date=due), Decimal('100'), TODAY), expected)
