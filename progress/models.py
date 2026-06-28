import uuid
from django.db import models
from children.models import Child


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
