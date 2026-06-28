from rest_framework import serializers
from .models import JourneyEntry, ChildNote


class JourneyEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JourneyEntry
        fields = ['id', 'child', 'type', 'text', 'date', 'staff_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChildNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildNote
        fields = ['id', 'child', 'text', 'date', 'staff_name', 'created_at']
        read_only_fields = ['id', 'created_at']
