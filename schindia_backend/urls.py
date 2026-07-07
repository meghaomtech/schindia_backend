from django.contrib import admin
from django.urls import path, include
from billing import legacy_views
from .dashboard import info_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('schindia_auth.urls')),
    path('api/v1/', include('centres.urls')),
    path('api/v1/', include('sessions_app.urls')),
    path('api/v1/', include('children.urls')),
    path('api/v1/', include('progress.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('roles.urls')),
    # Dashboard / Info
    path('api/v1/info/', info_dashboard, name='info-dashboard'),
    # Legacy endpoints for invoice generator (matches old Lambda paths)
    path('centers/', legacy_views.centers_view, name='legacy-centers'),
    path('centers/<str:center_code>/', legacy_views.center_delete_view, name='legacy-center-delete'),
    path('invoices/', legacy_views.invoices_view, name='legacy-invoices'),
    path('invoices/<str:invoice_id>/', legacy_views.invoice_detail_view, name='legacy-invoice-detail'),
]
