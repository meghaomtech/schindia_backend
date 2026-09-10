"""
The invoice as a PDF.

This is the document a parent actually receives. It is built from the stored
invoice and the same line/total rules the on-screen preview uses (totals.py,
mirroring the frontend's invoiceCalc.ts), so the copy reception looked at
before sending and the copy that lands in the parent's inbox cannot disagree
about what is owed.

Nothing here reads request data or works out prices of its own — hand it an
invoice dict as billing_db.get_invoice() returns it, plus the centre and child
it belongs to, and it renders exactly that.
"""

import io
import logging
import os
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .totals import compute_invoice_breakdown, invoice_lines

logger = logging.getLogger(__name__)

COMPANY_LEGAL = (
    'Shichida India licensed operating brand of Brain Astra Pvt Ltd. '
    'Company registration number CIN U72900KA2022PTC158571.'
)

# Matches the section headings on the on-screen invoice.
HEADING_BLUE = colors.HexColor('#1a5fa8')
BORDER_GREY = colors.HexColor('#d1d5db')
HEADER_FILL = colors.HexColor('#f9fafb')
CREDIT_RED = colors.HexColor('#dc2626')
MUTED = colors.HexColor('#6b7280')


class InvoicePdfError(RuntimeError):
    """Raised when the invoice document could not be rendered."""


def _logo_path():
    """
    The brand mark, when this deployment ships one.

    Configurable because the backend may be deployed without the frontend's
    public directory beside it; absent a file the document falls back to a
    text wordmark rather than failing to render.
    """
    configured = getattr(settings, 'INVOICE_PDF_LOGO', '') or os.environ.get(
        'INVOICE_PDF_LOGO', '')
    candidates = [configured] if configured else []
    candidates.append(
        os.path.join(os.path.dirname(settings.BASE_DIR), 'frontend', 'public',
                     'Shichida India logo.png')
    )
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _fmt_date(value):
    """dd/mm/yyyy, as the printed invoice shows dates. Blank stays blank."""
    if not value:
        return ''
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(value)


def _fmt_inr(amount):
    """
    Rupees with Indian digit grouping (1,23,456), matching toLocaleString('en-IN')
    on screen. The sign is written "Rs." rather than the rupee glyph: the fonts
    built into every PDF reader have no glyph for it, and the amount a family
    owes must not print as a black box.
    """
    whole = int(amount)
    sign = '-' if whole < 0 else ''
    digits = str(abs(whole))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ','.join(groups + [tail])
    return f"Rs. {sign}{digits}"


def _fmt_number(value):
    """Whole numbers print without a trailing .0 — quantities and GST rates."""
    number = float(value)
    return str(int(number)) if number == int(number) else str(number)


def _escape(value):
    """Paragraph markup is XML — an ampersand in a centre name must not break it."""
    return (
        str(value if value is not None else '')
        .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    )


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle('InvBody', parent=base['Normal'], fontSize=9,
                          leading=12.5, textColor=colors.HexColor('#1a1a1a'))
    return {
        'body': body,
        'title': ParagraphStyle('InvTitle', parent=body, fontSize=20,
                                leading=24, alignment=TA_CENTER,
                                fontName='Helvetica-Bold'),
        'wordmark': ParagraphStyle('InvWordmark', parent=body, fontSize=15,
                                   leading=18, fontName='Helvetica-Bold',
                                   textColor=HEADING_BLUE),
        'meta': ParagraphStyle('InvMeta', parent=body, alignment=TA_RIGHT),
        'section': ParagraphStyle('InvSection', parent=body, fontSize=9.5,
                                  leading=13, fontName='Helvetica-Bold',
                                  textColor=HEADING_BLUE, spaceAfter=3),
        'cell': ParagraphStyle('InvCell', parent=body, fontSize=9, leading=11.5),
        'cellRight': ParagraphStyle('InvCellR', parent=body, fontSize=9,
                                    leading=11.5, alignment=TA_RIGHT),
        'cellCentre': ParagraphStyle('InvCellC', parent=body, fontSize=9,
                                     leading=11.5, alignment=TA_CENTER),
        'note': ParagraphStyle('InvNote', parent=body, fontSize=8.5,
                               textColor=MUTED),
        'thanks': ParagraphStyle('InvThanks', parent=body, fontSize=9,
                                 alignment=TA_CENTER, textColor=MUTED,
                                 fontName='Helvetica-Oblique'),
        'footer': ParagraphStyle('InvFooter', parent=body, fontSize=7.5,
                                 leading=10, alignment=TA_CENTER,
                                 textColor=MUTED),
    }


