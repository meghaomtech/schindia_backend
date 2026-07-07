"""
DynamoDB table names configuration.
Prefix with environment to keep dev/prod separate.
"""

from decouple import config

ENV = config('DJANGO_ENV', default='local')
PREFIX = f"Shichida-{ENV}" if ENV != 'local' else "Shichida-dev"

# Table names
USERS_TABLE = f"{PREFIX}-Users"
CENTRES_TABLE = f"{PREFIX}-Centres"
ROOMS_TABLE = f"{PREFIX}-Rooms"
SESSIONS_TABLE = f"{PREFIX}-Sessions"
SESSION_SLOTS_TABLE = f"{PREFIX}-SessionSlots"
CHILDREN_TABLE = f"{PREFIX}-Children"
CONTACTS_TABLE = f"{PREFIX}-Contacts"
ENROLMENTS_TABLE = f"{PREFIX}-Enrolments"
JOURNEY_TABLE = f"{PREFIX}-Journey"
NOTES_TABLE = f"{PREFIX}-Notes"
INVOICES_TABLE = f"{PREFIX}-Invoices"
INVOICE_ITEMS_TABLE = f"{PREFIX}-InvoiceItems"
PURCHASES_TABLE = f"{PREFIX}-Purchases"
ROLES_TABLE = f"{PREFIX}-Roles"
ROLE_PERMISSIONS_TABLE = f"{PREFIX}-RolePermissions"
ROLE_MEMBERS_TABLE = f"{PREFIX}-RoleMembers"
ATTENDANCE_TABLE = f"{PREFIX}-Attendance"
COURSE_PROGRESS_TABLE = f"{PREFIX}-CourseProgress"
OTP_TABLE = f"{PREFIX}-OTP"

ALL_TABLES = {
    'users': USERS_TABLE,
    'centres': CENTRES_TABLE,
    'rooms': ROOMS_TABLE,
    'sessions': SESSIONS_TABLE,
    'session_slots': SESSION_SLOTS_TABLE,
    'children': CHILDREN_TABLE,
    'contacts': CONTACTS_TABLE,
    'enrolments': ENROLMENTS_TABLE,
    'journey': JOURNEY_TABLE,
    'notes': NOTES_TABLE,
    'invoices': INVOICES_TABLE,
    'invoice_items': INVOICE_ITEMS_TABLE,
    'purchases': PURCHASES_TABLE,
    'roles': ROLES_TABLE,
    'role_permissions': ROLE_PERMISSIONS_TABLE,
    'role_members': ROLE_MEMBERS_TABLE,
    'attendance': ATTENDANCE_TABLE,
    'course_progress': COURSE_PROGRESS_TABLE,
    'otp': OTP_TABLE,
}
