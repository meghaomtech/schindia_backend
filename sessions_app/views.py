from datetime import timedelta, datetime, date

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import sessions_db, centres_db
from .serializers import SessionSerializer, SessionSlotSerializer, GenerateSlotsSerializer


DAY_MAP = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}


def time_to_minutes(t):
    """Convert a time object to minutes since midnight."""
    return t.hour * 60 + t.minute


class SessionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    serializer_class = SessionSerializer

    def list(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            sessions = sessions_db.list_sessions(str(centre_pk))
        else:
            # Standalone: check query param
            centre_id = request.query_params.get('centre')
            sessions = sessions_db.list_sessions(str(centre_id)) if centre_id else []
        return Response(sessions)

    def retrieve(self, request, *args, **kwargs):
        session = sessions_db.get_session(str(kwargs['pk']))
        if not session:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(session)

    def create(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if not centre_pk:
            return Response({'detail': 'A centre is required to create a session.'}, status=status.HTTP_400_BAD_REQUEST)

        from .serializers import get_next_color

        data = request.data.copy()

        # Validate using the serializer (Req 8.8 — name uniqueness, duration, age, child_limit)
        # We need to check name uniqueness against Dynamo
        name = data.get('name', '')
        if name:
            existing_sessions = sessions_db.list_sessions(str(centre_pk))
            for s in existing_sessions:
                if s.get('name', '').lower() == name.lower():
                    return Response(
                        {'name': ['A session with this name already exists at this centre.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Validate duration
        hours = int(data.get('duration_hours', 1))
        minutes = int(data.get('duration_minutes', 30))
        total_minutes = hours * 60 + minutes
        if total_minutes < 30:
            return Response(
                {'duration_minutes': ['Total duration must be at least 30 minutes.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if total_minutes > 480:
            return Response(
                {'duration_minutes': ['Total duration must be 480 minutes (8 hours) or less.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate child_limit
        child_limit = int(data.get('child_limit', 12))
        if child_limit < 1 or child_limit > 50:
            return Response(
                {'child_limit': ['Child limit must be between 1 and 50.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate age range
        age_from = int(data.get('age_from', 0))
        age_to = int(data.get('age_to', 5))
        if age_from >= age_to:
            return Response(
                {'age_from': ['age_from must be less than age_to.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        data.pop('centre', None)
        # Auto-assign color (Req 8.9 — first unused colour)
        color = get_next_color(centre_pk)
        data['color_bg'] = color['bg']
        data['color_text'] = color['text']
        session = sessions_db.create_session(str(centre_pk), data)
        return Response(session, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        session = sessions_db.get_session(str(kwargs['pk']))
        if not session:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Scope check: ensure session belongs to the centre in the URL
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk and session.get('centre_id') != str(centre_pk):
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        updated = sessions_db.update_session(str(kwargs['pk']), request.data)
        return Response(updated)

    def destroy(self, request, *args, **kwargs):
        session = sessions_db.get_session(str(kwargs['pk']))
        if not session:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Scope check
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk and session.get('centre_id') != str(centre_pk):
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check for dependent slots (same guard as Room deletion — Req 5.7)
        centre_id = session.get('centre_id', str(centre_pk) if centre_pk else '')
        if centre_id:
            slots = sessions_db.list_slots(centre_id)
            dependent_slots = [s for s in slots if s.get('session_id') == str(kwargs['pk'])]
            if dependent_slots:
                return Response(
                    {'detail': 'Cannot delete session with existing timetable slots. Remove slots first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        sessions_db.delete_session(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionSlotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    serializer_class = SessionSlotSerializer

    def list(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            week = request.query_params.get('week')
            slots = sessions_db.list_slots(str(centre_pk), week)
        else:
            centre_id = request.query_params.get('centre')
            if centre_id:
                week = request.query_params.get('week')
                slots = sessions_db.list_slots(str(centre_id), week)
            else:
                slots = []
        return Response(slots)

    def retrieve(self, request, *args, **kwargs):
        slot = sessions_db.get_slot(str(kwargs['pk']))
        if not slot:
            return Response({'detail': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(slot)

    def create(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk')
        if not centre_pk:
            return Response({'detail': 'A centre is required to create a slot.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()

        # Validate session exists
        session_id = data.get('session_id') or data.get('session')
        if session_id:
            session = sessions_db.get_session(str(session_id))
            if not session:
                return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Conflict detection: check room/time overlap
            room_id = data.get('room_id') or data.get('room')
            start_time = data.get('start_time', '09:00')
            start_date = data.get('start_date')
            if room_id and start_time and start_date:
                time_parts = start_time.split(':')
                start_minutes = int(time_parts[0]) * 60 + int(time_parts[1])
                duration = session.get('duration_hours', 1) * 60 + session.get('duration_minutes', 30)
                try:
                    slot_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    if sessions_db._has_overlap(str(centre_pk), str(room_id), slot_date, start_minutes, duration):
                        return Response(
                            {'detail': 'Time conflict detected for this room and time.'},
                            status=status.HTTP_409_CONFLICT
                        )
                except (ValueError, TypeError):
                    pass

        slot = sessions_db.create_slot(str(centre_pk), data)
        return Response(slot, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        slot = sessions_db.get_slot(str(kwargs['pk']))
        if not slot:
            return Response({'detail': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Scope check
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk and slot.get('centre_id') != str(centre_pk):
            return Response({'detail': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)

        updated = sessions_db.update_slot(str(kwargs['pk']), request.data)
        return Response(updated)

    def destroy(self, request, *args, **kwargs):
        slot = sessions_db.get_slot(str(kwargs['pk']))
        if not slot:
            return Response({'detail': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Scope check
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk and slot.get('centre_id') != str(centre_pk):
            return Response({'detail': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)

        sessions_db.delete_slot(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def generate_slots(request, centre_pk):
    """Generate recurring weekly slots (up to 15) or a single one-off slot."""
    serializer = GenerateSlotsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    session_data = {
        'session_id': str(data['session_id']),
        'room_id': str(data['room_id']),
        'start_time': data['start_time'].strftime('%H:%M'),
        'booking_type': data['booking_type'],
        'start_date': data['start_date'].isoformat(),
        'starting_month': data['starting_month'],
        'starting_week': data['starting_week'],
        'teacher_ids': [str(t) for t in data.get('teacher_ids', [])],
        'child_ids': [str(c) for c in data.get('child_ids', [])],
        'notes': data.get('notes', ''),
    }

    created_slots, error = sessions_db.generate_slots(str(centre_pk), session_data)

    if created_slots is None:
        if error == 'Session not found.':
            return Response({'detail': error}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {'detail': 'Time conflicts detected.', 'conflicts': error},
            status=status.HTTP_409_CONFLICT
        )

    return Response(created_slots, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def timetable(request, centre_pk):
    """
    Return timetable data for a centre for a given week.
    Query params:
      - week: ISO date string (YYYY-MM-DD) for the Monday of the week. Defaults to current week.
      - filter_type: 'all' | 'room' | 'session' (Req 10.5)
      - filter_id: UUID of the room or session to filter by

    Returns slots grouped by day with room info, session info,
    enrolled children count, and course progress.
    """
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

    return _timetable_dynamo(request, str(centre_pk), week_start, week_end)


def _timetable_dynamo(request, centre_id, week_start, week_end):
    """DynamoDB-based timetable view."""
    from dynamo_backend.services import centres_db as _centres_db

    centre = _centres_db.get_centre(centre_id)
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

    # Apply filters (Req 10.5)
    filter_type = request.query_params.get('filter_type', 'all')
    filter_id = request.query_params.get('filter_id')

    for slot in all_slots:
        if filter_type == 'room' and filter_id and slot.get('room_id') != filter_id:
            continue
        if filter_type == 'session' and filter_id and slot.get('session_id') != filter_id:
            continue

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
                # Respect end_date
                end_date_str = slot.get('end_date')
                if end_date_str:
                    try:
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                        if end_date < target_date:
                            continue
                    except (ValueError, TypeError):
                        pass
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
