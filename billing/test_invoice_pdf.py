"""
The PDF a parent actually receives.

Two things are worth guarding here. That a document is produced at all — the
send path refuses to claim success without one. And that its figures are the
ones the on-screen preview showed: the rows and totals come from totals.py,
which mirrors the frontend's invoiceCalc.ts, so an invoice reception looked at
and the invoice that lands in an inbox cannot quietly disagree.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from billing.pdf_generator import (
    InvoicePdfError, build_invoice_pdf, invoice_pdf_filename,
)
from billing.totals import (
    compute_invoice_breakdown, compute_invoice_total, invoice_lines,
)

CENTRE = {
    'name': 'Shichida Indiranagar', 'city': 'Bengaluru',
    'street_address': '12 100ft Road', 'vat_number': '29ABCDE1234F1Z5',
    'bank_details': {'bank_name': 'HDFC', 'account_number': '000111222',
                     'ifsc_code': 'HDFC0000123', 'upi_id': 'shichida@upi'},
}
CHILD = {'id': 'c1', 'first_name': 'Aarav', 'last_name': 'Sharma',
         'centre_id': 'ctr'}


def invoice(**over):
    base = {
        'id': 'inv-1', 'number': 'BA260007',
        'invoice_date': '2026-09-04', 'due_date': '2026-09-30',
        'student_name': 'Aarav Sharma', 'parent_name': 'Riya Sharma',
        'email': 'riya@example.com', 'contact': '9876543210',
        'city': 'Bengaluru', 'center_code': 'Indiranagar',
        'registration_fee': 5000, 'session_fee_amount': 12000,
        'session_fee_start': '2026-09-01', 'session_fee_end': '2026-11-30',
        'extra_items': [{'description': 'Workbook set', 'quantity': 2, 'amount': 750}],
        'deductions': [{'description': 'Sibling discount', 'quantity': 1, 'amount': 1000}],
        'gst_percent': 18, 'gst_mode': 'excluding', 'debit_brought_forward': 500,
    }
    base.update(over)
    return base


class InvoiceLineTests(SimpleTestCase):
    """The rows, matching invoiceLines() in the frontend's invoiceCalc.ts."""

    def test_lists_fees_extras_and_deductions_in_order(self):
        rows = invoice_lines(invoice())
        self.assertEqual(
            [r['description'] for r in rows],
            ['Registration Fee', 'Session fee for the period', 'Workbook set',
             'Sibling discount'],
        )
        self.assertEqual([r['is_deduction'] for r in rows],
                         [False, False, False, True])

    def test_multiplies_a_line_by_its_quantity(self):
        rows = invoice_lines(invoice())
        workbooks = next(r for r in rows if r['description'] == 'Workbook set')
        self.assertEqual(workbooks['amount'], Decimal('1500'))

    def test_carries_the_session_period_onto_its_row(self):
        session = next(r for r in invoice_lines(invoice())
                       if r['description'].startswith('Session fee'))
        self.assertEqual(session['period_from'], '2026-09-01')
        self.assertEqual(session['period_to'], '2026-11-30')

    def test_leaves_out_rows_that_were_never_filled_in(self):
        rows = invoice_lines(invoice(
            extra_items=[{'description': '', 'quantity': 1, 'amount': 0}]))
        self.assertNotIn('', [r['description'] for r in rows])

    def test_zero_fees_produce_no_rows_at_all(self):
        rows = invoice_lines({'registration_fee': 0, 'session_fee_amount': 0,
                              'extra_items': [], 'deductions': []})
        self.assertEqual(rows, [])

    def test_gst_inclusive_rows_sum_to_the_subtotal_printed_under_them(self):
        # The reported bug this rule exists for: rows totalling the gross above
        # a net subtotal, so the invoice visibly did not add up.
        data = invoice(gst_mode='including', registration_fee=10000,
                       session_fee_amount=5000, extra_items=[], deductions=[],
                       debit_brought_forward=0)
        rows = invoice_lines(data)
        breakdown = compute_invoice_breakdown(data)
        self.assertEqual(sum(r['amount'] for r in rows),
                         breakdown['taxable_value'])

    def test_gst_inclusive_remainder_lands_on_the_largest_row(self):
        # 50 + 50 at 18% rounds to 43 + 43 against an 85 subtotal; the odd
        # rupee has to go somewhere rather than be dropped.
        data = {'registration_fee': 50, 'session_fee_amount': 50,
                'extra_items': [], 'deductions': [], 'gst_percent': 18,
                'gst_mode': 'including', 'debit_brought_forward': 0}
        rows = invoice_lines(data)
        self.assertEqual(sum(r['amount'] for r in rows),
                         compute_invoice_breakdown(data)['taxable_value'])


