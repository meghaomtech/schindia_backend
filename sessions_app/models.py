import uuid
from django.conf import settings
from django.db import models
from centres.models import Centre, Room


class Session(models.Model):
    AGE_UNIT_CHOICES = [('months', 'Months'), ('years', 'Years')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(max_length=50)
    child_limit = models.PositiveIntegerField(default=12)
    age_from = models.PositiveIntegerField(default=0)  # in months
    age_to = models.PositiveIntegerField(default=5)    # in months
    age_unit = models.CharField(max_length=10, choices=AGE_UNIT_CHOICES, default='years')
    duration_hours = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=30)
    color_bg = models.CharField(max_length=20, default='#e0f2fe')
    color_text = models.CharField(max_length=20, default='#0369a1')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('centre', 'name')

    def __str__(self):
        return f"{self.name} ({self.centre.name})"

    @property
    def duration_total_minutes(self):
        return self.duration_hours * 60 + self.duration_minutes


class SessionSlot(models.Model):
    BOOKING_TYPE_CHOICES = [('one-off', 'One-off'), ('recurring', 'Recurring')]
    DAY_CHOICES = [
        ('mon', 'Mon'), ('tue', 'Tue'), ('wed', 'Wed'),
        ('thu', 'Thu'), ('fri', 'Fri'), ('sat', 'Sat'), ('sun', 'Sun'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name='slots')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='slots')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='slots')
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    starting_month = models.PositiveIntegerField(default=1)
    starting_week = models.PositiveIntegerField(default=1)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='teaching_slots'
    )
    children = models.ManyToManyField(
        'children.Child', blank=True, related_name='slot_assignments'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'start_time']

    def __str__(self):
        return f"{self.session.name} - {self.day} {self.start_time}"
