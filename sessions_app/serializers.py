from rest_framework import serializers

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
    from dynamo_backend.services import sessions_db
    existing_sessions = sessions_db.list_sessions(str(centre_id))
    used_colors = {(s.get('color_bg'), s.get('color_text')) for s in existing_sessions}

    for color in SESSION_COLORS:
        if (color['bg'], color['text']) not in used_colors:
            return color

    # All colors used — cycle based on count
    count = len(used_colors)
    return SESSION_COLORS[count % len(SESSION_COLORS)]


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    centre = serializers.CharField(source='centre_id', required=False)
    name = serializers.CharField(max_length=50)
    child_limit = serializers.IntegerField(default=12)
    age_from = serializers.IntegerField(default=0)
    age_to = serializers.IntegerField(default=5)
    age_unit = serializers.ChoiceField(choices=['months', 'years'], default='years')
    duration_hours = serializers.IntegerField(default=1)
    duration_minutes = serializers.IntegerField(default=30)
    color_bg = serializers.CharField(read_only=True)
    color_text = serializers.CharField(read_only=True)
    enrolled_count = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    age_range_display = serializers.SerializerMethodField()
    created_at = serializers.CharField(read_only=True)

    def get_enrolled_count(self, obj):
        return len(obj.get('child_ids', [])) if isinstance(obj, dict) else 0

    def get_duration_display(self, obj):
        """Human-readable duration like '1hr 30min' or '2hr'."""
        hours = obj.get('duration_hours', 0)
        minutes = obj.get('duration_minutes', 0)
        parts = []
        if hours:
            parts.append(f"{hours}hr")
        if minutes:
            parts.append(f"{minutes}min")
        return ' '.join(parts) or '0min'

    def get_age_range_display(self, obj):
        """Human-readable age range like '0–12 months' or '2–3 years'."""
        return f"{obj.get('age_from', 0)}–{obj.get('age_to', 5)} {obj.get('age_unit', 'years')}"


class SessionSlotSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    centre = serializers.CharField(source='centre_id', required=False)
    room = serializers.CharField(source='room_id', required=False)
    session = serializers.CharField(source='session_id', required=False)
    day = serializers.ChoiceField(choices=['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])
    start_time = serializers.CharField()
    booking_type = serializers.ChoiceField(choices=['one-off', 'recurring'])
    start_date = serializers.CharField()
    end_date = serializers.CharField(required=False, allow_null=True)
    starting_month = serializers.IntegerField(default=1)
    starting_week = serializers.IntegerField(default=1)
    teacher_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    child_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    session_name = serializers.CharField(read_only=True)
    room_name = serializers.CharField(read_only=True)
    children_count = serializers.SerializerMethodField()
    duration_total_minutes = serializers.IntegerField(read_only=True)
    child_limit = serializers.IntegerField(read_only=True)
    color_bg = serializers.CharField(read_only=True)
    color_text = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)

    def get_children_count(self, obj):
        return len(obj.get('child_ids', [])) if isinstance(obj, dict) else 0


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
