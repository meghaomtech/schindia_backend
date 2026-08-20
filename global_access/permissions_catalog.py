"""
Canonical capability catalog for Global Roles & Permissions.

Mirrors the frontend's src/lib/globalAccess.ts (GLOBAL_CAPABILITIES /
CAPABILITY_CATEGORIES) exactly — keep the two in sync. The frontend file is
the source of truth for the taxonomy; this is the backend's copy of it.

Distinct from roles/permissions_catalog.py, which is the centre-scoped
taxonomy (Children, Staff, Finances, ...). This one is org-wide: Centres,
Global roles & people, Organisation finance, Data & security.
"""

CAPABILITY_CATEGORIES = {
    'Centres': [
        ('view_all_centres', 'View all centres'),
        ('create_centres', 'Create centres'),
        ('edit_any_centre', 'Edit any centre'),
        ('create_sub_centres', 'Create sub-centres'),
        ('archive_centres', 'Archive centres'),
        ('assign_centre_managers', 'Assign centre managers'),
        ('assign_affiliates_to_centres', 'Assign affiliates to centres'),
    ],
    'Global roles & people': [
        ('view_global_roles', 'View global roles'),
        ('view_people_directory', 'View people directory'),
        ('manage_global_roles', 'Add, edit and delete global roles'),
        ('create_centre_manager_accounts', 'Create Centre Manager accounts'),
        ('create_affiliate_accounts', 'Create Affiliate accounts'),
        ('manage_logins_access_requests', 'Manage logins & access requests'),
        ('onboard_staff', 'Onboard staff members'),
    ],
    # Staff records carry regulated personal data (Aadhaar, PAN, bank
    # details). These two keys gate it server-side — the fields are stripped
    # from every response unless the caller holds the matching capability,
    # so hiding them in the UI is never the only control. A person can always
    # see their own record; see global_access.views._visible_person.
    'Staff records': [
        ('staff_identity_documents', 'Identity & documents'),
        ('staff_bank_salary_details', 'Bank & salary details'),
    ],
    'Organisation finance': [
        ('product_catalogue', 'Product catalogue'),
        ('discounts_affiliate_rates', 'Discounts & affiliate rates'),
        ('financial_reports', 'Organisation financial reports'),
    ],
    'Data & security': [
        ('organisation_settings', 'Organisation settings'),
        ('security_policy', 'Security policy'),
        ('data_exports', 'Data exports'),
        ('delete_organisation_data', 'Delete organisation data'),
    ],
}

ALL_CAPABILITY_KEYS = [
    key for keys in CAPABILITY_CATEGORIES.values() for key, _label in keys
]

# Seeded so the app has something to show on first run — matches the
# frontend's SEED_ROLES in src/lib/globalAccess.ts. `kind` marks the three
# built-ins other screens depend on (selectable as a centre's manager /
# affiliate); only roles with no `kind` may be deleted.
SEED_ROLES = [
    {
        'kind': 'super_admin',
        'name': 'Super Admin',
        'description': 'Total control across the organisation. Holds every capability automatically.',
        'grants': {key: 'edit' for key in ALL_CAPABILITY_KEYS},
    },
    {
        'kind': 'centre_manager',
        'name': 'Centre Manager',
        'description': 'Runs one or more centres. Selectable as the manager when a centre is created.',
        'grants': {
            'edit_any_centre': 'edit',
            'create_sub_centres': 'edit',
            'view_all_centres': 'view',
            'view_global_roles': 'view',
            'view_people_directory': 'view',
            'financial_reports': 'view',
        },
    },
    {
        'kind': 'affiliate',
        'name': 'Affiliate',
        'description': (
            'Refers families to a centre — an individual referrer or a partner organisation. '
            'Read-only visibility of the centres they introduce business to.'
        ),
        'grants': {
            'view_all_centres': 'view',
            'financial_reports': 'view',
        },
    },
]
