from django.contrib import admin
from .models import Session, SessionSlot


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'centre', 'child_limit', 'age_from', 'age_to', 'age_unit']
    list_filter = ['centre', 'age_unit']
    search_fields = ['name']


@admin.register(SessionSlot)
class SessionSlotAdmin(admin.ModelAdmin):
    list_display = ['session', 'room', 'day', 'start_time', 'start_date', 'booking_type']
    list_filter = ['centre', 'day', 'booking_type']
    search_fields = ['session__name']
