from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'children', views.ChildViewSet, basename='child')
router.register(r'contacts', views.ContactViewSet, basename='contact-standalone')
router.register(r'enrolments', views.EnrolmentViewSet, basename='enrolment-standalone')

urlpatterns = [
    path('', include(router.urls)),
    # Children nested under centre
    path(
        'centres/<uuid:centre_pk>/children/',
        views.ChildViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='centre-children-list'
    ),
    path(
        'centres/<uuid:centre_pk>/children/<uuid:pk>/',
        views.ChildViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='centre-children-detail'
    ),
    # Nested contact endpoints under child
    path(
        'children/<uuid:child_pk>/contacts/',
        views.ContactViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-contacts-list'
    ),
    path(
        'children/<uuid:child_pk>/contacts/<uuid:pk>/',
        views.ContactViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-contacts-detail'
    ),
    # Nested enrolment endpoints under child
    path(
        'children/<uuid:child_pk>/enrolments/',
        views.EnrolmentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-enrolments-list'
    ),
    path(
        'children/<uuid:child_pk>/enrolments/<uuid:pk>/',
        views.EnrolmentViewSet.as_view({'delete': 'destroy'}),
        name='child-enrolments-detail'
    ),
]
