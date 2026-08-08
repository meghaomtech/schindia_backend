import logging
import uuid

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import roles_db, centres_db, auth_db
from dynamo_backend.services.roles_service import GLOBAL_SCOPE
from notifications.mailer import send_permission_updated_email
from .permissions_catalog import PERMISSION_CATEGORIES
from .global_roles import (
    DEFAULT_KINDS,
    KIND_AFFILIATE,
    KIND_CENTRE_MANAGER,
    ensure_default_global_roles,
    get_global_role_by_kind,
)

logger = logging.getLogger(__name__)


def _notify_permission_changes(role_id, changed_summary):
    """Send a permissions-updated email for a role after its permission flags changed."""
    if not changed_summary:
        return
    role = roles_db.get_role(str(role_id))
    if role:
        send_permission_updated_email(role, changed_summary)


class RoleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if not centre_pk:
            return Response([])
        roles = roles_db.list_roles(str(centre_pk))
        return Response(roles)

    def retrieve(self, request, *args, **kwargs):
        role = roles_db.get_role(str(kwargs['pk']))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk and role.get('centre_id') != str(centre_pk):
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(role)

    def create(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if not centre_pk:
            return Response({'detail': 'A centre is required to create a role.'}, status=status.HTTP_400_BAD_REQUEST)

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

    def partial_update(self, request, *args, **kwargs):
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

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deletion if:
        - Role has active members (Req 15.10)
        - Role is the last one with full admin permissions (Req 15.11)
        """
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


class GlobalRoleViewSet(viewsets.ViewSet):
    """Roles & Permissions outside/above individual centres (Global Settings).

    Same shape and rules as centre-level roles (RoleViewSet above), scoped to
    the GLOBAL_SCOPE sentinel instead of a centre_pk. The 3 default roles
    (Super Admin, Centre Manager, Affiliate) can be edited but not deleted —
    Centre Creation's manager dropdown / affiliate multi-select depend on the
    Centre Manager and Affiliate roles existing.
    """
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        roles = ensure_default_global_roles()
        return Response(roles)

    def retrieve(self, request, *args, **kwargs):
        role = roles_db.get_role(str(kwargs['pk']))
        if not role or role.get('centre_id') != GLOBAL_SCOPE:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(role)

    def create(self, request, *args, **kwargs):
        ensure_default_global_roles()
        data = request.data.copy()
        data.pop('centre', None)
        data.pop('kind', None)
        data['kind'] = 'custom'
        data['is_default'] = False

        name = data.get('name', '').strip()
        if not name:
            return Response({'name': ['Role name is required.']}, status=status.HTTP_400_BAD_REQUEST)
        if len(name) > 50:
            return Response(
                {'name': ['Role name must be 50 characters or less.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_roles = roles_db.list_roles(GLOBAL_SCOPE)
        for r in existing_roles:
            if r.get('name', '').lower() == name.lower():
                return Response(
                    {'name': ['A global role with this name already exists.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data['name'] = name
        role = roles_db.create_role(GLOBAL_SCOPE, data)
        return Response(role, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        role = roles_db.get_role(str(kwargs['pk']))
        if not role or role.get('centre_id') != GLOBAL_SCOPE:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        # kind and default-ness are structural, not editable via this endpoint
        data.pop('kind', None)
        data.pop('is_default', None)

        new_name = data.get('name', '').strip()
        if new_name:
            if len(new_name) > 50:
                return Response(
                    {'name': ['Role name must be 50 characters or less.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            existing_roles = roles_db.list_roles(GLOBAL_SCOPE)
            for r in existing_roles:
                if r.get('id') != str(kwargs['pk']) and r.get('name', '').lower() == new_name.lower():
                    return Response(
                        {'name': ['A global role with this name already exists.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            data['name'] = new_name

        updated = roles_db.update_role(str(kwargs['pk']), data)
        return Response(updated)

    def destroy(self, request, *args, **kwargs):
        role = roles_db.get_role(str(kwargs['pk']))
        if not role or role.get('centre_id') != GLOBAL_SCOPE:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        if role.get('is_default') or role.get('kind') in DEFAULT_KINDS:
            return Response(
                {'detail': 'This is a default global role and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role.get('members'):
            return Response(
                {'detail': 'Cannot delete this role because it has active members. '
                           'Please reassign them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roles_db.delete_role(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def global_roles_directory(request):
    """
    Flat lists of Centre Manager and Affiliate accounts, for Centre
    Creation's "Centre Manager" dropdown and "Assign Affiliates" multi-select.
    """
    manager_role = get_global_role_by_kind(KIND_CENTRE_MANAGER)
    affiliate_role = get_global_role_by_kind(KIND_AFFILIATE)

    def summarize(role):
        if not role:
            return []
        return [
            {'id': m['id'], 'name': m.get('name', ''), 'email': m.get('email', '')}
            for m in role.get('members', [])
        ]

    return Response({
        'centre_managers': summarize(manager_role),
        'affiliates': summarize(affiliate_role),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def global_people(request):
    """Same as centre_people, but for global roles (People tab, Req 14 parity)."""
    roles = ensure_default_global_roles()

    people = []
    seen_users = set()
    for role in roles:
        for member in role.get('members', []):
            user_id = member.get('user_id')
            if not user_id:
                continue
            if user_id in seen_users:
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
            })

    role_counts = {role.get('name', ''): len(role.get('members', [])) for role in roles}
    return Response({'total': len(people), 'role_counts': role_counts, 'people': people})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def global_permissions_matrix(request):
    """Permissions matrix for global roles (Req 16 parity)."""
    roles = ensure_default_global_roles()

    matrix = {}
    for module_name, entries in PERMISSION_CATEGORIES.items():
        matrix[module_name] = []
        for key, label in entries:
            row = {'key': key, 'label': label, 'roles': {}}
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
        'kind': r.get('kind', 'custom'),
        'is_default': bool(r.get('is_default')),
        'data_scope': r.get('data_scope', 'all'),
        'member_count': len(r.get('members', [])),
    } for r in roles]

    return Response({'roles': roles_data, 'matrix': matrix})


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def save_global_permissions_matrix(request):
    """Bulk update permissions for all global roles."""
    data = request.data
    roles = ensure_default_global_roles()
    valid_ids = {r['id'] for r in roles}

    skipped = []
    for role_id, perms in data.items():
        if role_id not in valid_ids:
            skipped.append(role_id)
            continue
        changed = []
        for key, flags in perms.items():
            roles_db.update_permission(str(role_id), key, flags)
            changed.append((key, flags))
        _notify_permission_changes(role_id, changed)

    resp = {'detail': 'Permissions saved successfully.'}
    if skipped:
        resp['skipped_role_ids'] = skipped
    return Response(resp)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def update_global_permission(request, role_pk, key):
    """Update a specific permission's flags for a global role."""
    role = roles_db.get_role(str(role_pk))
    if not role or role.get('centre_id') != GLOBAL_SCOPE:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
    result = roles_db.update_permission(str(role_pk), key, request.data)
    _notify_permission_changes(role_pk, [(key, result)])
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def add_global_member(request, role_pk):
    """
    Add a person to a global role. Unlike centre-role members (picked from an
    existing account), this is where Centre Manager / Affiliate accounts are
    created in the first place — name + email are enough, an id is minted
    for them.
    """
    role = roles_db.get_role(str(role_pk))
    if not role or role.get('centre_id') != GLOBAL_SCOPE:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    name = (request.data.get('name') or '').strip()
    email = (request.data.get('email') or '').strip()

    if not name:
        return Response({'name': ['Name is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'email': ['Email is required.']}, status=status.HTTP_400_BAD_REQUEST)

    existing = roles_db.list_members(role_pk)
    if any(m.get('email', '').lower() == email.lower() for m in existing):
        return Response(
            {'detail': 'This person already exists in this role.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user_id = request.data.get('user') or request.data.get('user_id') or str(uuid.uuid4())
    result = roles_db.add_member(str(role_pk), str(user_id), name=name, email=email)
    if result is None:
        return Response(
            {'detail': 'This person already exists in this role.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    _send_onboarding_email(
        email=email,
        name=name,
        centre_name='',
        role_name=role.get('name', ''),
    )

    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_global_member(request, role_pk, user_pk):
    """
    Remove a person from a global role. If they were the Centre Manager on
    any centre, or an assigned Affiliate, cascade the removal there too
    rather than leaving a dangling reference.
    """
    role = roles_db.get_role(str(role_pk))
    if not role or role.get('centre_id') != GLOBAL_SCOPE:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    members = role.get('members', [])
    member = next(
        (m for m in members if m.get('user_id') == str(user_pk) or m.get('id') == str(user_pk)),
        None
    )
    if not member:
        return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    result = roles_db.remove_member(str(role_pk), str(user_pk))
    if not result:
        return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    member_id = member.get('id')
    kind = role.get('kind')
    if kind == KIND_CENTRE_MANAGER:
        centres_db.clear_manager(member_id)
    elif kind == KIND_AFFILIATE:
        centres_db.remove_affiliate_everywhere(member_id)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def resend_global_invite(request, role_pk, user_pk):
    """Resend onboarding email to a global role member."""
    role = roles_db.get_role(str(role_pk))
    if not role or role.get('centre_id') != GLOBAL_SCOPE:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    member = next(
        (m for m in role.get('members', []) if m.get('user_id') == str(user_pk)),
        None
    )
    if not member:
        return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    success = _send_onboarding_email(
        email=member.get('email', ''),
        name=member.get('name', ''),
        centre_name='',
        role_name=role.get('name', ''),
    )
    if success:
        return Response({'detail': 'Onboarding email sent successfully.'})
    return Response(
        {'detail': 'Failed to send onboarding email.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_people(request, centre_pk):
    """
    Get all people assigned to a centre across all roles.
    Returns a flat list with user info and their role.
    Matches frontend's People tab in Roles & Permissions page (Req 14).
    """
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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def permissions_matrix(request, centre_pk):
    """
    Return the full permissions matrix for a centre (Req 16).
    Roles as columns, permissions as rows grouped by module.
    """
    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    roles = roles_db.list_roles(str(centre_pk))

    matrix = {}
    for module_name, entries in PERMISSION_CATEGORIES.items():
        matrix[module_name] = []
        for key, label in entries:
            row = {'key': key, 'label': label, 'roles': {}}
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

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    skipped = []
    for role_id, perms in data.items():
        role = roles_db.get_role(str(role_id))
        if not role or role.get('centre_id') != str(centre_pk):
            skipped.append(role_id)
            continue
        changed = []
        for key, flags in perms.items():
            roles_db.update_permission(str(role_id), key, flags)
            changed.append((key, flags))
        _notify_permission_changes(role_id, changed)

    resp = {'detail': 'Permissions saved successfully.'}
    if skipped:
        resp['skipped_role_ids'] = skipped
    return Response(resp)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def update_permission(request, role_pk, key):
    """Update a specific permission's flags for a role."""
    role = roles_db.get_role(str(role_pk))
    if not role:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
    result = roles_db.update_permission(str(role_pk), key, request.data)
    _notify_permission_changes(role_pk, [(key, result)])
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def add_member(request, role_pk):
    """
    Add a user to a role (Req 14.6).
    Also sends onboarding email (Req 22).
    """
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
    _send_onboarding_email(
        email=email,
        name=name,
        centre_name=role.get('centre_name', ''),
        role_name=role.get('name', ''),
    )

    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def resend_invite(request, role_pk, user_pk):
    """Resend onboarding email (Req 22.5)."""
    role = roles_db.get_role(str(role_pk))
    if not role:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    member = next(
        (m for m in role.get('members', []) if m.get('user_id') == str(user_pk)),
        None
    )
    if not member:
        return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    success = _send_onboarding_email(
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


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_member(request, role_pk, user_pk):
    """Remove a user from a role (Req 14.10-11)."""
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


def _send_onboarding_email(email, name, centre_name, role_name):
    """
    Send onboarding email to a new person (Req 22).
    Contains: centre name, assigned role, login link, OTP instructions.
    """
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
