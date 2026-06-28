from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceSentTo, Purchase


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


class InvoiceSentToInline(admin.TabularInline):
    model = InvoiceSentTo
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'child', 'invoice_date', 'due_date', 'status']
    list_filter = ['status', 'payment_term']
    search_fields = ['number', 'child__first_name', 'child__last_name']
    inlines = [InvoiceItemInline, InvoiceSentToInline]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['child', 'kind', 'name', 'date', 'amount', 'paid']
    list_filter = ['kind', 'paid']
    search_fields = ['name', 'child__first_name', 'child__last_name']
