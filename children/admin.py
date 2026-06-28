from django.contrib import admin
from .models import Child, Contact, ChildEnrolment


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 1


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['system_id', 'first_name', 'last_name', 'centre', 'gender', 'date_of_birth']
    list_filter = ['centre', 'gender']
    search_fields = ['first_name', 'last_name', 'system_id']
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'child', 'relation', 'is_main', 'is_bill_payer']
    list_filter = ['is_main', 'is_bill_payer', 'is_emergency']


@admin.register(ChildEnrolment)
class ChildEnrolmentAdmin(admin.ModelAdmin):
    list_display = ['child', 'slot', 'start_date', 'end_date']
    list_filter = ['start_date']