def _labelled(style, pairs):
    """The 'Label: value' lines used in the Bill To and Payment blocks."""
    return [
        Paragraph(f"{_escape(label)}: <b>{_escape(value)}</b>", style)
        for label, value in pairs if str(value or '').strip()
    ]


def _header(styles):
    path = _logo_path()
    if path:
        try:
            width, height = ImageReader(path).getSize()
            target_height = 18 * mm
            return Image(path, width=width * target_height / height,
                         height=target_height, hAlign='LEFT')
        except Exception:
            # A missing or unreadable logo must not cost a parent their bill.
            logger.warning("Invoice PDF: could not load logo at %s", path,
                           exc_info=True)
    return Paragraph('Shichida India', styles['wordmark'])


def _party_details(invoice, centre, child):
    """
    Who the invoice is for, and which centre raised it.

    Child and centre records win where they exist; the values typed onto the
    invoice are the fallback, because an invoice raised before a child is
    enrolled has no records to resolve and must still print a payer.
    """
    student = (
        f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
        if child else ''
    ) or invoice.get('student_name', '')

    centre_name = (centre or {}).get('name') or invoice.get('center_code', '')
    location = (centre or {}).get('city') or invoice.get('center_location', '')
    if centre_name and location:
        centre_line = f"{centre_name} - {location}"
    else:
        centre_line = centre_name or location

    return student, centre_name, centre_line


def _gst_percent(invoice):
    try:
        return float(invoice.get('gst_percent') or 0)
    except (TypeError, ValueError):
        return 0.0


def build_invoice_pdf(invoice, centre=None, child=None):
    """
    Render `invoice` and return the PDF as bytes.

    Raises InvoicePdfError when the document cannot be produced. Callers must
    treat that as a failure to send — an invoice with no document did not
    reach anybody, whatever the mail server says.
    """
    if not invoice:
        raise InvoicePdfError('No invoice to render.')
    try:
        return _render(invoice, centre, child)
    except Exception as exc:
        logger.error(
            "Invoice PDF generation failed for %s: %s",
            invoice.get('number') or invoice.get('id'), exc, exc_info=True,
        )
        raise InvoicePdfError(str(exc)) from exc


def _render(invoice, centre, child):
    styles = _styles()
    lines = invoice_lines(invoice)
    breakdown = compute_invoice_breakdown(invoice)
    gst_percent = _gst_percent(invoice)
    student, centre_name, centre_line = _party_details(invoice, centre, child)

    story = [
        _header(styles),
        Spacer(1, 6 * mm),
        Paragraph('INVOICE', styles['title']),
        Spacer(1, 4 * mm),
        Paragraph(
            "Invoice #: <b>{}</b><br/>Date: {}<br/>Due Date: {}".format(
                _escape(invoice.get('number') or invoice.get('invoice_number', '')),
                _escape(_fmt_date(invoice.get('invoice_date'))),
                _escape(_fmt_date(invoice.get('due_date'))),
            ),
            styles['meta'],
        ),
        Spacer(1, 6 * mm),
        Paragraph('BILL TO', styles['section']),
    ]

    story.extend(_labelled(styles['body'], [
        ('Student', student),
        ('Parent/Guardian', invoice.get('parent_name', '')),
        ('Center', centre_line),
        ('Address', (centre or {}).get('street_address') or invoice.get('full_address', '')),
        ('City', invoice.get('city', '')),
        ('Contact', invoice.get('contact', '')),
        ('Email', invoice.get('email', '')),
    ]))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph('REGISTRATION DETAILS', styles['section']))
    story.append(_items_table(lines, breakdown, gst_percent, styles))
    story.append(Spacer(1, 5 * mm))

    bank = (centre or {}).get('bank_details') or {}
    payment_rows = _labelled(styles['body'], [
        ('Account Holder', bank.get('account_holder_name')),
        ('Bank', bank.get('bank_name') or invoice.get('bank_name', '')),
        ('Account Number', bank.get('account_number') or invoice.get('account_number', '')),
        ('IFSC Code', bank.get('ifsc_code') or invoice.get('ifsc_code', '')),
        ('UPI ID', bank.get('upi_id') or invoice.get('upi_id', '')),
    ])
    if payment_rows:
        story.append(Paragraph('PAYMENT DETAILS', styles['section']))
        story.extend(payment_rows)
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        'Please reference your child full name or invoice number', styles['note']))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        'Thank you for registering with Shichida India!', styles['thanks']))
    story.append(Spacer(1, 4 * mm))

    gst_number = (centre or {}).get('vat_number') or invoice.get('gst_number', '')
    footer = COMPANY_LEGAL + (f" GST Number: {gst_number}" if gst_number else '')
    story.append(Paragraph(_escape(footer), styles['footer']))

    buffer = io.BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=12 * mm,
        title=f"Invoice {invoice.get('number', '')}".strip(),
        author=centre_name or 'Shichida India',
        subject=f"Invoice for {student}".strip(),
    ).build(story)
    return buffer.getvalue()


