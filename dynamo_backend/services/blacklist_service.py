"""DynamoDB service for revoked JWTs (replaces rest_framework_simplejwt.token_blacklist)."""

from datetime import datetime, timezone

from ..client import get_table
from ..tables import JWT_BLACKLIST_TABLE


class BlacklistDynamoService:
    def __init__(self):
        self.table_name = JWT_BLACKLIST_TABLE

    @property
    def table(self):
        return get_table(self.table_name)

    def add(self, jti, exp):
        """Blacklist a token by its jti. `exp` is a unix timestamp (or datetime) —
        stored as the DynamoDB TTL attribute so the row auto-expires once the
        token itself would have expired anyway."""
        if isinstance(exp, datetime):
            expires_at = int(exp.timestamp())
        else:
            expires_at = int(exp)

        self.table.put_item(Item={
            'jti': str(jti),
            'expires_at': expires_at,
            'blacklisted_at': int(datetime.now(timezone.utc).timestamp()),
        })

    def is_blacklisted(self, jti):
        response = self.table.get_item(Key={'jti': str(jti)})
        return 'Item' in response
