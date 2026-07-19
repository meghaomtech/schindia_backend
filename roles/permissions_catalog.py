"""
Canonical permission catalog for Roles & Permissions.

This mirrors the frontend's src/lib/permissions.ts (PERMISSION_CATEGORIES /
ALL_PERMISSION_KEYS export) exactly — keep the two in sync. The frontend file
is the source of truth for the taxonomy; this is the backend's copy of it.
"""

PERMISSION_CATEGORIES = {
    'Children': [
        ('children.view_info', 'View child information'),
        ('children.register_status', 'Register child status'),
        ('children.view_private_info', 'View child private info'),
        ('children.transfer_sites', 'Transfer children across sites'),
        ('children.sign_in_out', 'Sign children in and out'),
        ('children.add', 'Add children'),
        ('children.sibling_linking', 'Manage sibling linking'),
        ('children.manage_notes', 'Manage child notes'),
        ('children.view_notes', 'View child notes'),
        ('children.manage_contacts', 'Manage contacts'),
        ('children.manage_session_requests', 'Manage children session requests (leave or reschedule)'),
    ],
    'Staff': [
        ('staff.access_remotely', 'Access app remotely'),
        ('staff.add', 'Add staff'),
        ('staff.view_profiles', 'View staff profiles'),
        ('staff.edit_profiles', 'Edit staff profiles'),
        ('staff.edit_profile_pictures', 'Edit staff profile pictures'),
        ('staff.manage_personal_details', 'Manage staff personal details'),
        ('staff.view_contract_info', 'View staff contract info'),
        ('staff.manage_contract_info', 'Manage staff contract info'),
        ('staff.view_todos', 'View all staff to-dos'),
        ('staff.manage_leave', 'Manage staff leave'),
        ('staff.view_absence_statuses', 'View staff absence statuses'),
        ('staff.manage_absences', 'Manage staff absences'),
        ('staff.view_absences', 'View staff absences'),
        ('staff.approve_absence_requests', 'Approve staff absence requests'),
        ('staff.manage_own_sign_in', 'Manage own sign in'),
        ('staff.edit_own_attendance', 'Edit own attendance'),
        ('staff.view_all_attendance', 'View all staff attendance'),
        ('staff.edit_all_attendance', 'Edit all staff attendance'),
    ],
    'Communication & Events': [
        ('comms.view_calendar', 'View site calendar'),
        ('comms.add_calendar_events', 'Add calendar events'),
        ('comms.view_news_feed', 'View news feed (all)'),
        ('comms.send_news_posts', 'Send news feed posts'),
        ('comms.edit_all_posts', "Edit all users' posts"),
        ('comms.manage_classroom_messages', 'Manage classroom messages'),
        ('comms.send_private_messages', 'Send private messages to parents'),
        ('comms.send_org_messages', 'Send organisation messages'),
    ],
    'Registration & Forms': [
        ('registration.manage_contracts', 'Manage contracts'),
        ('registration.view_contracts', 'View contracts'),
        ('registration.delete_contracts', 'Delete contracts'),
    ],
    'Learning': [
        ('learning.manage_observations', 'Manage observations'),
        ('learning.view_observations', 'View observations'),
        ('learning.review_send_observations', 'Review and send observations'),
        ('learning.review_observations', 'Review observations'),
        ('learning.manage_activity_library', 'Manage activity library'),
        ('learning.manage_activity_plans', 'Manage activity plans'),
        ('learning.view_activity_plans', 'View activity plans'),
    ],
    'Finances': [
        ('finance.configure_payments', 'Configure in-app payments'),
        ('finance.configure_settings', 'Configure finance settings'),
        ('finance.manage_child_plans', 'Manage child plans'),
        ('finance.view_child_plans', 'View child plans'),
        ('finance.manage_plans_basic', 'Manage plans (basic)'),
        ('finance.manage_child_purchases', 'Manage child purchases'),
        ('finance.override_invoicing_profile', 'Override invoicing profile'),
        ('finance.manage_funding', 'Manage funding'),
        ('finance.manage_child_discounts', 'Manage child discounts'),
        ('finance.manage_child_surcharges', 'Manage child surcharges'),
        ('finance.manage_invoices', 'Manage invoices'),
        ('finance.view_invoices', 'View invoices'),
        ('finance.manage_invoices_basic', 'Manage invoices (basic)'),
        ('finance.cancel_invoices', 'Cancel invoices'),
        ('finance.edit_billing_details', 'Edit billing details'),
        ('finance.manage_bill_payer_accounts', 'Manage bill payer accounts'),
        ('finance.manage_bill_payer_payments', 'Manage bill payer payments'),
        ('finance.manage_bill_payer_surcharges', 'Manage bill payer surcharges'),
        ('finance.manage_bill_payer_credits', 'Manage bill payer credits'),
        ('finance.manage_bill_payer_tags', 'Manage bill payer tags'),
        ('finance.assign_bill_payer_tags', 'Assign bill payer tags'),
        ('finance.view_occupancy_reports', 'View occupancy reports'),
        ('finance.view_financial_reports', 'View financial reports'),
    ],
    'Administration': [
        ('admin.manage_staff_logins', 'Manage staff logins'),
        ('admin.configure_parent_logins', 'Configure parent logins'),
        ('admin.manage_departments_rooms', 'Manage departments and rooms'),
        ('admin.manage_departments', 'Manage departments'),
        ('admin.add_rooms', 'Add rooms'),
        ('admin.delete_rooms', 'Delete rooms'),
        ('admin.edit_rooms', 'Edit rooms'),
        ('admin.configure_centre_settings', 'Configure centre settings'),
        ('admin.edit_tags', 'Edit tags'),
        ('admin.configure_features', 'Configure features'),
    ],
    'Security': [
        ('security.configure', 'Configure security'),
    ],
    'Data Management': [
        ('data.manage_exports', 'Manage data exports'),
        ('data.delete_org_personal_data', 'Delete organisation personal data'),
        ('data.manage_content_reports', 'Manage content reports'),
    ],
}

