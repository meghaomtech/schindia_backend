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
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

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

    One line, out of compute_invoice_breakdown() below, so the figure stored on
    the invoice is by construction the same one the PDF prints as TOTAL.
    """
    return compute_invoice_breakdown(data)['total']


def _js_round(value):
    """
    JavaScript's Math.round: half away from zero for positives, half toward
    +infinity for negatives (Math.round(-0.5) === -0).

    The printed rows are shared with invoiceCalc.ts, which drives the on-screen
    preview. A row that rounds differently server-side would put a different
    figure on the emailed PDF than the one reception just looked at.
    """
    return (value + Decimal('0.5')).to_integral_value(rounding=ROUND_FLOOR)


def compute_invoice_breakdown(data):
    """
    The figures printed beneath the table: taxable value, GST, brought
    forward, and what is payable.

    Mirrors computeInvoiceTotals in invoiceCalc.ts. compute_invoice_total()
    below is the total out of this same calculation, so the PDF footer and the
    stored total cannot disagree.
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
        # GST is already inside `entered`, so it is worked back out rather
        # than added on top — the total is what was entered, not more.
        taxable = _round(entered / (1 + gst_percent / Decimal('100')))
        return {
            'entered': entered,
            'taxable_value': taxable,
            'gst_amount': entered - taxable,
            'debit_brought_forward': brought_forward,
            'total': entered + brought_forward,
        }

    gst_amount = _round(entered * gst_percent / Decimal('100'))
    return {
        'entered': entered,
        'taxable_value': entered,
        'gst_amount': gst_amount,
        'debit_brought_forward': brought_forward,
        'total': entered + gst_amount + brought_forward,
    }


def _item_quantity(item):
    """A line with no quantity stated is one of that thing, not none of it."""
    raw = item.get('quantity')
    return Decimal('1') if raw in (None, '') else _money(raw)


def invoice_lines(data):
    """
    The rows to print, with the amount each should show.

    Mirrors invoiceLines() in invoiceCalc.ts, including its GST-inclusive
    rule: when the amounts entered already contain tax, each row prints its
    tax-exclusive share, and the rounding remainder goes to the largest row.
    Rows that do not sum to the subtotal printed under them cannot be
    explained to a parent or an auditor.

    Each row is {'description', 'quantity', 'amount', 'is_deduction',
    'period_from', 'period_to'}; `amount` is always positive — the sign is
    carried by is_deduction, as it is on screen.
    """
    lines = []

    registration_fee = _money(data.get('registration_fee'))
    if registration_fee > 0:
        lines.append({
            'description': 'Registration Fee', 'quantity': Decimal('1'),
            'amount': registration_fee, 'is_deduction': False,
            'period_from': '', 'period_to': '',
        })

    session_fee = _money(data.get('session_fee_amount'))
    session_start = data.get('session_fee_start') or ''
    session_end = data.get('session_fee_end') or ''
    if session_start or session_end or session_fee > 0:
        lines.append({
            'description': 'Session fee for the period', 'quantity': Decimal('1'),
            'amount': session_fee, 'is_deduction': False,
            'period_from': session_start, 'period_to': session_end,
        })

    for is_deduction, key in ((False, 'extra_items'), (True, 'deductions')):
        for item in data.get(key) or []:
            if not isinstance(item, dict):
                continue
            description = item.get('description') or ''
            amount = _money(item.get('amount'))
            # A blank row the user never filled in is not a line on the bill.
            if not description and amount <= 0:
                continue
            quantity = _item_quantity(item)
            lines.append({
                'description': description, 'quantity': quantity,
                'amount': amount * quantity, 'is_deduction': is_deduction,
                'period_from': '', 'period_to': '',
            })

    gst_percent = _money(data.get('gst_percent'))
    if str(data.get('gst_mode')) != 'including' or gst_percent <= 0:
        return lines

    breakdown = compute_invoice_breakdown(data)
    entered = breakdown['entered']
    if entered == 0 or not lines:
        return lines

    taxable = breakdown['taxable_value']
    # Signed, because a deduction reduces the base it is a share of.
    signed = [(-l['amount'] if l['is_deduction'] else l['amount']) for l in lines]
    scaled = [_js_round(value * taxable / entered) for value in signed]

    remainder = taxable - sum(scaled)
    if remainder != 0:
        biggest = max(range(len(scaled)), key=lambda i: abs(scaled[i]))
        scaled[biggest] += remainder

    for line, value in zip(lines, scaled):
        line['amount'] = abs(value)
    return lines
