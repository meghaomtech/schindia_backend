import uuid
from django.db import models
from centres.models import Centre
from sessions_app.models import Session, SessionSlot


class Child(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Prefer not to say', 'Prefer not to say'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_id = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name='children')
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    date_of_birth = models.DateField()
    start_date = models.DateField()
    sibling = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='siblings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = 'children'

    def __str__(self):
        return f"{self.system_id} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.system_id:
            last = Child.objects.order_by('-system_id').first()
            if last and last.system_id.startswith('CHD-'):
                num = int(last.system_id.split('-')[1]) + 1
            else:
                num = 1
            self.system_id = f"CHD-{num:03d}"
        super().save(*args, **kwargs)


class Contact(models.Model):
    INVITE_CHOICES = [
        ("Don't invite", "Don't invite"),
        ('Parent', 'Parent'),
        ('Guardian', 'Guardian'),
        ('Carer', 'Carer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=150)
    relation = models.CharField(max_length=50)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    invite_as = models.CharField(max_length=20, choices=INVITE_CHOICES, default='Parent')
    is_main = models.BooleanField(default=False)
    is_bill_payer = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_main', 'name']

    def __str__(self):
        return f"{self.name} ({self.relation}) - {self.child}"


class ChildEnrolment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='enrolments')
    slot = models.ForeignKey(SessionSlot, on_delete=models.CASCADE, related_name='enrolments')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.child} → {self.slot}"
