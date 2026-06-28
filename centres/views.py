from rest_framework import viewsets, status
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


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        return Room.objects.filter(centre_id=self.kwargs['centre_pk'])

    def perform_create(self, serializer):
        centre = Centre.objects.get(pk=self.kwargs['centre_pk'])
        serializer.save(centre=centre)
