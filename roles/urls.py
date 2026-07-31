from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'roles', views.RoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
    # Global Roles & Permissions (outside/above individual centres)
    path(
        'global-roles/',
        views.GlobalRoleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='global-roles-list'
    ),
    path(
        'global-roles/directory/',
        views.global_roles_directory,
        name='global-roles-directory'
    ),
    path(
        'global-roles/people/',
        views.global_people,
        name='global-roles-people'
    ),
    path(
        'global-roles/permissions-matrix/',
        views.global_permissions_matrix,
        name='global-roles-permissions-matrix'
    ),
    path(
        'global-roles/permissions-matrix/save/',
        views.save_global_permissions_matrix,
        name='global-roles-permissions-matrix-save'
    ),
    path(
        'global-roles/<uuid:pk>/',
        views.GlobalRoleViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='global-roles-detail'
    ),
    path(
        'global-roles/<uuid:role_pk>/permissions/<str:key>/',
        views.update_global_permission,
        name='global-role-permission-update'
    ),
    path(
        'global-roles/<uuid:role_pk>/members/',
        views.add_global_member,
        name='global-role-member-add'
    ),
    path(
        'global-roles/<uuid:role_pk>/members/<uuid:user_pk>/',
        views.remove_global_member,
        name='global-role-member-remove'
    ),
    path(
        'global-roles/<uuid:role_pk>/members/<uuid:user_pk>/resend-invite/',
        views.resend_global_invite,
        name='global-role-member-resend-invite'
    ),
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
    # People at a centre (flat list across all roles) - Req 14
    path(
        'centres/<uuid:centre_pk>/people/',
        views.centre_people,
        name='centre-people'
    ),
    # Permissions matrix - Req 16
    path(
        'centres/<uuid:centre_pk>/permissions-matrix/',
        views.permissions_matrix,
        name='centre-permissions-matrix'
    ),
    path(
        'centres/<uuid:centre_pk>/permissions-matrix/save/',
        views.save_permissions_matrix,
        name='centre-permissions-matrix-save'
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
    path(
        'roles/<uuid:role_pk>/members/<uuid:user_pk>/resend-invite/',
        views.resend_invite,
        name='role-member-resend-invite'
    ),
]
