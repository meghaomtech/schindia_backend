from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'attendances', views.AttendanceViewSet, basename='attendance-standalone')
router.register(r'course-progress', views.CourseProgressViewSet, basename='course-progress-standalone')

urlpatterns = [
    path('', include(router.urls)),
    # Journey entries nested under child
    path(
        'children/<uuid:child_pk>/journey/',
        views.JourneyEntryViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-journey-list'
    ),
    path(
        'children/<uuid:child_pk>/journey/<uuid:pk>/',
        views.JourneyEntryViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-journey-detail'
    ),
    # Notes nested under child
    path(
        'children/<uuid:child_pk>/notes/',
        views.ChildNoteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-notes-list'
    ),
    path(
        'children/<uuid:child_pk>/notes/<uuid:pk>/',
        views.ChildNoteViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-notes-detail'
    ),
    # Attendance nested under child
    path(
        'children/<uuid:child_pk>/attendance/',
        views.AttendanceViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-attendance-list'
    ),
    path(
        'children/<uuid:child_pk>/attendance/<uuid:pk>/',
        views.AttendanceViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-attendance-detail'
    ),
    # Course progress nested under child
    path(
        'children/<uuid:child_pk>/course-progress/',
        views.CourseProgressViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='child-course-progress-list'
    ),
    path(
        'children/<uuid:child_pk>/course-progress/<uuid:pk>/',
        views.CourseProgressViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='child-course-progress-detail'
    ),
    # Child activity feed (unified timeline)
    path(
        'children/<uuid:child_pk>/activity/',
        views.child_activity_feed,
        name='child-activity-feed'
    ),
    # Child stats summary
    path(
        'children/<uuid:child_pk>/stats/',
        views.child_stats,
        name='child-stats'
    ),
]
