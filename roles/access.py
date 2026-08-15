"""
Resolves what a logged-in user is allowed to see/do, from the roles &
permissions matrix (roles_db). This is the single place that walks
Role/RolePermission/RoleMember to answer "what can this user do" — both
API enforcement (see the various apps' views.py) and the /api/auth/me/
response (schindia_auth/serializers.py) are built on top of it, so they
can't drift out of sync with each other.
"""

from rest_framework import status
from rest_framework.response import Response

# Global roles (schindia_auth.authentication.DynamoUser.role) that bypass all
# centre-membership/permission-matrix scoping entirely. 'root' is the system
# superuser; 'admin' is any approved portal user (centre owner/operator) —
# both see every centre. Only custom per-centre roles created via Roles &
# Permissions (Teacher, Manager, etc.) are scoped to the centres they were
# explicitly added to.
UNRESTRICTED_ROLES = {'root', 'admin'}


class UserAccess:
    """Resolved access for one user: which centres, and what per-key
    visible/edit flags at each. Unrestricted users (see UNRESTRICTED_ROLES)
    bypass all of this and can access everything.
    """

    def __init__(self, unrestricted=False):
        self.unrestricted = unrestricted
        # centre_id -> {'data_scope': str, 'role_names': [str], 'permissions': {key: {'visible': bool, 'edit': bool}}}
        self.centres = {}

    def accessible_centre_ids(self):
        """Set of centre ids this user may access, or None if unrestricted."""
        if self.unrestricted:
            return None
        return set(self.centres.keys())

    def can_access_centre(self, centre_id):
        if self.unrestricted:
            return True
        return str(centre_id) in self.centres

    def can_view(self, centre_id, key):
        return self._has_flag(centre_id, key, 'visible')

    def can_edit(self, centre_id, key):
        return self._has_flag(centre_id, key, 'edit')

    def _has_flag(self, centre_id, key, flag):
        if self.unrestricted:
            return True
        centre = self.centres.get(str(centre_id))
        if not centre:
            return False
        return bool(centre['permissions'].get(key, {}).get(flag, False))


def get_user_access(user, request=None):
    """Resolve a UserAccess for `user`, memoized on `request` if given
    so a single request doesn't repeatedly re-scan roles_db.
    """
    if request is not None:
        cached = getattr(request, '_user_access', None)
        if cached is not None:
            return cached

    access = _resolve_user_access(user)

    if request is not None:
        request._user_access = access
    return access


def _resolve_user_access(user):
    if getattr(user, 'role', None) in UNRESTRICTED_ROLES:
        return UserAccess(unrestricted=True)

    from dynamo_backend.services import roles_db, centres_db

    access = UserAccess(unrestricted=False)
    user_id = str(user.id)

    for centre in centres_db.list_centres():
        cid = centre['id']
        for role in roles_db.list_roles(cid):
            members = role.get('members', [])
            if not any(m.get('user_id') == user_id for m in members):
                continue

            entry = access.centres.setdefault(cid, {
                'data_scope': 'own',
                'role_names': [],
                'permissions': {},
                'name': centre.get('name', ''),
                'system_id': centre.get('system_id', ''),
            })
            entry['role_names'].append(role.get('name', ''))
            if role.get('data_scope') == 'all':
                entry['data_scope'] = 'all'
            for perm in role.get('permissions', []):
                key = perm.get('key')
                if not key:
                    continue
                existing = entry['permissions'].setdefault(key, {'visible': False, 'edit': False})
                existing['visible'] = existing['visible'] or bool(perm.get('visible', False))
                existing['edit'] = existing['edit'] or bool(perm.get('edit', False))

    return access


def centre_not_found(detail='Centre not found.'):
    return Response({'detail': detail}, status=status.HTTP_404_NOT_FOUND)


def permission_denied(detail='You do not have permission to perform this action.'):
    return Response({'detail': detail}, status=status.HTTP_403_FORBIDDEN)
