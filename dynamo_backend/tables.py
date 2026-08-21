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
# Every act that moves money against an invoice — payment, credit note,
# write-off, refund — in one append-only table. Kept separate from the
# invoice so a correction never mutates the issued document, and so the
# balance is always derivable from the trail rather than a stored figure.
INVOICE_LEDGER_TABLE = f"{PREFIX}-InvoiceLedger"
# Atomic counter for the invoice number series. A per-browser counter cannot
# produce an unbroken series — two people raising invoices simultaneously
# would issue the same number.
INVOICE_COUNTERS_TABLE = f"{PREFIX}-InvoiceCounters"
PURCHASES_TABLE = f"{PREFIX}-Purchases"
ROLES_TABLE = f"{PREFIX}-Roles"
ROLE_PERMISSIONS_TABLE = f"{PREFIX}-RolePermissions"
ROLE_MEMBERS_TABLE = f"{PREFIX}-RoleMembers"
# Global (org-wide) roles & permissions — see global_access app. Distinct from
# ROLES_TABLE above, which holds centre-scoped role templates.
GLOBAL_ROLES_TABLE = f"{PREFIX}-GlobalRoles"
GLOBAL_ROLE_PERMISSIONS_TABLE = f"{PREFIX}-GlobalRolePermissions"
GLOBAL_PEOPLE_TABLE = f"{PREFIX}-GlobalPeople"
GLOBAL_ASSIGNMENTS_TABLE = f"{PREFIX}-GlobalAssignments"
# Product catalogue & discount rules — see catalogue app. `centre_id` is
# absent on global (org-wide) rows and set on centre-specific additions.
CATALOGUE_ITEMS_TABLE = f"{PREFIX}-CatalogueItems"
DISCOUNT_RULES_TABLE = f"{PREFIX}-DiscountRules"
ATTENDANCE_TABLE = f"{PREFIX}-Attendance"
COURSE_PROGRESS_TABLE = f"{PREFIX}-CourseProgress"
OTP_TOKENS_TABLE = f"{PREFIX}-OtpTokens"
ROOT_ACCESS_REQUESTS_TABLE = f"{PREFIX}-RootAccessRequests"
JWT_BLACKLIST_TABLE = f"{PREFIX}-JwtBlacklist"

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
    'invoice_ledger': INVOICE_LEDGER_TABLE,
    'invoice_counters': INVOICE_COUNTERS_TABLE,
    'purchases': PURCHASES_TABLE,
    'roles': ROLES_TABLE,
    'role_permissions': ROLE_PERMISSIONS_TABLE,
    'role_members': ROLE_MEMBERS_TABLE,
    'global_roles': GLOBAL_ROLES_TABLE,
    'global_role_permissions': GLOBAL_ROLE_PERMISSIONS_TABLE,
    'global_people': GLOBAL_PEOPLE_TABLE,
    'global_assignments': GLOBAL_ASSIGNMENTS_TABLE,
    'catalogue_items': CATALOGUE_ITEMS_TABLE,
    'discount_rules': DISCOUNT_RULES_TABLE,
    'attendance': ATTENDANCE_TABLE,
    'course_progress': COURSE_PROGRESS_TABLE,
    'otp_tokens': OTP_TOKENS_TABLE,
    'root_access_requests': ROOT_ACCESS_REQUESTS_TABLE,
    'jwt_blacklist': JWT_BLACKLIST_TABLE,
}
