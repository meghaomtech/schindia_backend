import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from children.models import Child


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
        ('Generated', 'Generated'),
    ]
    TERM_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Half-yearly', 'Half-yearly'),
        ('Annually', 'Annually'),
        ('One-time', 'One-time'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=50, unique=True)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='invoices')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoices'
    )
    invoice_date = models.DateField()
    due_date = models.DateField()
    payment_term = models.CharField(max_length=20, choices=TERM_CHOICES)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Draft')
    sent_at = models.DateTimeField(null=True, blank=True)

    # Fee calculation fields (migrated from Lambda)
    student_name = models.CharField(max_length=200, blank=True)
    parent_name = models.CharField(max_length=200, blank=True)
    center_code = models.CharField(max_length=50, blank=True)
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    session_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    debit_brought_forward = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']

    def __str__(self):
        return f"Invoice {self.number} - {self.child}"

    def calculate_totals(self):
        """Calculate invoice totals from line items (mirrors Lambda logic)."""
        extras_total = self.extra_items.aggregate(
            total=models.Sum(models.F('amount') * models.F('quantity'))
        )['total'] or Decimal('0')

        deductions_total = self.deductions.aggregate(
            total=models.Sum(models.F('amount') * models.F('quantity'))
        )['total'] or Decimal('0')

        subtotal = self.registration_fee + self.session_fee_amount + extras_total - deductions_total
        self.gst_amount = (subtotal * self.gst_percent / Decimal('100')).quantize(Decimal('0.01'))
        self.total_amount = subtotal + self.gst_amount + self.debit_brought_forward
        return self.total_amount


class InvoiceItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"


class InvoiceExtraItem(models.Model):
    """Extra fee items (maps to Lambda's extraItems array)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='extra_items')
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Extra: {self.description} x{self.quantity} @ {self.amount}"


class InvoiceDeduction(models.Model):
    """Deduction items (maps to Lambda's deductions array)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='deductions')
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Deduction: {self.description} x{self.quantity} @ {self.amount}"


class InvoiceSentTo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='sent_to')
    channel = models.CharField(max_length=10)  # 'email' or 'sms'
    target = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.channel}: {self.target}"


class Purchase(models.Model):
    KIND_CHOICES = [
        ('Session', 'Session'),
        ('Consumable', 'Consumable'),
        ('Late fee', 'Late fee'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='purchases')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    name = models.CharField(max_length=200)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.kind}: {self.name} - {self.child}"
