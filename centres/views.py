from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
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

    def list(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            centres = centres_db.list_centres()
            return Response(centres)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            centre = centres_db.get_centre(str(kwargs['pk']))
            if not centre:
                return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(centre)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data.copy()
            centre = centres_db.create_centre(data)
            return Response(centre, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            centre = centres_db.update_centre(str(kwargs['pk']), request.data)
            if not centre:
                return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(centre)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            centres_db.delete_centre(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        return Room.objects.filter(centre_id=self.kwargs['centre_pk'])

    def list(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            rooms = centres_db.get_rooms(str(kwargs['centre_pk']))
            return Response(rooms)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            data = request.data.copy()
            room = centres_db.create_room(str(kwargs['centre_pk']), data)
            return Response(room, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import centres_db
            room = centres_db.update_room(str(kwargs['pk']), request.data)
            return Response(room)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Prevent removal of rooms with timetable assignments (Req 5.7)."""
        if use_dynamo():
            from dynamo_backend.services import centres_db, sessions_db
            centre_pk = str(kwargs['centre_pk'])
            room_id = str(kwargs['pk'])
            # Check if room has slots
            slots = sessions_db.list_slots(centre_pk)
            room_slots = [s for s in slots if s.get('room_id') == room_id]
            if room_slots:
                return Response(
                    {'detail': 'Cannot remove this room because it is assigned to timetable entries.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            centres_db.delete_room(room_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        room = self.get_object()
        if room.slots.exists():
            return Response(
                {'detail': 'Cannot remove this room because it is assigned to timetable entries.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
