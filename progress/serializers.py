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


class CourseProgressSerializer(serializers.ModelSerializer):
    display = serializers.CharField(read_only=True)

    class Meta:
        model = CourseProgress
        fields = ['id', 'child', 'current_month', 'current_week', 'display', 'updated_at']
        read_only_fields = ['id', 'updated_at']
