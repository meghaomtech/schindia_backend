from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('schindia_auth.urls')),
    path('api/v1/', include('centres.urls')),
    path('api/v1/', include('sessions_app.urls')),
    path('api/v1/', include('children.urls')),
    path('api/v1/', include('progress.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('roles.urls')),
]
