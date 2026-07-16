"""DynamoDB service for Invoice and Purchase operations."""

import uuid
from ..service import DynamoDBService
from ..tables import INVOICES_TABLE, INVOICE_ITEMS_TABLE, PURCHASES_TABLE


class BillingDynamoService:
    def __init__(self):
        self.invoices = DynamoDBService(INVOICES_TABLE)
        self.invoice_items = DynamoDBService(INVOICE_ITEMS_TABLE)
        self.purchases = DynamoDBService(PURCHASES_TABLE)

    # Invoice CRUD
    def create_invoice(self, data):
        """Create invoice with items."""
        items_data = data.pop('items', [])
        data['id'] = str(uuid.uuid4())

        invoice = self.invoices.create(data)

        created_items = []
        for item in items_data:
            item['id'] = str(uuid.uuid4())
            item['invoice_id'] = invoice['id']
            created_items.append(self.invoice_items.create(item))

        invoice['items'] = created_items
        return invoice

    def get_invoice(self, invoice_id):
        """Get invoice with items."""
        invoice = self.invoices.get(str(invoice_id))
        if invoice:
            invoice['items'] = self.list_invoice_items(invoice_id)
        return invoice

    def list_invoices(self, child_id=None, user_id=None):
        """List invoices filtered by child or user."""
        if child_id:
            invoices = self.invoices.query_by_index('child_id-index', 'child_id', str(child_id))
        elif user_id:
            invoices = self.invoices.query_by_index('user_id-index', 'user_id', str(user_id))
        else:
            invoices = self.invoices.list_all()

        for inv in invoices:
            inv['items'] = self.list_invoice_items(inv['id'])
        return invoices

    def update_invoice(self, invoice_id, updates):
        """Update invoice. If items provided, replace them."""
        items_data = updates.pop('items', None)
        invoice = self.invoices.update(str(invoice_id), updates)

        if items_data is not None:
            # Delete old items
            old_items = self.list_invoice_items(invoice_id)
            for item in old_items:
                self.invoice_items.delete(item['id'])
            # Create new items
            for item in items_data:
                item['id'] = str(uuid.uuid4())
                item['invoice_id'] = str(invoice_id)
                self.invoice_items.create(item)

        return invoice

    def delete_invoice(self, invoice_id):
        """Delete invoice and its items."""
        items = self.list_invoice_items(invoice_id)
        for item in items:
            self.invoice_items.delete(item['id'])
        return self.invoices.delete(str(invoice_id))

    def add_sent_to(self, invoice_id, channel, target):
        """Record that an invoice was sent via a channel (email/sms). Embedded on the invoice."""
        invoice = self.invoices.get(str(invoice_id))
        sent_to = (invoice or {}).get('sent_to') or []
        sent_to.append({'channel': channel, 'target': target})
        return self.invoices.update(str(invoice_id), {'sent_to': sent_to})

    def list_invoice_items(self, invoice_id):
        return self.invoice_items.query_by_index('invoice_id-index', 'invoice_id', str(invoice_id))

    # Purchase CRUD
    def list_purchases(self, child_id):
        return self.purchases.query_by_index('child_id-index', 'child_id', str(child_id))

    def create_purchase(self, child_id, data):
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.purchases.create(data)

    def update_purchase(self, purchase_id, updates):
        return self.purchases.update(str(purchase_id), updates)

    def delete_purchase(self, purchase_id):
        return self.purchases.delete(str(purchase_id))
