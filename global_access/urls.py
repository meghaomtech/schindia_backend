from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'global/roles', views.GlobalRoleViewSet, basename='global-role')

urlpatterns = [
    path('', include(router.urls)),
    path('global/people/', views.global_people, name='global-people'),
    path('global/people/add/', views.add_person, name='global-people-add'),
    path('global/people/<uuid:person_pk>/', views.remove_person, name='global-people-remove'),
    path('global/people/<uuid:person_pk>/roles/', views.assign_role, name='global-people-assign-role'),
    path('global/assignments/<uuid:assignment_pk>/', views.remove_assignment, name='global-assignment-remove'),
    path('global/permissions-matrix/', views.permissions_matrix, name='global-permissions-matrix'),
    path('global/permissions-matrix/save/', views.save_permissions_matrix, name='global-permissions-matrix-save'),
    path('global/roles/<uuid:role_pk>/permissions/<str:key>/', views.update_permission, name='global-role-permission-update'),
]
