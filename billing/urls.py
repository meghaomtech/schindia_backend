from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'purchases', views.PurchaseViewSet, basename='purchase')

urlpatterns = [
    # Must be before router.urls so 'summary' isn't matched as a pk
    path('invoices/summary/', views.invoice_summary, name='invoice-summary'),
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
        views.PurchaseViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-purchases-detail'
    ),
]
