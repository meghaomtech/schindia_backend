from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'purchases', views.PurchaseViewSet, basename='purchase')

urlpatterns = [
    # Must be before router.urls so 'summary' isn't matched as a pk
    path('invoices/summary/', views.invoice_summary, name='invoice-summary'),
    path('invoices/next-number/', views.next_invoice_number, name='invoice-next-number'),
    # Ledger acts. Must precede router.urls, and each is its own endpoint
    # because each asks its own permission (LEDGER_PERMISSIONS in views.py).
    path('invoices/<uuid:invoice_pk>/ledger/', views.invoice_ledger, name='invoice-ledger'),
    path('invoices/<uuid:invoice_pk>/payments/', views.record_payment, name='invoice-record-payment'),
    path('invoices/<uuid:invoice_pk>/credit-notes/', views.record_credit_note, name='invoice-record-credit-note'),
    path('invoices/<uuid:invoice_pk>/write-offs/', views.record_write_off, name='invoice-record-write-off'),
    path('invoices/<uuid:invoice_pk>/refunds/', views.record_refund, name='invoice-record-refund'),
    path('invoices/<uuid:invoice_pk>/cancel/', views.cancel_invoice, name='invoice-cancel'),
    path('', include(router.urls)),
    # Centre-level invoice endpoints (Req 29)
    path(
        'centres/<uuid:centre_pk>/invoices/',
        views.centre_invoices,
        name='centre-invoices-list'
    ),
    path(
        'centres/<uuid:centre_pk>/invoices/generate-data/',
        views.invoice_generate_data,
        name='centre-invoice-generate-data'
    ),
    path(
        'centres/<uuid:centre_pk>/invoices/debtors/',
        views.centre_debtors,
        name='centre-debtors'
    ),
    path(
        'centres/<uuid:centre_pk>/invoices/payments/',
        views.centre_payments,
        name='centre-payments'
    ),
    # Nested under child
    path(
        'children/<uuid:child_pk>/invoices/',
        views.InvoiceViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-invoices-list'
    ),
    path(
        'children/<uuid:child_pk>/invoices/<uuid:pk>/',
        views.InvoiceViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-invoices-detail'
    ),
    path(
        'children/<uuid:child_pk>/purchases/',
        views.PurchaseViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-purchases-list'
    ),
    path(
        'children/<uuid:child_pk>/purchases/<uuid:pk>/',
        # No 'get': 'retrieve' — PurchaseViewSet doesn't implement retrieve(), and
        # DRF's ViewSetMixin.as_view() resolves every action in this mapping eagerly,
        # so including a missing action here would 500 on PATCH/DELETE too (see PR #15).
        views.PurchaseViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-purchases-detail'
    ),
]
