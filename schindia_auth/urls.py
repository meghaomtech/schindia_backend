from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views

urlpatterns = [
    # Auth endpoints
    path('register/', views.register, name='register'),
    path('request-access/', views.request_access, name='request-access'),
    path('request-root-access/', views.request_root_access, name='request-root-access'),
    path('login/', views.login_view, name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
    path('change-password/', views.change_password, name='change-password'),
    # OTP email verification (Req 21: register -> OTP verify -> set password)
    path('otp/request/', views.otp_request, name='otp-request'),
    path('otp/verify/', views.otp_verify, name='otp-verify'),
    # Forgot password (Req 26.6)
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('reset-password/', views.reset_password, name='reset-password'),
    # Notification preferences (Req 25.4)
    path('notification-preferences/', views.notification_preferences, name='notification-preferences'),
    # Access request management (root only)
    path('access-requests/', views.access_requests_list, name='access-requests'),
    path('access-requests/<uuid:pk>/approve/', views.approve_request, name='approve-request'),
    path('access-requests/<uuid:pk>/reject/', views.reject_request, name='reject-request'),
]
