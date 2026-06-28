from django.contrib import admin
from .models import Centre, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1


@admin.register(Centre)
class CentreAdmin(admin.ModelAdmin):
    list_display = ['system_id', 'name', 'city', 'manager_name', 'created_at']
    search_fields = ['name', 'city', 'system_id']
    inlines = [RoomInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'centre']
    list_filter = ['centre']
