from django.utils import timezone
from django.db.models import Sum, Count, Q

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from children.models import Child
from .models import Invoice, InvoiceSentTo, Purchase
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

        # Filter by status if provided
        invoice_status = self.request.query_params.get('status')
        if invoice_status:
            queryset = queryset.filter(status=invoice_status)

        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceCreateSerializer
        return InvoiceListSerializer

    def perform_create(self, serializer):
        invoice = serializer.save(user=self.request.user)
        # Auto-send invoice email to parents (Req 23.1)
        results = send_invoice_email(invoice)
        for result in results:
            InvoiceSentTo.objects.create(
                invoice=invoice,
                channel='email',
                target=result['email'],
            )
        if results:
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
        results = send_invoice_email(invoice)
        if not results:
            return Response(
                {'detail': 'No parent email associated with this child.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Record sent_to entries
        for result in results:
            InvoiceSentTo.objects.create(
                invoice=invoice,
                channel='email',
                target=result['email'],
            )
        return Response({
            'detail': 'Invoice email sent.',
            'results': results,
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
    from centres.models import Centre

    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    invoices = Invoice.objects.filter(
        child__centre=centre
    ).prefetch_related('items', 'sent_to').select_related('child')

    # Filters (Req 29.9)
    inv_status = request.query_params.get('status')
    if inv_status and inv_status != 'All':
        invoices = invoices.filter(status=inv_status)

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
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

    # Summary statistics (Req 29.10)
    total_count = invoices.count()
    total_outstanding = invoices.filter(
        status__in=['Sent', 'Draft', 'Overdue']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = invoices.filter(
        status='Paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    overdue_count = invoices.filter(status='Overdue').count()

    # Serialize
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
    from centres.models import Centre

    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Centre details auto-populated (Req 29.3)
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

    # Children at this centre with parent info (Req 30.1-2)
    children = Child.objects.filter(
        centre=centre
    ).prefetch_related('contacts').select_related('session')

    children_data = []
    for child in children:
        # Find parent contact
        parent = child.contacts.filter(
            invite_as__in=['Parent', 'Guardian']
        ).first()

        children_data.append({
            'id': str(child.id),
            'student_name': f"{child.first_name} {child.middle_name} {child.last_name}".replace('  ', ' ').strip(),
            'parent_name': parent.name if parent else '',
            'parent_email': parent.email if parent else '',
            'parent_phone': parent.phone if parent else '',
            'session_name': child.session.name if child.session else '',
            'date_of_birth': child.date_of_birth.isoformat(),
        })

    # Check if bank details are configured (Req 18.6)
    bank_details_complete = bool(
        bank.get('account_holder_name') and
        bank.get('bank_name') and
        bank.get('account_number')
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
