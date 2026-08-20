"""DynamoDB service for Global (org-wide) Role, Permission, Person and Assignment operations.

Mirrors roles_service.py's Role/RolePermission/RoleMember pattern, but at
global scope (no centre_id) and with a standalone People table instead of
RoleMembers — a global "person" isn't always a portal login (e.g. an
Affiliate can be a partner organisation with no account).
"""

import uuid
from ..service import DynamoDBService
from ..tables import (
    GLOBAL_ROLES_TABLE,
    GLOBAL_ROLE_PERMISSIONS_TABLE,
    GLOBAL_PEOPLE_TABLE,
    GLOBAL_ASSIGNMENTS_TABLE,
)


class GlobalAccessDynamoService:
    def __init__(self):
        self.roles = DynamoDBService(GLOBAL_ROLES_TABLE)
        self.permissions = DynamoDBService(GLOBAL_ROLE_PERMISSIONS_TABLE)
        self.people = DynamoDBService(GLOBAL_PEOPLE_TABLE)
        self.assignments = DynamoDBService(GLOBAL_ASSIGNMENTS_TABLE)

    # ── Roles ───────────────────────────────────────────────────────
    def create_role(self, data):
        """Create a global role with optional permissions."""
        permissions_data = data.pop('permissions', [])
        data['id'] = str(uuid.uuid4())

        role = self.roles.create(data)

        for perm in permissions_data:
            perm['id'] = str(uuid.uuid4())
            perm['role_id'] = role['id']
            self.permissions.create(perm)

        role['permissions'] = self.list_permissions(role['id'])
        role['member_count'] = 0
        return role

    def get_role(self, role_id):
        role = self.roles.get(str(role_id))
        if role:
            role['permissions'] = self.list_permissions(role_id)
            role['member_count'] = len(self.list_assignments(role_id=role_id))
        return role

    def list_roles(self):
        roles = self.roles.list_all()
        for role in roles:
            role['permissions'] = self.list_permissions(role['id'])
            role['member_count'] = len(self.list_assignments(role_id=role['id']))
        return roles

    def update_role(self, role_id, updates):
        permissions_data = updates.pop('permissions', None)
        role = self.roles.update(str(role_id), updates)

        if permissions_data is not None:
            old = self.list_permissions(role_id)
            for p in old:
                self.permissions.delete(p['id'])
            for perm in permissions_data:
                perm['id'] = str(uuid.uuid4())
                perm['role_id'] = str(role_id)
                self.permissions.create(perm)

        return role

    def delete_role(self, role_id):
        """Deletes the role, its permissions, and every assignment to it —
        callers (views.py) are responsible for blocking this on protected
        roles (kind is set) before calling here.
        """
        for p in self.list_permissions(role_id):
            self.permissions.delete(p['id'])
        for a in self.list_assignments(role_id=role_id):
            self.assignments.delete(a['id'])
        return self.roles.delete(str(role_id))

    # ── Permissions ─────────────────────────────────────────────────
    def list_permissions(self, role_id):
        return self.permissions.query_by_index('role_id-index', 'role_id', str(role_id))

    def update_permission(self, role_id, key, updates):
        """Update or create a permission by role_id and key."""
        perms = self.list_permissions(role_id)
        existing = next((p for p in perms if p.get('key') == key), None)

        if existing:
            return self.permissions.update(existing['id'], updates)
        data = {
            'id': str(uuid.uuid4()),
            'role_id': str(role_id),
            'key': key,
            'edit': updates.get('edit', False),
            'visible': updates.get('visible', False),
        }
        return self.permissions.create(data)

    # ── People & assignments ────────────────────────────────────────
    def list_assignments(self, role_id=None, person_id=None):
        if role_id:
            return self.assignments.query_by_index('role_id-index', 'role_id', str(role_id))
        if person_id:
            return self.assignments.query_by_index('person_id-index', 'person_id', str(person_id))
        return self.assignments.list_all()

    def list_people(self):
        """Every global person, each carrying the role(s) assigned to them."""
        people = self.people.list_all()
        assignments = self.assignments.list_all()
        roles_by_id = {r['id']: r for r in self.roles.list_all()}

        by_person = {}
        for a in assignments:
            by_person.setdefault(a['person_id'], []).append(a)

        for person in people:
            person_assignments = by_person.get(person['id'], [])
            person['roles'] = [
                {
                    'assignment_id': a['id'],
                    'role_id': a['role_id'],
                    'role_name': roles_by_id.get(a['role_id'], {}).get('name', ''),
                    'centre_id': a.get('centre_id'),
                    'include_sub_centres': a.get('include_sub_centres', False),
                }
                for a in person_assignments
            ]
        return people

    def get_person(self, person_id):
        return self.people.get(str(person_id))

    def add_person(self, name, email, role_id, member_type='person',
                   profile=None, centre_id=None, include_sub_centres=False):
        """
        Create a person and assign them to a global role in one step.

        `profile` carries the optional staff-record fields collected by the
        onboarding wizard (job title, phone, emergency contact, identity and
        bank details). They're stored as-is; access control happens on the
        way out, in global_access.views._visible_person.
        """
        record = {'name': name, 'email': email, 'member_type': member_type}
        record.update(profile or {})
        person = self.people.create(record)
        assignment = self.assign_role(
            person['id'], role_id,
            centre_id=centre_id, include_sub_centres=include_sub_centres,
        )
        person['roles'] = [{
            'assignment_id': assignment['id'],
            'role_id': str(role_id),
            'centre_id': centre_id,
            'include_sub_centres': include_sub_centres,
        }]
        return person

    def update_person(self, person_id, updates):
        """Patch a staff record. Callers are responsible for field-level access."""
        return self.people.update(str(person_id), updates)

    def assign_role(self, person_id, role_id, centre_id=None, include_sub_centres=False):
        """
        Give a global person a role, optionally scoped to one centre.

        The same role at two different centres is a legitimate assignment
        (Priya is Teacher at Sunshine and Manager at Little Stars), so the
        duplicate check keys on the role *and* the centre rather than the
        role alone.
        """
        existing = self.list_assignments(person_id=person_id)
        if any(
            a['role_id'] == str(role_id) and (a.get('centre_id') or None) == (centre_id or None)
            for a in existing
        ):
            return None  # Already assigned at this scope
        return self.assignments.create({
            'id': str(uuid.uuid4()),
            'person_id': str(person_id),
            'role_id': str(role_id),
            'centre_id': centre_id or None,
            'include_sub_centres': bool(include_sub_centres),
        })

    def remove_person(self, person_id):
        """Removes the person from Global settings entirely — every assignment they hold."""
        for a in self.list_assignments(person_id=person_id):
            self.assignments.delete(a['id'])
        return self.people.delete(str(person_id))

    def remove_assignment(self, assignment_id):
        return self.assignments.delete(str(assignment_id))
