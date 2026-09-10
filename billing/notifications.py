"""
Invoice and session email notifications (Req 23, 25).
"""
import logging
from datetime import datetime

from django.core.mail import EmailMessage, send_mail

from dynamo_backend.services import children_db, centres_db, auth_db

from .pdf_generator import InvoicePdfError, build_invoice_pdf, invoice_pdf_filename

logger = logging.getLogger(__name__)


PARENT_ROLES = ('Parent', 'Guardian', 'Carer')


def invoice_recipients(invoice, child):
    """
    Who an invoice is addressed to.

    A child's parent contacts come first — those are the people on record. When
    there are none, the bill-payer address typed on the invoice is used: it is
    already printed on the document as the payer, and an invoice raised before
    a child is enrolled has no contacts to resolve at all. Refusing to send in
    that case simply means the bill is never delivered.
    """
    if child:
        from_contacts = [
            c['email'] for c in (child.get('contacts') or [])
            if c.get('invite_as') in PARENT_ROLES and c.get('email')
        ]
        if from_contacts:
            return from_contacts

    billed_to = (invoice.get('email') or '').strip()
    return [billed_to] if billed_to else []


def deliver_invoice_email(subject, message, recipient, attachment=None):
    """
    One invoice email to one address.

    The single place a message actually leaves this module, so the PDF is
    attached the same way whether the invoice was just raised or is being sent
    on afterwards. Raises on failure; the caller records the outcome per
    recipient so one bad address cannot swallow the rest.

    `attachment` is (filename, content, mimetype) or None.
    """
    if attachment is None:
        send_mail(subject=subject, message=message, from_email=None,
                  recipient_list=[recipient], fail_silently=False)
        return

    email = EmailMessage(subject=subject, body=message, to=[recipient])
    email.attach(*attachment)
    email.send(fail_silently=False)


def _bank_details_text(centre):
    bank_details = (centre or {}).get('bank_details') or {}
    if not bank_details:
        return ""
    text = "\n\nPayment Details:\n"
    for label, key in (
        ('Account Holder', 'account_holder_name'),
        ('Bank', 'bank_name'),
        ('Account Number', 'account_number'),
        ('IFSC Code', 'ifsc_code'),
        ('UPI ID', 'upi_id'),
    ):
        if bank_details.get(key):
            text += f"  {label}: {bank_details[key]}\n"
    return text


def _invoice_email_content(invoice, child, centre, attached_filename=None):
    """
    Subject and body for an invoice email.

    Names the invoice, the child, the centre, the amount and the due date, so
    a parent can identify the bill from the message alone — the attachment is
    the document, not the only place the essentials appear.
    """
    centre_name = (centre.get('name', '') if centre else '') or invoice.get('center_code', '')
    billed_for = (
        f"{child.get('first_name', '')} {child.get('last_name', '')}".strip() if child else ''
    ) or invoice.get('student_name', '')

    try:
        due_date_display = datetime.strptime(
            invoice.get('due_date', ''), '%Y-%m-%d').strftime('%d %B %Y')
    except (ValueError, TypeError):
        due_date_display = invoice.get('due_date', '')

    subject = f"Invoice for {billed_for} — {centre_name}"
    attachment_line = (
        f"\nYour invoice is attached as {attached_filename}.\n"
        if attached_filename else ""
    )
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"An invoice has been generated for {billed_for} "
        f"at {centre_name}.\n\n"
        f"Invoice Number: {invoice.get('number', '')}\n"
        f"Total Amount: ₹{invoice.get('total_amount', 0)}\n"
        f"Due Date: {due_date_display}\n"
        f"{attachment_line}"
        f"{_bank_details_text(centre)}\n"
        f"Please ensure payment is made by the due date.\n\n"
        f"Best regards,\n"
        f"{centre_name}"
    )
    return subject, message


def invoice_email_context(invoice):
    """The child and centre an invoice belongs to, for rendering and addressing."""
    child_id = invoice.get('child_id') or invoice.get('child')
    child = children_db.get_child(str(child_id)) if child_id else None
    # The centre comes from the child where there is one, and from the invoice's
    # own stamp otherwise — a childless invoice still belongs to a centre.
    centre_id = (child or {}).get('centre_id') or invoice.get('centre_id')
    centre = centres_db.get_centre(str(centre_id)) if centre_id else None
    return child, centre


def send_invoice_email(invoice, attach_pdf=True):
    """
    Send the invoice to whoever is billed for it (Req 23.1-3), with the
    invoice PDF attached.

    `invoice` is a dict as returned by billing_db.get_invoice().
    Returns {'sent': bool, 'reason': str|None, 'results': [...]}.

    A PDF that will not render is reported rather than papered over: sending
    the covering note without the document it describes leaves a parent with a
    demand for money and nothing to check it against.
    """
    child, centre = invoice_email_context(invoice)

    recipients = invoice_recipients(invoice, child)
    if not recipients:
        logger.warning(
            f"Invoice {invoice.get('number') or invoice.get('id')} has no recipient — "
            f"no parent contact and no bill-payer email. Not sent."
        )
        return {'sent': False, 'reason': 'no_contacts', 'results': []}

    attachment = None
    filename = None
    if attach_pdf:
        try:
            filename = invoice_pdf_filename(invoice)
            attachment = (filename, build_invoice_pdf(invoice, centre, child),
                          'application/pdf')
        except InvoicePdfError as exc:
            return {'sent': False, 'reason': 'pdf_failed', 'error': str(exc),
                    'results': []}

    subject, message = _invoice_email_content(invoice, child, centre, filename)

    results = []
    for email in recipients:
        try:
            deliver_invoice_email(subject, message, email, attachment)
            results.append({'email': email, 'status': 'sent', 'error': None})
        except Exception as e:
            logger.warning(f"Failed to send invoice email to {email}: {e}")
            results.append({'email': email, 'status': 'failed', 'error': str(e)})

    any_sent = any(r['status'] == 'sent' for r in results)
    return {'sent': any_sent, 'reason': None if any_sent else 'all_failed',
            'results': results}


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
