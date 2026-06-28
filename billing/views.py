from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from schindia_auth.permissions import IsApprovedUser
from children.models import Child
from .models import Invoice, Purchase
from .serializers import (
    InvoiceListSerializer,
    InvoiceCreateSerializer,
    PurchaseSerializer,
)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        queryset = Invoice.objects.prefetch_related('items', 'sent_to')
        if child_pk:
            queryset = queryset.filter(child_id=child_pk)
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceCreateSerializer
        return InvoiceListSerializer


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
