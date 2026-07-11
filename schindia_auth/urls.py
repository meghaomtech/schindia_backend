from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views

urlpatterns = [
    # Access request (person requests access with email + password)
    path('request-access/', views.request_access, name='request-access'),
    path('request-root-access/', views.request_root_access, name='request-root-access'),
    # Login: Step 1 - email + password → validates creds → sends OTP
    path('login/', views.login_send_otp, name='login'),
    # Login: Step 2 - email + OTP code → returns JWT
    path('login/verify/', views.otp_verify, name='login-verify'),
    # Token management
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('logout/', views.logout_view, name='logout'),
    # User info
    path('me/', views.me, name='me'),
    # Notification preferences (Req 25.4)
    path('notification-preferences/', views.notification_preferences, name='notification-preferences'),
    # Access request management (root/admin only)
    path('access-requests/', views.access_requests_list, name='access-requests'),
    path('access-requests/<uuid:pk>/approve/', views.approve_request, name='approve-request'),
    path('access-requests/<uuid:pk>/reject/', views.reject_request, name='reject-request'),
]
