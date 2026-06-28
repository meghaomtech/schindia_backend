from rest_framework import serializers
from .models import Session, SessionSlot


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            'id', 'centre', 'name', 'child_limit', 'age_from', 'age_to',
            'age_unit', 'duration_hours', 'duration_minutes',
            'color_bg', 'color_text', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        age_from = data.get('age_from', 0)
        age_to = data.get('age_to', 5)
        if age_from >= age_to:
            raise serializers.ValidationError(
                {'age_from': 'age_from must be less than age_to.'}
            )

        hours = data.get('duration_hours', 1)
        minutes = data.get('duration_minutes', 30)
        if hours * 60 + minutes < 15:
            raise serializers.ValidationError(
                {'duration_minutes': 'Total duration must be at least 15 minutes.'}
            )

        child_limit = data.get('child_limit', 12)
        if child_limit < 1:
            raise serializers.ValidationError(
                {'child_limit': 'Child limit must be at least 1.'}
            )

        return data


class SessionSlotSerializer(serializers.ModelSerializer):
    teacher_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    child_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = SessionSlot
        fields = [
            'id', 'centre', 'room', 'session', 'day', 'start_time',
            'booking_type', 'start_date', 'end_date', 'starting_month',
            'starting_week', 'teachers', 'children', 'teacher_ids',
            'child_ids', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'teachers', 'children']

    def create(self, validated_data):
        teacher_ids = validated_data.pop('teacher_ids', [])
        child_ids = validated_data.pop('child_ids', [])

        slot = SessionSlot.objects.create(**validated_data)

        if teacher_ids:
            slot.teachers.set(teacher_ids)
        if child_ids:
            slot.children.set(child_ids)

        return slot

    def update(self, instance, validated_data):
        teacher_ids = validated_data.pop('teacher_ids', None)
        child_ids = validated_data.pop('child_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if teacher_ids is not None:
            instance.teachers.set(teacher_ids)
        if child_ids is not None:
            instance.children.set(child_ids)

        return instance


class GenerateSlotsSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    room_id = serializers.UUIDField()
    start_time = serializers.TimeField()
    booking_type = serializers.ChoiceField(choices=['one-off', 'recurring'])
    start_date = serializers.DateField()
    starting_month = serializers.IntegerField(default=1)
    starting_week = serializers.IntegerField(default=1)
    teacher_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    child_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    notes = serializers.CharField(required=False, default='', allow_blank=True)
