from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('setup-root/', views.setup_root, name='setup-root'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
    path('access-requests/', views.access_requests_list, name='access-requests'),
    path('access-requests/<uuid:pk>/approve/', views.approve_request, name='approve-request'),
    path('access-requests/<uuid:pk>/reject/', views.reject_request, name='reject-request'),
]
