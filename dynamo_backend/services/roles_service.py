"""DynamoDB service for Role, Permission, and Member operations."""

import uuid
from ..service import DynamoDBService
from ..tables import ROLES_TABLE, ROLE_PERMISSIONS_TABLE, ROLE_MEMBERS_TABLE


class RolesDynamoService:
    def __init__(self):
        self.roles = DynamoDBService(ROLES_TABLE)
        self.permissions = DynamoDBService(ROLE_PERMISSIONS_TABLE)
        self.members = DynamoDBService(ROLE_MEMBERS_TABLE)

    # Role CRUD
    def create_role(self, centre_id, data):
        """Create a role with optional permissions."""
        permissions_data = data.pop('permissions', [])
        data['id'] = str(uuid.uuid4())
        data['centre_id'] = str(centre_id)

        role = self.roles.create(data)

        for perm in permissions_data:
            perm['id'] = str(uuid.uuid4())
            perm['role_id'] = role['id']
            self.permissions.create(perm)

        role['permissions'] = self.list_permissions(role['id'])
        role['members'] = []
        return role

    def get_role(self, role_id):
        """Get role with permissions and members."""
        role = self.roles.get(str(role_id))
        if role:
            role['permissions'] = self.list_permissions(role_id)
            role['members'] = self.list_members(role_id)
        return role

    def list_roles(self, centre_id):
        """List all roles for a centre."""
        roles = self.roles.query_by_index('centre_id-index', 'centre_id', str(centre_id))
        for role in roles:
            role['permissions'] = self.list_permissions(role['id'])
            role['members'] = self.list_members(role['id'])
        return roles

    def update_role(self, role_id, updates):
        permissions_data = updates.pop('permissions', None)
        role = self.roles.update(str(role_id), updates)

        if permissions_data is not None:
            # Replace all permissions
            old = self.list_permissions(role_id)
            for p in old:
                self.permissions.delete(p['id'])
            for perm in permissions_data:
                perm['id'] = str(uuid.uuid4())
                perm['role_id'] = str(role_id)
                self.permissions.create(perm)

        return role

    def delete_role(self, role_id):
        # Delete permissions and members
        for p in self.list_permissions(role_id):
            self.permissions.delete(p['id'])
        for m in self.list_members(role_id):
            self.members.delete(m['id'])
        return self.roles.delete(str(role_id))

    # Permissions
    def list_permissions(self, role_id):
        return self.permissions.query_by_index('role_id-index', 'role_id', str(role_id))

    def update_permission(self, role_id, key, updates):
        """Update or create a permission by role_id and key."""
        perms = self.list_permissions(role_id)
        existing = next((p for p in perms if p.get('key') == key), None)

        if existing:
            return self.permissions.update(existing['id'], updates)
        else:
            data = {
                'id': str(uuid.uuid4()),
                'role_id': str(role_id),
                'key': key,
                'edit': updates.get('edit', False),
                'visible': updates.get('visible', False),
            }
            return self.permissions.create(data)

    # Members
    def list_members(self, role_id):
        return self.members.query_by_index('role_id-index', 'role_id', str(role_id))

    def add_member(self, role_id, user_id, name='', email=''):
        """Add a user to a role. Stores name and email for display."""
        # Check if already a member
        existing = self.list_members(role_id)
        if any(m.get('user_id') == str(user_id) for m in existing):
            return None  # Already exists

        data = {
            'id': str(uuid.uuid4()),
            'role_id': str(role_id),
            'user_id': str(user_id),
            'name': name,
            'email': email,
        }
        return self.members.create(data)

    def remove_member(self, role_id, user_id):
        """Remove a user from a role. user_id can be either the user_id or the member record id."""
        members = self.list_members(role_id)
        # Try matching by user_id first, then by member record id
        member = next((m for m in members if m.get('user_id') == str(user_id)), None)
        if not member:
            member = next((m for m in members if m.get('id') == str(user_id)), None)
        if member:
            return self.members.delete(member['id'])
        return False
