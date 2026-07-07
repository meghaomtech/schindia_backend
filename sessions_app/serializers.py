from rest_framework import serializers
from .models import Session, SessionSlot


class SessionSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    age_range_display = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'centre', 'name', 'child_limit', 'age_from', 'age_to',
            'age_unit', 'duration_hours', 'duration_minutes',
            'color_bg', 'color_text', 'enrolled_count',
            'duration_display', 'age_range_display', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_enrolled_count(self, obj):
        """Count unique children assigned to this session."""
        return obj.children.count() if hasattr(obj, 'children') else 0

    def get_duration_display(self, obj):
        """Human-readable duration like '1hr 30min' or '2hr'."""
        parts = []
        if obj.duration_hours:
            parts.append(f"{obj.duration_hours}hr")
        if obj.duration_minutes:
            parts.append(f"{obj.duration_minutes}min")
        return ' '.join(parts) or '0min'

    def get_age_range_display(self, obj):
        """Human-readable age range like '0–12 months' or '2–3 years'."""
        return f"{obj.age_from}–{obj.age_to} {obj.age_unit}"

    def validate(self, data):
        age_from = data.get('age_from', 0)
        age_to = data.get('age_to', 5)
        if age_from >= age_to:
            raise serializers.ValidationError(
                {'age_from': 'age_from must be less than age_to.'}
            )

        hours = data.get('duration_hours', 1)
        minutes = data.get('duration_minutes', 30)
        total_minutes = hours * 60 + minutes
        if total_minutes < 30:
            raise serializers.ValidationError(
                {'duration_minutes': 'Total duration must be at least 30 minutes.'}
            )
        if total_minutes > 480:
            raise serializers.ValidationError(
                {'duration_minutes': 'Total duration must be 480 minutes (8 hours) or less.'}
            )

        child_limit = data.get('child_limit', 12)
        if child_limit < 1:
            raise serializers.ValidationError(
                {'child_limit': 'Child limit must be at least 1.'}
            )
        if child_limit > 50:
            raise serializers.ValidationError(
                {'child_limit': 'Child limit must be 50 or less.'}
            )

        # Session name uniqueness within centre (Req 8.8)
        name = data.get('name', '')
        centre = data.get('centre')
        if name and centre:
            existing = Session.objects.filter(centre=centre, name__iexact=name)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {'name': 'A session with this name already exists at this centre.'}
                )

        return data


class SessionSlotSerializer(serializers.ModelSerializer):
    teacher_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    child_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    session_name = serializers.CharField(source='session.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    children_count = serializers.SerializerMethodField()
    duration_total_minutes = serializers.IntegerField(
        source='session.duration_total_minutes', read_only=True
    )
    child_limit = serializers.IntegerField(source='session.child_limit', read_only=True)
    color_bg = serializers.CharField(source='session.color_bg', read_only=True)
    color_text = serializers.CharField(source='session.color_text', read_only=True)

    class Meta:
        model = SessionSlot
        fields = [
            'id', 'centre', 'room', 'session', 'day', 'start_time',
            'booking_type', 'start_date', 'end_date', 'starting_month',
            'starting_week', 'teachers', 'children', 'teacher_ids',
            'child_ids', 'notes', 'session_name', 'room_name',
            'children_count', 'duration_total_minutes', 'child_limit',
            'color_bg', 'color_text', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'teachers', 'children']

    def get_children_count(self, obj):
        return obj.children.count()

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