ALL_PERMISSION_KEYS = [
    key for keys in PERMISSION_CATEGORIES.values() for key, _label in keys
]

# Default permission presets by role name, mirroring the frontend's
# AddRoleModal.tsx name-alias table + src/lib/permissions.ts presets.
# Every listed key is granted {edit: True, visible: True}; unlisted keys
# default to {edit: False, visible: False}. All-or-nothing per key — no
# preset grants view-only access.
ROLE_NAME_ALIASES = {
    'manager': 'Manager',
    'admin': 'Manager',
    'administrator': 'Manager',
    'teacher': 'Teacher',
    'parent': 'Parent',
    'guardian': 'Parent',
}

ROLE_PRESETS = {
    'Manager': [
        'children.view_info', 'children.register_status', 'children.view_private_info',
        'children.sign_in_out', 'children.add', 'children.manage_notes', 'children.view_notes',
        'staff.view_profiles',
        'comms.view_calendar', 'comms.add_calendar_events', 'comms.view_news_feed',
        'comms.send_news_posts', 'comms.manage_classroom_messages',
        'registration.view_contracts',
        'learning.manage_observations', 'learning.view_observations', 'learning.view_activity_plans',
        'finance.view_invoices', 'finance.view_occupancy_reports', 'finance.view_financial_reports',
    ],
    'Teacher': [
        'children.view_info', 'children.sign_in_out', 'children.manage_notes', 'children.view_notes',
        'comms.view_calendar', 'comms.view_news_feed', 'comms.send_news_posts',
        'comms.manage_classroom_messages',
        'learning.manage_observations', 'learning.view_observations',
        'learning.manage_activity_plans', 'learning.view_activity_plans',
    ],
    'Parent': [
        'children.view_info', 'children.view_notes',
        'comms.view_calendar', 'comms.view_news_feed',
        'learning.view_activity_plans',
        'finance.view_invoices',
    ],
}
