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


def _parent_contact_emails(child):
    return {
        c['email'] for c in child.get('contacts', [])
        if c.get('invite_as') in ('Parent', 'Guardian', 'Carer') and c.get('email')
    }


def _send(subject, message, emails):
    """
    Send to each recipient independently so one bad address can't block the rest.
    Never raises — a mail outage must not fail the underlying CRUD action — but
    logs every failure at ERROR so rejections are visible rather than silent.
    Returns a list of {'email', 'status', 'error'}, matching billing.notifications.
    """
    results = []
    for email in emails:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            results.append({'email': email, 'status': 'sent', 'error': None})
        except Exception as e:
            # In the SES sandbox this is the expected failure for any recipient
            # that isn't itself a verified identity (MessageRejected).
            logger.error(f"Failed to send '{subject}' to {email}: {e}", exc_info=True)
            results.append({'email': email, 'status': 'failed', 'error': str(e)})

    if results and all(r['status'] == 'failed' for r in results):
        logger.error(f"'{subject}' failed for all {len(results)} recipient(s).")
    return results


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


def send_child_registered_email(child, centre):
    """Child registered successfully (onboarding email)."""
    child_name = f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
    centre_name = (centre or {}).get('name', '')

    subject = f"Welcome to Shichida — {child_name}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"This email confirms that {child_name} has been successfully registered at {centre_name}.\n\n"
        f"We look forward to welcoming you.\n\n"
        f"Best regards,\n"
        f"{centre_name}"
    )

    emails = _parent_contact_emails(child)
    centre_id = child.get('centre_id') or (centre or {}).get('id')
    if centre_id:
        emails |= get_centre_admin_emails(centre_id)
    _send(subject, message, emails)


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
    centre_id = role.get('centre_id')
    if centre_id:
        emails |= get_centre_admin_emails(centre_id)
    _send(subject, message, emails)


def send_staff_invite_email(person, role, centre_id=None):
    """
    Invite a newly-onboarded staff member to set their password and sign in
    (Global settings → People → Onboard staff, step 3).

    Mirrors the wizard's preview text so what the admin was shown is what
    actually goes out. Returns the same {'sent', 'reason', 'results'} shape
    as billing.notifications.send_invoice_email so callers can report back.
    """
    email = person.get('email')
    if not email:
        return {'sent': False, 'reason': 'no_email', 'results': []}

    first_name = (person.get('name') or '').split(' ')[0]
    role_name = (role or {}).get('name', 'staff member')

    centre_name = ''
    if centre_id:
        centre = centres_db.get_centre(str(centre_id))
        centre_name = (centre or {}).get('name', '')
    where = f"{role_name} at {centre_name}" if centre_name else role_name

    granted = sum(
        1 for p in (role or {}).get('permissions', [])
        if p.get('visible') or p.get('edit')
    )

    # Accounts are created with a random password nobody is told, so the
    # first login goes through the reset flow — that's why this walks them
    # to "Forgot your password?" rather than mentioning a password we set.
    subject = f"You have been set up on Shichida India — {where}"
    message = (
        f"Hello {first_name},\n\n"
        f"You have been set up on Shichida India as {where}.\n\n"
        f"To get in for the first time:\n"
        f"  1. Open the portal and choose \"Forgot your password?\"\n"
        f"  2. Enter this address — {email} — and we'll email you a code\n"
        f"  3. Use the code to choose your own password\n\n"
        f"After that, sign in with your email and password. We'll send a "
        f"one-time code to confirm it's you each time you log in.\n\n"
        f"Once you are in you will see {granted} areas of the portal. "
        f"Anything else appears locked, with a button to ask for it.\n\n"
        f"Best regards,\n"
        f"Shichida India Admin Portal"
    )

    results = _send(subject, message, [email])
    sent = any(r['status'] == 'sent' for r in results)
    return {
        'sent': sent,
        'reason': None if sent else 'send_failed',
        'results': results,
    }
