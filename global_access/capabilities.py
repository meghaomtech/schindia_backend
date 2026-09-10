"""
Resolves which org-wide capabilities a logged-in user holds.

Distinct from roles/access.py, which answers the centre-scoped question
("can this user edit children at Sunshine?"). This one answers the org-wide
question ("may this user see bank details at all?") by walking the user's
GlobalPerson record → assignments → global roles → grants.

Kept separate from views.py so the staff-record gating in _visible_person
and any future caller share one definition of the rule.

It is also where "Global Admin" is defined — the people who may decide a
child's move between centres. That is a narrower set than `unrestricted`:
every approved portal user is `admin` and therefore unrestricted, but only
root and holders of the Super Admin global role are Global Admins. Centre
Managers and centre-scoped staff are never Global Admins, whatever else
they hold.
"""
import logging

from dynamo_backend.services import auth_db, global_access_db
from roles.access import UNRESTRICTED_ROLES

logger = logging.getLogger(__name__)

# The system superuser (schindia_auth role). Always a Global Admin.
ROOT_ROLE = 'root'

# The seeded Super Admin global role is recognised by `kind`; the names are a
# fallback for an environment whose role was created by hand before the seed
# command stamped kinds on it.
GLOBAL_ADMIN_ROLE_KIND = 'super_admin'
GLOBAL_ADMIN_ROLE_NAMES = frozenset({'super admin', 'global admin'})


def _user_email(user):
    return (getattr(user, 'email', '') or '').strip().lower()


def _clean_email(value):
    return (value or '').strip().lower()


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


# ── Global Admins ───────────────────────────────────────────────────


def _is_global_admin_role(role):
    if (role or {}).get('kind') == GLOBAL_ADMIN_ROLE_KIND:
        return True
    return _clean_email(role.get('name')) in GLOBAL_ADMIN_ROLE_NAMES


def _global_admin_role_ids():
    return {r['id'] for r in global_access_db.list_roles() if _is_global_admin_role(r)}


def _holds_global_admin_role(person, admin_role_ids):
    """
    True when one of this person's assignments is the Super Admin role held
    organisation-wide. An assignment scoped to a centre — however the role is
    named — is centre-level access, not global, and does not count.
    """
    for assignment in (person or {}).get('roles', []):
        if assignment.get('role_id') not in admin_role_ids:
            continue
        if assignment.get('centre_id'):
            continue
        return True
    return False


def super_admin_emails():
    """
    Lower-cased addresses of every global person holding Super Admin org-wide.

    Raises on a lookup failure so callers decide what "unknown" means for
    them — for an access check it must mean denial.
    """
    admin_role_ids = _global_admin_role_ids()
    if not admin_role_ids:
        return set()
    emails = set()
    for person in global_access_db.list_people():
        if not _holds_global_admin_role(person, admin_role_ids):
            continue
        email = _clean_email(person.get('email'))
        if email:
            emails.add(email)
    return emails


def global_admin_emails():
    """
    Everyone who is a Global Admin, by address: approved root users, plus
    holders of the Super Admin global role.

    This is the single list both the move-request notification and the
    email-link check are built on, so the people who are told about a move
    are exactly the people allowed to decide it.
    """
    emails = set()
    for user in auth_db.list_by_role(ROOT_ROLE):
        if user.get('status') == 'approved':
            email = _clean_email(user.get('email'))
            if email:
                emails.add(email)
    emails |= super_admin_emails()
    return emails


def is_global_admin(user, request=None):
    """
    Whether this signed-in user is a Global Admin.

    Root is, by role. Anyone else is only if their address holds the Super
    Admin global role organisation-wide. An `admin` portal user without that
    assignment — a centre owner, a Centre Manager — is not, even though
    `unrestricted` lets them see every centre.
    """
    if getattr(user, 'role', None) == ROOT_ROLE:
        return True

    if request is not None:
        cached = getattr(request, '_is_global_admin', None)
        if cached is not None:
            return cached

    email = _user_email(user)
    result = False
    if email:
        try:
            result = email in super_admin_emails()
        except Exception as e:
            # A failed lookup is a denial, never a grant.
            logger.warning(f"Could not resolve Global Admin status for {email}: {e}")
            result = False

    if request is not None:
        request._is_global_admin = result
    return result


def email_is_global_admin(email):
    """
    Whether an address — one carried in a signed email link, with no session
    behind it — belongs to a current Global Admin.

    Checked at the moment the link is used, not when it was sent: a Super
    Admin whose role was removed after the email went out must not still be
    able to decide the move from their inbox.
    """
    email = _clean_email(email)
    if not email:
        return False
    try:
        return email in global_admin_emails()
    except Exception as e:
        logger.warning(f"Could not resolve Global Admin status for {email}: {e}")
        return False
