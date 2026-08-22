"""DynamoDB service for Invoice and Purchase operations."""

import uuid
from ..service import DynamoDBService
from ..tables import (
    INVOICES_TABLE, INVOICE_ITEMS_TABLE, INVOICE_LEDGER_TABLE,
    INVOICE_COUNTERS_TABLE, PURCHASES_TABLE,
)


class BillingDynamoService:
    def __init__(self):
        self.invoices = DynamoDBService(INVOICES_TABLE)
        self.invoice_items = DynamoDBService(INVOICE_ITEMS_TABLE)
        self.ledger = DynamoDBService(INVOICE_LEDGER_TABLE)
        self.invoice_counters = DynamoDBService(INVOICE_COUNTERS_TABLE)
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

    def list_invoices(self, child_id=None, user_id=None, centre_id=None):
        """
        List invoices filtered by child, user or centre.

        Centre matters on its own because an invoice can be raised at reception
        without naming a child — a registration fee taken before enrolment, for
        instance. Reaching invoices only through children loses exactly those,
        and they are unreachable afterwards at any centre.
        """
        if child_id:
            invoices = self.invoices.query_by_index('child_id-index', 'child_id', str(child_id))
        elif user_id:
            invoices = self.invoices.query_by_index('user_id-index', 'user_id', str(user_id))
        elif centre_id:
            invoices = self.invoices.query_by_index('centre_id-index', 'centre_id', str(centre_id))
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
    def get_purchase(self, purchase_id):
        return self.purchases.get(str(purchase_id))

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

    # ── Ledger: payments and corrections ────────────────────────────
    # Append-only. Nothing here edits the invoice, so the issued document
    # always reconciles to what was sent and the balance stays derivable.

    def list_ledger(self, invoice_id):
        return self.ledger.query_by_index('invoice_id-index', 'invoice_id', str(invoice_id))

    def add_ledger_entry(self, invoice_id, kind, amount, reason='', method='',
                         occurred_on=None, recorded_by=''):
        """Record one act against an invoice (payment, credit, write-off, refund)."""
        return self.ledger.create({
            'id': str(uuid.uuid4()),
            'invoice_id': str(invoice_id),
            'kind': kind,
            'amount': str(amount),
            'reason': reason,
            'method': method,
            'occurred_on': occurred_on or '',
            'recorded_by': recorded_by,
        })

    def get_ledger_entry(self, entry_id):
        return self.ledger.get(str(entry_id))

    def delete_ledger_entry(self, entry_id):
        return self.ledger.delete(str(entry_id))

    def cancel_invoice(self, invoice_id, reason, cancelled_by=''):
        """
        Void an issued invoice. Never deletes it — the number and the trail
        have to survive, or the GST series has a hole nobody can explain.
        """
        from datetime import datetime
        return self.update_invoice(str(invoice_id), {
            'cancelled_at': datetime.utcnow().isoformat(),
            'cancelled_reason': reason,
            'cancelled_by': cancelled_by,
        })

    # ── Invoice number series ────────────────────────────────────────
    # One unbroken org-wide series. The counter lives server-side and is
    # incremented atomically: a per-browser counter issues duplicates the
    # moment two people raise invoices at once, which a GST series cannot
    # survive being audited with.

    COUNTER_KEY = 'invoice'

    def _format_invoice_number(self, count, year=None):
        from datetime import date
        yr = str(year or date.today().year)[-2:]
        return f"BA{yr}{str(count).zfill(4)}"

    def peek_invoice_number(self):
        """
        The number that *would* be issued next, without consuming it.

        Opening a form and walking away must not burn a number — that is how
        series end up with holes nobody can explain.
        """
        row = self.invoice_counters.get(self.COUNTER_KEY) or {}
        return self._format_invoice_number(int(row.get('count', 0)) + 1)

    def allocate_invoice_number(self):
        """Consume the next number. Atomic, so concurrent callers never collide."""
        resp = self.invoice_counters.table.update_item(
            Key={'id': self.COUNTER_KEY},
            UpdateExpression='ADD #c :one',
            ExpressionAttributeNames={'#c': 'count'},
            ExpressionAttributeValues={':one': 1},
            ReturnValues='UPDATED_NEW',
        )
        return self._format_invoice_number(int(resp['Attributes']['count']))
