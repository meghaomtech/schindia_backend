"""
Global Roles & Permissions — roles that sit outside/above individual centres.

Structured identically to centre-level roles (same Role/RolePermission/
RoleMember tables, via the GLOBAL_SCOPE sentinel centre_id), but ship with
3 fixed default roles that the rest of the system depends on:

- Super Admin: highest level of control across all of Shichida.
- Centre Manager: members of this role populate the "Centre Manager"
  dropdown in Centre Creation.
- Affiliate: members of this role populate the "Assign Affiliates"
  multi-select in Centre Creation.

Admins can add custom global roles beyond these 3, and delete any role that
isn't one of the 3 defaults (enforced server-side via the is_default flag,
not just in the UI).
"""

from dynamo_backend.services import roles_db
from dynamo_backend.services.roles_service import GLOBAL_SCOPE
from .permissions_catalog import ALL_PERMISSION_KEYS, ROLE_PRESETS

KIND_SUPER_ADMIN = 'super_admin'
KIND_CENTRE_MANAGER = 'centre_manager'
KIND_AFFILIATE = 'affiliate'
KIND_CUSTOM = 'custom'

VALID_KINDS = {KIND_SUPER_ADMIN, KIND_CENTRE_MANAGER, KIND_AFFILIATE, KIND_CUSTOM}
DEFAULT_KINDS = {KIND_SUPER_ADMIN, KIND_CENTRE_MANAGER, KIND_AFFILIATE}


def _full_grant():
    return [{'key': key, 'edit': True, 'visible': True} for key in ALL_PERMISSION_KEYS]


def _grant_for_keys(keys):
    allowed = set(keys)
    return [
        {'key': key, 'edit': True, 'visible': True}
        for key in ALL_PERMISSION_KEYS
        if key in allowed
    ]


DEFAULT_ROLE_SEEDS = [
    {
        'name': 'Super Admin',
        'kind': KIND_SUPER_ADMIN,
        'description': 'Highest level of control across all of Shichida.',
        'permissions': _full_grant(),
    },
    {
        'name': 'Centre Manager',
        'kind': KIND_CENTRE_MANAGER,
        'description': (
            'Centre Manager accounts. Members of this role become selectable '
            'in the Centre Manager dropdown when creating or editing a centre.'
        ),
        'permissions': _grant_for_keys(ROLE_PRESETS.get('Manager', [])),
    },
    {
        'name': 'Affiliate',
        'kind': KIND_AFFILIATE,
        'description': (
            'Affiliate accounts. Members of this role become selectable in '
            'the Assign Affiliates field when creating or editing a centre.'
        ),
        'permissions': [],
    },
]


def ensure_default_global_roles():
    """Idempotently create the 3 default global roles if missing.

    Safe to call on every request that reads/writes global roles — a no-op
    once the defaults exist, and self-heals a fresh or partially-seeded
    environment without needing a one-off migration script.
    """
    existing = roles_db.list_roles(GLOBAL_SCOPE)
    existing_kinds = {r.get('kind') for r in existing}

    created_any = False
    for seed in DEFAULT_ROLE_SEEDS:
        if seed['kind'] in existing_kinds:
            continue
        data = {
            'name': seed['name'],
            'description': seed['description'],
            'kind': seed['kind'],
            'is_default': True,
            'data_scope': 'all',
            'permissions': [dict(p) for p in seed['permissions']],
        }
        roles_db.create_role(GLOBAL_SCOPE, data)
        created_any = True

    return roles_db.list_roles(GLOBAL_SCOPE) if created_any else existing


def get_global_role_by_kind(kind):
    roles = ensure_default_global_roles()
    return next((r for r in roles if r.get('kind') == kind), None)
