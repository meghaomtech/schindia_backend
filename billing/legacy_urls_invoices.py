from django.urls import path
from . import legacy_views

urlpatterns = [
    path('', legacy_views.invoices_view, name='legacy-invoices'),
    path('/<str:invoice_id>', legacy_views.invoice_detail_view, name='legacy-invoice-detail'),
]
