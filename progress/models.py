import uuid
from django.conf import settings
from django.db import models
from children.models import Child
from sessions_app.models import Session, SessionSlot


class JourneyEntry(models.Model):
    TYPE_CHOICES = [('Milestone', 'Milestone'), ('Observation', 'Observation')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='journey_entries')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    text = models.TextField()
    date = models.DateField()
    staff_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'journey entries'

    def __str__(self):
        return f"{self.type}: {self.child} - {self.date}"


class ChildNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='notes')
    text = models.TextField()
    date = models.DateField()
    staff_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Note: {self.child} - {self.date}"


class Attendance(models.Model):
    """Track when a child attends a session slot."""
    STATUS_CHOICES = [
        ('attended', 'Attended'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='attendances')
    slot = models.ForeignKey(SessionSlot, on_delete=models.CASCADE, related_name='attendances')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='attended')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='taught_attendances'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('child', 'slot', 'date')

    def __str__(self):
        return f"{self.child} - {self.session.name} on {self.date}"


class CourseProgress(models.Model):
    """Track course progress (Month/Week) for a child."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.OneToOneField(Child, on_delete=models.CASCADE, related_name='course_progress')
    current_month = models.PositiveIntegerField(default=1)
    current_week = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'course progress'

    def __str__(self):
        return f"{self.child} - M{self.current_month} W{self.current_week}"

    @property
    def display(self):
        return f"M{self.current_month} W{self.current_week}"
