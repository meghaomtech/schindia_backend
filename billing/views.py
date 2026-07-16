import logging
from datetime import date, datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import billing_db, centres_db, children_db
from .notifications import send_invoice_email

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            invoices = billing_db.list_invoices(child_id=str(child_pk))
        else:
            invoices = billing_db.list_invoices(user_id=str(request.user.id))
        return Response(invoices)

    def retrieve(self, request, *args, **kwargs):
        invoice = billing_db.get_invoice(str(kwargs['pk']))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(invoice)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user_id'] = str(request.user.id)
        invoice = billing_db.create_invoice(data)
        return Response(invoice, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        invoice = billing_db.update_invoice(str(kwargs['pk']), request.data)
        return Response(invoice)

    def destroy(self, request, *args, **kwargs):
        billing_db.delete_invoice(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark an invoice as sent and record the timestamp."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        if invoice.get('status') == 'Paid':
            return Response(
                {'detail': 'Cannot send a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = billing_db.update_invoice(str(pk), {
            'status': 'Sent',
            'sent_at': datetime.utcnow().isoformat(),
        })
        return Response(updated)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark an invoice as paid."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        updated = billing_db.update_invoice(str(pk), {'status': 'Paid'})
        return Response(updated)

    @action(detail=True, methods=['post'])
    def mark_overdue(self, request, pk=None):
        """Mark an invoice as overdue."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        updated = billing_db.update_invoice(str(pk), {'status': 'Overdue'})
        return Response(updated)

    @action(detail=True, methods=['post'])
    def resend_email(self, request, pk=None):
        """Resend invoice email to parents (Req 23.5)."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

        result = send_invoice_email(invoice)

        if result.get('reason') == 'no_contacts':
            return Response(
                {'detail': 'No parent email associated with this child.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if result.get('reason') == 'all_failed':
            errors = [r.get('error') for r in result.get('results', []) if r.get('error')]
            logger.warning(f"Invoice {invoice.get('id')} resend failed: {errors}")
            return Response(
                {'detail': 'Failed to send invoice email.', 'errors': errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        for entry in result.get('results', []):
            if entry['status'] == 'sent':
                billing_db.add_sent_to(str(pk), 'email', entry['email'])

        return Response({
            'detail': 'Invoice email sent.',
            'results': result.get('results', []),
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_summary(request):
    """Return invoice counts and totals grouped by status."""
    all_invoices = billing_db.list_invoices()

    total_invoices = len(all_invoices)
    status_totals = {}
    for inv in all_invoices:
        s = inv.get('status', 'Draft')
        entry = status_totals.setdefault(s, {'count': 0, 'total_amount': 0.0})
        entry['count'] += 1
        entry['total_amount'] += float(inv.get('total_amount', 0) or 0)

    today_iso = date.today().isoformat()
    overdue_count = sum(
        1 for inv in all_invoices
        if inv.get('status') in ('Sent', 'Draft') and (inv.get('due_date') or '') < today_iso
    )

    return Response({
        'total_invoices': total_invoices,
        'overdue_count': overdue_count,
        'by_status': status_totals,
    })


class PurchaseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if not child_pk:
            return Response([])
        purchases = billing_db.list_purchases(str(child_pk))
        return Response(purchases)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if not child_pk:
            return Response({'detail': 'A child is required to create a purchase.'}, status=status.HTTP_400_BAD_REQUEST)
        purchase = billing_db.create_purchase(str(child_pk), request.data.copy())
        return Response(purchase, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        purchase = billing_db.update_purchase(str(kwargs['pk']), request.data)
        return Response(purchase)

    def destroy(self, request, *args, **kwargs):
        billing_db.delete_purchase(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Centre-Level Invoice Endpoints (Req 29, 30)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_invoices(request, centre_pk):
    """
    List all invoices for a centre with filtering (Req 29.8-10).
    Query params: status, date_from, date_to, search
    """
    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Get all children at this centre, then their invoices
    children = children_db.list_children(str(centre_pk))
    child_ids = {c['id'] for c in children}

    # Summary stats over ALL centre invoices (before user filters)
    all_centre_invoices = []
    for child_id in child_ids:
        all_centre_invoices.extend(billing_db.list_invoices(child_id=child_id))

    total_outstanding = sum(
        float(i.get('total_amount', 0))
        for i in all_centre_invoices
        if i.get('status') in ('Sent', 'Draft', 'Overdue')
    )
    total_paid = sum(
        float(i.get('total_amount', 0))
        for i in all_centre_invoices
        if i.get('status') == 'Paid'
    )
    overdue_count = sum(1 for i in all_centre_invoices if i.get('status') == 'Overdue')

    # Apply filters for the response list
    all_invoices = list(all_centre_invoices)

    inv_status = request.query_params.get('status')
    if inv_status and inv_status != 'All':
        all_invoices = [i for i in all_invoices if i.get('status') == inv_status]

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from:
        all_invoices = [i for i in all_invoices if (i.get('invoice_date') or '') >= date_from]
    if date_to:
        all_invoices = [i for i in all_invoices if (i.get('invoice_date') or '') <= date_to]

    search = request.query_params.get('search')
    if search:
        search_lower = search.lower()
        all_invoices = [
            i for i in all_invoices
            if search_lower in (i.get('student_name') or '').lower()
            or search_lower in (i.get('number') or '').lower()
        ]

    return Response({
        'summary': {
            'total_invoices': len(all_centre_invoices),
            'total_outstanding': total_outstanding,
            'total_paid': total_paid,
            'overdue_count': overdue_count,
        },
        'invoices': all_invoices,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_generate_data(request, centre_pk):
    """
    Return pre-populated data for invoice generation (Req 29.3, 29.7, 30.1-2).
    Returns centre details + list of children at this centre with parent info.
    """
    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    bank = centre.get('bank_details', {}) or {}
    centre_data = {
        'centre_code': centre.get('system_id', ''),
        'centre_name': centre.get('name', ''),
        'centre_location': centre.get('city', ''),
        'full_address': f"{centre.get('street_address', '')}, {centre.get('city', '')}, {centre.get('postcode', '')}",
        'email': centre.get('email', ''),
        'phone': centre.get('phone', ''),
        'gst_number': centre.get('vat_number', ''),
        'bank_name': bank.get('bank_name', ''),
        'account_number': bank.get('account_number', ''),
        'ifsc_code': bank.get('ifsc_code', ''),
        'upi_id': bank.get('upi_id', ''),
        'account_holder_name': bank.get('account_holder_name', ''),
    }

    children = children_db.list_children(str(centre_pk))
    children_data = []
    for child in children:
        name_parts = [child.get('first_name', ''), child.get('middle_name', ''), child.get('last_name', '')]
        student_name = ' '.join(p for p in name_parts if p)
        # Find parent contact
        contacts = child.get('contacts', [])
        parent = next(
            (c for c in contacts if c.get('invite_as') in ('Parent', 'Guardian')),
            None
        )
        children_data.append({
            'id': child.get('id', ''),
            'student_name': student_name,
            'parent_name': parent.get('name', '') if parent else '',
            'parent_email': parent.get('email', '') if parent else '',
            'parent_phone': parent.get('phone', '') if parent else '',
            'session_name': child.get('session_name', ''),
            'date_of_birth': child.get('date_of_birth', ''),
        })

    bank_details_complete = bool(
        bank.get('account_holder_name') and
        bank.get('bank_name') and
        bank.get('account_number') and
        bank.get('ifsc_code')
    )

    return Response({
        'centre': centre_data,
        'children': children_data,
        'bank_details_complete': bank_details_complete,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_payments(request, centre_pk):
    """
    Payment tracking for a centre (Req 29.12).
    Returns invoices marked as paid with payment info.
    """
    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    children = children_db.list_children(str(centre_pk))

    payments = []
    for child in children:
        invoices = billing_db.list_invoices(child_id=child['id'])
        for inv in invoices:
            if inv.get('status') != 'Paid':
                continue
            student_name = inv.get('student_name') or f"{child.get('first_name', '')} {child.get('last_name', '')}"
            payments.append({
                'invoice_id': inv.get('id', ''),
                'invoice_number': inv.get('number', ''),
                'student_name': student_name,
                'amount': float(inv.get('total_amount', 0) or 0),
                'payment_date': (inv.get('updated_at') or '')[:10],
                'due_date': inv.get('due_date', ''),
            })

    payments.sort(key=lambda p: p['payment_date'], reverse=True)
    return Response({'payments': payments})
