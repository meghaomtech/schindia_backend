"""
Invoice and session email notifications (Req 23, 25).
"""
import logging
from datetime import datetime

from django.core.mail import send_mail

from dynamo_backend.services import children_db, centres_db, auth_db

logger = logging.getLogger(__name__)


def send_invoice_email(invoice):
    """
    Send invoice email to all parents linked to the child (Req 23.1-3).
    `invoice` is a dict as returned by billing_db.get_invoice().
    Returns list of {'email': ..., 'status': 'sent'|'failed', 'error': ...}.
    Returns empty list with a reason if no contacts found.
    """
    child_id = invoice.get('child_id') or invoice.get('child')
    child = children_db.get_child(str(child_id)) if child_id else None
    if not child:
        logger.warning(f"Invoice {invoice.get('id')} has no resolvable child — not sent.")
        return {'sent': False, 'reason': 'no_contacts', 'results': []}

    centre = centres_db.get_centre(str(child['centre_id'])) if child.get('centre_id') else None
    centre_name = centre.get('name', '') if centre else ''

    parent_contacts = [
        c for c in child.get('contacts', [])
        if c.get('invite_as') in ('Parent', 'Guardian', 'Carer') and c.get('email')
    ]

    if not parent_contacts:
        logger.warning(
            f"No parent email for child {child.get('id')} - invoice {invoice.get('number')} not sent."
        )
        return {'sent': False, 'reason': 'no_contacts', 'results': []}

    subject = f"Invoice for {child.get('first_name', '')} {child.get('last_name', '')} — {centre_name}"

    # Build bank details text
    bank_text = ""
    bank_details = (centre or {}).get('bank_details') or {}
    if bank_details:
        bank_text = "\n\nPayment Details:\n"
        if bank_details.get('account_holder_name'):
            bank_text += f"  Account Holder: {bank_details['account_holder_name']}\n"
        if bank_details.get('bank_name'):
            bank_text += f"  Bank: {bank_details['bank_name']}\n"
        if bank_details.get('account_number'):
            bank_text += f"  Account Number: {bank_details['account_number']}\n"
        if bank_details.get('ifsc_code'):
            bank_text += f"  IFSC Code: {bank_details['ifsc_code']}\n"
        if bank_details.get('upi_id'):
            bank_text += f"  UPI ID: {bank_details['upi_id']}\n"

    try:
        due_date_display = datetime.strptime(invoice.get('due_date', ''), '%Y-%m-%d').strftime('%d %B %Y')
    except (ValueError, TypeError):
        due_date_display = invoice.get('due_date', '')

    message = (
        f"Dear Parent/Guardian,\n\n"
        f"An invoice has been generated for {child.get('first_name', '')} {child.get('last_name', '')} "
        f"at {centre_name}.\n\n"
        f"Invoice Number: {invoice.get('number', '')}\n"
        f"Total Amount: ₹{invoice.get('total_amount', 0)}\n"
        f"Due Date: {due_date_display}\n"
        f"{bank_text}\n"
        f"Please ensure payment is made by the due date.\n\n"
        f"Best regards,\n"
        f"{centre_name}"
    )

    results = []
    for contact in parent_contacts:
        email = contact['email']
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
            logger.warning(f"Failed to send invoice email to {email}: {e}")
            results.append({'email': email, 'status': 'failed', 'error': str(e)})

    any_sent = any(r['status'] == 'sent' for r in results)
    return {'sent': any_sent, 'reason': None if any_sent else 'all_failed', 'results': results}


def _should_skip_notification(email, notification_type):
    """
    Check if a user with this email has disabled notifications (Req 25.4-5).
    notification_type: 'attendance' | 'milestone'
    Returns True if notification should NOT be sent.
    """
    user = auth_db.get_user_by_email(email)
    if not user:
        # Contact email not a portal user — send anyway
        return False

    pref = user.get('notification_preference', 'all')
    if pref == 'none':
        return True  # Skip all notifications
    if pref == 'milestones' and notification_type == 'attendance':
        return True  # Skip attendance, only send milestones
    return False  # Send


def _send_to_parent_contacts(child, subject, message, notification_type):
    """
    Common helper: send an email to all parent/guardian contacts of a child,
    respecting notification preferences (Req 25.4-5). `child` is a dict.
    """
    parent_contacts = [
        c for c in child.get('contacts', [])
        if c.get('invite_as') in ('Parent', 'Guardian', 'Carer') and c.get('email')
    ]

    if not parent_contacts:
        logger.warning(
            f"No parent contacts with email for child {child.get('id')} — "
            f"{notification_type} notification not sent."
        )
        return

    for contact in parent_contacts:
        email = contact['email']
        if _should_skip_notification(email, notification_type):
            continue
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send {notification_type} notification to {email}: {e}")


def send_attendance_notification(attendance, child, session=None, teacher_name='Unknown'):
    """
    Send attendance notification to parents (Req 25.1).
    `attendance`/`child`/`session` are dicts.
    """
    subject = f"Attendance Confirmed — {child.get('first_name', '')}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"{child.get('first_name', '')}'s attendance has been recorded:\n\n"
        f"Session: {(session or {}).get('name', '')}\n"
        f"Date: {attendance.get('date', '')}\n"
        f"Teacher: {teacher_name}\n\n"
        f"Best regards,\n"
        f"{child.get('centre_name', '')}"
    )

    _send_to_parent_contacts(child, subject, message, 'attendance')


def send_milestone_notification(journey_entry, child):
    """
    Send milestone/observation notification to parents (Req 25.3).
    `journey_entry`/`child` are dicts.
    """
    entry_type = journey_entry.get('type', '')

    subject = f"New {entry_type} — {child.get('first_name', '')}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"A new {entry_type.lower()} has been logged for {child.get('first_name', '')}:\n\n"
        f"{journey_entry.get('text', '')}\n\n"
        f"Logged by: {journey_entry.get('staff_name', '')}\n"
        f"Date: {journey_entry.get('date', '')}\n\n"
        f"Log in to the portal to view full details.\n\n"
        f"Best regards,\n"
        f"{child.get('centre_name', '')}"
    )

    _send_to_parent_contacts(child, subject, message, 'milestone')
