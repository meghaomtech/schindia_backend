from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceExtraItem, InvoiceDeduction, InvoiceSentTo, Purchase


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


class InvoiceExtraItemInline(admin.TabularInline):
    model = InvoiceExtraItem
    extra = 0


class InvoiceDeductionInline(admin.TabularInline):
    model = InvoiceDeduction
    extra = 0


class InvoiceSentToInline(admin.TabularInline):
    model = InvoiceSentTo
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'child', 'student_name', 'invoice_date', 'due_date', 'total_amount', 'status']
    list_filter = ['status', 'payment_term', 'center_code']
    search_fields = ['number', 'student_name', 'parent_name', 'child__first_name', 'child__last_name']
    readonly_fields = ['gst_amount', 'total_amount']
    inlines = [InvoiceItemInline, InvoiceExtraItemInline, InvoiceDeductionInline, InvoiceSentToInline]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['child', 'kind', 'name', 'date', 'amount', 'paid']
    list_filter = ['kind', 'paid']
    search_fields = ['name', 'child__first_name', 'child__last_name']
