import uuid
from django.conf import settings
from django.db import models
from centres.models import Centre


class Role(models.Model):
    DATA_SCOPE_CHOICES = [
        ('all', 'All data'),
        ('own', 'Own data only'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    data_scope = models.CharField(max_length=5, choices=DATA_SCOPE_CHOICES, default='all')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('centre', 'name')

    def __str__(self):
        return f"{self.name} ({self.centre.name})"


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    key = models.CharField(max_length=100)  # e.g. "children.view"
    edit = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'key')
        ordering = ['key']

    def __str__(self):
        return f"{self.role.name} - {self.key}"


class RoleMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='role_memberships'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('role', 'user')

    def __str__(self):
        return f"{self.user.email} → {self.role.name}"
