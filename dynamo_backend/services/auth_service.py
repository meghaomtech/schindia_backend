"""DynamoDB service for User/Auth operations."""

import uuid
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password

from ..service import DynamoDBService
from ..tables import USERS_TABLE


class AuthDynamoService:
    def __init__(self):
        self.db = DynamoDBService(USERS_TABLE)

    def create_user(self, email, password, first_name, last_name, role='admin', status='pending'):
        """Create a new user with hashed password."""
        user = {
            'id': str(uuid.uuid4()),
            'email': email,
            'username': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': make_password(password),
            'role': role,
            'status': status,
            'is_active': True,
            'requested_at': datetime.utcnow().isoformat(),
        }
        return self.db.create(user)

    def get_user_by_id(self, user_id):
        """Get user by UUID."""
        return self.db.get(str(user_id))

    def get_user_by_email(self, email):
        """Get user by email using GSI."""
        users = self.db.query_by_index('email-index', 'email', email)
        return users[0] if users else None

    def verify_password(self, user, raw_password):
        """Check password against stored hash."""
        return check_password(raw_password, user.get('password', ''))

    def update_user(self, user_id, updates):
        """Update user fields."""
        return self.db.update(str(user_id), updates)

    def list_by_role(self, role):
        """List all users with a specific role."""
        return self.db.query_by_field('role', role)

    def list_access_requests(self):
        """List all admin users (access requests)."""
        return self.db.query_by_field('role', 'admin')

    def root_exists(self):
        """Check if a root user already exists."""
        roots = self.db.query_by_field('role', 'root')
        return len(roots) > 0

    def get_all_users(self):
        """List all users."""
        return self.db.list_all()