def _items_table(lines, breakdown, gst_percent, styles):
    rows = [[
        Paragraph('<b>Description</b>', styles['cell']),
        Paragraph('<b>Quantity</b>', styles['cellCentre']),
        Paragraph('<b>Amount</b>', styles['cellRight']),
    ]]
    commands = [
        ('GRID', (0, 0), (-1, -1), 0.6, BORDER_GREY),
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]

    if not lines:
        rows.append([
            Paragraph('<i>No charges on this invoice.</i>', styles['cell']),
            Paragraph('', styles['cellCentre']),
            Paragraph(_fmt_inr(0), styles['cellRight']),
        ])

    for line in lines:
        description = _escape(line['description'])
        if line['is_deduction']:
            description = f"{description} (Credit)"
        if line['period_from'] or line['period_to']:
            description += "<br/>{} to {}".format(
                _escape(_fmt_date(line['period_from'])),
                _escape(_fmt_date(line['period_to'])),
            )
        amount = _fmt_inr(line['amount'])
        if line['is_deduction']:
            # Shown as a negative in red on screen, so it reads the same here.
            amount = f"- {amount}"
            commands.append(
                ('TEXTCOLOR', (0, len(rows)), (-1, len(rows)), CREDIT_RED))
        rows.append([
            Paragraph(description, styles['cell']),
            Paragraph(_fmt_number(line['quantity']), styles['cellCentre']),
            Paragraph(amount, styles['cellRight']),
        ])

    def summary(label, value, bold=False):
        rows.append([
            Paragraph(f"<b>{label}</b>" if bold else label, styles['cell']),
            Paragraph('', styles['cellCentre']),
            Paragraph(f"<b>{_fmt_inr(value)}</b>" if bold else _fmt_inr(value),
                      styles['cellRight']),
        ])
        commands.append(('SPAN', (0, len(rows) - 1), (1, len(rows) - 1)))

    # Subtotal and GST only appear when there is something to explain, exactly
    # as on screen — a plain invoice with no tax shows its total and no more.
    if gst_percent > 0 or breakdown['debit_brought_forward'] > 0:
        summary('Subtotal', breakdown['taxable_value'])
        if gst_percent > 0:
            summary(f"GST ({_fmt_number(gst_percent)}%)", breakdown['gst_amount'])
        if breakdown['debit_brought_forward'] > 0:
            summary('Debit Brought Forward', breakdown['debit_brought_forward'])

    summary('TOTAL', breakdown['total'], bold=True)
    commands.append(
        ('BACKGROUND', (0, len(rows) - 1), (-1, len(rows) - 1), HEADER_FILL))

    table = Table(rows, colWidths=[100 * mm, 25 * mm, 35 * mm], repeatRows=1)
    table.setStyle(TableStyle(commands))
    return table


def invoice_pdf_filename(invoice):
    """
    `Invoice-<number>.pdf`, sanitised — an attachment name becomes a filename
    on someone else's machine, so no path separators travel in it.
    """
    number = str(invoice.get('number') or invoice.get('id') or 'invoice')
    safe = ''.join(ch for ch in number if ch.isalnum() or ch in ('-', '_'))
    return f"Invoice-{safe or 'invoice'}.pdf"
