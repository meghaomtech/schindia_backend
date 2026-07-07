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
