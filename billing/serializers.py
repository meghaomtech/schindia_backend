from rest_framework import serializers
from .models import Invoice, InvoiceItem, InvoiceExtraItem, InvoiceDeduction, InvoiceSentTo, Purchase


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'amount']
        read_only_fields = ['id']


class InvoiceExtraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceExtraItem
        fields = ['id', 'description', 'amount', 'quantity']
        read_only_fields = ['id']


class InvoiceDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceDeduction
        fields = ['id', 'description', 'amount', 'quantity']
        read_only_fields = ['id']


class InvoiceSentToSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceSentTo
        fields = ['id', 'channel', 'target']
        read_only_fields = ['id']


class InvoiceListSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    extra_items = InvoiceExtraItemSerializer(many=True, read_only=True)
    deductions = InvoiceDeductionSerializer(many=True, read_only=True)
    sent_to = InvoiceSentToSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'child', 'invoice_date', 'due_date',
            'payment_term', 'tax_rate', 'status', 'sent_at',
            'student_name', 'parent_name', 'center_code',
            'registration_fee', 'session_fee_amount',
            'gst_percent', 'gst_amount', 'debit_brought_forward', 'total_amount',
            'items', 'extra_items', 'deductions', 'sent_to', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'gst_amount', 'total_amount']


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    extra_items = InvoiceExtraItemSerializer(many=True, required=False)
    deductions = InvoiceDeductionSerializer(many=True, required=False)
    sent_to = InvoiceSentToSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'child', 'invoice_date', 'due_date',
            'payment_term', 'tax_rate', 'status', 'sent_at',
            'student_name', 'parent_name', 'center_code',
            'registration_fee', 'session_fee_amount',
            'gst_percent', 'debit_brought_forward',
            'items', 'extra_items', 'deductions', 'sent_to',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        extra_items_data = validated_data.pop('extra_items', [])
        deductions_data = validated_data.pop('deductions', [])
        sent_to_data = validated_data.pop('sent_to', [])

        invoice = Invoice.objects.create(**validated_data)

        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        for extra_data in extra_items_data:
            InvoiceExtraItem.objects.create(invoice=invoice, **extra_data)
        for deduction_data in deductions_data:
            InvoiceDeduction.objects.create(invoice=invoice, **deduction_data)
        for sent_data in sent_to_data:
            InvoiceSentTo.objects.create(invoice=invoice, **sent_data)

        # Calculate totals after creating related items
        invoice.calculate_totals()
        invoice.save(update_fields=['gst_amount', 'total_amount'])

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        extra_items_data = validated_data.pop('extra_items', None)
        deductions_data = validated_data.pop('deductions', None)
        sent_to_data = validated_data.pop('sent_to', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                InvoiceItem.objects.create(invoice=instance, **item_data)

        if extra_items_data is not None:
            instance.extra_items.all().delete()
            for extra_data in extra_items_data:
                InvoiceExtraItem.objects.create(invoice=instance, **extra_data)

        if deductions_data is not None:
            instance.deductions.all().delete()
            for deduction_data in deductions_data:
                InvoiceDeduction.objects.create(invoice=instance, **deduction_data)

        if sent_to_data is not None:
            instance.sent_to.all().delete()
            for sent_data in sent_to_data:
                InvoiceSentTo.objects.create(invoice=instance, **sent_data)

        # Recalculate totals
        instance.calculate_totals()
        instance.save(update_fields=['gst_amount', 'total_amount'])

        return instance


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = [
            'id', 'child', 'kind', 'name', 'date', 'amount', 'paid', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
