from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from centres.models import Centre
from .models import Role, RolePermission, RoleMember
from .serializers import (
    RoleSerializer,
    RoleCreateSerializer,
    RolePermissionSerializer,
    RoleMemberSerializer,
)


class RoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        centre_pk = self.kwargs.get('centre_pk')
        queryset = Role.objects.prefetch_related('permissions', 'members', 'members__user')
        if centre_pk:
            queryset = queryset.filter(centre_id=centre_pk)
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RoleCreateSerializer
        return RoleSerializer

    def perform_create(self, serializer):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            centre = Centre.objects.get(pk=centre_pk)
            serializer.save(centre=centre)
        else:
            serializer.save()


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def update_permission(request, role_pk, key):
    """Update a specific permission's flags for a role."""
    try:
        role = Role.objects.get(pk=role_pk)
    except Role.DoesNotExist:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    permission, created = RolePermission.objects.get_or_create(
        role=role, key=key,
        defaults={'edit': False, 'visible': False}
    )

    serializer = RolePermissionSerializer(permission, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def add_member(request, role_pk):
    """Add a user to a role."""
    try:
        role = Role.objects.get(pk=role_pk)
    except Role.DoesNotExist:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get('user') or request.data.get('user_id')
    if not user_id:
        return Response(
            {'detail': 'user or user_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if RoleMember.objects.filter(role=role, user_id=user_id).exists():
        return Response(
            {'detail': 'User is already a member of this role.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    member = RoleMember.objects.create(role=role, user_id=user_id)
    serializer = RoleMemberSerializer(member)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_member(request, role_pk, user_pk):
    """Remove a user from a role."""
    try:
        member = RoleMember.objects.get(role_id=role_pk, user_id=user_pk)
    except RoleMember.DoesNotExist:
        return Response(
            {'detail': 'Member not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    member.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
