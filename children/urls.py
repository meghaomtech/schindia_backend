from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import move_requests, views

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
        views.ContactViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-contacts-detail'
    ),
    # Child moves between centres. Requesting one is scoped to the child's
    # own centre; deciding one is organisation-level and so sits at the top,
    # not under a centre that would imply a centre may decide its own.
    path(
        'children/<uuid:child_pk>/move-requests/',
        move_requests.child_move_requests,
        name='child-move-requests'
    ),
    path(
        'children/<uuid:child_pk>/move-preview/',
        move_requests.child_move_preview,
        name='child-move-preview'
    ),
    path(
        'move-requests/',
        move_requests.move_requests_list,
        name='move-requests-list'
    ),
    # Deciding from the email. No session: the signed token in the link is
    # the credential, and the page behind it asks for a click before acting.
    path(
        'move-requests/email-action/',
        move_requests.email_move_decision,
        name='move-request-email-action'
    ),
    path(
        'move-requests/<uuid:pk>/approve/',
        move_requests.approve_move_request,
        name='move-request-approve'
    ),
    path(
        'move-requests/<uuid:pk>/reject/',
        move_requests.reject_move_request,
        name='move-request-reject'
    ),
    # Nested enrolment endpoints under child
    path(
        'children/<uuid:child_pk>/enrolments/',
        views.EnrolmentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-enrolments-list'
    ),
    path(
        'children/<uuid:child_pk>/enrolments/<uuid:pk>/',
        # partial_update is implemented on the viewset — access checks and the
        # rescheduled notification included — but was never mapped here, so
        # moving a child to another slot answered 405.
        views.EnrolmentViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-enrolments-detail'
    ),
]
