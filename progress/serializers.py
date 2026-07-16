from datetime import date as date_type

from rest_framework import serializers


class JourneyEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    child = serializers.CharField(source='child_id', required=False)
    type = serializers.ChoiceField(choices=['Milestone', 'Observation'])
    text = serializers.CharField()
    date = serializers.DateField()
    staff_name = serializers.CharField(max_length=150)
    created_at = serializers.CharField(read_only=True)


class ChildNoteSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    child = serializers.CharField(source='child_id', required=False)
    text = serializers.CharField()
    date = serializers.DateField()
    staff_name = serializers.CharField(max_length=150)
    created_at = serializers.CharField(read_only=True)


class AttendanceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    child = serializers.CharField(source='child_id', required=False)
    slot = serializers.CharField(source='slot_id', required=False, allow_null=True)
    session = serializers.CharField(source='session_id', required=False, allow_null=True)
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=['attended', 'absent', 'late'], default='attended')
    teacher = serializers.CharField(source='teacher_id', required=False, allow_null=True)
    teacher_name = serializers.CharField(read_only=True, required=False)
    session_name = serializers.CharField(read_only=True, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(read_only=True)

    def validate_date(self, value):
        if value > date_type.today():
            raise serializers.ValidationError('Cannot record attendance for a future date.')
        return value


class CourseProgressSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True, required=False)
    child = serializers.CharField(source='child_id', required=False)
    current_month = serializers.IntegerField(default=1)
    current_week = serializers.IntegerField(default=1)
    display = serializers.CharField(read_only=True, required=False)
    updated_at = serializers.CharField(read_only=True, required=False)

    def validate_current_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError('Month must be between 1 and 12.')
        return value

    def validate_current_week(self, value):
        if value < 1 or value > 4:
            raise serializers.ValidationError('Week must be between 1 and 4.')
        return value
