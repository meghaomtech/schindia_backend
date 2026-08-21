"""
The single settlement calculation for invoices.

Every screen that shows what a family owes resolves through compute_balance,
so the centre list, the invoice detail and the child's tab cannot disagree.

Two rules shape the design:

  - An issued invoice is never destroyed or edited to correct it. Cancelling,
    crediting, writing off and refunding are each recorded acts appended to
    the ledger. A GST series with a missing number cannot be explained to an
    auditor, and a mutated total cannot be reconciled to what was sent.

  - Status is derived, never stored. A stored status drifts the moment a
    payment lands or a due date passes, and "Paid" vs "Written off" is
    exactly the distinction reporting must not lose.
"""
from datetime import date
from decimal import Decimal

# Ledger entry kinds. Each is a genuinely different act with its own
# permission — "we made a mistake" and "we forgave the debt" must never be
# recorded as the same thing.
PAYMENT = 'payment'
CREDIT_NOTE = 'credit_note'
WRITE_OFF = 'write_off'
REFUND = 'refund'
ENTRY_KINDS = (PAYMENT, CREDIT_NOTE, WRITE_OFF, REFUND)

# Derived statuses.
ISSUED = 'issued'
PART_PAID = 'part_paid'
PAID = 'paid'
OVERDUE = 'overdue'
WRITTEN_OFF = 'written_off'
VOID = 'void'


def _money(value):
    """Decimal, because float arithmetic on money silently loses paise."""
    if value in (None, ''):
        return Decimal('0')
    return Decimal(str(value))


def _sum(entries, kind):
    return sum((_money(e.get('amount')) for e in entries if e.get('kind') == kind), Decimal('0'))


def compute_balance(invoice, entries, today=None):
    """
    Resolve an invoice against its ledger.

    Returns totals plus the derived status. `entries` is every ledger row for
    this invoice; `invoice` needs `total`, `due_date` and `cancelled_at`.
    """
    entries = entries or []
    # Stored invoices use `total_amount`; `total` is accepted so callers
    # holding a already-normalised shape still resolve correctly.
    total = _money(invoice.get('total_amount', invoice.get('total')))

    payments = _sum(entries, PAYMENT)
    credits = _sum(entries, CREDIT_NOTE)
    write_offs = _sum(entries, WRITE_OFF)
    refunds = _sum(entries, REFUND)

    # Refunds add back: money that was paid and then returned is money the
    # family still owes, so a fully-refunded invoice must not read part-paid.
    outstanding = total - credits - payments - write_offs + refunds
    if outstanding < 0:
        outstanding = Decimal('0')

    return {
        'total': total,
        'paid': payments,
        'credited': credits,
        'written_off': write_offs,
        'refunded': refunds,
        'outstanding': outstanding,
        'status': derive_status(invoice, total, outstanding, write_offs, payments, today),
    }


def derive_status(invoice, total, outstanding, write_offs, payments, today=None):
    """
    Six statuses, in priority order.

    Cancelled wins over everything: a void invoice is owed by nobody whatever
    its lines said. Written off is checked before Paid so a forgiven debt is
    never reported as money received.
    """
    if invoice.get('cancelled_at'):
        return VOID

    if outstanding <= 0:
        # Wholly forgiven is not the same as settled — the money never arrived.
        if write_offs > 0 and payments <= 0:
            return WRITTEN_OFF
        return PAID

    due = invoice.get('due_date')
    if due:
        on = today or date.today()
        try:
            due_date = date.fromisoformat(str(due)[:10])
            if due_date < on:
                return OVERDUE
        except ValueError:
            pass  # An unparseable due date shouldn't mask the real status.

    if payments > 0 or outstanding < total:
        return PART_PAID
    return ISSUED


def ageing_bucket(invoice, outstanding, today=None):
    """
    Debt age band for the debtors view: current · 0-30 · 31-60 · 61-90 · 90+.
    Nothing outstanding is never in a bucket, whatever its due date.
    """
    if outstanding <= 0:
        return None
    due = invoice.get('due_date')
    if not due:
        return 'current'
    try:
        due_date = date.fromisoformat(str(due)[:10])
    except ValueError:
        return 'current'

    days = ((today or date.today()) - due_date).days
    if days <= 0:
        return 'current'
    if days <= 30:
        return '0-30'
    if days <= 60:
        return '31-60'
    if days <= 90:
        return '61-90'
    return '90+'
