import uuid
from django.db import models


class Centre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    street_address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    vat_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    manager_name = models.CharField(max_length=150)
    closure_dates = models.JSONField(default=list, blank=True)
    opening_times = models.JSONField(default=dict, blank=True)
    bank_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.system_id} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.system_id:
            last = Centre.objects.order_by('-system_id').first()
            if last and last.system_id.startswith('SC-'):
                num = int(last.system_id.split('-')[1]) + 1
            else:
                num = 1
            self.system_id = f"SC-{num:03d}"
        super().save(*args, **kwargs)


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('centre', 'name')

    def __str__(self):
        return f"{self.name} ({self.centre.name})"
