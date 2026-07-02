from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views

urlpatterns = [
    # Auth endpoints matching frontend expectations
    path('register/', views.register, name='register'),
    path('request-access/', views.request_access, name='request-access'),
    path('login/', views.login_view, name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
    path('change-password/', views.change_password, name='change-password'),
    # Access request management (root only)
    path('access-requests/', views.access_requests_list, name='access-requests'),
    path('access-requests/<uuid:pk>/approve/', views.approve_request, name='approve-request'),
    path('access-requests/<uuid:pk>/reject/', views.reject_request, name='reject-request'),
]
