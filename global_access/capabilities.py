"""
Resolves which org-wide capabilities a logged-in user holds.

Distinct from roles/access.py, which answers the centre-scoped question
("can this user edit children at Sunshine?"). This one answers the org-wide
question ("may this user see bank details at all?") by walking the user's
GlobalPerson record → assignments → global roles → grants.

Kept separate from views.py so the staff-record gating in _visible_person
and any future caller share one definition of the rule.
"""
import logging

from dynamo_backend.services import global_access_db
from roles.access import UNRESTRICTED_ROLES

logger = logging.getLogger(__name__)


def _user_email(user):
    return (getattr(user, 'email', '') or '').strip().lower()


def is_unrestricted(user):
    """Root/admin bypass every global capability, as they do centre scoping."""
    return getattr(user, 'role', None) in UNRESTRICTED_ROLES


def get_global_capabilities(user, request=None):
    """
    Set of capability keys this user holds org-wide.

    Returns an empty set for users with no global person record — callers
    must treat "no capability" as denial, never as unrestricted. Use
    is_unrestricted() for the bypass.
    """
    if request is not None:
        cached = getattr(request, '_global_capabilities', None)
        if cached is not None:
            return cached

    keys = set()
    email = _user_email(user)
    if email:
        try:
            person = next(
                (p for p in global_access_db.list_people()
                 if (p.get('email') or '').strip().lower() == email),
                None,
            )
            if person:
                roles_by_id = {r['id']: r for r in global_access_db.list_roles()}
                for assignment in person.get('roles', []):
                    role = roles_by_id.get(assignment.get('role_id'))
                    for perm in (role or {}).get('permissions', []):
                        if perm.get('visible') or perm.get('edit'):
                            keys.add(perm.get('key'))
        except Exception as e:
            # Never let a lookup failure read as "has permission".
            logger.warning(f"Could not resolve global capabilities for {email}: {e}")
            keys = set()

    if request is not None:
        request._global_capabilities = keys
    return keys


def has_global_capability(user, key, request=None):
    if is_unrestricted(user):
        return True
    return key in get_global_capabilities(user, request=request)
