"""
Shared email notifications for events that don't already have a home:
timetable/enrolment changes and role permission changes.

Follows the same plaintext send_mail + try/except-per-recipient pattern
used throughout the codebase (see billing/notifications.py), so a mail
outage never blocks the underlying CRUD action.
"""
import logging

from django.core.mail import send_mail

from dynamo_backend.services import centres_db, roles_db
from dynamo_backend.services.roles_service import GLOBAL_SCOPE
from roles.permissions_catalog import PERMISSION_CATEGORIES

logger = logging.getLogger(__name__)

ADMIN_PERMISSION_KEYS = {'people.manage', 'roles.manage'}

_PERMISSION_LABELS = {
    key: label
    for entries in PERMISSION_CATEGORIES.values()
    for key, label in entries
}


def _is_admin_role(role):
    perms = {p.get('key') for p in role.get('permissions', []) if p.get('visible')}
    return ADMIN_PERMISSION_KEYS.issubset(perms)


def get_centre_admin_emails(centre_id):
    """Manager + members of any role with full people/roles admin at this centre."""
    emails = set()
    centre = centres_db.get_centre(str(centre_id))
    manager = (centre or {}).get('manager') or {}
    manager_email = manager.get('email')
    if manager_email:
        emails.add(manager_email)

    for role in roles_db.list_roles(str(centre_id)):
        if _is_admin_role(role):
            for member in role.get('members', []):
                if member.get('email'):
                    emails.add(member['email'])
    return emails


def get_global_admin_emails():
    """Members of any global role with full people/roles admin permissions."""
    emails = set()
    for role in roles_db.list_roles(GLOBAL_SCOPE):
        if _is_admin_role(role):
            for member in role.get('members', []):
                if member.get('email'):
                    emails.add(member['email'])
    return emails


def _parent_contact_emails(child):
    return {
        c['email'] for c in child.get('contacts', [])
        if c.get('invite_as') in ('Parent', 'Guardian', 'Carer') and c.get('email')
    }


def _send(subject, message, emails):
    for email in emails:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"Failed to send '{subject}' to {email}: {e}")


def _slot_description(slot, session, room):
    day = (slot or {}).get('day', '').capitalize()
    time = (slot or {}).get('start_time', '')
    session_name = (session or {}).get('name', 'Session')
    room_name = (room or {}).get('name', '')
    parts = [session_name]
    if day or time:
        parts.append(f"{day} {time}".strip())
    if room_name:
        parts.append(f"Room: {room_name}")
    return " — ".join(parts)


def send_enrolment_added_email(child, slot, session, centre, room=None):
    """Child added to a timetable slot (Req: timetable planned / child added)."""
    child_name = f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
    centre_name = (centre or {}).get('name', '')
    description = _slot_description(slot, session, room)

    subject = f"New session scheduled — {child_name}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"{child_name} has been added to a new session at {centre_name}.\n\n"
        f"{description}\n\n"
        f"Best regards,\n"
        f"{centre_name}"
    )

    emails = _parent_contact_emails(child)
    centre_id = child.get('centre_id') or (centre or {}).get('id')
    if centre_id:
        emails |= get_centre_admin_emails(centre_id)
    _send(subject, message, emails)


def send_enrolment_removed_email(child, slot, session, centre, reason='removed', room=None):
    """
    Child removed from a slot, or moved to a different slot (Req: child
    removed / slot changes). `reason` is 'removed' or 'rescheduled'.
    """
    child_name = f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
    centre_name = (centre or {}).get('name', '')
    description = _slot_description(slot, session, room)

    if reason == 'rescheduled':
        subject = f"Session time changed — {child_name}"
        intro = f"{child_name}'s session at {centre_name} has been rescheduled."
    else:
        subject = f"Session removed — {child_name}"
        intro = f"{child_name} has been removed from a session at {centre_name}."

    message = (
        f"Dear Parent/Guardian,\n\n"
        f"{intro}\n\n"
        f"{description}\n\n"
        f"Best regards,\n"
        f"{centre_name}"
    )

    emails = _parent_contact_emails(child)
    centre_id = child.get('centre_id') or (centre or {}).get('id')
    if centre_id:
        emails |= get_centre_admin_emails(centre_id)
    _send(subject, message, emails)


def send_permission_updated_email(role, changed_summary):
    """
    A role's permissions changed (Req: role permission updated/changed).
    `changed_summary` is a list of (key, {'visible': bool, 'edit': bool}) tuples.
    """
    role_name = role.get('name', 'Role')
    is_global = role.get('centre_id') == GLOBAL_SCOPE

    lines = []
    for key, flags in changed_summary:
        label = _PERMISSION_LABELS.get(key, key)
        access = 'edit' if flags.get('edit') else ('view only' if flags.get('visible') else 'no access')
        lines.append(f"  - {label}: {access}")
    changes_text = "\n".join(lines) if lines else "  (see the portal for the latest permissions)"

    subject = f"Permissions updated — {role_name}"
    message = (
        f"Hi,\n\n"
        f"The permissions for the \"{role_name}\" role have been updated:\n\n"
        f"{changes_text}\n\n"
        f"Log in to the portal to review your access.\n\n"
        f"Best regards,\n"
        f"Shichida India Admin Portal"
    )

    emails = {m['email'] for m in role.get('members', []) if m.get('email')}
    if is_global:
        emails |= get_global_admin_emails()
    else:
        centre_id = role.get('centre_id')
        if centre_id:
            emails |= get_centre_admin_emails(centre_id)
    _send(subject, message, emails)
