import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from centres.models import Centre
from sessions_app.models import SessionSlot
from .models import Role, RolePermission, RoleMember
from .serializers import (
    RoleSerializer,
    RoleCreateSerializer,
    RolePermissionSerializer,
    RoleMemberSerializer,
)

logger = logging.getLogger(__name__)


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

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deletion if:
        - Role has active members (Req 15.10)
        - Role is the last one with full admin permissions (Req 15.11)
        """
        role = self.get_object()

        if role.members.exists():
            return Response(
                {'detail': 'Cannot delete this role because it has active members. '
                           'Please reassign them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if this is the last role with full admin permissions
        admin_keys = {'people.manage', 'roles.manage'}
        role_has_admin = set(
            role.permissions.filter(
                key__in=admin_keys, visible=True
            ).values_list('key', flat=True)
        ) == admin_keys

        if role_has_admin:
            # Check if there's another role at this centre with admin perms
            other_admin_roles = Role.objects.filter(
                centre=role.centre,
            ).exclude(pk=role.pk).filter(
                permissions__key__in=admin_keys,
                permissions__visible=True,
            ).distinct()

            # Need at least one other role that has BOTH admin keys
            has_other_admin = False
            for other_role in other_admin_roles:
                other_admin_perms = set(
                    other_role.permissions.filter(
                        key__in=admin_keys, visible=True
                    ).values_list('key', flat=True)
                )
                if other_admin_perms == admin_keys:
                    has_other_admin = True
                    break

            if not has_other_admin:
                return Response(
                    {'detail': 'Cannot delete the last role with full admin permissions. '
                               'At least one role must retain admin access.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().destroy(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_people(request, centre_pk):
    """
    Get all people assigned to a centre across all roles.
    Returns a flat list with user info and their role.
    Matches frontend's People tab in Roles & Permissions page (Req 14).
    """
    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    members = RoleMember.objects.filter(
        role__centre=centre
    ).select_related('user', 'role').order_by('role__name', 'user__first_name')

    people = []
    seen_users = set()
    for member in members:
        user = member.user
        if user.id in seen_users:
            continue
        seen_users.add(user.id)
        # Active sessions = timetable slots the person is assigned to as teacher
        active_sessions = SessionSlot.objects.filter(teachers=user).count()
        people.append({
            'id': str(user.id),
            'name': user.get_full_name(),
            'email': user.email,
            'role': member.role.name,
            'role_id': str(member.role.id),
            'active_sessions': active_sessions,
        })

    # Summary counts per role
    role_counts = {}
    for person in people:
        role_name = person['role']
        role_counts[role_name] = role_counts.get(role_name, 0) + 1

    return Response({
        'total': len(people),
        'role_counts': role_counts,
        'people': people,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def permissions_matrix(request, centre_pk):
    """
    Return the full permissions matrix for a centre (Req 16).
    Roles as columns, permissions as rows grouped by module.
    """
    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    roles = Role.objects.filter(centre=centre).prefetch_related('permissions')

    # Define all permission keys grouped by module
    permission_modules = {
        'Centres': ['centres.view', 'centres.edit'],
        'Sessions': ['sessions.view', 'sessions.edit'],
        'Timetable': ['timetable.view', 'timetable.edit'],
        'Children': ['children.view', 'children.edit'],
        'Invoices': ['invoices.view', 'invoices.edit'],
        'People & Roles': ['people.view', 'people.manage', 'roles.view', 'roles.manage'],
    }

    # Build the matrix
    matrix = {}
    for module_name, keys in permission_modules.items():
        matrix[module_name] = []
        for key in keys:
            row = {
                'key': key,
                'roles': {}
            }
            for role in roles:
                perm = role.permissions.filter(key=key).first()
                row['roles'][str(role.id)] = {
                    'visible': perm.visible if perm else False,
                    'edit': perm.edit if perm else False,
                }
            matrix[module_name].append(row)

    # Role metadata
    roles_data = []
    for role in roles:
        roles_data.append({
            'id': str(role.id),
            'name': role.name,
            'data_scope': role.data_scope,
            'member_count': role.members.count(),
        })

    return Response({
        'roles': roles_data,
        'matrix': matrix,
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def save_permissions_matrix(request, centre_pk):
    """
    Bulk update permissions for all roles at a centre.
    Expected body: { "role_id": { "key": {"visible": bool, "edit": bool}, ... }, ... }
    Enforces Req 16.7: at least one role must retain people.manage + roles.manage.
    """
    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data  # { role_id: { key: {visible, edit} } }

    # Validate: at least one role must keep people.manage + roles.manage
    admin_keys = {'people.manage', 'roles.manage'}
    any_role_has_admin = False

    for role_id, perms in data.items():
        has_people_manage = perms.get('people.manage', {}).get('visible', False)
        has_roles_manage = perms.get('roles.manage', {}).get('visible', False)
        if has_people_manage and has_roles_manage:
            any_role_has_admin = True
            break

    if not any_role_has_admin:
        return Response(
            {'detail': 'At least one role must retain people.manage and roles.manage permissions.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Apply changes
    for role_id, perms in data.items():
        try:
            role = Role.objects.get(pk=role_id, centre=centre)
        except Role.DoesNotExist:
            continue

        for key, flags in perms.items():
            perm, created = RolePermission.objects.get_or_create(
                role=role, key=key,
                defaults={'visible': False, 'edit': False}
            )
            perm.visible = flags.get('visible', perm.visible)
            perm.edit = flags.get('edit', perm.edit)
            perm.save()

    return Response({'detail': 'Permissions saved successfully.'})


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
    """
    Add a user to a role (Req 14.6).
    Also sends onboarding email (Req 22).
    """
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

    # Check if user already exists at this centre (Req 14.8)
    existing_at_centre = RoleMember.objects.filter(
        role__centre=role.centre, user_id=user_id
    ).exists()
    if existing_at_centre:
        return Response(
            {'detail': 'This person already exists at this centre.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    member = RoleMember.objects.create(role=role, user_id=user_id)

    # Send onboarding email (Req 22)
    _send_onboarding_email(member)

    serializer = RoleMemberSerializer(member)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def resend_invite(request, role_pk, user_pk):
    """Resend onboarding email (Req 22.5)."""
    try:
        member = RoleMember.objects.get(role_id=role_pk, user_id=user_pk)
    except RoleMember.DoesNotExist:
        return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    success = _send_onboarding_email(member)
    if success:
        return Response({'detail': 'Onboarding email sent successfully.'})
    return Response(
        {'detail': 'Failed to send onboarding email.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_member(request, role_pk, user_pk):
    """Remove a user from a role (Req 14.10-11)."""
    try:
        member = RoleMember.objects.get(role_id=role_pk, user_id=user_pk)
    except RoleMember.DoesNotExist:
        return Response(
            {'detail': 'Member not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    member.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _send_onboarding_email(member):
    """
    Send onboarding email to a new person (Req 22).
    Contains: centre name, assigned role, login link, OTP instructions.
    """
    user = member.user
    centre = member.role.centre
    role_name = member.role.name

    subject = f"Welcome to {centre.name} — Shichida India Portal"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"You have been added to {centre.name} as a {role_name}.\n\n"
        f"You can log in to the Shichida India Admin Portal using your "
        f"registered email address. An OTP will be sent to your email for "
        f"secure authentication.\n\n"
        f"Login here: {settings.CORS_ALLOWED_ORIGINS[0] if hasattr(settings, 'CORS_ALLOWED_ORIGINS') and settings.CORS_ALLOWED_ORIGINS else 'https://portal.shichida.in'}/login\n\n"
        f"If you have any questions, please contact the centre manager.\n\n"
        f"Best regards,\n"
        f"Shichida India Admin Portal"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to send onboarding email to {user.email}: {e}")
        return False
