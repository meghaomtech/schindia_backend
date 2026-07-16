"""DynamoDB service for root-access-request approval (replaces the Django Admin workflow)."""

from datetime import datetime

from ..service import DynamoDBService
from ..tables import ROOT_ACCESS_REQUESTS_TABLE


class RootAccessDynamoService:
    def __init__(self):
        self.db = DynamoDBService(ROOT_ACCESS_REQUESTS_TABLE)

    def create_request(self, name, email, password_hash):
        return self.db.create({
            'name': name,
            'email': email,
            'password': password_hash,
            'status': 'pending',
            'requested_at': datetime.utcnow().isoformat(),
        })

    def get_by_email(self, email):
        rows = self.db.query_by_index('email-index', 'email', email)
        return rows[0] if rows else None

    def get(self, request_id):
        return self.db.get(str(request_id))

    def list_requests(self):
        return self.db.list_all()

    def approve(self, request_id):
        return self.db.update(str(request_id), {
            'status': 'approved',
            'reviewed_at': datetime.utcnow().isoformat(),
        })

    def reject(self, request_id):
        return self.db.update(str(request_id), {
            'status': 'rejected',
            'reviewed_at': datetime.utcnow().isoformat(),
        })
