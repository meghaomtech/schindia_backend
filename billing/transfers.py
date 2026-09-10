"""
What happens to a child's invoices when they move to another centre.

Billing owns this rather than the children app, because the answer is an
accounting one. An issued invoice belongs to the centre that raised it: its
number is part of that centre's GST series, it may be half paid, and it is
what the old centre's books, debtors list and audit trail are made of.
Deleting it, or dragging it to the new centre, would take money out of one set
of books and put it in another.

So the invoices are detached from the child instead. After an approved move
the child carries none of the old centre's invoices — which is what the
transfer has to achieve — while the old centre keeps every one of them, with
a note saying which child they were raised for and why they came off.
"""

import logging
from datetime import datetime

from dynamo_backend.services import billing_db

logger = logging.getLogger(__name__)

DETACH_REASON = 'child_moved_centre'


def old_centre_invoices(child_id, from_centre_id):
    """
    The child's invoices that belong to the centre being left.

    Invoices raised at a different centre — a child who has moved before — are
    not this transfer's business and are left alone.
    """
    invoices = billing_db.list_invoices(child_id=str(child_id))
    return [
        inv for inv in invoices
        if not inv.get('detached_at')
        and str(inv.get('centre_id') or from_centre_id) == str(from_centre_id)
    ]


def clear_child_invoices_for_move(child_id, from_centre_id, move_request_id=''):
    """
    Detach the old centre's invoices from a child who has moved.

    Called only from inside an approved move. Returns the ids affected, so the
    caller can put back what it changed if a later step fails.

    Nothing is deleted and no figure is altered: the invoice keeps its number,
    its lines, its total and its ledger. It stops being the child's, and
    records whose it was.
    """
    detached = []
    stamp = datetime.utcnow().isoformat()

    for invoice in old_centre_invoices(child_id, from_centre_id):
        updates = {
            # Cleared last in the write, but stated first here: this is the
            # change that takes the invoice off the child.
            'child_id': None,
            'former_child_id': str(child_id),
            'detached_at': stamp,
            'detached_reason': DETACH_REASON,
            'detached_move_request_id': str(move_request_id or ''),
        }
        # Invoices raised before centre stamping would otherwise become
        # unreachable the moment the child link goes — the old centre would
        # lose them from its own history, which is the opposite of the point.
        if not invoice.get('centre_id'):
            updates['centre_id'] = str(from_centre_id)

        billing_db.update_invoice(invoice['id'], updates)
        detached.append(invoice['id'])

    if detached:
        logger.info(
            "Move %s: detached %d invoice(s) from child %s at centre %s",
            move_request_id or '-', len(detached), child_id, from_centre_id,
        )
    return detached


def reattach_child_invoices(child_id, invoice_ids):
    """
    Undo clear_child_invoices_for_move.

    The compensating half of the approval: if the move fails after the
    invoices have been detached, they have to go back to the child, or a
    transfer that never happened has silently emptied their billing history.
    """
    for invoice_id in invoice_ids:
        billing_db.update_invoice(str(invoice_id), {
            'child_id': str(child_id),
            'former_child_id': None,
            'detached_at': None,
            'detached_reason': None,
            'detached_move_request_id': None,
        })
