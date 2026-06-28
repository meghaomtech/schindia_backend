from django.contrib import admin
from .models import Role, RolePermission, RoleMember


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


class RoleMemberInline(admin.TabularInline):
    model = RoleMember
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'centre', 'description']
    list_filter = ['centre']
    search_fields = ['name']
    inlines = [RolePermissionInline, RoleMemberInline]
