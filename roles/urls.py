from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'roles', views.RoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
    # Nested under centre
    path(
        'centres/<uuid:centre_pk>/roles/',
        views.RoleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='centre-roles-list'
    ),
    path(
        'centres/<uuid:centre_pk>/roles/<uuid:pk>/',
        views.RoleViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='centre-roles-detail'
    ),
    # Permission and member management
    path(
        'roles/<uuid:role_pk>/permissions/<str:key>/',
        views.update_permission,
        name='role-permission-update'
    ),
    path(
        'roles/<uuid:role_pk>/members/',
        views.add_member,
        name='role-member-add'
    ),
    path(
        'roles/<uuid:role_pk>/members/<uuid:user_pk>/',
        views.remove_member,
        name='role-member-remove'
    ),
]
