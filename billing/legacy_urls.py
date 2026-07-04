from django.urls import path
from . import legacy_views

urlpatterns = [
    path('', legacy_views.centers_view, name='legacy-centers'),
    path('/<str:center_code>', legacy_views.center_delete_view, name='legacy-center-delete'),
]
