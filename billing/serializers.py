from rest_framework import serializers
from .models import Invoice, InvoiceItem, InvoiceSentTo, Purchase


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'amount']
        read_only_fields = ['id']


class InvoiceSentToSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceSentTo
        fields = ['id', 'channel', 'target']
        read_only_fields = ['id']


class InvoiceListSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    sent_to = InvoiceSentToSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'child', 'invoice_date', 'due_date',
            'payment_term', 'tax_rate', 'status', 'sent_at',
            'items', 'sent_to', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    sent_to = InvoiceSentToSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'child', 'invoice_date', 'due_date',
            'payment_term', 'tax_rate', 'status', 'sent_at',
            'items', 'sent_to',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        sent_to_data = validated_data.pop('sent_to', [])

        invoice = Invoice.objects.create(**validated_data)

        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        for sent_data in sent_to_data:
            InvoiceSentTo.objects.create(invoice=invoice, **sent_data)

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        sent_to_data = validated_data.pop('sent_to', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                InvoiceItem.objects.create(invoice=instance, **item_data)

        if sent_to_data is not None:
            instance.sent_to.all().delete()
            for sent_data in sent_to_data:
                InvoiceSentTo.objects.create(invoice=instance, **sent_data)

        return instance


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = [
            'id', 'child', 'kind', 'name', 'date', 'amount', 'paid', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
