from django.contrib import admin
from .models import JourneyEntry, ChildNote


@admin.register(JourneyEntry)
class JourneyEntryAdmin(admin.ModelAdmin):
    list_display = ['child', 'type', 'date', 'staff_name']
    list_filter = ['type', 'date']
    search_fields = ['child__first_name', 'child__last_name', 'text']


@admin.register(ChildNote)
class ChildNoteAdmin(admin.ModelAdmin):
    list_display = ['child', 'date', 'staff_name']
    list_filter = ['date']
    search_fields = ['child__first_name', 'child__last_name', 'text']
