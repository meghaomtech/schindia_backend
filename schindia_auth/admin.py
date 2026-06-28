from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'status', 'requested_at']
    list_filter = ['role', 'status']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-requested_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Shichida Fields', {'fields': ('role', 'status')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Shichida Fields', {'fields': ('role', 'status')}),
    )
