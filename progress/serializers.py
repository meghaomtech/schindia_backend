from datetime import date as date_type

from rest_framework import serializers
from .models import JourneyEntry, ChildNote, Attendance, CourseProgress


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


class AttendanceSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source='session.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'child', 'slot', 'session', 'date', 'status',
            'teacher', 'teacher_name', 'session_name', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name()
        return None

    def validate_date(self, value):
        if value > date_type.today():
            raise serializers.ValidationError('Cannot record attendance for a future date.')
        return value

    def validate(self, data):
        # Session must match slot's session if both provided
        slot = data.get('slot')
        session = data.get('session')
        if slot and session:
            if slot.session_id != session.id:
                raise serializers.ValidationError(
                    {'session': "Session must match the slot's session."}
                )

        # Duplicate attendance check (clean 400 instead of IntegrityError 500)
        child = data.get('child')
        att_date = data.get('date')
        if child and slot and att_date:
            existing = Attendance.objects.filter(child=child, slot=slot, date=att_date)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    'Attendance already recorded for this child on this date and slot.'
                )

        return data


class CourseProgressSerializer(serializers.ModelSerializer):
    display = serializers.CharField(read_only=True)

    class Meta:
        model = CourseProgress
        fields = ['id', 'child', 'current_month', 'current_week', 'display', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def validate_current_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError('Month must be between 1 and 12.')
        return value

    def validate_current_week(self, value):
        if value < 1 or value > 4:
            raise serializers.ValidationError('Week must be between 1 and 4.')
        return value
