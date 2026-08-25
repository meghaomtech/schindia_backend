from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'global/roles', views.GlobalRoleViewSet, basename='global-role')

urlpatterns = [
    path('', include(router.urls)),
    path('global/people/', views.global_people, name='global-people'),
    path('global/people/add/', views.add_person, name='global-people-add'),
    # Static segments must precede the <uuid:person_pk> patterns below, or
    # "onboard"/"documents" would be matched as a person id.
    path('global/people/onboard/', views.onboard_staff, name='global-people-onboard'),
    path('global/people/documents/upload/', views.upload_staff_document,
         name='global-people-document-upload'),
    path('global/people/<uuid:person_pk>/', views.person_detail, name='global-person-detail'),
    path('global/people/<uuid:person_pk>/documents/<int:index>/', views.staff_document,
         name='global-staff-document'),
    path('global/people/<uuid:person_pk>/roles/', views.assign_role, name='global-people-assign-role'),
    path('global/assignments/<uuid:assignment_pk>/', views.remove_assignment, name='global-assignment-remove'),
    path('global/permissions-matrix/', views.permissions_matrix, name='global-permissions-matrix'),
    path('global/permissions-matrix/save/', views.save_permissions_matrix, name='global-permissions-matrix-save'),
    path('global/roles/<uuid:role_pk>/permissions/<str:key>/', views.update_permission, name='global-role-permission-update'),
]
