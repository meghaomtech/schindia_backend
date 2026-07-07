from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Standalone session/slot endpoints (for PATCH/DELETE by ID)
router.register(r'sessions', views.SessionViewSet, basename='session-standalone')
router.register(r'slots', views.SessionSlotViewSet, basename='slot-standalone')

urlpatterns = [
    # Nested under centre
    path(
        'centres/<uuid:centre_pk>/sessions/',
        views.SessionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='centre-sessions-list'
    ),
    path(
        'centres/<uuid:centre_pk>/sessions/<uuid:pk>/',
        views.SessionViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='centre-sessions-detail'
    ),
    path(
        'centres/<uuid:centre_pk>/slots/',
        views.SessionSlotViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='centre-slots-list'
    ),
    path(
        'centres/<uuid:centre_pk>/slots/<uuid:pk>/',
        views.SessionSlotViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='centre-slots-detail'
    ),
    path(
        'centres/<uuid:centre_pk>/slots/generate/',
        views.generate_slots,
        name='centre-slots-generate'
    ),
    path(
        'centres/<uuid:centre_pk>/timetable/',
        views.timetable,
        name='centre-timetable'
    ),
] + router.urls
