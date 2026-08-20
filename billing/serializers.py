"""Validation for ledger acts recorded against an invoice."""
from decimal import Decimal

from rest_framework import serializers

from .ledger import CREDIT_NOTE, PAYMENT, REFUND, WRITE_OFF

# Reasons come from a defined list so reporting can group them, and so
# "why was this forgiven?" has an answer that isn't free text nobody reads.
CORRECTION_REASONS = {
    CREDIT_NOTE: ['billing_error', 'goodwill', 'service_not_delivered', 'duplicate_charge', 'other'],
    WRITE_OFF: ['uncollectable', 'family_hardship', 'below_threshold', 'other'],
    REFUND: ['overpayment', 'cancelled_service', 'duplicate_payment', 'other'],
}

CANCEL_REASONS = ['raised_in_error', 'duplicate', 'wrong_child', 'wrong_amount', 'other']

PAYMENT_METHODS = ['cash', 'card', 'upi', 'bank_transfer', 'cheque', 'other']


class _AmountMixin(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    occurred_on = serializers.DateField(required=False, allow_null=True)

    def validate_amount(self, value):
        # A zero or negative act is never a real correction, and a negative
        # one would quietly invert the balance.
        if value <= Decimal('0'):
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class PaymentSerializer(_AmountMixin):
    """Money received. Partial payments are the normal case, not an edge case."""
    method = serializers.ChoiceField(choices=PAYMENT_METHODS, required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)


class CorrectionSerializer(_AmountMixin):
    """A credit note, write-off or refund — each needs a reason."""
    reason = serializers.CharField(max_length=200)

    def __init__(self, *args, kind=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._kind = kind

    def validate_reason(self, value):
        allowed = CORRECTION_REASONS.get(self._kind)
        if allowed and value not in allowed:
            raise serializers.ValidationError(
                f"Reason must be one of: {', '.join(allowed)}."
            )
        return value


class CancelInvoiceSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=CANCEL_REASONS)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


KIND_SERIALIZERS = {
    PAYMENT: PaymentSerializer,
    CREDIT_NOTE: CorrectionSerializer,
    WRITE_OFF: CorrectionSerializer,
    REFUND: CorrectionSerializer,
}
