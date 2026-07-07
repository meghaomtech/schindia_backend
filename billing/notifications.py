"""
Invoice and session email notifications (Req 23, 25).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_invoice_email(invoice):
    """
    Send invoice email to all parents linked to the child (Req 23.1-3).
    Returns list of {'email': ..., 'status': 'sent'|'failed'}.
    """
    child = invoice.child
    centre = child.centre

    # Get parent contacts with email
    parent_contacts = child.contacts.filter(
        invite_as__in=['Parent', 'Guardian', 'Carer'],
        email__isnull=False,
    ).exclude(email='')

    if not parent_contacts.exists():
        logger.warning(
            f"No parent email for child {child.id} - invoice {invoice.number} not sent."
        )
        return []

    subject = f"Invoice {invoice.number} — {centre.name}"

    # Build bank details text
    bank_text = ""
    if centre.bank_details:
        bd = centre.bank_details
        bank_text = "\n\nPayment Details:\n"
        if bd.get('account_holder_name'):
            bank_text += f"  Account Holder: {bd['account_holder_name']}\n"
        if bd.get('bank_name'):
            bank_text += f"  Bank: {bd['bank_name']}\n"
        if bd.get('account_number'):
            bank_text += f"  Account Number: {bd['account_number']}\n"
        if bd.get('ifsc_code'):
            bank_text += f"  IFSC Code: {bd['ifsc_code']}\n"
        if bd.get('upi_id'):
            bank_text += f"  UPI ID: {bd['upi_id']}\n"

    message = (
        f"Dear Parent/Guardian,\n\n"
        f"An invoice has been generated for {child.first_name} {child.last_name} "
        f"at {centre.name}.\n\n"
        f"Invoice Number: {invoice.number}\n"
        f"Total Amount: ₹{invoice.total_amount}\n"
        f"Due Date: {invoice.due_date.strftime('%d %B %Y')}\n"
        f"{bank_text}\n"
        f"Please ensure payment is made by the due date.\n\n"
        f"Best regards,\n"
        f"{centre.name}"
    )

    results = []
    for contact in parent_contacts:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[contact.email],
                fail_silently=False,
            )
            results.append({'email': contact.email, 'status': 'sent'})
        except Exception as e:
            logger.warning(f"Failed to send invoice email to {contact.email}: {e}")
            results.append({'email': contact.email, 'status': 'failed'})

    return results


def send_attendance_notification(attendance):
    """
    Send attendance notification to parents (Req 25.1).
    """
    child = attendance.child
    session = attendance.session
    teacher_name = attendance.teacher.get_full_name() if attendance.teacher else 'Unknown'

    parent_contacts = child.contacts.filter(
        invite_as__in=['Parent', 'Guardian', 'Carer'],
        email__isnull=False,
    ).exclude(email='')

    if not parent_contacts.exists():
        return

    subject = f"Attendance Confirmed — {child.first_name}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"{child.first_name}'s attendance has been recorded:\n\n"
        f"Session: {session.name}\n"
        f"Date: {attendance.date.strftime('%d %B %Y')}\n"
        f"Teacher: {teacher_name}\n\n"
        f"Best regards,\n"
        f"{child.centre.name}"
    )

    for contact in parent_contacts:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[contact.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send attendance notification to {contact.email}: {e}")


def send_milestone_notification(journey_entry):
    """
    Send milestone/observation notification to parents (Req 25.3).
    """
    child = journey_entry.child

    parent_contacts = child.contacts.filter(
        invite_as__in=['Parent', 'Guardian', 'Carer'],
        email__isnull=False,
    ).exclude(email='')

    if not parent_contacts.exists():
        return

    entry_type = journey_entry.type
    subject = f"New {entry_type} — {child.first_name}"
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"A new {entry_type.lower()} has been logged for {child.first_name}:\n\n"
        f"{journey_entry.text}\n\n"
        f"Logged by: {journey_entry.staff_name}\n"
        f"Date: {journey_entry.date.strftime('%d %B %Y')}\n\n"
        f"Log in to the portal to view full details.\n\n"
        f"Best regards,\n"
        f"{child.centre.name}"
    )

    for contact in parent_contacts:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[contact.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send milestone notification to {contact.email}: {e}")
