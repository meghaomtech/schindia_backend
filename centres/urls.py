from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'centres', views.CentreViewSet, basename='centre')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'centres/<uuid:centre_pk>/rooms/',
        views.RoomViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='centre-rooms-list'
    ),
    path(
        'centres/<uuid:centre_pk>/rooms/<uuid:pk>/',
        views.RoomViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='centre-rooms-detail'
    ),
]
