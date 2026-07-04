from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import RootAccessRequest

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


@admin.register(RootAccessRequest)
class RootAccessRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'status', 'requested_at', 'reviewed_at']
    list_filter = ['status']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'name', 'email', 'requested_at', 'reviewed_at']
    actions = ['approve_requests', 'reject_requests']

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        """When status is changed to 'approved' via the edit form, create the User."""
        if change and obj.status == 'approved':
            # Check if user already exists
            if not User.objects.filter(email=obj.email).exists():
                parts = obj.name.strip().split(' ', 1)
                user = User(
                    username=obj.email,
                    email=obj.email,
                    first_name=parts[0],
                    last_name=parts[1] if len(parts) > 1 else '',
                    role='root',
                    status='approved',
                    is_staff=True,
                )
                user.password = obj.password  # already hashed
                user.save()
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description='Approve selected root access requests')
    def approve_requests(self, request, queryset):
        approved = 0
        for req in queryset.filter(status='pending'):
            if User.objects.filter(email=req.email).exists():
                self.message_user(
                    request,
                    f"User with email {req.email} already exists. Skipped.",
                    level=messages.WARNING,
                )
                continue

            parts = req.name.strip().split(' ', 1)
            user = User(
                username=req.email,
                email=req.email,
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else '',
                role='root',
                status='approved',
                is_staff=True,
            )
            user.password = req.password  # already hashed
            user.save()

            req.status = 'approved'
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_at'])
            approved += 1

        if approved:
            self.message_user(request, f"{approved} root user(s) created successfully.")

    @admin.action(description='Reject selected root access requests')
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected', reviewed_at=timezone.now()
        )
        self.message_user(request, f"{updated} request(s) rejected.")
