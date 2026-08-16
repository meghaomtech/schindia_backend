"""DynamoDB service for the product catalogue and discount rules.

Items and rules with no `centre_id` are global — visible at every centre.
Items with a `centre_id` are additions specific to that one centre. Tables
are small (tens to low hundreds of rows), so listing scans and filters in
Python rather than relying on the sparse `centre_id-index` GSI.
"""

import uuid
from ..service import DynamoDBService
from ..tables import CATALOGUE_ITEMS_TABLE, DISCOUNT_RULES_TABLE


class CatalogueDynamoService:
    def __init__(self):
        self.items = DynamoDBService(CATALOGUE_ITEMS_TABLE)
        self.discounts = DynamoDBService(DISCOUNT_RULES_TABLE)

    # ── Catalogue items ─────────────────────────────────────────────
    def list_items(self, centre_id=None, include_inactive=True):
        """Global items, plus `centre_id`'s own additions if given."""
        rows = self.items.list_all()
        if centre_id:
            rows = [r for r in rows if not r.get('centre_id') or r['centre_id'] == str(centre_id)]
        else:
            rows = [r for r in rows if not r.get('centre_id')]
        if not include_inactive:
            rows = [r for r in rows if r.get('active', True)]
        return rows

    def get_item(self, item_id):
        return self.items.get(str(item_id))

    def create_item(self, data):
        data['id'] = str(uuid.uuid4())
        data.setdefault('active', True)
        return self.items.create(data)

    def update_item(self, item_id, updates):
        return self.items.update(str(item_id), updates)

    def delete_item(self, item_id):
        return self.items.delete(str(item_id))

    # ── Discount rules ──────────────────────────────────────────────
    def list_discounts(self, centre_id=None, include_inactive=True):
        rows = self.discounts.list_all()
        if centre_id:
            rows = [r for r in rows if not r.get('centre_id') or r['centre_id'] == str(centre_id)]
        else:
            rows = [r for r in rows if not r.get('centre_id')]
        if not include_inactive:
            rows = [r for r in rows if r.get('active', True)]
        return rows

    def get_discount(self, discount_id):
        return self.discounts.get(str(discount_id))

    def create_discount(self, data):
        data['id'] = str(uuid.uuid4())
        data.setdefault('active', True)
        return self.discounts.create(data)

    def update_discount(self, discount_id, updates):
        return self.discounts.update(str(discount_id), updates)

    def delete_discount(self, discount_id):
        return self.discounts.delete(str(discount_id))
