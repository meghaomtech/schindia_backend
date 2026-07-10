from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views

urlpatterns = [
    # Access request (person requests access with email + password)
    path('request-access/', views.request_access, name='request-access'),
    path('request-root-access/', views.request_root_access, name='request-root-access'),
    # OTP Login (the ONLY login method - no password login)
    path('login/', views.otp_request, name='login'),  # Step 1: enter email, get OTP
    path('login/verify/', views.otp_verify, name='login-verify'),  # Step 2: enter OTP, get JWT
    # Token management
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('logout/', views.logout_view, name='logout'),
    # User info
    path('me/', views.me, name='me'),
    # OTP endpoints (alternate naming for backward compat)
    path('otp/request/', views.otp_request, name='otp-request'),
    path('otp/verify/', views.otp_verify, name='otp-verify'),
    # Notification preferences (Req 25.4)
    path('notification-preferences/', views.notification_preferences, name='notification-preferences'),
    # Access request management (root/admin only)
    path('access-requests/', views.access_requests_list, name='access-requests'),
    path('access-requests/<uuid:pk>/approve/', views.approve_request, name='approve-request'),
    path('access-requests/<uuid:pk>/reject/', views.reject_request, name='reject-request'),
]
