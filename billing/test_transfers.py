"""
What happens to a child's invoices when an approved move takes them elsewhere.

The functional requirement is that the child no longer carries the old
centre's invoices. The accounting requirement is that the old centre still
does — those invoices are its GST series, its debtors and its audit trail.
Detaching satisfies both; deleting or transferring satisfies only one.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from billing.transfers import (
    DETACH_REASON, clear_child_invoices_for_move, old_centre_invoices,
    reattach_child_invoices,
)

CHILD_ID = "11111111-1111-1111-1111-111111111111"
FROM_CENTRE = "22222222-2222-2222-2222-222222222222"
TO_CENTRE = "88888888-8888-8888-8888-888888888888"
REQUEST_ID = "44444444-4444-4444-4444-444444444444"


def invoice(invoice_id, **over):
    base = {'id': invoice_id, 'number': f'BA2600{invoice_id[-1]}',
            'child_id': CHILD_ID, 'centre_id': FROM_CENTRE,
            'total_amount': '5900'}
    base.update(over)
    return base


@patch('billing.transfers.billing_db')
class OldCentreInvoiceTests(SimpleTestCase):
    def test_finds_the_invoices_raised_by_the_centre_being_left(self, db):
        db.list_invoices.return_value = [invoice('inv-1'), invoice('inv-2')]

        found = old_centre_invoices(CHILD_ID, FROM_CENTRE)

        self.assertEqual([i['id'] for i in found], ['inv-1', 'inv-2'])

    def test_leaves_another_centres_invoices_alone(self, db):
        # A child who has moved before still carries invoices from elsewhere;
        # they are not this transfer's business.
        db.list_invoices.return_value = [
            invoice('inv-1'), invoice('inv-2', centre_id=TO_CENTRE)]

        found = old_centre_invoices(CHILD_ID, FROM_CENTRE)

        self.assertEqual([i['id'] for i in found], ['inv-1'])

    def test_treats_an_unstamped_invoice_as_the_current_centres(self, db):
        # Invoices raised before centre stamping have only the child to go on.
        db.list_invoices.return_value = [invoice('inv-1', centre_id=None)]

        self.assertEqual(len(old_centre_invoices(CHILD_ID, FROM_CENTRE)), 1)

    def test_skips_invoices_already_detached_by_an_earlier_move(self, db):
        db.list_invoices.return_value = [
            invoice('inv-1'), invoice('inv-2', detached_at='2026-01-01T00:00:00')]

        found = old_centre_invoices(CHILD_ID, FROM_CENTRE)

        self.assertEqual([i['id'] for i in found], ['inv-1'])


@patch('billing.transfers.billing_db')
class ClearChildInvoicesTests(SimpleTestCase):
    def test_takes_the_invoices_off_the_child(self, db):
        db.list_invoices.return_value = [invoice('inv-1')]

        cleared = clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        self.assertEqual(cleared, ['inv-1'])
        updates = db.update_invoice.call_args[0][1]
        self.assertIsNone(updates['child_id'])

    def test_records_whose_invoice_it_was_and_why_it_came_off(self, db):
        db.list_invoices.return_value = [invoice('inv-1')]

        clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        updates = db.update_invoice.call_args[0][1]
        self.assertEqual(updates['former_child_id'], CHILD_ID)
        self.assertEqual(updates['detached_reason'], DETACH_REASON)
        self.assertEqual(updates['detached_move_request_id'], REQUEST_ID)
        self.assertTrue(updates['detached_at'])

    def test_never_deletes_an_invoice(self, db):
        # The number is part of a GST series; a hole in it cannot be explained.
        db.list_invoices.return_value = [invoice('inv-1'), invoice('inv-2')]

        clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        db.delete_invoice.assert_not_called()

    def test_leaves_the_amounts_and_the_number_untouched(self, db):
        db.list_invoices.return_value = [invoice('inv-1')]

        clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        updates = db.update_invoice.call_args[0][1]
        for untouched in ('number', 'total_amount', 'status'):
            self.assertNotIn(untouched, updates)

    def test_keeps_the_invoice_findable_at_the_centre_that_raised_it(self, db):
        # Without the child link, an unstamped invoice would vanish from the
        # old centre's own history — the opposite of the point.
        db.list_invoices.return_value = [invoice('inv-1', centre_id=None)]

        clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        self.assertEqual(db.update_invoice.call_args[0][1]['centre_id'], FROM_CENTRE)

    def test_does_not_restamp_an_invoice_that_already_names_its_centre(self, db):
        db.list_invoices.return_value = [invoice('inv-1')]

        clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)

        self.assertNotIn('centre_id', db.update_invoice.call_args[0][1])

    def test_a_child_with_no_invoices_is_a_no_op(self, db):
        db.list_invoices.return_value = []

        self.assertEqual(
            clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID), [])
        db.update_invoice.assert_not_called()


@patch('billing.transfers.billing_db')
class ReattachInvoicesTests(SimpleTestCase):
    def test_puts_the_invoices_back_on_the_child(self, db):
        reattach_child_invoices(CHILD_ID, ['inv-1', 'inv-2'])

        self.assertEqual(db.update_invoice.call_count, 2)
        updates = db.update_invoice.call_args[0][1]
        self.assertEqual(updates['child_id'], CHILD_ID)

    def test_clears_every_trace_of_the_detachment(self, db):
        # A move that never happened must not leave the invoice looking as
        # though it did.
        reattach_child_invoices(CHILD_ID, ['inv-1'])

        updates = db.update_invoice.call_args[0][1]
        for field in ('former_child_id', 'detached_at', 'detached_reason',
                      'detached_move_request_id'):
            self.assertIsNone(updates[field])

    def test_a_rollback_with_nothing_detached_does_nothing(self, db):
        reattach_child_invoices(CHILD_ID, [])

        db.update_invoice.assert_not_called()


@patch('billing.transfers.billing_db')
class RoundTripTests(SimpleTestCase):
    def test_clearing_then_reattaching_leaves_the_child_holding_them_again(self, db):
        # The rollback path in an approved move that fails partway: whatever
        # was detached has to end up back on the child, all of it.
        stored = {'inv-1': invoice('inv-1'), 'inv-2': invoice('inv-2')}
        db.list_invoices.return_value = list(stored.values())
        db.update_invoice.side_effect = lambda i, updates: stored[i].update(updates)

        cleared = clear_child_invoices_for_move(CHILD_ID, FROM_CENTRE, REQUEST_ID)
        self.assertEqual(sorted(cleared), ['inv-1', 'inv-2'])
        self.assertEqual([i['child_id'] for i in stored.values()], [None, None])

        reattach_child_invoices(CHILD_ID, cleared)

        for stored_invoice in stored.values():
            self.assertEqual(stored_invoice['child_id'], CHILD_ID)
            self.assertIsNone(stored_invoice['detached_at'])
            self.assertIsNone(stored_invoice['former_child_id'])
