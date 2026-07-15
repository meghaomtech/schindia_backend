import logging

from django.utils import timezone
from django.db.models import Sum, Count, Q

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
from children.models import Child
from .models import Invoice, InvoiceSentTo, Purchase

logger = logging.getLogger(__name__)
from .serializers import (
    InvoiceListSerializer,
    InvoiceCreateSerializer,
    PurchaseSerializer,
)
from .notifications import send_invoice_email


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        queryset = Invoice.objects.prefetch_related('items', 'sent_to')
        if child_pk:
            queryset = queryset.filter(child_id=child_pk)
        invoice_status = self.request.query_params.get('status')
        if invoice_status:
            queryset = queryset.filter(status=invoice_status)
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceCreateSerializer
        return InvoiceListSerializer

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo():
            from dynamo_backend.services import billing_db
            if child_pk:
                invoices = billing_db.list_invoices(child_id=str(child_pk))
            else:
                invoices = billing_db.list_invoices(user_id=str(request.user.id))
            return Response(invoices)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            invoice = billing_db.get_invoice(str(kwargs['pk']))
            if not invoice:
                return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(invoice)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            data = request.data.copy()
            data['user_id'] = str(request.user.id)
            invoice = billing_db.create_invoice(data)
            return Response(invoice, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            invoice = billing_db.update_invoice(str(kwargs['pk']), request.data)
            return Response(invoice)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            billing_db.delete_invoice(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        invoice = serializer.save(user=self.request.user)
        result = send_invoice_email(invoice)
        for entry in result.get('results', []):
            if entry['status'] == 'sent':
                InvoiceSentTo.objects.create(
                    invoice=invoice,
                    channel='email',
                    target=entry['email'],
                )
        if result.get('sent'):
            invoice.status = 'Sent'
            invoice.sent_at = timezone.now()
            invoice.save(update_fields=['status', 'sent_at'])

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark an invoice as sent and record the timestamp."""
        invoice = self.get_object()
        if invoice.status == 'Paid':
            return Response(
                {'detail': 'Cannot send a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = 'Sent'
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=['status', 'sent_at', 'updated_at'])
        serializer = InvoiceListSerializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark an invoice as paid."""
        invoice = self.get_object()
        invoice.status = 'Paid'
        invoice.save(update_fields=['status', 'updated_at'])
        serializer = InvoiceListSerializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_overdue(self, request, pk=None):
        """Mark an invoice as overdue."""
        invoice = self.get_object()
        invoice.status = 'Overdue'
        invoice.save(update_fields=['status', 'updated_at'])
        serializer = InvoiceListSerializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resend_email(self, request, pk=None):
        """Resend invoice email to parents (Req 23.5)."""
        invoice = self.get_object()
        result = send_invoice_email(invoice)

        if result.get('reason') == 'no_contacts':
            return Response(
                {'detail': 'No parent email associated with this child.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if result.get('reason') == 'all_failed':
            # Log and return the actual errors
            errors = [r.get('error') for r in result.get('results', []) if r.get('error')]
            logger.warning(f"Invoice {invoice.id} resend failed: {errors}")
            return Response(
                {'detail': 'Failed to send invoice email.', 'errors': errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Record sent_to entries
        for entry in result.get('results', []):
            if entry['status'] == 'sent':
                InvoiceSentTo.objects.create(
                    invoice=invoice,
                    channel='email',
                    target=entry['email'],
                )
        return Response({
            'detail': 'Invoice email sent.',
            'results': result.get('results', []),
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_summary(request):
    """Return invoice counts and totals grouped by status."""
    total_invoices = Invoice.objects.count()
    status_counts = Invoice.objects.values('status').annotate(count=Count('id'))

    # Total amounts by status
    status_totals = {}
    for entry in status_counts:
        s = entry['status']
        total = Invoice.objects.filter(
            status=s
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        status_totals[s] = {
            'count': entry['count'],
            'total_amount': float(total),
        }

    overdue_count = Invoice.objects.filter(
        status__in=['Sent', 'Draft'],
        due_date__lt=timezone.now().date(),
    ).count()

    return Response({
        'total_invoices': total_invoices,
        'overdue_count': overdue_count,
        'by_status': status_totals,
    })


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return Purchase.objects.filter(child_id=child_pk)
        return Purchase.objects.all()

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import billing_db
            purchases = billing_db.list_purchases(str(child_pk))
            return Response(purchases)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import billing_db
            purchase = billing_db.create_purchase(str(child_pk), request.data.copy())
            return Response(purchase, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            purchase = billing_db.update_purchase(str(kwargs['pk']), request.data)
            return Response(purchase)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import billing_db
            billing_db.delete_purchase(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            serializer.save(child=child)
        else:
            serializer.save()


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
    if use_dynamo():
        from dynamo_backend.services import billing_db, centres_db, children_db
        centre = centres_db.get_centre(str(centre_pk))
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Get all children at this centre, then their invoices
        children = children_db.list_children(str(centre_pk))
        child_ids = {c['id'] for c in children}

        # Get invoices for all children at this centre
        all_invoices = []
        for child_id in child_ids:
            all_invoices.extend(billing_db.list_invoices(child_id=child_id))

        # Apply filters
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

        # Summary stats (computed over all centre invoices before user filters)
        # Re-fetch unfiltered for summary
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

        return Response({
            'summary': {
                'total_invoices': len(all_centre_invoices),
                'total_outstanding': total_outstanding,
                'total_paid': total_paid,
                'overdue_count': overdue_count,
            },
            'invoices': all_invoices,
        })

    # ORM path
    from centres.models import Centre
    from django.shortcuts import get_object_or_404
    centre = get_object_or_404(Centre, pk=centre_pk)

    # Validate date params
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from:
        try:
            from datetime import datetime
            datetime.strptime(date_from, '%Y-%m-%d')
        except ValueError:
            return Response({'detail': 'Invalid date_from format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
    if date_to:
        try:
            from datetime import datetime
            datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            return Response({'detail': 'Invalid date_to format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    # Summary stats over ALL centre invoices (before user filters)
    all_centre_invoices = Invoice.objects.filter(child__centre=centre)
    total_outstanding = all_centre_invoices.filter(
        status__in=['Sent', 'Draft', 'Overdue']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = all_centre_invoices.filter(
        status='Paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    overdue_count = all_centre_invoices.filter(status='Overdue').count()
    total_count = all_centre_invoices.count()

    # Filtered queryset for the response list
    invoices = all_centre_invoices.prefetch_related('items', 'sent_to').select_related('child')

    inv_status = request.query_params.get('status')
    if inv_status and inv_status != 'All':
        invoices = invoices.filter(status=inv_status)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)

    search = request.query_params.get('search')
    if search:
        invoices = invoices.filter(
            Q(child__first_name__icontains=search) |
            Q(child__last_name__icontains=search) |
            Q(number__icontains=search)
        )

    serializer = InvoiceListSerializer(invoices, many=True)

    return Response({
        'summary': {
            'total_invoices': total_count,
            'total_outstanding': float(total_outstanding),
            'total_paid': float(total_paid),
            'overdue_count': overdue_count,
        },
        'invoices': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_generate_data(request, centre_pk):
    """
    Return pre-populated data for invoice generation (Req 29.3, 29.7, 30.1-2).
    Returns centre details + list of children at this centre with parent info.
    """
    if use_dynamo():
        from dynamo_backend.services import centres_db, children_db
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

    # ORM path
    from centres.models import Centre
    from django.shortcuts import get_object_or_404
    centre = get_object_or_404(Centre, pk=centre_pk)

    bank = centre.bank_details or {}
    centre_data = {
        'centre_code': centre.system_id,
        'centre_name': centre.name,
        'centre_location': centre.city,
        'full_address': f"{centre.street_address}, {centre.city}, {centre.postcode}",
        'email': centre.email,
        'phone': centre.phone,
        'gst_number': centre.vat_number,
        'bank_name': bank.get('bank_name', ''),
        'account_number': bank.get('account_number', ''),
        'ifsc_code': bank.get('ifsc_code', ''),
        'upi_id': bank.get('upi_id', ''),
        'account_holder_name': bank.get('account_holder_name', ''),
    }

    children = Child.objects.filter(
        centre=centre
    ).prefetch_related('contacts').select_related('session')

    children_data = []
    for child in children:
        parent = child.contacts.filter(
            invite_as__in=['Parent', 'Guardian']
        ).first()

        student_name = ' '.join(p for p in [child.first_name, child.middle_name, child.last_name] if p)
        children_data.append({
            'id': str(child.id),
            'student_name': student_name,
            'parent_name': parent.name if parent else '',
            'parent_email': parent.email if parent else '',
            'parent_phone': parent.phone if parent else '',
            'session_name': child.session.name if child.session else '',
            'date_of_birth': child.date_of_birth.isoformat(),
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
    from centres.models import Centre

    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    paid_invoices = Invoice.objects.filter(
        child__centre=centre,
        status='Paid',
    ).select_related('child').order_by('-updated_at')

    payments = []
    for inv in paid_invoices:
        payments.append({
            'invoice_id': str(inv.id),
            'invoice_number': inv.number,
            'student_name': inv.student_name or f"{inv.child.first_name} {inv.child.last_name}",
            'amount': float(inv.total_amount),
            'payment_date': inv.updated_at.date().isoformat(),
            'due_date': inv.due_date.isoformat(),
        })

    return Response({'payments': payments})
