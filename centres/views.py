from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from schindia_auth.permissions import IsApprovedUser
from .models import Centre, Room
from .serializers import CentreListSerializer, CentreCreateSerializer, RoomSerializer


class CentreViewSet(viewsets.ModelViewSet):
    queryset = Centre.objects.prefetch_related('rooms').all()
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CentreCreateSerializer
        return CentreListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        return Room.objects.filter(centre_id=self.kwargs['centre_pk'])

    def perform_create(self, serializer):
        centre = Centre.objects.get(pk=self.kwargs['centre_pk'])
        serializer.save(centre=centre)

    def destroy(self, request, *args, **kwargs):
        """Prevent removal of rooms with timetable assignments (Req 5.7)."""
        room = self.get_object()
        # Check if room has any timetable slots assigned
        if room.slots.exists():
            return Response(
                {
                    'detail': 'Cannot remove this room because it is currently assigned '
                              'to one or more timetable entries. Please reassign or delete '
                              'those entries first.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
