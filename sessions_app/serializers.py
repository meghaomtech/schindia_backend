from rest_framework import serializers
from .models import Session, SessionSlot

# Predefined color palette for auto-assignment (Req 8.9)
SESSION_COLORS = [
    {'bg': '#e0f2fe', 'text': '#0369a1'},  # blue
    {'bg': '#fce7f3', 'text': '#be185d'},  # pink
    {'bg': '#dcfce7', 'text': '#166534'},  # green
    {'bg': '#fef3c7', 'text': '#92400e'},  # amber
    {'bg': '#ede9fe', 'text': '#5b21b6'},  # violet
    {'bg': '#ffedd5', 'text': '#c2410c'},  # orange
    {'bg': '#f0fdf4', 'text': '#15803d'},  # emerald
    {'bg': '#fdf2f8', 'text': '#9d174d'},  # rose
    {'bg': '#ecfeff', 'text': '#155e75'},  # cyan
    {'bg': '#fef9c3', 'text': '#854d0e'},  # yellow
    {'bg': '#f3e8ff', 'text': '#7e22ce'},  # purple
    {'bg': '#e0e7ff', 'text': '#3730a3'},  # indigo
]


def get_next_color(centre_id):
    """Pick the first colour from the palette not already in use at this centre."""
    from dynamo_backend.router import use_dynamo

    if use_dynamo():
        from dynamo_backend.services import sessions_db
        existing_sessions = sessions_db.list_sessions(str(centre_id))
        used_colors = {(s.get('color_bg'), s.get('color_text')) for s in existing_sessions}
    else:
        existing_sessions = Session.objects.filter(centre_id=centre_id)
        used_colors = set(existing_sessions.values_list('color_bg', 'color_text'))

    for color in SESSION_COLORS:
        if (color['bg'], color['text']) not in used_colors:
            return color

    # All colors used — cycle based on count
    count = len(used_colors)
    return SESSION_COLORS[count % len(SESSION_COLORS)]


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
        read_only_fields = ['id', 'color_bg', 'color_text', 'created_at']

    def get_enrolled_count(self, obj):
        """Count unique children assigned to this session (uses annotation if available)."""
        if hasattr(obj, 'enrolled_count_val'):
            return obj.enrolled_count_val
        return obj.children.count()

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

    def create(self, validated_data):
        """Auto-assign color on session creation (Req 8.9)."""
        centre = validated_data.get('centre')
        if centre:
            color = get_next_color(centre.id if hasattr(centre, 'id') else centre)
            validated_data['color_bg'] = color['bg']
            validated_data['color_text'] = color['text']
        return super().create(validated_data)


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
