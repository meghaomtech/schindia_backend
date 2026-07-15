import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
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
        from django.db.models import Count, Q
        from datetime import date
        centre_pk = self.kwargs.get('centre_pk')
        queryset = Role.objects.prefetch_related(
            'permissions',
            'members__user',
        ).all()

        # Annotate active_sessions on members via Prefetch
        from django.db.models import Prefetch
        members_qs = RoleMember.objects.select_related('user').annotate(
            active_sessions=Count(
                'user__teaching_slots',
                filter=Q(user__teaching_slots__start_date__lte=date.today()),
            )
        )
        queryset = queryset.prefetch_related(
            Prefetch('members', queryset=members_qs),
            'permissions',
        )

        if centre_pk:
            queryset = queryset.filter(centre_id=centre_pk)
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RoleCreateSerializer
        return RoleSerializer

    def list(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if use_dynamo() and centre_pk:
            from dynamo_backend.services import roles_db
            roles = roles_db.list_roles(str(centre_pk))
            return Response(roles)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if use_dynamo() and centre_pk:
            from dynamo_backend.services import roles_db
            data = request.data.copy()
            data.pop('centre', None)

            # Validate name (required, max 50 chars)
            name = data.get('name', '').strip()
            if not name:
                return Response(
                    {'name': ['Role name is required.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if len(name) > 50:
                return Response(
                    {'name': ['Role name must be 50 characters or less.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check name uniqueness (case-insensitive) and max 8 roles (Req 14.4)
            existing_roles = roles_db.list_roles(str(centre_pk))
            if len(existing_roles) >= 8:
                return Response(
                    {'name': ['Maximum 8 roles can be created per centre.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            for r in existing_roles:
                if r.get('name', '').lower() == name.lower():
                    return Response(
                        {'name': ['A role with this name already exists at this centre.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            data['name'] = name
            role = roles_db.create_role(str(centre_pk), data)
            return Response(role, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import roles_db
            role = roles_db.get_role(str(kwargs['pk']))
            if not role:
                return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Scope check
            centre_pk = self.kwargs.get('centre_pk')
            if centre_pk and role.get('centre_id') != str(centre_pk):
                return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

            # If renaming, check for duplicate name
            data = request.data.copy()
            new_name = data.get('name', '').strip()
            if new_name:
                if len(new_name) > 50:
                    return Response(
                        {'name': ['Role name must be 50 characters or less.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                cid = role.get('centre_id', str(centre_pk) if centre_pk else '')
                existing_roles = roles_db.list_roles(cid)
                for r in existing_roles:
                    if r.get('id') != str(kwargs['pk']) and r.get('name', '').lower() == new_name.lower():
                        return Response(
                            {'name': ['A role with this name already exists at this centre.']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                data['name'] = new_name

            updated = roles_db.update_role(str(kwargs['pk']), data)
            return Response(updated)
        return super().partial_update(request, *args, **kwargs)

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
        if use_dynamo():
            from dynamo_backend.services import roles_db
            role = roles_db.get_role(str(kwargs['pk']))
            if not role:
                return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Scope check
            centre_pk = self.kwargs.get('centre_pk')
            if centre_pk and role.get('centre_id') != str(centre_pk):
                return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Req 15.10: cannot delete if has members
            if role.get('members'):
                return Response(
                    {'detail': 'Cannot delete this role because it has active members. '
                               'Please reassign them first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Req 15.11: cannot delete last role with admin permissions
            admin_keys = {'people.manage', 'roles.manage'}
            role_perms = {p.get('key') for p in role.get('permissions', []) if p.get('visible')}
            role_has_admin = admin_keys.issubset(role_perms)

            if role_has_admin:
                cid = role.get('centre_id', str(centre_pk) if centre_pk else '')
                all_roles = roles_db.list_roles(cid)
                has_other_admin = False
                for other in all_roles:
                    if other.get('id') == str(kwargs['pk']):
                        continue
                    other_perms = {p.get('key') for p in other.get('permissions', []) if p.get('visible')}
                    if admin_keys.issubset(other_perms):
                        has_other_admin = True
                        break
                if not has_other_admin:
                    return Response(
                        {'detail': 'Cannot delete the last role with full admin permissions. '
                                   'At least one role must retain admin access.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            roles_db.delete_role(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)

        # ORM path
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
    if use_dynamo():
        from dynamo_backend.services import roles_db
        roles = roles_db.list_roles(str(centre_pk))

        people = []
        seen_users = set()
        for role in roles:
            for member in role.get('members', []):
                user_id = member.get('user_id')
                if not user_id:
                    continue

                # Use member data directly (name/email stored on add_member)
                # Collect all roles for multi-role users
                if user_id in seen_users:
                    # Find existing entry and append role
                    for person in people:
                        if person['id'] == user_id:
                            if role.get('name', '') not in person['roles']:
                                person['roles'].append(role.get('name', ''))
                            break
                    continue
                seen_users.add(user_id)

                people.append({
                    'id': user_id,
                    'name': member.get('name', ''),
                    'email': member.get('email', ''),
                    'role': role.get('name', ''),
                    'roles': [role.get('name', '')],
                    'role_id': role.get('id', ''),
                    'active_sessions': 0,  # TODO: requires teacher lookup in sessions service
                })

        # Summary counts per role
        role_counts = {}
        for role in roles:
            role_counts[role.get('name', '')] = len(role.get('members', []))

        return Response({
            'total': len(people),
            'role_counts': role_counts,
            'people': people,
        })

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
    # Define all permission keys grouped by module
    permission_modules = {
        'Centres': ['centres.view', 'centres.edit'],
        'Sessions': ['sessions.view', 'sessions.edit'],
        'Timetable': ['timetable.view', 'timetable.edit'],
        'Children': ['children.view', 'children.edit'],
        'Invoices': ['invoices.view', 'invoices.edit'],
        'People & Roles': ['people.view', 'people.manage', 'roles.view', 'roles.manage'],
    }

    if use_dynamo():
        from dynamo_backend.services import roles_db, centres_db
        centre = centres_db.get_centre(str(centre_pk))
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

        roles = roles_db.list_roles(str(centre_pk))

        matrix = {}
        for module_name, keys in permission_modules.items():
            matrix[module_name] = []
            for key in keys:
                row = {'key': key, 'roles': {}}
                for role in roles:
                    perm = next((p for p in role.get('permissions', []) if p.get('key') == key), None)
                    row['roles'][role['id']] = {
                        'visible': perm.get('visible', False) if perm else False,
                        'edit': perm.get('edit', False) if perm else False,
                    }
                matrix[module_name].append(row)

        roles_data = [{
            'id': r['id'],
            'name': r.get('name', ''),
            'data_scope': r.get('data_scope', 'own'),
            'member_count': len(r.get('members', [])),
        } for r in roles]

        return Response({'roles': roles_data, 'matrix': matrix})

    # ORM path
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

    if use_dynamo():
        from dynamo_backend.services import roles_db, centres_db
        centre = centres_db.get_centre(str(centre_pk))
        if not centre:
            return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

        skipped = []
        for role_id, perms in data.items():
            role = roles_db.get_role(str(role_id))
            if not role or role.get('centre_id') != str(centre_pk):
                skipped.append(role_id)
                continue
            for key, flags in perms.items():
                roles_db.update_permission(str(role_id), key, flags)

        resp = {'detail': 'Permissions saved successfully.'}
        if skipped:
            resp['skipped_role_ids'] = skipped
        return Response(resp)

    # ORM path
    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

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
    if use_dynamo():
        from dynamo_backend.services import roles_db
        role = roles_db.get_role(str(role_pk))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        result = roles_db.update_permission(str(role_pk), key, request.data)
        return Response(result)

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
    if use_dynamo():
        from dynamo_backend.services import roles_db
        role = roles_db.get_role(str(role_pk))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user') or request.data.get('user_id') or request.data.get('id')
        name = request.data.get('name', '')
        email = request.data.get('email', '')

        if not user_id:
            return Response(
                {'detail': 'user or user_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If name/email not provided, try to look up from Users table
        if not name or not email:
            from dynamo_backend.services import auth_db
            user = auth_db.get_user_by_id(str(user_id))
            if user:
                name = name or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                email = email or user.get('email', '')

        # Check per-centre uniqueness (Req 14.8) — user can't be in multiple roles at same centre
        centre_id = role.get('centre_id', '')
        if centre_id:
            all_roles = roles_db.list_roles(centre_id)
            for r in all_roles:
                for m in r.get('members', []):
                    if m.get('user_id') == str(user_id):
                        return Response(
                            {'detail': 'This person already exists at this centre.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

        result = roles_db.add_member(str(role_pk), str(user_id), name=name, email=email)
        if result is None:
            return Response(
                {'detail': 'This person already exists in this role.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Send onboarding email (Req 22)
        _send_onboarding_email_dynamo(
            email=email,
            name=name,
            centre_name=role.get('centre_name', ''),
            role_name=role.get('name', ''),
        )

        return Response(result, status=status.HTTP_201_CREATED)

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
    if use_dynamo():
        from dynamo_backend.services import roles_db
        role = roles_db.get_role(str(role_pk))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        member = next(
            (m for m in role.get('members', []) if m.get('user_id') == str(user_pk)),
            None
        )
        if not member:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

        success = _send_onboarding_email_dynamo(
            email=member.get('email', ''),
            name=member.get('name', ''),
            centre_name=role.get('centre_name', ''),
            role_name=role.get('name', ''),
        )
        if success:
            return Response({'detail': 'Onboarding email sent successfully.'})
        return Response(
            {'detail': 'Failed to send onboarding email.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

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
    if use_dynamo():
        from dynamo_backend.services import roles_db
        role = roles_db.get_role(str(role_pk))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if this is the last member with admin permissions (Req 14.10-11)
        admin_keys = {'people.manage', 'roles.manage'}
        role_perms = {p.get('key') for p in role.get('permissions', []) if p.get('visible')}
        if admin_keys.issubset(role_perms):
            # This is an admin role — check if removing this member leaves 0 admins at this centre
            centre_id = role.get('centre_id', '')
            all_roles = roles_db.list_roles(centre_id) if centre_id else []
            admin_members = set()
            for r in all_roles:
                r_perms = {p.get('key') for p in r.get('permissions', []) if p.get('visible')}
                if admin_keys.issubset(r_perms):
                    for m in r.get('members', []):
                        admin_members.add(m.get('user_id'))
            # If removing this user leaves no admins
            admin_members.discard(str(user_pk))
            if not admin_members:
                return Response(
                    {'detail': 'Cannot remove the last person with admin permissions.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = roles_db.remove_member(str(role_pk), str(user_pk))
        if not result:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
    frontend_url = getattr(settings, 'FRONTEND_URL', None) or (
        settings.CORS_ALLOWED_ORIGINS[0]
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS') and settings.CORS_ALLOWED_ORIGINS
        else 'https://portal.shichida.in'
    )

    subject = f"Welcome to {centre.name} — Shichida India Portal"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"You have been added to {centre.name} as a {role_name}.\n\n"
        f"You can log in to the Shichida India Admin Portal using your "
        f"registered email address. An OTP will be sent to your email for "
        f"secure authentication.\n\n"
        f"Login here: {frontend_url}/login\n\n"
        f"If you have any questions, please contact the centre manager.\n\n"
        f"Best regards,\n"
        f"Shichida India Admin Portal"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to send onboarding email to {user.email}: {e}")
        return False


def _send_onboarding_email_dynamo(email, name, centre_name, role_name):
    """Send onboarding email for Dynamo path (Req 22)."""
    if not email:
        return False

    frontend_url = getattr(settings, 'FRONTEND_URL', None) or (
        settings.CORS_ALLOWED_ORIGINS[0]
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS') and settings.CORS_ALLOWED_ORIGINS
        else 'https://portal.shichida.in'
    )

    subject = f"Welcome to {centre_name} — Shichida India Portal" if centre_name else "Welcome — Shichida India Portal"
    message = (
        f"Hi {name or 'there'},\n\n"
        f"You have been added to {centre_name or 'a centre'} as a {role_name or 'team member'}.\n\n"
        f"You can log in to the Shichida India Admin Portal using your "
        f"registered email address. An OTP will be sent to your email for "
        f"secure authentication.\n\n"
        f"Login here: {frontend_url}/login\n\n"
        f"If you have any questions, please contact the centre manager.\n\n"
        f"Best regards,\n"
        f"Shichida India Admin Portal"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to send onboarding email to {email}: {e}")
        return False
