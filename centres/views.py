from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import centres_db, sessions_db, children_db, roles_db
from roles.permissions_catalog import ALL_PERMISSION_KEYS
from .serializers import CentreCreateSerializer, RoomSerializer


class CentreViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    serializer_class = CentreCreateSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = {'request': self.request}
        return CentreCreateSerializer(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        centres = centres_db.list_centres()
        return Response(centres)

    def retrieve(self, request, *args, **kwargs):
        centre = centres_db.get_centre(str(kwargs['pk']))
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(centre)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()

        # Pop rooms — create them separately
        rooms_data = data.pop('rooms', [])
        centre = centres_db.create_centre(data)

        # Create rooms
        for room_data in rooms_data:
            centres_db.create_room(centre['id'], room_data)

        # Create default Admin role with every permission in the catalog (Req 15.4)
        permissions = [
            {'key': key, 'edit': True, 'visible': True}
            for key in ALL_PERMISSION_KEYS
        ]
        role_data = {
            'name': 'Admin',
            'description': 'Full administrative access',
            'data_scope': 'all',
            'permissions': permissions,
        }
        role = roles_db.create_role(centre['id'], role_data)

        # Assign requesting user to admin role
        if request.user and request.user.is_authenticated:
            user_id = str(request.user.id)
            name = request.user.get_full_name() if hasattr(request.user, 'get_full_name') else ''
            email = request.user.email if hasattr(request.user, 'email') else ''
            roles_db.add_member(role['id'], user_id, name=name, email=email)

        # Refresh centre to include rooms
        centre = centres_db.get_centre(centre['id'])
        return Response(centre, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        centre = centres_db.get_centre(str(kwargs['pk']))
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Validate through serializer (partial=True for PATCH)
        serializer = self.get_serializer(instance=centre, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = centres_db.update_centre(str(kwargs['pk']), serializer.validated_data)
        if not updated:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(updated)

    def destroy(self, request, *args, **kwargs):
        centre_id = str(kwargs['pk'])

        centre = centres_db.get_centre(centre_id)
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Block deletion if centre has dependent data
        sessions = sessions_db.list_sessions(centre_id)
        if sessions:
            return Response(
                {'detail': 'Cannot delete centre with existing sessions. Remove all sessions first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        children = [c for c in children_db.list_children(centre_id)]
        if children:
            return Response(
                {'detail': 'Cannot delete centre with enrolled children. Remove all children first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roles = roles_db.list_roles(centre_id)
        has_members = any(r.get('members') for r in roles)
        if has_members:
            return Response(
                {'detail': 'Cannot delete centre with active role members. Remove all members first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Safe to delete — clean up rooms and empty roles
        for room in centre.get('rooms', []):
            centres_db.delete_room(room['id'])
        for role in roles:
            roles_db.delete_role(role['id'])

        centres_db.delete_centre(centre_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    serializer_class = RoomSerializer

    def list(self, request, *args, **kwargs):
        rooms = centres_db.get_rooms(str(kwargs['centre_pk']))
        return Response(rooms)

    def retrieve(self, request, *args, **kwargs):
        room = centres_db.get_room(str(kwargs['pk']))
        if not room or room.get('centre_id') != str(kwargs['centre_pk']):
            return Response({'detail': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(room)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # Validate room name
        name = data.get('name', '').strip()
        if not name:
            return Response(
                {'name': ['Room name is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(name) > 50:
            return Response(
                {'name': ['Room name must be 50 characters or less.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check name uniqueness within centre
        centre_pk = str(kwargs['centre_pk'])
        existing_rooms = centres_db.get_rooms(centre_pk)
        for r in existing_rooms:
            if r.get('name', '').lower() == name.lower():
                return Response(
                    {'name': ['A room with this name already exists at this centre.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data['name'] = name
        room = centres_db.create_room(centre_pk, data)
        return Response(room, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        data = request.data.copy()

        # Validate room name if provided
        name = data.get('name')
        if name is not None:
            name = name.strip()
            if not name:
                return Response(
                    {'name': ['Room name is required.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if len(name) > 50:
                return Response(
                    {'name': ['Room name must be 50 characters or less.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Check uniqueness within centre
            centre_pk = str(kwargs['centre_pk'])
            existing_rooms = centres_db.get_rooms(centre_pk)
            for r in existing_rooms:
                if r.get('id') != str(kwargs['pk']) and r.get('name', '').lower() == name.lower():
                    return Response(
                        {'name': ['A room with this name already exists at this centre.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            data['name'] = name

        room = centres_db.update_room(str(kwargs['pk']), data)
        if not room:
            return Response({'detail': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(room)

    def destroy(self, request, *args, **kwargs):
        """Prevent removal of rooms with timetable assignments (Req 5.7)."""
        room_id = str(kwargs['pk'])
        # Use room_id-index for efficient lookup instead of scanning all centre slots
        room_slots = sessions_db.list_slots_by_room(room_id)
        if room_slots:
            return Response(
                {'detail': 'Cannot remove this room because it is assigned to timetable entries.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        centres_db.delete_room(room_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
