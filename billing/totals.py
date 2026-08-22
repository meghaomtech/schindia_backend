"""
What an invoice comes to.

This is computed here rather than accepted from the client. The total is the
figure a family is asked to pay and everything downstream — outstanding
balance, ageing, debtors, whether the invoice reads as settled — resolves
through it. A total posted by the browser could disagree with the lines
printed on the same document, and nobody could say afterwards which was right.

Mirrors computeInvoiceTotals in the frontend's invoiceCalc.ts, which drives
the printed preview. The two must agree, so the rounding matches: JavaScript's
Math.round is half-up on positive values, hence ROUND_HALF_UP.
"""
from decimal import Decimal, ROUND_HALF_UP

# The fee fields the generator form posts. Their presence is what identifies
# an invoice whose total is derivable from its own lines.
LINE_FIELDS = (
    'registration_fee', 'session_fee_amount', 'extra_items',
    'deductions', 'debit_brought_forward', 'gst_percent', 'gst_mode',
)


def is_line_itemised(data):
    """
    Whether this invoice's total can be worked out from its lines.

    Two shapes reach this endpoint. The generator posts fee fields and we own
    the arithmetic. An older shape posts `items` and an explicit total instead,
    and there is nothing here to recompute from — overriding that with a total
    derived from absent fee fields would zero a legitimate invoice.

    Presence is the test, not truthiness: a genuinely zero-value invoice still
    posts the fields, and its total really is zero.
    """
    return any(field in data for field in LINE_FIELDS)


def _money(value):
    """Decimal, because float arithmetic on money silently loses paise."""
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def _round(value):
    return value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _lines_total(items):
    """Sum amount x quantity over a list of line items."""
    total = Decimal('0')
    for item in items or []:
        if not isinstance(item, dict):
            continue
        # A line with no quantity stated is one of that thing, not none of it —
        # defaulting to zero would silently drop it from the bill. An explicit
        # zero is still respected.
        raw_quantity = item.get('quantity')
        quantity = Decimal('1') if raw_quantity in (None, '') else _money(raw_quantity)
        total += _money(item.get('amount')) * quantity
    return total


def compute_invoice_total(data):
    """
    The amount payable: fees plus extras, less deductions, plus GST and any
    balance brought forward.

    `gst_mode == 'including'` means the amounts entered already contain GST, so
    it is worked back out of them rather than added on top — the total is then
    what was entered, not more than it.
    """
    entered = (
        _money(data.get('registration_fee'))
        + _money(data.get('session_fee_amount'))
        + _lines_total(data.get('extra_items'))
        - _lines_total(data.get('deductions'))
    )

    gst_percent = _money(data.get('gst_percent'))
    brought_forward = _money(data.get('debit_brought_forward'))

    if str(data.get('gst_mode')) == 'including' and gst_percent > 0:
        # GST is already inside `entered`; adding it again would overcharge.
        return entered + brought_forward

    gst_amount = _round(entered * gst_percent / Decimal('100'))
    return entered + gst_amount + brought_forward
