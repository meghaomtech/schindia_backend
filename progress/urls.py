from django.urls import path
from . import views

urlpatterns = [
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
]
