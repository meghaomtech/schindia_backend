from datetime import timedelta, datetime, date

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
from centres.models import Centre, Room
from .models import Session, SessionSlot
from .serializers import SessionSerializer, SessionSlotSerializer, GenerateSlotsSerializer


DAY_MAP = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}


def time_to_minutes(t):
    """Convert a time object to minutes since midnight."""
    return t.hour * 60 + t.minute


def has_overlap(centre_id, room_id, date, start_minutes, duration_minutes, exclude_slot_id=None):
    """Check if a proposed slot conflicts with existing ones in the same room."""
    existing = SessionSlot.objects.filter(
        centre_id=centre_id,
        room_id=room_id,
        start_date=date,
    ).select_related('session')

    if exclude_slot_id:
        existing = existing.exclude(id=exclude_slot_id)

    proposed_end = start_minutes + duration_minutes

    for slot in existing:
        slot_start = time_to_minutes(slot.start_time)
        slot_duration = slot.session.duration_total_minutes
        slot_end = slot_start + slot_duration

        if start_minutes < slot_end and proposed_end > slot_start:
            return True

    return False


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            return Session.objects.filter(centre_id=centre_pk)
        return Session.objects.all()

    def perform_create(self, serializer):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            centre = Centre.objects.get(pk=centre_pk)
            serializer.save(centre=centre)
        else:
            serializer.save()


class SessionSlotViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSlotSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        centre_pk = self.kwargs.get('centre_pk')
        queryset = SessionSlot.objects.select_related('session', 'room', 'centre')

        if centre_pk:
            queryset = queryset.filter(centre_id=centre_pk)

        # Filter by week if provided
        week = self.request.query_params.get('week')
        if week:
            from datetime import datetime
            try:
                week_start = datetime.strptime(week, '%Y-%m-%d').date()
                week_end = week_start + timedelta(days=6)
                queryset = queryset.filter(start_date__gte=week_start, start_date__lte=week_end)
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            centre = Centre.objects.get(pk=centre_pk)
            serializer.save(centre=centre)
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def generate_slots(request, centre_pk):
    """Generate recurring weekly slots (up to 15) or a single one-off slot."""
    serializer = GenerateSlotsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        session = Session.objects.get(pk=data['session_id'], centre=centre)
    except Session.DoesNotExist:
        return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        room = Room.objects.get(pk=data['room_id'], centre=centre)
    except Room.DoesNotExist:
        return Response({'detail': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)

    start_date = data['start_date']
    start_time = data['start_time']
    start_minutes = time_to_minutes(start_time)
    duration_minutes = session.duration_total_minutes

    if data['booking_type'] == 'one-off':
        num_slots = 1
    else:
        num_slots = 15

    # Check for overlaps first
    conflicts = []
    slot_dates = []
    for i in range(num_slots):
        slot_date = start_date + timedelta(weeks=i)
        slot_dates.append(slot_date)
        if has_overlap(centre.id, room.id, slot_date, start_minutes, duration_minutes):
            conflicts.append(str(slot_date))

    if conflicts:
        return Response(
            {
                'detail': 'Time conflicts detected.',
                'conflicts': conflicts,
            },
            status=status.HTTP_409_CONFLICT
        )

    # Create slots
    created_slots = []
    starting_month = data['starting_month']
    starting_week = data['starting_week']

    for i, slot_date in enumerate(slot_dates):
        day = DAY_MAP[slot_date.weekday()]

        slot = SessionSlot.objects.create(
            centre=centre,
            room=room,
            session=session,
            day=day,
            start_time=start_time,
            booking_type=data['booking_type'],
            start_date=slot_date,
            starting_month=starting_month,
            starting_week=starting_week,
            notes=data.get('notes', ''),
        )

        if data.get('teacher_ids'):
            slot.teachers.set(data['teacher_ids'])
        if data.get('child_ids'):
            slot.children.set(data['child_ids'])

        created_slots.append(slot)

        # Advance week/month counters
        starting_week += 1
        if starting_week > 4:
            starting_week = 1
            starting_month += 1

    result_serializer = SessionSlotSerializer(created_slots, many=True)
    return Response(result_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def timetable(request, centre_pk):
    """
    Return timetable data for a centre for a given week.
    Query params:
      - week: ISO date string (YYYY-MM-DD) for the Monday of the week.
              Defaults to current week.
    
    Returns slots grouped by day with room info, session info, 
    enrolled children count, and course progress.
    """
    # Determine week range first (shared logic)
    week_param = request.query_params.get('week')
    if week_param:
        try:
            week_start = datetime.strptime(week_param, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Invalid week format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    if use_dynamo():
        return _timetable_dynamo(request, str(centre_pk), week_start, week_end)

    # Django ORM path
    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Get slots for this centre in this week range
    slots = SessionSlot.objects.filter(
        centre=centre,
        start_date__gte=week_start,
        start_date__lte=week_end,
    ).select_related('session', 'room').prefetch_related('children')

    # Also get recurring slots that fall within this week
    # Recurring slots have a start_date on or before this week's end
    # and would repeat weekly
    recurring_slots = SessionSlot.objects.filter(
        centre=centre,
        booking_type='recurring',
        start_date__lte=week_end,
    ).select_related('session', 'room').prefetch_related('children')

    # Build timetable data
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    timetable_data = {day: [] for day in days}

    # Track already-added slot IDs to avoid duplicates
    added_slot_ids = set()

    # Add direct week slots
    for slot in slots:
        day = DAY_MAP[slot.start_date.weekday()]
        children_count = slot.children.count()
        end_time_minutes = time_to_minutes(slot.start_time) + slot.session.duration_total_minutes
        end_hours = end_time_minutes // 60
        end_mins = end_time_minutes % 60

        timetable_data[day].append({
            'id': str(slot.id),
            'session_name': slot.session.name,
            'room_name': slot.room.name,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': f"{end_hours:02d}:{end_mins:02d}",
            'children_enrolled': children_count,
            'child_limit': slot.session.child_limit,
            'starting_month': slot.starting_month,
            'starting_week': slot.starting_week,
            'booking_type': slot.booking_type,
            'date': slot.start_date.isoformat(),
            'color_bg': slot.session.color_bg,
            'color_text': slot.session.color_text,
        })
        added_slot_ids.add(slot.id)

    # Add recurring slots that repeat into this week
    for slot in recurring_slots:
        if slot.id in added_slot_ids:
            continue

        # Check if this recurring slot's day matches a day in the requested week
        slot_day = slot.day
        if slot_day not in days:
            continue

        # Calculate if this slot would occur in this week
        day_index = days.index(slot_day)
        target_date = week_start + timedelta(days=day_index)

        # Only include if the recurring slot started on or before this date
        if slot.start_date > target_date:
            continue

        # Check week difference is valid (slot repeats weekly)
        days_diff = (target_date - slot.start_date).days
        if days_diff < 0 or days_diff % 7 != 0:
            continue

        children_count = slot.children.count()
        end_time_minutes = time_to_minutes(slot.start_time) + slot.session.duration_total_minutes
        end_hours = end_time_minutes // 60
        end_mins = end_time_minutes % 60

        # Calculate which month/week this occurrence is
        weeks_elapsed = days_diff // 7
        occ_month = slot.starting_month + (slot.starting_week - 1 + weeks_elapsed) // 4
        occ_week = ((slot.starting_week - 1 + weeks_elapsed) % 4) + 1

        timetable_data[slot_day].append({
            'id': str(slot.id),
            'session_name': slot.session.name,
            'room_name': slot.room.name,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': f"{end_hours:02d}:{end_mins:02d}",
            'children_enrolled': children_count,
            'child_limit': slot.session.child_limit,
            'starting_month': occ_month,
            'starting_week': occ_week,
            'booking_type': slot.booking_type,
            'date': target_date.isoformat(),
            'color_bg': slot.session.color_bg,
            'color_text': slot.session.color_text,
        })

    # Sort each day's slots by start_time
    for day in days:
        timetable_data[day].sort(key=lambda x: x['start_time'])

    # Get centre opening times and closure info
    closure_dates = centre.closure_dates or []
    opening_times = centre.opening_times or {}

    return Response({
        'centre_id': str(centre.id),
        'centre_name': centre.name,
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'opening_times': opening_times,
        'closure_dates': closure_dates,
        'timetable': timetable_data,
    })


def _timetable_dynamo(request, centre_id, week_start, week_end):
    """DynamoDB-based timetable view for production."""
    from dynamo_backend.services import centres_db, sessions_db

    centre = centres_db.get_centre(centre_id)
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Get all slots for this centre
    all_slots = sessions_db.list_slots(centre_id)
    # Get all sessions for lookup
    all_sessions = {s['id']: s for s in sessions_db.list_sessions(centre_id)}
    # Build room lookup
    rooms = {r['id']: r for r in centre.get('rooms', [])}

    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    timetable_data = {day: [] for day in days}

    for slot in all_slots:
        slot_date_str = slot.get('start_date', '')
        if not slot_date_str:
            continue

        try:
            slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
        except ValueError:
            continue

        # Check if slot falls in this week (direct or recurring)
        in_week = week_start <= slot_date <= week_end

        if not in_week and slot.get('booking_type') == 'recurring':
            # Check if recurring slot repeats into this week
            slot_day = slot.get('day', '')
            if slot_day in days:
                day_index = days.index(slot_day)
                target_date = week_start + timedelta(days=day_index)
                if slot_date <= target_date:
                    days_diff = (target_date - slot_date).days
                    if days_diff >= 0 and days_diff % 7 == 0:
                        in_week = True
                        slot_date = target_date

        if not in_week:
            continue

        session = all_sessions.get(slot.get('session_id', ''))
        if not session:
            continue

        room = rooms.get(slot.get('room_id', ''), {})
        duration = session.get('duration_hours', 1) * 60 + session.get('duration_minutes', 30)

        start_time = slot.get('start_time', '09:00')
        time_parts = start_time.split(':')
        start_minutes = int(time_parts[0]) * 60 + int(time_parts[1])
        end_minutes = start_minutes + duration
        end_hours = end_minutes // 60
        end_mins = end_minutes % 60

        day = DAY_MAP.get(slot_date.weekday(), 'mon')
        children_count = len(slot.get('child_ids', []))

        timetable_data[day].append({
            'id': slot.get('id', ''),
            'session_name': session.get('name', ''),
            'room_name': room.get('name', ''),
            'start_time': start_time,
            'end_time': f"{end_hours:02d}:{end_mins:02d}",
            'children_enrolled': children_count,
            'child_limit': session.get('child_limit', 12),
            'starting_month': slot.get('starting_month', 1),
            'starting_week': slot.get('starting_week', 1),
            'booking_type': slot.get('booking_type', 'recurring'),
            'date': slot_date.isoformat(),
            'color_bg': session.get('color_bg', '#e0f2fe'),
            'color_text': session.get('color_text', '#0369a1'),
        })

    # Sort each day
    for day in days:
        timetable_data[day].sort(key=lambda x: x['start_time'])

    return Response({
        'centre_id': centre_id,
        'centre_name': centre.get('name', ''),
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'opening_times': centre.get('opening_times', {}),
        'closure_dates': centre.get('closure_dates', []),
        'timetable': timetable_data,
    })