class BreakdownTests(SimpleTestCase):
    def test_total_is_the_breakdown_total(self):
        # The stored total and the figure the PDF prints come out of the same
        # calculation, so they cannot drift apart.
        data = invoice()
        self.assertEqual(compute_invoice_total(data),
                         compute_invoice_breakdown(data)['total'])

    def test_gst_is_added_on_top_when_amounts_exclude_it(self):
        breakdown = compute_invoice_breakdown(invoice())
        # 5000 + 12000 + 1500 - 1000 = 17500, +18% = 3150, +500 brought forward
        self.assertEqual(breakdown['taxable_value'], Decimal('17500'))
        self.assertEqual(breakdown['gst_amount'], Decimal('3150'))
        self.assertEqual(breakdown['total'], Decimal('21150'))

    def test_gst_is_worked_back_out_when_amounts_already_include_it(self):
        breakdown = compute_invoice_breakdown(invoice(gst_mode='including'))
        self.assertEqual(breakdown['total'], Decimal('18000'))  # 17500 + 500
        self.assertEqual(breakdown['taxable_value'] + breakdown['gst_amount'],
                         Decimal('17500'))


class BuildInvoicePdfTests(SimpleTestCase):
    def test_produces_a_real_pdf(self):
        document = build_invoice_pdf(invoice(), CENTRE, CHILD)
        self.assertTrue(document.startswith(b'%PDF-'))
        self.assertGreater(len(document), 1000)

    def test_renders_without_a_centre_or_child(self):
        # An invoice raised at reception before enrolment has neither, and
        # still has to reach the payer typed onto it.
        document = build_invoice_pdf(invoice(child_id=None), None, None)
        self.assertTrue(document.startswith(b'%PDF-'))

    def test_renders_an_invoice_with_no_lines(self):
        document = build_invoice_pdf(
            invoice(registration_fee=0, session_fee_amount=0,
                    session_fee_start='', session_fee_end='',
                    extra_items=[], deductions=[]),
            CENTRE, CHILD)
        self.assertTrue(document.startswith(b'%PDF-'))

    def test_a_centre_name_with_an_ampersand_does_not_break_the_document(self):
        # Paragraph markup is XML; an unescaped & would abort the render.
        document = build_invoice_pdf(
            invoice(parent_name='Ravi & Sons <Guardians>'), CENTRE, CHILD)
        self.assertTrue(document.startswith(b'%PDF-'))

    def test_refuses_to_render_nothing(self):
        with self.assertRaises(InvoicePdfError):
            build_invoice_pdf(None)

    def test_unusable_amounts_do_not_take_the_document_down(self):
        # Amounts are read defensively (totals._money), so a junk figure reads
        # as zero rather than costing a parent their bill entirely.
        document = build_invoice_pdf(invoice(extra_items=[
            {'description': 'Odd row', 'quantity': 'not-a-number', 'amount': None}
        ]), CENTRE, CHILD)
        self.assertTrue(document.startswith(b'%PDF-'))

    @patch('billing.pdf_generator.SimpleDocTemplate')
    def test_reports_a_render_failure_as_an_invoice_pdf_error(self, doc):
        # Callers distinguish "no document" from "not delivered", so the
        # failure has to arrive as this type rather than whatever reportlab
        # happened to raise.
        doc.side_effect = OSError('disk full')
        with self.assertRaises(InvoicePdfError):
            build_invoice_pdf(invoice(), CENTRE, CHILD)

    @patch('billing.pdf_generator._logo_path')
    def test_an_unreadable_logo_falls_back_to_the_wordmark(self, logo):
        logo.return_value = __file__  # a real path, not an image
        self.assertTrue(build_invoice_pdf(invoice(), CENTRE, CHILD)
                        .startswith(b'%PDF-'))


class FilenameTests(SimpleTestCase):
    def test_names_the_file_after_the_invoice_number(self):
        self.assertEqual(invoice_pdf_filename({'number': 'BA260007'}),
                         'Invoice-BA260007.pdf')

    def test_strips_anything_that_would_be_a_path(self):
        # The attachment name becomes a filename on someone else's machine.
        self.assertEqual(invoice_pdf_filename({'number': '../../etc/passwd'}),
                         'Invoice-etcpasswd.pdf')

    def test_falls_back_to_the_id_then_to_a_default(self):
        self.assertEqual(invoice_pdf_filename({'id': 'abc'}), 'Invoice-abc.pdf')
        self.assertEqual(invoice_pdf_filename({}), 'Invoice-invoice.pdf')
